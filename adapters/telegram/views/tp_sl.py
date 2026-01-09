"""
TP/SL View Builder
Shows entry, stop loss, and take profit levels for positions.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_tpsl_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build TP/SL view with clean format."""
    if formatter is None:
        formatter = get_formatter()
    
    positions = context.get('positions', [])
    open_positions = context.get('open_positions', 0)
    
    lines = [
        f"🎯 TP/SL Seviyeleri │ {open_positions} poz",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    if positions:
        for pos in positions:
            symbol = pos.get('symbol', 'UNKNOWN')
            sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '').replace('-USDT', '')[:5]
            
            entry = pos.get('entry', 0.0)
            sl = pos.get('sl', 0.0)
            tp = pos.get('tp', 0.0)
            rr = pos.get('rr', '1:2')
            
            # Format prices
            if entry > 1000:
                entry_str = f"${entry:,.0f}"
                sl_str = f"${sl:,.0f}"
                tp_str = f"${tp:,.0f}"
            elif entry > 1:
                entry_str = f"${entry:.2f}"
                sl_str = f"${sl:.2f}"
                tp_str = f"${tp:.2f}"
            else:
                entry_str = f"${entry:.4f}"
                sl_str = f"${sl:.4f}"
                tp_str = f"${tp:.4f}"
            
            lines.append(f"{sym}")
            lines.append(f"  📍 Entry : {entry_str}")
            lines.append(f"  🔻 SL    : {sl_str}")
            lines.append(f"  🔺 TP    : {tp_str}")
            lines.append(f"  📊 R:R   : {rr}")
            lines.append("")
    else:
        lines.append("No open position")
        lines.append("")
    
    now = datetime.now()
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    text = "\n".join(lines)
    
    # Buttons
    buttons = []
    
    # Edit buttons per position
    for pos in positions[:3]:
        symbol = pos.get('symbol', 'UNKNOWN')
        short_sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:5]
        
        buttons.append([
            {"text": f"🔻 {short_sym} SL Ayarla", "callback_data": f"ai:act|t=set_sl|s={short_sym}"},
            {"text": f"🔺 {short_sym} TP Ayarla", "callback_data": f"ai:act|t=set_tp|s={short_sym}"},
        ])
    
    # Navigation
    buttons.append([
        {"text": "🔄 Yenile", "callback_data": "ai:tpsl|r=1"},
        {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
        {"text": "📊 Pozisyonlar", "callback_data": "ai:pos"},
    ])
    
    return text, buttons
