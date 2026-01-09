"""
Main Dashboard View Builder
Clean, minimal design for the main trading dashboard.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
import json
from pathlib import Path

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def _is_trading_paused() -> bool:
    """Check if trading is paused from runtime_state.json."""
    try:
        state_file = Path("data/runtime_state.json")
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            return state.get('trading_paused', False)
    except:
        pass
    return False


def build_main_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build main dashboard view with clean, minimal design."""
    if formatter is None:
        formatter = get_formatter()
    
    status = context.get('status', {})
    portfolio = context.get('portfolio', {})
    risk = context.get('risk', {})
    signals = context.get('signals', [])
    mode = context.get('mode', 'paper')
    
    # Extract values
    balance = portfolio.get('balance', 0.0)
    pnl_1d = portfolio.get('pnl_1d', 0.0)
    pnl_7d = portfolio.get('pnl_7d', 0.0)
    open_pos = risk.get('open_positions', 0)
    exposure_pct = min(risk.get('exposure_pct', 0.0), 100)  # Cap at 100%
    cb_state = risk.get('cb_state', 'OFF')
    health = status.get('health', 'unknown')
    
    # Check trading pause status
    trading_paused = _is_trading_paused()
    
    # Mode indicator
    mode_icon = "🔴" if mode.upper() == 'LIVE' else "🧪"
    health_icon = "🟢" if health == 'ok' else "🟡" if health == 'warning' else "🔴"
    trading_status = "⏸️ PAUSED" if trading_paused else "▶️ ACTIVE"
    
    # Build clean text
    lines = [
        f"📊 AI Trading Bot",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"💼 Balance: <b>${balance:,.2f}</b>",
        f"",
        f"📊 Positions: {open_pos}",
        f"⚡ Exposure: {exposure_pct:.0f}%",
        f"🛡️ Circuit Breaker: {cb_state}",
        f"🤖 Trading: {trading_status}",
    ]
    
    # Top signals (max 3, compact format) - only show if there are signals
    if signals:
        lines.append(f"")
        signal_parts = []
        for sig in signals[:3]:
            sym = sig.get('symbol', '???').replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:4]
            score = sig.get('final_score', 0)
            dir_icon = "▲" if sig.get('direction') == 'LONG' else "▼" if sig.get('direction') == 'SHORT' else "─"
            signal_parts.append(f"{sym}{dir_icon}{score:.0f}")
        lines.append(f"📡 {' │ '.join(signal_parts)}")
    
    lines.append("")
    
    text = "\n".join(lines)
    
    # Footer
    now = datetime.now()
    text += f"\n{mode_icon} {mode.upper()} │ {health_icon} │ {now.strftime('%H:%M:%S')}"
    
    # Trading control button text
    trade_btn_text = "▶️ Start" if trading_paused else "⏸️ Pause"
    
    # Clean button layout
    buttons = [
        [
            {"text": "📊 Positions", "callback_data": "ai:pos"},
            {"text": "⚠️ Risk", "callback_data": "ai:risk"},
            {"text": "📋 Orders", "callback_data": "ai:ord"},
        ],
        [
            {"text": "📡 Signals", "callback_data": "ai:sig_hist"},
            {"text": "🚨 Alerts", "callback_data": "ai:alerts"},
            {"text": "💰 PnL", "callback_data": "ai:pnl"},
        ],
        [
            {"text": trade_btn_text, "callback_data": "ai:act|t=toggle_trading"},
            {"text": "🔄 Refresh", "callback_data": "ai:main|r=1"},
            {"text": "⚙️ Settings", "callback_data": "ai:set"},
        ]
    ]
    
    return text, buttons

