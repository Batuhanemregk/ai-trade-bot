"""
Test composite signal math and grading.
"""

from datetime import datetime

import pytest


class TestCompositeMath:
    """Test class for composite signal math and grading."""

    def test_composite_signal_import(self):
        """Test that CompositeSignal can be imported."""
        try:
            from scoring.composite_signal import (
                CompositeSignal,
                MLBlock,
                NewsBlock,
                RiskBlock,
                TechnicalBlock,
            )
            assert CompositeSignal is not None
            assert TechnicalBlock is not None
            assert MLBlock is not None
            assert NewsBlock is not None
            assert RiskBlock is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CompositeSignal components: {e}")

    def test_composite_signal_creation(self, test_weights, test_thresholds):
        """Test CompositeSignal creation with all components."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Create scoring blocks
        technical = TechnicalBlock(
            score=80.0,
            rationale="Strong uptrend with RSI confirmation",
            flags={"trend": "up", "meanrev": "off", "breakout": "on", "dir_hint": "LONG"}
        )

        ml = MLBlock(
            score=60.0,
            rationale="ML models predict moderate bullish sentiment",
            details={"model_status": "available", "confidence": "medium"}
        )

        news = NewsBlock(
            score=50.0,
            categories=["MARKET", "TECHNOLOGY"],
            rationale="Mixed news sentiment",
            volatility_impact=0.6
        )

        risk = RiskBlock(
            score=70.0,
            details={"risk_level": "medium", "penalties": ["Portfolio risk: -15.0"]}
        )

        # Create composite signal
        signal = CompositeSignal(
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        # Check basic properties
        assert signal.symbol == "BTC-USDT-SWAP"
        assert signal.technical.score == 80.0
        assert signal.ml.score == 60.0
        assert signal.news.score == 50.0
        assert signal.risk.score == 70.0

        # Check initial values
        assert signal.final_score == 0.0
        assert signal.decision == "FLAT"
        assert signal.confidence_pct == 0.0
        assert signal.grade == "D"

    def test_composite_signal_finalization(self, test_weights, test_thresholds):
        """Test CompositeSignal finalization with weights and thresholds."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Create scoring blocks with known scores
        technical = TechnicalBlock(
            score=80.0,
            rationale="Strong uptrend",
            flags={"trend": "up", "dir_hint": "LONG"}
        )

        ml = MLBlock(
            score=60.0,
            rationale="ML models available",
            details={"model_status": "available"}
        )

        news = NewsBlock(
            score=50.0,
            categories=["MARKET"],
            rationale="Neutral news",
            volatility_impact=0.5
        )

        risk = RiskBlock(
            score=70.0,
            details={"risk_level": "medium"}
        )

        # Create composite signal
        signal = CompositeSignal(
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical,
            ml=ml,
            news=news,
            risk=risk
        )

        # Finalize the signal
        signal.finalize(test_weights, test_thresholds, "LONG")

        # Calculate expected final score
        expected_score = (
            test_weights['technical'] * technical.score +
            test_weights['ml'] * ml.score +
            test_weights['news'] * news.score +
            test_weights['risk'] * risk.score
        )

        # Check final score calculation (exact float comparison within 1e-6)
        assert abs(signal.final_score - expected_score) < 1e-6, \
            f"Final score {signal.final_score} != expected {expected_score}"

        # Check confidence percentage
        assert signal.confidence_pct == signal.final_score

        # Check decision (should be LONG due to direction hint and high confidence)
        assert signal.decision == "LONG"

    def test_composite_math_accuracy(self, test_weights, test_thresholds):
        """Test that composite math calculations are mathematically accurate."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test case 1: All scores at 100
        technical = TechnicalBlock(score=100.0, rationale="Perfect", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=100.0, rationale="Perfect", details={})
        news = NewsBlock(score=100.0, categories=["MARKET"], rationale="Perfect", volatility_impact=1.0)
        risk = RiskBlock(score=100.0, details={})

        signal = CompositeSignal(
            symbol="TEST",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "LONG")

        # With all scores at 100, final score should be 100
        assert abs(signal.final_score - 100.0) < 1e-6, f"Perfect scores should result in 100, got {signal.final_score}"

        # Test case 2: All scores at 0
        technical.score = 0.0
        ml.score = 0.0
        news.score = 0.0
        risk.score = 0.0

        signal.finalize(test_weights, test_thresholds, "FLAT")

        # With all scores at 0, final score should be 0
        assert abs(signal.final_score - 0.0) < 1e-6, f"Zero scores should result in 0, got {signal.final_score}"

        # Test case 3: Mixed scores
        technical.score = 80.0
        ml.score = 60.0
        news.score = 40.0
        risk.score = 20.0

        signal.finalize(test_weights, test_thresholds, "FLAT")

        # Expected: 0.4*80 + 0.25*60 + 0.2*40 + 0.15*20 = 32 + 15 + 8 + 3 = 58
        expected = 58.0
        assert abs(signal.final_score - expected) < 1e-6, f"Expected {expected}, got {signal.final_score}"

    def test_grading_bands_mapping(self, test_weights, test_thresholds):
        """Test that grading bands map correctly to score ranges."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test different score ranges
        test_cases = [
            (92.0, "A+"),
            (85.0, "A"),
            (75.0, "B"),
            (65.0, "C"),
            (55.0, "D")
        ]

        for target_score, expected_grade in test_cases:
            # Create blocks that will result in the target score
            # We need to solve: 0.4*ta + 0.25*ml + 0.2*news + 0.15*risk = target_score
            # Let's use a simple approach: set all scores to target_score
            technical = TechnicalBlock(score=target_score, rationale="Test", flags={"dir_hint": "FLAT"})
            ml = MLBlock(score=target_score, rationale="Test", details={})
            news = NewsBlock(score=target_score, categories=["TEST"], rationale="Test", volatility_impact=0.5)
            risk = RiskBlock(score=target_score, details={})

            signal = CompositeSignal(
                symbol="TEST",
                timestamp=datetime.now(),
                timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
                technical=technical, ml=ml, news=news, risk=risk
            )

            signal.finalize(test_weights, test_thresholds, "FLAT")

            # Check grade
            assert signal.grade == expected_grade, \
                f"Score {signal.final_score:.1f} should be grade {expected_grade}, got {signal.grade}"

    def test_decision_logic(self, test_weights, test_thresholds):
        """Test decision logic based on confidence and direction hints."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test case 1: High confidence with LONG direction hint
        technical = TechnicalBlock(score=90.0, rationale="Strong", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=90.0, rationale="Strong", details={})
        news = NewsBlock(score=90.0, categories=["MARKET"], rationale="Strong", volatility_impact=0.8)
        risk = RiskBlock(score=90.0, details={})

        signal = CompositeSignal(
            symbol="TEST",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "LONG")

        assert signal.decision == "LONG", f"High confidence with LONG hint should result in LONG decision, got {signal.decision}"
        assert signal.confidence_pct >= test_thresholds['min_confidence_pct'], "Should meet minimum confidence"

        # Test case 2: Low confidence should result in FLAT
        technical.score = 30.0
        ml.score = 30.0
        news.score = 30.0
        risk.score = 30.0

        signal.finalize(test_weights, test_thresholds, "LONG")

        assert signal.decision == "FLAT", f"Low confidence should result in FLAT decision, got {signal.decision}"
        assert signal.confidence_pct < test_thresholds['min_confidence_pct'], "Should not meet minimum confidence"

        # Test case 3: High confidence without direction hint
        technical.score = 90.0
        ml.score = 90.0
        news.score = 90.0
        risk.score = 90.0
        technical.flags["dir_hint"] = "FLAT"

        signal.finalize(test_weights, test_thresholds, None)

        # Should determine direction from technical+ML consensus
        assert signal.decision in ["LONG", "SHORT", "FLAT"], f"Decision should be valid: {signal.decision}"

    def test_confidence_thresholds(self, test_weights, test_thresholds):
        """Test that confidence thresholds are properly enforced."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test with scores just below threshold
        min_confidence = test_thresholds['min_confidence_pct']

        # Calculate scores that will result in just below threshold
        target_score = min_confidence - 1.0

        technical = TechnicalBlock(score=target_score, rationale="Test", flags={"dir_hint": "FLAT"})
        ml = MLBlock(score=target_score, rationale="Test", details={})
        news = NewsBlock(score=target_score, categories=["TEST"], rationale="Test", volatility_impact=0.5)
        risk = RiskBlock(score=target_score, details={})

        signal = CompositeSignal(
            symbol="TEST",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "LONG")

        # Should result in FLAT decision due to low confidence
        assert signal.decision == "FLAT", f"Score {signal.final_score:.1f} below threshold {min_confidence} should result in FLAT"

        # Test with scores just above threshold
        target_score = min_confidence + 1.0

        technical.score = target_score
        ml.score = target_score
        news.score = target_score
        risk.score = target_score

        signal.finalize(test_weights, test_thresholds, "LONG")

        # Should result in LONG decision due to sufficient confidence
        assert signal.decision == "LONG", f"Score {signal.final_score:.1f} above threshold {min_confidence} should result in LONG"

    def test_score_bounds_enforcement(self, test_weights, test_thresholds):
        """Test that final scores are properly bounded to [0, 100]."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test with extreme scores
        technical = TechnicalBlock(score=150.0, rationale="Extreme", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=-50.0, rationale="Extreme", details={})
        news = NewsBlock(score=200.0, categories=["TEST"], rationale="Extreme", volatility_impact=1.5)
        risk = RiskBlock(score=300.0, details={})

        signal = CompositeSignal(
            symbol="TEST",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "FLAT")

        # Final score should be bounded
        assert 0 <= signal.final_score <= 100, f"Final score {signal.final_score} should be in [0, 100] range"

    def test_composite_signal_serialization(self, test_weights, test_thresholds):
        """Test that CompositeSignal can be serialized to dictionary."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Create a complete signal
        technical = TechnicalBlock(score=80.0, rationale="Test", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=70.0, rationale="Test", details={})
        news = NewsBlock(score=60.0, categories=["TEST"], rationale="Test", volatility_impact=0.6)
        risk = RiskBlock(score=75.0, details={})

        signal = CompositeSignal(
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "LONG")

        # Convert to dictionary
        signal_dict = signal.to_dict()

        # Check structure
        assert 'symbol' in signal_dict
        assert 'timestamp' in signal_dict
        assert 'timeframes' in signal_dict
        assert 'technical' in signal_dict
        assert 'ml' in signal_dict
        assert 'news' in signal_dict
        assert 'risk' in signal_dict
        assert 'final_score' in signal_dict
        assert 'decision' in signal_dict
        assert 'confidence_pct' in signal_dict
        assert 'grade' in signal_dict
        assert 'meta' in signal_dict

        # Check values
        assert signal_dict['symbol'] == "BTC-USDT-SWAP"
        assert signal_dict['final_score'] == signal.final_score
        assert signal_dict['decision'] == signal.decision
        assert signal_dict['grade'] == signal.grade

        # Check nested structures
        assert signal_dict['technical']['score'] == technical.score
        assert signal_dict['ml']['score'] == ml.score
        assert signal_dict['news']['score'] == news.score
        assert signal_dict['risk']['score'] == risk.score

    def test_position_size_multiplier(self, test_weights, test_thresholds):
        """Test position size multiplier based on grade."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test different grades
        test_cases = [
            (95.0, "A+", 1.0),   # Large position
            (85.0, "A", 0.7),     # Medium position
            (75.0, "B", 0.5),     # Small position
            (65.0, "C", 0.3),     # Tiny position
            (55.0, "D", 0.0)      # No trade
        ]

        for target_score, expected_grade, expected_multiplier in test_cases:
            technical = TechnicalBlock(score=target_score, rationale="Test", flags={"dir_hint": "LONG"})
            ml = MLBlock(score=target_score, rationale="Test", details={})
            news = NewsBlock(score=target_score, categories=["TEST"], rationale="Test", volatility_impact=0.5)
            risk = RiskBlock(score=target_score, details={})

            signal = CompositeSignal(
                symbol="TEST",
                timestamp=datetime.now(),
                timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
                technical=technical, ml=ml, news=news, risk=risk
            )

            signal.finalize(test_weights, test_thresholds, "LONG")

            # Check grade
            assert signal.grade == expected_grade, f"Score {signal.final_score:.1f} should be grade {expected_grade}"

            # Check position size multiplier
            multiplier = signal.get_position_size_multiplier()
            assert multiplier == expected_multiplier, \
                f"Grade {expected_grade} should have multiplier {expected_multiplier}, got {multiplier}"

    def test_tradeability_check(self, test_weights, test_thresholds):
        """Test tradeability check based on confidence and decision."""
        from scoring.composite_signal import (
            CompositeSignal,
            MLBlock,
            NewsBlock,
            RiskBlock,
            TechnicalBlock,
        )

        # Test case 1: Tradeable signal
        technical = TechnicalBlock(score=80.0, rationale="Strong", flags={"dir_hint": "LONG"})
        ml = MLBlock(score=80.0, rationale="Strong", details={})
        news = NewsBlock(score=80.0, categories=["MARKET"], rationale="Strong", volatility_impact=0.8)
        risk = RiskBlock(score=80.0, details={})

        signal = CompositeSignal(
            symbol="TEST",
            timestamp=datetime.now(),
            timeframes={"trend": "1h", "main": "15m", "entry": "5m"},
            technical=technical, ml=ml, news=news, risk=risk
        )

        signal.finalize(test_weights, test_thresholds, "LONG")

        assert signal.is_tradeable(), f"Signal with score {signal.final_score} and decision {signal.decision} should be tradeable"

        # Test case 2: Non-tradeable signal (low confidence)
        technical.score = 30.0
        ml.score = 30.0
        news.score = 30.0
        risk.score = 30.0

        signal.finalize(test_weights, test_thresholds, "FLAT")

        assert not signal.is_tradeable(), f"Signal with score {signal.final_score} and decision {signal.decision} should not be tradeable"

        # Test case 3: Non-tradeable signal (FLAT decision)
        technical.score = 80.0
        ml.score = 50.0  # Set ML score to neutral to get FLAT direction
        news.score = 80.0
        risk.score = 80.0
        technical.flags = {"dir_hint": "FLAT"}  # Set technical direction to FLAT

        signal.finalize(test_weights, test_thresholds, "FLAT")

        assert not signal.is_tradeable(), "Signal with FLAT decision should not be tradeable"
