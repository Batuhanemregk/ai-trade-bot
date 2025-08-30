"""
Error mapping utilities.
Maps OKX/CCXT errors to domain errors for consistent error handling.
"""

from typing import Any, Dict, Optional, Union


class DomainError(Exception):
    """Base domain error class."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, 
                 error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error
        self.error_code = error_code
        self.context = context or {}
    
    def __repr__(self):
        return f"{self.__class__.__name__}(message='{self.message}', error_code='{self.error_code}')"


class ExchangeError(DomainError):
    """Base exchange error class."""
    pass


class AuthenticationError(ExchangeError):
    """Authentication/authorization error."""
    pass


class RateLimitError(ExchangeError):
    """Rate limit exceeded error."""
    pass


class InsufficientFundsError(ExchangeError):
    """Insufficient funds error."""
    pass


class InvalidOrderError(ExchangeError):
    """Invalid order parameters error."""
    pass


class OrderError(ExchangeError):
    """Generic order error."""
    pass


class OrderNotFoundError(ExchangeError):
    """Order not found error."""
    pass


class SymbolNotFoundError(ExchangeError):
    """Symbol not found error."""
    pass


class NetworkError(ExchangeError):
    """Network/connection error."""
    pass


class TimeoutError(ExchangeError):
    """Request timeout error."""
    pass


class ValidationError(ExchangeError):
    """Data validation error."""
    pass


class ConfigurationError(ExchangeError):
    """Configuration error."""
    pass


class InstrumentError(ExchangeError):
    """Instrument-related error."""
    pass


class PositionError(ExchangeError):
    """Position-related error."""
    pass


class BalanceError(ExchangeError):
    """Balance-related error."""
    pass


class InsufficientBalanceError(BalanceError):
    """Insufficient balance error."""
    pass


class OrderExecutionError(ExchangeError):
    """Order execution error."""
    pass


class BracketOrderError(ExchangeError):
    """Bracket order error."""
    pass


class InvalidParameterError(ExchangeError):
    """Invalid parameter error."""
    pass


def map_okx_error(error_code: str, error_message: str, 
                  context: Optional[Dict[str, Any]] = None) -> DomainError:
    """Map OKX error code to domain error."""
    # Simple mapping for now
    if '50024' in error_code:
        return InsufficientBalanceError(message=error_message, error_code=error_code, context=context)
    elif '50010' in error_code or '50011' in error_code or '50012' in error_code:
        return InvalidOrderError(message=error_message, error_code=error_code, context=context)
    else:
        return ExchangeError(message=error_message, error_code=error_code, context=context)


def map_ccxt_error(ccxt_error: Exception, 
                   context: Optional[Dict[str, Any]] = None) -> DomainError:
    """Map CCXT error to domain error."""
    return ExchangeError(message=str(ccxt_error), original_error=ccxt_error, context=context)


def normalize_error(error: Union[Exception, DomainError], 
                   context: Optional[Dict[str, Any]] = None) -> DomainError:
    """Normalize any error to a domain error."""
    if isinstance(error, DomainError):
        return error
    
    # Try to map based on error type
    if hasattr(error, 'code') and hasattr(error, 'message'):
        # OKX-like error
        return map_okx_error(str(error.code), str(error.message), context)
    elif hasattr(error, 'type') and hasattr(error, 'message'):
        # CCXT-like error
        return map_ccxt_error(error, context)
    else:
        # Generic error
        return ExchangeError(message=str(error), original_error=error, context=context)


def create_domain_error(error_type: str, message: str, 
                       original_error: Optional[Exception] = None,
                       error_code: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None) -> DomainError:
    """Create a domain error of the specified type."""
    error_classes = {
        'DomainError': DomainError,
        'ExchangeError': ExchangeError,
        'AuthenticationError': AuthenticationError,
        'RateLimitError': RateLimitError,
        'InsufficientFundsError': InsufficientFundsError,
        'InvalidOrderError': InvalidOrderError,
        'OrderError': OrderError,
        'OrderNotFoundError': OrderNotFoundError,
        'SymbolNotFoundError': SymbolNotFoundError,
        'NetworkError': NetworkError,
        'TimeoutError': TimeoutError,
        'ValidationError': ValidationError,
        'ConfigurationError': ConfigurationError,
        'InstrumentError': InstrumentError,
        'PositionError': PositionError,
        'BalanceError': BalanceError,
        'InsufficientBalanceError': InsufficientBalanceError,
        'OrderExecutionError': OrderExecutionError,
        'BracketOrderError': BracketOrderError,
        'InvalidParameterError': InvalidParameterError,
    }
    
    error_class = error_classes.get(error_type, DomainError)
    return error_class(
        message=message,
        original_error=original_error,
        error_code=error_code,
        context=context or {}
    )


def is_retryable_error(error: Union[Exception, DomainError]) -> bool:
    """Check if error is retryable."""
    if isinstance(error, DomainError):
        # Retryable error types
        retryable_types = {
            RateLimitError,
            NetworkError,
            TimeoutError,
            ExchangeError  # Some exchange errors might be retryable
        }
        return type(error) in retryable_types
    
    # Generic retryable errors
    retryable_messages = [
        'rate limit',
        'network',
        'timeout',
        'busy',
        'try again',
        'temporary',
        'maintenance'
    ]
    
    error_message = str(error).lower()
    return any(msg in error_message for msg in retryable_messages)


def get_error_summary() -> Dict[str, Any]:
    """Get error mapping summary."""
    return {
        'error_classes': [
            'DomainError',
            'ExchangeError',
            'AuthenticationError',
            'RateLimitError',
            'InsufficientFundsError',
            'InvalidOrderError',
            'OrderError',
            'OrderNotFoundError',
            'SymbolNotFoundError',
            'NetworkError',
            'TimeoutError',
            'ValidationError',
            'ConfigurationError',
            'InstrumentError',
            'PositionError',
            'BalanceError',
            'InsufficientBalanceError',
            'OrderExecutionError',
            'BracketOrderError',
            'InvalidParameterError',
        ],
        'functions': [
            'map_okx_error',
            'map_ccxt_error',
            'normalize_error',
            'create_domain_error',
            'is_retryable_error',
            'get_error_summary',
            'get_error_mapper'
        ]
    }


def get_error_mapper() -> Dict[str, Any]:
    """Get error mapper configuration and utilities."""
    return {
        'mapper': {
            'okx': map_okx_error,
            'ccxt': map_ccxt_error,
            'normalize': normalize_error,
            'create': create_domain_error,
            'is_retryable': is_retryable_error
        },
        'error_types': {
            'DomainError': DomainError,
            'ExchangeError': ExchangeError,
            'AuthenticationError': AuthenticationError,
            'RateLimitError': RateLimitError,
            'InsufficientFundsError': InsufficientFundsError,
            'InvalidOrderError': InvalidOrderError,
            'OrderError': OrderError,
            'OrderNotFoundError': OrderNotFoundError,
            'SymbolNotFoundError': SymbolNotFoundError,
            'NetworkError': NetworkError,
            'TimeoutError': TimeoutError,
            'ValidationError': ValidationError,
            'ConfigurationError': ConfigurationError,
            'InstrumentError': InstrumentError,
            'PositionError': PositionError,
            'BalanceError': BalanceError,
            'InsufficientBalanceError': InsufficientBalanceError,
            'OrderExecutionError': OrderExecutionError,
            'BracketOrderError': BracketOrderError,
            'InvalidParameterError': InvalidParameterError,
        }
    }
