# ML Feature Specification

**Date**: 2025-11-01  
**Purpose**: Complete specification of ML features for LightGBM models  
**No Look-Ahead**: All features computed from current and historical data only

---

## Overview

**Total Features**: 68-74 (depends on MTF availability)  
**Source**: `ml/features/builder.py`  
**Training**: `ml/training/train_lgbm_per_symbol_tf.py`  
**Usage**: Binary classification (price up/down prediction)

---

## Category 1: Technical Analysis Indicators (29 features)

### Moving Averages (6 features)

#### SMA - Simple Moving Average
- **Features**: `sma_5`, `sma_10`, `sma_20`, `sma_50`
- **Formula**: `SMA(n) = sum(close[t:n]) / n`
- **Parameters**: Periods [5, 10, 20, 50]
- **Use**: Trend identification, support/resistance

#### EMA - Exponential Moving Average
- **Features**: `ema_12`, `ema_26`
- **Formula**: `EMA(n) = alpha * close + (1 - alpha) * EMA_prev`
- **Parameters**: Spans [12, 26] (for MACD)
- **Use**: Trend identification, faster signal than SMA

### MACD - Moving Average Convergence Divergence (3 features)

- **Features**: `macd_line`, `macd_signal`, `macd_hist`
- **Formula**:
  - MACD Line = EMA(12) - EMA(26)
  - Signal = EMA(9) of MACD Line
  - Histogram = MACD Line - Signal
- **Parameters**: (12, 26, 9)
- **Use**: Momentum, trend changes

### RSI - Relative Strength Index (1 feature)

- **Feature**: `rsi_14`
- **Formula**:
  - Gain = avg of positive price changes
  - Loss = avg of negative price changes
  - RS = Gain / Loss
  - RSI = 100 - (100 / (1 + RS))
- **Parameters**: Period 14
- **Use**: Overbought/oversold conditions
- **Range**: 0-100

### Stochastic Oscillator (2 features)

- **Features**: `stoch_k`, `stoch_d`
- **Formula**:
  - %K = 100 * (close - low_min) / (high_max - low_min)
  - %D = 3-period SMA of %K
- **Parameters**: Period 14, smooth 3
- **Use**: Momentum, overbought/oversold
- **Range**: 0-100

### Williams %R (1 feature)

- **Feature**: `williams_r`
- **Formula**: `-100 * (high_max - close) / (high_max - low_min)`
- **Parameters**: Period 14
- **Use**: Momentum
- **Range**: -100 to 0

### ADX System (3 features)

- **Features**: `adx`, `plus_di`, `minus_di`
- **Formula**:
  - True Range = max(high-low, |high-close_prev|, |low-close_prev|)
  - ATR = 14-period SMA of TR
  - +DI = 100 * (SMA of +DM) / ATR
  - -DI = 100 * (SMA of -DM) / ATR
  - DX = 100 * |+DI - -DI| / (+DI + -DI)
  - ADX = 14-period SMA of DX
- **Parameters**: Period 14
- **Use**: Trend strength and direction
- **Range**: ADX 0-100, +/-DI 0-100

### ATR - Average True Range (2 features)

- **Features**: `atr_14`, `atr_pct`
- **Formula**:
  - ATR(14) = 14-period SMA of True Range
  - ATR% = (ATR / close) * 100
- **Parameters**: Period 14
- **Use**: Volatility measurement

### Bollinger Bands (5 features)

- **Features**: `bb_upper`, `bb_lower`, `bb_width`, `bb_pos`, `bb_pctb`
- **Formula**:
  - Middle = SMA(20)
  - Upper = Middle + 2*STD(20)
  - Lower = Middle - 2*STD(20)
  - Width = (Upper - Lower) / Middle
  - Position = (close - Middle) / (2*STD)
  - %B = (close - Lower) / (Upper - Lower)
- **Parameters**: Period 20, std 2
- **Use**: Volatility, mean reversion

