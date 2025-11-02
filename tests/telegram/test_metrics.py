"""
Tests for Telegram bot metrics integration.
Verifies that counters increase and metrics are recorded correctly.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from adapters.telegram.handlers import TelegramHandlers
from adapters.telegram.middleware import MetricsHook
from monitoring.prometheus_exporter import PrometheusExporter
from tests.telegram.conftest import mock_update, mock_context


@pytest.fixture
def metrics_hook():
    """Fixture for MetricsHook."""
    return MetricsHook()


@pytest.mark.asyncio
async def test_view_render_metrics():
    """Test that view render metrics are recorded."""
    handlers = TelegramHandlers()
    
    # Mock update
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.chat.id = 12345
    update.message.reply_text = AsyncMock()
    
    context = MagicMock()
    
    # Get exporter and check initial count
    exporter = handlers.metrics_hook._get_exporter()
    if exporter:
        initial_count = exporter.tg_views_render_total.labels(view='main')._value.get()
        
        # Trigger view render
        await handlers.handle_start(update, context)
        
        # Verify counter increased
        final_count = exporter.tg_views_render_total.labels(view='main')._value.get()
        assert final_count > initial_count, "View render counter should increase"
    else:
        pytest.skip("Prometheus exporter not available")


@pytest.mark.asyncio
async def test_callback_metrics():
    """Test that callback metrics are recorded."""
    handlers = TelegramHandlers()
    
    # Get exporter
    exporter = handlers.metrics_hook._get_exporter()
    if not exporter:
        pytest.skip("Prometheus exporter not available")
    
    # Mock callback query
    callback_query = MagicMock()
    callback_query.data = "ai:sig"
    callback_query.from_user.id = 12345
    callback_query.message = MagicMock()
    callback_query.message.chat.id = 12345
    callback_query.message.message_id = 1
    callback_query.message.text = "Test view"
    callback_query.edit_message_text = AsyncMock()
    callback_query.answer = AsyncMock()
    
    update = MagicMock()
    update.callback_query = callback_query
    update.effective_user.id = 12345
    
    context = MagicMock()
    
    # Record initial counter value
    initial_count = exporter.tg_callbacks_total.labels(view='sig', act='view')._value.get()
    
    # Trigger callback
    await handlers.handle_callback(update, context)
    
    # Verify counter increased
    final_count = exporter.tg_callbacks_total.labels(view='sig', act='view')._value.get()
    assert final_count > initial_count, "Callback counter should increase"


@pytest.mark.asyncio
async def test_error_metrics():
    """Test that error metrics are recorded."""
    handlers = TelegramHandlers()
    
    # Get exporter
    exporter = handlers.metrics_hook._get_exporter()
    if not exporter:
        pytest.skip("Prometheus exporter not available")
    
    # Record initial error count
    initial_count = exporter.tg_errors_total.labels(type='test_error')._value.get()
    
    # Trigger error
    handlers.metrics_hook.record_error('test_error', 'telegram')
    
    # Verify counter increased
    final_count = exporter.tg_errors_total.labels(type='test_error')._value.get()
    assert final_count > initial_count, "Error counter should increase"


def test_metrics_hook_recording():
    """Test that MetricsHook records metrics correctly."""
    metrics_hook = MetricsHook()
    
    # Get exporter
    exporter = metrics_hook._get_exporter()
    if not exporter:
        pytest.skip("Prometheus exporter not available")
    
    # Test view render recording
    metrics_hook.record_view_render('test_view', 50.0, 1024, success=True)
    
    # Verify counter
    count = exporter.tg_views_render_total.labels(view='test_view')._value.get()
    assert count > 0, "View render counter should be > 0"
    
    # Test callback recording
    metrics_hook.record_callback('test_view', 'test_action', success=True)
    
    # Verify counter
    count = exporter.tg_callbacks_total.labels(view='test_view', act='test_action')._value.get()
    assert count > 0, "Callback counter should be > 0"


@pytest.mark.asyncio
async def test_rate_limit_metrics():
    """Test that rate limit metrics are recorded."""
    handlers = TelegramHandlers()
    
    # Get exporter
    exporter = handlers.metrics_hook._get_exporter()
    if not exporter:
        pytest.skip("Prometheus exporter not available")
    
    # Record initial rate limit count
    initial_count = exporter.tg_rate_limited_total._value.get()
    
    # Trigger rate limit
    handlers.metrics_hook.record_rate_limit()
    
    # Verify counter increased
    final_count = exporter.tg_rate_limited_total._value.get()
    assert final_count > initial_count, "Rate limit counter should increase"


def test_prometheus_export():
    """Test that Prometheus exporter includes Telegram metrics."""
    exporter = PrometheusExporter()
    
    # Verify Telegram metrics exist
    assert hasattr(exporter, 'tg_views_render_total'), "Should have tg_views_render_total"
    assert hasattr(exporter, 'tg_callbacks_total'), "Should have tg_callbacks_total"
    assert hasattr(exporter, 'tg_errors_total'), "Should have tg_errors_total"
    assert hasattr(exporter, 'tg_rate_limited_total'), "Should have tg_rate_limited_total"
    assert hasattr(exporter, 'tg_latency_ms'), "Should have tg_latency_ms"
    assert hasattr(exporter, 'tg_message_size_bytes'), "Should have tg_message_size_bytes"

