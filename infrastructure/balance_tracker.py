"""
Balance Tracker - Manages cached balance with smart refresh strategy.

Rules:
1. Update immediately after successful trades (open/close)
2. Periodic snapshot every 10 minutes if no trades
3. Position sizing ALWAYS uses cached free balance
"""

import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BalanceTracker:
    """
    Singleton balance tracker with smart caching.
    
    - Uses 'free' balance (available for trading), not 'total'
    - Updates after every trade
    - Periodic refresh every 10 minutes if idle
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cached_balance: float = 0.0
        self._last_update: float = 0.0
        self._snapshot_interval: int = 600  # 10 minutes default
        self._balance_type: str = "free"    # free | total
        self._initialized = True
        
        logger.info("💰 BalanceTracker initialized (singleton)")
    
    def configure(self, snapshot_interval: int = 600, balance_type: str = "free"):
        """Configure tracker from policy settings."""
        self._snapshot_interval = snapshot_interval
        self._balance_type = balance_type
        logger.info(f"💰 BalanceTracker configured: type={balance_type}, interval={snapshot_interval}s")
    
    async def get_balance(self, exchange_adapter, force_refresh: bool = False) -> float:
        """
        Get cached balance, refresh if needed.
        
        Args:
            exchange_adapter: Exchange adapter for fetching balance
            force_refresh: Force immediate refresh (after trade)
            
        Returns:
            Available USDT balance
        """
        now = time.time()
        age = now - self._last_update
        
        # Refresh if: forced, no cache, or cache too old
        should_refresh = force_refresh or self._cached_balance == 0.0 or age > self._snapshot_interval
        
        if should_refresh:
            try:
                if hasattr(exchange_adapter, 'fetch_balance'):
                    balance = await exchange_adapter.fetch_balance()
                else:
                    balance = await exchange_adapter.ccxt_client.fetch_balance()
                
                # Get the configured balance type (free or total)
                usdt_data = balance.get('USDT', {})
                new_balance = usdt_data.get(self._balance_type, 0.0)
                
                # Fallback to alternative if zero
                if new_balance == 0.0:
                    alt_type = 'total' if self._balance_type == 'free' else 'free'
                    new_balance = usdt_data.get(alt_type, 0.0)
                
                old_balance = self._cached_balance
                self._cached_balance = new_balance
                self._last_update = now
                
                if force_refresh:
                    logger.info(f"💰 [BALANCE] Force refresh: ${old_balance:.2f} → ${new_balance:.2f}")
                else:
                    logger.info(f"💰 [BALANCE] Snapshot update: ${new_balance:.2f} (age was {age:.0f}s)")
                    
            except Exception as e:
                logger.warning(f"⚠️ [BALANCE] Fetch failed: {e}, using cached ${self._cached_balance:.2f}")
        
        return self._cached_balance
    
    def invalidate(self):
        """Force next get_balance to refresh."""
        self._last_update = 0.0
        logger.debug("[BALANCE] Cache invalidated")
    
    def update_after_trade(self):
        """Mark that a trade just happened, next call will refresh."""
        self._last_update = 0.0  # Force refresh on next get
        logger.info("💰 [BALANCE] Will refresh on next position sizing")
    
    @property
    def cached_balance(self) -> float:
        return self._cached_balance
    
    @property
    def cache_age(self) -> float:
        return time.time() - self._last_update


# Singleton accessor
_balance_tracker: Optional[BalanceTracker] = None


def get_balance_tracker() -> BalanceTracker:
    """Get or create the singleton BalanceTracker."""
    global _balance_tracker
    if _balance_tracker is None:
        _balance_tracker = BalanceTracker()
    return _balance_tracker
