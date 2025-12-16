"""
PnL View Builder
Clean PnL display with balance and position breakdown.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_pnl_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build PnL view with clean format."""
    if formatter is None:
        formatter = get_formatter()
    
    balance = context.get('balance', 0.0)
    unrealized_pnl = context.get('unrealized_pnl', 0.0)
    realized_pnl = context.get('realized_pnl', 0.0)
    positions = context.get('positions', [])
    
    # Determine PnL status
    total_pnl = unrealized_pnl + realized_pnl
    pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
    
    lines = [
        f"💰 PnL Özeti",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
        f"💼 Balance   : ${balance:,.2f}",
        f"📈 UPNL      : ${unrealized_pnl:+,.2f}",
        f"📊 RPNL      : ${realized_pnl:+,.2f}",
        f"{pnl_icon} Toplam    : ${total_pnl:+,.2f}",
        "",
    ]
    
    # Position breakdown
    if positions:
        lines.append("── Pozisyon Detay ──")
        for pos in positions[:5]:
            symbol = pos.get('symbol', 'UNKNOWN')
            sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:5]
            qty = pos.get('qty', 0.0)
            upnl = pos.get('upnl', 0.0)
            upnl_pct = pos.get('upnl_pct', 0.0)
            icon = "🟢" if upnl >= 0 else "🔴"
            
            lines.append(f"{sym:5} │ {qty:.2f} │ {icon} ${upnl:+.2f} ({upnl_pct:+.1f}%)")
        lines.append("")
    
    now = datetime.now()
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    text = "\n".join(lines)
    
    # Buttons
    buttons = [
        [
            {"text": "🔄 Yenile", "callback_data": "ai:pnl|r=1"},
            {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
            {"text": "📊 Pozisyonlar", "callback_data": "ai:pos"},
        ]
    ]
    
    return text, buttons
