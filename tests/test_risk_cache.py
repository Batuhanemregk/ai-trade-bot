from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from application.risk_service import RiskService


def _policy():
    return {
        'trading': {
            'risk': {
                'risk_assessment': {
                    'volatility_risk': {},
                    'correlation_risk': {'market_cap_tiers': {}},
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_risk_cache_hit_and_state_change():
    service = RiskService(_policy())

    service._calculate_volatility_risk = AsyncMock(return_value=40.0)
    service._calculate_liquidity_risk = AsyncMock(return_value=50.0)
    service._calculate_correlation_risk = AsyncMock(return_value=55.0)
    service._calculate_market_risk = lambda *_: 45.0

    context = {
        "timeframe": "1m",
        "bar_id": datetime.now(timezone.utc).isoformat(),
        "position_snapshot_hash": "state-v1",
    }

    market_data = {"trend": None, "main": None, "entry": None, "fourh": None}

    await service.assess_risk("BTC-USDT", 55.0, "long", market_data, risk_context=context)
    assert service._calculate_volatility_risk.await_count == 1

    await service.assess_risk("BTC-USDT", 55.0, "long", market_data, risk_context=context)
    assert service._calculate_volatility_risk.await_count == 1

    context["position_snapshot_hash"] = "state-v2"
    await service.assess_risk("BTC-USDT", 55.0, "long", market_data, risk_context=context)
    assert service._calculate_volatility_risk.await_count == 2

