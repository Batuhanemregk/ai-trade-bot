"""
Test ML and news scoring fallbacks.
"""

from unittest.mock import Mock, patch

import pytest


class TestMLNewsFallbacks:
    """Test class for ML and news scoring fallbacks."""

    def test_ml_scorer_import(self):
        """Test that ML scorer can be imported."""
        try:
            from scoring.ml_scorer import MLScorer
            scorer = MLScorer()
            assert scorer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import MLScorer: {e}")

    def test_ml_scorer_initialization(self):
        """Test ML scorer initialization."""
        from scoring.ml_scorer import MLScorer

        scorer = MLScorer()
        assert hasattr(scorer, 'models_available')
        assert isinstance(scorer.models_available, bool)

    def test_ml_neutral_score_when_models_unavailable(self):
        """Test that ML scorer returns neutral score when models are unavailable."""
        from scoring.ml_scorer import MLScorer

        # Create scorer with mocked unavailable models
        with patch('scoring.ml_scorer.ml_trading_signals') as mock_ml:
            mock_ml.is_trained = False

            scorer = MLScorer()
            # Force models_available to False
            scorer.models_available = False

            # Test scoring
            score, rationale, details = scorer.score("BTC-USDT-SWAP", {})

            # Should return neutral score
            assert score == 50.0, f"Expected neutral score 50.0, got {score}"
            assert "no ML models available" in rationale.lower(), f"Rationale should mention no models: {rationale}"
            assert details['model_status'] == 'unavailable', f"Model status should be unavailable: {details['model_status']}"

    def test_ml_scoring_with_available_models(self, ohlcv_bundle_factory):
        """Test ML scoring when models are available."""
        from scoring.ml_scorer import MLScorer

        # Mock ML integration
        with patch('scoring.ml_scorer.ml_trading_signals') as mock_ml:
            mock_ml.is_trained = True
            mock_ml.predict.return_value = {
                'score': 75.0,
                'confidence': 0.8,
                'direction': 'LONG'
            }

            scorer = MLScorer()
            scorer.models_available = True

            bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 50000, 0.02)
            score, rationale, details = scorer.score("BTC-USDT-SWAP", bundle)

            # Score should be higher than neutral
            assert score > 50.0, f"ML score should be > 50 when models available, got {score}"
            assert details['model_status'] == 'available', f"Model status should be available: {details['model_status']}"

    def test_ml_scoring_consistency(self, ohlcv_bundle_factory):
        """Test that ML scoring produces consistent results for same data."""
        from scoring.ml_scorer import MLScorer

        with patch('scoring.ml_scorer.ml_trading_signals') as mock_ml:
            mock_ml.is_trained = True
            mock_ml.predict.return_value = {
                'score': 75.0,
                'confidence': 0.8,
                'direction': 'LONG'
            }

            scorer = MLScorer()
            scorer.models_available = True
            bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 50000, 0.02)

            # Score same data multiple times
            scores = []
            for _ in range(3):
                score, _, _ = scorer.score("BTC-USDT-SWAP", bundle)
                scores.append(score)

            # Scores should be identical (deterministic)
            assert len(set(scores)) == 1, f"ML scoring not deterministic: {scores}"

    def test_news_scorer_import(self):
        """Test that news scorer can be imported."""
        try:
            from scoring.news_scorer import NewsScorer
            scorer = NewsScorer()
            assert scorer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import NewsScorer: {e}")

    def test_news_scorer_initialization(self):
        """Test news scorer initialization."""
        from scoring.news_scorer import NewsScorer

        scorer = NewsScorer()
        assert hasattr(scorer, 'news_client')
        assert hasattr(scorer, 'sentiment_keywords')
        assert isinstance(scorer.sentiment_keywords, dict)

    def test_news_neutral_score_when_client_unavailable(self):
        """Test that news scorer returns neutral score when client is unavailable."""
        from scoring.news_scorer import NewsScorer

        # Create scorer with mocked unavailable client
        with patch('scoring.news_scorer.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Client unavailable")

            scorer = NewsScorer()
            # Force news_client to None
            scorer.news_client = None

            # Test scoring
            score, categories, rationale, volatility_impact = scorer.score("BTC-USDT-SWAP")

            # Should return neutral score
            assert score == 50.0, f"Expected neutral score 50.0, got {score}"
            assert "general" in categories, f"Should have general category: {categories}"
            assert volatility_impact == 0.5, f"Expected neutral volatility impact 0.5, got {volatility_impact}"

    def test_news_scoring_with_positive_news(self):
        """Test news scoring with positive news."""
        from scoring.news_scorer import NewsScorer

        # Mock news client with positive news
        mock_client = Mock()
        mock_client.get_news.return_value = [
            {
                "title": "Bitcoin adoption surges in institutional markets",
                "summary": "Major banks announce Bitcoin trading services",
                "sentiment": "positive",
                "category": "ADOPTION"
            }
        ]

        with patch('scoring.news_scorer.get_client', return_value=mock_client):
            scorer = NewsScorer()
            scorer.news_client = mock_client

            score, categories, rationale, volatility_impact = scorer.score("BTC-USDT-SWAP")

            # Score should be higher than neutral
            assert score > 50.0, f"News score should be > 50 with positive news, got {score}"
            assert "ADOPTION" in categories, f"Should have ADOPTION category: {categories}"
            assert volatility_impact > 0.5, f"Volatility impact should be > 0.5 with positive news: {volatility_impact}"

    def test_news_scoring_with_negative_news(self):
        """Test news scoring with negative news."""
        from scoring.news_scorer import NewsScorer

        # Mock news client with negative news
        mock_client = Mock()
        mock_client.get_news.return_value = [
            {
                "title": "Regulatory concerns mount in crypto markets",
                "summary": "New restrictions proposed by financial authorities",
                "sentiment": "negative",
                "category": "REGULATION"
            }
        ]

        with patch('scoring.news_scorer.get_client', return_value=mock_client):
            scorer = NewsScorer()
            scorer.news_client = mock_client

            score, categories, rationale, volatility_impact = scorer.score("BTC-USDT-SWAP")

            # Score should be lower than neutral
            assert score < 50.0, f"News score should be < 50 with negative news, got {score}"
            assert "REGULATION" in categories, f"Should have REGULATION category: {categories}"
            assert volatility_impact > 0.5, f"Volatility impact should be > 0.5 with negative news: {volatility_impact}"

    def test_news_scoring_with_empty_news(self):
        """Test news scoring when no news is available."""
        from scoring.news_scorer import NewsScorer

        # Mock news client with empty news
        mock_client = Mock()
        mock_client.get_news.return_value = []

        with patch('scoring.news_scorer.get_client', return_value=mock_client):
            scorer = NewsScorer()
            scorer.news_client = mock_client

            score, categories, rationale, volatility_impact = scorer.score("BTC-USDT-SWAP")

            # Should return neutral score
            assert score == 50.0, f"Expected neutral score 50.0 with no news, got {score}"
            assert "general" in categories, f"Should have general category: {categories}"
            assert volatility_impact == 0.5, f"Expected neutral volatility impact 0.5, got {volatility_impact}"

    def test_news_sentiment_keywords(self):
        """Test that sentiment keywords are properly configured."""
        from scoring.news_scorer import NewsScorer

        scorer = NewsScorer()

        # Check required categories exist
        required_categories = ['SECURITY', 'REGULATION', 'ADOPTION', 'TECHNOLOGY', 'MARKET']
        for category in required_categories:
            assert category in scorer.sentiment_keywords, f"Category {category} missing from sentiment keywords"
            assert 'positive' in scorer.sentiment_keywords[category], f"Positive keywords missing for {category}"
            assert 'negative' in scorer.sentiment_keywords[category], f"Negative keywords missing for {category}"
            assert len(scorer.sentiment_keywords[category]['positive']) > 0, f"No positive keywords for {category}"
            assert len(scorer.sentiment_keywords[category]['negative']) > 0, f"No negative keywords for {category}"

    def test_news_scoring_consistency(self):
        """Test that news scoring produces consistent results for same input."""
        from scoring.news_scorer import NewsScorer

        # Mock news client with fixed news
        mock_client = Mock()
        fixed_news = [
            {
                "title": "Test news",
                "summary": "Test summary",
                "sentiment": "positive",
                "category": "TECHNOLOGY"
            }
        ]
        mock_client.get_news.return_value = fixed_news

        with patch('scoring.news_scorer.get_client', return_value=mock_client):
            scorer = NewsScorer()
            scorer.news_client = mock_client

            # Score same news multiple times
            scores = []
            for _ in range(3):
                score, _, _, _ = scorer.score("BTC-USDT-SWAP")
                scores.append(score)

            # Scores should be identical (deterministic)
            assert len(set(scores)) == 1, f"News scoring not deterministic: {scores}"

    def test_ml_news_integration_fallbacks(self, ohlcv_bundle_factory):
        """Test that ML and news fallbacks work together in integration."""
        from scoring.ml_scorer import MLScorer
        from scoring.news_scorer import NewsScorer

        # Test ML unavailable + news available
        with patch('scoring.ml_scorer.ml_trading_signals') as mock_ml:
            mock_ml.is_trained = False

            ml_scorer = MLScorer()
            ml_scorer.models_available = False

            ml_score, ml_rationale, ml_details = ml_scorer.score("BTC-USDT-SWAP", ohlcv_bundle_factory())

            # ML should be neutral
            assert ml_score == 50.0, f"ML should be neutral when unavailable: {ml_score}"

        # Test news unavailable + ML available
        with patch('scoring.news_scorer.get_client') as mock_news:
            mock_news.side_effect = Exception("News unavailable")

            news_scorer = NewsScorer()
            news_scorer.news_client = None

            news_score, news_categories, news_rationale, news_volatility = news_scorer.score("BTC-USDT-SWAP")

            # News should be neutral
            assert news_score == 50.0, f"News should be neutral when unavailable: {news_score}"
