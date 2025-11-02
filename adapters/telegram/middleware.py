"""
Telegram Middleware - Rate limiting, error handling, logging, and metrics hooks
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Any, Dict, Optional
from functools import wraps
from loguru import logger


class RateLimiter:
    """
    Simple rate limiter to prevent spam.
    
    Uses token bucket algorithm: allows N requests per time window.
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list[datetime]] = defaultdict(list)
        self.logger = logger.bind(component="rate_limiter")
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed for given key.
        
        Args:
            key: Request key (e.g., user_id, chat_id)
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests outside window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        self.logger.warning(f"Rate limit exceeded for key={key}")
        return False
    
    def reset(self, key: Optional[str] = None):
        """
        Reset rate limiter for a key or all keys.
        
        Args:
            key: Key to reset, or None for all keys
        """
        if key:
            self.requests.pop(key, None)
        else:
            self.requests.clear()


class ErrorHandler:
    """
    Error handler wrapper for async functions.
    
    Provides friendly error messages and retry functionality.
    """
    
    def __init__(self, show_friendly_errors: bool = True):
        """
        Initialize error handler.
        
        Args:
            show_friendly_errors: Whether to show user-friendly error messages
        """
        self.show_friendly_errors = show_friendly_errors
        self.logger = logger.bind(component="error_handler")
    
    def wrap_async(
        self,
        func: Callable,
        error_message: str = "Couldn't load data (timeout). Tap to retry.",
        include_retry: bool = True
    ):
        """
        Wrap an async function with error handling.
        
        Args:
            func: Async function to wrap
            error_message: User-friendly error message
            include_retry: Whether to include retry callback
        
        Returns:
            Wrapped function
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                
                if self.show_friendly_errors:
                    error_response = {
                        'text': error_message,
                        'error': str(e),
                        'retry_callback': None
                    }
                    
                    if include_retry:
                        # Generate retry callback based on function context
                        error_response['retry_callback'] = self._generate_retry_callback(func, args, kwargs)
                    
                    return error_response
                else:
                    raise
        
        return wrapper
    
    def _generate_retry_callback(self, func: Callable, args: tuple, kwargs: dict) -> Optional[str]:
        """
        Generate retry callback data.
        
        Args:
            func: Function that failed
            args: Function arguments
            kwargs: Function keyword arguments
        
        Returns:
            Callback data string or None
        """
        # For now, return a simple retry callback
        # This can be enhanced to include function context
        return "ai:retry"
    
    def handle_error(
        self,
        error: Exception,
        context: str = "",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle an error and return error response.
        
        Args:
            error: Exception that occurred
            context: Context description
            correlation_id: Optional correlation ID for tracking
        
        Returns:
            Error response dictionary
        """
        if not correlation_id:
            correlation_id = f"err_{int(time.time())}"
        
        self.logger.error(
            f"Error in {context}: {error}",
            correlation_id=correlation_id,
            exc_info=True
        )
        
        return {
            'text': f"Couldn't load {context} (timeout). Tap to retry.",
            'error': str(error),
            'correlation_id': correlation_id,
            'retry_callback': "ai:retry"
        }


