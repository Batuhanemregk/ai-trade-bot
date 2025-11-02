"""
Telegram adapter module for AiBotBS.
Provides Telegram bot integration with views, callbacks, and handlers.
"""

from .client import TelegramClient
from .callback_registry import CallbackRegistry, get_callback_registry
from .formatter import TelegramFormatter, get_formatter
from .middleware import (
    RateLimiter,
    ErrorHandler,
    LoggingMiddleware,
    MetricsHook,
    get_rate_limiter,
    get_error_handler,
    get_logging_middleware,
    get_metrics_hook,
)

__all__ = [
    "TelegramClient",
    "CallbackRegistry",
    "get_callback_registry",
    "TelegramFormatter",
    "get_formatter",
    "RateLimiter",
    "ErrorHandler",
    "LoggingMiddleware",
    "MetricsHook",
    "get_rate_limiter",
    "get_error_handler",
    "get_logging_middleware",
    "get_metrics_hook",
]

