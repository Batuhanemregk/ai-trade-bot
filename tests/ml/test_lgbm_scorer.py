"""
Tests for LightGBM Scorer
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from scoring.ml_scorer import MLScorer


def test_scorer_initialization():
    """Test ML scorer initialization."""
    scorer = MLScorer()
    
    # Should initialize even if models not found
    assert scorer is not None
    assert hasattr(scorer, 'models')
    assert hasattr(scorer, 'feature_builder')


def test_extract_symbol():
    """Test symbol extraction from full symbol string."""
    scorer = MLScorer()
    
    assert scorer._extract_symbol('BTC-USDT-SWAP') == 'BTC'
    assert scorer._extract_symbol('ETH-USDT-SWAP') == 'ETH'
    assert scorer._extract_symbol('SOL-USDT-SWAP') == 'SOL'
    assert scorer._extract_symbol('BTCUSDT') == 'BTC'
    assert scorer._extract_symbol('BTC') == 'BTC'


def test_extract_timeframe():
    """Test timeframe extraction from OHLCV bundle."""
    scorer = MLScorer()
    
    # Test with main key
    bundle = {'main': pd.DataFrame({'close': [100]})}
    assert scorer._extract_timeframe(bundle) == '15m'
    
    # Test with explicit TF
    bundle = {'1h': pd.DataFrame({'close': [100]})}
    assert scorer._extract_timeframe(bundle) == '1h'
    
    bundle = {'4h': pd.DataFrame({'close': [100]})}
    assert scorer._extract_timeframe(bundle) == '4h'
    
    # Test default
    bundle = {}
    assert scorer._extract_timeframe(bundle) == '15m'


def test_score_fallback():
    """Test fallback scoring when model unavailable."""
    scorer = MLScorer()
    
    # Create mock OHLCV bundle
    dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    df = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100,
        'low': np.random.rand(100) * 100,
        'close': np.random.rand(100) * 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    bundle = {'main': df}
    
    # Score (should use fallback if no models)
    score, rationale, details = scorer.score('BTC-USDT-SWAP', bundle)
    
    # Verify fallback behavior
    assert 0 <= score <= 100
    assert 'fallback' in details.get('source', '') or 'model' in rationale.lower()
    assert 'p_up' in details
    assert 'p_down' in details


def test_score_with_mock_model():
    """Test scoring with a mock model (if available)."""
    scorer = MLScorer()
    
    # Only test if models are loaded
    if len(scorer.models) == 0:
        pytest.skip("No models loaded, skipping model test")
    
    # Create mock OHLCV bundle
    dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
    df = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100,
        'low': np.random.rand(100) * 100,
        'close': np.random.rand(100) * 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    bundle = {'main': df, '1h': df, '4h': df}
    
    # Score
    score, rationale, details = scorer.score('BTC-USDT-SWAP', bundle)
    
    # Verify output format
    assert 0 <= score <= 100
    assert isinstance(rationale, str)
    assert isinstance(details, dict)
    assert 'p_up' in details
    assert 'model_type' in details


def test_confidence_calculation():
    """Test confidence level calculation."""
    scorer = MLScorer()
    
    assert scorer._calculate_confidence(0.50) == 'low'
    assert scorer._calculate_confidence(0.70) == 'high'
    assert scorer._calculate_confidence(0.30) == 'high'
    assert scorer._calculate_confidence(0.60) == 'medium'
    assert scorer._calculate_confidence(0.45) == 'medium'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

