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
    build_emergency_view,
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
from adapters.telegram.action_dispatcher import get_action_dispatcher
from adapters.telegram.confirmation import get_confirmation_manager
from adapters.telegram.user_settings import get_user_settings


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
        # Phase 1: Action routing components
        self.action_dispatcher = get_action_dispatcher()
        self.confirmation_manager = get_confirmation_manager()
        self.user_settings = get_user_settings()
    
    async def _build_view(self, view_id: str, params: Dict[str, Any] = None) -> tuple:
        """
        Build a view by view_id.
        
        Args:
            view_id: View identifier (main, settings, pos, etc.)
            params: Optional parameters
            
        Returns:
            Tuple of (text, buttons)
        """
        params = params or {}
        user_id = params.get('u')
        
        # View ID to builder mapping
        if view_id == 'main':
            context = await self.context_resolver.resolve_main_context()
            return build_main_view(context, self.formatter)
        elif view_id in ['set', 'settings']:
            context = await self.context_resolver.resolve_settings_context(user_id)
            return build_settings_view(context, self.formatter)
        elif view_id in ['pos', 'positions']:
            context = await self.context_resolver.resolve_positions_context()
            return build_positions_view(context, self.formatter)
        elif view_id == 'sig':
            context = await self.context_resolver.resolve_signals_context()
            return build_signals_view(context, self.formatter)
        elif view_id == 'risk':
            context = await self.context_resolver.resolve_risk_context()
            return build_risk_view(context, self.formatter)
        elif view_id == 'orders':
            context = await self.context_resolver.resolve_orders_context()
            return build_orders_view(context, self.formatter)
        elif view_id == 'pnl':
            context = await self.context_resolver.resolve_pnl_context()
            return build_pnl_view(context, self.formatter)
        elif view_id == 'emg':
            context = await self.context_resolver.resolve_emergency_context()
            return build_emergency_view(context, self.formatter)
        # Advanced settings views
        elif view_id == 'adv':
            from adapters.telegram.views.advanced import build_advanced_menu
            context = {}
            return build_advanced_menu(context, self.formatter)
        elif view_id == 'adv_size':
            from adapters.telegram.views.advanced import build_position_size_view
            context = await self.context_resolver.resolve_position_size_context()
            return build_position_size_view(context, self.formatter)
        elif view_id == 'adv_coins':
            from adapters.telegram.views.advanced import build_coins_menu
            context = await self.context_resolver.resolve_coins_context()
            return build_coins_menu(context, self.formatter)
        elif view_id == 'adv_active':
            from adapters.telegram.views.advanced import build_active_coins_view
            context = await self.context_resolver.resolve_coins_context()
            return build_active_coins_view(context, self.formatter)
        elif view_id == 'adv_add':
            from adapters.telegram.views.advanced import build_add_coins_menu
            context = {}
            return build_add_coins_menu(context, self.formatter)
        elif view_id == 'adv_cat':
            from adapters.telegram.views.advanced import build_coin_category_view
            category = params.get('c', 'all')
            context = await self.context_resolver.resolve_coin_category_context(category)
            return build_coin_category_view(context, self.formatter)
        elif view_id == 'adv_thresh':
            from adapters.telegram.views.advanced import build_thresholds_view
            context = await self.context_resolver.resolve_thresholds_context()
            return build_thresholds_view(context, self.formatter)
        elif view_id == 'adv_age':
            from adapters.telegram.views.advanced import build_age_view
            context = await self.context_resolver.resolve_age_context()
            return build_age_view(context, self.formatter)
        elif view_id == 'adv_weight':
            from adapters.telegram.views.advanced import build_weights_view
            context = await self.context_resolver.resolve_weights_context()
            return build_weights_view(context, self.formatter)
        elif view_id == 'adv_mlboost':
            from adapters.telegram.views.advanced import build_ml_boost_view
            context = await self.context_resolver.resolve_ml_boost_context()
            return build_ml_boost_view(context, self.formatter)
        elif view_id == 'adv_atr':
            from adapters.telegram.views.advanced import build_atr_view
            context = await self.context_resolver.resolve_atr_context()
            return build_atr_view(context, self.formatter)
        # Signal history views
        elif view_id == 'sig_hist':
            from adapters.telegram.views.signals_history import build_signal_history_menu
            context = await self.context_resolver.resolve_signal_history_context()
            return build_signal_history_menu(context, self.formatter)
        elif view_id == 'sig_coin':
            from adapters.telegram.views.signals_history import build_coin_signals_view
            # Support both 's' and 'sym' parameter names for compatibility
            symbol = params.get('s', params.get('sym', ''))
            context = await self.context_resolver.resolve_coin_signals_context(symbol)
            return build_coin_signals_view(context, self.formatter)
        # Alerts view
        elif view_id == 'alerts':
            from adapters.telegram.views.alerts_history import build_alerts_view
            level = params.get('l', None)
            context = await self.context_resolver.resolve_alerts_context(level)
            return build_alerts_view(context, self.formatter)
        else:
            # Default to main view
            context = await self.context_resolver.resolve_main_context()
            return build_main_view(context, self.formatter)
    
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
            
            # ═══════════════════════════════════════════════════════════
            # ACTION ROUTING: ai:act|t=<action_type>|s=<symbol>|...
            # ═══════════════════════════════════════════════════════════
            if view_id == 'act':
                await self._handle_action(query, user_id, params)
                return
            
            # ═══════════════════════════════════════════════════════════
            # CONFIRMATION ROUTING: ai:cfm|tok=<token>|a=<accept|reject>
            # ═══════════════════════════════════════════════════════════
            if view_id == 'cfm':
                await self._handle_confirmation(query, user_id, params)
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
    
    async def _handle_action(self, query, user_id: int, params: Dict[str, Any]):
        """
        Handle action callbacks (ai:act|t=<type>|s=<symbol>|...).
        
        Actions:
        - close: Close a position
        - edit_sl: Edit stop loss
        - edit_tp: Edit take profit
        - cancel: Cancel an order
        - toggle: Toggle a setting
        - emergency: Emergency stop all
        """
        action_type = params.get('t', '')
        symbol = params.get('s', '')
        
        # Check if action needs confirmation
        needs_confirm = self.action_dispatcher.needs_confirmation(action_type)
        
        if needs_confirm:
            # Request confirmation first
            confirm_text, confirm_buttons = self.confirmation_manager.request_confirmation(
                action_type=action_type,
                symbol=symbol,
                params=params,
                user_id=user_id
            )
            keyboard = build_keyboard(confirm_buttons)
            await query.edit_message_text(
                confirm_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
        
        # Execute action directly - params dict contains symbol and user_id
        params['u'] = user_id  # Add user_id to params
        result = await self.action_dispatcher.dispatch(action_type, params)
        
        # Determine which view to return to
        next_view = result.next_view if result.next_view else params.get('back', 'main')
        
        # If action has next_view, redirect there with fresh data
        # For actions that require restart, show the message first
        if result.success and 'Restart' in result.message:
            # Show restart warning message with continue button
            text = f"✅ {result.message}"
            buttons = [[{'text': '◀️ Ayarlara Dön', 'callback_data': 'ai:set|r=1'}]]
            keyboard = build_keyboard(buttons)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        elif result.success and next_view in ['settings', 'main', 'pos', 'positions']:
            # Build the target view directly
            text, buttons = await self._build_view(next_view if next_view != 'positions' else 'pos', {'r': '1'})
            keyboard = build_keyboard(buttons)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            # Build response with back button
            if result.success:
                text = f"✅ {result.message}"
            else:
                text = f"❌ {result.message}"
            
            buttons = [[{'text': '◀️ Geri', 'callback_data': f'ai:{next_view}'}]]
            keyboard = build_keyboard(buttons)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        
        # Log action
        self.logger.info(f"Action executed: {action_type} {symbol} -> {result.success}")
        self.metrics_hook.record_callback('action', action_type, success=result.success)
    
    async def _handle_confirmation(self, query, user_id: int, params: Dict[str, Any]):
        """
        Handle confirmation callbacks (ai:cfm|tok=<token>|a=<accept|reject>).
        """
        token = params.get('tok', '')
        action = params.get('a', 'reject')  # accept or reject
        
        if action == 'accept':
            # Validate and execute the confirmed action
            pending = self.confirmation_manager.validate_token(token, user_id)
            
            if pending is None:
                await query.edit_message_text(
                    "❌ Onay süresi doldu veya geçersiz token.",
                    parse_mode='HTML'
                )
                return
            
            # Execute the action
            result = await self.action_dispatcher.dispatch(
                pending['action_type'],
                pending['symbol'],
                pending['params'],
                user_id
            )
            
            if result.success:
                text = f"✅ {result.message}"
            else:
                text = f"❌ {result.message}"
            
            back_view = pending['params'].get('back', 'pos')
            buttons = [[{'text': '◀️ Geri', 'callback': f'ai:{back_view}'}]]
            keyboard = build_keyboard(buttons)
            
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
            
        else:
            # Rejected - go back
            back_view = params.get('back', 'pos')
            text, buttons = await self._build_view(back_view, {})
            keyboard = build_keyboard(buttons)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')


# Global instance
_handlers: Optional[TelegramHandlers] = None


def get_handlers() -> TelegramHandlers:
    """Get the global handlers instance."""
    global _handlers
    if _handlers is None:
        _handlers = TelegramHandlers()
    return _handlers