class LoggingMiddleware:
    """
    Logging middleware for tracking render times and sizes.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="logging_middleware")
    
    def log_render(
        self,
        view: str,
        render_time_ms: float,
        message_size_bytes: int,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """
        Log a view render event.
        
        Args:
            view: View name
            render_time_ms: Render time in milliseconds
            message_size_bytes: Message size in bytes
            additional_context: Optional additional context
        """
        context_str = ""
        if additional_context:
            # Format context as key=value pairs
            context_parts = [f"{k}={v}" for k, v in additional_context.items()]
            context_str = " " + " ".join(context_parts)
        
        # Format: tg view=<id> ms=<t> size=<bytes> err=<0/1>
        err_flag = 1 if additional_context and additional_context.get('error') else 0
        self.logger.info(
            f"tg view={view} ms={render_time_ms:.0f} size={message_size_bytes} err={err_flag}{context_str}"
        )
    
    def log_callback(
        self,
        callback_data: str,
        process_time_ms: float,
        view: Optional[str] = None
    ):
        """
        Log a callback event.
        
        Args:
            callback_data: Callback data string
            view: Optional view name
            process_time_ms: Processing time in milliseconds
        """
        view_str = f" view={view}" if view else ""
        self.logger.info(
            f"TG callback={callback_data[:50]}{view_str} t={process_time_ms:.0f}ms"
        )


class MetricsHook:
    """
    Metrics instrumentation hook.
    
    Provides interface for recording metrics (wired to Prometheus).
    """
    
    def __init__(self):
        self.logger = logger.bind(component="metrics_hook")
        self.prometheus_exporter: Optional[Any] = None
    
    def set_prometheus_exporter(self, exporter: Any):
        """
        Set Prometheus exporter instance.
        
        Args:
            exporter: PrometheusExporter instance
        """
        self.prometheus_exporter = exporter
    
    def _get_exporter(self) -> Optional[Any]:
        """Get Prometheus exporter (lazy import)."""
        if self.prometheus_exporter:
            return self.prometheus_exporter
        
        try:
            from monitoring.prometheus_exporter import get_prometheus_exporter
            self.prometheus_exporter = get_prometheus_exporter()
            return self.prometheus_exporter
        except Exception as e:
            self.logger.warning(f"Failed to get Prometheus exporter: {e}")
            return None
    
    def record_view_render(
        self,
        view: str,
        render_time_ms: float,
        message_size_bytes: int,
        success: bool = True
    ):
        """
        Record view render metric.
        
        Args:
            view: View name
            render_time_ms: Render time in milliseconds
            message_size_bytes: Message size in bytes
            success: Whether render was successful
        """
        exporter = self._get_exporter()
        if exporter:
            try:
                exporter.record_tg_view_render(view, render_time_ms, message_size_bytes, success)
            except Exception as e:
                self.logger.error(f"Failed to record view render metric: {e}")
    
    def record_callback(
        self,
        view: str,
        action: str,
        success: bool = True
    ):
        """
        Record callback metric.
        
        Args:
            view: View name
            action: Action name
            success: Whether callback was successful
        """
        exporter = self._get_exporter()
        if exporter:
            try:
                exporter.record_tg_callback(view, action, success)
            except Exception as e:
                self.logger.error(f"Failed to record callback metric: {e}")
    
    def record_error(
        self,
        error_type: str,
        component: str = "telegram"
    ):
        """
        Record error metric.
        
        Args:
            error_type: Error type
            component: Component name (ignored, always telegram)
        """
        exporter = self._get_exporter()
        if exporter:
            try:
                exporter.record_tg_error(error_type)
            except Exception as e:
                self.logger.error(f"Failed to record error metric: {e}")
    
    def record_rate_limit(self):
        """Record rate limit metric."""
        exporter = self._get_exporter()
        if exporter:
            try:
                exporter.record_tg_rate_limit()
            except Exception as e:
                self.logger.error(f"Failed to record rate limit metric: {e}")


# Global instances
_rate_limiter: Optional[RateLimiter] = None
_error_handler: Optional[ErrorHandler] = None
_logging_middleware: Optional[LoggingMiddleware] = None
_metrics_hook: Optional[MetricsHook] = None


def get_rate_limiter(max_requests: int = 10, window_seconds: int = 60) -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests, window_seconds)
    return _rate_limiter


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def get_logging_middleware() -> LoggingMiddleware:
    """Get global logging middleware instance."""
    global _logging_middleware
    if _logging_middleware is None:
        _logging_middleware = LoggingMiddleware()
    return _logging_middleware


def get_metrics_hook() -> MetricsHook:
    """Get global metrics hook instance."""
    global _metrics_hook
    if _metrics_hook is None:
        _metrics_hook = MetricsHook()
    return _metrics_hook

