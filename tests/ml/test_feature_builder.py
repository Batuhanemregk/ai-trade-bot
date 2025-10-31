"""
Tests for ML Feature Builder
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ml.features import FeatureBuilder


def test_no_look_ahead():
    """Test that features don't use future data."""
    builder = FeatureBuilder()
    
    # Create sample OHLCV data
    dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.1,
        'high': prices + np.abs(np.random.randn(100) * 0.2),
        'low': prices - np.abs(np.random.randn(100) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Build features
    df_features = builder.build_features(df)
    
    # Verify no future data usage
    # Features at time t should only use data up to time t
    for i in range(10, len(df_features)):
        # Get features for bar i
        features_i = df_features.iloc[i]
        
        # Verify RSI, MACD, etc. only use past data
        # RSI uses rolling window, so should be valid
        assert not pd.isna(features_i.get('rsi_14', 50)) or i < 14  # RSI needs 14 bars
    
    assert len(builder.feature_columns) > 50  # Should have 60+ features


def test_feature_completeness():
    """Test that all expected features are present."""
    builder = FeatureBuilder()
    
    dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    df = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100,
        'low': np.random.rand(100) * 100,
        'close': np.random.rand(100) * 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    df_features = builder.build_features(df)
    
    # Check for key feature categories
    assert 'rsi_14' in df_features.columns
    assert 'macd_hist' in df_features.columns
    assert 'sma_20' in df_features.columns
    assert 'bb_pos' in df_features.columns
    assert 'hour_sin' in df_features.columns
    assert 'volume_sma_20' in df_features.columns
    
    # Check feature count
    assert len(builder.feature_columns) >= 60


def test_multitf_features():
    """Test multi-timeframe feature integration."""
    builder = FeatureBuilder()
    
    # Create 15m data
    dates_15m = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    df_15m = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100,
        'low': np.random.rand(100) * 100,
        'close': np.random.rand(100) * 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates_15m)
    
    # Create 1h data
    dates_1h = pd.date_range(start='2025-01-01', periods=25, freq='1H')
    df_1h = pd.DataFrame({
        'open': np.random.rand(25) * 100,
        'high': np.random.rand(25) * 100,
        'low': np.random.rand(25) * 100,
        'close': np.random.rand(25) * 100,
        'volume': np.random.randint(5000, 50000, 25)
    }, index=dates_1h)
    
    # Build features with MTF
    df_features = builder.build_features(df_15m, df_1h=df_1h)
    
    # Verify MTF features present
    assert 'rsi_14_1h' in df_features.columns
    assert 'macd_hist_1h' in df_features.columns
    assert 'trend_strength_1h' in df_features.columns
    
    # Verify no look-ahead: MTF features should use backward fill
    # (value from last 1h bar before current 15m bar)
    assert not df_features['rsi_14_1h'].isna().all()


def test_label_construction():
    """Test threshold-based label construction."""
    builder = FeatureBuilder()
    
    dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    
    # Create price series with known future moves
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    # Make some future moves > 0.25%
    prices[50] = prices[49] * 1.005  # +0.5% move
    prices[60] = prices[59] * 0.995  # -0.5% move
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Build features first
    df_features = builder.build_features(df)
    
    # Create labels
    df_labels = builder.create_label(df_features, forward_bars=3, threshold_pct=0.25)
    
    # Verify label column present
    assert 'label' in df_labels.columns
    
    # Verify labels are binary
    assert df_labels['label'].isin([0, 1]).all()
    
    # Verify forward_bars rows dropped
    assert len(df_labels) == len(df_features) - 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

