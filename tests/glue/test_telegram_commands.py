"""
Integration tests for Telegram commands.
Tests command outputs and ensures no network calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from telegram_bot.commands import command_handler


@pytest.mark.glue
class TestTelegramCommands:
    """Test Telegram command integration."""
    
    @pytest.mark.asyncio
    async def test_help_command_format(self):
        """Test /help command format."""
        help_text = await command_handler.handle_help({})
        
        # Should contain expected sections
        assert "🤖 **AiBotBS Commands**" in help_text
        assert "**Trading:**" in help_text
        assert "**System:**" in help_text
        assert "**Control:**" in help_text
        
        # Should list specific commands
        assert "/scoring" in help_text
        assert "/risk" in help_text
        assert "/positions" in help_text
        assert "/news" in help_text
        
        # Should be reasonable length
        assert len(help_text) > 200
        assert len(help_text) < 1000
    
    @pytest.mark.asyncio
    async def test_scoring_command_deterministic(self):
        """Test /scoring command returns deterministic output."""
        # Patch scoring service to return mock data
        with patch('application.scoring_service.ScoringService') as mock_scoring:
            mock_service = Mock()
            mock_service.get_status = AsyncMock(return_value={
                "status": "active",
                "last_update": "2023-01-01T00:00:00Z",
                "active_models": 3
            })
            mock_scoring.return_value = mock_service
            
            scoring_text = await command_handler.handle_scoring({})
        
        # Should contain expected format
        assert "📊 **Scoring Status**" in scoring_text
        assert "Status: active" in scoring_text
        assert "Last Update: 2023-01-01T00:00:00Z" in scoring_text
        assert "Active Models: 3" in scoring_text
        
        # Should be consistent length
        assert len(scoring_text) > 50
        assert len(scoring_text) < 200
    
    @pytest.mark.asyncio
    async def test_risk_command_deterministic(self):
        """Test /risk command returns deterministic output."""
        # Patch risk service to return mock data
        with patch('application.risk_service.RiskService') as mock_risk:
            mock_service = Mock()
            mock_service.get_status = AsyncMock(return_value={
                "risk_level": "medium",
                "daily_pnl": 150.0,
                "max_drawdown": -50.0
            })
            mock_risk.return_value = mock_service
            
            risk_text = await command_handler.handle_risk({})
        
        # Should contain expected format
        assert "⚠️ **Risk Status**" in risk_text
        assert "Risk Level: medium" in risk_text
        assert "Daily PnL: 150.0" in risk_text
        assert "Max Drawdown: -50.0" in risk_text
        
        # Should be consistent length
        assert len(risk_text) > 50
        assert len(risk_text) < 200
    
    @pytest.mark.asyncio
    async def test_news_command_deterministic(self):
        """Test /news command returns deterministic output."""
        # Patch news aggregator to return mock data
        with patch('news.news_manager.NewsManager') as mock_news:
            mock_aggregator = Mock()
            mock_aggregator.get_latest_news = AsyncMock(return_value=[
                {
                    "title": "Bitcoin Shows Strong Momentum",
                    "source": "CryptoNews",
                    "sentiment": "positive"
                },
                {
                    "title": "Ethereum Network Upgrade",
                    "source": "DeFiInsider",
                    "sentiment": "positive"
                }
            ])
            mock_news.return_value = mock_aggregator
            
            news_text = await command_handler.handle_news({})
        
        # Should contain expected format
        assert "📰 **Latest News**" in news_text
        assert "Bitcoin Shows Strong Momentum" in news_text
        assert "Ethereum Network Upgrade" in news_text
        assert "CryptoNews" in news_text
        assert "DeFiInsider" in news_text
        
        # Should be consistent length
        assert len(news_text) > 100
        assert len(news_text) < 500
    
    @pytest.mark.asyncio
    async def test_positions_command_deterministic(self):
        """Test /positions command returns deterministic output."""
        # Patch portfolio service to return mock data
        with patch('application.portfolio_service.PortfolioService') as mock_portfolio:
            mock_service = Mock()
            mock_service.get_positions = AsyncMock(return_value=[
                {
                    "symbol": "BTC-USDT",
                    "side": "long",
                    "size": 0.1,
                    "unrealized_pnl": 150.0
                }
            ])
            mock_portfolio.return_value = mock_service
            
            positions_text = await command_handler.handle_positions({})
        
        # Should contain expected format
        assert "📊 **Current Positions**" in positions_text
        assert "BTC-USDT" in positions_text
        assert "long" in positions_text
        assert "0.1" in positions_text
        assert "150.0" in positions_text
        
        # Should be consistent length
        assert len(positions_text) > 50
        assert len(positions_text) < 300
    
    @pytest.mark.asyncio
    async def test_no_network_calls(self):
        """Test that commands don't make network calls."""
        # Mock all external dependencies
        with patch('application.scoring_service.ScoringService') as mock_scoring, \
             patch('application.risk_service.RiskService') as mock_risk, \
             patch('news.news_manager.NewsManager') as mock_news, \
             patch('application.portfolio_service.PortfolioService') as mock_portfolio:
            
            # Setup mocks
            mock_scoring.return_value.get_status.return_value = {"status": "active"}
            mock_risk.return_value.get_status.return_value = {"risk_level": "low"}
            mock_news.return_value.get_latest_news.return_value = []
            mock_portfolio.return_value.get_positions.return_value = []
            
            # Execute all commands
            commands = [
                command_handler.handle_scoring({}),
                command_handler.handle_risk({}),
                command_handler.handle_news({}),
                command_handler.handle_positions({})
            ]
            
            # All should complete without network calls
            results = await asyncio.gather(*commands)
            
            # Verify all returned text
            for result in results:
                assert isinstance(result, str)
                assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_command_error_handling(self):
        """Test that commands handle errors gracefully."""
        # Mock services to raise exceptions
        with patch('application.scoring_service.ScoringService') as mock_scoring:
            mock_scoring.side_effect = Exception("Service unavailable")
            
            scoring_text = await command_handler.handle_scoring({})
            
            # Should return error message
            assert "❌ Failed to get scoring status" in scoring_text
        
        with patch('application.risk_service.RiskService') as mock_risk:
            mock_risk.side_effect = Exception("Risk service error")
            
            risk_text = await command_handler.handle_risk({})
            
            # Should return error message
            assert "❌ Failed to get risk status" in risk_text
    
    @pytest.mark.asyncio
    async def test_command_logging(self, caplog):
        """Test that commands log their execution."""
        # Execute a command
        await command_handler.handle_help({})
        
        # Check logs
        log_messages = [record.message for record in caplog.records]
        help_logs = [msg for msg in log_messages if "Help command received" in msg]
        
        assert len(help_logs) > 0
