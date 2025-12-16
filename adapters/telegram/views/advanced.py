"""
Advanced Settings Views for Telegram Bot.
Provides UI for position sizing, coin management, thresholds, age, and score weights.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

# Static coin categories
COIN_CATEGORIES = {
    'ai': {
        'name': '🤖 AI/ML',
        'coins': ['FET', 'RENDER', 'TAO', 'NEAR', 'GRT', 'OCEAN', 'AGIX', 'NMR', 'AKT', 'ARKM']
    },
    'meme': {
        'name': '🐕 Meme',
        'coins': ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK', 'FLOKI', 'MEME', 'TURBO', 'BRETT', 'NEIRO']
    },
    'gaming': {
        'name': '🎮 Gaming',
        'coins': ['IMX', 'GALA', 'AXS', 'SAND', 'MANA', 'ENJ', 'ILV', 'YGG', 'MAGIC', 'PRIME']
    },
    'rwa': {
        'name': '🏠 RWA',
        'coins': ['ONDO', 'RIO', 'MKR', 'AAVE', 'MPL', 'TRU', 'CFG']
    },
    'solana': {
        'name': '☀️ Solana',
        'coins': ['SOL', 'RAY', 'JTO', 'PYTH', 'JUP', 'BONK', 'WIF', 'ORCA']
    },
    'ethereum': {
        'name': '💎 Ethereum',
        'coins': ['ETH', 'UNI', 'AAVE', 'MKR', 'LDO', 'ENS', 'CRV', 'COMP']
    },
    'bnb': {
        'name': '🟡 BNB Chain',
        'coins': ['BNB', 'CAKE', 'XVS', 'BAKE', 'ALPHA', 'TWT']
    },
    'l2': {
        'name': '🔷 Layer 2',
        'coins': ['ARB', 'OP', 'MATIC', 'MNT', 'STRK', 'ZK']
    },
    'l1': {
        'name': '🌐 Layer 1',
        'coins': ['BTC', 'ETH', 'SOL', 'AVAX', 'ADA', 'DOT', 'ATOM', 'NEAR', 'SUI', 'APT']
    },
    'defi': {
        'name': '💼 DeFi',
        'coins': ['UNI', 'AAVE', 'MKR', 'CRV', 'COMP', 'SNX', 'SUSHI', 'YFI', '1INCH']
    },
    'privacy': {
        'name': '🔐 Privacy',
        'coins': ['XMR', 'ZEC', 'DASH', 'SCRT']
    },
    'infra': {
        'name': '⚡ Infrastructure',
        'coins': ['LINK', 'GRT', 'FIL', 'AR', 'RNDR', 'THETA']
    }
}


def build_advanced_menu(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build main advanced settings menu."""
    lines = [
        "🔧 <b>Gelişmiş Ayarlar</b>",
        "",
        "Aşağıdaki ayarları değiştirebilirsiniz.",
        "Tüm değişiklikler <b>restart</b> gerektirir.",
        "",
    ]
    
    buttons = [
        [
            {"text": "📊 Pozisyon Boyutu", "callback_data": "ai:adv_size"},
            {"text": "🪙 Coinler", "callback_data": "ai:adv_coins"},
        ],
        [
            {"text": "📈 Thresholds", "callback_data": "ai:adv_thresh"},
            {"text": "⏰ Poz. Yaşı", "callback_data": "ai:adv_age"},
        ],
        [
            {"text": "⚖️ Score Ağırlıkları", "callback_data": "ai:adv_weight"},
            {"text": "🚀 ML Boost", "callback_data": "ai:adv_mlboost"},
        ],
        [
            {"text": "◀️ Ayarlara Dön", "callback_data": "ai:set"},
        ],
    ]
    
    return "\n".join(lines), buttons


