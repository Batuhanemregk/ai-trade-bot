"""
Signals View Builder
Shows real signals with gate data (persist, age, confirmation).
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_signals_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build signals view with real data including gate info."""
    if formatter is None:
        formatter = get_formatter()
    
    signals = context.get('signals', [])
    timeframe = context.get('timeframe', '15m')
    last_update = context.get('last_update', datetime.now())
    issues = context.get('issues', [])
    
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    
    lines = [
        f"📡 Sinyaller │ {timeframe}",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    # Show issues if any
    if issues:
        for issue in issues[:2]:
            lines.append(f"⚠️ {issue}")
        lines.append("")
    
    # Signal list with gate data
    if signals:
        for signal in signals[:6]:
            symbol = signal.get('symbol', 'UNKNOWN')
            sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '').replace('-USDT', '')[:5]
            
            score = signal.get('final_score', 0.0)
            grade = signal.get('grade', '?')
            direction = signal.get('direction', 'FLAT')
            
            # Gate data
            persist = signal.get('persist', 0)
            persist_max = signal.get('persist_max', 5)
            age = signal.get('age', 0)
            age_max = signal.get('age_max', 6)
            confirm = signal.get('confirm', 0)
            confirm_max = signal.get('confirm_max', 2)
            
            # Component scores
            ta = signal.get('ta', 0)
            ml = signal.get('ml', 0)
            
            # Direction indicator
            if direction == 'LONG':
                dir_icon = "▲"
            elif direction == 'SHORT':
                dir_icon = "▼"
            else:
                dir_icon = "─"
            
            # Grade color
            if grade in ['A+', 'A']:
                grade_icon = "🟢"
            elif grade in ['B+', 'B']:
                grade_icon = "🟡"
            else:
                grade_icon = "🔴"
            
            # Main line
            lines.append(f"{sym:5} {dir_icon} {score:4.0f} {grade:2} {grade_icon}")
            
            # Gate line (if has meaningful data)
            if persist > 0 or age > 0:
                lines.append(f"  P:{persist}/{persist_max} A:{age}/{age_max} C:{confirm}/{confirm_max}")
            
            # Component scores (compact)
            if ta > 0 or ml > 0:
                lines.append(f"  TA:{ta:.0f} ML:{ml:.0f}")
            
            lines.append("")
    else:
        lines.append("No signals found")
        lines.append("")
    
    lines.append(f"⏰ {time_str}")
    
    text = "\n".join(lines)
    
    buttons = [
        [
            {"text": "🔄 Yenile", "callback_data": "ai:sig|r=1"},
            {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
        ]
    ]
    
    return text, buttons
