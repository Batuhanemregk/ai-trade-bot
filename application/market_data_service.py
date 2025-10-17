"""
Market Data Service - Robust market data fetching with fallbacks
Enhanced with unified MarketDataCache for TA/ML/Risk sharing.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from loguru import logger


class MarketDataCache:
    """
    Unified market data cache shared between TA, ML, and Risk services.
    Ensures single fetch per analysis cycle and data consistency.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.ttl_seconds = 300  # 5 minutes
    
    def get(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get cached data for symbol and timeframe."""
        key = f"{symbol}:{timeframe}"
        
        if key not in self.cache:
            return None
        
        # Check if cache is still valid
        cache_time = self.cache_timestamps.get(key)
        if cache_time:
            age = (datetime.now(timezone.utc) - cache_time).total_seconds()
            if age > self.ttl_seconds:
                # Cache expired
                del self.cache[key]
                del self.cache_timestamps[key]
                return None
        
        return self.cache[key]
    
    def set(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Cache data for symbol and timeframe."""
        key = f"{symbol}:{timeframe}"
        self.cache[key] = data
        self.cache_timestamps[key] = datetime.now(timezone.utc)
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def get_age(self, symbol: str, timeframe: str) -> Optional[float]:
        """Get cache age in seconds."""
        key = f"{symbol}:{timeframe}"
        cache_time = self.cache_timestamps.get(key)
        if cache_time:
            return (datetime.now(timezone.utc) - cache_time).total_seconds()
        return None


# Global singleton cache
_market_data_cache = MarketDataCache()


def get_market_data_cache() -> MarketDataCache:
    """Get the global market data cache instance."""
    return _market_data_cache


class MarketDataService:
    """Robust market data fetching with multiple fallback strategies."""
    
    def __init__(self, exchange_adapter, policy: Dict):
        self.exchange_adapter = exchange_adapter
        self.policy = policy
        self.cache_path = Path("data/last_market_cache.json")
        self.cache_path.parent.mkdir(exist_ok=True)
        self.cache_ttl = 300  # 5 minutes
        
        # Load existing cache
        self.cache = self._load_cache()
        
        # Use global market data cache
        self.market_cache = get_market_data_cache()
    
    def _load_cache(self) -> Dict:
        """Load market data cache from disk."""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load market cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save market data cache to disk."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save market cache: {e}")
    
    async def fetch_market_data_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch market data for multiple symbols with fallbacks."""
        results = {}
        
        # Fetch all symbols in parallel
        tasks = []
        for symbol in symbols:
            task = self._fetch_single_symbol_data(symbol)
            tasks.append((symbol, task))
        
        # Wait for all tasks to complete
        for symbol, task in tasks:
            try:
                data = await task
                results[symbol] = data
            except Exception as e:
                logger.error(f"❌ Failed to fetch data for {symbol}: {e}")
                results[symbol] = None
        
        # Log summary
        successful = sum(1 for data in results.values() if data is not None)
        failed = len(symbols) - successful
        logger.info(f"[MARKET] batch fetch completed: {successful} success, {failed} failed")
        
        return results
    
    async def _fetch_single_symbol_data(self, symbol: str) -> Optional[Dict]:
        """Fetch market data for a single symbol with fallbacks."""
        try:
            # Normalize symbol for CCXT
            ccxt_symbol = self.exchange_adapter.normalize_symbol_for_ccxt(symbol)
            
            # Strategy 1: Try ticker first (fastest)
            ticker_data = await self._fetch_ticker(ccxt_symbol)
            if ticker_data:
                logger.info(f"[MARKET] sym={symbol} src=ticker price={ticker_data.get('price', 'N/A')} vol24h={ticker_data.get('volume', 'N/A')}")
                return ticker_data
            
            # Strategy 2: Try OHLCV (more reliable)
            ohlcv_data = await self._fetch_ohlcv(ccxt_symbol)
            if ohlcv_data and not ohlcv_data.empty:
                logger.info(f"[MARKET] sym={symbol} src=ohlcv price={ohlcv_data['close'].iloc[-1]:.2f} vol={ohlcv_data['volume'].sum():.0f}")
                return {
                    'price': float(ohlcv_data['close'].iloc[-1]),
                    'volume': float(ohlcv_data['volume'].sum()),
                    'high': float(ohlcv_data['high'].max()),
                    'low': float(ohlcv_data['low'].min()),
                    'change': float((ohlcv_data['close'].iloc[-1] - ohlcv_data['close'].iloc[-2]) / ohlcv_data['close'].iloc[-2] * 100) if len(ohlcv_data) > 1 else 0
                }
            
            # Strategy 3: Try cache
            cached_data = self._get_cached_data(symbol)
            if cached_data:
                logger.info(f"[MARKET] sym={symbol} src=cache price={cached_data.get('price', 'N/A')} vol={cached_data.get('volume', 'N/A')}")
                return cached_data
            
            # Strategy 4: Skip symbol
            logger.warning(f"[MARKET] sym={symbol} src=SKIP reason=no data (ticker/ohlcv/cache)")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    async def _fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker data."""
        try:
            ticker = await self.exchange_adapter.get_ticker(symbol)
            if ticker and 'last' in ticker:
                return {
                    'price': float(ticker['last']),
                    'volume': float(ticker.get('baseVolume', ticker.get('quoteVolume', 0))),
                    'high': float(ticker.get('high', ticker['last'])),
                    'low': float(ticker.get('low', ticker['last'])),
                    'change': float(ticker.get('change', 0))
                }
        except Exception as e:
            logger.debug(f"Ticker fetch failed for {symbol}: {e}")
        return None
    
    async def _fetch_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data."""
        try:
            ohlcv = await self.exchange_adapter.get_ohlcv(symbol, '1m', 60)
            if ohlcv and len(ohlcv) > 0:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            logger.debug(f"OHLCV fetch failed for {symbol}: {e}")
        return None
    
    def _get_cached_data(self, symbol: str) -> Optional[Dict]:
        """Get cached data if still valid."""
        try:
            if symbol in self.cache:
                cached = self.cache[symbol]
                cache_time = datetime.fromisoformat(cached['timestamp'])
                if (datetime.now(timezone.utc) - cache_time).total_seconds() < self.cache_ttl:
                    return cached['data']
        except Exception as e:
            logger.debug(f"Cache read failed for {symbol}: {e}")
        return None
    
    def _update_cache(self, symbol: str, data: Dict):
        """Update cache with new data."""
        try:
            self.cache[symbol] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': data
            }
            self._save_cache()
        except Exception as e:
            logger.error(f"❌ Failed to update cache for {symbol}: {e}")
    
    async def build_dataframes(self, market_data: Dict[str, Dict]) -> Dict[str, pd.DataFrame]:
        """Build DataFrames from market data."""
        dataframes = {}
        dropped_count = 0
        
        for symbol, data in market_data.items():
            if data is None:
                dropped_count += 1
                continue
                
            try:
                # Create DataFrame from market data
                df_data = {
                    'close': [data['price']],
                    'high': [data['high']],
                    'low': [data['low']],
                    'volume': [data['volume']],
                    'open': [data['price']]  # Use price as open for simplicity
                }
                
                df = pd.DataFrame(df_data)
                df.index = [datetime.now(timezone.utc)]
                dataframes[symbol] = df
                
                # Update cache
                self._update_cache(symbol, data)
                
            except Exception as e:
                logger.error(f"❌ Failed to build DataFrame for {symbol}: {e}")
                dropped_count += 1
        
        logger.info(f"[MARKET] dataframe built rows={len(dataframes)} dropped={dropped_count}")
        return dataframes
