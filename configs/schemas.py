"""
Pydantic Models for Configuration Validation
Follows SOLID principles with type-safe configuration
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ExchangeMode(str, Enum):
    """Exchange mode enumeration."""
    LIVE = "live"
    DRY_RUN = "dry-run"


class ExchangeName(str, Enum):
    """Supported exchanges."""
    OKX = "okx"


class SymbolsConfig(BaseModel):
    """Symbol configuration."""
    default_quote: str = "USDT"
    supported_pairs: List[str] = Field(min_length=1)
    trading_pairs: List[str] = Field(min_length=1)
    
    @field_validator('trading_pairs')
    @classmethod
    def validate_trading_pairs(cls, v):
        """Validate trading pairs format."""
        for pair in v:
            if '-' not in pair:
                raise ValueError(f"Invalid trading pair format: {pair}")
        return v


class ExchangeConfig(BaseModel):
    """Exchange configuration with validation."""
    name: ExchangeName
    mode: ExchangeMode
    testnet: bool = False
    sandbox: bool = False
    symbols: SymbolsConfig
    
    @model_validator(mode='after')
    def validate_mode_consistency(self):
        """Ensure mode consistency with testnet/sandbox."""
        if self.mode == ExchangeMode.LIVE and (self.testnet or self.sandbox):
            raise ValueError("Cannot use live mode with testnet or sandbox enabled")
        return self


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_position_size: float = Field(ge=0.01, le=0.5, description="Max position size (1%-50%)")
    max_leverage: float = Field(ge=1.0, le=10.0, description="Max leverage (1x-10x)")
    stop_loss_pct: float = Field(ge=0.005, le=0.1, description="Stop loss % (0.5%-10%)")
    take_profit_pct: float = Field(ge=0.01, le=0.2, description="Take profit % (1%-20%)")
    max_drawdown: float = Field(ge=0.05, le=0.5, description="Max drawdown (5%-50%)")
    
    @field_validator('take_profit_pct')
    @classmethod
    def tp_greater_than_sl(cls, v, info):
        """Ensure TP > SL."""
        if 'stop_loss_pct' in info.data and v <= info.data['stop_loss_pct']:
            raise ValueError("take_profit_pct must be greater than stop_loss_pct")
        return v


class ScoringWeights(BaseModel):
    """Scoring weights configuration."""
    ta_weight: float = Field(ge=0.0, le=1.0, description="TA weight")
    ml_weight: float = Field(ge=0.0, le=1.0, description="ML weight")
    news_weight: float = Field(ge=0.0, le=1.0, description="News weight")
    risk_weight: float = Field(ge=0.0, le=1.0, description="Risk weight")
    min_composite_score: float = Field(ge=0.0, le=1.0, description="Min score threshold")
    
    @model_validator(mode='after')
    def weights_sum_to_one(self):
        """Ensure weights sum to approximately 1.0."""
        total = self.ta_weight + self.ml_weight + self.news_weight + self.risk_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Scoring weights must sum to 1.0 (±0.01), got {total:.3f}. "
                f"Adjust weights: ta={self.ta_weight}, ml={self.ml_weight}, "
                f"news={self.news_weight}, risk={self.risk_weight}"
            )
        return self


class DecisionThresholds(BaseModel):
    """Decision threshold configuration."""
    enter_long: float = Field(ge=50, le=100, description="Long entry threshold")
    exit_long: float = Field(ge=0, le=50, description="Long exit threshold")
    enter_short: float = Field(ge=0, le=50, description="Short entry threshold")
    exit_short: float = Field(ge=50, le=100, description="Short exit threshold")
    flat_range: List[float] = Field(min_length=2, max_length=2)
    
    @field_validator('flat_range')
    @classmethod
    def validate_flat_range(cls, v):
        """Ensure flat range is valid."""
        if v[0] >= v[1]:
            raise ValueError(f"Flat range invalid: [{v[0]}, {v[1]}] - min must be < max")
        if v[0] < 0 or v[1] > 100:
            raise ValueError(f"Flat range must be 0-100: [{v[0]}, {v[1]}]")
        return v


class ScoringConfig(BaseModel):
    """Scoring configuration."""
    ta_weight: float
    ml_weight: float
    news_weight: float
    risk_weight: float
    min_composite_score: float
    decision_thresholds: DecisionThresholds
    
    @model_validator(mode='after')
    def validate_weights(self):
        """Validate weight sum."""
        total = self.ta_weight + self.ml_weight + self.news_weight + self.risk_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")
        return self


class TradingConfig(BaseModel):
    """Trading configuration."""
    risk: RiskConfig
    scoring: ScoringConfig


class RetryConfig(BaseModel):
    """Retry configuration."""
    attempts: int = Field(ge=1, le=5, description="Retry attempts (1-5)")
    backoff_seconds: List[int] = Field(min_length=1)
    
    @field_validator('backoff_seconds')
    @classmethod
    def validate_backoff(cls, v):
        """Ensure backoff values are reasonable."""
        for i, val in enumerate(v):
            if val < 1 or val > 300:
                raise ValueError(f"Backoff value {i} ({val}s) must be 1-300 seconds")
        return v


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    semaphore_limit: int = Field(ge=1, le=10, description="Max concurrent jobs (1-10)")
    retry: RetryConfig
    
    @field_validator('semaphore_limit')
    @classmethod
    def validate_semaphore(cls, v):
        """Validate semaphore limit."""
        if v < 1:
            raise ValueError("semaphore_limit must be at least 1")
        if v > 10:
            raise ValueError("semaphore_limit should not exceed 10 (risk of overload)")
        return v


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""
    enabled: bool
    token: Optional[str] = None
    chat_id: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_telegram(self):
        """Ensure token/chat_id provided when enabled."""
        if self.enabled:
            # Allow environment variable placeholders like ${TELEGRAM_BOT_TOKEN}
            # These will be expanded at runtime by bootstrap.py
            if not self.token:
                raise ValueError("Telegram enabled but token not configured")
            if not self.chat_id:
                raise ValueError("Telegram enabled but chat_id not configured")
        return self


class ScheduleConfig(BaseModel):
    """Schedule cron expressions."""
    trading_15m: str = Field(pattern=r'^[\*/0-9 ]+$')
    trailing_5m: str = Field(pattern=r'^[\*/0-9 ]+$')
    regime_1h: str = Field(pattern=r'^[\*/0-9 ]+$')
    risk_1m: str = Field(pattern=r'^[\*/0-9 ]+$')
    market_overview: Optional[str] = Field(None, pattern=r'^[\*/0-9 ]+$')
    telegram_summary_15m: Optional[str] = Field(None, pattern=r'^[\*/0-9 ]+$')


class IdempotencyConfig(BaseModel):
    """Idempotency configuration."""
    persist_path: str
    cleanup_interval_hours: int = Field(ge=1, le=168, description="Cleanup interval (1-168 hours)")


class PolicyConfig(BaseModel):
    """Main policy configuration model."""
    schedule: ScheduleConfig
    scheduler: SchedulerConfig
    idempotency: IdempotencyConfig
    exchange: ExchangeConfig
    trading: TradingConfig
    telegram: TelegramConfig
    
    @model_validator(mode='after')
    def validate_policy(self):
        """Cross-field validation."""
        # Ensure risk limits are reasonable
        if self.trading.risk.max_position_size > 0.2:
            raise ValueError(
                f"max_position_size too high ({self.trading.risk.max_position_size:.1%}). "
                "Consider values ≤20% for safety."
            )
        
        return self


def validate_policy_dict(policy: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate policy dictionary against Pydantic model.
    
    Args:
        policy: Policy dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        PolicyConfig(**policy)
        return True, None
    except Exception as e:
        return False, str(e)


def get_validation_errors(policy: Dict) -> List[str]:
    """
    Get list of validation errors.
    
    Args:
        policy: Policy dictionary
        
    Returns:
        List of error messages (empty if valid)
    """
    try:
        PolicyConfig(**policy)
        return []
    except Exception as e:
        # Parse Pydantic validation errors
        errors = []
        if hasattr(e, 'errors'):
            for error in e.errors():
                loc = ' -> '.join(str(l) for l in error['loc'])
                msg = error['msg']
                errors.append(f"{loc}: {msg}")
        else:
            errors.append(str(e))
        return errors

