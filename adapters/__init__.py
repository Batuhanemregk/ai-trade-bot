"""
Adapters Module for AiBotBS
Handles external service integrations and data transformations.
"""

from .exchange_okx_ccxt import OKXCCXTAdapter
from .exchange_okx_rest import OKXRESTAdapter
from .okx_client_facade import (
    get_symbol_meta, get_symbol_meta_sync,
    get_tick_size, get_min_size, get_lot_size, get_contract_value,
    get_fallback_tick_size, get_fallback_min_size, get_fallback_lot_size
)
from .error_mapping import (
    DomainError, OrderError, ValidationError, ExchangeError, NetworkError,
    InsufficientBalanceError, SymbolNotFoundError, RateLimitError, InvalidParameterError,
    map_okx_error, map_ccxt_error, normalize_error, create_domain_error,
    is_retryable_error, get_error_summary
)

__all__ = [
    # Exchange adapters
    'OKXCCXTAdapter',
    'OKXRESTAdapter',
    
    # OKX client facade functions
    'get_symbol_meta',
    'get_symbol_meta_sync',
    'get_tick_size',
    'get_min_size',
    'get_lot_size',
    'get_contract_value',
    'get_fallback_tick_size',
    'get_fallback_min_size',
    'get_fallback_lot_size',
    
    # Error handling
    'DomainError',
    'OrderError', 
    'ValidationError',
    'ExchangeError',
    'NetworkError',
    'InsufficientBalanceError',
    'SymbolNotFoundError',
    'RateLimitError',
    'InvalidParameterError',
    
    # Error mapping functions
    'map_okx_error',
    'map_ccxt_error',
    'normalize_error',
    'create_domain_error',
    'is_retryable_error',
    'get_error_summary'
]
