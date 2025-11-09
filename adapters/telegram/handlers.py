"""
Telegram Handlers - Command and callback handlers
Handles /start, /help, /portfolio, /positions, /risk, /health commands
and routes callbacks with ai:* schema to view builders.
"""

import time
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from adapters.telegram.context_resolver import get_context_resolver
from adapters.telegram.views import (
    build_main_view,
    build_signals_view,
    build_risk_view,
    build_orders_view,
    build_tpsl_view,
    build_trailing_view,
    build_pnl_view,
    build_settings_view,
    build_positions_view,
    build_analysis_summary_view,
    build_analysis_detail_view,
)
from adapters.telegram.keyboards import build_keyboard
from adapters.telegram.callback_registry import get_callback_registry
from adapters.telegram.formatter import get_formatter
from adapters.telegram.middleware import (
    get_rate_limiter,
    get_error_handler,
    get_logging_middleware,
    get_metrics_hook,
)


class TelegramHandlers:
    """
    Telegram command and callback handlers.
    
    Features:
    - Command handlers for /start, /help, /portfolio, etc.
    - Callback routing with ai:* schema
    - View builders integration
    - Error handling and logging
    - Metrics recording
    """
    
    def __init__(self):
        self.logger = logger.bind(component="telegram_handlers")
        self.context_resolver = get_context_resolver()
        self.callback_registry = get_callback_registry()
        self.formatter = get_formatter()
        self.rate_limiter = get_rate_limiter()
        self.error_handler = get_error_handler()
        self.logging_middleware = get_logging_middleware()
        self.metrics_hook = get_metrics_hook()
    
    def register_handlers(self, application):
        """
        Register all handlers with the Telegram application.
        
        Args:
            application: Telegram Application instance
        """
        from telegram.ext import CommandHandler, CallbackQueryHandler
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.handle_start))
        application.add_handler(CommandHandler("help", self.handle_help))
        application.add_handler(CommandHandler("portfolio", self.handle_portfolio))
        application.add_handler(CommandHandler("positions", self.handle_positions))
        application.add_handler(CommandHandler("risk", self.handle_risk))
        application.add_handler(CommandHandler("health", self.handle_health))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        self.logger.info("Registered Telegram handlers")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        start_time = time.time()
        try:
            user_id = update.effective_user.id
            
            # Rate limiting
            if not self.rate_limiter.is_allowed(str(user_id)):
                await update.message.reply_text("Rate limit exceeded. Please wait.")
                self.metrics_hook.record_rate_limit()
                return
            
            # Get main view
            main_context = await self.context_resolver.resolve_main_context()
            text, buttons = build_main_view(main_context, self.formatter)
            
            # Validate and truncate message size if needed
            is_valid, _ = self.formatter.validate_message_size(text)
            if not is_valid:
                text = self.formatter.truncate_message(text)
            
            # Build keyboard
            keyboard = build_keyboard(buttons)
            
            # Send message
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Record metrics
            render_time_ms = (time.time() - start_time) * 1000
            size_bytes = len(text.encode('utf-8'))
            success = True
            self.metrics_hook.record_view_render('main', render_time_ms, size_bytes, success=success)
            self.logging_middleware.log_render('main', render_time_ms, size_bytes)
            
        except Exception as e:
            self.logger.error(f"Error in handle_start: {e}", exc_info=True)
            self.metrics_hook.record_error('start_command', 'telegram')
            render_time_ms = (time.time() - start_time) * 1000
            self.logging_middleware.log_render('main', render_time_ms, 0, additional_context={'error': True})
            await update.message.reply_text("Error: Couldn't load dashboard. Please try again.")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """🤖 **AiBotBS Commands**

**Trading:**
• /start - Main dashboard
• /portfolio - Portfolio overview
• /positions - Current positions
• /risk - Risk management info

**System:**
• /health - System health status
• /help - Show this help

**Navigation:**
Use buttons in messages to navigate between views.
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command - shows main view."""
        await self.handle_start(update, context)
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command - shows positions view."""
        start_time = time.time()
        try:
            user_id = update.effective_user.id
            
            # Rate limiting
            if not self.rate_limiter.is_allowed(str(user_id)):
                await update.message.reply_text("Rate limit exceeded. Please wait.")
                self.metrics_hook.record_rate_limit()
                return
            
            # Get positions view
            positions_context = await self.context_resolver.resolve_positions_context()
            text, buttons = build_positions_view(positions_context, self.formatter)
            
            # Validate and truncate message size if needed
            is_valid, _ = self.formatter.validate_message_size(text)
            if not is_valid:
                text = self.formatter.truncate_message(text)
            
            # Build keyboard
            keyboard = build_keyboard(buttons)
            
            # Send message
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Record metrics
            render_time_ms = (time.time() - start_time) * 1000
            size_bytes = len(text.encode('utf-8'))
            self.metrics_hook.record_view_render('positions', render_time_ms, size_bytes, success=True)
            self.logging_middleware.log_render('positions', render_time_ms, size_bytes)
            
        except Exception as e:
            self.logger.error(f"Error in handle_positions: {e}", exc_info=True)
            self.metrics_hook.record_error('positions_command', 'telegram')
            await update.message.reply_text("Error: Couldn't load positions. Please try again.")
    
    async def handle_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command - shows risk view."""
        start_time = time.time()
        try:
            user_id = update.effective_user.id
            
            # Rate limiting
            if not self.rate_limiter.is_allowed(str(user_id)):
                await update.message.reply_text("Rate limit exceeded. Please wait.")
                return
            
            # Get risk view
            risk_context = await self.context_resolver.resolve_risk_context()
            text, buttons = build_risk_view(risk_context, self.formatter)
            
            # Validate and truncate message size if needed
            is_valid, _ = self.formatter.validate_message_size(text)
            if not is_valid:
                text = self.formatter.truncate_message(text)
            
            # Build keyboard
            keyboard = build_keyboard(buttons)
            
            # Send message
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Record metrics
            render_time_ms = (time.time() - start_time) * 1000
            size_bytes = len(text.encode('utf-8'))
            self.metrics_hook.record_view_render('risk', render_time_ms, size_bytes, success=True)
            self.logging_middleware.log_render('risk', render_time_ms, size_bytes)
            
        except Exception as e:
            self.logger.error(f"Error in handle_risk: {e}", exc_info=True)
            self.metrics_hook.record_error('risk_command', 'telegram')
            await update.message.reply_text("Error: Couldn't load risk view. Please try again.")
    
    async def handle_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /health command."""
        health_text = """🟢 **System Health**

