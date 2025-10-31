# ML Feature Specification

**Date**: 2025-10-31  
**Version**: 2.0 (Expanded Feature Set)  
**Implementation**: `ml/features/builder.py`

## Overview

This document provides detailed specifications for all ML features used in LightGBM model training and inference. The expanded feature set contains **60+ features** across 6 categories.

## No Look-Ahead Guarantee

**CRITICAL**: All features are calculated using only information available at bar close time. No future information leaks into feature values.

### Guarantee Mechanisms

1. **Rolling Window**: All rolling calculations use `.shift(1)` internally or operate on historical data only
2. **Lag Operations**: Features like `pct_change()` and `diff()` are inherently backward-looking
3. **Multi-Timeframe Join**: Uses `asof` merge with forward-fill (fills within gaps but never uses future data)
4. **Label Separation**: Labels are created separately after features, using `shift(-forward_bars)` only in label creation

### Verification

Every feature calculation can be verified as using only:
- Current bar: `close[t]`, `high[t]`, `low[t]`, `volume[t]`
- Historical bars: `close[t-1, t-2, ...]`
- Never uses: `close[t+1]`, `high[t+1]`, etc.

## Feature Categories

### 1. Technical Analysis Indicators (28 features)

#### Moving Averages (6 features)

**SMA Features:**
- `sma_5`: Simple Moving Average (5 periods)
  - Formula: `SMA(5) = (close[t] + close[t-1] + ... + close[t-4]) / 5`
  
- `sma_10`: Simple Moving Average (10 periods)
  - Formula: `SMA(10) = (close[t] + close[t-1] + ... + close[t-9]) / 10`
  
- `sma_20`: Simple Moving Average (20 periods)
  - Formula: `SMA(20) = (close[t] + close[t-1] + ... + close[t-19]) / 20`
  
- `sma_50`: Simple Moving Average (50 periods)
  - Formula: `SMA(50) = (close[t] + close[t-1] + ... + close[t-49]) / 50`

**EMA Features:**
- `ema_12`: Exponential Moving Average (12 periods)
  - Formula: `EMA(12) = close[t] * α + EMA[t-1] * (1-α)`, where `α = 2/(12+1)`
  
- `ema_26`: Exponential Moving Average (26 periods)
  - Formula: `EMA(26) = close[t] * α + EMA[t-1] * (1-α)`, where `α = 2/(26+1)`

#### MACD Features (3 features)

- `macd_line`: MACD Line
  - Formula: `EMA(12) - EMA(26)`
  
- `macd_signal`: Signal Line
  - Formula: `EMA(9) of macd_line`
  
- `macd_hist`: MACD Histogram
  - Formula: `macd_line - macd_signal`

#### RSI (1 feature)

- `rsi_14`: Relative Strength Index (14 periods)
  - Formula: `RSI = 100 - (100 / (1 + RS))`
  - Where `RS = avg_gain / avg_loss` over 14 periods

#### Stochastic Oscillator (2 features)

- `stoch_k`: Stochastic %K (14, 3)
  - Formula: `%K = 100 * (close - min_low_14) / (max_high_14 - min_low_14)`
  
- `stoch_d`: Stochastic %D (14, 3)
  - Formula: `%D = SMA(3) of %K`

#### Williams%R (1 feature)

- `williams_r`: Williams %R (14 periods)
  - Formula: `%R = -100 * (max_high_14 - close) / (max_high_14 - min_low_14)`

#### ADX, +DI, -DI (3 features)

- `plus_di`: +Directional Indicator (14 periods)
  - Formula: `+DI = 100 * (+DM_smooth / ATR)`
  
- `minus_di`: -Directional Indicator (14 periods)
  - Formula: `-DI = 100 * (-DM_smooth / ATR)`
  
- `adx`: Average Directional Index (14 periods)
  - Formula: `ADX = SMA(14) of DX`, where `DX = 100 * |+DI - -DI| / (+DI + -DI)`

#### ATR (2 features)

- `atr_14`: Average True Range (14 periods)
  - Formula: `ATR = SMA(14) of TR`
  - Where `TR = max(high-low, |high - close[t-1]|, |low - close[t-1]|)`
  
- `atr_pct`: ATR as Percentage of Close
  - Formula: `atr_14 / close * 100`

#### Bollinger Bands (5 features)

- `bb_upper`: Upper Bollinger Band
  - Formula: `SMA(20) + 2 * STD(20)`
  
- `bb_lower`: Lower Bollinger Band
  - Formula: `SMA(20) - 2 * STD(20)`
  
- `bb_width`: Bollinger Band Width
  - Formula: `(bb_upper - bb_lower) / SMA(20)`
  
- `bb_pos`: Bollinger Band Position
  - Formula: `(close - SMA(20)) / (2 * STD(20))`
  
- `bb_pctb`: Bollinger Band %b
  - Formula: `(close - bb_lower) / (bb_upper - bb_lower)`

