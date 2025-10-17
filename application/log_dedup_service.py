"""
Log Deduplication Service
Prevents repetitive log messages from spamming the logs.
"""

from typing import Dict, Set
from datetime import datetime, timedelta


class LogDedupService:
    """Service to deduplicate repetitive log messages."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._seen_messages: Dict[str, datetime] = {}
        self._first_occurrence: Set[str] = set()
    
    def should_log(self, key: str) -> tuple[bool, bool]:
        """
        Check if a message should be logged.
        
        Returns:
            (should_log, is_first_occurrence)
        """
        now = datetime.now()
        
        # Check if this is first occurrence
        is_first = key not in self._first_occurrence
        
        if is_first:
            self._first_occurrence.add(key)
            self._seen_messages[key] = now
            return True, True
        
        # Check if we've seen this recently
        if key in self._seen_messages:
            last_seen = self._seen_messages[key]
            if (now - last_seen).total_seconds() < self.ttl_seconds:
                return False, False
        
        # Time to log again
        self._seen_messages[key] = now
        return True, False
    
    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory bloat."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.ttl_seconds * 2)
        
        # Remove old entries
        old_keys = [
            key for key, timestamp in self._seen_messages.items()
            if timestamp < cutoff
        ]
        
        for key in old_keys:
            del self._seen_messages[key]
            self._first_occurrence.discard(key)


# Global singleton instance
_log_dedup_service = LogDedupService()


def get_log_dedup_service() -> LogDedupService:
    """Get the global log dedup service instance."""
    return _log_dedup_service

