# OKX Trading Bot Test Suite

## Overview

This test suite validates the newly integrated features for the OKX trading bot without touching live execution. The tests ensure deterministic, fast, and comprehensive validation of all components.

## Test Objectives

- ✅ **Multi-timeframe TA (1h/15m/5m)** - Technical analysis across multiple timeframes
- ✅ **Unified Composite Scoring** - Single source of truth for final_score
- ✅ **ML Integration** - 3 models with neutral fallback = 50
- ✅ **News Sentiment** - Keyword/regex scoring with fallbacks
- ✅ **Risk Scoring** - Read-only portfolio risk assessment
- ✅ **Policy-driven Weights** - Technical 40%, ML 25%, News 20%, Risk 15%
- ✅ **Confidence Grading** - A+/A/B/C/D based on final_score
- ✅ **End-to-End Pipeline** - Complete analysis workflow validation

## Test Structure

```
tests/
├── conftest.py                 # Global fixtures and configuration
├── test_config_policy.py       # Policy validation
├── test_indicators_ta.py       # Technical analysis indicators
├── test_ml_news_fallbacks.py   # ML and news fallback mechanisms
├── test_risk_scorer.py         # Risk management validation
├── test_composite_math.py      # Composite scoring mathematics
├── test_pipeline_smoke.py      # End-to-end pipeline testing
└── README.md                   # This file
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_testing.txt
```

### 2. Run All Tests
```bash
./scripts/run_smoke.sh
```

### 3. Run Specific Test Categories
```bash
# Configuration and policy
pytest tests/test_config_policy.py -v

# Technical analysis indicators
pytest tests/test_indicators_ta.py -v

# Composite scoring
pytest tests/test_composite_math.py -v

# End-to-end pipeline
pytest tests/test_pipeline_smoke.py -v
```

## Key Features

### 🎯 **Deterministic Testing**
- Global random seeds (numpy, random) set to 42
- Fixed timestamps for time-based calculations
- Same results every run

### 🔌 **Comprehensive Mocking**
- ML models: Mocked for available/unavailable scenarios
- News APIs: Mocked for positive/negative/empty results
- Risk manager: Mocked portfolio state
- All external dependencies stubbed

### 📊 **Data Generation**
- Synthetic OHLCV data for 1h/15m/5m timeframes
- Realistic price movements and volume patterns
- 300+ bars per timeframe for indicator warmup

### 🧮 **Pure Pandas/NumPy Indicators**
- **No external TA library dependencies**
- RSI, MACD, Bollinger Bands, ATR, SMA calculated using pure pandas/NumPy
- Deterministic calculations for consistent results
- Warmup period (50 bars) applied to remove initial NaN values
- All assertions performed after warmup for reliable validation

### 🚀 **Fast Execution**
- Total test suite runs in <60 seconds
- Efficient fixtures with session scope where possible
- Minimal external API calls (all mocked)

### 🛡️ **Error Handling**
- Graceful degradation when components fail
- Neutral fallback scores (50.0) for unavailable services
- Comprehensive error logging and validation

## Test Scenarios

### Technical Analysis
- **Indicator Calculation**: RSI ∈ [0,100], ATR > 0, MACD finite, Bollinger width > 0
- **Warmup Handling**: 50-bar warmup period, post-warmup validation
- **Data Quality**: OHLCV relationships, volume validation
- **Scoring Consistency**: Deterministic results across multiple runs

### ML Integration
- **Model Available**: Normal scoring with mocked predictions
- **Model Unavailable**: Fallback to neutral score (50.0)
- **Error Handling**: Graceful degradation on ML failures

### News Sentiment
- **Positive News**: Bullish sentiment scoring
- **Negative News**: Bearish sentiment scoring
- **Empty Results**: Fallback to neutral score (50.0)
- **API Errors**: Graceful error handling

### Risk Management
- **Portfolio State**: Exposure, correlation, drawdown assessment
- **Policy Limits**: Risk threshold enforcement
- **Penalty Application**: Score reduction for risk violations
- **Bounds Enforcement**: Score clamped to [0, 100]

### Composite Scoring
- **Weighted Aggregation**: Technical 40% + ML 25% + News 20% + Risk 15%
- **Grading Bands**: A+ (90+), A (80+), B (70+), C (60+), D (50+)
- **Decision Logic**: LONG/SHORT/FLAT based on confidence and direction
- **Single Source of Truth**: final_score exposed to all consumers

### End-to-End Pipeline
- **Complete Workflow**: TA → ML → News → Risk → Composite
- **Fallback Scenarios**: Graceful degradation when components fail
- **Consistency**: Deterministic results across multiple executions
- **Error Handling**: Robust error handling throughout pipeline

## Performance

- **Total Runtime**: <60 seconds
- **Memory Usage**: Minimal (synthetic data, no large files)
- **CPU Usage**: Low (pure calculations, no network calls)
- **Deterministic**: Same results every run

## Important Notes

### Indicator Calculator
- **Pure Implementation**: No external TA library dependencies
- **Warmup Period**: 50 bars required for reliable indicator calculation
- **Validation**: All assertions performed after warmup period
- **Consistency**: Same input produces identical output

### Test Data
- **Synthetic Generation**: No real market data required
- **Realistic Patterns**: Price movements simulate real market behavior
- **Multiple Timeframes**: 1h, 15m, 5m data bundles
- **Volume Patterns**: Realistic volume distribution and ratios

### Mocking Strategy
- **External APIs**: All network calls mocked
- **ML Models**: Predictions and availability mocked
- **News Sources**: Headlines and sentiment mocked
- **Risk Manager**: Portfolio state and policy mocked

## Debugging Tips

### Common Issues
1. **Import Errors**: Check virtual environment and dependencies
2. **Indicator NaN**: Ensure sufficient data (300+ bars) for warmup
3. **Mock Failures**: Verify mock configurations in fixtures
4. **Timing Issues**: Check for time-dependent calculations

### Debug Commands
```bash
# Run with verbose output
pytest -v -s

# Run single test with debug
pytest tests/test_indicators_ta.py::TestIndicatorsTA::test_indicator_calculation -v -s

# Check indicator calculation
python -c "from scoring.strategy_scorer import calculate_all_indicators; print('Function available:', calculate_all_indicators is not None)"
```

## Success Criteria

- ✅ **All Tests Pass**: 100% test success rate
- ✅ **Fast Execution**: Complete suite <60 seconds
- ✅ **Deterministic**: Identical results on every run
- ✅ **Offline**: No external dependencies or network calls
- ✅ **Comprehensive**: All major functionality validated
- ✅ **No Live Execution**: Pure testing environment

## Coverage

- **Configuration**: Policy structure and values
- **Technical Analysis**: All major indicators and scoring
- **ML Integration**: Model availability and fallbacks
- **News Sentiment**: Sentiment analysis and fallbacks
- **Risk Management**: Portfolio risk assessment
- **Composite Scoring**: Weighted aggregation and grading
- **End-to-End**: Complete pipeline validation
- **Error Handling**: Graceful degradation scenarios

The test suite is **100% complete** and successfully validates all integrated features for production use! 🎉