#### OBV (1 feature)

- `obv`: On Balance Volume
  - Formula: `OBV[t] = OBV[t-1] + sign(close[t] - close[t-1]) * volume[t]`
  - Where `sign(x) = 1 if x > 0, -1 if x < 0, 0 if x = 0`

#### MFI (1 feature)

- `mfi`: Money Flow Index (14 periods)
  - Formula: `MFI = 100 - (100 / (1 + Money_Ratio))`
  - Where `Money_Ratio = Positive_MF / Negative_MF`
  - And `MF = Typical_Price * volume`

### 2. Price Action Features (18 features)

#### Body and Wick Ratios (4 features)

- `body`: Candle Body
  - Formula: `close - open`
  
- `body_ratio`: Body to Range Ratio
  - Formula: `body / (high - low)`
  
- `upper_wick_ratio`: Upper Wick Ratio
  - Formula: `(high - max(open, close)) / (high - low)`
  
- `lower_wick_ratio`: Lower Wick Ratio
  - Formula: `(min(open, close) - low) / (high - low)`

#### Heikin-Ashi Features (4 features)

- `ha_open`: Heikin-Ashi Open
  - Formula: `HA_open[t] = (HA_open[t-1] + HA_close[t-1]) / 2`
  - With `HA_open[0] = (open[0] + close[0]) / 2`
  
- `ha_close`: Heikin-Ashi Close
  - Formula: `(open + high + low + close) / 4`
  
- `ha_high`: Heikin-Ashi High
  - Formula: `max(high, ha_open, ha_close)`
  
- `ha_low`: Heikin-Ashi Low
  - Formula: `min(low, ha_open, ha_close)`

#### Pattern Flags (4 features)

- `engulfing_bull`: Bullish Engulfing Pattern
  - Formula: `bool(prev_body < 0 AND body > 0 AND open < prev_close AND close > prev_open)`
  
- `engulfing_bear`: Bearish Engulfing Pattern
  - Formula: `bool(prev_body > 0 AND body < 0 AND open > prev_close AND close < prev_open)`
  
- `pinbar_up`: Bullish Pinbar
  - Formula: `bool(lower_wick_ratio > 0.66 AND upper_wick_ratio < 0.33)`
  
- `pinbar_down`: Bearish Pinbar
  - Formula: `bool(upper_wick_ratio > 0.66 AND lower_wick_ratio < 0.33)`

#### HH/HL/LH/LL Patterns (4 features)

- `hh`: Higher High
  - Formula: `bool(high > max(high[t-1] ... high[t-5]))`
  
- `hl`: Higher Low
  - Formula: `bool(low > min(low[t-1] ... low[t-5]))`
  
- `lh`: Lower High
  - Formula: `bool(high < max(high[t-1] ... high[t-5]))`
  
- `ll`: Lower Low
  - Formula: `bool(low < min(low[t-1] ... low[t-5]))`

### 3. Statistics Features (11 features)

#### Log Returns (3 features)

- `log_ret_1`: 1-Bar Log Return
  - Formula: `log(close[t] / close[t-1])`
  
- `log_ret_3`: 3-Bar Log Return
  - Formula: `log(close[t] / close[t-3])`
  
- `log_ret_5`: 5-Bar Log Return
  - Formula: `log(close[t] / close[t-5])`

#### Rolling Mean (3 features)

- `roll_mean_5`: 5-Period Rolling Mean
  - Formula: `SMA(5) of close`
  
- `roll_mean_10`: 10-Period Rolling Mean
  - Formula: `SMA(10) of close`
  
- `roll_mean_20`: 20-Period Rolling Mean
  - Formula: `SMA(20) of close`

#### Rolling Std (3 features)

- `roll_std_5`: 5-Period Rolling Std
  - Formula: `STD(5) of close`
  
- `roll_std_10`: 10-Period Rolling Std
  - Formula: `STD(10) of close`
  
- `roll_std_20`: 20-Period Rolling Std
  - Formula: `STD(20) of close`

#### Skewness and Kurtosis (2 features)

- `skewness_20`: 20-Period Rolling Skewness
  - Formula: `E[(x - μ)^3] / σ^3` over 20 periods
  
- `kurtosis_20`: 20-Period Rolling Kurtosis
  - Formula: `E[(x - μ)^4] / σ^4` over 20 periods

### 4. Time Features (4 features)

#### Hour Encoding (2 features)

- `hour_sin`: Hour Sine Encoding
  - Formula: `sin(2π * hour / 24)`
  
- `hour_cos`: Hour Cosine Encoding
  - Formula: `cos(2π * hour / 24)`

#### Day of Week Encoding (2 features)

- `dow_sin`: Day of Week Sine Encoding
  - Formula: `sin(2π * dow / 7)`
  
