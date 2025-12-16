# adapters/telegram/views/alerts_history.py
"""
Telegram views for alert/error history display.
Shows warnings and errors captured from logs.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone


def build_alerts_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build alerts history view.
    
    Args:
        context: Dict with 'alerts' list and 'counts' dict
        formatter: Message formatter
    
    Returns:
        Tuple of (text, buttons)
    """
    alerts = context.get('alerts', [])
    counts = context.get('counts', {})
    
    # Level icons
    level_icons = {
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔴'
    }
    
    lines = [
        "🚨 <b>Uyarı ve Hatalar</b>",
        "",
        f"⚠️ Warning: <b>{counts.get('WARNING', 0)}</b>",
        f"❌ Error: <b>{counts.get('ERROR', 0)}</b>",
        f"🔴 Critical: <b>{counts.get('CRITICAL', 0)}</b>",
        "",
    ]
    
    if not alerts:
        lines.append("<i>Henüz uyarı veya hata yok. 👍</i>")
    else:
        lines.append(f"Son <b>{len(alerts)}</b> mesaj:")
        lines.append("")
        
        for alert in alerts[:15]:  # Max 15 in view
            time_val = alert.get('time')
            if isinstance(time_val, datetime):
                time_str = time_val.strftime('%H:%M')
            else:
                time_str = '??:??'
            
            level = alert.get('level', 'INFO')
            icon = level_icons.get(level, '•')
            message = alert.get('message', '')[:60]
            source = alert.get('source', '')[:10]
            
            lines.append(f"{icon} <code>{time_str}</code> [{source}]")
            lines.append(f"   {message}")
            lines.append("")
        
        if len(alerts) > 15:
            lines.append(f"<i>+{len(alerts) - 15} daha...</i>")
    
    # Buttons
    buttons = [
        [
            {"text": "⚠️ Warnings", "callback_data": "ai:alerts|l=WARNING"},
            {"text": "❌ Errors", "callback_data": "ai:alerts|l=ERROR"},
        ],
        [
            {"text": "🔄 Yenile", "callback_data": "ai:alerts"},
            {"text": "🗑️ Temizle", "callback_data": "ai:act|t=clear_alerts"},
        ],
        [
            {"text": "◀️ Ana Menü", "callback_data": "ai:main"},
        ],
    ]
    
    return "\n".join(lines), buttons