Status: Healthy
Mode: Paper
Last Job: Active

Use /start to view dashboard."""
        await update.message.reply_text(health_text, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle callback queries with ai:* schema.
        
        Routes callbacks to appropriate view builders.
        Edits message instead of sending new one.
        """
        query = update.callback_query
        await query.answer()
        
        start_time = time.time()
        
        try:
            user_id = query.from_user.id
            callback_data_raw = query.data
            
            # Resolve callback through registry
            callback_data = self.callback_registry.resolve(callback_data_raw)
            
            # Parse callback schema: ai:<view>|k1=v1|k2=v2
            parsed = self._parse_callback(callback_data)
            view_id = parsed.get('view', 'main')
            params = parsed.get('params', {})
            
            # Rate limiting
            if not self.rate_limiter.is_allowed(str(user_id)):
                await query.answer("Rate limit exceeded", show_alert=False)
                self.metrics_hook.record_rate_limit()
                return
            
            # Route to view builder
            text, buttons = await self._build_view(view_id, params)
            
            # Validate and truncate message size if needed
            is_valid, size_bytes_pre = self.formatter.validate_message_size(text)
            if not is_valid:
                # Truncate message if exceeds limit
                text = self.formatter.truncate_message(text)
                size_bytes_pre = len(text.encode('utf-8'))
            
            # Build keyboard
            keyboard = build_keyboard(buttons)
            
            # Edit message
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                # Message might be identical or deleted
                if "message is not modified" in str(e).lower():
                    self.logger.debug("Message not modified (expected)")
                elif "message to edit not found" in str(e).lower():
                    # Message deleted, send new one
                    await query.message.reply_text(
                        text,
                        reply_markup=keyboard,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                else:
                    raise
            
            # Log callback
            process_time_ms = (time.time() - start_time) * 1000
            self.logging_middleware.log_callback(callback_data, process_time_ms, view_id)
            
            # Record metrics (use final size after truncation)
            size_bytes = len(text.encode('utf-8'))
            success = True
            self.metrics_hook.record_callback(view_id, params.get('act', 'view'), success=success)
            self.metrics_hook.record_view_render(view_id, process_time_ms, size_bytes, success=success)
            
        except Exception as e:
            self.logger.error(f"Error in handle_callback: {e}", exc_info=True)
            self.metrics_hook.record_error('callback', 'telegram')
            
            # Show error message
            error_response = self.error_handler.handle_error(e, "callback")
            await query.edit_message_text(
                error_response['text'],
                parse_mode='HTML'
            )
    
    def _parse_callback(self, callback_data: str) -> Dict[str, Any]:
        """
        Parse callback data with ai:* schema.
        
        Args:
            callback_data: Callback data string (e.g., "ai:sig|sym=BTC|act=open")
        
        Returns:
            Dict with 'view' and 'params' keys
        """
        if not callback_data.startswith('ai:'):
            return {'view': 'main', 'params': {}}
        
        # Remove 'ai:' prefix
        rest = callback_data[3:]
        
        # Split view and params
        parts = rest.split('|')
        view = parts[0]
        
        # Parse params
        params = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value
        
        return {'view': view, 'params': params}
    
    async def _build_view(self, view_id: str, params: Dict[str, Any]) -> tuple[str, list]:
        """
        Build view text and buttons based on view ID.
        
        Args:
            view_id: View ID (main, sig, risk, ord, tpsl, trl, pnl, set)
            params: View parameters
        
        Returns:
            Tuple of (text, buttons)
        """
        if view_id == 'an':
            if params.get('s'):
                context = await self.context_resolver.resolve_analysis_detail_context(params.get('s'))
                text, buttons = build_analysis_detail_view(context, self.formatter)
            else:
                context = await self.context_resolver.resolve_analysis_summary_context()
                text, buttons = build_analysis_summary_view(context, self.formatter)
            return text, buttons

        view_id_map = {
            'main': ('main', self.context_resolver.resolve_main_context, build_main_view),
            'sig': ('signals', lambda: self.context_resolver.resolve_signals_context(limit=6, symbol_filter=params.get('sym')), build_signals_view),
            'risk': ('risk', self.context_resolver.resolve_risk_context, build_risk_view),
            'ord': ('orders', lambda: self.context_resolver.resolve_orders_context(page=int(params.get('p', 0))), build_orders_view),
            'tpsl': ('tpsl', self.context_resolver.resolve_tpsl_context, build_tpsl_view),
            'trl': ('trailing', self.context_resolver.resolve_trailing_context, build_trailing_view),
            'pnl': ('pnl', self.context_resolver.resolve_pnl_context, build_pnl_view),
            'set': ('settings', lambda: self.context_resolver.resolve_settings_context(user_id=None), build_settings_view),
            'pos': ('positions', self.context_resolver.resolve_positions_context, build_positions_view),
        }
        
        if view_id not in view_id_map:
            # Default to main
            view_id = 'main'
        
        view_name, context_resolver, view_builder = view_id_map[view_id]
        
        # Resolve context
        context = await context_resolver()
        
        # Build view
        text, buttons = view_builder(context, self.formatter)
        
        return text, buttons


# Global instance
_handlers: Optional[TelegramHandlers] = None


def get_handlers() -> TelegramHandlers:
    """Get the global handlers instance."""
    global _handlers
    if _handlers is None:
        _handlers = TelegramHandlers()
    return _handlers

