"""
TP/SL View Builder
Builds the TP/SL brackets view with entry, SL, TP, and R:R for each position.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_tpsl_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build TP/SL view.
    
    Args:
        context: Context dict from ContextResolver.resolve_tpsl_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    positions = context.get('positions', [])
    open_positions = context.get('open_positions', 0)
    
    # Header
    header = f"TP/SL Brackets • {open_positions} pos"
    
    # Position lines
    position_lines = []
    for pos in positions:
        symbol = pos.get('symbol', 'UNKNOWN')
        entry = pos.get('entry', 0.0)
        sl = pos.get('sl', 0.0)
        tp = pos.get('tp', 0.0)
        sl_atr = pos.get('sl_atr', '-2ATR')
        tp_atr = pos.get('tp_atr', '+4ATR')
        rr = pos.get('rr', '1:2')
        
        line = (
            f"{symbol}  entry {formatter.format_number(entry, 2)}  "
            f"SL {formatter.format_number(sl, 2)} ({sl_atr})  "
            f"TP {formatter.format_number(tp, 2)} ({tp_atr})  "
            f"R:R {rr}"
        )
        position_lines.append(line)
    
    if not position_lines:
        position_lines.append("No open positions")
    
    # Build text
    lines = [header, ""] + position_lines + [""]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "Trailing", "callback_data": "ai:trl"},
            {"text": "Positions", "callback_data": "ai:pos"}
        ]
    ]
    
    return text, buttons

