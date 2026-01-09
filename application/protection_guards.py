"""
Protection Guards - Trading Protection System
Implements once_per_bar, entry_cooldown, same_direction_block, reversal, idempotency,
re-entry guard, and higher timeframe bias filter.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import pandas as pd

from infrastructure.config_manager import config_manager

# Import new guard modules
try:
    from application.re_entry_guard import get_re_entry_guard
    RE_ENTRY_GUARD_AVAILABLE = True
except ImportError:
    RE_ENTRY_GUARD_AVAILABLE = False
    logger.warning("ReEntryGuard not available")

try:
    from application.higher_tf_bias_filter import get_htf_bias_filter
    HTF_BIAS_FILTER_AVAILABLE = True
except ImportError:
    HTF_BIAS_FILTER_AVAILABLE = False
    logger.warning("HigherTimeframeBiasFilter not available")



@dataclass
class ProtectionResult:
    """Result of protection guard check"""
    allowed: bool
    reason: str
    details: Dict[str, Any]


class ProtectionGuards:
    """
    Trading protection guards system.
    Implements all protection mechanisms as specified.
    """
    
    def __init__(self):
        self.config = config_manager
        self._once_per_bar_store = {}  # In-memory store for once-per-bar
        self._entry_cooldown_store = {}  # In-memory store for cooldown
        self._idempotency_store = {}  # In-memory store for idempotency
        
        # Load configuration
        self.once_per_bar_enabled, _ = self.config.get('trading.strategy.once_per_bar', True)
        self.same_direction_block, _ = self.config.get('trading.strategy.same_direction_block', True)
        self.reversal_enabled, _ = self.config.get('trading.strategy.reversal_enabled', True)
        self.entry_cooldown_bars, _ = self.config.get('trading.entry_cooldown_bars', 2)
        self.use_position_tpsl, _ = self.config.get('trading.use_position_tpsl', True)
        self.reduce_only, _ = self.config.get('trading.reduce_only', True)
        
        # Initialize new guard modules
        self.re_entry_guard = get_re_entry_guard() if RE_ENTRY_GUARD_AVAILABLE else None
        self.htf_bias_filter = get_htf_bias_filter() if HTF_BIAS_FILTER_AVAILABLE else None
        
        logger.info(f"[GUARDS] Protection guards initialized:")
        logger.info(f"  once_per_bar: {self.once_per_bar_enabled}")
        logger.info(f"  same_direction_block: {self.same_direction_block}")
        logger.info(f"  reversal_enabled: {self.reversal_enabled}")
        logger.info(f"  entry_cooldown_bars: {self.entry_cooldown_bars}")
        logger.info(f"  use_position_tpsl: {self.use_position_tpsl}")
        logger.info(f"  reduce_only: {self.reduce_only}")
        logger.info(f"  re_entry_guard: {'enabled' if self.re_entry_guard else 'disabled'}")
        logger.info(f"  htf_bias_filter: {'enabled' if self.htf_bias_filter else 'disabled'}")
    
    def check_re_entry(self, symbol: str, direction: str, 
                       ohlcv_data: Optional[pd.DataFrame] = None) -> ProtectionResult:
        """
        Check re-entry guard after a losing trade.
        NOTE: Full integration requires RSI, ATR, volume data from signal processor.
        For now, we check only time-based bypass.
        """
        if not self.re_entry_guard:
            return ProtectionResult(True, "re_entry_disabled", {})
        
        try:
            # Simplified check - just verify no recent loss state or time bypass
            base_symbol = symbol.split('-')[0] if '-' in symbol else symbol
            
            if base_symbol not in self.re_entry_guard.last_loss_state:
                return ProtectionResult(True, "no_previous_loss", {})
            
            last_loss = self.re_entry_guard.last_loss_state[base_symbol]
            last_direction = last_loss.get('direction', '')
            
            # Opposite direction always allowed
            if direction.upper() != last_direction.upper():
                return ProtectionResult(True, "opposite_direction", {})
            
            # Check time bypass
            time_since_loss = self.re_entry_guard._hours_since(last_loss.get('timestamp', ''))
            if time_since_loss >= self.re_entry_guard.bypass_hours:
                # Clear state and allow
                del self.re_entry_guard.last_loss_state[base_symbol]
                self.re_entry_guard._save_state()
                return ProtectionResult(True, f"bypass_{self.re_entry_guard.bypass_hours}h_timeout", 
                                       {"hours_since_loss": time_since_loss})
            
            # Block same direction within bypass period
            return ProtectionResult(False, "same_direction_within_bypass_period", 
                                   {"hours_since_loss": time_since_loss, 
                                    "bypass_hours": self.re_entry_guard.bypass_hours})
            
        except Exception as e:
            logger.warning(f"Re-entry guard error: {e}")
            return ProtectionResult(True, "re_entry_error", {"error": str(e)})
    
    def check_htf_bias(self, symbol: str, direction: str,
                       ohlcv_1h: Optional[pd.DataFrame] = None,
                       ohlcv_4h: Optional[pd.DataFrame] = None) -> ProtectionResult:
        """
        Check higher timeframe bias filter.
        """
        if not self.htf_bias_filter:
            return ProtectionResult(True, "htf_bias_disabled", {})
        
        try:
            # Call check_signal_alignment - returns BiasResult object
            result = self.htf_bias_filter.check_signal_alignment(
                symbol, direction, ohlcv_1h, ohlcv_4h
            )
            
            # BiasResult has: bias, confidence, aligned_with_signal, block_trade, reason, details
            if result.block_trade:
                return ProtectionResult(False, f"htf_bias_blocked_{result.reason}", 
                                       {"bias": result.bias, "confidence": result.confidence})
            else:
                return ProtectionResult(True, f"htf_bias_aligned", 
                                       {"bias": result.bias, "confidence": result.confidence})
                                       
        except Exception as e:
            logger.warning(f"HTF bias filter error: {e}")
            return ProtectionResult(True, "htf_bias_error", {"error": str(e)})


    
    def check_once_per_bar(self, symbol: str, timeframe: str, bar_id: str) -> ProtectionResult:
        """
        Check once-per-bar protection.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '15m')
            bar_id: Bar identifier (e.g., '2025-10-23T15:00Z')
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if not self.once_per_bar_enabled:
            return ProtectionResult(True, "disabled", {})
        
        key = f"{symbol}:{timeframe}:{bar_id}"
        
        if key in self._once_per_bar_store:
            return ProtectionResult(
                False, 
                "once_per_bar", 
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "bar_id": bar_id,
                    "first_processed": self._once_per_bar_store[key]
                }
            )
        
        # Mark as processed
        self._once_per_bar_store[key] = datetime.now(timezone.utc)
        
        return ProtectionResult(True, "ok", {"symbol": symbol, "bar_id": bar_id})
    
    def check_entry_cooldown(self, symbol: str, last_entry_time: Optional[datetime]) -> ProtectionResult:
        """
        Check entry cooldown protection.
        
        Args:
            symbol: Trading symbol
            last_entry_time: Last entry time for this symbol
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if not last_entry_time:
            return ProtectionResult(True, "no_previous_entry", {})
        
        # Calculate cooldown duration (15 minutes per bar)
        cooldown_minutes = self.entry_cooldown_bars * 15
        cooldown_duration = timedelta(minutes=cooldown_minutes)
        
        time_since_entry = datetime.now(timezone.utc) - last_entry_time
        
        if time_since_entry < cooldown_duration:
            remaining_minutes = (cooldown_duration - time_since_entry).total_seconds() / 60
            return ProtectionResult(
                False,
                "entry_cooldown",
                {
                    "symbol": symbol,
                    "last_entry": last_entry_time.isoformat(),
                    "cooldown_minutes": cooldown_minutes,
                    "remaining_minutes": round(remaining_minutes, 1)
                }
            )
        
        return ProtectionResult(True, "cooldown_ok", {"symbol": symbol, "time_since_entry_minutes": round(time_since_entry.total_seconds() / 60, 1)})
    
    def check_same_direction_block(self, symbol: str, direction: str, current_positions: Dict[str, Any]) -> ProtectionResult:
        """
        Check same direction block protection.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ('LONG' or 'SHORT')
            current_positions: Current positions dictionary
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if not self.same_direction_block:
            return ProtectionResult(True, "disabled", {})
        
        # Check if there's already a position in the same direction
        if symbol in current_positions:
            position = current_positions[symbol]
            position_direction = position.get('side', '').upper()
            
            if position_direction == direction.upper():
                return ProtectionResult(
                    False,
                    "same_direction_block",
                    {
                        "symbol": symbol,
                        "direction": direction,
                        "existing_position": position,
                        "existing_direction": position_direction
                    }
                )
        
        return ProtectionResult(True, "direction_ok", {"symbol": symbol, "direction": direction})
    
    def check_reversal(self, symbol: str, direction: str, current_positions: Dict[str, Any]) -> ProtectionResult:
        """
        Check if this is a valid reversal.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ('LONG' or 'SHORT')
            current_positions: Current positions dictionary
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if not self.reversal_enabled:
            return ProtectionResult(True, "disabled", {})
        
        # Check if there's a position in opposite direction (valid reversal)
        if symbol in current_positions:
            position = current_positions[symbol]
            position_direction = position.get('side', '').upper()
            
            if position_direction != direction.upper():
                return ProtectionResult(
                    True,
                    "valid_reversal",
                    {
                        "symbol": symbol,
                        "new_direction": direction,
                        "existing_position": position,
                        "existing_direction": position_direction
                    }
                )
        
        return ProtectionResult(True, "no_reversal_needed", {"symbol": symbol, "direction": direction})
    
    def check_idempotency(self, client_order_id: str) -> ProtectionResult:
        """
        Check idempotency protection.
        
        Args:
            client_order_id: Client order ID to check
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if client_order_id in self._idempotency_store:
            return ProtectionResult(
                False,
                "idempotent_exists",
                {
                    "client_order_id": client_order_id,
                    "first_created": self._idempotency_store[client_order_id]
                }
            )
        
        # Mark as created
        self._idempotency_store[client_order_id] = datetime.now(timezone.utc)
        
        return ProtectionResult(True, "ok", {"client_order_id": client_order_id})
    
    def check_gating(self, gate_result: str) -> ProtectionResult:
        """
        Check gating protection.
        
        Args:
            gate_result: Gate result ('PASS', 'PENDING', 'FAIL')
            
        Returns:
            ProtectionResult with allowed/reason
        """
        if gate_result != "PASS":
            return ProtectionResult(
                False,
                "gating",
                {
                    "gate_result": gate_result,
                    "required": "PASS"
                }
            )
        
        return ProtectionResult(True, "gating_ok", {"gate_result": gate_result})
    
    def check_min_notional(self, size: float, min_size: float, min_notional: float, 
                          price: float, mode: str) -> ProtectionResult:
        """
        Check minimum notional protection.
        
        Args:
            size: Order size
            min_size: Minimum order size
            min_notional: Minimum notional value
            price: Order price
            mode: Trading mode
            
        Returns:
            ProtectionResult with allowed/reason
        """
        # Check size constraints
        if size < min_size:
            return ProtectionResult(
                False,
                "below_min_size",
                {
                    "size": size,
                    "min_size": min_size,
                    "deficit": min_size - size,
                    "mode": mode
                }
            )
        
        # Check notional constraints
        notional_value = size * price
        if notional_value < min_notional:
            return ProtectionResult(
                False,
                "below_min_notional",
                {
                    "size": size,
                    "price": price,
                    "notional_value": notional_value,
                    "min_notional": min_notional,
                    "deficit": min_notional - notional_value,
                    "mode": mode
                }
            )
        
        return ProtectionResult(True, "min_ok", {
            "size": size,
            "price": price,
            "notional_value": notional_value,
            "min_size": min_size,
            "min_notional": min_notional,
            "mode": mode
        })
    
    def comprehensive_check(self, symbol: str, direction: str, timeframe: str, bar_id: str,
                           gate_result: str, client_order_id: str, size: float, 
                           min_size: float, min_notional: float, price: float,
                           mode: str, current_positions: Dict[str, Any],
                           last_entry_time: Optional[datetime] = None,
                           ohlcv_15m: Optional[pd.DataFrame] = None,
                           ohlcv_1h: Optional[pd.DataFrame] = None,
                           ohlcv_4h: Optional[pd.DataFrame] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Perform comprehensive protection check.
        
        Returns:
            Tuple of (allowed, skip_reason, details)
        """
        checks = [
            ("gating", self.check_gating(gate_result)),
            ("once_per_bar", self.check_once_per_bar(symbol, timeframe, bar_id)),
            ("entry_cooldown", self.check_entry_cooldown(symbol, last_entry_time)),
            ("same_direction_block", self.check_same_direction_block(symbol, direction, current_positions)),
            ("reversal", self.check_reversal(symbol, direction, current_positions)),
            ("idempotency", self.check_idempotency(client_order_id)),
            ("min_notional", self.check_min_notional(size, min_size, min_notional, price, mode)),
            # NEW: Re-entry guard
            ("re_entry", self.check_re_entry(symbol, direction, ohlcv_15m)),
            # NEW: Higher timeframe bias filter
            ("htf_bias", self.check_htf_bias(symbol, direction, ohlcv_1h, ohlcv_4h)),
        ]
        
        # Check each protection guard
        for check_name, result in checks:
            if not result.allowed:
                logger.info(f"[GUARDS] {check_name.upper()}: {result.reason} - {result.details}")
                return False, result.reason, result.details
        
        # All checks passed
        logger.info(f"[GUARDS] All protection checks passed for {symbol} {direction}")
        return True, "ok", {"symbol": symbol, "direction": direction, "mode": mode}


# Global protection guards instance
protection_guards = ProtectionGuards()
