"""
Tests for callback data length enforcement (≤64B).
"""

import pytest
from adapters.telegram.callback_registry import get_callback_registry
from adapters.telegram.views import (
    build_main_view,
    build_signals_view,
    build_risk_view,
    build_orders_view,
    build_tpsl_view,
    build_trailing_view,
    build_pnl_view,
    build_settings_view,
    build_positions_view,
)
from adapters.telegram.keyboards import build_keyboard
from adapters.telegram.formatter import get_formatter
def test_all_callbacks_under_64_bytes():
    """Test that all callback data in all views is ≤64 bytes."""
    registry = get_callback_registry()
    formatter = get_formatter()
    
    # Sample context data (not using fixture)
    sample_ctx = {
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
    
    # Test all views
    views = [
        ('main', build_main_view, sample_ctx),
        ('signals', build_signals_view, {
            **sample_ctx,
            'signals': sample_ctx['signals'] * 3,
            'timeframe': '15m',
            'last_update': '2024-01-01T12:00:00Z'
        }),
        ('risk', build_risk_view, {
            'exposure_pct': 18.0,
            'exposure_max': 60.0,
            'open_positions': 3,
            'max_positions': 20,
            'cb_state': 'OFF',
            'tier_alloc': {'T1': 40.0, 'T2': 35.0, 'T3': 25.0},
            'limits': {'max_position_size_pct': 10.0, 'stop_loss_pct': 1.5, 'leverage': 3.0},
            'guards': {'persist': 3, 'age': 6, 'confirm': 2, 'hyster': '±5'},
            'alerts': []
        }),
        ('orders', build_orders_view, {
            'orders': [
                {'timestamp': '01:55', 'symbol': 'BTCUSDT', 'type': 'MKT', 'side': 'OPEN', 'qty': 10.79, 'price': 111155.2, 'status': 'ok'},
                {'timestamp': '01:55', 'symbol': 'BTCUSDT', 'type': 'LIMIT', 'side': 'SELL', 'qty': 10.79, 'price': 111094.5, 'status': 'queued'},
            ],
            'page': 0,
            'has_prev': False,
            'has_next': True,
        }),
        ('tpsl', build_tpsl_view, {
            'positions': [
                {'symbol': 'BTCUSDT', 'entry': 109032.6, 'sl': 108130.3, 'tp': 111094.5, 'sl_atr': '-2ATR', 'tp_atr': '+4ATR', 'rr': '1:2'},
            ],
            'open_positions': 1,
        }),
        ('trailing', build_trailing_view, {
            'trailing_stops': [
                {'symbol': 'BTCUSDT', 'active': True, 'base_sl': 108130.3, 'trail_price': 108980.0, 'gain_r': 0.35},
            ],
        }),
        ('pnl', build_pnl_view, {
            'balance': 1245.80,
            'unrealized_pnl': -2.58,
            'realized_pnl': 47.12,
            'positions': [
                {'symbol': 'BTCUSDT', 'qty': 76.2, 'entry': 109032.6, 'mark': 108853.3, 'upnl': -0.12, 'upnl_pct': -1.31},
                {'symbol': 'SOLUSDT', 'qty': 207.7, 'entry': 189.06, 'mark': 187.16, 'upnl': -2.11, 'upnl_pct': -3.01},
            ],
        }),
        ('settings', build_settings_view, {
            'compact_mode': False,
            'emojis': True,
            'confirmations': True,
            'timeframe': '15m',
            'timeframe_locked': False,
        }),
        ('positions', build_positions_view, {
            'positions': [
                {'symbol': 'BTCUSDT', 'side': 'LONG', 'size': 76.2, 'entry_price': 109032.6, 'current_price': 108853.3, 'unrealized_pnl': -0.12, 'upnl_pct': -1.31},
            ],
            'open_positions': 1,
        }),
    ]
    
    max_lengths = {}
    
    for view_name, view_builder, context in views:
        # Build view
        text, buttons = view_builder(context, formatter)
        
        # Build keyboard (this registers callbacks)
        keyboard = build_keyboard(buttons)
        
        # Check all callback data lengths
        max_len = 0
        if hasattr(keyboard, 'inline_keyboard'):
            for row in keyboard.inline_keyboard:
                for button in row:
                    if hasattr(button, 'callback_data') and button.callback_data:
                        callback_len = len(button.callback_data.encode('utf-8'))
                        max_len = max(max_len, callback_len)
                        
                        # Assert ≤64 bytes
                        assert callback_len <= 64, (
                            f"View '{view_name}' has callback data exceeding 64 bytes: "
                            f"'{button.callback_data}' ({callback_len}B)"
                        )
        
        max_lengths[view_name] = max_len
        print(f"View '{view_name}': max callback length = {max_len}B")
    
    # Print summary
    print("\n=== Callback Length Summary ===")
    for view_name, max_len in sorted(max_lengths.items()):
        print(f"{view_name:15} {max_len:3}B")


def test_callback_registry_compression():
    """Test that callback registry compresses long callbacks."""
    registry = get_callback_registry()
    
    # Test compression with key shortening
    long_callback = "ai:sig|sym=BTCUSDT|page=next|action=open"
    registered = registry.register(long_callback)
    
    # Resolve back
    resolved = registry.resolve(registered)
    
    # Verify it's compressed and still resolves correctly
    assert len(registered.encode('utf-8')) <= 64, "Compressed callback should be ≤64B"
    assert resolved is not None, "Should resolve compressed callback"
    
    # Verify keys are expanded
    assert 'sym=' in resolved or 'symbol=' in resolved, "Keys should be expanded on resolve"


def test_callback_schema_parsing():
    """Test that callback schema (ai:*) is correctly parsed."""
    from adapters.telegram.handlers import TelegramHandlers
    
    handlers = TelegramHandlers()
    
    # Test valid callbacks (note: _parse_callback returns 'view' not 'view_id')
    test_cases = [
        ("ai:main", {"view": "main", "params": {}}),
        ("ai:sig|s=BTC", {"view": "sig", "params": {"s": "BTC"}}),
        ("ai:ord|s=BTC|p=next", {"view": "ord", "params": {"s": "BTC", "p": "next"}}),
        ("ai:tpsl|s=ETH|a=edit", {"view": "tpsl", "params": {"s": "ETH", "a": "edit"}}),
    ]
    
    for callback_data, expected in test_cases:
        parsed = handlers._parse_callback(callback_data)
        
        assert parsed['view'] == expected['view'], f"View mismatch for {callback_data}: got {parsed.get('view')}, expected {expected['view']}"
        assert parsed['params'] == expected['params'], f"Params mismatch for {callback_data}: got {parsed.get('params')}, expected {expected['params']}"

