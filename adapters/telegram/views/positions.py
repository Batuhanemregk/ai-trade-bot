"""
Positions View Builder
Builds the positions view with current open positions.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_positions_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build positions view.
    
    Args:
        context: Context dict from ContextResolver.resolve_positions_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    positions = context.get('positions', [])
    open_positions = context.get('open_positions', 0)
    last_update = context.get('last_update', datetime.now())
    issues = context.get('issues', [])
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"Positions • {open_positions} open • Last {time_str}"
    
    # Show issues if any
    issue_lines = []
    if issues:
        issue_lines.append("⚠️ " + ", ".join(issues))
    
    # Position lines
    position_lines = []
    for pos in positions:
        symbol = pos.get('symbol', 'UNKNOWN')
        side = pos.get('side', 'LONG')
        size = pos.get('size', 0.0)
        entry = pos.get('entry_price', 0.0)
        mark = pos.get('current_price', 0.0)
        upnl = pos.get('unrealized_pnl', 0.0)
        upnl_pct = pos.get('upnl_pct', 0.0)
        
        # Format side with emoji
        side_emoji = formatter.format_emoji('long' if side == 'LONG' else 'short', fallback=side)
        
        line = (
            f"{symbol}  {side_emoji} {side}  "
            f"size {size:.2f}  entry {formatter.format_number(entry, 2)}  "
            f"mark {formatter.format_number(mark, 2)}  "
            f"UPNL ${formatter.format_number(upnl, 2)} ({upnl_pct:.2f}%)"
        )
        position_lines.append(line)
    
    if not position_lines:
        position_lines.append("No open positions")
    
    # Build text
    lines = [header]
    if issue_lines:
        lines.append("")  # Empty line before issues
        lines.extend(issue_lines)
    lines.append("")  # Empty line before positions
    lines.extend(position_lines if position_lines else ["No open positions"])
    lines.append("")  # Empty line before footer
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "PnL", "callback_data": "ai:pnl"},
            {"text": "TP/SL", "callback_data": "ai:tpsl"},
            {"text": "Orders", "callback_data": "ai:ord"}
        ]
    ]
    
    return text, buttons

