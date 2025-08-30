"""
Domain entities for trading strategy.
Contains data models, enums, and configuration types.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class MarketRegime(Enum):
    """Market regime enumeration."""
    BULLISH_TREND = "bullish_trend"
    BEARISH_TREND = "bearish_trend"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


class SignalDecision(Enum):
    """Signal decision enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class TradingSignal:
    """Trading signal data model."""
    decision: str
    confidence: float
    context: Dict[str, Any]
    ta_score: Optional[float] = None
    news_score: Optional[float] = None
    final_score: Optional[float] = None
    usage: Optional[Dict[str, Any]] = None


@dataclass
class StrategyParams:
    """Strategy parameters data model."""
    ema_periods: List[int]
    adx_period: int
    supertrend_atr_period: int
    supertrend_factor: float
    macd_fast: int
    macd_slow: int
    macd_signal: int
    rsi_period: int
    atr_period: int
    bollinger_period: int
    bollinger_std_dev: float
    swing_window: int
    swing_tolerance: float
    fib_lookback: int


@dataclass
class SupportResistanceLevels:
    """Support and resistance levels data model."""
    support: List[float]
    resistance: List[float]
    pivot_points: Dict[str, float]
    fibonacci_levels: Dict[str, float]


@dataclass
class IndicatorValues:
    """Current indicator values data model."""
    current_price: float
    ema_20: float
    ema_50: float
    ema_200: float
    adx: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    atr: float


# Default strategy parameters
DEFAULT_STRATEGY_PARAMS = StrategyParams(
    ema_periods=[20, 50, 200],
    adx_period=14,
    supertrend_atr_period=10,
    supertrend_factor=3.0,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    rsi_period=14,
    atr_period=14,
    bollinger_period=20,
    bollinger_std_dev=2.0,
    swing_window=20,
    swing_tolerance=0.02,
    fib_lookback=50
)


__all__ = [
    "MarketRegime",
    "SignalDecision", 
    "TradingSignal",
    "StrategyParams",
    "SupportResistanceLevels",
    "IndicatorValues",
    "DEFAULT_STRATEGY_PARAMS",
]
