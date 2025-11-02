"""
Test fixtures for Telegram bot tests.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

from adapters.telegram.callback_registry import CallbackRegistry
from adapters.telegram.formatter import TelegramFormatter
from adapters.telegram.context_resolver import ContextResolver
from adapters.telegram.middleware import RateLimiter, MetricsHook


@pytest.fixture
def callback_registry():
    """Fixture for CallbackRegistry."""
    return CallbackRegistry()


@pytest.fixture
def formatter():
    """Fixture for TelegramFormatter."""
    return TelegramFormatter(use_emojis=False, compact_mode=False)


@pytest.fixture
def context_resolver():
    """Fixture for ContextResolver."""
    return ContextResolver()


@pytest.fixture
def rate_limiter():
    """Fixture for RateLimiter."""
    return RateLimiter()


@pytest.fixture
def metrics_hook():
    """Fixture for MetricsHook."""
    return MetricsHook()


@pytest.fixture
def mock_update():
    """Fixture for mock Telegram Update."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.chat.id = 12345
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message.chat.id = 12345
    update.callback_query.message.message_id = 1
    return update


@pytest.fixture
def mock_context():
    """Fixture for mock Telegram Context."""
    context = MagicMock()
    context.args = []
    return context


@pytest.fixture
def sample_context():
    """Fixture for sample view context data."""
    return {
        'status': {'health': 'healthy', 'last_job': '02:30:15', 'queue': 0},
        'portfolio': {'balance': 1245.80, 'pnl_1d': 12.4, 'pnl_7d': 37.2},
        'risk': {'exposure_pct': 18.0, 'exposure_max': 60.0, 'open_positions': 3, 'max_positions': 20, 'cb_state': 'OFF'},
        'signals': [
            {'symbol': 'BTCUSDT', 'final_score': 65.8, 'grade': 'B', 'direction': 'LONG'},
            {'symbol': 'ETHUSDT', 'final_score': 44.1, 'grade': 'D', 'direction': 'FLAT'},
        ],
        'mode': 'paper',
        'symbols_count': 12
    }

