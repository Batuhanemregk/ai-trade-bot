"""
Main Dashboard View Builder
Builds the main dashboard view with status, portfolio, risk, and signals summary.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_main_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build main dashboard view.
    
    Args:
        context: Context dict from ContextResolver.resolve_main_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons) where buttons is List[List[Dict[str, str]]]
    """
    if formatter is None:
        formatter = get_formatter()
    
    status = context.get('status', {})
    portfolio = context.get('portfolio', {})
    risk = context.get('risk', {})
    signals = context.get('signals', [])
    mode = context.get('mode', 'paper')
    symbols_count = context.get('symbols_count', 0)
    issues = context.get('issues', [])
    
    # Header with emoji
    mode_emoji = "🔴" if mode.upper() == 'LIVE' else "🧪"
    header = f"🤖 AiBotBS Dashboard • {mode_emoji}{mode} • {symbols_count} sym"
    
    # Show issues if any
    issue_lines = []
    if issues:
        issue_lines.append("⚠️ " + ", ".join(issues[:3]))  # Show first 3 issues
    
    # Extract status values
    health = status.get('health', 'unknown')
    last_job = status.get('last_job', 'N/A')
    queue = status.get('queue', 0)
    
    # Status block with emojis
    health_emoji = "🟢" if health == 'ok' else "🟡" if health == 'warning' else "🔴"
    status_line = f"📊 Status: {health_emoji}{health} • ⏰ Last {last_job} • 📋 Queue {queue}"
    
    # Extract portfolio values
    balance = portfolio.get('balance', 0.0)
    pnl_1d = portfolio.get('pnl_1d', 0.0)
    pnl_7d = portfolio.get('pnl_7d', 0.0)
    
    # Portfolio block with emojis
    pnl_emoji = "📈" if pnl_1d >= 0 else "📉"
    portfolio_line = f"💰 Portfolio: ${formatter.format_number(balance, 2)} • {pnl_emoji} 1D ${formatter.format_number(pnl_1d, 1)} / 7D ${formatter.format_number(pnl_7d, 1)}"
    
    # Extract risk values
    exposure_pct = risk.get('exposure_pct', 0.0)
    exposure_max = risk.get('exposure_max', 60.0)
    open_pos = risk.get('open_positions', 0)
    max_pos = risk.get('max_positions', 20)
    cb_state = risk.get('cb_state', 'OFF')
    
    # Risk block with emojis
    exp_emoji = "🟢" if exposure_pct < 30 else "🟡" if exposure_pct < 50 else "🔴"
    cb_emoji = "✅" if cb_state == 'OFF' else "🚨"
    risk_line = f"⚠️ Risk: {exp_emoji}Exp {exposure_pct:.0f}%/{exposure_max:.0f}% • 📊 Open {open_pos}/{max_pos} • {cb_emoji}CB {cb_state}"
    
    # Signals block with emojis
    signals_parts = []
    for signal in signals[:3]:  # Top 3 for main view
        symbol = signal.get('symbol', 'UNKNOWN')
        score = signal.get('final_score', 0.0)
        grade = signal.get('grade', 'D')
        direction = signal.get('direction', 'FLAT')
        
        # Direction emoji
        dir_emoji = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "⚪"
        signals_parts.append(f"{dir_emoji}{symbol} {score:.1f}({grade})")
    
    signals_line = f"📡 Signals: {' • '.join(signals_parts) if signals_parts else 'None'}"
    
    # Build text
    lines = [header]
    if issue_lines:
        lines.append("")  # Empty line before issues
        lines.extend(issue_lines)
    lines.append("")  # Empty line before blocks
    lines.extend([
        status_line,
        portfolio_line,
        risk_line,
        signals_line,
        ""
    ])
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text, timeframe="15m", mode=mode)
    
    # Build buttons
    buttons = [
        [
            {"text": "Signals", "callback_data": "ai:sig"},
            {"text": "Risk", "callback_data": "ai:risk"},
            {"text": "Positions", "callback_data": "ai:pos"},
            {"text": "Orders", "callback_data": "ai:ord"}
        ],
        [
            {"text": "PnL", "callback_data": "ai:pnl"},
            {"text": "TP/SL", "callback_data": "ai:tpsl"},
            {"text": "Trailing", "callback_data": "ai:trl"},
            {"text": "Settings", "callback_data": "ai:set"}
        ]
    ]
    
    return text, buttons

