"""
Test suite for scoring service.
Tests weight math, grading, and composite score composition.
"""

from datetime import datetime

import pytest

from application.scoring_service import AnalysisResult, CompositeScore, ScoringService
from domain.models import SignalType


class TestScoringService:
    """Test the scoring service functionality."""

    @pytest.fixture
    def scoring_config(self):
        """Default scoring configuration for testing."""
        return {
            "scoring_weights": {"ta": 0.4, "ml": 0.4, "news": 0.2},
            "buy_threshold": 60.0,
            "sell_threshold": 40.0,
            "confidence_threshold": 0.6
        }

    @pytest.fixture
    def scoring_service(self, scoring_config):
        """Scoring service instance for testing."""
        return ScoringService(scoring_config)

    @pytest.fixture
    def mock_ta_result(self):
        """Mock technical analysis result."""
        return AnalysisResult(
            source="ta",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=80.0,
            signal=SignalType.BUY,
            confidence=0.9,
            rationale="Strong bullish signals: RSI oversold, MACD crossover"
        )

    @pytest.fixture
    def mock_ml_result(self):
        """Mock machine learning result."""
        return AnalysisResult(
            source="ml",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=70.0,
            signal=SignalType.BUY,
            confidence=0.8,
            rationale="ML model predicts 70% probability of upward movement"
        )

    @pytest.fixture
    def mock_news_result(self):
        """Mock news sentiment result."""
        return AnalysisResult(
            source="news",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=0.8,  # Positive sentiment
            signal=SignalType.BUY,
            confidence=0.7,
            rationale="Recent news shows positive developments"
        )

    def test_scoring_service_initialization(self, scoring_service):
        """Test scoring service initialization."""
        assert scoring_service.weights["ta"] == 0.4
        assert scoring_service.weights["ml"] == 0.4
        assert scoring_service.weights["news"] == 0.2
        assert scoring_service.buy_threshold == 60.0
        assert scoring_service.sell_threshold == 40.0
        assert scoring_service.confidence_threshold == 0.6

        # Check grade thresholds
        assert scoring_service.grade_thresholds["A+"] == 90.0
        assert scoring_service.grade_thresholds["A"] == 80.0
        assert scoring_service.grade_thresholds["B"] == 70.0
        assert scoring_service.grade_thresholds["C"] == 60.0
        assert scoring_service.grade_thresholds["D"] == 0.0

    def test_compose_score_with_all_results(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test composing score with all analysis results."""
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        # Verify composite score structure
        assert isinstance(composite_score, CompositeScore)
        assert composite_score.symbol == "BTC-USDT-SWAP"
        assert composite_score.ta_score == 80.0
        assert composite_score.ml_score == 70.0
        assert composite_score.news_score == 0.8

        # Verify weights
        assert composite_score.ta_weight == 0.4
        assert composite_score.ml_weight == 0.4
        assert composite_score.news_weight == 0.2

        # Verify component signals and confidences
        assert composite_score.ta_signal == SignalType.BUY
        assert composite_score.ml_signal == SignalType.BUY
        assert composite_score.news_signal == SignalType.BUY
        assert composite_score.ta_confidence == 0.9
        assert composite_score.ml_confidence == 0.8
        assert composite_score.news_confidence == 0.7

    def test_weight_math_calculation(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test that weighted score calculation is correct."""
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        # Calculate expected weighted score
        # TA: 80.0 * 0.4 = 32.0
        # ML: 70.0 * 0.4 = 28.0
        # News: 0.8 * 0.2 = 0.16 (news score is already in 0-100 scale)
        expected_score = (80.0 * 0.4) + (70.0 * 0.4) + (0.8 * 0.2)
        expected_score = 32.0 + 28.0 + 0.16  # = 60.16

        assert abs(composite_score.overall_score - expected_score) < 0.01

        # Verify overall confidence (weighted average)
        expected_confidence = (0.9 * 0.4) + (0.8 * 0.4) + (0.7 * 0.2)
        expected_confidence = 0.36 + 0.32 + 0.14  # = 0.82

        assert abs(composite_score.overall_confidence - expected_confidence) < 0.01

    def test_grade_calculation(self, scoring_service):
        """Test grade calculation based on score thresholds."""
        # Test A+ grade
        assert scoring_service._calculate_grade(95.0) == "A+"
        assert scoring_service._calculate_grade(90.0) == "A+"

        # Test A grade
        assert scoring_service._calculate_grade(89.9) == "A"
        assert scoring_service._calculate_grade(80.0) == "A"

        # Test B grade
        assert scoring_service._calculate_grade(79.9) == "B"
        assert scoring_service._calculate_grade(70.0) == "B"

        # Test C grade
        assert scoring_service._calculate_grade(69.9) == "C"
        assert scoring_service._calculate_grade(60.0) == "C"

        # Test D grade
        assert scoring_service._calculate_grade(59.9) == "D"
        assert scoring_service._calculate_grade(0.0) == "D"

    def test_signal_determination(self, scoring_service):
        """Test signal determination based on score thresholds."""
        # Test BUY signal
        assert scoring_service._determine_signal(75.0) == SignalType.BUY
        assert scoring_service._determine_signal(60.0) == SignalType.BUY

        # Test SELL signal
        assert scoring_service._determine_signal(35.0) == SignalType.SELL
        assert scoring_service._determine_signal(40.0) == SignalType.SELL

        # Test HOLD signal
        assert scoring_service._determine_signal(50.0) == SignalType.HOLD
        assert scoring_service._determine_signal(59.9) == SignalType.HOLD
        assert scoring_service._determine_signal(40.1) == SignalType.HOLD

    def test_compose_score_with_missing_results(self, scoring_service, mock_ta_result):
        """Test composing score with missing analysis results."""
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            symbol="BTC-USDT-SWAP"
        )

        # Should create default results for missing ML and news
        assert composite_score.ta_score == 80.0
        assert composite_score.ml_score == 50.0  # Default neutral score
        assert composite_score.news_score == 50.0  # Default neutral score

        # Default results should have no confidence
        assert composite_score.ta_confidence == 0.9
        assert composite_score.ml_confidence == 0.0
        assert composite_score.news_confidence == 0.0

        # Should indicate missing data in rationale
        assert "No ML data available" in composite_score.ml_rationale
        assert "No NEWS data available" in composite_score.news_rationale

    def test_composite_rationale_generation(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test composite rationale generation."""
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        rationale = composite_score.composite_rationale

        # Should contain overall assessment
        assert "bullish signals" in rationale.lower()

        # Should contain component highlights
        assert "strong technical analysis" in rationale.lower()
        assert "strong ml prediction" in rationale.lower()
        assert "positive news sentiment" in rationale.lower()

    def test_get_score_summary(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test getting score summary."""
        # First compose a score
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        # Get summary
        summary = scoring_service.get_score_summary("BTC-USDT-SWAP")

        # Verify summary structure
        assert summary["symbol"] == "BTC-USDT-SWAP"
        assert summary["grade"] == composite_score.grade
        assert summary["overall_score"] == composite_score.overall_score
        assert summary["signal"] == composite_score.overall_signal.value
        assert summary["confidence"] == composite_score.overall_confidence

        # Verify components
        assert "ta" in summary["components"]
        assert "ml" in summary["components"]
        assert "news" in summary["components"]

        # Verify weights
        assert summary["weights"] == scoring_service.weights

    def test_get_service_status(self, scoring_service):
        """Test getting service status."""
        status = scoring_service.get_service_status()

        assert "weights" in status
        assert "thresholds" in status
        assert "grade_thresholds" in status
        assert "performance" in status

        # Verify performance metrics
        assert status["performance"]["scores_generated"] == 0
        assert status["performance"]["signals_generated"] == 0
        assert status["performance"]["last_score"] is None

    def test_performance_tracking(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test that performance metrics are tracked correctly."""
        initial_status = scoring_service.get_service_status()

        # Compose a score
        scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        updated_status = scoring_service.get_service_status()

        # Verify counters increased
        assert updated_status["performance"]["scores_generated"] == initial_status["performance"]["scores_generated"] + 1
        assert updated_status["performance"]["last_score"] == "BTC-USDT-SWAP"

    def test_risk_annotations_integration(self, scoring_service, mock_ta_result, mock_ml_result, mock_news_result):
        """Test that composite score includes risk annotation fields."""
        composite_score = scoring_service.compose_score(
            ta_result=mock_ta_result,
            ml_result=mock_ml_result,
            news_result=mock_news_result,
            symbol="BTC-USDT-SWAP"
        )

        # Should have risk annotation fields
        assert hasattr(composite_score, 'risk_notes')
        assert hasattr(composite_score, 'risk_penalties')

        # Should be empty initially
        assert composite_score.risk_notes == []
        assert composite_score.risk_penalties == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

