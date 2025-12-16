# adapters/telegram/views/signals_history.py
"""
Telegram views for signal history display.
Shows per-coin signal history with TA, ML, Final scores.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone


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
        "📊 <b>Sinyal Geçmişi</b>",
        "",
        f"Toplam: <b>{stats.get('total_signals', 0)}</b> sinyal",
        f"Coin sayısı: <b>{stats.get('symbols', 0)}</b>",
        "",
        "<i>Görüntülemek için coin seçin:</i>",
    ]
    
    # Build coin buttons (2 per row)
    buttons = []
    row = []
    for sym in symbols:
        # Shorten symbol name
        short = sym.replace('-USDT-SWAP', '').replace('USDT', '')
        count = stats.get('per_symbol', {}).get(sym, 0)
        
        row.append({
            "text": f"{short} ({count})",
            "callback_data": f"ai:sig_coin|s={sym}"
        })
        
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Add action buttons
    buttons.append([
        {"text": "🗑️ Tümünü Temizle", "callback_data": "ai:act|t=clear_all_sig"},
        {"text": "🔄 Yenile", "callback_data": "ai:sig_hist"},
    ])
    buttons.append([
        {"text": "◀️ Ana Menü", "callback_data": "ai:main"},
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
        f"📈 <b>{short_symbol} Sinyal Geçmişi</b>",
        "",
    ]
    
    if not signals:
        lines.append("<i>Henüz sinyal kaydı yok.</i>")
    else:
        lines.append(f"Son <b>{len(signals)}</b> sinyal:")
        lines.append("")
        lines.append("<code>")
        lines.append("Zaman  | TA   ML   → Final  Dir")
        lines.append("─" * 32)
        
        for sig in signals[:20]:  # Max 20 in view
            time_str = sig['time'].strftime('%H:%M') if isinstance(sig['time'], datetime) else str(sig['time'])[:5]
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
            lines.append(f"\n<i>+{len(signals) - 20} daha...</i>")
    
    # Buttons
    buttons = [
        [
            {"text": "🔄 Yenile", "callback_data": f"ai:sig_coin|s={symbol}"},
            {"text": "🗑️ Temizle", "callback_data": f"ai:act|t=clear_sig|s={symbol}"},
        ],
        [
            {"text": "◀️ Coin Listesi", "callback_data": "ai:sig_hist"},
        ],
    ]
    
    return "\n".join(lines), buttons
