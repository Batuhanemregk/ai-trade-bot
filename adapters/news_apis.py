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
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
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
        """Get news for a specific symbol (filters general crypto news)"""
        try:
            # Get general crypto news
            all_news = await self.get_crypto_news(limit * 2)  # Get more to filter
            
            # Extract symbol keywords
            symbol_keywords = self._get_symbol_keywords(symbol)
            
            # Filter news by symbol relevance
            relevant_news = []
            for item in all_news:
                if self._is_relevant_to_symbol(item, symbol_keywords):
                    relevant_news.append(item)
                    if len(relevant_news) >= limit:
                        break
            
            return relevant_news
            
        except Exception as e:
            logger.error(f"Failed to get news for symbol {symbol}: {e}")
            return []
    
    def _get_symbol_keywords(self, symbol: str) -> List[str]:
        """Get keywords for symbol filtering"""
        # Remove -USDT-SWAP suffix
        base_symbol = symbol.replace('-USDT-SWAP', '').replace('-USDT', '')
        
        # Symbol to keyword mapping
        symbol_keywords = {
            'BTC': ['bitcoin', 'btc', 'crypto', 'cryptocurrency'],
            'ETH': ['ethereum', 'eth', 'ether', 'defi', 'smart contract'],
            'SOL': ['solana', 'sol', 'blockchain', 'defi'],
            'ADA': ['cardano', 'ada', 'blockchain'],
            'DOT': ['polkadot', 'dot', 'parachain'],
            'AVAX': ['avalanche', 'avax', 'blockchain'],
            'MATIC': ['polygon', 'matic', 'ethereum scaling'],
            'LINK': ['chainlink', 'link', 'oracle'],
            'UNI': ['uniswap', 'uni', 'dex', 'defi'],
            'ATOM': ['cosmos', 'atom', 'blockchain'],
            'NEAR': ['near protocol', 'near', 'blockchain'],
            'FTM': ['fantom', 'ftm', 'blockchain'],
            'ALGO': ['algorand', 'algo', 'blockchain'],
            'VET': ['vechain', 'vet', 'blockchain'],
            'ICP': ['internet computer', 'icp', 'blockchain'],
            'XRP': ['ripple', 'xrp', 'cryptocurrency'],
            'CFX': ['conflux', 'cfx', 'blockchain'],
            'BIO': ['biopassport', 'bio', 'cryptocurrency'],
            'PENGU': ['penguin', 'pengu', 'cryptocurrency'],
            'CRO': ['cronos', 'cro', 'cryptocurrency'],
            'LDO': ['lido', 'ldo', 'ethereum', 'staking'],
            'TAO': ['bittensor', 'tao', 'ai', 'blockchain'],
            'ARB': ['arbitrum', 'arb', 'ethereum', 'layer 2'],
            'SUI': ['sui', 'blockchain', 'defi'],
            'FET': ['fetch.ai', 'fet', 'ai', 'blockchain'],
            'JUP': ['jupiter', 'jup', 'solana', 'dex'],
            'OP': ['optimism', 'op', 'ethereum', 'layer 2']
        }
        
        return symbol_keywords.get(base_symbol, [base_symbol.lower()])
    
    def _is_relevant_to_symbol(self, news_item: Dict[str, Any], keywords: List[str]) -> bool:
        """Check if news item is relevant to symbol"""
        try:
            # Get text content to search
            title = news_item.get('title', '').lower()
            body = news_item.get('body', '').lower()
            tags = news_item.get('tags', '').lower()
            categories = news_item.get('categories', '').lower()
            
            # Combine all text
            all_text = f"{title} {body} {tags} {categories}"
            
            # Check if any keyword is present
            for keyword in keywords:
                if keyword.lower() in all_text:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking news relevance: {e}")
            return False


class MultiSourceNewsClient:
    """Combines multiple news sources for comprehensive coverage - CryptoCompare only"""
    
    def __init__(self):
        self.cryptocompare = CryptoCompareNewsAPI()
        self._session = None
        self._session_lock = asyncio.Lock()
    
    async def _get_session(self):
        """Get or create persistent session"""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    self._session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=30),
                        connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
                    )
        return self._session
    
    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news from CryptoCompare for a symbol"""
        try:
            # Use persistent session
            session = await self._get_session()
            async with self.cryptocompare as cc:
                cc.session = session  # Use persistent session
                news = await cc.get_news_for_symbol(symbol, limit)
                return news
            
        except Exception as e:
            logger.error(f"Failed to get news for symbol {symbol}: {e}")
            return []
    
    async def close(self):
        """Close persistent session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _remove_duplicates(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate news items based on URL"""
        seen_urls = set()
        unique_news = []
        
        for item in news_list:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(item)
        
        return unique_news