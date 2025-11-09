"""
Decision Logger - Structured Logging System
Implements single-line summary + detailed file logging for trading decisions
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from infrastructure.config_manager import config_manager


class DecisionLogger:
    """
    Structured decision logging system.
    Provides single-line console summaries and detailed file logs.
    """
    
    def __init__(self):
        self.config = config_manager
        
        # Load configuration
        self.log_summary_mode, _ = self.config.get('logging.summary_mode', 'line')
        self.news_verbosity, _ = self.config.get('logging.news_verbosity', 'summary')
        self._decision_seen: Dict[tuple[str, str], str] = {}
        
        # Skip reason dictionary for consistent logging
        self.skip_reasons = {
            'gating': 'Gate not PASS',
            'once_per_bar': 'Already processed this bar',
            'same_direction_block': 'Same direction position exists',
            'below_min_size': 'Order size below minimum',
            'below_min_notional': 'Order value below minimum',
            'entry_cooldown': 'Entry cooldown active',
            'idempotent_exists': 'Order already exists',
            'no_signal': 'No valid signal',
            'not_profitable': 'Position not profitable for scale-in',
            'max_ladders_reached': 'Maximum ladders reached',
            'insufficient_distance': 'Insufficient price distance',
            'opposite_direction': 'Opposite direction signal',
            'no_flip_allowed': 'Reversal not enabled'
        }
        
        logger.info(f"[DECISION_LOGGER] Decision logger initialized:")
        logger.info(f"  summary_mode: {self.log_summary_mode}")
        logger.info(f"  news_verbosity: {self.news_verbosity}")
    
    def log_decision_summary(self, symbol: str, timeframe: str, signal_scores: Dict[str, float],
                           gate_result: str, gate_details: Dict[str, Any], direction: str,
                           size: float, leverage: float, sl_price: float, tp_price: float,
                           risk_exp: float, tier: str, cb_status: str, state_transition: str,
                           strategy: str, guards: Dict[str, bool], source: str,
                           bar_id: Optional[str] = None, run_id: Optional[str] = None) -> None:
        """
        Log single-line decision summary.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            signal_scores: Signal scores (TA, ML, News, Risk)
            gate_result: Gate result (PASS/PENDING/FAIL)
            gate_details: Gate details (persist, conf, age, hyst)
            direction: Trade direction
            size: Position size
            leverage: Leverage
            sl_price: Stop loss price
            tp_price: Take profit price
            risk_exp: Risk exposure
            tier: Risk tier
            cb_status: Circuit breaker status
            state_transition: State transition (READY→OPEN)
            strategy: Strategy mode
            guards: Guard statuses
            source: Configuration source
        """
        # Format time
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        cache_key = (symbol, timeframe)
        if bar_id and self._decision_seen.get(cache_key) == bar_id:
            logger.info(f"⏭️ {time_str} | {symbol} | tf={timeframe} bar={bar_id} decision skipped(idempotent)")
            return
        if bar_id:
            self._decision_seen[cache_key] = bar_id
        
        # Format signal scores
        ta_score = signal_scores.get('ta', 0.0)
        ml_score = signal_scores.get('ml', 0.0)
        news_score = signal_scores.get('news', 0.0)
        risk_score = signal_scores.get('risk', 0.0)
        final_score = signal_scores.get('final', 0.0)
        
        # Format gate details
        persist_info = gate_details.get('persist', '')
        conf_info = gate_details.get('conf', '')
        age_info = gate_details.get('age', '')
        hyst_info = gate_details.get('hyst', '')
        
        # Format guards
        once_ok = "OK" if guards.get('once_per_bar', True) else "HIT"
        cooldown_ok = "OK" if guards.get('cooldown', True) else "HIT"
        
        # Single-line summary
        summary = (
            f"ℹ️ {time_str} | {symbol} | tf={timeframe} | bar={bar_id or '-'} | run={run_id or '-'} | "
            f"TA={ta_score:.1f} ML={ml_score:.1f} News={news_score:.1f} Risk={risk_score:.1f} | "
            f"Final={final_score:.1f} ({gate_result}) | "
            f"Dir={direction} | Gate={gate_result} "
            f"(persist {persist_info}, conf {conf_info}, age {age_info}, hyst={hyst_info}) | "
            f"size={size:.1%} lev={leverage:.0f}x SL={sl_price:.0f} TP={tp_price:.0f} | "
            f"risk: exp={risk_exp:.0%} tier={tier} cb={cb_status} | "
            f"state: {state_transition} | strategy={strategy} | "
            f"once={once_ok} cooldown={cooldown_ok} | src={source}"
        )
        
        logger.info(summary)
    
    def log_skip_decision(self, symbol: str, reason: str, details: Dict[str, Any]) -> None:
        """
        Log skip decision with reason.
        
        Args:
            symbol: Trading symbol
            reason: Skip reason
            details: Skip details
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        # Get human-readable reason
        human_reason = self.skip_reasons.get(reason, reason)
        
        # Format details
        details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        
        skip_msg = f"⏭️ {time_str} | {symbol} | SKIP: {human_reason} | {details_str}"
        logger.info(skip_msg)
    
    def log_entry_decision(self, symbol: str, direction: str, quantity: float,
                          price: float, mode: str, strategy: str) -> None:
        """
        Log entry decision.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction
            quantity: Position quantity
            price: Entry price
            mode: Trading mode
            strategy: Strategy mode
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        entry_msg = (
            f"🚀 {time_str} | {symbol} | ENTRY: {direction} "
            f"qty={quantity:.4f} price={price:.2f} mode={mode} strategy={strategy}"
        )
        logger.info(entry_msg)
    
    def log_flip_decision(self, symbol: str, old_direction: str, new_direction: str,
                         quantity: float, price: float, mode: str) -> None:
        """
        Log flip decision.
        
        Args:
            symbol: Trading symbol
            old_direction: Old position direction
            new_direction: New position direction
            quantity: Position quantity
            price: Entry price
            mode: Trading mode
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        flip_msg = (
            f"🔄 {time_str} | {symbol} | FLIP: {old_direction}→{new_direction} "
            f"qty={quantity:.4f} price={price:.2f} mode={mode}"
        )
        logger.info(flip_msg)
    
    def log_scale_in_decision(self, symbol: str, direction: str, quantity: float,
                             price: float, ladder: int, mode: str) -> None:
        """
        Log scale-in decision.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction
            quantity: Position quantity
            price: Entry price
            ladder: Ladder number
            mode: Trading mode
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        scale_msg = (
            f"📈 {time_str} | {symbol} | SCALE-IN: {direction} "
            f"qty={quantity:.4f} price={price:.2f} ladder={ladder} mode={mode}"
        )
        logger.info(scale_msg)
    
    def log_position_tpsl(self, symbol: str, sl_order_id: str, tp_order_id: str,
                         sl_price: float, tp_price: float, mode: str) -> None:
        """
        Log position-level TP/SL creation.
        
        Args:
            symbol: Trading symbol
            sl_order_id: Stop loss order ID
            tp_order_id: Take profit order ID
            sl_price: Stop loss price
            tp_price: Take profit price
            mode: Trading mode
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        tpsl_msg = (
            f"🎯 {time_str} | {symbol} | POSITION-TP/SL: "
            f"SL={sl_order_id}@{sl_price:.2f} TP={tp_order_id}@{tp_price:.2f} mode={mode}"
        )
        logger.info(tpsl_msg)
    
    def log_trailing_modify(self, symbol: str, position_id: str, old_sl: float,
                           new_sl: float, modifications: int, mode: str) -> None:
        """
        Log trailing stop modification.
        
        Args:
            symbol: Trading symbol
            position_id: Position ID
            old_sl: Old stop loss price
            new_sl: New stop loss price
            modifications: Number of modifications
            mode: Trading mode
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        trail_msg = (
            f"📊 {time_str} | {symbol} | TRAILING-MODIFY: "
            f"pos={position_id} {old_sl:.2f}→{new_sl:.2f} mod#{modifications} mode={mode}"
        )
        logger.info(trail_msg)
    
    def log_safety_block(self, symbol: str, mode: str, reason: str) -> None:
        """
        Log safety block (non-LIVE mode).
        
        Args:
            symbol: Trading symbol
            mode: Trading mode
            reason: Block reason
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        safety_msg = f"🛡️ {time_str} | {symbol} | SAFETY: {mode} mode - {reason}"
        logger.info(safety_msg)
    
    def log_error(self, symbol: str, operation: str, error: str, details: Dict[str, Any]) -> None:
        """
        Log error with details.
        
        Args:
            symbol: Trading symbol
            operation: Operation that failed
            error: Error message
            details: Error details
        """
        time_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        error_msg = f"❌ {time_str} | {symbol} | ERROR: {operation} - {error} | {details_str}"
        logger.error(error_msg)
    
    def log_decision(self, symbol: str, timeframe: str, signal_scores: Dict[str, float],
                    gate_result: str, gate_details: Dict[str, Any], direction: str,
                    size: float, leverage: float, sl_price: float, tp_price: float,
                    risk_exp: float, tier: str, cb_status: str, state_transition: str,
                    strategy: str, guards: Dict[str, bool], source: str,
                    bar_id: Optional[str] = None, run_id: Optional[str] = None) -> None:
        """
        Alias for log_decision_summary for backward compatibility.
        """
        self.log_decision_summary(symbol, timeframe, signal_scores, gate_result, 
                                 gate_details, direction, size, leverage, sl_price, 
                                 tp_price, risk_exp, tier, cb_status, state_transition, 
                                 strategy, guards, source, bar_id=bar_id, run_id=run_id)


# Global decision logger instance
decision_logger = DecisionLogger()