"""
News Watermark Manager - Tracks last processed timestamps for incremental news fetching
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional
from loguru import logger


class NewsWatermarkManager:
    """Manages watermarks for incremental news fetching per symbol"""
    
    def __init__(self, state_file_path: str = "data/news_watermarks.json"):
        self.state_file_path = state_file_path
        self.watermarks: Dict[str, datetime] = {}
        self._ensure_data_directory()
        self._load_watermarks()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
    
    def _load_watermarks(self):
        """Load watermarks from disk"""
        try:
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r') as f:
                    data = json.load(f)
                    for symbol, timestamp_str in data.items():
                        self.watermarks[symbol] = datetime.fromisoformat(timestamp_str)
                logger.info(f"📊 Loaded {len(self.watermarks)} watermarks from {self.state_file_path}")
            else:
                logger.info("📊 No existing watermarks found, starting fresh")
        except Exception as e:
            logger.error(f"❌ Failed to load watermarks: {e}")
            self.watermarks = {}
    
    def _save_watermarks(self):
        """Save watermarks to disk"""
        try:
            data = {}
            for symbol, timestamp in self.watermarks.items():
                data[symbol] = timestamp.isoformat()
            
            with open(self.state_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"💾 Saved {len(self.watermarks)} watermarks to {self.state_file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save watermarks: {e}")
    
    def get_watermark(self, symbol: str) -> Optional[datetime]:
        """Get watermark for a symbol"""
        return self.watermarks.get(symbol)
    
    def has_watermark(self, symbol: str) -> bool:
        """Check if symbol has a watermark"""
        return symbol in self.watermarks
    
    def get_all_watermarks(self) -> Dict[str, str]:
        """Get all watermarks as ISO strings"""
        return {symbol: timestamp.isoformat() for symbol, timestamp in self.watermarks.items()}
    
    def set_watermark(self, symbol: str, timestamp: datetime):
        """Set watermark for a symbol"""
        self.watermarks[symbol] = timestamp
        self._save_watermarks()
        logger.info(f"📊 [NEWS] sym={symbol} watermark={timestamp.isoformat()}")
    
    def get_fetch_since_timestamp(self, symbol: str, overlap_minutes: int = 30) -> Optional[datetime]:
        """Get timestamp to fetch news since (with overlap)"""
        watermark = self.get_watermark(symbol)
        if watermark is None:
            return None
        
        from datetime import timedelta
        return watermark - timedelta(minutes=overlap_minutes)
    
    def update_watermark_from_news(self, symbol: str, news_items: list):
        """Update watermark based on latest news timestamp"""
        if not news_items:
            return
        
        # Find the latest timestamp from news items
        latest_timestamp = None
        for item in news_items:
            # Try different timestamp fields
            timestamp = None
            if 'publishedAt' in item:
                timestamp = self._parse_timestamp(item['publishedAt'])
            elif 'published_at' in item:
                timestamp = self._parse_timestamp(item['published_at'])
            elif 'timestamp' in item:
                timestamp = self._parse_timestamp(item['timestamp'])
            elif 'time' in item:
                timestamp = self._parse_timestamp(item['time'])
            
            if timestamp and (latest_timestamp is None or timestamp > latest_timestamp):
                latest_timestamp = timestamp
        
        if latest_timestamp:
            self.set_watermark(symbol, latest_timestamp)
    
    def _parse_timestamp(self, timestamp_value) -> Optional[datetime]:
        """Parse various timestamp formats"""
        try:
            if isinstance(timestamp_value, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
            elif isinstance(timestamp_value, str):
                # ISO format or other string formats
                if timestamp_value.endswith('Z'):
                    return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(timestamp_value)
            elif isinstance(timestamp_value, datetime):
                return timestamp_value
        except Exception as e:
            logger.debug(f"Failed to parse timestamp {timestamp_value}: {e}")
        
        return None
    
    def get_all_watermarks(self) -> Dict[str, datetime]:
        """Get all watermarks"""
        return self.watermarks.copy()
    
    def clear_watermark(self, symbol: str):
        """Clear watermark for a symbol (for bootstrap)"""
        if symbol in self.watermarks:
            del self.watermarks[symbol]
            self._save_watermarks()
            logger.info(f"🗑️ Cleared watermark for {symbol}")
    
    def clear_all_watermarks(self):
        """Clear all watermarks"""
        self.watermarks.clear()
        self._save_watermarks()
        logger.info("🗑️ Cleared all watermarks")
