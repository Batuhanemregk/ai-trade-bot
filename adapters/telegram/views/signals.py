"""
Signals View Builder
Builds the signals view with top 6 signals by confidence.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_signals_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build signals view.
    
    Args:
        context: Context dict from ContextResolver.resolve_signals_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    signals = context.get('signals', [])
    timeframe = context.get('timeframe', '15m')
    last_update = context.get('last_update', datetime.now())
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"Signals • TF {timeframe} • Last {time_str}"
    
    # Signals list (top 6)
    signal_lines = []
    for signal in signals[:6]:
        symbol = signal.get('symbol', 'UNKNOWN')
        final_score = signal.get('final_score', 0.0)
        grade = signal.get('grade', 'D')
        direction = signal.get('direction', 'FLAT')
        ta = signal.get('ta', 0.0)
        ml = signal.get('ml', 0.0)
        news = signal.get('news', 0.0)
        risk = signal.get('risk', 0.0)
        
        persist = signal.get('persist', 0)
        persist_max = signal.get('persist_max', 5)
        age = signal.get('age', 0)
        age_max = signal.get('age_max', 6)
        confirm = signal.get('confirm', 0)
        confirm_max = signal.get('confirm_max', 2)
        
        # Format signal line
        line = (
            f"{symbol}  Final {final_score:.1f} ({grade})  "
            f"Dir {direction}  TA {ta:.0f}  ML {ml:.0f}  "
            f"News {news:.0f}  Risk {risk:.0f}"
        )
        
        # Add persist/age/confirm if available
        if persist > 0:
            line += f"\n  Persist {persist}/{persist_max} Age {age}/{age_max} Confirm {confirm}/{confirm_max}"
        
        signal_lines.append(line)
    
    # Build text
    lines = [header, ""] + signal_lines + [""]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text, timeframe=timeframe)
    
    # Build buttons
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "Risk", "callback_data": "ai:risk"},
            {"text": "Positions", "callback_data": "ai:pos"},
            {"text": "Orders", "callback_data": "ai:ord"}
        ]
    ]
    
    return text, buttons

