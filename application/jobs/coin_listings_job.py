"""
Coin Listings Job (4h)
Caches trending, top volume, and other coin lists from OKX every 4 hours.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from loguru import logger

from .base_job import BaseJob


# Global cache for coin listings
_coin_listings_cache: Dict[str, Dict[str, Any]] = {}


def get_coin_listings_cache() -> Dict[str, Dict[str, Any]]:
    """Get the global coin listings cache."""
    return _coin_listings_cache


class CoinListingsJob(BaseJob):
    """4-hour coin listings update job."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
    
    async def initialize(self):
        """Initialize job components."""
        try:
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            logger.info("✅ CoinListingsJob initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CoinListingsJob: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.exchange_adapter:
                await self.exchange_adapter.close()
        except Exception as e:
            logger.error(f"❌ CoinListingsJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute coin listings update."""
        global _coin_listings_cache
        
        try:
            logger.info("[JOB] coin_listings_4h starting execution")
            
            # Fetch all SWAP tickers
            tickers = await self.exchange_adapter.fetch_tickers()
            swap_tickers = {k: v for k, v in tickers.items() if 'SWAP' in k and 'USDT' in k}
            
            logger.info(f"[COIN_LIST] Fetched {len(swap_tickers)} SWAP tickers")
            
            # 1. Top Volume (sorted by 24h quote volume)
            sorted_by_volume = sorted(
                swap_tickers.items(), 
                key=lambda x: x[1].get('quoteVolume', 0) or 0, 
                reverse=True
            )
            volume_coins = [self._extract_base(k) for k, _ in sorted_by_volume[:20]]
            
            # 2. Top Gainers (sorted by 24h percentage change, positive)
            sorted_by_gain = sorted(
                swap_tickers.items(), 
                key=lambda x: x[1].get('percentage', 0) or 0, 
                reverse=True
            )
            gainers_coins = [self._extract_base(k) for k, _ in sorted_by_gain[:20]]
            
            # 3. Trending (approximated by high volume + positive change)
            trending_coins = []
            for sym, ticker in swap_tickers.items():
                vol = ticker.get('quoteVolume', 0) or 0
                pct = ticker.get('percentage', 0) or 0
                if vol > 50000000 and pct > 0:  # High volume + positive
                    trending_coins.append((sym, vol * pct))
            trending_coins.sort(key=lambda x: x[1], reverse=True)
            trending_result = [self._extract_base(k) for k, _ in trending_coins[:20]]
            
            # 4. Losers (sorted by 24h percentage change, negative)
            sorted_by_loss = sorted(
                swap_tickers.items(), 
                key=lambda x: x[1].get('percentage', 0) or 0
            )
            losers_coins = [self._extract_base(k) for k, _ in sorted_by_loss[:20]]
            
            # 5. New Listings (OKX doesn't have direct endpoint, use tickers with low volume as proxy)
            # This is an approximation - coins with very low volume might be new
            sorted_by_low_vol = sorted(
                [(k, v) for k, v in swap_tickers.items() if (v.get('quoteVolume', 0) or 0) > 10000],
                key=lambda x: x[1].get('quoteVolume', 0) or 0
            )
            new_listings = [self._extract_base(k) for k, _ in sorted_by_low_vol[:20]]
            
            # Update cache
            now = datetime.now(timezone.utc)
            _coin_listings_cache = {
                'volume': {
                    'coins': volume_coins,
                    'updated_at': now.isoformat(),
                    'name': '📈 Top Hacim'
                },
                'trending': {
                    'coins': trending_result,
                    'updated_at': now.isoformat(),
                    'name': '🔥 Trending'
                },
                'gainers': {
                    'coins': gainers_coins,
                    'updated_at': now.isoformat(),
                    'name': '📈 Top Gainers'
                },
                'losers': {
                    'coins': losers_coins,
                    'updated_at': now.isoformat(),
                    'name': '📉 Düşenler'
                },
                'new_listings': {
                    'coins': new_listings,
                    'updated_at': now.isoformat(),
                    'name': '🆕 New Listings'
                },
                'all': {
                    'coins': [self._extract_base(k) for k in sorted_by_volume[:50]],
                    'updated_at': now.isoformat(),
                    'name': '💰 Tüm Coinler'
                }
            }
            
            logger.info(f"[COIN_LIST] Cache updated: volume={len(volume_coins)}, trending={len(trending_result)}, "
                       f"gainers={len(gainers_coins)}, losers={len(losers_coins)}")
            
        except Exception as e:
            logger.error(f"❌ CoinListingsJob execution failed: {e}")
            raise
    
    def _extract_base(self, symbol: str) -> str:
        """Extract base symbol from OKX symbol format."""
        # Handle formats like 'BTC/USDT:USDT' or 'BTC-USDT-SWAP'
        if '/' in symbol:
            return symbol.split('/')[0]
        elif '-' in symbol:
            return symbol.split('-')[0]
        return symbol