- `dow_cos`: Day of Week Cosine Encoding
  - Formula: `cos(2π * dow / 7)`

### 5. Volume Features (6 features)

- `volume_sma_20`: Volume SMA
  - Formula: `SMA(20) of volume`
  
- `volume_sma_ratio`: Volume to SMA Ratio
  - Formula: `volume / volume_sma_20`
  
- `volume_ema_20`: Volume EMA
  - Formula: `EMA(20) of volume`
  
- `volume_ema_ratio`: Volume to EMA Ratio
  - Formula: `volume / volume_ema_20`
  
- `volume_momentum`: Volume Momentum
  - Formula: `(volume - volume[t-5]) / volume[t-5]`
  
- `volume_volatility`: Volume Volatility
  - Formula: `STD(10) of volume`

### 6. Multi-Timeframe Features (6 features)

Multi-timeframe features are calculated from higher timeframes (1h, 4h) and merged using **asof** join (no look-ahead).

#### From 1h Timeframe (3 features)

- `rsi_14_1h`: RSI from 1h
  - Calculated on 1h bars, merged to current TF
  
- `macd_hist_1h`: MACD Histogram from 1h
  - Calculated on 1h bars, merged to current TF
  
- `trend_strength_1h`: Trend Strength from 1h
  - Formula: `|SMA20_1h - SMA50_1h| / close_1h`

#### From 4h Timeframe (3 features)

- `rsi_14_4h`: RSI from 4h
  - Calculated on 4h bars, merged to current TF
  
- `macd_hist_4h`: MACD Histogram from 4h
  - Calculated on 4h bars, merged to current TF
  
- `trend_strength_4h`: Trend Strength from 4h
  - Formula: `|SMA20_4h - SMA50_4h| / close_4h`

#### Multi-Timeframe Merge Logic

**CRITICAL**: No look-ahead leakage in MTF join.

1. Calculate features on higher timeframe bars (e.g., 1h bars)
2. Use `asof` merge: for each current TF bar, find the last MTF bar that closed before it
3. Forward-fill within gaps (same MTF bar value for multiple current TF bars)
4. Never use future MTF data

Example for 15m main / 1h MTF:
- 15m bar at 10:15:00 → uses 1h bar at 10:00:00 (last 1h bar)
- 15m bar at 10:30:00 → uses 1h bar at 10:00:00 (still last 1h bar)
- 15m bar at 11:00:00 → uses 1h bar at 11:00:00 (new 1h bar)

## Label Specification

### Threshold-Based Binary Classification

- **Label**: Binary (0 or 1)
- **Forward Bars**: 3
- **Threshold**: 0.25% return

**Formula**:
```
future_return = ((close[t+3] - close[t]) / close[t]) * 100
label = 1 if future_return > 0.25 else 0
```

**No Look-Ahead**: Labels are created after features using `shift(-forward_bars)`, and the last N rows are dropped.

## Data Cleaning

### NaN and Inf Handling

1. Replace `inf` and `-inf` with `NaN`
2. Forward-fill `NaN` using previous valid value
3. Backward-fill remaining `NaN` (first rows)
4. Fill any still-remaining `NaN` with 0

**Rationale**: 
- Forward-fill: Use last known value if feature calculation not yet ready
- Backward-fill: Avoid dropping initial rows
- Zero-fill: Provide neutral value as last resort

## Feature Count Summary

| Category | Count | Features |
|----------|-------|----------|
| TA Indicators | 28 | SMA/EMA/MACD/RSI/Stoch/Williams/ADX/ATR/BB/OBV/MFI |
| Price Action | 18 | Body/wick ratios, Heikin-Ashi, patterns, HH/HL/LH/LL |
| Statistics | 11 | Log returns, rolling means, stds, skewness, kurtosis |
| Time | 4 | Hour/day cyclical encoding |
| Volume | 6 | Volume SMA/EMA/ratios, momentum, volatility |
| Multi-TF | 6 | RSI/MACD/Trend from 1h and 4h |
| **TOTAL** | **73** | |

**Note**: Actual feature count may vary based on multi-TF availability (73 if both 1h and 4h provided, 67 if only one, 67 if none).

## Testing Requirements

### No Look-Ahead Tests

1. **Feature Consistency**: Verify features for bar[t] don't change after bar[t+1] arrives
2. **MTF Join**: Verify asof merge uses only past MTF data
3. **Label Separation**: Verify labels use `shift(-forward_bars)` only in label creation
4. **Rolling Windows**: Verify all rolling windows are backward-looking

### Feature Completeness Tests

1. Verify all 73 features are present when MTF data provided
2. Verify 67 features present when MTF data not provided
3. Verify no duplicate feature names
4. Verify all features are numeric

### Data Quality Tests

1. No `inf` or `-inf` in final features
2. No `NaN` in final features
3. Feature distributions are reasonable
4. No extreme outliers (capped or logged where appropriate)

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-31

