"""
Telegram view preview script.
Sends all views directly to Telegram to preview formats.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"[OK] Loaded .env from: {env_file}")

# Add project root to path
sys.path.insert(0, str(project_root))

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


# Sample context data
SAMPLE_CONTEXTS = {
    'main': {
        'status': {'health': 'healthy', 'last_job': '02:30:15', 'queue': 0},
        'portfolio': {'balance': 1245.80, 'pnl_1d': 12.4, 'pnl_7d': 37.2},
        'risk': {'exposure_pct': 18.0, 'exposure_max': 60.0, 'open_positions': 3, 'max_positions': 20, 'cb_state': 'OFF'},
        'signals': [
            {'symbol': 'BTCUSDT', 'final_score': 65.8, 'grade': 'B', 'direction': 'LONG'},
            {'symbol': 'ETHUSDT', 'final_score': 44.1, 'grade': 'D', 'direction': 'FLAT'},
            {'symbol': 'SOLUSDT', 'final_score': 58.2, 'grade': 'C', 'direction': 'LONG'},
        ],
        'mode': 'paper',
        'symbols_count': 12
    },
    'signals': {
        'signals': [
            {
                'symbol': 'BTCUSDT',
                'final_score': 65.8,
                'grade': 'B',
                'direction': 'LONG',
                'ta': 75.0,
                'ml': 68.0,
                'news': 55.0,
                'risk': 42.0,
                'persist': 3,
                'persist_max': 5,
                'age': 2,
                'age_max': 6,
                'confirm': 1,
                'confirm_max': 2
            },
            {
                'symbol': 'ETHUSDT',
                'final_score': 44.1,
                'grade': 'D',
                'direction': 'FLAT',
                'ta': 40.0,
                'ml': 52.0,
                'news': 60.0,
                'risk': 35.0,
                'persist': 2,
                'persist_max': 5,
                'age': 1,
                'age_max': 6,
                'confirm': 0,
                'confirm_max': 2
            },
            {
                'symbol': 'SOLUSDT',
                'final_score': 58.2,
                'grade': 'C',
                'direction': 'LONG',
                'ta': 65.0,
                'ml': 55.0,
                'news': 50.0,
                'risk': 40.0,
                'persist': 3,
                'persist_max': 5,
                'age': 3,
                'age_max': 6,
                'confirm': 1,
                'confirm_max': 2
            },
        ],
        'timeframe': '15m',
        'last_update': datetime.now(timezone.utc)
    },
    'risk': {
        'exposure_pct': 18.0,
        'exposure_max': 60.0,
        'open_positions': 3,
        'max_positions': 20,
        'cb_state': 'OFF',
        'tier_alloc': {'T1': 40.0, 'T2': 35.0, 'T3': 25.0},
        'limits': {
            'max_position_size_pct': 10.0,
            'stop_loss_pct': 1.5,
            'leverage': 3.0
        },
        'guards': {
            'persist': 3,
            'age': 6,
            'confirm': 2,
            'hyster': '±5'
        },
        'alerts': []
    },
    'orders': {
        'orders': [
            {
                'timestamp': '01:54',
                'symbol': 'BTCUSDT',
                'type': 'MKT',
                'side': 'OPEN',
                'qty': 10.79,
                'price': 111155.2,
                'status': 'ok'
            },
            {
                'timestamp': '01:55',
                'symbol': 'BTCUSDT',
                'type': 'LIMIT',
                'side': 'SELL',
                'qty': 10.79,
                'price': 111094.5,
                'status': 'queued'
            },
            {
                'timestamp': '01:55',
                'symbol': 'BTCUSDT',
                'type': 'LIMIT',
                'side': 'SELL',
                'qty': 10.79,
                'price': 108130.3,
                'status': 'queued'
            },
        ],
        'page': 0,
        'has_prev': False,
        'has_next': True,
        'last_update': datetime.now(timezone.utc)
    },
    'tpsl': {
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'entry': 109032.6,
                'sl': 108130.3,
                'tp': 111094.5,
                'sl_atr': '-2ATR',
                'tp_atr': '+4ATR',
                'rr': '1:2'
            }
        ],
        'open_positions': 1,
        'last_update': datetime.now(timezone.utc)
    },
    'trailing': {
        'trailing_stops': [
            {
                'symbol': 'BTCUSDT',
                'active': True,
                'base_sl': 108130.3,
                'trail_price': 108980.0,
                'gain_r': 0.35
            }
        ],
        'last_update': datetime.now(timezone.utc)
    },
    'pnl': {
        'balance': 1245.80,
        'unrealized_pnl': -2.58,
        'realized_pnl': 47.12,
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'qty': 76.2,
                'entry': 109032.6,
                'mark': 108853.3,
                'upnl': -0.12,
                'upnl_pct': -1.31
            },
            {
                'symbol': 'SOLUSDT',
                'qty': 207.7,
                'entry': 189.06,
                'mark': 187.16,
                'upnl': -2.11,
                'upnl_pct': -3.01
            }
        ]
    },
    'positions': {
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
        'last_update': datetime.now(timezone.utc)
    },
    'settings': {
        'compact_mode': False,
        'emojis': True,
        'confirmations': True,
        'timeframe': '15m',
        'timeframe_locked': False
    }
}

VIEW_BUILDERS = {
    'main': build_main_view,
    'signals': build_signals_view,
    'risk': build_risk_view,
    'orders': build_orders_view,
    'tpsl': build_tpsl_view,
    'trailing': build_trailing_view,
    'pnl': build_pnl_view,
    'settings': build_settings_view,
    'positions': build_positions_view,
}


async def send_view(bot: Bot, chat_id: str, view_name: str, text: str, keyboard):
    """Send a view to Telegram."""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        print(f"[OK] {view_name} sent successfully")
    except TelegramError as e:
        print(f"[ERROR] Error sending {view_name}: {e}")


async def send_all_views(chat_id: str = None):
    """Send all views to Telegram for preview."""
    # Get token from env
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("[ERROR] TELEGRAM_BOT_TOKEN not found in .env")
        print("   Please add TELEGRAM_BOT_TOKEN=your_token_here to .env file")
        return
    
    # Get chat ID
    if not chat_id:
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not chat_id:
            # Try other common names
            chat_id = os.getenv('TELEGRAM_USER_ID') or os.getenv('TELEGRAM_ID')
            if not chat_id:
                print("[ERROR] TELEGRAM_CHAT_ID not found in .env")
                print("   Please add TELEGRAM_CHAT_ID=your_chat_id to .env file")
                print("   Or pass as argument: python scripts/send_telegram_views.py <chat_id>")
                return
    
    print(f"[INFO] Using token: {token[:10]}...")
    print(f"[INFO] Using chat ID: {chat_id}")
    
    bot = Bot(token=token)
    formatter = get_formatter()
    
    print(f"Sending all views to chat_id: {chat_id}\n")
    
    # Send each view
    for view_name in ['main', 'signals', 'risk', 'orders', 'tpsl', 'trailing', 'pnl', 'positions', 'settings']:
        try:
            context = SAMPLE_CONTEXTS.get(view_name, {})
            builder = VIEW_BUILDERS.get(view_name)
            
            if not builder:
                print(f"[WARN] No builder for {view_name}")
                continue
            
            # Build view
            text, buttons = builder(context, formatter)
            keyboard = build_keyboard(buttons)
            
            # Send with label
            label = f"\n{'='*20}\n{view_name.upper()} VIEW\n{'='*20}\n"
            await bot.send_message(
                chat_id=chat_id,
                text=label,
                parse_mode='HTML'
            )
            await asyncio.sleep(0.5)  # Small delay
            
            # Send view
            await send_view(bot, chat_id, view_name, text, keyboard)
            await asyncio.sleep(1)  # Delay between views
            
        except Exception as e:
            print(f"[ERROR] Error processing {view_name}: {e}")
    
    print(f"\n[OK] All views sent to chat_id: {chat_id}")


if __name__ == "__main__":
    chat_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(send_all_views(chat_id))

