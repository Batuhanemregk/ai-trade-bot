"""
Telegram Client - Wrapper around python-telegram-bot Application
Handles connection management and message sending with error handling.
"""

import os
from typing import Optional
from loguru import logger

from telegram import Update
from telegram.ext import Application, ContextTypes


class TelegramClient:
    """
    Telegram client wrapper around python-telegram-bot Application.
    
    Handles:
    - Application initialization from token
    - Connection management (start/stop)
    - Message sending with error handling
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Telegram client.
        
        Args:
            token: Bot token (if None, reads from TELEGRAM_BOT_TOKEN env var)
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("Telegram bot token not provided and TELEGRAM_BOT_TOKEN not set")
        
        self.application: Optional[Application] = None
        self.logger = logger.bind(component="telegram_client")
        self._is_running = False
    
    async def start(self):
        """Start the Telegram bot application."""
        if self._is_running:
            self.logger.warning("Telegram client already running")
            return
        
        try:
            self.logger.info("Starting Telegram client...")
            self.application = Application.builder().token(self.token).build()
            await self.application.initialize()
            await self.application.start()
            
            if self.application.updater:
                await self.application.updater.start_polling()
            
            self._is_running = True
            self.logger.info("✅ Telegram client started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Telegram client: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot application."""
        if not self._is_running:
            return
        
        try:
            self.logger.info("Stopping Telegram client...")
            
            if self.application and self.application.updater:
                await self.application.updater.stop()
            
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
            
            self._is_running = False
            self.logger.info("✅ Telegram client stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping Telegram client: {e}")
            raise
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = 'HTML',
        reply_markup: Optional[dict] = None,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Send a message to a chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_markup: Inline keyboard markup
            disable_web_page_preview: Disable web page preview
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.application or not self._is_running:
            self.logger.warning("Telegram client not running, cannot send message")
            return False
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        parse_mode: Optional[str] = 'HTML',
        reply_markup: Optional[dict] = None,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Edit an existing message.
        
        Args:
            chat_id: Telegram chat ID
            message_id: Message ID to edit
            text: New message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_markup: Inline keyboard markup
            disable_web_page_preview: Disable web page preview
        
        Returns:
            True if edited successfully, False otherwise
        """
        if not self.application or not self._is_running:
            self.logger.warning("Telegram client not running, cannot edit message")
            return False
        
        try:
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to edit Telegram message: {e}")
            return False
    
    @property
    def bot(self):
        """Get the bot instance."""
        if not self.application:
            return None
        return self.application.bot
    
    @property
    def is_running(self) -> bool:
        """Check if the client is running."""
        return self._is_running


async def init_telegram_app(token: Optional[str] = None) -> TelegramClient:
    """
    Bootstrap function to initialize and start Telegram bot with all handlers.
    
    This is the single entry point for initializing the Telegram bot:
    - Creates TelegramClient with token from env if not provided
    - Registers all command handlers (/start, /help, /portfolio, /positions, /risk, /health)
    - Registers callback handler for ai:* schema routing
    - Starts the application and begins polling
    
    Usage:
        client = await init_telegram_app()
        # Bot is now running and handling messages
    
    Args:
        token: Optional bot token (defaults to TELEGRAM_BOT_TOKEN env var)
    
    Returns:
        TelegramClient instance (running)
    
    Raises:
        ValueError: If token is not provided and TELEGRAM_BOT_TOKEN not set
        Exception: If startup fails
    """
    from adapters.telegram.handlers import get_handlers
    
    # Create client
    client = TelegramClient(token)
    
    # Build application (don't start yet)
    client.application = Application.builder().token(client.token).build()
    await client.application.initialize()
    
    # Register handlers BEFORE starting
    handlers = get_handlers()
    handlers.register_handlers(client.application)
    
    # Start application
    await client.application.start()
    
    if client.application.updater:
        await client.application.updater.start_polling()
    
    client._is_running = True
    client.logger.info("✅ Telegram bot initialized and started with all handlers")
    
    return client