### Volume Indicators (2 features)

#### OBV - On-Balance Volume
- **Feature**: `obv`
- **Formula**: Cumulative sum of volume * sign(price_change)
- **Use**: Volume trend confirmation

#### MFI - Money Flow Index
- **Feature**: `mfi`
- **Formula**: `100 - (100 / (1 + Money_Ratio))`
- **Parameters**: Period 14
- **Use**: Volume-weighted RSI
- **Range**: 0-100

---

## Category 2: Price Action Features (16 features)

### Candlestick Structure (4 features)

- **Features**: `body`, `body_ratio`, `upper_wick_ratio`, `lower_wick_ratio`
- **Formula**:
  - Body = close - open
  - Range = high - low
  - Body Ratio = body / range
  - Upper Wick = (high - max(open, close)) / range
  - Lower Wick = (min(open, close) - low) / range
- **Use**: Candlestick pattern recognition

### Heikin-Ashi OHLC (4 features)

- **Features**: `ha_open`, `ha_high`, `ha_low`, `ha_close`
- **Formula**:
  - HA Close = (open + high + low + close) / 4
  - HA Open = (HA_open_prev + HA_close_prev) / 2
  - HA High = max(high, HA_open, HA_close)
  - HA Low = min(low, HA_open, HA_close)
- **Use**: Trend smoothing, noise reduction

### Pattern Flags (8 features, binary 0/1)

#### Engulfing Patterns
- `engulfing_bull`: Bullish engulfing detected
- `engulfing_bear`: Bearish engulfing detected

#### Pinbar Patterns
- `pinbar_up`: Long lower wick (>66%), short upper wick (<33%)
- `pinbar_down`: Long upper wick (>66%), short lower wick (<33%)

#### Swing Patterns
- `hh`: Higher High (current high > previous 5 highs max)
- `hl`: Higher Low (current low > previous 5 lows min)
- `lh`: Lower High (current high < previous 5 highs max)
- `ll`: Lower Low (current low < previous 5 lows min)

**Parameters**: N=5 bars lookback for swing patterns

---

## Category 3: Statistical Features (16 features)

### Log Returns (3 features)

- **Features**: `log_ret_1`, `log_ret_3`, `log_ret_5`
- **Formula**: `log(close_t / close_{t-n})`
- **Parameters**: Periods [1, 3, 5]
- **Use**: Normalized returns

### Rolling Statistics (9 features)

#### Rolling Mean
- **Features**: `roll_mean_5`, `roll_mean_10`, `roll_mean_20`
- **Formula**: `SMA(n)` of close

#### Rolling Std
- **Features**: `roll_std_5`, `roll_std_10`, `roll_std_20`
- **Formula**: `STD(n)` of close
- **Use**: Volatility measurement

#### Distribution
- **Features**: `skewness_20`, `kurtosis_20`
- **Formula**: Rolling skew/kurtosis of close
- **Parameters**: Period 20
- **Use**: Distribution shape

### Volatility Regime (2 features)

- **Feature**: `volatility_regime` (binary 0/1)
- **Formula**: `1 if STD(20) > STD(100), else 0`
- **Use**: High vs low volatility regimes

- **Feature**: `volatility_zscore`
- **Formula**: `(STD(20) - mean(STD(20)) / std(STD(20))`
- **Use**: Normalized volatility measure

### Distance Features (4 features) - NEW in Phase 2

- **Features**: `distance_sma_20`, `distance_sma_50`, `distance_high_20`, `distance_low_20`
- **Formula**: `(value - reference) / close`
- **Use**: Normalized distance from key levels
- **Rationale**: Price position relative to SMAs/highs/lows

---

## Category 4: Volume Features (6 features)

### Volume Moving Averages
- `volume_sma_20`: 20-period SMA of volume
- `volume_ema_20`: 20-period EMA of volume

