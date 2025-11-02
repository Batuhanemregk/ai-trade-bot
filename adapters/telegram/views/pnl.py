"""
PnL View Builder
Builds the PnL view with balance, unrealized/realized PnL, and position breakdown.
"""

from typing import Dict, Any, List, Tuple

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_pnl_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build PnL view.
    
    Args:
        context: Context dict from ContextResolver.resolve_pnl_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    balance = context.get('balance', 0.0)
    unrealized_pnl = context.get('unrealized_pnl', 0.0)
    realized_pnl = context.get('realized_pnl', 0.0)
    positions = context.get('positions', [])
    
    # Header
    header = "PnL"
    
    # Summary
    summary_line = (
        f"Bal ${formatter.format_number(balance, 2)} • "
        f"UPNL ${formatter.format_number(unrealized_pnl, 2)} • "
        f"RPNL ${formatter.format_number(realized_pnl, 2)}"
    )
    
    # Position lines
    position_lines = []
    for pos in positions:
        symbol = pos.get('symbol', 'UNKNOWN')
        qty = pos.get('qty', 0.0)
        entry = pos.get('entry', 0.0)
        mark = pos.get('mark', 0.0)
        upnl = pos.get('upnl', 0.0)
        upnl_pct = pos.get('upnl_pct', 0.0)
        
        line = (
            f"{symbol}  qty {qty:.1f}  entry {formatter.format_number(entry, 2)}  "
            f"mark {formatter.format_number(mark, 2)}  "
            f"UPNL ${formatter.format_number(upnl, 2)} ({upnl_pct:.2f}%)"
        )
        position_lines.append(line)
    
    if not position_lines:
        position_lines.append("No open positions")
    
    # Build text
    lines = [header, summary_line, ""] + position_lines + [""]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = [
        [
            {"text": "Export CSV", "callback_data": "ai:pnl|a=csv"},
            {"text": "Main", "callback_data": "ai:main"}
        ]
    ]
    
    return text, buttons

