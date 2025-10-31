"""
ML Integration Tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from ml.features import FeatureBuilder
from scoring.ml_scorer import MLScorer


def test_full_pipeline():
    """Test full ML pipeline from features to scoring."""
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
    
    # Step 1: Build features
    builder = FeatureBuilder()
    df_features = builder.build_features(df)
    
    assert len(builder.feature_columns) >= 60
    assert len(df_features) == 100
    
    # Step 2: Create labels
    df_labels = builder.create_label(df_features, forward_bars=3, threshold_pct=0.25)
    
    assert 'label' in df_labels.columns
    assert len(df_labels) == 97  # 100 - 3 (forward_bars)
    
    # Step 3: Score using ML scorer
    scorer = MLScorer()
    bundle = {'main': df}
    score, rationale, details = scorer.score('BTC-USDT-SWAP', bundle)
    
    # Verify output
    assert 0 <= score <= 100
    assert isinstance(rationale, str)
    assert isinstance(details, dict)
    assert 'p_up' in details


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

