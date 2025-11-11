"""
Analysis-specific Telegram view builders.
Provides summary and detail cards for analysis results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from adapters.telegram.formatter import TelegramFormatter


def build_analysis_summary_view(
    context: Dict[str, Any],
    formatter: TelegramFormatter,
) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build summary view text and button layout in TELEGRAM_CARDS.md format."""
    results = context.get("results", [])
    timeframe = context.get("timeframe", "15m")
    last_update = context.get("last_update")
    mode = context.get("mode", "paper")
    
    # Parse last_update if it's a string
    if isinstance(last_update, str):
        try:
            last_update = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
        except ValueError:
            last_update = datetime.now(timezone.utc)
    elif last_update is None:
        last_update = datetime.now(timezone.utc)
    
    # Header: Analysis Summary • TF 15m • Last <hh:mm:ss>
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"Analysis Summary • TF {timeframe} • Last {time_str}"
    
    lines = [header, ""]
    
    # Show top 6 signals (matching SIGNALS view format)
    for entry in results[:6]:
        symbol = entry.get('symbol', 'UNKNOWN')
        final_score = entry.get('final_score', 0.0)
        grade = entry.get('grade', 'D')
        direction = entry.get('decision', 'FLAT')
        ta_score = entry.get('ta_score', 0.0)
        ml_score = entry.get('ml_score', 0.0)
        news_score = entry.get('news_score', 0.0)
        risk_score = entry.get('risk_score', 0.0)
        
        # Persist/age/confirm info
        persist_count = entry.get('persist_count', 0)
        persist_required = entry.get('persist_required', 5)
        age_bars = entry.get('age_bars', 0)
        age_max = entry.get('age_max', 6)
        confirm_count = entry.get('confirmation_bars', 0)
        confirm_required = entry.get('conf_required', 2)
        
        # Format signal line (matching TELEGRAM_CARDS.md format)
        line = f"{symbol}  Final {final_score:.1f} ({grade})  Dir {direction}"
        lines.append(line)
        
        # Component scores
        lines.append(f"TA {ta_score:.0f}  ML {ml_score:.0f}  News {news_score:.0f}  Risk {risk_score:.0f}")
        
        # Persist/Age/Confirm (if available)
        if persist_count > 0 or age_bars > 0 or confirm_count > 0:
            persist_str = f"Persist {persist_count}/{persist_required}"
            age_str = f"Age {age_bars}/{age_max}"
            confirm_str = f"Confirm {confirm_count}/{confirm_required}"
            lines.append(f"{persist_str}  {age_str}  {confirm_str}")
        
        lines.append("")  # Empty line between signals
    
    # Build text
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text, timeframe=timeframe, mode=mode, timestamp=last_update)
    
    # Build buttons: Symbol buttons (top 8) + Navigation buttons
    buttons: List[List[Dict[str, str]]] = []
    
    # Symbol buttons (2 per row, max 8 symbols)
    symbol_row: List[Dict[str, str]] = []
    for entry in results[:8]:
        symbol = entry.get('symbol', 'UNKNOWN')
        score = entry.get('final_score', 0.0)
        label = f"{symbol} {score:.1f}"
        symbol_row.append({"text": label, "callback_data": f"ai:an|s={symbol}"})
        if len(symbol_row) == 2:
            buttons.append(symbol_row)
            symbol_row = []
    if symbol_row:
        buttons.append(symbol_row)
    
    # Navigation buttons (matching SIGNALS view)
    buttons.append([
        {"text": "Main", "callback_data": "ai:main"},
        {"text": "Signals", "callback_data": "ai:sig"},
        {"text": "Risk", "callback_data": "ai:risk"},
        {"text": "Positions", "callback_data": "ai:pos"},
        {"text": "Orders", "callback_data": "ai:ord"}
    ])
    
    if not buttons:
        buttons = [[{"text": "Main", "callback_data": "ai:main"}]]
    
    return text, buttons


def build_analysis_detail_view(
    context: Dict[str, Any],
    formatter: TelegramFormatter,
) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build symbol detail view text and button layout."""
    symbol = context.get('symbol', 'UNKNOWN')
    detail = context.get('detail', {}) or {}
    timeframe = context.get('timeframe', '15m')
    last_update = context.get('last_update')
    mode = context.get('mode', 'paper')
    
    # Parse last_update if it's a string
    if isinstance(last_update, str):
        try:
            last_update = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
        except ValueError:
            last_update = datetime.now(timezone.utc)
    elif last_update is None:
        last_update = datetime.now(timezone.utc)
    
    # Header
    time_str = last_update.strftime('%H:%M:%S') if isinstance(last_update, datetime) else str(last_update)
    header = f"{symbol} Analysis • TF {timeframe} • Last {time_str}"
    lines = [header, ""]
    
    # Score and decision
    final_score = detail.get('final_score', 0.0)
    grade = detail.get('grade', 'D')
    direction = detail.get('decision', 'FLAT')
    lines.append(f"Final {final_score:.1f} ({grade})  Dir {direction}")
    lines.append("")
    
    # Component scores
    ta_score = detail.get('ta_score', 0.0)
    ml_score = detail.get('ml_score', 0.0)
    news_score = detail.get('news_score', 0.0)
    risk_score = detail.get('risk_score', 0.0)
    lines.append(f"TA {ta_score:.0f}  ML {ml_score:.0f}  News {news_score:.0f}  Risk {risk_score:.0f}")
    lines.append("")
    
    # Persist/Age/Confirm
    persist_count = detail.get('persist_count', 0)
    persist_required = detail.get('persist_required', 5)
    age_bars = detail.get('age_bars', 0)
    age_max = detail.get('age_max', 6)
    confirm_count = detail.get('confirmation_bars', 0)
    confirm_required = detail.get('conf_required', 2)
    
    if persist_count > 0 or age_bars > 0 or confirm_count > 0:
        persist_str = f"Persist {persist_count}/{persist_required}"
        age_str = f"Age {age_bars}/{age_max}"
        confirm_str = f"Confirm {confirm_count}/{confirm_required}"
        lines.append(f"{persist_str}  {age_str}  {confirm_str}")
        lines.append("")
    
    # News info
    news_info = detail.get('news_info', {})
    if news_info:
        news_type = news_info.get('type', 'general')
        news_confidence = news_info.get('confidence', 0.0)
        news_title = news_info.get('title', 'No recent news')
        lines.append(f"📰 News: {news_type} ({news_confidence:.1f})")
        if news_title and news_title != 'No recent news':
            # Truncate long titles
            if len(news_title) > 60:
                news_title = news_title[:57] + "..."
            lines.append(f"<i>{news_title}</i>")
        lines.append("")
    
    # Risk info
    risk_info = detail.get('risk_info', {})
    if risk_info:
        risk_level = risk_info.get('level', 'medium')
        factors = risk_info.get('factors', [])
        lines.append(f"⚠️ Risk level: {risk_level}")
        if factors:
            factors_str = ", ".join(factors[:4])
            if len(factors_str) > 60:
                factors_str = factors_str[:57] + "..."
            lines.append(f"<i>{factors_str}</i>")
        lines.append("")
    
    # Build text
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text, timeframe=timeframe, mode=mode, timestamp=last_update)
    
    # Build buttons: Navigation buttons (matching detail view pattern)
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "Signals", "callback_data": "ai:sig"},
            {"text": "Risk", "callback_data": "ai:risk"}
        ],
        [
            {"text": "⬅️ Back", "callback_data": "ai:an"}
        ]
    ]
    
    return text, buttons

