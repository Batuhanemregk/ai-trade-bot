# ML Feature Inventory

**Date**: 2025-10-31  
**Status**: Current Implementation  
**Total Features**: 23  

## Overview

This document inventories all ML features currently used in the LightGBM model (`models/lgb_v1.pkl`). Features are extracted from:
- Code: `ml/feature_engineering.py`
- Model metadata: `models/lgb_v1_version.json`

## Feature List (Alphabetical)

| Feature Name | Category | Source | Description |
|--------------|----------|--------|-------------|
| atr_pct | TA | Code + Model | Average True Range as percentage of close price |
| bb_pos | TA | Code + Model | Bollinger Band position (close relative to bands) |
| dow_cos | Time | Code + Model | Day of week (cyclic cosine encoding) |
| dow_sin | Time | Code + Model | Day of week (cyclic sine encoding) |
| hour_cos | Time | Code + Model | Hour of day (cyclic cosine encoding) |
| hour_sin | Time | Code + Model | Hour of day (cyclic sine encoding) |
| macd_hist | TA | Code + Model | MACD histogram (signal - line) |
| price_momentum_20 | Regime | Code + Model | 20-bar price momentum (pct change) |
| price_momentum_5 | Regime | Code + Model | 5-bar price momentum (pct change) |
| ret_1 | Returns | Code + Model | 1-bar return percentage |
| ret_16 | Returns | Code + Model | 16-bar return percentage |
| ret_4 | Returns | Code + Model | 4-bar return percentage |
| rsi_14 | TA | Code + Model | Relative Strength Index (14 periods) |
| sma_diff | Trend | Code + Model | SMA20-SMA50 difference as percentage |
| sma_ratio | Trend | Code + Model | SMA20/SMA50 ratio |
| timeframe | Meta | Model | Timeframe indicator (categorical) |
| trend_strength | Regime | Code + Model | Trend strength measurement |
| volatility_20 | Regime | Code + Model | 20-bar rolling volatility (std) |
| volatility_regime | Regime | Code + Model | Volatility regime flag (binary) |
| volume_momentum | Volume | Code + Model | 5-bar volume momentum |
| volume_sma_20 | Volume | Code + Model | 20-bar volume SMA |
| volume_sma_ratio | Volume | Code + Model | Current volume / volume_sma_20 |
| volume_volatility | Volume | Code + Model | 10-bar volume volatility (std) |

## Feature Grouping

### Technical Analysis (5 features)
1. `rsi_14` - RSI indicator
2. `macd_hist` - MACD histogram
3. `atr_pct` - ATR percentage
4. `bb_pos` - Bollinger Band position

**Note**: These are the core TA features. The expanded feature set will add 15+ additional TA indicators.

### Returns (3 features)
1. `ret_1` - 1-bar return
2. `ret_4` - 4-bar return
3. `ret_16` - 16-bar return

### Trend (2 features)
1. `sma_diff` - SMA20-SMA50 difference
2. `sma_ratio` - SMA20/SMA50 ratio

### Time Features (4 features)
1. `hour_sin` - Hour sine encoding
2. `hour_cos` - Hour cosine encoding
3. `dow_sin` - Day of week sine encoding
4. `dow_cos` - Day of week cosine encoding

### Volume (4 features)
1. `volume_sma_20` - Volume SMA
2. `volume_sma_ratio` - Volume ratio
3. `volume_momentum` - Volume momentum
4. `volume_volatility` - Volume volatility

### Market Regime (4 features)
1. `price_momentum_5` - Short-term momentum
2. `price_momentum_20` - Medium-term momentum
3. `volatility_20` - Volatility measure
4. `volatility_regime` - Regime flag
5. `trend_strength` - Trend strength

### Metadata (1 feature)
1. `timeframe` - Timeframe indicator (categorical)

**Total by Category**: TA (5) + Returns (3) + Trend (2) + Time (4) + Volume (4) + Regime (5) + Meta (1) = 23

## Implementation Details

### Source Code
- **Location**: `ml/feature_engineering.py`
- **Class**: `FeatureEngineer`
- **Methods**:
  - `_add_ta_features()` - Lines 73-106
  - `_add_return_features()` - Lines 108-116
  - `_add_trend_features()` - Lines 118-129
  - `_add_time_features()` - Lines 131-144
  - `_add_volume_features()` - Lines 217-229
  - `_add_regime_features()` - Lines 231-244

### Model Artifacts
- **Model**: `models/lgb_v1.pkl`
- **Metadata**: `models/lgb_v1_version.json`
- **Training Period**: 2025-04-27 to 2025-10-24 (6 months)
- **Symbols**: BTC/USDT, ETH/USDT, SOL/USDT
- **Performance**: AUC = 0.973, Accuracy = 0.891

## Feature Engineering Notes

### No Look-Ahead Leakage
All features are calculated using only historical data available at bar close:
- Rolling windows use `.shift()` where necessary
- `pct_change()` is backward-looking
- EMA calculations use `adjust=False` for consistency

### Data Cleaning
Features undergo the following cleaning steps:
1. Replace inf with NaN
2. Forward fill NaN
3. Backward fill remaining NaN
4. Fill any remaining NaN with 0

### Labeling Strategy
Current labels use binary classification:
- Label = 1 if `close_{t+1} > close_t`
- Label = 0 otherwise
- Forward bars: 1 (next bar)

**Note**: Expanded implementation will use threshold-based labels (forward_bars=3, threshold=0.25%).

## Missing/To-Be-Added Features

Based on requirements, the following features are NOT yet implemented:

### Additional TA Indicators (15+ features)
- SMA: 5, 10 periods
- EMA: 12, 26 periods
- Stochastic: %K, %D
- Williams%R
- ADX, +DI, -DI
- BB upper, BB lower, BB width, BB %b
- OBV
- MFI

### Price Action Features (14+ features)
- Body ratio, wick ratios
- Heikin-Ashi OHLC
- Pattern flags (engulfing, pinbar)
- HH/HL/LH/LL patterns

### Statistics Features (7+ features)
- Log returns
- Rolling means (5, 10 periods)
- Rolling std (5, 10 periods)
- Skewness, kurtosis

### Multi-Timeframe Features (6+ features)
- RSI, MACD, trend from 1h and 4h timeframes

## Next Steps

1. Expand feature set from 23 → 50+ features
2. Implement multi-timeframe feature integration
3. Add threshold-based labeling
4. Train separate models per symbol-TF combination

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-31

