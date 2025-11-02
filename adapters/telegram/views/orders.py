"""
Orders View Builder
Builds the orders view with paginated recent orders.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_orders_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build orders view.
    
    Args:
        context: Context dict from ContextResolver.resolve_orders_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    orders = context.get('orders', [])
    page = context.get('page', 0)
    has_prev = context.get('has_prev', False)
    has_next = context.get('has_next', False)
    last_update = context.get('last_update', datetime.now())
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"Orders • Last {time_str}"
    
    # Orders list
    order_lines = []
    for order in orders:
        timestamp = order.get('timestamp', 'N/A')
        symbol = order.get('symbol', 'UNKNOWN')
        order_type = order.get('type', 'MKT')
        side = order.get('side', 'OPEN')
        qty = order.get('qty', 0.0)
        price = order.get('price', 0.0)
        status = order.get('status', 'ok')
        
        line = f"{timestamp}  {symbol}  {order_type}  {side}  qty {qty:.2f}  @{formatter.format_number(price, 2)}  {status}"
        order_lines.append(line)
    
    if not order_lines:
        order_lines.append("No recent orders")
    
    # Build text
    lines = [header, ""] + order_lines + [""]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = []
    
    # Pagination buttons
    nav_buttons = []
    if has_prev:
        nav_buttons.append({"text": "Prev", "callback_data": f"ai:ord|p=prev"})
    if has_next:
        nav_buttons.append({"text": "Next", "callback_data": f"ai:ord|p=next"})
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Navigation buttons
    buttons.append([
        {"text": "Main", "callback_data": "ai:main"}
    ])
    
    return text, buttons

