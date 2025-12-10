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
        
        # Log verbosity control
        self.verbose_logging = os.getenv('NEWS_VERBOSITY', 'summary').lower() == 'full'
        
        # Storage paths from policy
        storage_paths = self.news_config.get('storage_paths', {})
        self.watermark_path = storage_paths.get('watermarks', 'data/news_watermarks.json')
        self.digest_path = storage_paths.get('digests', 'data/news_llm_digest.json')
        self.news_storage_path = storage_paths.get('news_store', 'data/news_storage.json')
        
        # Initialize components with paths
        self.news_client = MultiSourceNewsClient()
        self.watermark_manager = NewsWatermarkManager(self.watermark_path)
        self.digest_manager = NewsDigestManager(
            cache_path=self.digest_path,
            ttl_minutes=self.llm_config.get('cache', {}).get('ttl_minutes', 60)
        )
        
        # Initialize LLM analyzer if enabled
        self.llm_analyzer = None
        if self.llm_config.get('enabled', True):
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.llm_analyzer = NewsLLMAnalyzer(openai_key)
                logger.info("✅ News service initialized with LLM analysis")
            else:
                logger.warning("⚠️ LLM analysis disabled - no OpenAI API key")
        
        # Load symbol aliases
        self.symbol_aliases = self._load_symbol_aliases()
        
        # News storage
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
    
    async def ensure_bootstrap_on_start(self, symbols: List[str]):
        """On-start bootstrap: If no watermarks exist, bootstrap all symbols"""
        symbols_without_watermark = []
        
        for symbol in symbols:
            if not self.watermark_manager.has_watermark(symbol):
                symbols_without_watermark.append(symbol)
        
        if symbols_without_watermark:
            logger.info(f"🔄 [NEWS] On-start bootstrap for {len(symbols_without_watermark)} symbols without watermarks")
            await self.bootstrap_all_symbols(symbols_without_watermark)
        else:
            logger.info("✅ [NEWS] All symbols have watermarks, skipping bootstrap")
    
    async def lazy_bootstrap_symbol(self, symbol: str):
        """Lazy bootstrap: Bootstrap single symbol if no watermark"""
        if not self.watermark_manager.has_watermark(symbol):
            logger.info(f"🔄 [NEWS] Lazy bootstrap for {symbol} (no watermark)")
            lookback_hours = self.news_config.get('lookback_hours_bootstrap', 24)
            since_timestamp = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            await self._bootstrap_symbol(symbol, since_timestamp)
    
    async def _bootstrap_symbol(self, symbol: str, since_timestamp: datetime):
        """Bootstrap news collection for a single symbol"""
        if self.verbose_logging:
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
            
            if self.verbose_logging:
                logger.info(f"✅ [NEWS] sym={symbol} bootstrap completed: {len(news_items)} articles")
        else:
            if self.verbose_logging:
                logger.warning(f"⚠️ [NEWS] sym={symbol} no articles found in bootstrap")
    
    async def incremental_update_symbols(self, symbols: List[str]):
        """Incremental news update for all symbols"""
        if self.verbose_logging:
            logger.info(f"🔄 Starting incremental news update for {len(symbols)} symbols")
        
        overlap_minutes = self.news_config.get('overlap_minutes', 30)
        total_fetched = 0
        total_llm = 0
        total_changed = 0
        errors = 0
        
        for symbol in symbols:
            try:
                await self._incremental_update_symbol(symbol, overlap_minutes)
            except Exception as e:
                logger.error(f"❌ Incremental update failed for {symbol}: {e}")
                errors += 1
        
        if not self.verbose_logging:
            # Summary log instead of verbose logs
            stats = self.get_news_stats()
            logger.info(f"NEWS 5m | symbols={len(symbols)} | fetched={stats.get('total_articles', 0)} | llm={stats.get('llm_analyzed', 0)} | changed={stats.get('cache_changed', 0)} | errors={errors}")
        else:
            logger.info("✅ Incremental news update completed")
    
    async def _incremental_update_symbol(self, symbol: str, overlap_minutes: int):
        """Incremental news update for a single symbol"""
        # Lazy bootstrap if no watermark
        if not self.watermark_manager.has_watermark(symbol):
            await self.lazy_bootstrap_symbol(symbol)
            return
        
        # Get fetch since timestamp with overlap
        since_timestamp = self.watermark_manager.get_fetch_since_timestamp(symbol, overlap_minutes)
        
        if since_timestamp is None:
            logger.warning(f"⚠️ [NEWS] sym={symbol} no watermark after bootstrap, skipping incremental")
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
            
            # Force digest invalidation on new articles
            logger.info(f"[NEWS_SCORE] {symbol} updated: +{len(new_news_items)} articles, forcing LLM re-analysis")
            
            # Run LLM analysis for new articles
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
            
            # If no timestamp filtering needed (bootstrap), return all news
            if since_timestamp.year < 2020:  # Very old timestamp means bootstrap
                if self.verbose_logging:
                    logger.info(f"📰 [NEWS] sym={symbol} bootstrap mode: returning {len(news_items)} articles")
                return news_items
            
            # Filter by timestamp for incremental updates
            filtered_items = []
            for item in news_items:
                item_timestamp = self._extract_timestamp(item)
                if item_timestamp and item_timestamp >= since_timestamp:
                    filtered_items.append(item)
            
            if self.verbose_logging:
                logger.info(f"📰 [NEWS] sym={symbol} timestamp filter: {len(news_items)} -> {len(filtered_items)} articles")
            return filtered_items
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch news for {symbol}: {e}")
            return []
    
    def _extract_timestamp(self, item: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from news item"""
        timestamp_fields = ['publishedAt', 'published_at', 'published_on', 'timestamp', 'time']
        
        for field in timestamp_fields:
            if field in item and item[field]:
                try:
                    timestamp_value = item[field]
                    if isinstance(timestamp_value, (int, float)):
                        # CryptoCompare uses Unix timestamp
                        return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
                    elif isinstance(timestamp_value, str):
                        if timestamp_value.endswith('Z'):
                            return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                        else:
                            return datetime.fromisoformat(timestamp_value)
                    elif isinstance(timestamp_value, datetime):
                        return timestamp_value
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp {field}={timestamp_value}: {e}")
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
            logger.info(f"📊 [LLM] sym={symbol} digest=UNCHANGED run=NO items={len(news_items)}")
            return
        
        # Run LLM analysis
        try:
            logger.info(f"📊 [LLM] sym={symbol} digest=CHANGED run=YES items={len(news_items[:max_items])}")
            
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
            
            # Log classification results
            classification = self._determine_classification(categories, score)
            logger.info(f"📊 [NEWSCLS] type={classification['type']} sym={symbol} conf={classification['confidence']:.2f} title=\"{news_items[0].get('title', 'N/A')[:50]}...\"")
            
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for {symbol}: {e}")
    
    def _determine_classification(self, categories: List[str], score: float) -> Dict[str, Any]:
        """Determine news classification type and confidence"""
        if not categories:
            return {'type': 'general', 'confidence': 0.5}
        
        # Check for symbol-specific categories
        symbol_specific = any('SYMBOL_SPECIFIC' in cat for cat in categories)
        mixed = any('MIXED' in cat for cat in categories)
        
        if symbol_specific:
            return {'type': 'symbol_specific', 'confidence': score / 100.0}
        elif mixed:
            return {'type': 'mixed', 'confidence': score / 100.0}
        else:
            return {'type': 'general', 'confidence': score / 100.0}
    
    async def get_news_score(self, symbol: str) -> Tuple[float, List[str], str, float]:
        """Get news score for a symbol.
        
        Includes both symbol-specific news AND general market news.
        Per user request: general market news should impact all active coins.
        """
        try:
            logger.debug(f"[NEWS_SCORE] get_news_score called for {symbol}")
            
            # Normalize symbol: BTC-USDT-SWAP -> BTC, ETH-USDT-SWAP -> ETH, etc.
            base_symbol = symbol.split('-')[0].upper() if '-' in symbol else symbol.upper()
            
            # Collect news from multiple sources:
            # 1. Symbol-specific news (e.g., "BTC", "ETH")
            # 2. General market news (e.g., "CRYPTO", "MARKET", "general")
            news_items = []
            
            # 1. Get symbol-specific news
            symbol_news = self.news_data.get(symbol, [])
            if not symbol_news:
                symbol_news = self.news_data.get(base_symbol, [])
            
            if symbol_news:
                news_items.extend(symbol_news)
                logger.debug(f"[NEWS_SCORE] {symbol}: found {len(symbol_news)} symbol-specific articles")
            
            # 2. Get general market news (impacts ALL coins)
            general_keys = ['general', 'GENERAL', 'CRYPTO', 'crypto', 'MARKET', 'market']
            general_news_count = 0
            for key in general_keys:
                general_news = self.news_data.get(key, [])
                if general_news:
                    news_items.extend(general_news)
                    general_news_count += len(general_news)
            
            if general_news_count > 0:
                logger.debug(f"[NEWS_SCORE] {symbol}: added {general_news_count} general market articles")
            
            logger.debug(f"[NEWS_SCORE] {symbol} has {len(news_items)} total articles (symbol + general)")
            
            if not news_items:
                logger.info(f"[NEWS_SCORE] {symbol} -> 50.0 (no articles for {symbol} or general market)")
                return 50.0, ["GENERAL"], "No news data available", 0.5
            
            max_items = self.llm_config.get('digest', {}).get('max_items_per_symbol', 30)
            digest_hash, is_changed, cached_result = self.digest_manager.get_digest_status(
                symbol, news_items, max_items
            )
            
            logger.debug(f"[NEWS_SCORE] {symbol} digest_status: changed={is_changed}, has_cache={cached_result is not None}")
            
            if cached_result:
                score = cached_result['score']
                logger.info(f"[NEWS_SCORE] {symbol} -> {score:.1f} (cached LLM result)")
                return (
                    score,
                    cached_result['categories'],
                    cached_result['rationale'],
                    cached_result['volatility_impact']
                )
            else:
                # Try to run LLM analysis on-demand if analyzer is available
                if self.llm_analyzer and news_items:
                    try:
                        logger.info(f"[NEWS_SCORE] {symbol} -> Running on-demand LLM analysis for {len(news_items)} articles")
                        max_items = self.llm_config.get('digest', {}).get('max_items_per_symbol', 30)
                        
                        score, categories, rationale, volatility_impact = await self.llm_analyzer.analyze_news_batch(
                            news_items[:max_items], symbol, self.symbol_aliases
                        )
                        
                        # Cache the result
                        result = {
                            'score': score,
                            'categories': categories,
                            'rationale': rationale,
                            'volatility_impact': volatility_impact,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        self.digest_manager.cache_digest_result(base_symbol, digest_hash, result)
                        
                        logger.info(f"[NEWS_SCORE] {symbol} -> {score:.1f} (on-demand LLM analysis)")
                        return score, categories, rationale, volatility_impact
                        
                    except Exception as llm_error:
                        logger.warning(f"[NEWS_SCORE] {symbol} LLM analysis failed: {llm_error}, using neutral")
                
                # Fallback to neutral score
                logger.info(f"[NEWS_SCORE] {symbol} -> 50.0 (no LLM analysis available)")
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
    
    async def close(self):
        """Close news service and clean up resources"""
        try:
            if self.news_client:
                await self.news_client.close()
            logger.info("✅ News service closed successfully")
        except Exception as e:
            logger.error(f"❌ Error closing news service: {e}")