def build_position_size_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build position size settings view."""
    min_pct = context.get('min_percentage', 0.01)
    max_pct = context.get('max_percentage', 0.10)
    
    lines = [
        "📊 <b>Pozisyon Boyutu Ayarları</b>",
        "",
        f"Min: <b>{min_pct*100:.0f}%</b>",
        f"Max: <b>{max_pct*100:.0f}%</b>",
        "",
        "Değiştirmek için butona basın:",
    ]
    
    # Min buttons
    min_buttons = [{"text": f"Min {p}%", "callback_data": f"ai:act|t=set_min_size|v={p}"} for p in [1, 2, 3, 5]]
    max_buttons = [{"text": f"Max {p}%", "callback_data": f"ai:act|t=set_max_size|v={p}"} for p in [5, 10, 15, 20]]
    
    buttons = [
        min_buttons,
        max_buttons,
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons


def build_coins_menu(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build coin management menu."""
    active_coins = context.get('active_coins', [])
    
    # Extract base symbols
    display_coins = [c.split('-')[0] for c in active_coins]
    
    lines = [
        "🪙 <b>Coin Yönetimi</b>",
        "",
        f"Aktif: <b>{len(active_coins)}</b> coin",
        f"📋 {', '.join(display_coins[:5])}{'...' if len(display_coins) > 5 else ''}",
        "",
    ]
    
    buttons = [
        [
            {"text": "📋 Aktif Coinler", "callback_data": "ai:adv_active"},
            {"text": "➕ Coin Ekle", "callback_data": "ai:adv_add"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons


def build_active_coins_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build active coins list with remove buttons."""
    active_coins = context.get('active_coins', [])
    
    lines = [
        "📋 <b>Aktif Coinler</b>",
        "",
        "Kaldırmak için butona basın:",
        "",
    ]
    
    buttons = []
    for coin in active_coins:
        base = coin.split('-')[0]
        buttons.append([{"text": f"❌ {base}", "callback_data": f"ai:act|t=remove_coin|s={coin}"}])
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv_coins"}])
    
    return "\n".join(lines), buttons


def build_add_coins_menu(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build category selection menu for adding coins."""
    lines = [
        "➕ <b>Coin Ekle</b>",
        "",
        "Kategori seçin:",
        "",
    ]
    
    buttons = [
        # Dynamic categories
        [
            {"text": "📈 Top Hacim", "callback_data": "ai:adv_cat|c=volume"},
            {"text": "🔥 Trending", "callback_data": "ai:adv_cat|c=trending"},
        ],
        [
            {"text": "📉 Düşenler", "callback_data": "ai:adv_cat|c=losers"},
            {"text": "💰 Tüm Coinler", "callback_data": "ai:adv_cat|c=all"},
        ],
        # Static categories - row 1
        [
            {"text": "🤖 AI", "callback_data": "ai:adv_cat|c=ai"},
            {"text": "🐕 Meme", "callback_data": "ai:adv_cat|c=meme"},
            {"text": "🎮 Gaming", "callback_data": "ai:adv_cat|c=gaming"},
        ],
        # Static categories - row 2
        [
            {"text": "☀️ Solana", "callback_data": "ai:adv_cat|c=solana"},
            {"text": "💎 ETH", "callback_data": "ai:adv_cat|c=ethereum"},
            {"text": "🟡 BNB", "callback_data": "ai:adv_cat|c=bnb"},
        ],
        # Static categories - row 3
        [
            {"text": "🔷 L2", "callback_data": "ai:adv_cat|c=l2"},
            {"text": "🌐 L1", "callback_data": "ai:adv_cat|c=l1"},
            {"text": "💼 DeFi", "callback_data": "ai:adv_cat|c=defi"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv_coins"}],
    ]
    
    return "\n".join(lines), buttons


def build_coin_category_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build coin list for selected category."""
    category = context.get('category', '')
    coins = context.get('coins', [])
    active_coins = context.get('active_coins', [])
    category_name = context.get('category_name', category)
    
    # Extract base symbols from active
    active_bases = {c.split('-')[0] for c in active_coins}
    
    lines = [
        f"🪙 <b>{category_name}</b>",
        "",
        "Eklemek için butona basın:",
        "",
    ]
    
    buttons = []
    row = []
    for coin in coins:
        base = coin.split('-')[0] if '-' in coin else coin
        is_active = base in active_bases
        text = f"{'✓ ' if is_active else ''}{base}"
        cb = f"ai:act|t=add_coin|s={base}"
        row.append({"text": text, "callback_data": cb})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv_add"}])
    
    return "\n".join(lines), buttons


def build_thresholds_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build thresholds settings view."""
    enter_long = context.get('enter_long', 52)
    exit_long = context.get('exit_long', 40)
    enter_short = context.get('enter_short', 48)
    exit_short = context.get('exit_short', 60)
    
    lines = [
        "📈 <b>Threshold Ayarları</b>",
        "",
        f"LONG Giriş: <b>{enter_long}</b>",
        f"LONG Çıkış: <b>{exit_long}</b>",
        f"SHORT Giriş: <b>{enter_short}</b>",
        f"SHORT Çıkış: <b>{exit_short}</b>",
        "",
    ]
    
    buttons = [
        [
            {"text": f"↑ Long Giriş", "callback_data": "ai:act|t=set_thresh|k=enter_long|d=up"},
            {"text": f"↓ Long Giriş", "callback_data": "ai:act|t=set_thresh|k=enter_long|d=down"},
        ],
        [
            {"text": f"↑ Long Çıkış", "callback_data": "ai:act|t=set_thresh|k=exit_long|d=up"},
            {"text": f"↓ Long Çıkış", "callback_data": "ai:act|t=set_thresh|k=exit_long|d=down"},
        ],
        [
            {"text": f"↑ Short Giriş", "callback_data": "ai:act|t=set_thresh|k=enter_short|d=up"},
            {"text": f"↓ Short Giriş", "callback_data": "ai:act|t=set_thresh|k=enter_short|d=down"},
        ],
        [
            {"text": f"↑ Short Çıkış", "callback_data": "ai:act|t=set_thresh|k=exit_short|d=up"},
            {"text": f"↓ Short Çıkış", "callback_data": "ai:act|t=set_thresh|k=exit_short|d=down"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons


def build_age_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build position age settings view."""
    current_age = context.get('max_position_age_hours', 24)
    
    lines = [
        "⏰ <b>Pozisyon Yaşı Ayarı</b>",
        "",
        f"Mevcut: <b>{current_age} saat</b>",
        "",
        "Bu süreden eski pozisyonlar otomatik kapatılır.",
        "",
    ]
    
    age_options = [6, 12, 24, 48, 72]
    buttons = []
    row = []
    for age in age_options:
        selected = "✓ " if age == current_age else ""
        row.append({"text": f"{selected}{age}h", "callback_data": f"ai:act|t=set_age|v={age}"})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv"}])
    
    return "\n".join(lines), buttons


def build_weights_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build score weights settings view with preset options."""
    ta_weight = context.get('ta_weight', 0.4)
    ml_weight = context.get('ml_weight', 0.6)
    news_weight = context.get('news_weight', 0.05)
    risk_weight = context.get('risk_weight', 0.05)
    
    # Determine current preset
    ta_pct = int(ta_weight * 100)
    ml_pct = int(ml_weight * 100)
    current = f"{ta_pct}/{ml_pct}"
    
    lines = [
        "⚖️ <b>TA/ML Ağırlık Oranı</b>",
        "",
        f"📊 Şu anki: <b>TA {ta_pct}% / ML {ml_pct}%</b>",
        f"📰 News: {news_weight:.0%} | 🛡️ Risk: {risk_weight:.0%}",
        "",
        "Bir preset seç:",
        "",
    ]
    
    # Preset buttons - TA/ML ratios (News=%5, Risk=%5 sabit)
    buttons = [
        [
            {"text": "✅ 20/80" if current == "20/80" else "20/80", "callback_data": "ai:act|t=set_preset|ta=20|ml=80"},
            {"text": "✅ 30/70" if current == "30/70" else "30/70", "callback_data": "ai:act|t=set_preset|ta=30|ml=70"},
            {"text": "✅ 40/60" if current == "40/60" else "40/60", "callback_data": "ai:act|t=set_preset|ta=40|ml=60"},
        ],
        [
            {"text": "✅ 50/50" if current == "50/50" else "50/50", "callback_data": "ai:act|t=set_preset|ta=50|ml=50"},
            {"text": "✅ 60/40" if current == "60/40" else "60/40", "callback_data": "ai:act|t=set_preset|ta=60|ml=40"},
            {"text": "✅ 70/30" if current == "70/30" else "70/30", "callback_data": "ai:act|t=set_preset|ta=70|ml=30"},
        ],
        [
            {"text": "✅ 80/20" if current == "80/20" else "80/20", "callback_data": "ai:act|t=set_preset|ta=80|ml=20"},
            {"text": "✅ 90/10" if current == "90/10" else "90/10", "callback_data": "ai:act|t=set_preset|ta=90|ml=10"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons


def build_ml_boost_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build ML Boost settings view."""
    ml_boost = context.get('ml_boost', {})
    enabled = ml_boost.get('enabled', False)
    tiers = ml_boost.get('tiers', [])
    
    # Sort tiers by threshold
    sorted_tiers = sorted(tiers, key=lambda x: x.get('ta_threshold', 0))
    
    lines = [
        "🚀 <b>ML Score Boost Ayarları</b>",
        "",
        f"Durum: <b>{'✅ Aktif' if enabled else '❌ Kapalı'}</b>",
        "",
        "<b>Tier Ayarları:</b>",
    ]
    
    for tier in sorted_tiers:
        threshold = tier.get('ta_threshold', 0)
        multiplier = tier.get('multiplier', 1)
        lines.append(f"• TA ≥ {threshold}: ML × <b>{multiplier}</b>")
    
    if not sorted_tiers:
        lines.append("• Tier yok")
    
    lines.extend([
        "",
        "<i>TA yüksek olduğunda ML skorunu çarparak</i>",
        "<i>final skoru artırır.</i>",
    ])
    
    # Buttons for tier 1 (65 threshold)
    tier1 = next((t for t in tiers if t.get('ta_threshold') == 65), {})
    tier1_mult = tier1.get('multiplier', 0)
    
    # Buttons for tier 2 (70 threshold)
    tier2 = next((t for t in tiers if t.get('ta_threshold') == 70), {})
    tier2_mult = tier2.get('multiplier', 0)
    
    buttons = [
        [{"text": f"{'✅' if enabled else '❌'} ML Boost {'Kapat' if enabled else 'Aç'}", "callback_data": f"ai:act|t=toggle_mlboost|v={0 if enabled else 1}"}],
        [{"text": "── TA ≥ 65 Multiplier ──", "callback_data": "ai:noop"}],
        [
            {"text": f"{'✅' if tier1_mult == 1 else ''} 1x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=1"},
            {"text": f"{'✅' if tier1_mult == 2 else ''} 2x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=2"},
            {"text": f"{'✅' if tier1_mult == 3 else ''} 3x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=3"},
            {"text": f"{'✅' if tier1_mult == 4 else ''} 4x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=4"},
            {"text": f"{'✅' if tier1_mult == 5 else ''} 5x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=5"},
        ],
        [{"text": "── TA ≥ 70 Multiplier ──", "callback_data": "ai:noop"}],
        [
            {"text": f"{'✅' if tier2_mult == 1 else ''} 1x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=1"},
            {"text": f"{'✅' if tier2_mult == 2 else ''} 2x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=2"},
            {"text": f"{'✅' if tier2_mult == 3 else ''} 3x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=3"},
            {"text": f"{'✅' if tier2_mult == 4 else ''} 4x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=4"},
            {"text": f"{'✅' if tier2_mult == 5 else ''} 5x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=5"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons
