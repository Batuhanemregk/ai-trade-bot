"""
Domain errors for AiBotBS trading system.
Custom exceptions for business logic errors.
"""

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


# Trading Errors
class InsufficientBalanceError(DomainError):
    """Raised when there's insufficient balance for a trade."""

    def __init__(self, required: float, available: float, currency: str = "USDT"):
        message = f"Insufficient balance: required {required} {currency}, available {available} {currency}"
        super().__init__(message, "INSUFFICIENT_BALANCE", {
            "required": required,
            "available": available,
            "currency": currency
        })


class InvalidOrderError(DomainError):
    """Raised when an order is invalid."""

    def __init__(self, reason: str, order_details: dict[str, Any] | None = None):
        super().__init__(f"Invalid order: {reason}", "INVALID_ORDER", {
            "reason": reason,
            "order_details": order_details
        })


class OrderExecutionError(DomainError):
    """Raised when order execution fails."""

    def __init__(self, reason: str, order_id: str | None = None, exchange_error: str | None = None):
        super().__init__(f"Order execution failed: {reason}", "ORDER_EXECUTION_ERROR", {
            "reason": reason,
            "order_id": order_id,
            "exchange_error": exchange_error
        })


class PositionNotFoundError(DomainError):
    """Raised when a position is not found."""

    def __init__(self, symbol: str, side: str | None = None):
        message = f"Position not found for {symbol}"
        if side:
            message += f" ({side})"
        super().__init__(message, "POSITION_NOT_FOUND", {
            "symbol": symbol,
            "side": side
        })


# Risk Management Errors
class RiskLimitExceededError(DomainError):
    """Raised when a risk limit is exceeded."""

    def __init__(self, risk_type: str, current_value: float, limit_value: float, symbol: str | None = None):
        message = f"Risk limit exceeded: {risk_type} = {current_value} (limit: {limit_value})"
        if symbol:
            message += f" for {symbol}"
        super().__init__(message, "RISK_LIMIT_EXCEEDED", {
            "risk_type": risk_type,
            "current_value": current_value,
            "limit_value": limit_value,
            "symbol": symbol
        })


class LeverageExceededError(DomainError):
    """Raised when leverage exceeds the allowed limit."""

    def __init__(self, requested_leverage: float, max_leverage: float):
        message = f"Leverage {requested_leverage}x exceeds maximum allowed {max_leverage}x"
        super().__init__(message, "LEVERAGE_EXCEEDED", {
            "requested_leverage": requested_leverage,
            "max_leverage": max_leverage
        })


class DrawdownLimitExceededError(DomainError):
    """Raised when drawdown exceeds the allowed limit."""

    def __init__(self, current_drawdown: float, max_drawdown: float):
        message = f"Drawdown {current_drawdown:.2%} exceeds maximum allowed {max_drawdown:.2%}"
        super().__init__(message, "DRAWDOWN_LIMIT_EXCEEDED", {
            "current_drawdown": current_drawdown,
            "max_drawdown": max_drawdown
        })


# Scoring Errors
class InsufficientDataError(DomainError):
    """Raised when there's insufficient data for scoring."""

    def __init__(self, data_type: str, required_periods: int, available_periods: int):
        message = f"Insufficient {data_type} data: required {required_periods}, available {available_periods}"
        super().__init__(message, "INSUFFICIENT_DATA", {
            "data_type": data_type,
            "required_periods": required_periods,
            "available_periods": available_periods
        })


class ScoringError(DomainError):
    """Raised when scoring calculation fails."""

    def __init__(self, reason: str, symbol: str | None = None, component: str | None = None):
        message = f"Scoring error: {reason}"
        if symbol:
            message += f" for {symbol}"
        if component:
            message += f" in {component}"
        super().__init__(message, "SCORING_ERROR", {
            "reason": reason,
            "symbol": symbol,
            "component": component
        })


# Market Data Errors
class MarketDataError(DomainError):
    """Raised when market data operations fail."""

    def __init__(self, reason: str, symbol: str | None = None, timeframe: str | None = None):
        message = f"Market data error: {reason}"
        if symbol:
            message += f" for {symbol}"
        if timeframe:
            message += f" ({timeframe})"
        super().__init__(message, "MARKET_DATA_ERROR", {
            "reason": reason,
            "symbol": symbol,
            "timeframe": timeframe
        })


class SymbolNotFoundError(DomainError):
    """Raised when a trading symbol is not found."""

    def __init__(self, symbol: str, exchange: str | None = None):
        message = f"Symbol {symbol} not found"
        if exchange:
            message += f" on {exchange}"
        super().__init__(message, "SYMBOL_NOT_FOUND", {
            "symbol": symbol,
            "exchange": exchange
        })


# Exchange Errors
class ExchangeError(DomainError):
    """Raised when exchange operations fail."""

    def __init__(self, reason: str, exchange: str, error_code: str | None = None):
        message = f"Exchange error on {exchange}: {reason}"
        super().__init__(message, "EXCHANGE_ERROR", {
            "reason": reason,
            "exchange": exchange,
            "error_code": error_code
        })


class ExchangeConnectionError(DomainError):
    """Raised when connection to exchange fails."""

    def __init__(self, exchange: str, reason: str):
        message = f"Failed to connect to {exchange}: {reason}"
        super().__init__(message, "EXCHANGE_CONNECTION_ERROR", {
            "exchange": exchange,
            "reason": reason
        })


class ExchangeRateLimitError(DomainError):
    """Raised when exchange rate limit is exceeded."""

    def __init__(self, exchange: str, retry_after: int | None = None):
        message = f"Rate limit exceeded on {exchange}"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message, "EXCHANGE_RATE_LIMIT_ERROR", {
            "exchange": exchange,
            "retry_after": retry_after
        })


# News and Sentiment Errors
class NewsSourceError(DomainError):
    """Raised when news source operations fail."""

    def __init__(self, source: str, reason: str):
        message = f"News source error for {source}: {reason}"
        super().__init__(message, "NEWS_SOURCE_ERROR", {
            "source": source,
            "reason": reason
        })


class SentimentAnalysisError(DomainError):
    """Raised when sentiment analysis fails."""

    def __init__(self, reason: str, model: str | None = None, text: str | None = None):
        message = f"Sentiment analysis error: {reason}"
        if model:
            message += f" (model: {model})"
        super().__init__(message, "SENTIMENT_ANALYSIS_ERROR", {
            "reason": reason,
            "model": model,
            "text": text[:100] if text else None  # Truncate long text
        })


# Agent System Errors
class AgentError(DomainError):
    """Raised when agent operations fail."""

    def __init__(self, agent_name: str, reason: str, agent_type: str | None = None):
        message = f"Agent {agent_name} error: {reason}"
        if agent_type:
            message += f" (type: {agent_type})"
        super().__init__(message, "AGENT_ERROR", {
            "agent_name": agent_name,
            "agent_type": agent_type,
            "reason": reason
        })


class AgentCommunicationError(DomainError):
    """Raised when agent communication fails."""

    def __init__(self, from_agent: str, to_agent: str, reason: str):
        message = f"Communication error from {from_agent} to {to_agent}: {reason}"
        super().__init__(message, "AGENT_COMMUNICATION_ERROR", {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason
        })


class AgentTimeoutError(DomainError):
    """Raised when agent operation times out."""

    def __init__(self, agent_name: str, operation: str, timeout_seconds: int):
        message = f"Agent {agent_name} operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(message, "AGENT_TIMEOUT_ERROR", {
            "agent_name": agent_name,
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })


# Configuration Errors
class ConfigurationError(DomainError):
    """Raised when configuration is invalid."""

    def __init__(self, reason: str, config_key: str | None = None, config_value: Any | None = None):
        message = f"Configuration error: {reason}"
        if config_key:
            message += f" (key: {config_key})"
        super().__init__(message, "CONFIGURATION_ERROR", {
            "reason": reason,
            "config_key": config_key,
            "config_value": config_value
        })


class MissingConfigurationError(DomainError):
    """Raised when required configuration is missing."""

    def __init__(self, config_key: str, description: str | None = None):
        message = f"Missing required configuration: {config_key}"
        if description:
            message += f" ({description})"
        super().__init__(message, "MISSING_CONFIGURATION", {
            "config_key": config_key,
            "description": description
        })


# Validation Errors
class ValidationError(DomainError):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: Any, constraint: str):
        message = f"Validation error: {field} = {value} violates constraint: {constraint}"
        super().__init__(message, "VALIDATION_ERROR", {
            "field": field,
            "value": value,
            "constraint": constraint
        })


class InvalidCurrencyError(DomainError):
    """Raised when currency is invalid."""

    def __init__(self, currency: str, supported_currencies: list[str] | None = None):
        message = f"Invalid currency: {currency}"
        if supported_currencies:
            message += f". Supported: {', '.join(supported_currencies)}"
        super().__init__(message, "INVALID_CURRENCY", {
            "currency": currency,
            "supported_currencies": supported_currencies
        })


class InvalidPrecisionError(DomainError):
    """Raised when precision is invalid."""

    def __init__(self, value: float, precision: int, max_precision: int):
        message = f"Invalid precision: {value} has {precision} decimal places, max allowed: {max_precision}"
        super().__init__(message, "INVALID_PRECISION", {
            "value": value,
            "precision": precision,
            "max_precision": max_precision
        })
