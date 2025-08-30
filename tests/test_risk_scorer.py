"""
Test risk scoring functionality.
"""

from unittest.mock import patch

import pytest


class TestRiskScorer:
    """Test class for risk scoring."""

    def test_risk_scorer_import(self):
        """Test that risk scorer can be imported."""
        try:
            from scoring.risk_scorer import RiskScorer
            scorer = RiskScorer()
            assert scorer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import RiskScorer: {e}")

    def test_risk_scorer_initialization(self):
        """Test risk scorer initialization."""
        from scoring.risk_scorer import RiskScorer

        scorer = RiskScorer()
        assert hasattr(scorer, 'risk_manager')
        assert hasattr(scorer, 'policy')

    def test_risk_scoring_with_portfolio_state(self, portfolio_state):
        """Test risk scoring with dummy portfolio state."""
        from scoring.risk_scorer import RiskScorer

        # Mock risk manager and policy
        with patch('scoring.risk_scorer.risk_manager') as mock_risk_manager, \
             patch('scoring.risk_scorer.load_policy') as mock_load_policy:

            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            score, details = scorer.score("BTC-USDT-SWAP", portfolio_state)

            # Check return types
            assert isinstance(score, (int, float))
            assert isinstance(details, dict)

            # Check score range
            assert 0 <= score <= 100, f"Risk score {score} not in [0, 100] range"

            # Check details structure
            assert 'risk_score' in details
            assert 'penalties' in details
            assert 'risk_limits' in details
            assert 'portfolio_state' in details
            assert 'risk_level' in details

            # Check risk level
            assert details['risk_level'] in ['low', 'medium', 'high'], f"Invalid risk level: {details['risk_level']}"

    def test_risk_scoring_without_policy(self):
        """Test risk scoring when policy is not available."""
        from scoring.risk_scorer import RiskScorer

        # Mock failed policy loading
        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.side_effect = Exception("Policy not available")

            scorer = RiskScorer()
            scorer.policy = None

            portfolio_state = {"total_exposure": 0.1}
            score, details = scorer.score("BTC-USDT-SWAP", portfolio_state)

            # Should return neutral score
            assert score == 50.0, f"Expected neutral score 50.0 when no policy, got {score}"

    def test_risk_penalties_calculation(self, portfolio_state):
        """Test that risk penalties are calculated correctly."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            score, details = scorer.score("BTC-USDT-SWAP", portfolio_state)

            # Check that penalties are applied
            penalties = details.get('penalties', [])
            assert len(penalties) > 0, "Should have some risk penalties"

            # Check penalty descriptions
            for penalty in penalties:
                assert isinstance(penalty, str), f"Penalty should be string: {penalty}"
                assert ":" in penalty, f"Penalty should have format 'Type: -Value': {penalty}"
                assert penalty.startswith(("Portfolio risk:", "Position concentration:", "Drawdown limit:", "Correlation risk:", "Margin utilization:"))

    def test_portfolio_risk_penalty(self, portfolio_state):
        """Test portfolio risk penalty calculation."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Test with high portfolio exposure
            high_exposure_state = portfolio_state.copy()
            high_exposure_state['total_exposure'] = 0.20  # 20% exposure

            score, details = scorer.score("BTC-USDT-SWAP", high_exposure_state)

            # Score should be lower due to high exposure
            assert score < 100, f"Score should be < 100 with high exposure, got {score}"

            # Check for portfolio risk penalty
            penalties = details.get('penalties', [])
            portfolio_penalties = [p for p in penalties if p.startswith("Portfolio risk:")]
            assert len(portfolio_penalties) > 0, "Should have portfolio risk penalty"

    def test_correlation_risk_penalty(self, portfolio_state):
        """Test correlation risk penalty calculation."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Test with high correlation
            high_corr_state = portfolio_state.copy()
            high_corr_state['correlation'] = 0.90  # 90% correlation

            score, details = scorer.score("BTC-USDT-SWAP", high_corr_state)

            # Score should be lower due to high correlation
            assert score < 100, f"Score should be < 100 with high correlation, got {score}"

            # Check for correlation risk penalty
            penalties = details.get('penalties', [])
            correlation_penalties = [p for p in penalties if p.startswith("Correlation risk:")]
            assert len(correlation_penalties) > 0, "Should have correlation risk penalty"

    def test_drawdown_risk_penalty(self, portfolio_state):
        """Test drawdown risk penalty calculation."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Test with high drawdown
            high_dd_state = portfolio_state.copy()
            high_dd_state['drawdown'] = -0.20  # -20% drawdown

            score, details = scorer.score("BTC-USDT-SWAP", high_dd_state)

            # Score should be lower due to high drawdown
            assert score < 100, f"Score should be < 100 with high drawdown, got {score}"

            # Check for drawdown penalty
            penalties = details.get('penalties', [])
            drawdown_penalties = [p for p in penalties if p.startswith("Drawdown limit:")]
            assert len(drawdown_penalties) > 0, "Should have drawdown penalty"

    def test_risk_score_bounds(self, portfolio_state):
        """Test that risk score stays within bounds."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Test with extreme risk values
            extreme_state = portfolio_state.copy()
            extreme_state.update({
                'total_exposure': 1.0,      # 100% exposure
                'correlation': 0.99,         # 99% correlation
                'drawdown': -0.50,           # -50% drawdown
                'margin_utilization': 0.95   # 95% margin used
            })

            score, details = scorer.score("BTC-USDT-SWAP", extreme_state)

            # Score should still be within bounds
            assert 0 <= score <= 100, f"Risk score {score} not in [0, 100] range"

            # Score should be very low
            assert score < 30, f"Extreme risk should result in very low score, got {score}"

    def test_risk_scoring_consistency(self, portfolio_state):
        """Test that risk scoring produces consistent results for same input."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Score same portfolio state multiple times
            scores = []
            for _ in range(3):
                score, _ = scorer.score("BTC-USDT-SWAP", portfolio_state)
                scores.append(score)

            # Scores should be identical (deterministic)
            assert len(set(scores)) == 1, f"Risk scoring not deterministic: {scores}"

    def test_risk_level_classification(self, portfolio_state):
        """Test that risk levels are classified correctly."""
        from scoring.risk_scorer import RiskScorer

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Test different risk scenarios
            test_cases = [
                ({"total_exposure": 0.02, "correlation": 0.30, "drawdown": -0.02}, "low"),
                ({"total_exposure": 0.10, "correlation": 0.60, "drawdown": -0.08}, "medium"),
                ({"total_exposure": 0.25, "correlation": 0.85, "drawdown": -0.20}, "high")
            ]

            for state_updates, expected_level in test_cases:
                test_state = portfolio_state.copy()
                test_state.update(state_updates)

                score, details = scorer.score("BTC-USDT-SWAP", test_state)
                actual_level = details.get('risk_level')

                assert actual_level == expected_level, f"Expected risk level {expected_level}, got {actual_level} for state {state_updates}"

    def test_risk_scorer_error_handling(self):
        """Test that risk scorer handles errors gracefully."""
        from scoring.risk_scorer import RiskScorer

        # Test with invalid portfolio state
        invalid_state = {"invalid_key": "invalid_value"}

        with patch('scoring.risk_scorer.load_policy') as mock_load_policy:
            mock_load_policy.return_value = {
                'risk_limits': {
                    'max_portfolio_risk_pct': 5,
                    'max_position_risk_pct': 2,
                    'max_drawdown_pct': 15,
                    'max_correlation_pct': 80
                }
            }

            scorer = RiskScorer()
            scorer.policy = mock_load_policy.return_value

            # Should not raise exception
            try:
                score, details = scorer.score("BTC-USDT-SWAP", invalid_state)
                assert 0 <= score <= 100, f"Score should be in valid range: {score}"
            except Exception as e:
                pytest.fail(f"Risk scorer should handle invalid state gracefully: {e}")
