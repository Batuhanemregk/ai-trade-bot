"""
Analysis Cards Service - Rich Telegram cards for trading analysis
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from loguru import logger

from adapters.telegram.client import TelegramClient
from adapters.telegram.formatter import get_formatter
from adapters.telegram.views.analysis import (
    build_analysis_detail_view,
    build_analysis_summary_view,
)
from application.jobs.base_job import BaseJob
from infrastructure.feature_flags import TELEGRAM_MOCK_ENABLED
from application.analysis_cards_state import (
    set_latest_analysis,
    get_latest_analysis,
)
from adapters.telegram.keyboards import build_keyboard


class AnalysisCardsService:
    """Service for sending rich analysis cards to Telegram"""
    
    def __init__(self, policy: Dict[str, Any], telegram_client=None):
        self.policy = policy
        self.telegram_client = telegram_client
        self.is_enabled = policy.get('analysis_cards', {}).get('enabled', False)
        self.formatter = get_formatter()
        self.chat_id = None
        self.summary_state: Dict[str, Any] = {
            'message_id': None,
            'chat_id': None,
            'bar_id': None,
            'text': None,
            'keyboard_signature': None,
        }
        
        if self.is_enabled:
            self._initialize_telegram()
    
    def _initialize_telegram(self):
        """Initialize Telegram client"""
        try:
            # Get chat_id from policy or environment
            import os
            self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            if not self.chat_id:
                telegram_config = self.policy.get('telegram', {})
                self.chat_id = telegram_config.get('chat_id', '')
            
            # Telegram client should be passed from scheduler via constructor
            # If not provided, it will be None and cards won't be sent
            if self.telegram_client:
                logger.info("✅ Analysis cards service initialized with Telegram client")
            else:
                logger.info("ℹ️ Analysis cards service initialized (Telegram client not set - will be set by scheduler)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize analysis cards: {e}")
            self.telegram_client = None
    
    async def send_startup_message(self):
        """Send startup message"""
        if not self.is_enabled or not self.telegram_client:
            return
        
        try:
            # Get chat_id
            import os
            chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            if not chat_id:
                telegram_config = self.policy.get('telegram', {})
                chat_id = telegram_config.get('chat_id', '')
            if not chat_id:
                logger.warning("⚠️ No chat_id for startup message")
                return
            
            message = self._create_startup_card()
            # Send message
            success = await self.telegram_client.send_message(
                chat_id=str(chat_id),
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            if success:
                logger.info("📊 [CARDS] Startup message sent")
            else:
                logger.error("❌ Failed to send startup message")
        except Exception as e:
            logger.error(f"❌ Failed to send startup message: {e}")
    
    async def send_shutdown_message(self):
        """Send shutdown message"""
        if not self.is_enabled or not self.telegram_client:
            return
        
        try:
            # Get chat_id
            import os
            chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            if not chat_id:
                telegram_config = self.policy.get('telegram', {})
                chat_id = telegram_config.get('chat_id', '')
            if not chat_id:
                logger.warning("⚠️ No chat_id for shutdown message")
                return
            
            message = self._create_shutdown_card()
            # Send message
            success = await self.telegram_client.send_message(
                chat_id=str(chat_id),
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            if success:
                logger.info("📊 [CARDS] Shutdown message sent")
            else:
                logger.error("❌ Failed to send shutdown message")
        except Exception as e:
            logger.error(f"❌ Failed to send shutdown message: {e}")
    
    async def send_analysis_cards(self, analysis_results: List[Dict[str, Any]]):
        """Store analysis results in state for Telegram summary job and button callbacks."""
        if not analysis_results:
            logger.debug("📊 [CARDS] No analysis results to store")
            return
        
        # Determine bar/run identifiers
        first_entry = analysis_results[0]
        bar_id = first_entry.get('bar_id')
        if not bar_id:
            bar_id = BaseJob.get_bar_id(datetime.now(timezone.utc), '15m')
        run_id = first_entry.get('run_id', 'unknown')
        
        # Persist shared state for callbacks and summary job (15m periodic)
        set_latest_analysis(bar_id, run_id, analysis_results)
        logger.info(f"📊 [CARDS] Analysis state updated: bar_id={bar_id} run_id={run_id} symbols={len(analysis_results)}")
        
        # Note: Telegram summary will be sent by telegram_summary_15m job (every 15 minutes)
        # The job checks if analysis exists and sends it if not already published
        # This allows users to view analysis via buttons anytime, and get periodic summaries
        # The job runs at second=20 of each 15m bar, after trading_analysis completes (second=7)
    
    def _create_startup_card(self) -> str:
        """Create startup card"""
        now = datetime.now(timezone.utc)
        return f"""
