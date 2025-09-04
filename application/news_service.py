"""
News Service - Main news collection and analysis service with LLM integration
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from adapters.news_apis import MultiSourceNewsClient
from application.news_watermark_manager import NewsWatermarkManager
from application.news_digest_manager import NewsDigestManager
from application.news_llm_analyzer import NewsLLMAnalyzer


class NewsService:
    """Main news service with LLM integration and incremental fetching"""
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.news_config = policy.get('news', {})
        self.llm_config = policy.get('news_llm', {})
        self.scoring_config = policy.get('news_scoring', {})
        
        # Initialize components
        self.news_client = MultiSourceNewsClient()
        self.watermark_manager = NewsWatermarkManager()
        self.digest_manager = NewsDigestManager(
            ttl_minutes=self.llm_config.get('cache', {}).get('ttl_minutes', 60)
        )
        
        # Initialize LLM analyzer if enabled
        self.llm_analyzer = None
        if self.llm_config.get('enabled', True):
            import os
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.llm_analyzer = NewsLLMAnalyzer(openai_key)
                logger.info("✅ News service initialized with LLM analysis")
            else:
                logger.warning("⚠️ LLM analysis disabled - no OpenAI API key")
        
        # Load symbol aliases
        self.symbol_aliases = self._load_symbol_aliases()
        
        # News storage
        self.news_storage_path = "data/news_storage.json"
        self.news_data: Dict[str, List[Dict[str, Any]]] = {}
        self._load_news_storage()
    
    def _load_symbol_aliases(self) -> Dict[str, Any]:
        """Load symbol aliases from config"""
        try:
            import yaml
            with open('configs/symbol_alias.yaml', 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load symbol aliases: {e}")
            return {}
    
    def _load_news_storage(self):
        """Load news storage from disk"""
        try:
            if os.path.exists(self.news_storage_path):
                with open(self.news_storage_path, 'r') as f:
                    self.news_data = json.load(f)
                logger.info(f"📊 Loaded news storage with {len(self.news_data)} symbols")
            else:
                logger.info("📊 No existing news storage found")
        except Exception as e:
            logger.error(f"❌ Failed to load news storage: {e}")
            self.news_data = {}
    
    def _save_news_storage(self):
        """Save news storage to disk"""
        try:
            os.makedirs(os.path.dirname(self.news_storage_path), exist_ok=True)
            with open(self.news_storage_path, 'w') as f:
                json.dump(self.news_data, f, indent=2)
            logger.debug("💾 Saved news storage")
        except Exception as e:
            logger.error(f"❌ Failed to save news storage: {e}")
    
    async def bootstrap_all_symbols(self, symbols: List[str]):
        """Bootstrap news collection for all symbols"""
        logger.info(f"🚀 Starting news bootstrap for {len(symbols)} symbols")
        
        lookback_hours = self.news_config.get('lookback_hours_bootstrap', 24)
        since_timestamp = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        for symbol in symbols:
            try:
                await self._bootstrap_symbol(symbol, since_timestamp)
            except Exception as e:
                logger.error(f"❌ Bootstrap failed for {symbol}: {e}")
        
        logger.info("✅ News bootstrap completed")
    
    async def _bootstrap_symbol(self, symbol: str, since_timestamp: datetime):
        """Bootstrap news collection for a single symbol"""
        logger.info(f"📊 [NEWS] sym={symbol} bootstrap since={since_timestamp.isoformat()}")
        
        # Fetch news
        news_items = await self._fetch_news_for_symbol(symbol, since_timestamp)
        
        if news_items:
            # Store news
            self.news_data[symbol] = news_items
            self._save_news_storage()
            
            # Update watermark
            self.watermark_manager.update_watermark_from_news(symbol, news_items)
            
            # Run LLM analysis if enabled
            if self.llm_analyzer:
                await self._analyze_news_with_llm(symbol, news_items)
            
            logger.info(f"✅ [NEWS] sym={symbol} bootstrap completed: {len(news_items)} articles")
        else:
            logger.warning(f"⚠️ [NEWS] sym={symbol} no articles found in bootstrap")
    
    async def incremental_update_symbols(self, symbols: List[str]):
        """Incremental news update for all symbols"""
        logger.info(f"🔄 Starting incremental news update for {len(symbols)} symbols")
        
        overlap_minutes = self.news_config.get('overlap_minutes', 30)
        
        for symbol in symbols:
            try:
                await self._incremental_update_symbol(symbol, overlap_minutes)
            except Exception as e:
                logger.error(f"❌ Incremental update failed for {symbol}: {e}")
        
        logger.info("✅ Incremental news update completed")
    
    async def _incremental_update_symbol(self, symbol: str, overlap_minutes: int):
        """Incremental news update for a single symbol"""
        # Get fetch since timestamp
        since_timestamp = self.watermark_manager.get_fetch_since_timestamp(symbol, overlap_minutes)
        
        if since_timestamp is None:
            logger.warning(f"⚠️ [NEWS] sym={symbol} no watermark, skipping incremental")
            return
        
        logger.info(f"📊 [NEWS] sym={symbol} incremental since={since_timestamp.isoformat()}")
        
        # Fetch new news
        new_news_items = await self._fetch_news_for_symbol(symbol, since_timestamp)
        
        if new_news_items:
            # Merge with existing news
            existing_news = self.news_data.get(symbol, [])
            merged_news = self._merge_and_dedupe_news(existing_news, new_news_items)
            
            # Store updated news
            self.news_data[symbol] = merged_news
            self._save_news_storage()
            
            # Update watermark
            self.watermark_manager.update_watermark_from_news(symbol, new_news_items)
            
            # Run LLM analysis if digest changed
            if self.llm_analyzer:
                await self._analyze_news_with_llm(symbol, merged_news)
            
            logger.info(f"✅ [NEWS] sym={symbol} incremental: {len(new_news_items)} new, {len(merged_news)} total")
        else:
            logger.info(f"📊 [NEWS] sym={symbol} incremental: no new articles")
    
    async def _fetch_news_for_symbol(self, symbol: str, since_timestamp: datetime) -> List[Dict[str, Any]]:
        """Fetch news for a symbol since timestamp"""
        try:
            # Use multi-source news client
            news_items = await self.news_client.get_news_for_symbol(symbol, limit=50)
            
            # Filter by timestamp
            filtered_items = []
            for item in news_items:
                item_timestamp = self._extract_timestamp(item)
                if item_timestamp and item_timestamp >= since_timestamp:
                    filtered_items.append(item)
            
            return filtered_items
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch news for {symbol}: {e}")
            return []
    
    def _extract_timestamp(self, item: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from news item"""
        timestamp_fields = ['publishedAt', 'published_at', 'timestamp', 'time']
        
        for field in timestamp_fields:
            if field in item and item[field]:
                try:
                    timestamp_value = item[field]
                    if isinstance(timestamp_value, (int, float)):
                        return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
                    elif isinstance(timestamp_value, str):
                        if timestamp_value.endswith('Z'):
                            return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                        else:
                            return datetime.fromisoformat(timestamp_value)
                    elif isinstance(timestamp_value, datetime):
                        return timestamp_value
                except Exception:
                    continue
        
        return None
    
    def _merge_and_dedupe_news(self, existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge and deduplicate news items"""
        # Create set of existing URLs for deduplication
        existing_urls = {item.get('url', '') for item in existing}
        
        # Add new items that aren't duplicates
        merged = existing.copy()
        for item in new:
            if item.get('url', '') not in existing_urls:
                merged.append(item)
        
        # Sort by timestamp (newest first)
        merged.sort(key=lambda x: self._extract_timestamp(x) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return merged
    
    async def _analyze_news_with_llm(self, symbol: str, news_items: List[Dict[str, Any]]):
        """Analyze news with LLM if digest changed"""
        if not self.llm_analyzer:
            return
        
        max_items = self.llm_config.get('digest', {}).get('max_items_per_symbol', 30)
        
        # Get digest status
        digest_hash, is_changed, cached_result = self.digest_manager.get_digest_status(
            symbol, news_items, max_items
        )
        
        if not is_changed and cached_result:
            logger.info(f"📊 [LLM] sym={symbol} using cached result")
            return
        
        # Run LLM analysis
        try:
            score, categories, rationale, volatility_impact = await self.llm_analyzer.analyze_news_batch(
                news_items[:max_items], symbol, self.symbol_aliases
            )
            
            # Cache result
            result = {
                'score': score,
                'categories': categories,
                'rationale': rationale,
                'volatility_impact': volatility_impact,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.digest_manager.cache_digest_result(symbol, digest_hash, result)
            
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for {symbol}: {e}")
    
    async def get_news_score(self, symbol: str) -> Tuple[float, List[str], str, float]:
        """Get news score for a symbol"""
        try:
            # Get latest cached LLM result
            news_items = self.news_data.get(symbol, [])
            if not news_items:
                return 50.0, ["GENERAL"], "No news data available", 0.5
            
            max_items = self.llm_config.get('digest', {}).get('max_items_per_symbol', 30)
            digest_hash, _, cached_result = self.digest_manager.get_digest_status(
                symbol, news_items, max_items
            )
            
            if cached_result:
                return (
                    cached_result['score'],
                    cached_result['categories'],
                    cached_result['rationale'],
                    cached_result['volatility_impact']
                )
            else:
                # Fallback to neutral score
                return 50.0, ["GENERAL"], "No LLM analysis available", 0.5
                
        except Exception as e:
            logger.error(f"❌ Failed to get news score for {symbol}: {e}")
            return 50.0, ["GENERAL"], "Error getting news score", 0.5
    
    def get_news_stats(self) -> Dict[str, Any]:
        """Get news service statistics"""
        total_articles = sum(len(news) for news in self.news_data.values())
        watermark_stats = self.watermark_manager.get_all_watermarks()
        digest_stats = self.digest_manager.get_cache_stats()
        
        return {
            'symbols_with_news': len(self.news_data),
            'total_articles': total_articles,
            'watermarks': len(watermark_stats),
            'digest_cache': digest_stats,
            'llm_enabled': self.llm_analyzer is not None
        }
