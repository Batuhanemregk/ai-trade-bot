"""
Re-Entry Guard - Koşul Değişimi Kontrolü
Kayıp sonrası aynı yöne tekrar girmeden önce piyasa koşullarının değiştiğini kontrol eder.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class ReEntryCheck:
    """Result of re-entry eligibility check."""
    allowed: bool
    reason: str
    conditions_met: Dict[str, bool]
    time_since_loss: Optional[float]  # hours


class ReEntryGuard:
    """
    Guards against entering the same direction after a loss without condition change.
    
    Koşullar (EN AZ 1 gerekli):
    - RSI delta > 10 puan
    - Fiyat > 1.0 ATR hareket (yön farketmez)
    - MACD ters yönde cross
    - Volume spike > 1.3x ortalama
    
    Bypass:
    - 4 saat bekleme → koşul aranmadan giriş izni
    - Ters yönde giriş → koşul aranmaz
    """
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.state_file = Path('data/re_entry_state.json')
        
        # Config from policy
        re_entry_config = policy.get('trading', {}).get('re_entry', {})
        self.rsi_delta_threshold = re_entry_config.get('rsi_delta', 10)
        self.atr_threshold = re_entry_config.get('atr_threshold', 1.0)
        self.volume_spike_threshold = re_entry_config.get('volume_spike', 1.3)
        self.bypass_hours = re_entry_config.get('bypass_hours', 4)
        
        # Last losing trade state per symbol
        self.last_loss_state: Dict[str, Dict[str, Any]] = {}
        
        self._load_state()
        logger.info(f"✅ ReEntryGuard initialized (RSI delta>{self.rsi_delta_threshold}, ATR>{self.atr_threshold})")
    
    def record_trade_result(self, symbol: str, direction: str, pnl: float, 
                           entry_price: float, rsi: float, atr: float):
        """Record trade result for future re-entry checks."""
        if pnl < 0:
            # Kayıp işlem - state'i kaydet
            self.last_loss_state[symbol] = {
                'direction': direction.upper(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'entry_price': entry_price,
                'rsi_at_entry': rsi,
                'atr_at_entry': atr,
                'pnl': pnl
            }
            self._save_state()
            logger.info(f"[RE-ENTRY] Kayıp kaydedildi: {symbol} {direction} PnL={pnl:.2f}")
        else:
            # Kazanç - state'i temizle
            if symbol in self.last_loss_state:
                del self.last_loss_state[symbol]
                self._save_state()
                logger.info(f"[RE-ENTRY] Kazanç sonrası state temizlendi: {symbol}")
    
    def check_re_entry(self, symbol: str, direction: str, 
                      current_price: float, current_rsi: float, 
                      current_atr: float, current_volume: float,
                      avg_volume: float, macd_crossed: bool = False) -> ReEntryCheck:
        """
        Check if re-entry is allowed based on condition changes.
        
        Args:
            symbol: Trading symbol
            direction: Proposed direction ('LONG' or 'SHORT')
            current_price: Current price
            current_rsi: Current RSI value
            current_atr: Current ATR value
            current_volume: Current bar volume
            avg_volume: Average volume (last 10 bars)
            macd_crossed: Whether MACD crossed in opposite direction since last trade
            
        Returns:
            ReEntryCheck with allowed status and reasons
        """
        direction = direction.upper()
        
        # Eğer bu sembolde kayıp yok, giriş serbest
        if symbol not in self.last_loss_state:
            return ReEntryCheck(
                allowed=True,
                reason="no_previous_loss",
                conditions_met={},
                time_since_loss=None
            )
        
        last_loss = self.last_loss_state[symbol]
        last_direction = last_loss['direction']
        
        # Ters yönde giriş → koşul aranmaz
        if direction != last_direction:
            return ReEntryCheck(
                allowed=True,
                reason="opposite_direction",
                conditions_met={},
                time_since_loss=self._hours_since(last_loss['timestamp'])
            )
        
        # Aynı yönde giriş - koşulları kontrol et
        time_since_loss = self._hours_since(last_loss['timestamp'])
        
        # 4 saat bypass
        if time_since_loss >= self.bypass_hours:
            # State'i temizle - 4 saat geçti
            del self.last_loss_state[symbol]
            self._save_state()
            return ReEntryCheck(
                allowed=True,
                reason=f"bypass_{self.bypass_hours}h_timeout",
                conditions_met={},
                time_since_loss=time_since_loss
            )
        
        # Koşulları kontrol et
        conditions = {}
        
        # 1. RSI Delta
        rsi_at_entry = last_loss.get('rsi_at_entry', 50)
        rsi_delta = abs(current_rsi - rsi_at_entry)
        conditions['rsi_delta'] = rsi_delta > self.rsi_delta_threshold
        
        # 2. Fiyat ATR
        entry_price = last_loss.get('entry_price', current_price)
        atr_at_entry = last_loss.get('atr_at_entry', current_atr)
        price_change = abs(current_price - entry_price)
        atr_move = price_change / atr_at_entry if atr_at_entry > 0 else 0
        conditions['price_atr'] = atr_move >= self.atr_threshold
        
        # 3. Volume Spike
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        conditions['volume_spike'] = volume_ratio >= self.volume_spike_threshold
        
        # 4. MACD Cross
        conditions['macd_cross'] = macd_crossed
        
        # En az 1 koşul sağlanmalı
        any_condition_met = any(conditions.values())
        
        if any_condition_met:
            # Koşul sağlandı - state'i temizle
            del self.last_loss_state[symbol]
            self._save_state()
            
            met_conditions = [k for k, v in conditions.items() if v]
            logger.info(f"[RE-ENTRY] {symbol} giriş izni: {met_conditions}")
            
            return ReEntryCheck(
                allowed=True,
                reason=f"condition_met: {', '.join(met_conditions)}",
                conditions_met=conditions,
                time_since_loss=time_since_loss
            )
        
        # Hiçbir koşul sağlanmadı
        logger.info(f"[RE-ENTRY] {symbol} BLOK: Koşullar değişmedi. RSI delta={rsi_delta:.1f}, "
                   f"ATR move={atr_move:.2f}, Volume ratio={volume_ratio:.2f}")
        
        return ReEntryCheck(
            allowed=False,
            reason="no_condition_change",
            conditions_met=conditions,
            time_since_loss=time_since_loss
        )
    
    def _hours_since(self, timestamp_str: str) -> float:
        """Calculate hours since timestamp."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            delta = datetime.now(timezone.utc) - timestamp
            return delta.total_seconds() / 3600
        except:
            return 0
    
    def _save_state(self):
        """Save state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({
                    'last_loss_state': self.last_loss_state,
                    'last_update': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save re-entry state: {e}")
    
    def _load_state(self):
        """Load state from disk."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.last_loss_state = data.get('last_loss_state', {})
                    logger.debug(f"Loaded re-entry state for {len(self.last_loss_state)} symbols")
        except Exception as e:
            logger.error(f"Failed to load re-entry state: {e}")
            self.last_loss_state = {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current re-entry guard status."""
        return {
            'active_blocks': len(self.last_loss_state),
            'blocked_symbols': list(self.last_loss_state.keys()),
            'config': {
                'rsi_delta': self.rsi_delta_threshold,
                'atr_threshold': self.atr_threshold,
                'volume_spike': self.volume_spike_threshold,
                'bypass_hours': self.bypass_hours
            }
        }


# Global instance
_re_entry_guard: Optional[ReEntryGuard] = None


def get_re_entry_guard(policy: Dict[str, Any] = None) -> ReEntryGuard:
    """Get global re-entry guard instance."""
    global _re_entry_guard
    if _re_entry_guard is None:
        if policy is None:
            from infrastructure.bootstrap import load_policy
            policy = load_policy()
        _re_entry_guard = ReEntryGuard(policy)
    return _re_entry_guard
