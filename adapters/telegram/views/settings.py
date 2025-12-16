"""
Settings View Builder
Clean settings with restart button.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_settings_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build settings view with restart button."""
    if formatter is None:
        formatter = get_formatter()
    
    # User settings
    compact_mode = context.get('compact_mode', True)
    emojis = context.get('emojis', False)
    confirmations = context.get('confirmations', True)
    timeframe = context.get('timeframe', '15m')
    leverage = context.get('leverage', 5)
    
    # Trading features from policy
    trailing_enabled = context.get('trailing_enabled', False)
    partial_tp_enabled = context.get('partial_tp_enabled', False)
    time_exit_enabled = context.get('time_exit_enabled', False)
    dynamic_tpsl_enabled = context.get('dynamic_tpsl_enabled', False)
    
    def status(val): return "✅" if val else "❌"
    
    lines = [
        f"⚙️ Ayarlar",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📦 Compact   : {status(compact_mode)}",
        f"😀 Emoji     : {status(emojis)}",
        f"✋ Onay      : {status(confirmations)}",
        f"⏱️ Timeframe : {timeframe} 🔒",
        f"⚡ Kaldıraç  : {leverage}x",
        "",
        f"── Çıkış Stratejisi ──",
        f"📈 Trailing  : {status(trailing_enabled)}",
        f"💰 Partial TP: {status(partial_tp_enabled)}",
        f"⏰ Time Exit : {status(time_exit_enabled)}",
        f"📊 ATR TP/SL : {status(dynamic_tpsl_enabled)}",
        "",
    ]
    
    now = datetime.now()
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    text = "\n".join(lines)
    
    # Buttons
    buttons = [
        # User setting toggles
        [
            {"text": f"📦 Compact", "callback_data": "ai:act|t=toggle|k=compact"},
            {"text": f"😀 Emoji", "callback_data": "ai:act|t=toggle|k=emojis"},
            {"text": f"✋ Onay", "callback_data": "ai:act|t=toggle|k=confirmations"},
        ],
    ]
    
    # Leverage buttons
    lev_buttons = []
    for lev in [1, 3, 5, 7, 10]:
        is_selected = (leverage == lev)
        btn_text = f"{'✓' if is_selected else ''}{lev}x"
        lev_buttons.append({
            "text": btn_text.strip(),
            "callback_data": f"ai:act|t=set_lev|v={lev}"
        })
    buttons.append(lev_buttons)
    
    # Trading feature toggles
    buttons.append([
        {"text": f"📈 Trail", "callback_data": "ai:act|t=toggle|k=trailing"},
        {"text": f"💰 PartTP", "callback_data": "ai:act|t=toggle|k=partial_tp"},
    ])
    buttons.append([
        {"text": f"⏰ TimeEx", "callback_data": "ai:act|t=toggle|k=time_exit"},
        {"text": f"📊 ATR", "callback_data": "ai:act|t=toggle|k=dynamic_tpsl"},
    ])
    
    # Advanced Settings link
    buttons.append([
        {"text": "🔧 Gelişmiş Ayarlar", "callback_data": "ai:adv"},
    ])
    
    # Navigation + Restart
    buttons.append([
        {"text": "🔄 Yenile", "callback_data": "ai:set|r=1"},
        {"text": "🔃 Bot Restart", "callback_data": "ai:act|t=restart"},
        {"text": "🏠 Ana Sayfa", "callback_data": "ai:main"},
    ])
    
    return text, buttons
