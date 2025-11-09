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
        self._entries: Dict[str, Dict[str, datetime | int]] = {}
        self._first_occurrence: Set[str] = set()
    
    def should_log(self, key: str) -> tuple[bool, bool, int]:
        """
        Check if a message should be logged and return deduplication metadata.
        
        Returns:
            (should_log, is_first_occurrence, dedup_count)
        """
        now = datetime.now()
        
        # Check if this is first occurrence
        is_first = key not in self._first_occurrence
        
        if is_first:
            self._first_occurrence.add(key)
            self._entries[key] = {'last_logged': now, 'suppressed': 0}
            return True, True, 0
        
        entry = self._entries.setdefault(key, {'last_logged': now, 'suppressed': 0})
        last_logged = entry['last_logged']
        suppressed = entry['suppressed']
        
        if (now - last_logged).total_seconds() < self.ttl_seconds:
            entry['suppressed'] = suppressed + 1
            return False, False, 0
        
        # Time to log again
        dedup_count = entry['suppressed']
        entry['suppressed'] = 0
        entry['last_logged'] = now
        return True, False, dedup_count
    
    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory bloat."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.ttl_seconds * 2)
        
        # Remove old entries
        old_keys = []
        for key, entry in self._entries.items():
            last_logged = entry['last_logged']
            if last_logged < cutoff:
                old_keys.append(key)
        
        for key in old_keys:
            del self._entries[key]
            self._first_occurrence.discard(key)


# Global singleton instance
_log_dedup_service = LogDedupService()


def get_log_dedup_service() -> LogDedupService:
    """Get the global log dedup service instance."""
    return _log_dedup_service

