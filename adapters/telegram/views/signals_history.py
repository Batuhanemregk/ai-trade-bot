# adapters/telegram/views/signals_history.py
"""
Telegram views for signal history display.
Shows per-coin signal history with TA, ML, Final scores.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta


def build_signal_history_menu(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build signal history main menu - coin selection.
    
    Args:
        context: Dict with 'symbols' list
        formatter: Message formatter
    
    Returns:
        Tuple of (text, buttons)
    """
    symbols = context.get('symbols', [])
    stats = context.get('stats', {})
    
    lines = [
        "📊 <b>Signal History</b>",
        "",
        f"Total: <b>{stats.get('total_signals', 0)}</b> signals | <b>{stats.get('symbols', 0)}</b> coins",
        "",
        "<i>Select a coin to view:</i>",
    ]
    
    # Build coin buttons (5 per row, max 5 rows = 25 coins)
    buttons = []
    row = []
    max_coin_rows = 5  # Limit to stay within 8 row telegram limit
    
    for sym in symbols:
        # Shorten symbol name
        short = sym.replace('-USDT-SWAP', '').replace('USDT', '')
        count = stats.get('per_symbol', {}).get(sym, 0)
        
        row.append({
            "text": f"{short}({count})",
            "callback_data": f"ai:sig_coin|s={sym}"
        })
        
        if len(row) == 5:
            buttons.append(row)
            row = []
            if len(buttons) >= max_coin_rows:
                break
    
    if row and len(buttons) < max_coin_rows:
        buttons.append(row)
    
    # Add action buttons
    buttons.append([
        {"text": "🗑️ Clear", "callback_data": "ai:act|t=clear_all_sig"},
        {"text": "🔄 Refresh", "callback_data": "ai:sig_hist"},
    ])
    buttons.append([
        {"text": "◀️ Main Menu", "callback_data": "ai:main"},
    ])
    
    return "\n".join(lines), buttons


def build_coin_signals_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build signal history view for a specific coin.
    
    Args:
        context: Dict with 'symbol', 'signals' list
        formatter: Message formatter
    
    Returns:
        Tuple of (text, buttons)
    """
    symbol = context.get('symbol', 'UNKNOWN')
    signals = context.get('signals', [])
    short_symbol = symbol.replace('-USDT-SWAP', '').replace('USDT', '')
    
    lines = [
        f"📈 <b>{short_symbol} Signal History</b>",
        "",
    ]
    
    if not signals:
        lines.append("<i>No signal records yet.</i>")
    else:
        lines.append(f"Last <b>{len(signals)}</b> signals:")
        lines.append("")
        lines.append("<code>")
        lines.append("Time   | TA   ML   → Final  Dir")
        lines.append("─" * 32)
        
        for sig in signals[:20]:  # Max 20 in view
            # Convert UTC to Turkey time (UTC+3)
            if isinstance(sig['time'], datetime):
                turkey_tz = timezone(timedelta(hours=3))
                local_time = sig['time'].astimezone(turkey_tz) if sig['time'].tzinfo else sig['time'].replace(tzinfo=timezone.utc).astimezone(turkey_tz)
                time_str = local_time.strftime('%H:%M')
            else:
                time_str = str(sig['time'])[:5]
            ta = sig.get('ta', 0)
            ml = sig.get('ml', 0)
            final = sig.get('final', 0)
            direction = sig.get('dir', 'flat')[:5].upper()
            
            # Direction emoji
            if direction.startswith('LONG'):
                dir_icon = '🟢'
            elif direction.startswith('SHORT'):
                dir_icon = '🔴'
            else:
                dir_icon = '⚪'
            
            lines.append(f"{time_str} | {ta:4.0f} {ml:4.0f} → {final:5.1f} {dir_icon}")
        
        lines.append("</code>")
        
        if len(signals) > 20:
            lines.append(f"\n<i>+{len(signals) - 20} more...</i>")
    
    # Buttons
    buttons = [
        [
            {"text": "🔄 Refresh", "callback_data": f"ai:sig_coin|s={symbol}"},
            {"text": "🗑️ Clear", "callback_data": f"ai:act|t=clear_sig|s={symbol}"},
        ],
        [
            {"text": "◀️ Coin List", "callback_data": "ai:sig_hist"},
        ],
    ]
    
    return "\n".join(lines), buttons
