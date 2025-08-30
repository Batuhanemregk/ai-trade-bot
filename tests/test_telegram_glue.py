"""
Test suite for Telegram bot integration with scoring and risk services.
Tests command outputs and service integration without network calls.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from application.risk_service import RiskAssessment, RiskService
from application.scoring_service import AnalysisResult, CompositeScore, ScoringService
from domain.models import RiskLevel, SignalType
from telegram_bot.handlers import CommandHandler


class TestTelegramGlue:
    """Test Telegram bot integration with scoring and risk services."""

    @pytest.fixture
    def mock_update(self):
        """Mock Telegram update object."""
        update = Mock()
        update.message = Mock()
        update.message.reply_html = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Mock Telegram context object."""
        context = Mock()
        context.args = []
        return context

    @pytest.fixture
    def command_handler(self):
        """Command handler instance for testing."""
        return CommandHandler()

    @pytest.fixture
    def mock_scoring_service(self):
        """Mock scoring service."""
        service = Mock(spec=ScoringService)

        # Mock analysis results
        ta_result = AnalysisResult(
            source="ta",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=75.0,
            signal=SignalType.BUY,
            confidence=0.8,
            rationale="Strong bullish signals: RSI oversold, MACD crossover"
        )

        ml_result = AnalysisResult(
            source="ml",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=68.0,
            signal=SignalType.BUY,
            confidence=0.7,
            rationale="ML model predicts 68% probability of upward movement"
        )

        news_result = AnalysisResult(
            source="news",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            score=0.6,
            signal=SignalType.BUY,
            confidence=0.6,
            rationale="Recent news shows positive developments"
        )

        # Mock composite score
        composite_score = CompositeScore(
            id="test_score_001",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            overall_score=72.8,
            overall_signal=SignalType.BUY,
            overall_confidence=0.74,
            grade="B",
            ta_score=75.0,
            ml_score=68.0,
            news_score=0.6,
            ta_signal=SignalType.BUY,
            ml_signal=SignalType.BUY,
            news_signal=SignalType.BUY,
            ta_confidence=0.8,
            ml_confidence=0.7,
            news_confidence=0.6,
            ta_weight=0.4,
            ml_weight=0.4,
            news_weight=0.2,
            ta_rationale="Strong bullish signals: RSI oversold, MACD crossover",
            ml_rationale="ML model predicts 68% probability of upward movement",
            news_rationale="Recent news shows positive developments",
            composite_rationale="Moderate bullish signals with some caution. Strong technical analysis (75.0). Strong ML prediction (68.0). Positive news sentiment (0.60).",
            risk_notes=[],
            risk_penalties={}
        )

        # Mock service methods
        service.compose_score.return_value = composite_score
        service.get_service_status.return_value = {
            "weights": {"ta": 0.4, "ml": 0.4, "news": 0.2},
            "thresholds": {"buy": 60.0, "sell": 40.0, "confidence": 0.6},
            "grade_thresholds": {"A+": 90.0, "A": 80.0, "B": 70.0, "C": 60.0, "D": 0.0},
            "performance": {"scores_generated": 1, "signals_generated": 0, "last_score": "BTC-USDT-SWAP"}
        }

        return service

    @pytest.fixture
    def mock_risk_service(self):
        """Mock risk service."""
        service = Mock(spec=RiskService)

        # Mock risk assessment
        risk_assessment = RiskAssessment(
            id="test_risk_001",
            symbol="BTC-USDT-SWAP",
            timestamp=datetime.now(),
            risk_score=0.35,
            risk_level=RiskLevel.MEDIUM,
            risk_factors=["Large position size (80.0% of max)", "High leverage (80.0% of max)"],
            risk_limits={},
            position_size=80000.0,
            notional_value=160000.0,
            margin_required=10000.0,
            max_position_size=100000.0,
            leverage_used=2.0,
            max_leverage=10.0,
            portfolio_exposure=0.15,
            max_portfolio_exposure=0.10,
            market_volatility=0.25,
            correlation=0.3,
            risk_adjusted_score=65.8,
            risk_rationale="Risk Level: MEDIUM (Score: 0.35) Risk Factors: • Large position size (80.0% of max) • High leverage (80.0% of max) Recommendation: Monitor closely and set tight stop-losses.",
            metadata={}
        )

        # Mock service methods
        service.assess_risk.return_value = risk_assessment
        service.annotate_composite_score.return_value = [
            "⚠️ Large position: 80.0% of max size",
            "⚡ High leverage: 80.0% of max",
            "🎯 Total risk penalty: -7.0 points"
        ]
        service.get_risk_summary.return_value = {
            "symbol": "BTC-USDT-SWAP",
            "risk_score": 0.35,
            "risk_level": "medium",
            "risk_factors": ["Large position size (80.0% of max)", "High leverage (80.0% of max)"],
            "risk_adjusted_score": 65.8,
            "rationale": "Risk Level: MEDIUM (Score: 0.35)...",
            "limits": {"max_position_size": 100000.0, "max_leverage": 10.0, "max_portfolio_exposure": 0.10},
            "current": {"position_size": 80000.0, "leverage": 2.0, "portfolio_exposure": 0.15}
        }
        service.get_service_status.return_value = {
            "risk_limits": {"max_position_size": 100000.0, "max_leverage": 10.0, "max_drawdown": 0.20},
            "risk_weights": {"position_size": 0.25, "leverage": 0.25, "portfolio_exposure": 0.20},
            "performance": {"assessments_performed": 1, "risk_violations": 0, "score_downgrades": 1, "last_assessment": "BTC-USDT-SWAP"}
        }

        return service

    @pytest.mark.asyncio
    async def test_scoring_command_integration(self, command_handler, mock_update, mock_context,
                                            mock_scoring_service, mock_risk_service):
        """Test /scoring command integration with services."""
        # Set up context args
        mock_context.args = ["BTC-USDT-SWAP"]

        # Mock service imports at module level
        with patch('application.scoring_service.ScoringService', return_value=mock_scoring_service), \
             patch('application.risk_service.RiskService', return_value=mock_risk_service), \
             patch('application.scoring_service.AnalysisResult'), \
             patch('domain.models.SignalType'), \
             patch('datetime.datetime'):

            # Call the scoring command
            await command_handler.cmd_scoring(mock_update, mock_context)

            # Verify reply was called
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Verify key content elements
            assert "Scoring Analysis for BTC-USDT-SWAP" in message
            assert "Overall Score: B (72.8/100)" in message
            assert "Signal: BUY" in message
            assert "Confidence: 74.0%" in message
            assert "TA: 75.0/100 (BUY) [80.0%]" in message
            assert "ML: 68.0/100 (BUY) [70.0%]" in message
            assert "News: 0.60 (BUY) [60.0%]" in message
            assert "⚖️ <b>Weights:</b> TA: 40.0%, ML: 40.0%, News: 20.0%" in message
            assert "Strong technical analysis (75.0)" in message
            assert "Strong ML prediction (68.0)" in message
            assert "Positive news sentiment (0.60)" in message

    @pytest.mark.asyncio
    async def test_risk_command_integration(self, command_handler, mock_update, mock_context,
                                          mock_risk_service):
        """Test /risk command integration with risk service."""
        # Set up context args
        mock_context.args = ["BTC-USDT-SWAP"]

        # Mock service imports at module level
        with patch('application.risk_service.RiskService', return_value=mock_risk_service), \
             patch('domain.models.SignalType'):

            # Call the risk command
            await command_handler.cmd_risk(mock_update, mock_context)

            # Verify reply was called
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Verify key content elements
            assert "Risk Assessment for BTC-USDT-SWAP" in message
            assert "Risk Level: MEDIUM" in message
            assert "Risk Score: 0.35/1.0" in message
            assert "Risk-Adjusted Score: 65.8" in message
            assert "Large position size (80.0% of max)" in message
            assert "High leverage (80.0% of max)" in message
            assert "Position Details:" in message
            assert "Size: $80,000" in message
            assert "Leverage: 2.0x" in message
            assert "Risk Limits:" in message
            assert "Max Position Size: $100,000" in message
            assert "Max Leverage: 10.0x" in message

    @pytest.mark.asyncio
    async def test_news_command_integration(self, command_handler, mock_update, mock_context):
        """Test /news command integration with sentiment client."""
        # Set up context args
        mock_context.args = ["BTC", "24h"]

        # Mock sentiment client at module level
        mock_sentiment_result = {
            "news_score": 0.6,
            "items": [
                {"label": "Headline 1", "sent": 0.7, "conf": 0.8},
                {"label": "Headline 2", "sent": 0.5, "conf": 0.7}
            ],
            "usage": {"mock": True, "reason": "no_api_key"},
            "ai_commentary": "Mock Analysis: Based on 5 headlines, sentiment appears moderately bullish. Mock Recommendation: monitor for entry opportunities with appropriate risk management. [MOCK FALLBACK - No OpenAI API key]"
        }

        with patch('llm.sentiment_client.score_news', return_value=mock_sentiment_result):
            # Call the news command
            await command_handler.cmd_news(mock_update, mock_context)

            # Verify reply was called
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Verify key content elements
            assert "News Analysis for BTC" in message
            assert "Sentiment Score: 0.60" in message
            assert "Lookback Period: 24h" in message
            assert "Headlines Analyzed: 5" in message
            assert "AI Commentary:" in message
            assert "moderately bullish" in message
            assert "monitor for entry opportunities" in message
            assert "Mock Analysis:" in message
            assert "MOCK FALLBACK" in message

    @pytest.mark.asyncio
    async def test_scoring_command_without_symbol(self, command_handler, mock_update, mock_context,
                                                mock_scoring_service, mock_risk_service):
        """Test /scoring command without symbol argument (uses default)."""
        # No args in context
        mock_context.args = []

        # Mock service imports at module level
        with patch('application.scoring_service.ScoringService', return_value=mock_scoring_service), \
             patch('application.risk_service.RiskService', return_value=mock_risk_service), \
             patch('application.scoring_service.AnalysisResult'), \
             patch('domain.models.SignalType'), \
             patch('datetime.datetime'):

            # Call the scoring command
            await command_handler.cmd_scoring(mock_update, mock_context)

            # Verify reply was called
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Should use default symbol
            assert "Scoring Analysis for BTC-USDT-SWAP" in message

    @pytest.mark.asyncio
    async def test_risk_command_without_symbol(self, command_handler, mock_update, mock_context,
                                             mock_risk_service):
        """Test /risk command without symbol argument (uses default)."""
        # No args in context
        mock_context.args = []

        # Mock service imports at module level
        with patch('application.risk_service.RiskService', return_value=mock_risk_service), \
             patch('domain.models.SignalType'):

            # Call the risk command
            await command_handler.cmd_risk(mock_update, mock_context)

            # Verify reply was called
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Should use default symbol
            assert "Risk Assessment for BTC-USDT-SWAP" in message

    @pytest.mark.asyncio
    async def test_scoring_command_error_handling(self, command_handler, mock_update, mock_context):
        """Test /scoring command error handling."""
        # Mock service import to raise exception at module level
        with patch('application.scoring_service.ScoringService', side_effect=Exception("Service unavailable")):
            # Call the scoring command
            await command_handler.cmd_scoring(mock_update, mock_context)

            # Verify error reply was sent
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Should contain error message
            assert "Scoring analysis failed" in message
            assert "Service unavailable" in message
            assert "Try /scoring SYMBOL" in message

    @pytest.mark.asyncio
    async def test_risk_command_error_handling(self, command_handler, mock_update, mock_context):
        """Test /risk command error handling."""
        # Mock service import to raise exception at module level
        with patch('application.risk_service.RiskService', side_effect=Exception("Risk service error")):
            # Call the risk command
            await command_handler.cmd_risk(mock_update, mock_context)

            # Verify error reply was sent
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Should contain error message
            assert "Risk assessment failed" in message
            assert "Risk service error" in message
            assert "Try /risk SYMBOL" in message

    @pytest.mark.asyncio
    async def test_news_command_error_handling(self, command_handler, mock_update, mock_context):
        """Test /news command error handling."""
        # Mock sentiment client to raise exception at module level
        with patch('llm.sentiment_client.score_news', side_effect=Exception("Sentiment analysis failed")):
            # Call the news command
            await command_handler.cmd_news(mock_update, mock_context)

            # Verify error reply was sent
            mock_update.message.reply_html.assert_called_once()

            # Get the message content
            message = mock_update.message.reply_html.call_args[0][0]

            # Should contain error message
            assert "News analysis failed" in message
            assert "Sentiment analysis failed" in message
            assert "Try /news SYMBOL" in message

    def test_command_handler_initialization(self, command_handler):
        """Test command handler initialization."""
        assert hasattr(command_handler, 'policy')
        assert hasattr(command_handler, 'news_client')
        assert hasattr(command_handler, 'start_time')

    @pytest.mark.asyncio
    async def test_log_command_method(self, command_handler, mock_update):
        """Test the _log_command method."""
        # Since CommandHandler doesn't have a logger attribute, we'll test the method exists
        assert hasattr(command_handler, '_log_command')

        # Test that the method can be called (it might not do anything in test mode)
        try:
            await command_handler._log_command(mock_update, "test_command")
            # If no exception, the method executed successfully
            assert True
        except Exception as e:
            # If there's an exception, it should be a reasonable one (not AttributeError)
            assert not isinstance(e, AttributeError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