🚀 <b>AiBotBS Scheduler Started</b>
⏰ <b>Time:</b> {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
📊 <b>Status:</b> All systems operational
🔧 <b>Jobs:</b> 6 active jobs registered
📰 <b>News:</b> CryptoCompare API active
🤖 <b>LLM:</b> OpenAI analysis enabled
💹 <b>Trading:</b> Live mode ready

<i>Analysis cards will be sent every 15 minutes</i>
"""
    
    def _create_shutdown_card(self) -> str:
        """Create shutdown card"""
        now = datetime.now(timezone.utc)
        return f"""
🛑 <b>AiBotBS Scheduler Stopped</b>
⏰ <b>Time:</b> {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
📊 <b>Status:</b> Graceful shutdown completed
🔧 <b>Jobs:</b> All jobs stopped
📰 <b>News:</b> Service stopped
🤖 <b>LLM:</b> Service stopped
💹 <b>Trading:</b> Service stopped

<i>Goodbye! 👋</i>
"""
    
    def _build_summary_context(
        self,
        bar_id: str,
        run_id: str,
        analysis_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build summary context for view builders."""
        sorted_results = sorted(
            analysis_results,
            key=lambda r: r.get('final_score', 0.0),
            reverse=True,
        )
        counts = {
            'LONG': sum(1 for r in analysis_results if r.get('decision') == 'LONG'),
            'SHORT': sum(1 for r in analysis_results if r.get('decision') == 'SHORT'),
            'FLAT': sum(1 for r in analysis_results if r.get('decision') == 'FLAT'),
        }
        
        # Get policy for timeframe and mode
        timeframe = self.policy.get('trading', {}).get('timeframe', '15m')
        mode = self.policy.get('trading', {}).get('mode', 'paper').lower()
        last_update = datetime.now(timezone.utc)
        
        return {
            'bar_id': bar_id,
            'run_id': run_id,
            'results': sorted_results,
            'counts': counts,
            'timeframe': timeframe,
            'mode': mode,
            'last_update': last_update,
            'generated_at': last_update.isoformat(),
        }
    
    async def _publish_summary(self, summary_context: Dict[str, Any]) -> None:
        """Send or edit summary message based on context."""
        text, buttons = build_analysis_summary_view(summary_context, self.formatter)
        keyboard_markup = build_keyboard(buttons)
        reply_markup = keyboard_markup.to_dict()
        keyboard_signature = tuple(
            tuple(button['callback_data'] for button in row)
            for row in buttons
        )
        
        if TELEGRAM_MOCK_ENABLED or not self.telegram_client:
            self.summary_state['bar_id'] = summary_context.get('bar_id')
            self.summary_state['text'] = "<mock>"
            self.summary_state['keyboard_signature'] = keyboard_signature
            return
        
        existing_bar = self.summary_state.get('bar_id')
        existing_text = self.summary_state.get('text')
        existing_sig = self.summary_state.get('keyboard_signature')
        if (self.summary_state.get('message_id') and
                existing_bar == summary_context.get('bar_id') and
                existing_text == text and
                existing_sig == keyboard_signature):
            return
        
        # Get chat_id from policy or state
        chat_id = self.summary_state.get('chat_id') or self.chat_id
        if not chat_id:
            # Try to get from policy (environment variable)
            import os
            chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            if not chat_id:
                telegram_config = self.policy.get('telegram', {})
                chat_id = telegram_config.get('chat_id', '')
            if not chat_id:
                logger.error("❌ [CARDS] No chat_id available for sending message")
                return
        
        # Store chat_id in state
        self.summary_state['chat_id'] = chat_id
        self.chat_id = chat_id
        
        # If we have existing message, try editing
        message_id = self.summary_state.get('message_id')
        success = False
        if message_id and chat_id:
            try:
                success = await self.telegram_client.edit_message_text(
                    chat_id=str(chat_id),
                    message_id=message_id,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                if not success:
                    logger.warning("Failed to edit summary message, sending a new one")
            except Exception as e:
                logger.warning(f"Failed to edit message: {e}, sending a new one")
                success = False
        
        if not success:
            try:
                # Send new message
                sent_message = await self.telegram_client.bot.send_message(
                    chat_id=str(chat_id),
                    text=text,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                if sent_message:
                    self.summary_state['message_id'] = sent_message.message_id
                    self.summary_state['chat_id'] = chat_id
                    success = True
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                success = False
        
        if success:
            self.summary_state['bar_id'] = summary_context.get('bar_id')
            self.summary_state['text'] = text
            self.summary_state['keyboard_signature'] = keyboard_signature
            logger.info(
                "📊 [CARDS] Summary published "
                f"bar={summary_context.get('bar_id')} run={summary_context.get('run_id')}"
            )
        else:
            logger.error(
                "❌ [CARDS] Failed to publish summary "
                f"bar={summary_context.get('bar_id')} run={summary_context.get('run_id')}"
            )
    
    async def publish_latest_summary(self) -> None:
        """Ensure latest summary is published (used by summary job)."""
        state = get_latest_analysis()
        if not state or not state.get('results'):
            return
        summary_context = self._build_summary_context(
            state.get('bar_id', '-'),
            state.get('run_id', 'unknown'),
            state.get('results', []),
        )
        await self._publish_summary(summary_context)
