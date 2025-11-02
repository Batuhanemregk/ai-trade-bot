# ML Feature Inventory

**Date**: 2025-11-01  
**Source**: `ml/features/builder.py`  
**Total Features**: 68 (single timeframe)  
**With MTF**: 68-74 depending on available timeframes

---

## Feature Count by Category

| Category | Count | Description |
|----------|-------|-------------|
| **Technical Analysis** | 29 | TA indicators (SMA, EMA, MACD, RSI, etc.) |
| **Price Action** | 16 | Candlestick patterns, HH/HL/LH/LL, Heikin-Ashi |
| **Statistics** | 16 | Rolling stats, skewness, kurtosis, volatility regime |
| **Volume** | 6 | Volume indicators and momentum |
| **Time** | 4 | Cyclical time encoding |
| **Multi-Timeframe** | 0-6 | Features from 1h/4h (conditional) |
| **TOTAL** | **68-74** | Varies by MTF availability |

---

## Alphabetical Feature List

### A-C

- `adx` - Average Directional Index
- `atr_14` - Average True Range (14-period)
- `atr_pct` - ATR as percentage of price
- `bb_lower` - Bollinger Bands lower
- `bb_pctb` - Bollinger Bands %b (position in band)
- `bb_pos` - Bollinger Bands position (normalized)
- `bb_upper` - Bollinger Bands upper
- `bb_width` - Bollinger Bands width
- `body` - Candlestick body (close - open)
- `body_ratio` - Body to range ratio

### D-F

- `distance_high_20` - Distance from 20-bar high (normalized)
- `distance_low_20` - Distance from 20-bar low (normalized)
- `distance_sma_20` - Distance from SMA20 (normalized)
- `distance_sma_50` - Distance from SMA50 (normalized)
- `dow_cos` - Day of week (cosine encoding)
- `dow_sin` - Day of week (sine encoding)
- `ema_12` - Exponential Moving Average (12-period)
- `ema_26` - Exponential Moving Average (26-period)
- `engulfing_bear` - Bearish engulfing pattern flag
- `engulfing_bull` - Bullish engulfing pattern flag

### H-L

- `ha_close` - Heikin-Ashi close
- `ha_high` - Heikin-Ashi high
- `ha_low` - Heikin-Ashi low
- `ha_open` - Heikin-Ashi open
- `hh` - Higher High pattern flag
- `hl` - Higher Low pattern flag
- `hour_cos` - Hour of day (cosine encoding)
- `hour_sin` - Hour of day (sine encoding)
- `kurtosis_20` - Kurtosis (20-period rolling)
- `lh` - Lower High pattern flag
- `ll` - Lower Low pattern flag
- `log_ret_1` - Log return (1-period)
- `log_ret_3` - Log return (3-period)
- `log_ret_5` - Log return (5-period)
- `lower_wick_ratio` - Lower wick to range ratio

### M-P

- `macd_hist` - MACD histogram
- `macd_line` - MACD line
- `macd_signal` - MACD signal line
- `mfi` - Money Flow Index
- `minus_di` - Minus Directional Indicator
- `obv` - On-Balance Volume
- `pinbar_down` - Bearish pinbar pattern flag
- `pinbar_up` - Bullish pinbar pattern flag
- `plus_di` - Plus Directional Indicator

### R-S

- `roll_mean_10` - Rolling mean (10-period)
- `roll_mean_20` - Rolling mean (20-period)
- `roll_mean_5` - Rolling mean (5-period)
- `roll_std_10` - Rolling std (10-period)
- `roll_std_20` - Rolling std (20-period)
- `roll_std_5` - Rolling std (5-period)
- `rsi_14` - Relative Strength Index (14-period)
- `skewness_20` - Skewness (20-period rolling)
- `sma_10` - Simple Moving Average (10-period)
- `sma_20` - Simple Moving Average (20-period)
- `sma_5` - Simple Moving Average (5-period)
- `sma_50` - Simple Moving Average (50-period)
- `stoch_d` - Stochastic %D
- `stoch_k` - Stochastic %K

### T-V

- `upper_wick_ratio` - Upper wick to range ratio
- `volatility_regime` - Volatility regime flag (high/low)
- `volatility_zscore` - Volatility z-score
- `volume_ema_20` - Volume EMA (20-period)
- `volume_ema_ratio` - Volume to volume EMA ratio
- `volume_momentum` - Volume momentum (5-period change)
- `volume_sma_20` - Volume SMA (20-period)
- `volume_sma_ratio` - Volume to volume SMA ratio
- `volume_volatility` - Volume volatility (10-period std)
- `williams_r` - Williams %R

### Multi-Timeframe Features (0-6, conditional)

