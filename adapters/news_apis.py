"""
News API Adapters - Multiple free news sources for cryptocurrency news
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger


class CryptoCompareNewsAPI:
    """CryptoCompare free news API - no API key required"""
    
    def __init__(self):
        self.base_url = "https://min-api.cryptocompare.com/data/v2"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_crypto_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get latest cryptocurrency news"""
        try:
            url = f"{self.base_url}/news/?lang=EN&limit={limit}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # CryptoCompare returns 'Data' array directly on success
                    if 'Data' in data and isinstance(data['Data'], list):
                        return data['Data']
                    elif data.get('Response') == 'Success':
                        return data.get('Data', [])
                    else:
                        logger.warning(f"CryptoCompare API error: {data.get('Message', 'Unknown error')}")
                        return []
                else:
                    logger.error(f"CryptoCompare API HTTP error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"CryptoCompare API request failed: {e}")
            return []
    
    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news filtered by symbol (basic keyword matching)"""
        try:
            # Get general crypto news
            all_news = await self.get_crypto_news(limit * 2)
            
            # Filter by symbol keywords
            symbol_keywords = self._get_symbol_keywords(symbol)
            filtered_news = []
            
            for article in all_news:
                if self._is_relevant_to_symbol(article, symbol_keywords):
                    filtered_news.append(article)
                    if len(filtered_news) >= limit:
                        break
            
            return filtered_news
        except Exception as e:
            logger.error(f"Symbol news filtering failed for {symbol}: {e}")
            return []
    
    def _get_symbol_keywords(self, symbol: str) -> List[str]:
        """Get relevant keywords for a symbol"""
        base_symbol = symbol.split('-')[0].upper()
        
        # Common symbol mappings
        symbol_mappings = {
            'BTC': ['bitcoin', 'btc'],
            'ETH': ['ethereum', 'eth', 'ether'],
            'SOL': ['solana', 'sol'],
            'ADA': ['cardano', 'ada'],
            'DOT': ['polkadot', 'dot'],
            'AVAX': ['avalanche', 'avax'],
            'MATIC': ['polygon', 'matic'],
            'LINK': ['chainlink', 'link'],
            'UNI': ['uniswap', 'uni'],
            'ATOM': ['cosmos', 'atom'],
            'NEAR': ['near', 'near protocol'],
            'FTM': ['fantom', 'ftm'],
            'ALGO': ['algorand', 'algo'],
            'VET': ['vechain', 'vet'],
            'ICP': ['internet computer', 'icp'],
            'XRP': ['ripple', 'xrp'],
            'CFX': ['conflux', 'cfx'],
            'BIO': ['biopassport', 'bio'],
            'PENGU': ['penguin', 'pengu'],
            'CRO': ['crypto.com', 'cro'],
            'LDO': ['lido', 'ldo'],
            'TAO': ['bittensor', 'tao'],
            'ARB': ['arbitrum', 'arb'],
            'SUI': ['sui', 'sui network'],
            'RENDER': ['render', 'render token'],
            'FET': ['fetch.ai', 'fet'],
            'JUP': ['jupiter', 'jup'],
            'OP': ['optimism', 'op']
        }
        
        return symbol_mappings.get(base_symbol, [base_symbol.lower()])
    
    def _is_relevant_to_symbol(self, article: Dict[str, Any], keywords: List[str]) -> bool:
        """Check if article is relevant to symbol"""
        title = article.get('title', '').lower()
        body = article.get('body', '').lower()
        tags = ' '.join(article.get('tags', [])).lower()
        
        text = f"{title} {body} {tags}"
        
        for keyword in keywords:
            if keyword.lower() in text:
                return True
        
        return False


class NewsAPIClient:
    """NewsAPI.org client - requires free API key"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_crypto_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get cryptocurrency news from NewsAPI"""
        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': 'cryptocurrency OR bitcoin OR ethereum OR crypto',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': min(limit, 100),  # NewsAPI max 100 per request
                'apiKey': self.api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('articles', [])
                else:
                    logger.error(f"NewsAPI HTTP error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"NewsAPI request failed: {e}")
            return []


class GNewsClient:
    """GNews.io client - requires free API key"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gnews.io/api/v4"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_crypto_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get cryptocurrency news from GNews"""
        try:
            url = f"{self.base_url}/search"
            params = {
                'q': 'cryptocurrency bitcoin ethereum crypto',
                'lang': 'en',
                'country': 'us',
                'max': min(limit, 10),  # GNews free plan max 10 per request
                'apikey': self.api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('articles', [])
                else:
                    logger.error(f"GNews HTTP error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"GNews request failed: {e}")
            return []


class MultiSourceNewsClient:
    """Combines multiple news sources for comprehensive coverage"""
    
    def __init__(self, newsapi_key: Optional[str] = None, gnews_key: Optional[str] = None):
        self.cryptocompare = CryptoCompareNewsAPI()
        self.newsapi = NewsAPIClient(newsapi_key) if newsapi_key else None
        self.gnews = GNewsClient(gnews_key) if gnews_key else None
    
    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news from all available sources for a symbol"""
        all_news = []
        
        try:
            # CryptoCompare (always available)
            async with self.cryptocompare as cc:
                cc_news = await cc.get_news_for_symbol(symbol, limit // 2)
                all_news.extend(cc_news)
            
            # NewsAPI (if available)
            if self.newsapi:
                async with self.newsapi as na:
                    na_news = await na.get_crypto_news(limit // 4)
                    # Filter by symbol
                    symbol_keywords = self.cryptocompare._get_symbol_keywords(symbol)
                    filtered_na_news = [
                        article for article in na_news 
                        if self.cryptocompare._is_relevant_to_symbol(article, symbol_keywords)
                    ]
                    all_news.extend(filtered_na_news[:limit // 4])
            
            # GNews (if available)
            if self.gnews:
                async with self.gnews as gn:
                    gn_news = await gn.get_crypto_news(limit // 4)
                    # Filter by symbol
                    symbol_keywords = self.cryptocompare._get_symbol_keywords(symbol)
                    filtered_gn_news = [
                        article for article in gn_news 
                        if self.cryptocompare._is_relevant_to_symbol(article, symbol_keywords)
                    ]
                    all_news.extend(filtered_gn_news[:limit // 4])
            
            # Remove duplicates and limit results
            unique_news = self._remove_duplicates(all_news)
            return unique_news[:limit]
            
        except Exception as e:
            logger.error(f"Multi-source news collection failed for {symbol}: {e}")
            return []
    
    def _remove_duplicates(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on title similarity"""
        seen_titles = set()
        unique_news = []
        
        for article in news_list:
            title = article.get('title', '').lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(article)
        
        return unique_news
