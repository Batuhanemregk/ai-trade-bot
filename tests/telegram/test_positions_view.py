"""
Tests for positions view.
Verifies that positions view renders correctly and within size limits.
"""

import pytest
from adapters.telegram.views.positions import build_positions_view
from adapters.telegram.formatter import get_formatter
from adapters.telegram.keyboards import build_keyboard


def test_positions_view_renders():
    """Test that positions view renders non-empty text."""
    formatter = get_formatter()
    
    context = {
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'size': 76.2,
                'entry_price': 109032.6,
                'current_price': 108853.3,
                'unrealized_pnl': -0.12,
                'upnl_pct': -1.31
            },
            {
                'symbol': 'SOLUSDT',
                'side': 'SHORT',
                'size': 207.7,
                'entry_price': 189.06,
                'current_price': 187.16,
                'unrealized_pnl': -2.11,
                'upnl_pct': -3.01
            }
        ],
        'open_positions': 2,
        'last_update': '2024-01-01T12:00:00Z'
    }
    
    text, buttons = build_positions_view(context, formatter)
    
    # Verify text is non-empty
    assert text, "Positions view should have non-empty text"
    assert len(text) > 0, "Positions view text should have length > 0"
    
    # Verify buttons exist
    assert buttons, "Positions view should have buttons"
    assert len(buttons) > 0, "Positions view should have at least one button row"


def test_positions_view_size_limit():
    """Test that positions view stays within 3500 character limit."""
    formatter = get_formatter()
    
    # Create context with many positions
    context = {
        'positions': [
            {
                'symbol': f'SYMBOL{i}',
                'side': 'LONG' if i % 2 == 0 else 'SHORT',
                'size': 100.0 + i,
                'entry_price': 1000.0 + i,
                'current_price': 1005.0 + i,
                'unrealized_pnl': 5.0 + i,
                'upnl_pct': 0.5 + i * 0.1
            }
            for i in range(20)  # Many positions
        ],
        'open_positions': 20,
        'last_update': '2024-01-01T12:00:00Z'
    }
    
    text, buttons = build_positions_view(context, formatter)
    
    # Verify size limit
    assert len(text) <= 3500, f"Positions view text should be ≤3500 chars (got {len(text)})"


def test_positions_view_empty():
    """Test that positions view handles empty positions gracefully."""
    formatter = get_formatter()
    
    context = {
        'positions': [],
        'open_positions': 0,
        'last_update': '2024-01-01T12:00:00Z'
    }
    
    text, buttons = build_positions_view(context, formatter)
    
    # Should still render
    assert text, "Positions view should render even with no positions"
    assert 'No open positions' in text or 'open' in text.lower(), "Should indicate no positions"
    
    # Should still have buttons
    assert buttons, "Positions view should have buttons even with no positions"


def test_positions_view_callbacks():
    """Test that positions view callbacks are ≤64 bytes."""
    formatter = get_formatter()
    
    context = {
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'size': 76.2,
                'entry_price': 109032.6,
                'current_price': 108853.3,
                'unrealized_pnl': -0.12,
                'upnl_pct': -1.31
            }
        ],
        'open_positions': 1,
        'last_update': '2024-01-01T12:00:00Z'
    }
    
    text, buttons = build_positions_view(context, formatter)
    keyboard = build_keyboard(buttons)
    
    # Check all callback data lengths
    if hasattr(keyboard, 'inline_keyboard'):
        for row in keyboard.inline_keyboard:
            for button in row:
                if hasattr(button, 'callback_data') and button.callback_data:
                    callback_len = len(button.callback_data.encode('utf-8'))
                    assert callback_len <= 64, (
                        f"Positions view callback exceeds 64 bytes: "
                        f"'{button.callback_data}' ({callback_len}B)"
                    )


@pytest.mark.asyncio
async def test_positions_view_integration():
    """Integration test for positions view with real handler."""
    from adapters.telegram.handlers import TelegramHandlers
    from unittest.mock import MagicMock, AsyncMock
    
    handlers = TelegramHandlers()
    
    # Mock update
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.chat.id = 12345
    update.message.reply_text = AsyncMock()
    
    context = MagicMock()
    
    # Should not raise
    await handlers.handle_positions(update, context)
    
    # Verify message was sent
    assert update.message.reply_text.called