### Volume Ratios
- `volume_sma_ratio`: volume / volume_sma_20
- `volume_ema_ratio`: volume / volume_ema_20

### Volume Dynamics
- `volume_momentum`: `pct_change(5)` of volume
- `volume_volatility`: `STD(10)` of volume

---

## Category 5: Time Features (4 features)

### Cyclical Encoding

- **Features**: `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`
- **Formula**:
  - Hour: `sin(2π * hour / 24)`, `cos(2π * hour / 24)`
  - DOW: `sin(2π * dow / 7)`, `cos(2π * dow / 7)`
- **Use**: Seasonality, intraday patterns

---

## Category 6: Multi-Timeframe Features (0-6 features)

**Conditional**: Only added when higher timeframes available

### From 1h Timeframe (3 features if available)
- `rsi_14_1h`: RSI computed on 1h bars
- `macd_hist_1h`: MACD histogram on 1h bars
- `trend_strength_1h`: |SMA20 - SMA50| / close on 1h

### From 4h Timeframe (3 features if available)
- `rsi_14_4h`: RSI computed on 4h bars
- `macd_hist_4h`: MACD histogram on 4h bars
- `trend_strength_4h`: |SMA20 - SMA50| / close on 4h

**No Look-Ahead**: Backward-fill merge using timestamp join

---

## Feature Engineering Principles

### 1. No Look-Ahead

**All features** use only:
- Current bar data
- Historical data via `.shift()`, `.rolling()`
- Backward-fill merge for MTF (not forward-fill)

**Verification**:
- All rolling windows use historical data only
- MTF merge uses 'asof' join (backward-fill)
- No future data leakage

### 2. Normalization

**Price-normalized features**:
- `atr_pct`: ATR / price
- `distance_*`: All distance features normalized by price
- `bb_pos`, `bb_pctb`: Position within bands

**Volume ratios**: Volume / volume_average

**Rationale**: Stability across different price levels

### 3. Cyclical Encoding

**Time features** use sin/cos encoding:
- Preserves cyclical nature (hour 23 close to hour 0)
- Better for tree-based models than ordinal encoding

### 4. Pattern Flags

**Binary flags** (0/1) for:
- Candlestick patterns
- Swing patterns
- Volatility regime

**Rationale**: Clear categorical signals

---

## Data Cleaning

**Pipeline**:
1. Replace inf with NaN
2. Forward-fill NaN within series
3. Backward-fill remaining NaN
4. Fill any remaining with 0

**Applied to**: All features before training

---

## Training Configuration

**Current Setup** (`ml/training/train_lgbm_per_symbol_tf.py`):
- **Label**: Binary (forward_bars=1, threshold_pct=0.15%)
- **Models**: 9 separate models (3 symbols × 3 TFs)
- **Features**: 68-74 per model
- **Validation**: Time-series 5-fold CV

**Model Files**: `models/lgbm/{SYMBOL}_{TF}_last6m.pkl`

---

## Usage in Inference

**Scorer**: `scoring/ml_scorer.py`

**Flow**:
1. Load OHLCV data
2. Call `FeatureBuilder.build_features()`
3. Extract feature columns matching trained model
4. Predict with LightGBM
5. Map probability to score (0-100)

**Fallback**: Neutral score if model unavailable

---

## Future Enhancements

### Potential Additions

1. **Cross-Asset**:
   - BTC dominance impact
   - ETH/BTC correlation
   - Market-wide momentum

2. **External Data**:
   - Order book imbalance
   - Funding rate
   - Social sentiment

3. **Advanced**:
   - Regime-specific features
   - Event detection
   - Microstructure features

4. **On-Chain**:
   - Exchange reserves
   - Whale movements
   - DEX flows

---

**Last Updated**: 2025-11-01  
**Version**: Phase 2 Expanded  
**Status**: ✅ Production-Ready  
**No Look-Ahead**: ✅ Verified
