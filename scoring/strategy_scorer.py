"""
Pure functions for technical analysis scoring.
Contains TA/ATR/RSI helpers and composite scoring glue.
"""

import numpy as np
import pandas as pd
import ta
from typing import Dict, List, Tuple

from domain.strategy import (
    MarketRegime, 
    SignalDecision, 
    TradingSignal,
    SupportResistanceLevels,
    IndicatorValues,
    DEFAULT_STRATEGY_PARAMS
)


def calculate_ema(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """Calculate Exponential Moving Averages."""
    if periods is None:
        periods = DEFAULT_STRATEGY_PARAMS.ema_periods
    
    result_df = df.copy()
    
    for period in periods:
        col_name = f'ema_{period}'
        result_df[col_name] = ta.trend.ema_indicator(
            close=df['close'],
            window=period
        )
    
    return result_df


def calculate_adx(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """Calculate Average Directional Index."""
    if period is None:
        period = DEFAULT_STRATEGY_PARAMS.adx_period
    
    result_df = df.copy()
    
    result_df['adx'] = ta.trend.adx(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=period
    )
    
    result_df['di_plus'] = ta.trend.adx_pos(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=period
    )
    
    result_df['di_minus'] = ta.trend.adx_neg(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=period
    )
    
    return result_df


def calculate_supertrend(df: pd.DataFrame, atr_period: int = None, factor: float = None) -> pd.DataFrame:
    """Calculate SuperTrend indicator manually."""
    if atr_period is None:
        atr_period = DEFAULT_STRATEGY_PARAMS.supertrend_atr_period
    if factor is None:
        factor = DEFAULT_STRATEGY_PARAMS.supertrend_factor
    
    result_df = df.copy()
    
    # Calculate ATR
    result_df['atr'] = ta.volatility.average_true_range(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=atr_period
    )
    
    # Calculate SuperTrend manually
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    atr = result_df['atr'].values
    
    # Initialize arrays
    supertrend = np.zeros(len(df))
    direction = np.zeros(len(df))
    
    # Calculate basic upper and lower bands
    basic_upper = (high + low) / 2 + factor * atr
    basic_lower = (high + low) / 2 - factor * atr
    
    # Initialize first values
    supertrend[0] = basic_lower[0]
    direction[0] = 1  # 1 for uptrend, -1 for downtrend
    
    # Calculate SuperTrend
    for i in range(1, len(df)):
        if direction[i-1] == 1:  # Previous trend was up
            if close[i] > basic_upper[i]:
                direction[i] = 1
                supertrend[i] = basic_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = basic_upper[i]
        else:  # Previous trend was down
            if close[i] < basic_lower[i]:
                direction[i] = -1
                supertrend[i] = basic_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = basic_lower[i]
    
    result_df['supertrend'] = supertrend
    result_df['supertrend_direction'] = direction
    
    return result_df


def calculate_macd(df: pd.DataFrame, fast: int = None, slow: int = None, signal: int = None) -> pd.DataFrame:
    """Calculate MACD indicator."""
    if fast is None:
        fast = DEFAULT_STRATEGY_PARAMS.macd_fast
    if slow is None:
        slow = DEFAULT_STRATEGY_PARAMS.macd_slow
    if signal is None:
        signal = DEFAULT_STRATEGY_PARAMS.macd_signal
    
    result_df = df.copy()
    
    result_df['macd'] = ta.trend.macd(
        close=df['close'],
        window_fast=fast,
        window_slow=slow
    )
    
    result_df['macd_signal'] = ta.trend.macd_signal(
        close=df['close'],
        window_fast=fast,
        window_slow=slow
    )
    
    result_df['macd_histogram'] = ta.trend.macd_diff(
        close=df['close'],
        window_fast=fast,
        window_slow=slow
    )
    
    return result_df


def calculate_rsi(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """Calculate RSI indicator."""
    if period is None:
        period = DEFAULT_STRATEGY_PARAMS.rsi_period
    
    result_df = df.copy()
    result_df['rsi'] = ta.momentum.rsi(close=df['close'], window=period)
    return result_df


def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """Calculate Average True Range."""
    if period is None:
        period = DEFAULT_STRATEGY_PARAMS.atr_period
    
    result_df = df.copy()
    result_df['atr'] = ta.volatility.average_true_range(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=period
    )
    return result_df


def calculate_bollinger_bands(df: pd.DataFrame, period: int = None, std_dev: float = None) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    if period is None:
        period = DEFAULT_STRATEGY_PARAMS.bollinger_period
    if std_dev is None:
        std_dev = DEFAULT_STRATEGY_PARAMS.bollinger_std_dev
    
    result_df = df.copy()
    
    bb = ta.volatility.BollingerBands(
        close=df['close'],
        window=period,
        window_dev=std_dev
    )
    
    result_df['bb_upper'] = bb.bollinger_hband()
    result_df['bb_middle'] = bb.bollinger_mavg()
    result_df['bb_lower'] = bb.bollinger_lband()
    
    return result_df


def find_swing_levels(df: pd.DataFrame, window: int = None, tolerance: float = None) -> Dict[str, List[float]]:
    """Find support and resistance levels using swing high/low analysis."""
    if window is None:
        window = DEFAULT_STRATEGY_PARAMS.swing_window
    if tolerance is None:
        tolerance = DEFAULT_STRATEGY_PARAMS.swing_tolerance
    
    highs = []
    lows = []
    
    for i in range(window, len(df) - window):
        # Check for swing high
        if all(df['high'].iloc[i] >= df['high'].iloc[i-window:i]) and \
           all(df['high'].iloc[i] >= df['high'].iloc[i+1:i+window+1]):
            highs.append(df['high'].iloc[i])
        
        # Check for swing low
        if all(df['low'].iloc[i] <= df['low'].iloc[i-window:i]) and \
           all(df['low'].iloc[i] <= df['low'].iloc[i+1:i+window+1]):
            lows.append(df['low'].iloc[i])
    
    # Cluster levels to avoid duplicates
    support_levels = _cluster_levels(lows, tolerance)
    resistance_levels = _cluster_levels(highs, tolerance)
    
    return {
        "support": support_levels,
        "resistance": resistance_levels
    }


def _cluster_levels(levels: List[float], tolerance: float) -> List[float]:
    """Cluster price levels to avoid duplicates."""
    if not levels:
        return []
    
    levels = sorted(levels)
    clustered = [levels[0]]
    
    for level in levels[1:]:
        if abs(level - clustered[-1]) / clustered[-1] > tolerance:
            clustered.append(level)
    
    return clustered


def calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate pivot points."""
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]
    close = df['close'].iloc[-1]
    
    pivot = (high + low + close) / 3
    
    return {
        "pivot": pivot,
        "r1": 2 * pivot - low,
        "r2": pivot + (high - low),
        "s1": 2 * pivot - high,
        "s2": pivot - (high - low)
    }


def _calculate_sma_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Simple Moving Averages."""
    result_df = df.copy()
    
    # SMA 20
    result_df['sma_20'] = df['close'].rolling(window=20).mean()
    
    # SMA 50
    result_df['sma_50'] = df['close'].rolling(window=50).mean()
    
    return result_df


def _calculate_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate volume-based indicators."""
    result_df = df.copy()
    
    # Volume SMA
    result_df['volume_sma'] = df['volume'].rolling(window=20).mean()
    
    # Volume ratio (current volume / average volume)
    result_df['volume_ratio'] = df['volume'] / result_df['volume_sma']
    
    return result_df


def _calculate_price_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price level indicators."""
    result_df = df.copy()
    
    # 20-period high and low
    result_df['high_20'] = df['high'].rolling(window=20).max()
    result_df['low_20'] = df['low'].rolling(window=20).min()
    
    # Current price (close)
    result_df['current_price'] = df['close']
    
    return result_df


def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = None) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels."""
    if lookback is None:
        lookback = DEFAULT_STRATEGY_PARAMS.fib_lookback
    
    if len(df) < lookback:
        return {}
    
    recent_data = df.tail(lookback)
    high = recent_data['high'].max()
    low = recent_data['low'].min()
    range_size = high - low
    
    return {
        "fib_0": low,
        "fib_236": low + 0.236 * range_size,
        "fib_382": low + 0.382 * range_size,
        "fib_500": low + 0.500 * range_size,
        "fib_618": low + 0.618 * range_size,
        "fib_786": low + 0.786 * range_size,
        "fib_100": high
    }


def detect_market_regime(df: pd.DataFrame) -> str:
    """Detect market regime based on technical indicators."""
    if len(df) < 50:
        return MarketRegime.SIDEWAYS.value
    
    # Get recent data
    recent = df.tail(20)
    
    # Check trend strength using ADX
    adx = recent['adx'].iloc[-1] if 'adx' in recent.columns else 0
    
    # Check EMA alignment
    ema_20 = recent['ema_20'].iloc[-1] if 'ema_20' in recent.columns else recent['close'].iloc[-1]
    ema_50 = recent['ema_50'].iloc[-1] if 'ema_50' in recent.columns else recent['close'].iloc[-1]
    ema_200 = recent['ema_200'].iloc[-1] if 'ema_200' in recent.columns else recent['close'].iloc[-1]
    
    # Check volatility using ATR
    atr = recent['atr'].iloc[-1] if 'atr' in recent.columns else 0
    avg_atr = recent['atr'].mean() if 'atr' in recent.columns else 0
    
    # Determine regime
    if adx > 25:  # Strong trend
        if ema_20 > ema_50 > ema_200:
            return MarketRegime.BULLISH_TREND.value
        elif ema_20 < ema_50 < ema_200:
            return MarketRegime.BEARISH_TREND.value
        else:
            return MarketRegime.SIDEWAYS.value
    elif atr > avg_atr * 1.5:  # High volatility
        return MarketRegime.VOLATILE.value
    else:
        return MarketRegime.SIDEWAYS.value


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators."""
    df = calculate_ema(df)
    df = calculate_adx(df)
    df = calculate_supertrend(df)
    df = calculate_macd(df)
    df = calculate_rsi(df)  # Fixed duplicate assignment
    df = calculate_atr(df)
    df = calculate_bollinger_bands(df)
    
    # Add missing indicators needed by ta_scorer
    df = _calculate_sma_indicators(df)
    df = _calculate_volume_indicators(df)
    df = _calculate_price_levels(df)
    
    return df


__all__ = [
    "calculate_ema",
    "calculate_adx", 
    "calculate_supertrend",
    "calculate_macd",
    "calculate_rsi",
    "calculate_atr",
    "calculate_bollinger_bands",
    "find_swing_levels",
    "calculate_pivot_points",
    "calculate_fibonacci_levels",
    "detect_market_regime",
    "calculate_all_indicators",
]
