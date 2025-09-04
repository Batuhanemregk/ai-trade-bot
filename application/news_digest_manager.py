"""
News Digest Manager - Manages digest-based caching for LLM analysis
"""

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class NewsDigestManager:
    """Manages digest-based caching for LLM analysis to avoid redundant API calls"""
    
    def __init__(self, cache_file_path: str = "data/news_digest_cache.json", ttl_minutes: int = 60):
        self.cache_file_path = cache_file_path
        self.ttl_minutes = ttl_minutes
        self.digest_cache: Dict[str, Dict[str, Any]] = {}
        self._ensure_data_directory()
        self._load_cache()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
    
    def _load_cache(self):
        """Load digest cache from disk"""
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r') as f:
                    data = json.load(f)
                    self.digest_cache = data
                logger.info(f"📊 Loaded {len(self.digest_cache)} digest cache entries")
            else:
                logger.info("📊 No existing digest cache found, starting fresh")
        except Exception as e:
            logger.error(f"❌ Failed to load digest cache: {e}")
            self.digest_cache = {}
    
    def _save_cache(self):
        """Save digest cache to disk"""
        try:
            with open(self.cache_file_path, 'w') as f:
                json.dump(self.digest_cache, f, indent=2)
            logger.debug(f"💾 Saved {len(self.digest_cache)} digest cache entries")
        except Exception as e:
            logger.error(f"❌ Failed to save digest cache: {e}")
    
    def _create_digest(self, news_items: List[Dict[str, Any]], max_items: int = 30) -> str:
        """Create digest hash from news items"""
        # Sort by timestamp (newest first) and take max_items
        sorted_items = sorted(news_items, key=lambda x: self._get_timestamp(x), reverse=True)[:max_items]
        
        # Create digest from url, timestamp, and title
        digest_data = []
        for item in sorted_items:
            digest_data.append({
                'url': item.get('url', ''),
                'timestamp': self._get_timestamp(item).isoformat() if self._get_timestamp(item) else '',
                'title': item.get('title', '')
            })
        
        # Sort by timestamp for consistent digest
        digest_data.sort(key=lambda x: x['timestamp'])
        
        # Create hash
        digest_str = json.dumps(digest_data, sort_keys=True)
        return hashlib.sha256(digest_str.encode()).hexdigest()[:16]  # First 16 chars
    
    def _get_timestamp(self, item: Dict[str, Any]) -> datetime:
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
        
        # Fallback to current time
        return datetime.now(timezone.utc)
    
    def get_digest_status(self, symbol: str, news_items: List[Dict[str, Any]], max_items: int = 30) -> Tuple[str, bool, Optional[Dict[str, Any]]]:
        """
        Get digest status for news items
        
        Returns:
            Tuple of (digest_hash, is_changed, cached_result)
        """
        current_digest = self._create_digest(news_items, max_items)
        
        # Check if we have cached result for this digest
        cache_key = f"{symbol}_{current_digest}"
        
        if cache_key in self.digest_cache:
            cached_entry = self.digest_cache[cache_key]
            
            # Check TTL
            cached_time = datetime.fromisoformat(cached_entry['timestamp'])
            if datetime.now(timezone.utc) - cached_time < timedelta(minutes=self.ttl_minutes):
                logger.info(f"📊 [LLM] sym={symbol} digest=SAME run=NO items={len(news_items)}")
                return current_digest, False, cached_entry['result']
            else:
                # TTL expired, remove from cache
                del self.digest_cache[cache_key]
                self._save_cache()
        
        # Check if digest changed from last time
        last_digest_key = f"{symbol}_last"
        is_changed = True
        
        if last_digest_key in self.digest_cache:
            last_digest = self.digest_cache[last_digest_key]['digest']
            is_changed = current_digest != last_digest
        
        if is_changed:
            logger.info(f"📊 [LLM] sym={symbol} digest=CHANGED run=YES items={len(news_items)}")
        else:
            logger.info(f"📊 [LLM] sym={symbol} digest=SAME run=NO items={len(news_items)}")
        
        return current_digest, is_changed, None
    
    def cache_digest_result(self, symbol: str, digest_hash: str, result: Dict[str, Any]):
        """Cache LLM analysis result for a digest"""
        cache_key = f"{symbol}_{digest_hash}"
        last_digest_key = f"{symbol}_last"
        
        cache_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'result': result,
            'digest': digest_hash
        }
        
        self.digest_cache[cache_key] = cache_entry
        self.digest_cache[last_digest_key] = cache_entry
        
        self._save_cache()
        logger.debug(f"💾 Cached digest result for {symbol} (digest: {digest_hash[:8]}...)")
    
    def get_cached_result(self, symbol: str, digest_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached result for a specific digest"""
        cache_key = f"{symbol}_{digest_hash}"
        
        if cache_key in self.digest_cache:
            cached_entry = self.digest_cache[cache_key]
            
            # Check TTL
            cached_time = datetime.fromisoformat(cached_entry['timestamp'])
            if datetime.now(timezone.utc) - cached_time < timedelta(minutes=self.ttl_minutes):
                return cached_entry['result']
            else:
                # TTL expired, remove from cache
                del self.digest_cache[cache_key]
                self._save_cache()
        
        return None
    
    def clear_cache_for_symbol(self, symbol: str):
        """Clear all cache entries for a symbol"""
        keys_to_remove = [key for key in self.digest_cache.keys() if key.startswith(f"{symbol}_")]
        for key in keys_to_remove:
            del self.digest_cache[key]
        
        self._save_cache()
        logger.info(f"🗑️ Cleared digest cache for {symbol}")
    
    def clear_all_cache(self):
        """Clear all digest cache"""
        self.digest_cache.clear()
        self._save_cache()
        logger.info("🗑️ Cleared all digest cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.digest_cache)
        symbols = set()
        expired_entries = 0
        
        for key in self.digest_cache.keys():
            if not key.endswith('_last'):
                symbol = key.split('_')[0]
                symbols.add(symbol)
                
                # Check if expired
                entry = self.digest_cache[key]
                cached_time = datetime.fromisoformat(entry['timestamp'])
                if datetime.now(timezone.utc) - cached_time >= timedelta(minutes=self.ttl_minutes):
                    expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'unique_symbols': len(symbols),
            'expired_entries': expired_entries,
            'ttl_minutes': self.ttl_minutes
        }
