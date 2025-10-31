"""
Canonical column names for technical indicators.
Single source of truth for indicator column naming across features and scoring.
"""

# Canonical indicator column names used across features and scoring
COL = {
    # Trend indicators
    "ADX": "adx",
    "EMA20": "ema_20", 
    "EMA50": "ema_50",
    "EMA200": "ema_200",
    
    # Momentum indicators
    "STOCH_K": "stoch_k",
    "STOCH_D": "stoch_d",
    
    # Volume indicators
    "VOLUME_RATIO": "volume_ratio",
    
    # Price levels
    "CURRENT_PRICE": "current_price",
    "HIGH_20": "high_20",
    "LOW_20": "low_20",
    
    # Moving averages
    "SMA_20": "sma_20",
    "SMA_50": "sma_50",
    
    # Volatility
    "ATR": "atr",
    "BB_UPPER": "bb_upper",
    "BB_MIDDLE": "bb_middle", 
    "BB_LOWER": "bb_lower",
    "BB_WIDTH": "bb_width",
    
    # Oscillators
    "RSI": "rsi",
    "MACD": "macd",
    "MACD_SIGNAL": "macd_signal",
    "MACD_HISTOGRAM": "macd_histogram",
    
    # Volume
    "VOLUME_SMA": "volume_sma"
}
