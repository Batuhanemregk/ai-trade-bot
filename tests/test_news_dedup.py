from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from application.news_service import NewsService


class DummyAnalyzer:
    model = "dummy-model"

    def __init__(self):
        self.calls: List[int] = []

    async def analyze_news_batch(self, articles: List[Dict[str, Any]], symbol: str, aliases: Dict[str, Any]):
        self.calls.append(len(articles))
        return 62.0, ["GENERAL"], "ok", 0.4


def _build_policy(tmp_path):
    storage_paths = {
        'watermarks': str(tmp_path / "watermarks.json"),
        'digests': str(tmp_path / "digests.json"),
        'news_store': str(tmp_path / "news_store.json"),
    }
    return {
        'news': {'storage_paths': storage_paths},
        'news_llm': {'enabled': True, 'cache': {'ttl_minutes': 60}, 'digest': {'max_items_per_symbol': 10}},
        'news_scoring': {},
    }


def _sample_news():
    published = datetime.now(timezone.utc) - timedelta(minutes=2)
    return [
        {
            "title": "BTC rallies on market optimism",
            "body": "Bitcoin extends gains amid macro clarity.",
            "url": "https://example.com/btc-rally",
            "source": {"name": "ExampleWire"},
            "publishedAt": published.isoformat().replace("+00:00", "Z"),
        },
        {
            "title": "Institutional flows increase",
            "body": "Funds report larger inflows to crypto assets.",
            "url": "https://example.com/inflows",
            "source": {"name": "ExampleWire"},
            "publishedAt": (published - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        },
    ]


@pytest.mark.asyncio
async def test_news_dedup_skips_duplicate_llm_calls(tmp_path):
    policy = _build_policy(tmp_path)
    service = NewsService(policy)
    dummy_analyzer = DummyAnalyzer()
    service.llm_analyzer = dummy_analyzer

    news_items = _sample_news()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=5)

    await service._analyze_news_with_llm(
        "BTC-USDT",
        news_items,
        timeframe="5m",
        window_start=window_start,
        window_end=now,
    )
    assert len(dummy_analyzer.calls) == 1

    await service._analyze_news_with_llm(
        "BTC-USDT",
        news_items,
        timeframe="5m",
        window_start=window_start,
        window_end=now,
    )
    assert len(dummy_analyzer.calls) == 1

    extended_window = now + timedelta(minutes=5)
    mutated_articles = [dict(item) for item in news_items]
    mutated_articles[0]["title"] = "BTC pulls back on profit taking"
    await service._analyze_news_with_llm(
        "BTC-USDT",
        mutated_articles,
        timeframe="5m",
        window_start=window_start,
        window_end=extended_window,
    )
    assert len(dummy_analyzer.calls) == 2

