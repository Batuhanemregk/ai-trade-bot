"""
Risk View Builder
Builds the risk overview view with exposure, tier alloc, limits, and guards.
"""

from typing import Dict, Any, List, Tuple

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_risk_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """
    Build risk view.
    
    Args:
        context: Context dict from ContextResolver.resolve_risk_context()
        formatter: Optional formatter instance
    
    Returns:
        Tuple of (text, buttons)
    """
    if formatter is None:
        formatter = get_formatter()
    
    exposure_pct = context.get('exposure_pct', 0.0)
    exposure_max = context.get('exposure_max', 60.0)
    open_pos = context.get('open_positions', 0)
    max_pos = context.get('max_positions', 20)
    cb_state = context.get('cb_state', 'OFF')
    
    tier_alloc = context.get('tier_alloc', {})
    limits = context.get('limits', {})
    guards = context.get('guards', {})
    alerts = context.get('alerts', [])
    
    # Header
    header = f"Risk Overview • Exposure {exposure_pct:.0f}%/{exposure_max:.0f}% • Open {open_pos}/{max_pos}"
    
    # Exposure and CB state
    exposure_line = f"Exposure {exposure_pct:.0f}% / {exposure_max:.0f}% • Open {open_pos} / {max_pos} • CB {cb_state}"
    
    # Tier allocation
    t1_pct = tier_alloc.get('T1', 0.0)
    t2_pct = tier_alloc.get('T2', 0.0)
    t3_pct = tier_alloc.get('T3', 0.0)
    tier_line = f"Tier Alloc: T1 {t1_pct:.0f}% • T2 {t2_pct:.0f}% • T3 {t3_pct:.0f}%"
    
    # Limits
    max_pos_size = limits.get('max_position_size_pct', 10.0)
    stop_loss = limits.get('stop_loss_pct', 1.5)
    leverage = limits.get('leverage', 3.0)
    limits_line = f"Limits: MaxPos {max_pos_size:.0f}% • StopLoss {stop_loss:.1f}% • Leverage {leverage:.1f}x"
    
    # Guards
    persist = guards.get('persist', 3)
    age = guards.get('age', 6)
    confirm = guards.get('confirm', 2)
    hyster = guards.get('hyster', '±5')
    guards_line = f"Guards: persist={persist} age={age} confirm={confirm} hyster={hyster}"
    
    # Alerts
    alerts_text = "None" if not alerts else ", ".join(alerts[:3])
    alerts_line = f"Alerts (last 1h): {alerts_text}"
    
    # Build text
    lines = [
        "Risk Overview",
        "",
        exposure_line,
        tier_line,
        limits_line,
        guards_line,
        alerts_line,
        ""
    ]
    text = "\n".join(lines)
    
    # Add footer
    text = formatter.add_footer(text)
    
    # Build buttons
    buttons = [
        [
            {"text": "Main", "callback_data": "ai:main"},
            {"text": "Settings", "callback_data": "ai:set"},
            {"text": "Positions", "callback_data": "ai:pos"},
            {"text": "Orders", "callback_data": "ai:ord"}
        ]
    ]
    
    return text, buttons

