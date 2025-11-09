from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from application.news_service import NewsService
from application.risk_service import RiskService


class StubAnalyzer:
    model = "stub-model"

    def __init__(self):
        self.calls = 0

    async def analyze_news_batch(self, articles, symbol, aliases):
        self.calls += 1
        return 58.0, ["GENERAL"], "ok", 0.3


def _news_policy(tmp_path):
    storage_paths = {
        'watermarks': str(tmp_path / "watermarks.json"),
        'digests': str(tmp_path / "digests.json"),
        'news_store': str(tmp_path / "news_store.json"),
    }
    return {
        'news': {'storage_paths': storage_paths},
        'news_llm': {'enabled': True, 'cache': {'ttl_minutes': 60}, 'digest': {'max_items_per_symbol': 5}},
        'news_scoring': {},
    }


def _sample_items():
    base = datetime.now(timezone.utc)
    return [{
        "title": "BTC consolidates",
        "body": "Markets pause ahead of macro data.",
        "url": "https://example.com/1",
        "source": {"name": "Wire"},
        "publishedAt": base.isoformat().replace("+00:00", "Z"),
    }]


@pytest.mark.asyncio
async def test_runtime_dedup_news_and_risk(tmp_path):
    news_service = NewsService(_news_policy(tmp_path))
    analyzer = StubAnalyzer()
    news_service.llm_analyzer = analyzer

    risk_service = RiskService({'trading': {'risk': {'risk_assessment': {'volatility_risk': {}, 'correlation_risk': {}}}}})
    risk_service._calculate_volatility_risk = AsyncMock(return_value=42.0)
    risk_service._calculate_liquidity_risk = AsyncMock(return_value=48.0)
    risk_service._calculate_correlation_risk = AsyncMock(return_value=54.0)
    risk_service._calculate_market_risk = lambda *_: 46.0

    news_items = _sample_items()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=5)

    risk_context = {
        "timeframe": "1m",
        "bar_id": "2025-01-01T00:00Z",
        "position_snapshot_hash": "state-hash",
    }
    market_data = {"trend": None, "main": None, "entry": None, "fourh": None}

    # Initial miss scheduling both services
    await news_service._analyze_news_with_llm(
        "BTC-USDT",
        news_items,
        timeframe="5m",
        window_start=window_start,
        window_end=now,
    )
    await risk_service.assess_risk("BTC-USDT", 55.0, "long", market_data, risk_context=risk_context)

    # Second call within same bar/window should hit caches
    await news_service._analyze_news_with_llm(
        "BTC-USDT",
        news_items,
        timeframe="5m",
        window_start=window_start,
        window_end=now,
    )
    await risk_service.assess_risk("BTC-USDT", 55.0, "long", market_data, risk_context=risk_context)

    assert analyzer.calls == 1
    assert risk_service._calculate_volatility_risk.await_count == 1

