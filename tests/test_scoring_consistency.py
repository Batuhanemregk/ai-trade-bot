"""
Test scoring consistency for the composite signal system.
"""

from datetime import datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Import the scoring components
from scoring import (
    CompositeSignal,
    MLBlock,
    NewsBlock,
    RiskBlock,
    TechnicalBlock,
    ml_scorer,
    news_scorer,
    risk_scorer,
    ta_scorer,
)


class TestScoringConsistency:
    """Test class for scoring consistency."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create sample OHLCV data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        self.sample_ohlcv = pd.DataFrame({
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }, index=dates)

        # Sample scoring weights
        self.sample_weights = {
            'technical': 0.40,
            'ml': 0.25,
            'news': 0.20,
            'risk': 0.15
        }

        # Sample thresholds
        self.sample_thresholds = {
            'min_confidence_pct': 60,
            'grades': {
                'Aplus': [90, 100],
                'A': [80, 89],
                'B': [70, 79],
                'C': [60, 69]
            }
        }

    def test_technical_block_creation(self):
        """Test TechnicalBlock creation and validation."""
        technical_block = TechnicalBlock(
            score=75.5,
            rationale="Strong uptrend with RSI confirmation",
            flags={"trend": "up", "dir_hint": "LONG"}
        )

        assert technical_block.score == 75.5
        assert technical_block.rationale == "Strong uptrend with RSI confirmation"
        assert technical_block.flags["trend"] == "up"
        assert technical_block.flags["dir_hint"] == "LONG"

    def test_ml_block_creation(self):
        """Test MLBlock creation and validation."""
        ml_block = MLBlock(
            score=82.0,
            rationale="RandomForest predicts BUY, LinearRegression bullish",
            details={"model_status": "available", "confidence": "high"}
        )

        assert ml_block.score == 82.0
        assert ml_block.rationale == "RandomForest predicts BUY, LinearRegression bullish"
        assert ml_block.details["model_status"] == "available"

    def test_news_block_creation(self):
        """Test NewsBlock creation and validation."""
        news_block = NewsBlock(
            score=68.0,
            categories=["MARKET", "TECHNOLOGY"],
            rationale="Positive market sentiment, technology adoption news",
            volatility_impact=0.7
        )

        assert news_block.score == 68.0
        assert "MARKET" in news_block.categories
        assert news_block.volatility_impact == 0.7

    def test_risk_block_creation(self):
        """Test RiskBlock creation and validation."""
        risk_block = RiskBlock(
            score=85.0,
            details={"risk_level": "low", "penalties": []}
        )

        assert risk_block.score == 85.0
        assert risk_block.details["risk_level"] == "low"

    def test_composite_signal_creation(self):
        """Test CompositeSignal creation."""
        technical = TechnicalBlock(score=80.0, rationale="Good TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=75.0, rationale="ML bullish", details={})
        news = NewsBlock(score=70.0, categories=["MARKET"], rationale="Good news", volatility_impact=0.6)
        risk = RiskBlock(score=90.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        assert composite.symbol == "BTC-USDT"
        assert composite.technical.score == 80.0
        assert composite.ml.score == 75.0
        assert composite.news.score == 70.0
        assert composite.risk.score == 90.0

    def test_final_score_calculation(self):
        """Test that final score calculation matches expected weighted sum."""
        technical = TechnicalBlock(score=80.0, rationale="Good TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=75.0, rationale="ML bullish", details={})
        news = NewsBlock(score=70.0, categories=["MARKET"], rationale="Good news", volatility_impact=0.6)
        risk = RiskBlock(score=90.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        # Calculate expected final score
        expected_score = (
            self.sample_weights['technical'] * 80.0 +
            self.sample_weights['ml'] * 75.0 +
            self.sample_weights['news'] * 70.0 +
            self.sample_weights['risk'] * 90.0
        )

        # Finalize the signal
        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")

        # Check that final score matches expected calculation
        assert abs(composite.final_score - expected_score) < 0.01
        assert composite.confidence_pct == composite.final_score

    def test_grade_assignment(self):
        """Test that grades are assigned correctly based on thresholds."""
        # Test A+ grade
        technical = TechnicalBlock(score=95.0, rationale="Excellent TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=90.0, rationale="ML very bullish", details={})
        news = NewsBlock(score=85.0, categories=["MARKET"], rationale="Very positive news", volatility_impact=0.8)
        risk = RiskBlock(score=95.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")
        assert composite.grade == "A+"

        # Test B grade
        technical = TechnicalBlock(score=70.0, rationale="Moderate TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=65.0, rationale="ML neutral", details={})
        news = NewsBlock(score=60.0, categories=["MARKET"], rationale="Neutral news", volatility_impact=0.5)
        risk = RiskBlock(score=75.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")
        assert composite.grade == "B"

    def test_decision_logic(self):
        """Test that decision logic respects technical+ML consensus and confidence."""
        # Test LONG decision with high confidence
        technical = TechnicalBlock(score=85.0, rationale="Strong bullish TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=80.0, rationale="ML bullish", details={})
        news = NewsBlock(score=75.0, categories=["MARKET"], rationale="Positive news", volatility_impact=0.7)
        risk = RiskBlock(score=85.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")
        assert composite.decision == "LONG"
        assert composite.confidence_pct >= 60

        # Test FLAT decision with low confidence
        technical = TechnicalBlock(score=45.0, rationale="Weak TA", flags={"dir_hint": "FLAT"})
        ml = MLBlock(score=40.0, rationale="ML bearish", details={})
        news = NewsBlock(score=35.0, categories=["MARKET"], rationale="Negative news", volatility_impact=0.8)
        risk = RiskBlock(score=50.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "FLAT")
        assert composite.decision == "FLAT"  # Should be FLAT due to low confidence

    def test_position_size_multiplier(self):
        """Test position size multiplier based on grade."""
        technical = TechnicalBlock(score=90.0, rationale="Excellent TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=85.0, rationale="ML very bullish", details={})
        news = NewsBlock(score=80.0, categories=["MARKET"], rationale="Very positive news", volatility_impact=0.7)
        risk = RiskBlock(score=90.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")

        # A+ grade should give 1.0 multiplier (large position)
        assert composite.grade == "A+"
        assert composite.get_position_size_multiplier() == 1.0

        # Test other grades
        composite.grade = "A"
        assert composite.get_position_size_multiplier() == 0.7

        composite.grade = "B"
        assert composite.get_position_size_multiplier() == 0.5

        composite.grade = "C"
        assert composite.get_position_size_multiplier() == 0.3

        composite.grade = "D"
        assert composite.get_position_size_multiplier() == 0.0

    def test_composite_signal_serialization(self):
        """Test that CompositeSignal can be converted to dictionary and back."""
        technical = TechnicalBlock(score=80.0, rationale="Good TA", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=75.0, rationale="ML bullish", details={})
        news = NewsBlock(score=70.0, categories=["MARKET"], rationale="Good news", volatility_impact=0.6)
        risk = RiskBlock(score=85.0, details={})

        composite = CompositeSignal(
            symbol="BTC-USDT",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")

        # Convert to dictionary
        signal_dict = composite.to_dict()

        # Verify all key fields are present
        assert "symbol" in signal_dict
        assert "final_score" in signal_dict
        assert "decision" in signal_dict
        assert "grade" in signal_dict
        assert "technical" in signal_dict
        assert "ml" in signal_dict
        assert "news" in signal_dict
        assert "risk" in signal_dict

        # Verify technical block data
        assert signal_dict["technical"]["score"] == 80.0
        assert signal_dict["technical"]["flags"]["dir_hint"] == "LONG"

    def test_scoring_components_integration(self):
        """Test that all scoring components work together."""
        # Mock the scoring components to return predictable values
        with patch.object(ta_scorer, 'score', return_value=(80.0, "Good TA", {"dir_hint": "LONG"})):
            with patch.object(ml_scorer, 'score', return_value=(75.0, "ML bullish", {})):
                with patch.object(news_scorer, 'score', return_value=(70.0, ["MARKET"], "Good news", 0.6)):
                    with patch.object(risk_scorer, 'score', return_value=(85.0, {})):

                        # Create blocks
                        technical = TechnicalBlock(score=80.0, rationale="Good TA", flags={"dir_hint": "LONG"})
                        ml = MLBlock(score=75.0, rationale="ML bullish", details={})
                        news = NewsBlock(score=70.0, categories=["MARKET"], rationale="Good news", volatility_impact=0.6)
                        risk = RiskBlock(score=85.0, details={})

                        # Create composite signal
                        composite = CompositeSignal(
                            symbol="BTC-USDT",
                            timestamp=datetime.now(),
                            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
                            technical=technical,
                            ml=ml,
                            news=news,
                            risk=risk
                        )

                        # Finalize
                        composite.finalize(self.sample_weights, self.sample_thresholds, "LONG")

                        # Verify integration works
                        assert composite.decision == "LONG"
                        assert composite.grade in ["A+", "A", "B"]
                        assert composite.is_tradeable()
                        assert composite.get_position_size_multiplier() > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
