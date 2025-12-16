"""
Telegram View Builders
Pure functions that build view text and buttons from context.
"""

from .main import build_main_view
from .signals import build_signals_view
from .risk import build_risk_view
from .orders import build_orders_view
from .tp_sl import build_tpsl_view
from .trailing import build_trailing_view
from .pnl import build_pnl_view
from .settings import build_settings_view
from .positions import build_positions_view
from .emergency import build_emergency_view
from .advanced import (
    build_advanced_menu,
    build_position_size_view,
    build_coins_menu,
    build_active_coins_view,
    build_add_coins_menu,
    build_coin_category_view,
    build_thresholds_view,
    build_age_view,
    build_weights_view,
    COIN_CATEGORIES,
)

__all__ = [
    "build_main_view",
    "build_signals_view",
    "build_risk_view",
    "build_orders_view",
    "build_tpsl_view",
    "build_trailing_view",
    "build_pnl_view",
    "build_settings_view",
    "build_positions_view",
    "build_emergency_view",
    "build_advanced_menu",
    "build_position_size_view",
    "build_coins_menu",
    "build_active_coins_view",
    "build_add_coins_menu",
    "build_coin_category_view",
    "build_thresholds_view",
    "build_age_view",
    "build_weights_view",
    "COIN_CATEGORIES",
]
