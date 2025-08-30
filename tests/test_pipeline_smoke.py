"""
End-to-end pipeline smoke test for OKX trading bot.
"""

from unittest.mock import Mock, patch

import pytest

from scoring.composite_signal import CompositeSignal
from scoring.ml_scorer import MLScorer
from scoring.news_scorer import NewsScorer
from scoring.risk_scorer import RiskScorer
from scoring.ta_scorer import TAScorer
from scoring.strategy_scorer import calculate_all_indicators


class TestPipelineSmoke:
    """End-to-end pipeline smoke tests."""

    def test_pipeline_imports(self):
        """Test that all pipeline components can be imported."""
        # All imports should work
        assert TAScorer is not None
        assert MLScorer is not None
        assert NewsScorer is not None
        assert RiskScorer is not None
        assert CompositeSignal is not None
        assert calculate_all_indicators is not None

    def test_full_pipeline_execution(self, ohlcv_bundle_factory, fake_ml_provider,
                                   fake_news_provider, portfolio_state, test_weights, test_thresholds):
        """Test complete end-to-end pipeline execution."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]  # Use 15m for main analysis

        # Ensure indicators are computed before scoring
        indicators_df = calculate_all_indicators(main_df)
        assert not indicators_df.empty, "Indicators should be computed"

        # Mock ML provider
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider_class.return_value = fake_ml_provider

            # Mock news provider
            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client_class.return_value = fake_news_provider

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute scoring pipeline
                ta_score, ta_rationale, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                ml_score, ml_rationale = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                news_score, news_rationale = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                risk_score, risk_rationale = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                # Validate individual scores
                assert 0 <= ta_score <= 100, f"TA score out of range: {ta_score}"
                assert 0 <= ml_score <= 100, f"ML score out of range: {ml_score}"
                assert 0 <= news_score <= 100, f"News score out of range: {news_score}"
                assert 0 <= risk_score <= 100, f"Risk score out of range: {risk_score}"

                # Create composite signal
                signal = CompositeSignal(
                    technical=ta_score,
                    ml=ml_score,
                    news=news_score,
                    risk=risk_score
                )

                # Finalize signal
                signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))

                # Validate final signal
                assert 0 <= signal.final_score <= 100, f"Final score out of range: {signal.final_score}"
                assert signal.decision in ["LONG", "SHORT", "FLAT"], f"Invalid decision: {signal.decision}"
                assert signal.confidence_pct == signal.final_score, "Confidence should equal final score"
                assert signal.grade in ["A+", "A", "B", "C", "D"], f"Invalid grade: {signal.grade}"

                # Validate single source of truth
                assert signal.final_score == pytest.approx(
                    test_weights["technical"] * ta_score +
                    test_weights["ml"] * ml_score +
                    test_weights["news"] * news_score +
                    test_weights["risk"] * risk_score,
                    abs=1e-6
                )

    def test_ml_fallback_scenario(self, ohlcv_bundle_factory, portfolio_state, test_weights, test_thresholds):
        """Test ML fallback when models are unavailable."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]

        # Compute indicators
        indicators_df = calculate_all_indicators(main_df)

        # Mock ML provider with no models available
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider = Mock()
            mock_ml_provider.is_model_available.return_value = False
            mock_ml_provider.get_model.return_value = None
            mock_ml_provider_class.return_value = mock_ml_provider

            # Mock news provider
            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client = Mock()
                mock_news_client.get_news_for_symbol.return_value = []
                mock_news_client.fetch_news.return_value = []
                mock_news_client_class.return_value = mock_news_client

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute scoring
                ta_score, _, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                ml_score, _ = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                news_score, _ = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                risk_score, _ = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                # ML should fall back to neutral score
                assert ml_score == 50.0, f"ML should fall back to 50, got {ml_score}"

                # News should fall back to neutral score
                assert news_score == 50.0, f"News should fall back to 50, got {news_score}"

                # Create and finalize composite signal
                signal = CompositeSignal(
                    technical=ta_score,
                    ml=ml_score,
                    news=news_score,
                    risk=risk_score
                )

                signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))

                # Validate final signal
                assert 0 <= signal.final_score <= 100
                assert signal.decision in ["LONG", "SHORT", "FLAT"]
                assert signal.grade in ["A+", "A", "B", "C", "D"]

    def test_news_fallback_scenario(self, ohlcv_bundle_factory, portfolio_state, test_weights, test_thresholds):
        """Test news fallback when client is unavailable."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]

        # Compute indicators
        indicators_df = calculate_all_indicators(main_df)

        # Mock ML provider
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider = Mock()
            mock_ml_provider.is_model_available.return_value = True
            mock_ml_provider.get_model.return_value = Mock()
            mock_ml_provider_class.return_value = mock_ml_provider

            # Mock news provider with error
            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client = Mock()
                mock_news_client.get_news_for_symbol.side_effect = Exception("News API error")
                mock_news_client.fetch_news.side_effect = Exception("News API error")
                mock_news_client_class.return_value = mock_news_client

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute scoring
                ta_score, _, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                ml_score, _ = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                news_score, _ = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                risk_score, _ = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                # News should fall back to neutral score
                assert news_score == 50.0, f"News should fall back to 50, got {news_score}"

                # Create and finalize composite signal
                signal = CompositeSignal(
                    technical=ta_score,
                    ml=ml_score,
                    news=news_score,
                    risk=risk_score
                )

                signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))

                # Validate final signal
                assert 0 <= signal.final_score <= 100
                assert signal.decision in ["LONG", "SHORT", "FLAT"]
                assert signal.grade in ["A+", "A", "B", "C", "D"]

    def test_pipeline_consistency(self, ohlcv_bundle_factory, fake_ml_provider,
                                fake_news_provider, portfolio_state, test_weights, test_thresholds):
        """Test that pipeline produces consistent results."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]

        # Compute indicators
        indicators_df = calculate_all_indicators(main_df)

        # Mock providers
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider_class.return_value = fake_ml_provider

            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client_class.return_value = fake_news_provider

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute pipeline multiple times
                final_scores = []

                for _ in range(3):
                    ta_score, _, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                    ml_score, _ = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                    news_score, _ = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                    risk_score, _ = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                    signal = CompositeSignal(
                        technical=ta_score,
                        ml=ml_score,
                        news=news_score,
                        risk=risk_score
                    )

                    signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))
                    final_scores.append(signal.final_score)

                # Results should be identical (deterministic)
                assert len(set(final_scores)) == 1, f"Pipeline not deterministic: {final_scores}"

    def test_pipeline_error_handling(self, ohlcv_bundle_factory, portfolio_state, test_weights, test_thresholds):
        """Test pipeline error handling and graceful degradation."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]

        # Compute indicators
        indicators_df = calculate_all_indicators(main_df)

        # Mock providers with errors
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider = Mock()
            mock_ml_provider.is_model_available.side_effect = Exception("ML error")
            mock_ml_provider_class.return_value = mock_ml_provider

            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client = Mock()
                mock_news_client.get_news_for_symbol.side_effect = Exception("News error")
                mock_news_client_class.return_value = mock_news_client

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute scoring (should handle errors gracefully)
                ta_score, _, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                ml_score, _ = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                news_score, _ = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                risk_score, _ = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                # All scores should be valid despite errors
                assert 0 <= ta_score <= 100
                assert 0 <= ml_score <= 100
                assert 0 <= news_score <= 100
                assert 0 <= risk_score <= 100

                # Create and finalize composite signal
                signal = CompositeSignal(
                    technical=ta_score,
                    ml=ml_score,
                    news=news_score,
                    risk=risk_score
                )

                signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))

                # Final signal should be valid
                assert 0 <= signal.final_score <= 100
                assert signal.decision in ["LONG", "SHORT", "FLAT"]
                assert signal.grade in ["A+", "A", "B", "C", "D"]

    def test_single_source_of_truth(self, ohlcv_bundle_factory, fake_ml_provider,
                                   fake_news_provider, portfolio_state, test_weights, test_thresholds):
        """Test that final_score is the single source of truth for all consumers."""
        # Get synthetic data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        main_df = bundle["15m"]

        # Compute indicators
        indicators_df = calculate_all_indicators(main_df)

        # Mock providers
        with patch('scoring.ml_scorer.MLProvider') as mock_ml_provider_class:
            mock_ml_provider_class.return_value = fake_ml_provider

            with patch('scoring.news_scorer.NewsClient') as mock_news_client_class:
                mock_news_client_class.return_value = fake_news_provider

                # Initialize scorers
                ta_scorer = TAScorer()
                ml_scorer = MLScorer()
                news_scorer = NewsScorer()
                risk_scorer = RiskScorer()

                # Execute scoring
                ta_score, _, ta_flags = ta_scorer.score(indicators_df, "BTC-USDT-SWAP")
                ml_score, _ = ml_scorer.score(indicators_df, "BTC-USDT-SWAP")
                news_score, _ = news_scorer.score(indicators_df, "BTC-USDT-SWAP")
                risk_score, _ = risk_scorer.score(portfolio_state, "BTC-USDT-SWAP")

                # Create composite signal
                signal = CompositeSignal(
                    technical=ta_score,
                    ml=ml_score,
                    news=news_score,
                    risk=risk_score
                )

                signal.finalize(test_weights, test_thresholds, ta_flags.get("dir_hint", "FLAT"))

                # Test single source of truth
                final_score = signal.final_score

                # All consumers should use the same final_score
                assert signal.confidence_pct == final_score
                assert signal.decision in ["LONG", "SHORT", "FLAT"]
                assert signal.grade in ["A+", "A", "B", "C", "D"]

                # Test that final_score is accessible to downstream consumers
                summary = signal.to_dict()
                assert str(final_score) in summary, "Summary should include final_score"
                assert signal.grade in summary, "Summary should include grade"

                # Test position size calculation
                position_size = signal.position_size_multiplier
                assert isinstance(position_size, float)
                assert 0 <= position_size <= 1
