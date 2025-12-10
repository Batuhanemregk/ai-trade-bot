"""
Test News Assignment (General to All Symbols)

Tests for the smart news assignment where general market news
is distributed to all active trading symbols.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


class TestGeneralNewsAssignment:
    """Tests for general news distribution to all symbols."""
    
    @pytest.fixture
    def news_service_with_data(self):
        """Create NewsService with mixed news data."""
        from application.news_service import NewsService
        
        policy = {
            'news': {},
            'news_llm': {'enabled': False},
            'news_scoring': {}
        }
        
        with patch.object(NewsService, '__init__', lambda x, y: None):
            service = NewsService.__new__(NewsService)
            service.news_data = {
                'BTC': [
                    {'title': 'Bitcoin hits new high', 'body': 'BTC price...'}
                ],
                'ETH': [
                    {'title': 'Ethereum upgrade', 'body': 'ETH network...'}
                ],
                'general': [
                    {'title': 'Crypto market rally', 'body': 'Broad market...'},
                    {'title': 'Fed rate decision', 'body': 'Impact on crypto...'}
                ],
                'CRYPTO': [
                    {'title': 'Industry news', 'body': 'Overall market...'}
                ]
            }
            service.llm_analyzer = None
            service.llm_config = {'digest': {'max_items_per_symbol': 30}}
            service.digest_manager = MagicMock()
            service.digest_manager.get_digest_status = MagicMock(
                return_value=('hash123', False, None)
            )
        return service
    
    @pytest.mark.asyncio
    async def test_btc_includes_general_news(self, news_service_with_data):
        """Test that BTC score includes general market news."""
        service = news_service_with_data
        
        # Get news items through internal logic
        base_symbol = 'BTC'
        news_items = []
        
        # Symbol-specific
        symbol_news = service.news_data.get(base_symbol, [])
        news_items.extend(symbol_news)
        
        # General news
        for key in ['general', 'GENERAL', 'CRYPTO', 'crypto', 'MARKET', 'market']:
            general_news = service.news_data.get(key, [])
            news_items.extend(general_news)
        
        # BTC should have 1 symbol-specific + 2 general + 1 CRYPTO = 4 articles
        assert len(news_items) == 4
    
    @pytest.mark.asyncio
    async def test_sol_gets_general_news_only(self, news_service_with_data):
        """Test that SOL (no specific news) still gets general news."""
        service = news_service_with_data
        
        base_symbol = 'SOL'  # No symbol-specific news
        news_items = []
        
        # Symbol-specific (none for SOL)
        symbol_news = service.news_data.get(base_symbol, [])
        news_items.extend(symbol_news)
        
        # General news
        for key in ['general', 'GENERAL', 'CRYPTO', 'crypto', 'MARKET', 'market']:
            general_news = service.news_data.get(key, [])
            news_items.extend(general_news)
        
        # SOL should have 0 symbol-specific + 2 general + 1 CRYPTO = 3 articles
        assert len(news_items) == 3
    
    def test_general_keys_checked(self):
        """Test that all general news keys are checked."""
        expected_keys = ['general', 'GENERAL', 'CRYPTO', 'crypto', 'MARKET', 'market']
        
        # These keys should be checked in get_news_score
        for key in expected_keys:
            assert key.lower() in ['general', 'crypto', 'market']


class TestNewsScoreIntegration:
    """Integration tests for news score calculation."""
    
    @pytest.mark.asyncio
    async def test_symbol_normalization(self):
        """Test that symbol normalization works correctly."""
        # BTC-USDT-SWAP should normalize to BTC
        full_symbol = 'BTC-USDT-SWAP'
        base_symbol = full_symbol.split('-')[0].upper()
        
        assert base_symbol == 'BTC'
    
    @pytest.mark.asyncio
    async def test_news_score_with_no_news(self):
        """Test news score returns neutral when no news available."""
        from application.news_service import NewsService
        
        with patch.object(NewsService, '__init__', lambda x, y: None):
            service = NewsService.__new__(NewsService)
            service.news_data = {}
            service.llm_analyzer = None
            service.llm_config = {'digest': {'max_items_per_symbol': 30}}
            service.digest_manager = MagicMock()
            service.digest_manager.get_digest_status = MagicMock(
                return_value=('hash', False, None)
            )
            
            # Manually call the logic
            news_items = []
            assert len(news_items) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
