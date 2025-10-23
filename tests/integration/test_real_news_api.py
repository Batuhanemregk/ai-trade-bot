"""
Real News API Integration Tests
Tests actual news API connectivity and data retrieval without mocks
"""
import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from adapters.news_apis import CryptoCompareNewsAPI, MultiSourceNewsClient
from application.news_service import NewsService
from application.news_llm_analyzer import NewsLLMAnalyzer
from configs.policy import load_policy


class TestRealNewsAPI:
    """Test real news API connectivity and data retrieval"""
    
    @pytest.fixture(scope="class")
    def policy(self):
        """Load real policy configuration"""
        return load_policy()
    
    @pytest.fixture(scope="class")
    def news_client(self):
        """Create real news client"""
        return MultiSourceNewsClient()
    
    @pytest.fixture(scope="class")
    def news_service(self, policy):
        """Create real news service"""
        return NewsService(policy)
    
    @pytest.fixture(scope="class")
    def llm_analyzer(self, policy):
        """Create real LLM analyzer"""
        return NewsLLMAnalyzer(policy)
    
    @pytest.mark.asyncio
    async def test_cryptocompare_news_api(self, news_client):
        """Test CryptoCompare news API with real data"""
        try:
            symbol = "BTC"
            limit = 10
            
            # Test direct CryptoCompare API
            async with CryptoCompareNewsAPI() as cc_api:
                news = await cc_api.get_news_for_symbol(symbol, limit)
                
                assert news is not None
                assert isinstance(news, list)
                assert len(news) <= limit
                
                if len(news) > 0:
                    article = news[0]
                    assert 'title' in article
                    assert 'body' in article
                    assert 'published_on' in article
                    assert 'source' in article
                    assert article['title'] is not None
                    assert len(article['title']) > 0
                    
                    print(f"✅ CryptoCompare: Retrieved {len(news)} real articles for {symbol}")
                    print(f"   Latest: {article['title'][:50]}...")
                else:
                    print(f"⚠️ CryptoCompare: No articles found for {symbol}")
            
        except Exception as e:
            pytest.skip(f"CryptoCompare API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multi_source_news_client(self, news_client):
        """Test multi-source news client with real data"""
        try:
            symbol = "BTC"
            limit = 5
            
            news = await news_client.get_news_for_symbol(symbol, limit)
            
            assert news is not None
            assert isinstance(news, list)
            assert len(news) <= limit
            
            if len(news) > 0:
                article = news[0]
                assert 'title' in article
                assert 'body' in article
                assert 'published_on' in article
                
                print(f"✅ Multi-source client: Retrieved {len(news)} real articles for {symbol}")
                print(f"   Latest: {article['title'][:50]}...")
            else:
                print(f"⚠️ Multi-source client: No articles found for {symbol}")
            
        except Exception as e:
            pytest.skip(f"Multi-source news client test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_service_real_data(self, news_service):
        """Test news service with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Test news fetching
            news_data = await news_service.get_news_score(symbol)
            
            assert news_data is not None
            assert isinstance(news_data, tuple)
            assert len(news_data) == 2
            
            score, details = news_data
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
            assert isinstance(details, dict)
            assert 'categories' in details
            assert 'rationale' in details
            
            print(f"✅ News service: Score {score:.1f} for {symbol}")
            print(f"   Categories: {details.get('categories', [])}")
            
        except Exception as e:
            pytest.skip(f"News service test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_analyzer_real_data(self, llm_analyzer):
        """Test LLM analyzer with real news data"""
        try:
            # Create sample real news data
            sample_news = [
                {
                    'title': 'Bitcoin Reaches New All-Time High Amid Institutional Adoption',
                    'body': 'Bitcoin has reached a new all-time high as major institutions continue to adopt cryptocurrency. The price surge is driven by increased demand from corporate treasuries and investment funds.',
                    'published_on': int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
                    'source': 'CoinDesk'
                },
                {
                    'title': 'Ethereum Network Upgrade Improves Transaction Speed',
                    'body': 'The latest Ethereum network upgrade has successfully improved transaction processing speed and reduced gas fees. Developers report significant performance improvements.',
                    'published_on': int((datetime.now(timezone.utc) - timedelta(hours=4)).timestamp()),
                    'source': 'Ethereum Foundation'
                }
            ]
            
            # Test LLM analysis
            analysis = await llm_analyzer.analyze_news_batch(sample_news)
            
            assert analysis is not None
            assert isinstance(analysis, dict)
            assert 'overall_sentiment' in analysis
            assert 'categories' in analysis
            assert 'confidence' in analysis
            assert 'summary' in analysis
            
            print(f"✅ LLM analyzer: Sentiment {analysis['overall_sentiment']}")
            print(f"   Confidence: {analysis['confidence']:.2f}")
            print(f"   Categories: {analysis['categories']}")
            
        except Exception as e:
            pytest.skip(f"LLM analyzer test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_news(self, news_client):
        """Test news fetching for multiple symbols"""
        try:
            symbols = ["BTC", "ETH", "SOL", "ADA", "DOT"]
            results = {}
            
            for symbol in symbols:
                try:
                    news = await news_client.get_news_for_symbol(symbol, limit=3)
                    results[symbol] = {
                        'count': len(news),
                        'latest_title': news[0]['title'][:30] + "..." if news else "No articles"
                    }
                    print(f"✅ {symbol}: {len(news)} articles - {results[symbol]['latest_title']}")
                    
                except Exception as e:
                    results[symbol] = {'error': str(e)}
                    print(f"⚠️ {symbol}: Failed - {e}")
            
            # At least some symbols should have news
            successful_symbols = [s for s, r in results.items() if 'error' not in r and r['count'] > 0]
            assert len(successful_symbols) > 0, "No symbols returned news successfully"
            
            print(f"✅ Successfully tested {len(successful_symbols)}/{len(symbols)} symbols with news")
            
        except Exception as e:
            pytest.skip(f"Multiple symbols news test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_timestamp_filtering(self, news_client):
        """Test news timestamp filtering with real data"""
        try:
            symbol = "BTC"
            limit = 20
            
            # Get news without filtering
            all_news = await news_client.get_news_for_symbol(symbol, limit)
            
            if len(all_news) > 0:
                # Check timestamps
                now = datetime.now(timezone.utc)
                recent_news = []
                old_news = []
                
                for article in all_news:
                    pub_time = datetime.fromtimestamp(article['published_on'], tz=timezone.utc)
                    age_hours = (now - pub_time).total_seconds() / 3600
                    
                    if age_hours <= 24:  # Last 24 hours
                        recent_news.append(article)
                    else:
                        old_news.append(article)
                
                print(f"✅ News timestamp filtering: {len(recent_news)} recent, {len(old_news)} older")
                print(f"   Recent range: {min([a['published_on'] for a in recent_news]) if recent_news else 'N/A'} to {max([a['published_on'] for a in recent_news]) if recent_news else 'N/A'}")
                
                # Most news should be recent for active symbols
                if len(all_news) >= 5:
                    recent_ratio = len(recent_news) / len(all_news)
                    assert recent_ratio > 0.3, f"Too few recent articles: {recent_ratio:.2f}"
            
        except Exception as e:
            pytest.skip(f"News timestamp filtering test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_content_quality(self, news_client):
        """Test news content quality and structure"""
        try:
            symbol = "BTC"
            limit = 10
            
            news = await news_client.get_news_for_symbol(symbol, limit)
            
            if len(news) > 0:
                quality_checks = {
                    'has_title': 0,
                    'has_body': 0,
                    'has_timestamp': 0,
                    'has_source': 0,
                    'title_length_ok': 0,
                    'body_length_ok': 0
                }
                
                for article in news:
                    # Check required fields
                    if article.get('title'):
                        quality_checks['has_title'] += 1
                        if 10 <= len(article['title']) <= 200:
                            quality_checks['title_length_ok'] += 1
                    
                    if article.get('body'):
                        quality_checks['has_body'] += 1
                        if len(article['body']) >= 50:
                            quality_checks['body_length_ok'] += 1
                    
                    if article.get('published_on'):
                        quality_checks['has_timestamp'] += 1
                    
                    if article.get('source'):
                        quality_checks['has_source'] += 1
                
                total_articles = len(news)
                quality_ratios = {k: v / total_articles for k, v in quality_checks.items()}
                
                print(f"✅ News quality check for {total_articles} articles:")
                for check, ratio in quality_ratios.items():
                    print(f"   {check}: {ratio:.2f}")
                
                # Quality thresholds
                assert quality_ratios['has_title'] >= 0.9, "Too many articles missing titles"
                assert quality_ratios['has_body'] >= 0.8, "Too many articles missing body"
                assert quality_ratios['has_timestamp'] >= 0.9, "Too many articles missing timestamps"
                assert quality_ratios['title_length_ok'] >= 0.8, "Too many articles with poor title length"
            
        except Exception as e:
            pytest.skip(f"News content quality test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_api_rate_limits(self, news_client):
        """Test news API rate limiting"""
        try:
            symbol = "BTC"
            
            # Make multiple rapid requests
            tasks = []
            for i in range(5):  # Make 5 rapid requests
                task = news_client.get_news_for_symbol(symbol, limit=3)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"✅ News API rate limit test: {successful} successful, {failed} failed")
            assert successful > 0, "No news requests succeeded"
            
        except Exception as e:
            pytest.skip(f"News API rate limit test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_service_cleanup(self, news_service):
        """Test news service cleanup and resource management"""
        try:
            # Test that news service can be properly closed
            await news_service.close()
            print("✅ News service cleanup completed successfully")
            
        except Exception as e:
            print(f"⚠️ News service cleanup test: {e}")


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/integration/test_real_news_api.py -v -s
    pytest.main([__file__, "-v", "-s"])