Available only when higher timeframes provided (1h, 4h):

- `rsi_14_1h` - RSI from 1h timeframe
- `rsi_14_4h` - RSI from 4h timeframe
- `macd_hist_1h` - MACD histogram from 1h timeframe
- `macd_hist_4h` - MACD histogram from 4h timeframe
- `trend_strength_1h` - Trend strength from 1h timeframe
- `trend_strength_4h` - Trend strength from 4h timeframe

---

## Feature Groupings

### 1. Technical Analysis (29 features)

**Moving Averages**:
- `sma_5`, `sma_10`, `sma_20`, `sma_50`
- `ema_12`, `ema_26`

**MACD**:
- `macd_line`, `macd_signal`, `macd_hist`

**Momentum Oscillators**:
- `rsi_14`
- `stoch_k`, `stoch_d`
- `williams_r`

**Trend Strength**:
- `adx`
- `plus_di`, `minus_di`

**Volatility**:
- `atr_14`, `atr_pct`

**Bands**:
- `bb_upper`, `bb_lower`, `bb_width`, `bb_pos`, `bb_pctb`

**Volume**:
- `obv`
- `mfi`

### 2. Price Action (16 features)

**Candlestick Structure**:
- `body`, `body_ratio`
- `upper_wick_ratio`, `lower_wick_ratio`

**Heikin-Ashi**:
- `ha_open`, `ha_high`, `ha_low`, `ha_close`

**Pattern Flags** (binary 0/1):
- `engulfing_bull`, `engulfing_bear`
- `pinbar_up`, `pinbar_down`
- `hh`, `hl`, `lh`, `ll`

### 3. Statistics (16 features)

**Returns**:
- `log_ret_1`, `log_ret_3`, `log_ret_5`

**Rolling Statistics**:
- `roll_mean_5`, `roll_mean_10`, `roll_mean_20`
- `roll_std_5`, `roll_std_10`, `roll_std_20`

**Distribution**:
- `skewness_20`, `kurtosis_20`

**Volatility Regime**:
- `volatility_regime` (binary: high/low)
- `volatility_zscore`

**Distance Features** (Phase 2 additions):
- `distance_sma_20`, `distance_sma_50`
- `distance_high_20`, `distance_low_20`

### 4. Volume (6 features)

- `volume_sma_20`, `volume_sma_ratio`
- `volume_ema_20`, `volume_ema_ratio`
- `volume_momentum`
- `volume_volatility`

### 5. Time (4 features)

**Cyclical Encoding**:
- `hour_sin`, `hour_cos`
- `dow_sin`, `dow_cos`

### 6. Multi-Timeframe (0-6 features)

Conditional on available higher timeframes:

- `rsi_14_{1h|4h}`
- `macd_hist_{1h|4h}`
- `trend_strength_{1h|4h}`

---

## Feature Source

**Primary Source**: `ml/features/builder.py`

**Components**:
1. `_add_ta_indicators()` - Lines 75-162
2. `_add_price_action()` - Lines 164-224
3. `_add_statistics()` - Lines 226-270
4. `_add_time_features()` - Lines 272-285
5. `_add_volume_features()` - Lines 287-304
6. `_add_multitf_features()` - Lines 306-347

---

## Look-Ahead Analysis

**✅ NO LOOK-AHEAD CONFIRMED**

- All features use `.shift()` or `rolling()` operations
- MTF features use backward-fill merge (asof)
- Forward-fill only within gaps (no future data)
- Future returns calculated separately for labeling

---

## Feature Quality Notes

### Phase 2 Improvements

**New Features Added** (6 total):
- `volatility_regime` - Regime detection
- `volatility_zscore` - Normalized volatility
- `distance_sma_20`, `distance_sma_50` - SMA distance
- `distance_high_20`, `distance_low_20` - High/low distance

**Rationale**:
- Volatility regime helps model adapt to market conditions
- Distance features normalize price position relative to key levels
- All features are relative/normalized for stability

### Existing Features

**Mature**:
- All TA indicators use standard parameters
- Statistical features properly normalized
- Time features use cyclical encoding

**Potential Improvements**:
- Cross-asset correlations
- Order book features
- Social sentiment
- On-chain metrics

---

## Usage in Training

**Training Script**: `ml/training/train_lgbm_per_symbol_tf.py`

**Feature Count**:
- 15m models: 68 features (single TF only)
- 1h models: 65 features (with 4h MTF)
- 4h models: 65 features (with 1h MTF)

**Model Files**: `models/lgbm/{SYMBOL}_{TF}_last6m.pkl`

---

**Last Updated**: 2025-11-01  
**Version**: Phase 2 Expanded  
**Status**: ✅ Production-Ready
