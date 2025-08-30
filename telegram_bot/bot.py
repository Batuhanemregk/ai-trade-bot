"""
Telegram bot main module.
Contains start/stop wiring, Updater/Application bootstrap.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.ext import ContextTypes

from .commands import command_handler
from .keyboards import keyboard_builder
from infrastructure.logger import get_agent_logger


class TelegramBot:
    """Main Telegram bot class with lifecycle management."""
    
    def __init__(self, token: str):
        self.token = token
        self.logger = get_agent_logger("telegram_bot")
        self.application: Optional[Application] = None
        self._shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_event.set()
    
    async def start(self):
        """Start the Telegram bot."""
        try:
            self.logger.info("Starting Telegram bot...")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Register handlers
            self._register_handlers()
            
            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.logger.info("Telegram bot started successfully")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the Telegram bot."""
        try:
            if self.application:
                self.logger.info("Stopping Telegram bot...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.logger.info("Telegram bot stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping Telegram bot: {e}")
    
    def _register_handlers(self):
        """Register all command and callback handlers."""
        if not self.application:
            return
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("scoring", self._cmd_scoring))
        self.application.add_handler(CommandHandler("risk", self._cmd_risk))
        self.application.add_handler(CommandHandler("news", self._cmd_news))
        self.application.add_handler(CommandHandler("positions", self._cmd_positions))
        self.application.add_handler(CommandHandler("orders", self._cmd_orders))
        self.application.add_handler(CommandHandler("config_get", self._cmd_config_get))
        self.application.add_handler(CommandHandler("config_set", self._cmd_config_set))
        self.application.add_handler(CommandHandler("scheduler", self._cmd_scheduler))
        self.application.add_handler(CommandHandler("agents", self._cmd_agents))
        self.application.add_handler(CommandHandler("restart", self._cmd_restart))
        self.application.add_handler(CommandHandler("shutdown", self._cmd_shutdown))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        self.logger.info("Registered all Telegram bot handlers")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        try:
            user = update.effective_user
            message_text = update.message.text
            
            self.logger.info(f"Message from {user.id} (@{user.username}): {message_text[:50]}...")
            
            # Echo the message for now
            await update.message.reply_text(f"Received: {message_text}")
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def initialize(self):
        """Initialize Telegram bot."""
        try:
            if not self.application:
                self.logger.warning("Telegram bot not initialized")
                return False
            
            self.logger.info("Telegram bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def send_notification(self, title: str, message: str, level: str = "info"):
        """Send notification message."""
        try:
            # Format message with title and level
            formatted_message = f"<b>{title}</b>\n\n{message}"
            
            # Add level emoji
            if level == "success":
                formatted_message = "✅ " + formatted_message
            elif level == "warning":
                formatted_message = "⚠️ " + formatted_message
            elif level == "error":
                formatted_message = "❌ " + formatted_message
            else:
                formatted_message = "ℹ️ " + formatted_message
            
            # Send message
            return await self.send_message(formatted_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False
    
    async def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to Telegram."""
        try:
            if not self.application:
                self.logger.warning("Telegram bot not initialized")
                return False
            
            # Use provided chat_id or get from environment
            if not chat_id:
                import os
                chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not chat_id:
                self.logger.warning("No chat_id provided and TELEGRAM_CHAT_ID not set")
                return False
            
            # Send message
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            self.logger.info(f"Message sent to {chat_id}: {message[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        self.logger.info(f"Start command from user {user.id} (@{user.username})")
        
        welcome_text = f"""🤖 **Welcome to AiBotBS!**

Hello {user.first_name}! I'm your AI-powered trading bot assistant.

Use /help to see all available commands, or use the menu below to navigate."""
        
        keyboard = keyboard_builder.main_menu()
        await update.message.reply_text(welcome_text, reply_markup=keyboard)
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = await command_handler.handle_help({})
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _cmd_scoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scoring command."""
        scoring_text = await command_handler.handle_scoring({})
        await update.message.reply_text(scoring_text, parse_mode='Markdown')
    
    async def _cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command."""
        risk_text = await command_handler.handle_risk({})
        await update.message.reply_text(risk_text, parse_mode='Markdown')
    
    async def _cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command."""
        news_text = await command_handler.handle_news({})
        await update.message.reply_text(news_text, parse_mode='Markdown')
    
    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        positions_text = await command_handler.handle_positions({})
        await update.message.reply_text(positions_text, parse_mode='Markdown')
    
    async def _cmd_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /orders command."""
        orders_text = await command_handler.handle_orders({})
        await update.message.reply_text(orders_text, parse_mode='Markdown')
    
    async def _cmd_config_get(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config_get command."""
        config_text = await command_handler.handle_config_get({})
        await update.message.reply_text(config_text, parse_mode='Markdown')
    
    async def _cmd_config_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config_set command."""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Usage: /config_set <key> <value>")
            return
        
        key, value = context.args[0], context.args[1]
        config_text = await command_handler.handle_config_set({}, key, value)
        await update.message.reply_text(config_text, parse_mode='Markdown')
    
    async def _cmd_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scheduler command."""
        scheduler_text = await command_handler.handle_scheduler({})
        await update.message.reply_text(scheduler_text, parse_mode='Markdown')
    
    async def _cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /agents command."""
        agents_text = await command_handler.handle_agents({})
        await update.message.reply_text(agents_text, parse_mode='Markdown')
    
    async def _cmd_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /restart command."""
        restart_text = await command_handler.handle_restart({})
        await update.message.reply_text(restart_text, parse_mode='Markdown')
    
    async def _cmd_shutdown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /shutdown command."""
        shutdown_text = await command_handler.handle_shutdown({})
        await update.message.reply_text(shutdown_text, parse_mode='Markdown')
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        self.logger.info(f"Callback query: {callback_data}")
        
        # Handle menu navigation
        if callback_data == "menu_main":
            keyboard = keyboard_builder.main_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        elif callback_data == "menu_trading":
            keyboard = keyboard_builder.trading_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        elif callback_data == "menu_system":
            keyboard = keyboard_builder.system_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        elif callback_data == "menu_agents":
            keyboard = keyboard_builder.agents_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        elif callback_data == "menu_news":
            keyboard = keyboard_builder.news_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        elif callback_data == "config_menu":
            keyboard = keyboard_builder.config_menu()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        else:
            # Handle other callbacks
            await self._handle_command_callback(query, callback_data)
    
    async def _handle_command_callback(self, query, callback_data: str):
        """Handle command callbacks."""
        if callback_data == "help":
            help_text = await command_handler.handle_help({})
            await query.edit_message_text(help_text, parse_mode='Markdown')
        elif callback_data == "scoring":
            scoring_text = await command_handler.handle_scoring({})
            await query.edit_message_text(scoring_text, parse_mode='Markdown')
        elif callback_data == "risk":
            risk_text = await command_handler.handle_risk({})
            await query.edit_message_text(risk_text, parse_mode='Markdown')
        elif callback_data == "news":
            news_text = await command_handler.handle_news({})
            await query.edit_message_text(news_text, parse_mode='Markdown')
        elif callback_data == "positions":
            positions_text = await command_handler.handle_positions({})
            await query.edit_message_text(positions_text, parse_mode='Markdown')
        elif callback_data == "orders":
            orders_text = await command_handler.handle_orders({})
            await query.edit_message_text(orders_text, parse_mode='Markdown')
        elif callback_data == "scheduler":
            scheduler_text = await command_handler.handle_scheduler({})
            await query.edit_message_text(scheduler_text, parse_mode='Markdown')
        elif callback_data == "agents":
            agents_text = await command_handler.handle_agents({})
            await query.edit_message_text(agents_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"Unknown callback: {callback_data}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        user = update.effective_user
        text = update.message.text
        
        self.logger.info(f"Message from user {user.id}: {text}")
        
        # Echo message for now
        await update.message.reply_text(f"You said: {text}")


async def main():
    """Main function to run the bot."""
    import os
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    bot = TelegramBot(token)
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["TelegramBot", "main"]
