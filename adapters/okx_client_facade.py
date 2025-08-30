"""
OKX Client Facade - Simplified interface for OKX API operations
"""

import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger

from .exchange_okx_rest import OKXRESTAdapter


# Global cache for symbol metadata
_symbol_meta_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 3600  # 1 hour cache TTL
_last_cache_update = 0


async def get_symbol_meta(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get symbol metadata including tick size, lot size, min size, etc.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
        
    Returns:
        Symbol metadata dictionary or None if not found
    """
    global _symbol_meta_cache, _last_cache_update
    
    # Check cache first
    if symbol in _symbol_meta_cache:
        return _symbol_meta_cache[symbol]
    
    # Check if cache needs refresh
    current_time = asyncio.get_event_loop().time()
    if current_time - _last_cache_update > _cache_ttl:
        await _refresh_symbol_cache()
    
    # Return from cache if available
    return _symbol_meta_cache.get(symbol)


async def _refresh_symbol_cache():
    """Refresh the symbol metadata cache from OKX API."""
    global _symbol_meta_cache, _last_cache_update
    
    try:
        # Create OKX REST adapter
        adapter = OKXRESTAdapter()
        
        # Fetch all instruments
        instruments = await adapter.get_instruments()
        
        if instruments and 'data' in instruments:
            # Clear old cache
            _symbol_meta_cache.clear()
            
            # Process instruments
            for instrument in instruments['data']:
                symbol = instrument.get('instId', '')
                if symbol:
                    # Extract relevant metadata
                    meta = {
                        'symbol': symbol,
                        'tickSz': float(instrument.get('tickSz', '0.01')),
                        'minSz': float(instrument.get('minSz', '0.001')),
                        'lotSz': float(instrument.get('lotSz', '0.001')),
                        'contractVal': float(instrument.get('ctVal', '1.0')),
                        'category': instrument.get('instType', ''),
                        'baseCcy': instrument.get('baseCcy', ''),
                        'quoteCcy': instrument.get('quoteCcy', ''),
                        'state': instrument.get('state', ''),
                        'expTime': instrument.get('expTime', ''),
                    }
                    _symbol_meta_cache[symbol] = meta
            
            _last_cache_update = asyncio.get_event_loop().time()
            logger.info(f"✅ Symbol cache refreshed: {len(_symbol_meta_cache)} symbols")
            
    except Exception as e:
        logger.error(f"❌ Failed to refresh symbol cache: {e}")
        # Keep old cache if refresh fails


def get_symbol_meta_sync(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous version of get_symbol_meta.
    Note: This will return None if cache is empty. Use async version for fresh data.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Symbol metadata from cache or None
    """
    return _symbol_meta_cache.get(symbol)


def get_tick_size(symbol: str, default: float = 0.01) -> float:
    """
    Get tick size for a symbol.
    
    Args:
        symbol: Trading symbol
        default: Default tick size if symbol not found
        
    Returns:
        Tick size
    """
    meta = get_symbol_meta_sync(symbol)
    if meta and 'tickSz' in meta:
        return meta['tickSz']
    return default


def get_min_size(symbol: str, default: float = 0.001) -> float:
    """
    Get minimum size for a symbol.
    
    Args:
        symbol: Trading symbol
        default: Default min size if symbol not found
        
    Returns:
        Minimum size
    """
    meta = get_symbol_meta_sync(symbol)
    if meta and 'minSz' in meta:
        return meta['minSz']
    return default


def get_lot_size(symbol: str, default: float = 0.001) -> float:
    """
    Get lot size for a symbol.
    
    Args:
        symbol: Trading symbol
        default: Default lot size if symbol not found
        
    Returns:
        Lot size
    """
    meta = get_symbol_meta_sync(symbol)
    if meta and 'lotSz' in meta:
        return meta['lotSz']
    return default


def get_contract_value(symbol: str, default: float = 1.0) -> float:
    """
    Get contract value for a symbol.
    
    Args:
        symbol: Trading symbol
        default: Default contract value if symbol not found
        
    Returns:
        Contract value
    """
    meta = get_symbol_meta_sync(symbol)
    if meta and 'contractVal' in meta:
        return meta['contractVal']
    return default


def get_fallback_tick_size(symbol: str) -> float:
    """
    Get fallback tick size based on symbol name.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Fallback tick size
    """
    if "BTC" in symbol:
        return 0.1
    elif "ETH" in symbol:
        return 0.01
    elif "USDT" in symbol:
        return 0.01
    else:
        return 0.01


def get_fallback_min_size(symbol: str) -> float:
    """
    Get fallback minimum size based on symbol name.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Fallback minimum size
    """
    if "BTC" in symbol:
        return 0.0001
    elif "ETH" in symbol:
        return 0.001
    else:
        return 0.001


def get_fallback_lot_size(symbol: str) -> float:
    """
    Get fallback lot size based on symbol name.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Fallback lot size
    """
    if "BTC" in symbol:
        return 0.0001
    elif "ETH" in symbol:
        return 0.001
    else:
        return 0.001


# Initialize cache on module import
async def _init_cache():
    """Initialize the symbol cache."""
    await _refresh_symbol_cache()


# Export functions
__all__ = [
    'get_symbol_meta',
    'get_symbol_meta_sync',
    'get_tick_size',
    'get_min_size',
    'get_lot_size',
    'get_contract_value',
    'get_fallback_tick_size',
    'get_fallback_min_size',
    'get_fallback_lot_size',
]
