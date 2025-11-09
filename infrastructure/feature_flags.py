"""
Feature flag utilities for runtime behaviour toggles.
Centralises environment-driven switches with sane defaults.
"""

from __future__ import annotations

import os


def _get_bool(name: str, default: bool) -> bool:
    """Read boolean flag from environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    """Read integer flag from environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Scheduler / deduplication flags
DEDUP_ENABLED: bool = _get_bool("DEDUP_ENABLED", True)
DEDUP_CACHE_SECONDS: int = _get_int("DEDUP_CACHE_SECONDS", 3600)  # 1 hour default
DEDUP_CACHE_MAX_ITEMS: int = _get_int("DEDUP_CACHE_MAX_ITEMS", 128)

# News & risk dedup flags
NEWS_DEDUP_ENABLED: bool = _get_bool("NEWS_DEDUP_ENABLED", True)
NEWS_DEDUP_TTL_SECONDS: int = _get_int("NEWS_DEDUP_TTL_SECONDS", 300)
RISK_CACHE_ENABLED: bool = _get_bool("RISK_CACHE_ENABLED", True)
RISK_CACHE_TTL_SECONDS: int = _get_int("RISK_CACHE_TTL_SECONDS", 75)

# Telegram integration
TELEGRAM_MOCK_ENABLED: bool = _get_bool("TELEGRAM_MOCK", False)


__all__ = [
    "DEDUP_ENABLED",
    "DEDUP_CACHE_SECONDS",
    "DEDUP_CACHE_MAX_ITEMS",
    "NEWS_DEDUP_ENABLED",
    "NEWS_DEDUP_TTL_SECONDS",
    "RISK_CACHE_ENABLED",
    "RISK_CACHE_TTL_SECONDS",
    "TELEGRAM_MOCK_ENABLED",
]

