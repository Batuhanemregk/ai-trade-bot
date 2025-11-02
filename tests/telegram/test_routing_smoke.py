"""
Smoke tests for Telegram bot routing and navigation.
Tests navigation roundtrips and callback routing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from adapters.telegram.handlers import TelegramHandlers
from adapters.telegram.client import TelegramClient
from tests.telegram.conftest import mock_update, mock_context


@pytest.mark.asyncio
async def test_start_navigation():
    """Test /start command navigation."""
    handlers = TelegramHandlers()
    
    # Mock update
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.chat.id = 12345
    update.message.reply_text = AsyncMock()
    
    context = MagicMock()
    
    # Should not raise
    await handlers.handle_start(update, context)
    
    # Verify message was sent
    assert update.message.reply_text.called


@pytest.mark.asyncio
async def test_callback_navigation_roundtrip():
    """Test navigation roundtrip: /start -> main -> signals -> main."""
    handlers = TelegramHandlers()
    
    # Mock callback query
    callback_query = MagicMock()
    callback_query.data = "ai:sig"
    callback_query.from_user.id = 12345
    callback_query.message = MagicMock()
    callback_query.message.chat.id = 12345
    callback_query.message.message_id = 1
    callback_query.message.text = "Main view"
    callback_query.edit_message_text = AsyncMock()
    callback_query.answer = AsyncMock()
    
    update = MagicMock()
    update.callback_query = callback_query
    update.effective_user.id = 12345
    
    context = MagicMock()
    
    # Test signals callback
    await handlers.handle_callback(update, context)
    
    # Verify message was edited (not new message sent)
    assert callback_query.edit_message_text.called
    
    # Test back to main
    callback_query.data = "ai:main"
    callback_query.edit_message_text.reset_mock()
    
    await handlers.handle_callback(update, context)
    
    # Verify message was edited again
    assert callback_query.edit_message_text.called


@pytest.mark.asyncio
async def test_all_view_callbacks():
    """Test that all view callbacks can be routed correctly."""
    handlers = TelegramHandlers()
    
    view_ids = ['main', 'sig', 'risk', 'ord', 'tpsl', 'trl', 'pnl', 'set', 'pos']
    
    for view_id in view_ids:
        callback_query = MagicMock()
        callback_query.data = f"ai:{view_id}"
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
        
        # Should not raise
        await handlers.handle_callback(update, context)
        
        # Verify callback was handled
        assert callback_query.answer.called or callback_query.edit_message_text.called, (
            f"View '{view_id}' callback not handled"
        )


@pytest.mark.asyncio
async def test_unknown_callback():
    """Test that unknown callbacks are handled gracefully."""
    handlers = TelegramHandlers()
    
    callback_query = MagicMock()
    callback_query.data = "ai:unknown"
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
    
    # Should not raise, but should handle gracefully
    await handlers.handle_callback(update, context)
    
    # Should either answer or edit
    assert callback_query.answer.called or callback_query.edit_message_text.called


@pytest.mark.asyncio
async def test_message_edit_on_navigation():
    """Test that message is edited (not sent) when navigating between views."""
    handlers = TelegramHandlers()
    
    # Disable rate limiting for this test
    handlers.rate_limiter = MagicMock()
    handlers.rate_limiter.is_allowed = MagicMock(return_value=True)
    
    callback_query = MagicMock()
    callback_query.data = "ai:risk"
    callback_query.from_user.id = 12345
    callback_query.message = MagicMock()
    callback_query.message.chat.id = 12345
    callback_query.message.message_id = 1
    callback_query.message.text = "Main view"
    callback_query.edit_message_text = AsyncMock()
    callback_query.answer = AsyncMock()
    
    update = MagicMock()
    update.callback_query = callback_query
    update.effective_user.id = 12345
    
    context = MagicMock()
    
    await handlers.handle_callback(update, context)
    
    # Verify edit_message_text was called (not send_message)
    assert callback_query.edit_message_text.called, "Should edit message, not send new one"
    
    # Verify message text and markup were provided
    call_args = callback_query.edit_message_text.call_args
    assert 'text' in call_args.kwargs or len(call_args.args) > 0, "Should provide new text"
    assert 'reply_markup' in call_args.kwargs, "Should provide reply markup"

