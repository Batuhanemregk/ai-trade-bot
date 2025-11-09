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
    """Build summary view text and button layout."""
    bar_id = context.get("bar_id", "-")
    run_id = context.get("run_id", "-")
    updated_at = context.get("generated_at")
    results = context.get("results", [])
    counts = context.get("counts", {})
    
    header = [
        "📊 <b>15m Analysis Summary</b>",
        f"Bar: <code>{bar_id}</code>",
        f"Run: <code>{run_id}</code>",
    ]
    if updated_at:
        try:
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            header.append(f"Updated: {dt.strftime('%H:%M:%S')} UTC")
        except ValueError:
            header.append(f"Updated: {updated_at}")
    
    totals_line = (
        f"LONG {counts.get('LONG', 0)} • "
        f"SHORT {counts.get('SHORT', 0)} • "
        f"FLAT {counts.get('FLAT', 0)} • "
        f"TOTAL {len(results)}"
    )
    
    lines = header + ["", totals_line, ""]
    
    # Show top results
    for entry in results[:12]:
        symbol = entry.get('symbol', 'UNKNOWN')
        score = entry.get('final_score', 0.0)
        grade = entry.get('grade', '-')
        decision = entry.get('decision', 'FLAT')
        ta_score = entry.get('ta_score', 0.0)
        ml_score = entry.get('ml_score', 0.0)
        news_score = entry.get('news_score', 0.0)
        risk_score = entry.get('risk_score', 0.0)
        lines.append(
            f"{symbol} • {score:.1f} ({grade}) • {decision} | "
            f"TA {ta_score:.1f} / ML {ml_score:.1f} / News {news_score:.1f} / Risk {risk_score:.1f}"
        )
    
    if len(results) > 12:
        lines.append(f"... {len(results) - 12} more symbols hidden")
    
    text = "\n".join(lines)
    
    # Build buttons (symbols rows of 2)
    buttons: List[List[Dict[str, str]]] = []
    row: List[Dict[str, str]] = []
    for entry in results[:8]:  # Limit buttons to top 8 symbols
        symbol = entry.get('symbol', 'UNKNOWN')
        score = entry.get('final_score', 0.0)
        label = f"{symbol} {score:.1f}"
        row.append({"text": label, "callback_data": f"ai:an|s={symbol}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    if not buttons:
        buttons = [[{"text": "Refresh", "callback_data": "ai:an"}]]
    else:
        # Add footer row for refresh
        buttons.append([
            {"text": "🔄 Refresh", "callback_data": "ai:an"},
        ])
    
    return text, buttons


def build_analysis_detail_view(
    context: Dict[str, Any],
    formatter: TelegramFormatter,
) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build symbol detail view text and button layout."""
    symbol = context.get('symbol', 'UNKNOWN')
    detail = context.get('detail', {}) or {}
    bar_id = context.get('bar_id', '-')
    run_id = context.get('run_id', '-')
    
    lines = [
        f"📈 <b>{symbol} Detail</b>",
        f"Bar: <code>{bar_id}</code>",
        f"Run: <code>{run_id}</code>",
        "",
    ]
    
    score = detail.get('final_score', 0.0)
    grade = detail.get('grade', '-')
    decision = detail.get('decision', 'FLAT')
    lines.append(f"Score: {score:.1f} ({grade}) • Decision: {decision}")
    
    lines.append(
        "Scores:"
        f"\n• TA {detail.get('ta_score', 0.0):.1f}"
        f"\n• ML {detail.get('ml_score', 0.0):.1f}"
        f"\n• News {detail.get('news_score', 0.0):.1f}"
        f"\n• Risk {detail.get('risk_score', 0.0):.1f}"
    )
    
    news_info = detail.get('news_info', {})
    if news_info:
        lines.append("")
        lines.append(
            f"📰 News: {news_info.get('type', 'general')} "
            f"({news_info.get('confidence', 0):.1f})"
        )
        lines.append(f"<i>{news_info.get('title', 'No recent news')}</i>")
    
    risk_info = detail.get('risk_info', {})
    if risk_info:
        lines.append("")
        lines.append(f"⚠️ Risk level: {risk_info.get('level', 'medium')}")
        factors = risk_info.get('factors', [])
        if factors:
            lines.append("<i>" + ", ".join(factors[:4]) + "</i>")
    
    text = "\n".join(lines)
    
    buttons = [
        [{"text": "⬅️ Geri", "callback_data": "ai:an"}],
    ]
    
    return text, buttons

