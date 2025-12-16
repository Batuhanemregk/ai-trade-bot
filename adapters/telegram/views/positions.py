"""
Positions View Builder
Clean, compact position display.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_positions_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build positions view with clean, compact format."""
    if formatter is None:
        formatter = get_formatter()
    
    positions = context.get('positions', [])
    open_positions = context.get('open_positions', 0)
    last_update = context.get('last_update', datetime.now())
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    
    lines = [
        f"📊 Pozisyonlar │ {open_positions} açık",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    # Position list
    if positions:
        for pos in positions:
            symbol = pos.get('symbol', 'UNKNOWN')
            # Clean symbol
            sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '').replace('-USDT', '')[:5]
            
            side = pos.get('side', 'LONG').upper()
            size = pos.get('size', 0.0)
            entry = pos.get('entry_price', 0.0)
            upnl = pos.get('unrealized_pnl', 0.0)
            upnl_pct = pos.get('upnl_pct', 0.0)
            
            # Direction indicator
            side_icon = "▲" if side == 'LONG' else "▼"
            pnl_icon = "🟢" if upnl >= 0 else "🔴"
            
            # Compact line
            line = f"{sym:5} {side_icon} {side:5} │ {size:.4f} │ {pnl_icon} ${upnl:+.2f}"
            lines.append(line)
    else:
        lines.append("Açık pozisyon yok")
    
    lines.append("")
    lines.append(f"⏰ {time_str}")
    
    text = "\n".join(lines)
    
    # Buttons - per position actions
    buttons = []
    
    for pos in positions[:4]:
        symbol = pos.get('symbol', 'UNKNOWN')
        short_sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:5]
        side = pos.get('side', 'LONG').upper()
        side_icon = "🟢" if side == 'LONG' else "🔴"
        
        buttons.append([
            {"text": f"{side_icon} {short_sym} Kapat", "callback_data": f"ai:act|t=close|s={short_sym}"},
            {"text": f"🎯 TP/SL", "callback_data": f"ai:tpsl|s={short_sym}"},
        ])
    
    # Navigation
    buttons.append([
        {"text": "🔄 Yenile", "callback_data": "ai:pos|r=1"},
        {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
        {"text": "💰 PnL", "callback_data": "ai:pnl"},
    ])
    
    return text, buttons
