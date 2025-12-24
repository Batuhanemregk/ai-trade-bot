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
            {"text": "🎯 ATR TP/SL", "callback_data": "ai:adv_atr"},
        ],
        [
            {"text": "◀️ Ayarlara Dön", "callback_data": "ai:set"},
        ],
    ]
    
    return "\n".join(lines), buttons


def build_position_size_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build tier-based position sizing view - adjusts actual values used by runtime."""
    # Current tier values from policy (trading.scoring.position_sizing.tiers)
    tiers = context.get('tiers', {})
    weak_pct = tiers.get('weak', {}).get('position_pct', 0.02)
    medium_pct = tiers.get('medium', {}).get('position_pct', 0.04)
    strong_pct = tiers.get('strong', {}).get('position_pct', 0.06)
    extreme_pct = tiers.get('extreme', {}).get('position_pct', 0.08)
    
    # Pending values (from session)
    pending = context.get('pending_tiers', {})
    p_weak = pending.get('weak', weak_pct)
    p_medium = pending.get('medium', medium_pct)
    p_strong = pending.get('strong', strong_pct)
    p_extreme = pending.get('extreme', extreme_pct)
    
    # Check for pending changes
    has_changes = bool(pending) and (
        p_weak != weak_pct or p_medium != medium_pct or 
        p_strong != strong_pct or p_extreme != extreme_pct
    )
    
    # Display percentages
    d_weak = int(p_weak * 100)
    d_medium = int(p_medium * 100)
    d_strong = int(p_strong * 100)
    d_extreme = int(p_extreme * 100)
    
    status = "📝 Değişiklikler bekliyor..." if has_changes else "✅ Kayıtlı"
    
    lines = [
        "📊 <b>Pozisyon Boyutu (Tier-Based)</b>",
        "",
        "Sinyal gücüne göre pozisyon yüzdesi:",
        "",
        f"🟢 Weak:    <b>{d_weak}%</b>  (strength 0.0-0.3)",
        f"🟡 Medium:  <b>{d_medium}%</b>  (strength 0.3-0.5)",
        f"🟠 Strong:  <b>{d_strong}%</b>  (strength 0.5-0.7)",
        f"🔴 Extreme: <b>{d_extreme}%</b>  (strength 0.7-1.0)",
        "",
        f"<i>{status}</i>",
    ]
    
    # +/- 1% buttons for each tier
    buttons = [
        # Weak row
        [
            {"text": "🟢 Weak", "callback_data": "ai:noop"},
            {"text": "◀ -1%", "callback_data": "ai:act|t=adj_tier|k=weak|d=down"},
            {"text": f"{d_weak}%", "callback_data": "ai:noop"},
            {"text": "+1% ▶", "callback_data": "ai:act|t=adj_tier|k=weak|d=up"},
        ],
        # Medium row
        [
            {"text": "🟡 Medium", "callback_data": "ai:noop"},
            {"text": "◀ -1%", "callback_data": "ai:act|t=adj_tier|k=medium|d=down"},
            {"text": f"{d_medium}%", "callback_data": "ai:noop"},
            {"text": "+1% ▶", "callback_data": "ai:act|t=adj_tier|k=medium|d=up"},
        ],
        # Strong row
        [
            {"text": "🟠 Strong", "callback_data": "ai:noop"},
            {"text": "◀ -1%", "callback_data": "ai:act|t=adj_tier|k=strong|d=down"},
            {"text": f"{d_strong}%", "callback_data": "ai:noop"},
            {"text": "+1% ▶", "callback_data": "ai:act|t=adj_tier|k=strong|d=up"},
        ],
        # Extreme row
        [
            {"text": "🔴 Extreme", "callback_data": "ai:noop"},
            {"text": "◀ -1%", "callback_data": "ai:act|t=adj_tier|k=extreme|d=down"},
            {"text": f"{d_extreme}%", "callback_data": "ai:noop"},
            {"text": "+1% ▶", "callback_data": "ai:act|t=adj_tier|k=extreme|d=up"},
        ],
    ]
    
    # Save/Cancel if pending
    if has_changes:
        buttons.append([
            {"text": "✅ Kaydet", "callback_data": "ai:act|t=save_tiers"},
            {"text": "❌ İptal", "callback_data": "ai:act|t=cancel_tiers"},
        ])
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv"}])
    
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
        f"Toplam: {len(active_coins)} coin",
        "Kaldırmak için butona basın:",
    ]
    
    # Group coins into rows of 4 to respect 8 row limit
    buttons = []
    row = []
    for coin in active_coins:
        base = coin.split('-')[0]
        row.append({"text": f"❌ {base}", "callback_data": f"ai:act|t=remove_coin|s={coin}"})
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
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
        # Dynamic categories - row 1
        [
            {"text": "📈 Top Hacim", "callback_data": "ai:adv_cat|c=volume"},
            {"text": "🔥 Trending", "callback_data": "ai:adv_cat|c=trending"},
        ],
        # Dynamic categories - row 2
        [
            {"text": "📈 Top Gainers", "callback_data": "ai:adv_cat|c=gainers"},
            {"text": "📉 Düşenler", "callback_data": "ai:adv_cat|c=losers"},
        ],
        # Dynamic categories - row 3
        [
            {"text": "🆕 New Listings", "callback_data": "ai:adv_cat|c=new_listings"},
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
    """Build thresholds settings view with preview mode."""
    # Current saved values
    enter_long = context.get('enter_long', 52)
    exit_long = context.get('exit_long', 40)
    enter_short = context.get('enter_short', 48)
    exit_short = context.get('exit_short', 60)
    
    # Pending values
    pending = context.get('pending_thresh', {})
    p_el = pending.get('enter_long', enter_long)
    p_xl = pending.get('exit_long', exit_long)
    p_es = pending.get('enter_short', enter_short)
    p_xs = pending.get('exit_short', exit_short)
    
    # Check for pending changes
    has_changes = bool(pending) and (
        p_el != enter_long or p_xl != exit_long or 
        p_es != enter_short or p_xs != exit_short
    )
    
    status = "📝 Değişiklikler bekliyor..." if has_changes else "✅ Kayıtlı"
    
    lines = [
        "📈 <b>Threshold Ayarları</b>",
        "",
        f"LONG Giriş: <b>{p_el}</b>",
        f"LONG Çıkış: <b>{p_xl}</b>",
        f"SHORT Giriş: <b>{p_es}</b>",
        f"SHORT Çıkış: <b>{p_xs}</b>",
        "",
        f"<i>{status}</i>",
    ]
    
    # +/- buttons for each threshold (adj_thresh for preview)
    buttons = [
        [
            {"text": "L.Giriş", "callback_data": "ai:noop"},
            {"text": "◀ -2", "callback_data": "ai:act|t=adj_thresh|k=enter_long|d=down"},
            {"text": f"{p_el}", "callback_data": "ai:noop"},
            {"text": "+2 ▶", "callback_data": "ai:act|t=adj_thresh|k=enter_long|d=up"},
        ],
        [
            {"text": "L.Çıkış", "callback_data": "ai:noop"},
            {"text": "◀ -2", "callback_data": "ai:act|t=adj_thresh|k=exit_long|d=down"},
            {"text": f"{p_xl}", "callback_data": "ai:noop"},
            {"text": "+2 ▶", "callback_data": "ai:act|t=adj_thresh|k=exit_long|d=up"},
        ],
        [
            {"text": "S.Giriş", "callback_data": "ai:noop"},
            {"text": "◀ -2", "callback_data": "ai:act|t=adj_thresh|k=enter_short|d=down"},
            {"text": f"{p_es}", "callback_data": "ai:noop"},
            {"text": "+2 ▶", "callback_data": "ai:act|t=adj_thresh|k=enter_short|d=up"},
        ],
        [
            {"text": "S.Çıkış", "callback_data": "ai:noop"},
            {"text": "◀ -2", "callback_data": "ai:act|t=adj_thresh|k=exit_short|d=down"},
            {"text": f"{p_xs}", "callback_data": "ai:noop"},
            {"text": "+2 ▶", "callback_data": "ai:act|t=adj_thresh|k=exit_short|d=up"},
        ],
    ]
    
    # Save/Cancel if pending
    if has_changes:
        buttons.append([
            {"text": "✅ Kaydet", "callback_data": "ai:act|t=save_thresh"},
            {"text": "❌ İptal", "callback_data": "ai:act|t=cancel_thresh"},
        ])
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv"}])
    
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
    """Build score weights settings view with individual +/- controls and save/cancel."""
    # Current saved values from policy
    ta_weight = context.get('ta_weight', 0.55)
    ml_weight = context.get('ml_weight', 0.35)
    news_weight = context.get('news_weight', 0.05)
    risk_weight = context.get('risk_weight', 0.05)
    
    # Pending values (from session, if any adjustments made)
    pending = context.get('pending_weights', {})
    p_ta = pending.get('ta', ta_weight)
    p_ml = pending.get('ml', ml_weight)
    p_news = pending.get('news', news_weight)
    p_risk = pending.get('risk', risk_weight)
    
    # Check if there are pending changes
    has_changes = bool(pending) and (
        p_ta != ta_weight or p_ml != ml_weight or 
        p_news != news_weight or p_risk != risk_weight
    )
    
    # Calculate percentages (use pending if available)
    ta_pct = int(p_ta * 100)
    ml_pct = int(p_ml * 100)
    news_pct = int(p_news * 100)
    risk_pct = int(p_risk * 100)
    total = ta_pct + ml_pct + news_pct + risk_pct
    
    # Total check indicator
    total_ok = "✅" if total == 100 else f"⚠️ {total}%"
    
    # Show pending changes indicator
    status = "📝 Değişiklikler bekliyor..." if has_changes else "✅ Kayıtlı"
    
    lines = [
        "⚖️ <b>Score Ağırlıkları</b>",
        "",
        f"📊 TA:    <b>{ta_pct}%</b>",
        f"🤖 ML:    <b>{ml_pct}%</b>",
        f"📰 News:  <b>{news_pct}%</b>",
        f"🛡️ Risk:  <b>{risk_pct}%</b>",
        "",
        f"Toplam: <b>{total}%</b> {total_ok}",
        "",
        f"<i>{status}</i>",
    ]
    
    # +/- 5% buttons for each weight (adj_ prefix for adjustment without saving)
    buttons = [
        # TA row
        [
            {"text": "📊 TA", "callback_data": "ai:noop"},
            {"text": "◀ -5%", "callback_data": "ai:act|t=adj_weight|k=ta|d=down"},
            {"text": f"{ta_pct}%", "callback_data": "ai:noop"},
            {"text": "+5% ▶", "callback_data": "ai:act|t=adj_weight|k=ta|d=up"},
        ],
        # ML row
        [
            {"text": "🤖 ML", "callback_data": "ai:noop"},
            {"text": "◀ -5%", "callback_data": "ai:act|t=adj_weight|k=ml|d=down"},
            {"text": f"{ml_pct}%", "callback_data": "ai:noop"},
            {"text": "+5% ▶", "callback_data": "ai:act|t=adj_weight|k=ml|d=up"},
        ],
        # News row
        [
            {"text": "📰 News", "callback_data": "ai:noop"},
            {"text": "◀ -5%", "callback_data": "ai:act|t=adj_weight|k=news|d=down"},
            {"text": f"{news_pct}%", "callback_data": "ai:noop"},
            {"text": "+5% ▶", "callback_data": "ai:act|t=adj_weight|k=news|d=up"},
        ],
        # Risk row
        [
            {"text": "🛡️ Risk", "callback_data": "ai:noop"},
            {"text": "◀ -5%", "callback_data": "ai:act|t=adj_weight|k=risk|d=down"},
            {"text": f"{risk_pct}%", "callback_data": "ai:noop"},
            {"text": "+5% ▶", "callback_data": "ai:act|t=adj_weight|k=risk|d=up"},
        ],
    ]
    
    # Save/Cancel buttons if there are pending changes
    if has_changes:
        buttons.append([
            {"text": "✅ Kaydet", "callback_data": "ai:act|t=save_weights"},
            {"text": "❌ İptal", "callback_data": "ai:act|t=cancel_weights"},
        ])
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv"}])
    
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
    
    # Buttons for tier 0 (60 threshold)
    tier0 = next((t for t in tiers if t.get('ta_threshold') == 60), {})
    tier0_mult = tier0.get('multiplier', 0)
    
    # Buttons for tier 1 (65 threshold)
    tier1 = next((t for t in tiers if t.get('ta_threshold') == 65), {})
    tier1_mult = tier1.get('multiplier', 0)
    
    # Buttons for tier 2 (70 threshold)
    tier2 = next((t for t in tiers if t.get('ta_threshold') == 70), {})
    tier2_mult = tier2.get('multiplier', 0)
    
    buttons = [
        [{"text": f"{'✅' if enabled else '❌'} ML Boost {'Kapat' if enabled else 'Aç'}", "callback_data": f"ai:act|t=toggle_mlboost|v={0 if enabled else 1}"}],
        # TA ≥ 60 row
        [
            {"text": "60:", "callback_data": "ai:noop"},
            {"text": f"{'✅' if tier0_mult == 2 else ''} 2x", "callback_data": "ai:act|t=set_ml_tier|th=60|m=2"},
            {"text": f"{'✅' if tier0_mult == 3 else ''} 3x", "callback_data": "ai:act|t=set_ml_tier|th=60|m=3"},
            {"text": f"{'✅' if tier0_mult == 4 else ''} 4x", "callback_data": "ai:act|t=set_ml_tier|th=60|m=4"},
            {"text": f"{'✅' if tier0_mult == 5 else ''} 5x", "callback_data": "ai:act|t=set_ml_tier|th=60|m=5"},
        ],
        # TA ≥ 65 row
        [
            {"text": "65:", "callback_data": "ai:noop"},
            {"text": f"{'✅' if tier1_mult == 2 else ''} 2x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=2"},
            {"text": f"{'✅' if tier1_mult == 3 else ''} 3x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=3"},
            {"text": f"{'✅' if tier1_mult == 4 else ''} 4x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=4"},
            {"text": f"{'✅' if tier1_mult == 5 else ''} 5x", "callback_data": "ai:act|t=set_ml_tier|th=65|m=5"},
        ],
        # TA ≥ 70 row
        [
            {"text": "70:", "callback_data": "ai:noop"},
            {"text": f"{'✅' if tier2_mult == 2 else ''} 2x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=2"},
            {"text": f"{'✅' if tier2_mult == 3 else ''} 3x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=3"},
            {"text": f"{'✅' if tier2_mult == 4 else ''} 4x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=4"},
            {"text": f"{'✅' if tier2_mult == 5 else ''} 5x", "callback_data": "ai:act|t=set_ml_tier|th=70|m=5"},
        ],
        [{"text": "◀️ Geri", "callback_data": "ai:adv"}],
    ]
    
    return "\n".join(lines), buttons


def build_atr_view(context: Dict[str, Any], formatter) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build ATR TP/SL multiplier settings view with preview mode."""
    # Current values from policy
    sl_mult = context.get('sl_atr_mult', 2.0)
    tp_mult = context.get('tp_atr_mult', 4.0)
    fallback_sl = context.get('fallback_sl_pct', 1.5)
    fallback_tp = context.get('fallback_tp_pct', 3.0)
    
    # Pending values (from session)
    pending = context.get('pending_atr', {})
    p_sl = pending.get('sl', sl_mult)
    p_tp = pending.get('tp', tp_mult)
    
    # Check for pending changes
    has_changes = bool(pending) and (p_sl != sl_mult or p_tp != tp_mult)
    
    # Calculate R:R ratio using display values
    rr_ratio = p_tp / p_sl if p_sl > 0 else 0
    
    status = "📝 Değişiklikler bekliyor..." if has_changes else "✅ Kayıtlı"
    
    lines = [
        "🎯 <b>ATR TP/SL Ayarları</b>",
        "",
        f"🛡️ Stop Loss: <b>{p_sl} ATR</b>",
        f"🎯 Take Profit: <b>{p_tp} ATR</b>",
        f"📊 Risk/Reward: <b>1:{rr_ratio:.1f}</b>",
        "",
        f"<i>Fallback: SL %{fallback_sl}, TP %{fallback_tp}</i>",
        "",
        f"<i>{status}</i>",
    ]
    
    # +/- buttons for SL and TP
    buttons = [
        # SL row
        [
            {"text": "🛡️ SL", "callback_data": "ai:noop"},
            {"text": "◀ -0.5", "callback_data": "ai:act|t=adj_atr|k=sl|d=down"},
            {"text": f"{p_sl} ATR", "callback_data": "ai:noop"},
            {"text": "+0.5 ▶", "callback_data": "ai:act|t=adj_atr|k=sl|d=up"},
        ],
        # TP row
        [
            {"text": "🎯 TP", "callback_data": "ai:noop"},
            {"text": "◀ -0.5", "callback_data": "ai:act|t=adj_atr|k=tp|d=down"},
            {"text": f"{p_tp} ATR", "callback_data": "ai:noop"},
            {"text": "+0.5 ▶", "callback_data": "ai:act|t=adj_atr|k=tp|d=up"},
        ],
    ]
    
    # Save/Cancel if pending
    if has_changes:
        buttons.append([
            {"text": "✅ Kaydet", "callback_data": "ai:act|t=save_atr"},
            {"text": "❌ İptal", "callback_data": "ai:act|t=cancel_atr"},
        ])
    
    buttons.append([{"text": "◀️ Geri", "callback_data": "ai:adv"}])
    
    return "\n".join(lines), buttons
