"""
Risk View Builder
Shows actual risk metrics only.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_risk_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build risk view with real data only."""
    if formatter is None:
        formatter = get_formatter()
    
    exposure_pct = min(context.get('exposure_pct', 0.0), 100)
    exposure_max = context.get('exposure_max', 60.0)
    open_pos = context.get('open_positions', 0)
    max_pos = context.get('max_positions', 20)
    cb_state = context.get('cb_state', 'OFF')
    alerts = context.get('alerts', [])
    
    # Status icons
    exp_icon = "🟢" if exposure_pct < 40 else "🟡" if exposure_pct < 70 else "🔴"
    cb_icon = "🟢" if cb_state == 'OFF' else "🔴"
    
    lines = [
        f"⚠️ Risk Durumu",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📊 Exposure  : {exp_icon} {exposure_pct:.1f}%",
        f"📈 Pozisyon  : {open_pos} / {max_pos}",
        f"🛡️ CB        : {cb_icon} {cb_state}",
        "",
    ]
    
    # Alerts
    if alerts:
        lines.append("── Uyarılar ──")
        for alert in alerts[:3]:
            lines.append(f"⚠️ {alert}")
        lines.append("")
    
    now = datetime.now()
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    text = "\n".join(lines)
    
    buttons = [
        [
            {"text": "🔄 Yenile", "callback_data": "ai:risk|r=1"},
            {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
        ]
    ]
    
    return text, buttons
