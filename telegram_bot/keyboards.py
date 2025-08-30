"""
Inline keyboards and builders for Telegram bot.
Contains keyboard layouts and button configurations.
"""

from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class KeyboardBuilder:
    """Builder for Telegram inline keyboards."""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Create main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Trading", callback_data="menu_trading"),
                InlineKeyboardButton("⚙️ System", callback_data="menu_system")
            ],
            [
                InlineKeyboardButton("📰 News", callback_data="menu_news"),
                InlineKeyboardButton("🤖 Agents", callback_data="menu_agents")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help"),
                InlineKeyboardButton("📈 Status", callback_data="status")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def trading_menu() -> InlineKeyboardMarkup:
        """Create trading menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Scoring", callback_data="scoring"),
                InlineKeyboardButton("⚠️ Risk", callback_data="risk")
            ],
            [
                InlineKeyboardButton("📈 Positions", callback_data="positions"),
                InlineKeyboardButton("📋 Orders", callback_data="orders")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="menu_main"),
                InlineKeyboardButton("📊 PnL", callback_data="pnl")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def system_menu() -> InlineKeyboardMarkup:
        """Create system menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("⚙️ Config", callback_data="config_menu"),
                InlineKeyboardButton("⏰ Scheduler", callback_data="scheduler")
            ],
            [
                InlineKeyboardButton("🔄 Restart", callback_data="restart"),
                InlineKeyboardButton("🛑 Shutdown", callback_data="shutdown")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="menu_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def config_menu() -> InlineKeyboardMarkup:
        """Create config menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📖 Get Config", callback_data="config_get"),
                InlineKeyboardButton("✏️ Set Config", callback_data="config_set")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="menu_system")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def agents_menu() -> InlineKeyboardMarkup:
        """Create agents menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🤖 Agent Status", callback_data="agents"),
                InlineKeyboardButton("📊 Performance", callback_data="agent_performance")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="menu_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def news_menu() -> InlineKeyboardMarkup:
        """Create news menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📰 Latest News", callback_data="news"),
                InlineKeyboardButton("📊 Sentiment", callback_data="news_sentiment")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="menu_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirmation_buttons(action: str, data: str = "") -> InlineKeyboardMarkup:
        """Create confirmation buttons for destructive actions."""
        callback_data = f"{action}_confirm:{data}" if data else f"{action}_confirm"
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=callback_data),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(menu: str) -> InlineKeyboardMarkup:
        """Create back button to specific menu."""
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data=f"menu_{menu}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination_buttons(current_page: int, total_pages: int, 
                          callback_prefix: str) -> InlineKeyboardMarkup:
        """Create pagination buttons."""
        keyboard = []
        
        # Navigation buttons
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(
                InlineKeyboardButton("◀️ Prev", callback_data=f"{callback_prefix}:{current_page-1}")
            )
        
        nav_buttons.append(
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="page_info")
        )
        
        if current_page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton("Next ▶️", callback_data=f"{callback_prefix}:{current_page+1}")
            )
        
        keyboard.append(nav_buttons)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def quick_actions() -> InlineKeyboardMarkup:
        """Create quick actions keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Quick Status", callback_data="quick_status"),
                InlineKeyboardButton("⚠️ Emergency Stop", callback_data="emergency_stop")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
                InlineKeyboardButton("📈 Summary", callback_data="summary")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


# Global keyboard builder instance
keyboard_builder = KeyboardBuilder()


__all__ = ["KeyboardBuilder", "keyboard_builder"]
