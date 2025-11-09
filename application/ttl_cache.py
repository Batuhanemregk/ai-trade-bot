"""
Generic TTL cache utility with deep-copy semantics and simple metrics.
Used for news/risk deduplication layers.
"""

from __future__ import annotations

import copy
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

from loguru import logger

_CACHE_HITS = defaultdict(int)
_CACHE_MISSES = defaultdict(int)
_CACHE_ITEMS = defaultdict(int)


class TTLCache:
    """Thread-safe TTL cache with deep copy semantics."""

    def __init__(self, name: str):
        self.name = name
        self._store: Dict[Any, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._metrics_exporter = None
        self._metrics_checked = False

    def get(self, key: Any) -> Optional[Any]:
        """Retrieve value if present and not expired."""
        with self._lock:
            self._purge_expired_locked()
            if key not in self._store:
                _CACHE_MISSES[self.name] += 1
                self._record_miss()
                return None

            value, expires_at = self._store[key]
            if expires_at is not None and expires_at <= time.time():
                # Expired entry – drop and treat as miss
                del self._store[key]
                _CACHE_MISSES[self.name] += 1
                _CACHE_ITEMS[self.name] = len(self._store)
                self._record_miss()
                self._record_items()
                return None

            _CACHE_HITS[self.name] += 1
            self._record_hit()
            return copy.deepcopy(value)

    def set(self, key: Any, value: Any, ttl: float) -> None:
        """Store value with TTL in seconds."""
        expires_at = time.time() + ttl if ttl is not None else None
        with self._lock:
            self._store[key] = (copy.deepcopy(value), expires_at)
            self._purge_expired_locked()
            _CACHE_ITEMS[self.name] = len(self._store)
            self._record_items()

    def purge_expired(self) -> int:
        """Manually purge expired entries and return number removed."""
        with self._lock:
            removed = self._purge_expired_locked()
            if removed:
                _CACHE_ITEMS[self.name] = len(self._store)
                self._record_items()
            return removed

    def size(self) -> int:
        """Return number of live entries (after purging expired)."""
        with self._lock:
            self._purge_expired_locked()
            return len(self._store)

    def _purge_expired_locked(self) -> int:
        now = time.time()
        removed = 0
        to_delete = [
            key for key, (_, expiry) in self._store.items()
            if expiry is not None and expiry <= now
        ]
        for key in to_delete:
            del self._store[key]
            removed += 1
        return removed

    def _get_metrics_exporter(self):
        if self._metrics_checked:
            return self._metrics_exporter
        try:
            from monitoring.prometheus_exporter import get_prometheus_exporter

            exporter = get_prometheus_exporter()
        except Exception:
            exporter = None
        self._metrics_exporter = exporter
        self._metrics_checked = True
        return exporter

    def _record_hit(self):
        exporter = self._get_metrics_exporter()
        if exporter:
            exporter.record_cache_hit(self.name)

    def _record_miss(self):
        exporter = self._get_metrics_exporter()
        if exporter:
            exporter.record_cache_miss(self.name)

    def _record_items(self):
        exporter = self._get_metrics_exporter()
        if exporter:
            exporter.set_cache_items(self.name, len(self._store))


def get_cache_metrics() -> Dict[str, Dict[str, int]]:
    """
    Return copy of cache metrics counters.

    Structure:
        {
            'hits': {'cache_name': count, ...},
            'misses': {'cache_name': count, ...},
            'items': {'cache_name': count, ...},
        }
    """
    return {
        "hits": dict(_CACHE_HITS),
        "misses": dict(_CACHE_MISSES),
        "items": dict(_CACHE_ITEMS),
    }

