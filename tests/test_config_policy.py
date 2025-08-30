"""
Test configuration and policy validation.
"""



class TestConfigPolicy:
    """Test class for configuration and policy validation."""

    def test_policy_file_exists(self, policy):
        """Test that policy.yaml exists and can be loaded."""
        assert policy is not None
        assert isinstance(policy, dict)
        assert len(policy) > 0

    def test_timeframes_configuration(self, policy):
        """Test that required timeframe keys exist with correct values."""
        timeframes = policy.get('timeframes', {})

        # Check required timeframe keys exist
        assert 'trend_filter' in timeframes, "trend_filter missing from timeframes"
        assert 'main' in timeframes, "main missing from timeframes"
        assert 'entry_confirmation' in timeframes, "entry_confirmation missing from timeframes"

        # Check timeframe values
        assert timeframes['trend_filter'] == "1h", f"trend_filter should be '1h', got {timeframes['trend_filter']}"
        assert timeframes['main'] == "15m", f"main should be '15m', got {timeframes['main']}"
        assert timeframes['entry_confirmation'] == "5m", f"entry_confirmation should be '5m', got {timeframes['entry_confirmation']}"

    def test_scoring_weights_configuration(self, policy):
        """Test that scoring weights are correctly configured."""
        scoring = policy.get('scoring', {})
        weights = scoring.get('weights', {})

        # Check required weight keys exist
        assert 'technical' in weights, "technical weight missing from scoring.weights"
        assert 'ml' in weights, "ml weight missing from scoring.weights"
        assert 'news' in weights, "news weight missing from scoring.weights"
        assert 'risk' in weights, "risk weight missing from scoring.weights"

        # Check weight values
        assert weights['technical'] == 0.40, f"technical weight should be 0.40, got {weights['technical']}"
        assert weights['ml'] == 0.25, f"ml weight should be 0.25, got {weights['ml']}"
        assert weights['news'] == 0.20, f"news weight should be 0.20, got {weights['news']}"
        assert weights['risk'] == 0.15, f"risk weight should be 0.15, got {weights['risk']}"

        # Check weights sum to 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 1e-6, f"weights should sum to 1.0, got {total_weight}"

    def test_thresholds_configuration(self, policy):
        """Test that thresholds are correctly configured."""
        thresholds = policy.get('thresholds', {})

        # Check min_confidence_pct exists
        assert 'min_confidence_pct' in thresholds, "min_confidence_pct missing from thresholds"
        assert thresholds['min_confidence_pct'] == 60, f"min_confidence_pct should be 60, got {thresholds['min_confidence_pct']}"

        # Check grades configuration
        grades = thresholds.get('grades', {})
        assert 'Aplus' in grades, "Aplus grade missing from thresholds.grades"
        assert 'A' in grades, "A grade missing from thresholds.grades"
        assert 'B' in grades, "B grade missing from thresholds.grades"
        assert 'C' in grades, "C grade missing from thresholds.grades"

        # Check grade ranges
        assert grades['Aplus'] == [90, 100], f"Aplus grade should be [90, 100], got {grades['Aplus']}"
        assert grades['A'] == [80, 89], f"A grade should be [80, 89], got {grades['A']}"
        assert grades['B'] == [70, 79], f"B grade should be [70, 79], got {grades['B']}"
        assert grades['C'] == [60, 69], f"C grade should be [60, 69], got {grades['C']}"

    def test_news_configuration(self, policy):
        """Test that news configuration is correct."""
        news = policy.get('news', {})

        # Check lookback_minutes
        assert 'lookback_minutes' in news, "lookback_minutes missing from news"
        assert news['lookback_minutes'] == 1440, f"lookback_minutes should be 1440, got {news['lookback_minutes']}"

        # Check sources list
        assert 'sources' in news, "sources missing from news"
        sources = news['sources']
        assert isinstance(sources, list), "sources should be a list"
        assert len(sources) > 0, "sources list should not be empty"

        # Check specific sources
        expected_sources = ["cryptocompare", "coindesk", "cointelegraph"]
        for source in expected_sources:
            assert source in sources, f"Expected source '{source}' missing from sources list"

    def test_risk_limits_configuration(self, policy):
        """Test that risk limits are configured."""
        risk_limits = policy.get('risk_limits', {})

        # Check required risk limit keys exist
        assert 'max_portfolio_risk_pct' in risk_limits, "max_portfolio_risk_pct missing from risk_limits"
        assert 'max_position_risk_pct' in risk_limits, "max_position_risk_pct missing from risk_limits"
        assert 'max_drawdown_pct' in risk_limits, "max_drawdown_pct missing from risk_limits"
        assert 'max_correlation_pct' in risk_limits, "max_correlation_pct missing from risk_limits"

        # Check values are reasonable
        assert 0 < risk_limits['max_portfolio_risk_pct'] <= 100, f"max_portfolio_risk_pct should be 0-100, got {risk_limits['max_portfolio_risk_pct']}"
        assert 0 < risk_limits['max_position_risk_pct'] <= 100, f"max_position_risk_pct should be 0-100, got {risk_limits['max_position_risk_pct']}"
        assert 0 < risk_limits['max_drawdown_pct'] <= 100, f"max_drawdown_pct should be 0-100, got {risk_limits['max_drawdown_pct']}"
        assert 0 < risk_limits['max_correlation_pct'] <= 100, f"max_correlation_pct should be 0-100, got {risk_limits['max_correlation_pct']}"

    def test_trading_configuration(self, policy):
        """Test that trading configuration is correct."""
        trading = policy.get('trading', {})

        # Check required trading keys exist
        assert 'enabled' in trading, "enabled missing from trading"
        assert 'min_confidence' in trading, "min_confidence missing from trading"
        assert 'max_positions' in trading, "max_positions missing from trading"

        # Check values
        assert isinstance(trading['enabled'], bool), "trading.enabled should be boolean"
        assert 0 <= trading['min_confidence'] <= 1, f"min_confidence should be 0-1, got {trading['min_confidence']}"
        assert trading['max_positions'] > 0, f"max_positions should be > 0, got {trading['max_positions']}"

    def test_policy_structure_integrity(self, policy):
        """Test overall policy structure integrity."""
        # Check top-level sections exist
        required_sections = [
            'positions', 'risk', 'leverage', 'bias', 'streak', 'thresholds',
            'tracking', 'daily_pnl_guard', 'okx', 'notifications', 'timeframes',
            'scoring', 'news', 'risk_limits', 'trading'
        ]

        for section in required_sections:
            assert section in policy, f"Required section '{section}' missing from policy"

        # Check no empty sections
        for section, content in policy.items():
            if isinstance(content, dict):
                assert len(content) > 0, f"Section '{section}' is empty"
            elif isinstance(content, list):
                assert len(content) > 0, f"Section '{section}' list is empty"
