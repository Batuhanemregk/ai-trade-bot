"""
Orders View Builder
Clean order display with pagination.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_orders_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build orders view with clean format."""
    if formatter is None:
        formatter = get_formatter()
    
    orders = context.get('orders', [])
    page = context.get('page', 0)
    has_prev = context.get('has_prev', False)
    has_next = context.get('has_next', False)
    last_update = context.get('last_update', datetime.now())
    
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    
    lines = [
        f"📋 Emirler",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    if orders:
        for order in orders[:6]:
            symbol = order.get('symbol', 'UNKNOWN')
            sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:5]
            order_type = order.get('type', 'MKT')[:3]
            side = order.get('side', 'BUY')
            qty = order.get('qty', 0.0)
            price = order.get('price', 0.0)
            status = order.get('status', 'ok')
            
            side_icon = "▲" if side.upper() in ['BUY', 'LONG'] else "▼"
            status_icon = "✅" if status.lower() in ['filled', 'ok'] else "⏳" if status.lower() in ['pending', 'open'] else "❌"
            
            lines.append(f"{sym:5} {side_icon} {order_type} │ {qty:.3f} @ ${price:,.2f} {status_icon}")
    else:
        lines.append("Emir bulunamadı")
    
    lines.append("")
    lines.append(f"⏰ {time_str}")
    
    text = "\n".join(lines)
    
    # Buttons
    buttons = []
    
    # Cancel buttons for pending orders
    for order in orders[:3]:
        status = order.get('status', 'filled').lower()
        if status in ('pending', 'open', 'new'):
            order_id = order.get('id', order.get('order_id', ''))
            symbol = order.get('symbol', 'UNKNOWN').replace('-USDT-SWAP', '')[:5]
            if order_id:
                buttons.append([
                    {"text": f"❌ {symbol} İptal", "callback_data": f"ai:act|t=cancel|id={order_id[:8]}"}
                ])
    
    # Pagination
    nav = []
    if has_prev:
        nav.append({"text": "⬅️ Önceki", "callback_data": f"ai:ord|p={page-1}"})
    if has_next:
        nav.append({"text": "➡️ Sonraki", "callback_data": f"ai:ord|p={page+1}"})
    if nav:
        buttons.append(nav)
    
    # Navigation
    buttons.append([
        {"text": "🔄 Yenile", "callback_data": "ai:ord|r=1"},
        {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
        {"text": "📊 Pozisyonlar", "callback_data": "ai:pos"},
    ])
    
    return text, buttons
