"""
Analysis Cards Service - Rich Telegram cards for trading analysis
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from loguru import logger

from adapters.telegram_client import TelegramClient
from infrastructure.bootstrap import load_policy


class AnalysisCardsService:
    """Service for sending rich analysis cards to Telegram"""
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.telegram_client = None
        self.is_enabled = policy.get('analysis_cards', {}).get('enabled', False)
        
        if self.is_enabled:
            self._initialize_telegram()
    
    def _initialize_telegram(self):
        """Initialize Telegram client"""
        try:
            from infrastructure.notification_service import NotificationService
            notification_service = NotificationService()
            if notification_service.is_initialized:
                self.telegram_client = notification_service.telegram_client
                logger.info("✅ Analysis cards service initialized with Telegram")
            else:
                logger.warning("⚠️ Telegram not available for analysis cards")
        except Exception as e:
            logger.error(f"❌ Failed to initialize analysis cards: {e}")
    
    async def send_startup_message(self):
        """Send startup message"""
        if not self.is_enabled or not self.telegram_client:
            return
        
        try:
            message = self._create_startup_card()
            # Start worker if not running
            if not self.telegram_client.is_running:
                await self.telegram_client.start()
            # Send message
            success = await self.telegram_client.send_message(message)
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
            message = self._create_shutdown_card()
            # Start worker if not running
            if not self.telegram_client.is_running:
                await self.telegram_client.start()
            # Send message
            success = await self.telegram_client.send_message(message)
            if success:
                logger.info("📊 [CARDS] Shutdown message sent")
            else:
                logger.error("❌ Failed to send shutdown message")
        except Exception as e:
            logger.error(f"❌ Failed to send shutdown message: {e}")
    
    async def send_analysis_cards(self, analysis_results: List[Dict[str, Any]]):
        """Send analysis cards for all symbols"""
        if not self.is_enabled or not self.telegram_client:
            return
        
        try:
            # Start worker if not running
            if not self.telegram_client.is_running:
                await self.telegram_client.start()
            
            # Group results by decision
            long_symbols = [r for r in analysis_results if r.get('decision') == 'LONG']
            short_symbols = [r for r in analysis_results if r.get('decision') == 'SHORT']
            flat_symbols = [r for r in analysis_results if r.get('decision') == 'FLAT']
            
            # Send summary first
            summary_message = self._create_summary_card(len(long_symbols), len(short_symbols), len(flat_symbols))
            success = await self.telegram_client.send_message(summary_message)
            if not success:
                logger.error("❌ Failed to send summary card")
                return
            
            # Send individual cards for each decision
            for symbol_data in long_symbols + short_symbols + flat_symbols:
                card_message = self._create_symbol_card(symbol_data)
                success = await self.telegram_client.send_message(card_message)
                if not success:
                    logger.error(f"❌ Failed to send card for {symbol_data.get('symbol', 'UNKNOWN')}")
                await asyncio.sleep(0.5)  # Rate limiting
            
            logger.info(f"📊 [CARDS] Sent {len(analysis_results)} analysis cards")
            
        except Exception as e:
            logger.error(f"❌ Failed to send analysis cards: {e}")
    
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
    
    def _create_summary_card(self, long_count: int, short_count: int, flat_count: int) -> str:
        """Create summary card"""
        now = datetime.now(timezone.utc)
        total = long_count + short_count + short_count
        
        return f"""
📊 <b>Market Analysis Summary</b>
⏰ <b>Time:</b> {now.strftime('%H:%M:%S')} UTC
📈 <b>LONG:</b> {long_count} symbols
📉 <b>SHORT:</b> {short_count} symbols
➡️ <b>FLAT:</b> {flat_count} symbols
🔢 <b>Total:</b> {total} symbols analyzed

<i>Detailed analysis below ⬇️</i>
"""
    
    def _create_symbol_card(self, data: Dict[str, Any]) -> str:
        """Create individual symbol card"""
        symbol = data.get('symbol', 'UNKNOWN')
        decision = data.get('decision', 'FLAT')
        final_score = data.get('final_score', 0)
        ta_score = data.get('ta_score', 0)
        ml_score = data.get('ml_score', 0)
        news_score = data.get('news_score', 0)
        risk_score = data.get('risk_score', 0)
        
        # Decision emoji
        decision_emoji = {
            'LONG': '🟢',
            'SHORT': '🔴', 
            'FLAT': '⚪'
        }.get(decision, '❓')
        
        # News info
        news_info = data.get('news_info', {})
        news_type = news_info.get('type', 'general')
        news_confidence = news_info.get('confidence', 0)
        news_title = news_info.get('title', 'No recent news')[:50]
        
        # Risk info
        risk_info = data.get('risk_info', {})
        risk_level = risk_info.get('level', 'medium')
        risk_factors = risk_info.get('factors', [])
        
        return f"""
{decision_emoji} <b>{symbol}</b> - {decision}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Scores:</b>
• Final: {final_score:.1f}
• TA: {ta_score:.1f}
• ML: {ml_score:.1f}
• News: {news_score:.1f}
• Risk: {risk_score:.1f}

📰 <b>News:</b> {news_type} ({news_confidence:.1f})
<i>{news_title}...</i>

⚠️ <b>Risk:</b> {risk_level}
<i>{', '.join(risk_factors[:3])}</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
