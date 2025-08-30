"""
Instrument cache management.
Handles caching of exchange instrument information with TTL management.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class InstrumentCache:
    """Manages caching of exchange instrument information."""
    
    def __init__(self, cache_dir: str = "state", default_ttl: int = 1800):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "instrument_cache.json"
        self.default_ttl = default_ttl  # 30 minutes default
        
        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._last_cleanup = time.time()
        
        # Load existing cache
        self.load_cache()
    
    def load_cache(self):
        """Load cache from persistent storage."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get('instruments', {})
                    self._cache_timestamps = data.get('timestamps', {})
                print(f"✅ Loaded {len(self._cache)} instruments from cache")
            else:
                print("📁 No existing instrument cache found, starting fresh")
        except Exception as e:
            print(f"❌ Failed to load instrument cache: {e}")
            self._cache = {}
            self._cache_timestamps = {}
    
    def save_cache(self):
        """Save cache to persistent storage."""
        try:
            data = {
                'instruments': self._cache,
                'timestamps': self._cache_timestamps,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save instrument cache: {e}")
    
    def get_instrument(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get instrument information from cache.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Instrument information or None if not found/expired
        """
        if symbol not in self._cache:
            return None
        
        # Check if cache entry is expired
        if self._is_expired(symbol):
            self._remove_instrument(symbol)
            return None
        
        return self._cache[symbol].copy()
    
    def set_instrument(self, symbol: str, instrument_data: Dict[str, Any], ttl: Optional[int] = None):
        """
        Cache instrument information.
        
        Args:
            symbol: Trading symbol
            instrument_data: Instrument information
            ttl: Time to live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[symbol] = instrument_data.copy()
        self._cache_timestamps[symbol] = time.time() + ttl
        
        # Auto-save cache
        self.save_cache()
    
    def has_instrument(self, symbol: str) -> bool:
        """
        Check if instrument exists in cache and is not expired.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if valid instrument exists, False otherwise
        """
        if symbol not in self._cache:
            return False
        
        return not self._is_expired(symbol)
    
    def remove_instrument(self, symbol: str):
        """
        Remove instrument from cache.
        
        Args:
            symbol: Trading symbol
        """
        self._remove_instrument(symbol)
        self.save_cache()
    
    def _remove_instrument(self, symbol: str):
        """Remove instrument from memory cache."""
        if symbol in self._cache:
            del self._cache[symbol]
        if symbol in self._cache_timestamps:
            del self._cache_timestamps[symbol]
    
    def _is_expired(self, symbol: str) -> bool:
        """Check if instrument cache entry is expired."""
        if symbol not in self._cache_timestamps:
            return True
        
        return time.time() > self._cache_timestamps[symbol]
    
    def cleanup_expired(self):
        """Remove expired cache entries."""
        expired_symbols = []
        
        for symbol in list(self._cache.keys()):
            if self._is_expired(symbol):
                expired_symbols.append(symbol)
        
        for symbol in expired_symbols:
            self._remove_instrument(symbol)
        
        if expired_symbols:
            print(f"🧹 Cleaned up {len(expired_symbols)} expired instruments")
            self.save_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        total_instruments = len(self._cache)
        expired_count = sum(1 for symbol in self._cache if self._is_expired(symbol))
        valid_count = total_instruments - expired_count
        
        # Calculate average TTL remaining
        remaining_ttls = []
        for symbol in self._cache:
            if not self._is_expired(symbol):
                remaining = self._cache_timestamps[symbol] - current_time
                if remaining > 0:
                    remaining_ttls.append(remaining)
        
        avg_remaining_ttl = sum(remaining_ttls) / len(remaining_ttls) if remaining_ttls else 0
        
        return {
            'total_instruments': total_instruments,
            'valid_instruments': valid_count,
            'expired_instruments': expired_count,
            'cache_hit_rate': valid_count / total_instruments if total_instruments > 0 else 0,
            'average_remaining_ttl': avg_remaining_ttl,
            'default_ttl': self.default_ttl,
            'last_cleanup': self._last_cleanup
        }
    
    def clear_cache(self):
        """Clear all cached instruments."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.save_cache()
        print("🗑️ Instrument cache cleared")
    
    def get_instruments_by_type(self, instrument_type: str) -> List[str]:
        """
        Get symbols of a specific instrument type.
        
        Args:
            instrument_type: Type of instrument ('SWAP', 'SPOT', 'MARGIN')
        
        Returns:
            List of symbols of the specified type
        """
        symbols = []
        for symbol, instrument_data in self._cache.items():
            if not self._is_expired(symbol):
                inst_type = instrument_data.get('instType', '')
                if inst_type == instrument_type:
                    symbols.append(symbol)
        
        return symbols
    
    def get_instruments_by_quote(self, quote_currency: str) -> List[str]:
        """
        Get symbols with a specific quote currency.
        
        Args:
            quote_currency: Quote currency (e.g., 'USDT', 'BTC')
        
        Returns:
            List of symbols with the specified quote currency
        """
        symbols = []
        for symbol, instrument_data in self._cache.items():
            if not self._is_expired(symbol):
                quote = instrument_data.get('quoteCcy', '')
                if quote == quote_currency:
                    symbols.append(symbol)
        
        return symbols
    
    def search_instruments(self, query: str) -> List[str]:
        """
        Search instruments by symbol name.
        
        Args:
            query: Search query (case-insensitive)
        
        Returns:
            List of matching symbols
        """
        query_lower = query.lower()
        matches = []
        
        for symbol in self._cache:
            if not self._is_expired(symbol):
                if query_lower in symbol.lower():
                    matches.append(symbol)
        
        return matches
    
    def get_instrument_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get summary information for an instrument.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Summary dictionary or None if not found
        """
        instrument = self.get_instrument(symbol)
        if not instrument:
            return None
        
        return {
            'symbol': symbol,
            'inst_type': instrument.get('instType', ''),
            'base_currency': instrument.get('baseCcy', ''),
            'quote_currency': instrument.get('quoteCcy', ''),
            'tick_size': instrument.get('tickSz', 0),
            'lot_size': instrument.get('lotSz', 0),
            'min_size': instrument.get('minSz', 0),
            'contract_value': instrument.get('ctVal', 0),
            'status': instrument.get('state', ''),
            'expiry': instrument.get('expTime', ''),
            'cached_at': datetime.fromtimestamp(self._cache_timestamps.get(symbol, 0)).isoformat() if symbol in self._cache_timestamps else None
        }
    
    def refresh_instrument(self, symbol: str, new_data: Dict[str, Any], ttl: Optional[int] = None):
        """
        Refresh instrument data in cache.
        
        Args:
            symbol: Trading symbol
            new_data: New instrument data
            ttl: Time to live in seconds (uses default if None)
        """
        self.set_instrument(symbol, new_data, ttl)
        print(f"🔄 Refreshed instrument cache for {symbol}")
    
    def bulk_update(self, instruments_data: Dict[str, Dict[str, Any]], ttl: Optional[int] = None):
        """
        Update multiple instruments at once.
        
        Args:
            instruments_data: Dictionary of symbol -> instrument data
            ttl: Time to live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        current_time = time.time()
        updated_count = 0
        
        for symbol, instrument_data in instruments_data.items():
            self._cache[symbol] = instrument_data.copy()
            self._cache_timestamps[symbol] = current_time + ttl
            updated_count += 1
        
        self.save_cache()
        print(f"📦 Bulk updated {updated_count} instruments in cache")
    
    def get_cache_keys(self) -> List[str]:
        """Get all cached symbol keys."""
        return list(self._cache.keys())
    
    def is_cache_stale(self, max_age_hours: int = 1) -> bool:
        """
        Check if cache is stale (no recent updates).
        
        Args:
            max_age_hours: Maximum age in hours
        
        Returns:
            True if cache is stale, False otherwise
        """
        if not self._cache_timestamps:
            return True
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        latest_timestamp = max(self._cache_timestamps.values())
        
        return latest_timestamp < cutoff_time


# Global instrument cache instance
_instrument_cache = None

def get_instrument_cache() -> InstrumentCache:
    """Get the global instrument cache instance."""
    global _instrument_cache
    if _instrument_cache is None:
        _instrument_cache = InstrumentCache()
    return _instrument_cache


def cache_instrument(symbol: str, instrument_data: Dict[str, Any], ttl: Optional[int] = None):
    """Cache instrument data using global cache."""
    get_instrument_cache().set_instrument(symbol, instrument_data, ttl)


def get_cached_instrument(symbol: str) -> Optional[Dict[str, Any]]:
    """Get cached instrument data using global cache."""
    return get_instrument_cache().get_instrument(symbol)


def has_cached_instrument(symbol: str) -> bool:
    """Check if instrument is cached using global cache."""
    return get_instrument_cache().has_instrument(symbol)


def clear_instrument_cache():
    """Clear global instrument cache."""
    get_instrument_cache().clear_cache()


def get_instrument_cache_stats() -> Dict[str, Any]:
    """Get global instrument cache statistics."""
    return get_instrument_cache().get_cache_stats()

