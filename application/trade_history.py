"""
Trade History - Trade kayıt ve per-symbol streak tracking sistemi.

Bu modül:
1. Kapanan her işlemi kaydeder (symbol, direction, pnl, timestamp)
2. Per-symbol ardışık kayıp sayısını takip eder
3. Streak guard kontrolü için veri sağlar
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger


class TradeHistory:
    """Trade history management with per-symbol streak tracking."""
    
    def __init__(self):
        self.history_file = Path("data/trade_history.jsonl")
        self.streak_file = Path("data/symbol_streaks.json")
        
        # Per-symbol streak tracking: {symbol: consecutive_losses}
        self.symbol_streaks: Dict[str, int] = {}
        
        # Per-symbol last loss info
        self.last_loss_info: Dict[str, Dict[str, Any]] = {}
        
        # Ensure data dir exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_streaks()
        logger.info(f"✅ TradeHistory initialized. Tracking {len(self.symbol_streaks)} symbols.")
    
    def record_trade(self, symbol: str, direction: str, pnl: float, 
                    entry_price: float = 0, exit_price: float = 0,
                    entry_time: datetime = None, exit_time: datetime = None,
                    metadata: Dict = None) -> Dict[str, Any]:
        """
        Record a closed trade and update streak tracking.
        
        Returns:
            Dict with trade info and current streak status
        """
        # Extract base symbol
        base_symbol = self._extract_base(symbol)
        
        now = datetime.now(timezone.utc)
        trade_record = {
            'symbol': symbol,
            'base_symbol': base_symbol,
            'direction': direction.upper(),
            'pnl': float(pnl),
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'entry_time': entry_time.isoformat() if entry_time else None,
            'exit_time': exit_time.isoformat() if exit_time else now.isoformat(),
            'recorded_at': now.isoformat(),
            'is_win': pnl > 0,
            'metadata': metadata or {}
        }
        
        # Append to history file
        try:
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(trade_record) + '\n')
        except Exception as e:
            logger.error(f"Failed to write trade history: {e}")
        
        # Update streak tracking
        old_streak = self.symbol_streaks.get(base_symbol, 0)
        
        if pnl < 0:
            # Kayıp - streak artır
            self.symbol_streaks[base_symbol] = old_streak + 1
            self.last_loss_info[base_symbol] = {
                'pnl': pnl,
                'direction': direction.upper(),
                'timestamp': now.isoformat(),
                'entry_price': entry_price
            }
            new_streak = old_streak + 1
            logger.warning(f"🔴 [{base_symbol}] Kayıp #{new_streak}: PnL={pnl:.2f}")
        else:
            # Kazanç - streak sıfırla
            self.symbol_streaks[base_symbol] = 0
            if base_symbol in self.last_loss_info:
                del self.last_loss_info[base_symbol]
            new_streak = 0
            logger.info(f"🟢 [{base_symbol}] Kazanç! Streak sıfırlandı. PnL={pnl:.2f}")
        
        self._save_streaks()
        
        return {
            'trade': trade_record,
            'old_streak': old_streak,
            'new_streak': new_streak,
            'should_reduce_size': new_streak >= 2,
            'should_cooldown': new_streak >= 3,
            'should_full_stop': new_streak >= 7
        }
    
    def get_symbol_streak(self, symbol: str) -> int:
        """Get current streak for a symbol."""
        base_symbol = self._extract_base(symbol)
        return self.symbol_streaks.get(base_symbol, 0)
    
    def get_all_streaks(self) -> Dict[str, int]:
        """Get all symbol streaks."""
        return self.symbol_streaks.copy()
    
    def get_symbols_with_streak(self, min_streak: int = 2) -> List[str]:
        """Get symbols with streak >= min_streak."""
        return [s for s, streak in self.symbol_streaks.items() if streak >= min_streak]
    
    def get_recent_trades(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get recent trades, optionally filtered by symbol."""
        trades = []
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    for line in f:
                        try:
                            trade = json.loads(line.strip())
                            if symbol is None or trade.get('base_symbol') == self._extract_base(symbol):
                                trades.append(trade)
                        except:
                            continue
        except Exception as e:
            logger.error(f"Failed to read trade history: {e}")
        
        return trades[-limit:]
    
    def get_global_streak(self) -> int:
        """Get global consecutive loss streak (across all symbols)."""
        all_trades = self.get_recent_trades(limit=20)
        consecutive = 0
        for trade in reversed(all_trades):
            if trade.get('pnl', 0) < 0:
                consecutive += 1
            else:
                break
        return consecutive
    
    def reset_symbol_streak(self, symbol: str, reason: str = "manual"):
        """Manually reset a symbol's streak."""
        base_symbol = self._extract_base(symbol)
        old_streak = self.symbol_streaks.get(base_symbol, 0)
        self.symbol_streaks[base_symbol] = 0
        if base_symbol in self.last_loss_info:
            del self.last_loss_info[base_symbol]
        self._save_streaks()
        logger.info(f"🔄 [{base_symbol}] Streak reset: {old_streak} -> 0 ({reason})")
    
    def _extract_base(self, symbol: str) -> str:
        """Extract base symbol: 'SOL-USDT-SWAP' -> 'SOL'"""
        if '-' in symbol:
            return symbol.split('-')[0]
        if 'USDT' in symbol:
            return symbol.replace('USDT', '').replace('_', '')
        return symbol
    
    def _save_streaks(self):
        """Save streak data to disk."""
        try:
            with open(self.streak_file, 'w') as f:
                json.dump({
                    'symbol_streaks': self.symbol_streaks,
                    'last_loss_info': self.last_loss_info,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save streaks: {e}")
    
    def _load_streaks(self):
        """Load streak data from disk."""
        try:
            if self.streak_file.exists():
                with open(self.streak_file, 'r') as f:
                    data = json.load(f)
                    self.symbol_streaks = data.get('symbol_streaks', {})
                    self.last_loss_info = data.get('last_loss_info', {})
                    logger.debug(f"Loaded streaks: {self.symbol_streaks}")
        except Exception as e:
            logger.warning(f"Failed to load streaks: {e}")
            self.symbol_streaks = {}
            self.last_loss_info = {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get trade history and streak status."""
        return {
            'symbol_streaks': self.symbol_streaks,
            'symbols_with_2plus': self.get_symbols_with_streak(2),
            'symbols_with_3plus': self.get_symbols_with_streak(3),
            'global_streak': self.get_global_streak(),
            'total_trades': sum(1 for _ in open(self.history_file)) if self.history_file.exists() else 0
        }


# Global instance
_trade_history: Optional[TradeHistory] = None


def get_trade_history() -> TradeHistory:
    """Get global trade history instance."""
    global _trade_history
    if _trade_history is None:
        _trade_history = TradeHistory()
    return _trade_history
