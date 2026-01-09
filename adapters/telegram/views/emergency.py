"""
Emergency View Builder
Builds the emergency control view with panic buttons for critical actions.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_emergency_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build emergency control view.
    
    Args:
        context: Context dict with current positions and risk status
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    open_positions = context.get('open_positions', 0)
    total_exposure = context.get('total_exposure', 0.0)
    total_upnl = context.get('total_upnl', 0.0)
    cb_state = context.get('cb_state', 'OFF')
    mode = context.get('mode', 'PAPER')
    
    # Header with warning
    header = "🚨 EMERGENCY CONTROLS 🚨"
    
    # Status summary
    upnl_emoji = "📈" if total_upnl >= 0 else "📉"
    cb_emoji = "✅" if cb_state == 'OFF' else "🔴"
    mode_emoji = "🔴" if mode.upper() == 'LIVE' else "🧪"
    
    lines = [
        header,
        "",
        f"⚠️ {mode_emoji} Mode: {mode.upper()}",
        f"📊 Open Positions: {open_positions}",
        f"💰 Total Exposure: ${formatter.format_number(total_exposure, 2)}",
        f"{upnl_emoji} Unrealized PnL: ${formatter.format_number(total_upnl, 2)}",
        f"{cb_emoji} Circuit Breaker: {cb_state}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ WARNING: The following actions cannot be undone!",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    text = "\n".join(lines)
    
    # Build emergency action buttons
    buttons = []
    
    # Close all positions button (only if positions exist)
    if open_positions > 0:
        buttons.append([
            {"text": "🔴 CLOSE ALL POSITIONS", "callback_data": "ai:act|t=close_all|back=main"}
        ])
    
    # Circuit breaker controls
    if cb_state == 'OFF':
        buttons.append([
            {"text": "🚫 Circuit Breaker ACTIVATE", "callback_data": "ai:act|t=cb_on|back=main"}
        ])
    else:
        buttons.append([
            {"text": "✅ Circuit Breaker DEACTIVATE", "callback_data": "ai:act|t=cb_off|back=main"}
        ])
    
    # Cancel all pending orders
    buttons.append([
        {"text": "❌ Cancel All Pending Orders", "callback_data": "ai:act|t=cancel_all|back=main"}
    ])
    
    # Navigation - prominent back button
    buttons.append([
        {"text": "◀️ BACK (Safe)", "callback_data": "ai:main"}
    ])
    
    return text, buttons
