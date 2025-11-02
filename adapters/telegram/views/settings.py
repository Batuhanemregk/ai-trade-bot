"""
Settings View Builder
Builds the settings view with user preferences (compact, emojis, confirmations, timeframe).
"""

from typing import Dict, Any, List, Tuple

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_settings_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build settings view.
    
    Args:
        context: Context dict from ContextResolver.resolve_settings_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    compact_mode = context.get('compact_mode', True)
    emojis = context.get('emojis', False)
    confirmations = context.get('confirmations', True)
    timeframe = context.get('timeframe', '15m')
    timeframe_locked = context.get('timeframe_locked', True)
    
    # Header
    header = "Settings"
    
    # Settings lines
    compact_str = "ON" if compact_mode else "OFF"
    emojis_str = "ON" if emojis else "OFF"
    confirm_str = "ON" if confirmations else "OFF"
    tf_str = f"{timeframe}" + (" (locked by policy)" if timeframe_locked else "")
    
    lines = [
        header,
        "",
        f"Compact mode: {compact_str}",
        f"Emojis      : {emojis_str}",
        f"Confirmations: {confirm_str}",
        f"Timeframe   : {tf_str}",
        ""
    ]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text, timeframe=timeframe)
    
    # Build buttons
    buttons = [
        [
            {"text": "Save", "callback_data": "ai:set|a=save"},
            {"text": "Main", "callback_data": "ai:main"}
        ]
    ]
    
    return text, buttons

