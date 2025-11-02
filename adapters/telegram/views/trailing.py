"""
Trailing Stops View Builder
Builds the trailing stops view with trail status, base SL, trail price, and gain.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_trailing_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build trailing stops view.
    
    Args:
        context: Context dict from ContextResolver.resolve_trailing_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    trailing_stops = context.get('trailing_stops', [])
    last_update = context.get('last_update', datetime.now())
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"Trailing Stops (job 5m) • Last {time_str}"
    
    # Trailing stop lines
    trail_lines = []
    for trail in trailing_stops:
        symbol = trail.get('symbol', 'UNKNOWN')
        active = trail.get('active', False)
        base_sl = trail.get('base_sl', 0.0)
        trail_price = trail.get('trail_price', 0.0)
        gain_r = trail.get('gain_r', 0.0)
        
        active_str = "ON" if active else "OFF"
        gain_str = f"+{gain_r:.2f}R" if gain_r >= 0 else f"{gain_r:.2f}R"
        
        line = (
            f"{symbol}  trail {active_str}  "
            f"base SL {formatter.format_number(base_sl, 2)}  "
            f"trail {formatter.format_number(trail_price, 2)}  "
            f"gain {gain_str}"
        )
        trail_lines.append(line)
    
    if not trail_lines:
        trail_lines.append("No active trailing stops")
    
    # Build text
    lines = [header, ""] + trail_lines + [""]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "TP/SL", "callback_data": "ai:tpsl"},
            {"text": "Positions", "callback_data": "ai:pos"}
        ]
    ]
    
    return text, buttons

