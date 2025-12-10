"""
Test ML Model Fallback Strategy

Tests for the TA-only fallback when ML models are unavailable.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
import numpy as np


class TestMLFallback:
    """Tests for ML model fallback to TA-only mode."""
    
    @pytest.fixture
    def mock_ohlcv_data(self):
        """Create mock OHLCV data."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        return {
            'main': pd.DataFrame({
                'open': np.random.uniform(50000, 51000, 100),
                'high': np.random.uniform(51000, 52000, 100),
                'low': np.random.uniform(49000, 50000, 100),
                'close': np.random.uniform(50000, 51000, 100),
                'volume': np.random.uniform(100, 1000, 100)
            }, index=dates)
        }
    
    def test_fallback_returns_none_score(self):
        """Test that ML fallback returns None score for TA-only mode."""
        from scoring.ml_scorer import MLScorer
        
        scorer = MLScorer()
        # Without loaded models, should use fallback
        score, rationale, details = scorer._fallback_score('BTC')
        
        assert score is None
        assert 'TA-only mode' in rationale
        assert details.get('ml_available') is False
    
    def test_scorer_without_model_uses_fallback(self, mock_ohlcv_data):
        """Test that scorer uses fallback when model not loaded."""
        from scoring.ml_scorer import MLScorer
        
        scorer = MLScorer()
        # Clear any loaded models
        scorer.models = {}
        
        score, rationale, details = scorer.score('XYZ', mock_ohlcv_data)
        
        # Should return None for TA-only mode
        assert score is None or details.get('source') == 'fallback'
    
    @pytest.mark.asyncio
    async def test_compute_ml_analysis_propagates_none(self, mock_ohlcv_data):
        """Test that _compute_ml_analysis propagates None from fallback."""
        from infrastructure.runtime import _compute_ml_analysis
        from scoring.ml_scorer import MLScorer
        
        ml_scorer = MLScorer()
        ml_scorer.models = {}  # No models loaded
        
        score, rationale, details = await _compute_ml_analysis(
            ml_scorer, mock_ohlcv_data, 'UNKNOWN-COIN'
        )
        
        # Should return None to indicate TA-only mode
        assert score is None or details.get('fallback') is True
    
    @pytest.mark.asyncio
    async def test_no_main_data_triggers_ta_only(self):
        """Test that missing main timeframe data triggers TA-only mode."""
        from infrastructure.runtime import _compute_ml_analysis
        from scoring.ml_scorer import MLScorer
        
        ml_scorer = MLScorer()
        empty_data = {}  # No main timeframe
        
        score, rationale, details = await _compute_ml_analysis(
            ml_scorer, empty_data, 'BTC'
        )
        
        assert score is None
        assert details.get('fallback') is True


class TestMLModelLoading:
    """Tests for ML model loading (15m only)."""
    
    def test_only_15m_models_loaded(self):
        """Test that only 15m timeframe models are loaded (9→3 reduction)."""
        from scoring.ml_scorer import MLScorer
        
        scorer = MLScorer()
        
        # Check that no 1h or 4h models are loaded
        for key in scorer.models.keys():
            assert '_15m' in key or key.endswith('_15m'), f"Unexpected model key: {key}"
            assert '_1h' not in key, f"1h model should not be loaded: {key}"
            assert '_4h' not in key, f"4h model should not be loaded: {key}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
