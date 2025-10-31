import asyncio
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from application.jobs.base_job import BaseJob
from application.analysis_cards import AnalysisCardsService
from application.utils.markdown_escape import format_telegram_message

class TelegramSummary15mJob(BaseJob):
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.analysis_cards = None
    
    async def initialize(self, exchange_adapter=None):
        """Initialize the job"""
        self.exchange_adapter = exchange_adapter
        self.analysis_cards = AnalysisCardsService(self.policy)
        logger.info("✅ TelegramSummary15mJob initialized")
    
    async def cleanup(self):
        """Cleanup telegram summary resources"""
        try:
            if hasattr(self, 'analysis_cards') and self.analysis_cards:
                # Close telegram client session if exists
                if hasattr(self.analysis_cards, 'telegram_client') and self.analysis_cards.telegram_client:
                    await self.analysis_cards.telegram_client.stop()
                    logger.debug("✅ Closed telegram client for TelegramSummary15mJob")
        except Exception as e:
            logger.error(f"❌ TelegramSummary15mJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute the 15-minute summary job"""
        try:
            logger.info("[JOB] name=telegram_summary_15m status=STARTING")
            
            # Check idempotency for 15m bar
            bar_id = self.get_current_bar_id('15m')
            job_key = 'telegram_summary_15m'
            if self.is_bar_already_processed(job_key, '15m'):
                logger.info(f"already processed tf=15m bar={bar_id} → skipping")
                return
            
            # Get symbols from policy
            symbols = self.policy.get('exchange', {}).get('symbols', {}).get('supported_pairs', [])
            
            # Generate summary cards
            summary_cards = await self._generate_summary_cards(symbols)
            
            # Send to Telegram
            await self._send_summary_to_telegram(summary_cards)
            
            # Mark bar as processed
            self.mark_bar_processed(job_key, '15m')
            
            logger.info(f"[JOB] name=telegram_summary_15m status=SUCCESS dur=0.0s")
            
        except Exception as e:
            logger.error(f"[JOB] name=telegram_summary_15m status=FAIL error={e}")
    
    async def _generate_summary_cards(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Generate summary cards for all symbols"""
        cards = []
        
        for symbol in symbols:
            try:
                # Get analysis data (simplified for now)
                card = {
                    'symbol': symbol,
                    'final_score': 50.0,  # Placeholder
                    'ta_score': 45.0,
                    'ml_score': 55.0,
                    'news_score': 60.0,
                    'risk_score': 40.0,
                    'decision': 'FLAT',
                    'regime': 'NEUTRAL',
                    'position': 'NONE'
                }
                cards.append(card)
                
            except Exception as e:
                logger.error(f"Failed to generate card for {symbol}: {e}")
        
        return cards
    
    async def _send_summary_to_telegram(self, cards: List[Dict[str, Any]]):
        """Send summary to Telegram with chunking"""
        try:
            # Format message
            message = self._format_summary_message(cards)
            
            # Check message length and chunk if needed
            max_chars = 3500  # Telegram limit with safety margin
            if len(message) > max_chars:
                chunks = self._chunk_message(message, max_chars)
                for i, chunk in enumerate(chunks):
                    await self.analysis_cards.telegram_client.send_message(
                        f"📊 Market Summary ({i+1}/{len(chunks)})\n\n{chunk}"
                    )
                logger.info(f"[TG] message built symbols={len(cards)} chars={len(message)} parts={len(chunks)} parse=MarkdownV2")
            else:
                await self.analysis_cards.telegram_client.send_message(
                    f"📊 Market Summary\n\n{message}"
                )
                logger.info(f"[TG] message built symbols={len(cards)} chars={len(message)} parts=1 parse=MarkdownV2")
            
            logger.info(f"[TG] send ok len={len(message)}")
            
        except Exception as e:
            logger.error(f"[TG] send fail error={e}")
    
    def _format_summary_message(self, cards: List[Dict[str, Any]]) -> str:
        """Format summary message"""
        message_parts = []
        
        for card in cards:
            symbol = card['symbol']
            score = card['final_score']
            decision = card['decision']
            ta = card['ta_score']
            ml = card['ml_score']
            news = card['news_score']
            risk = card['risk_score']
            
            # Format card
            card_text = f"**{symbol}**\n"
            card_text += f"Score: {score:.1f} | {decision}\n"
            card_text += f"TA: {ta:.1f} | ML: {ml:.1f} | News: {news:.1f} | Risk: {risk:.1f}\n"
            card_text += "---\n"
            
            message_parts.append(card_text)
        
        return "\n".join(message_parts)
    
    def _chunk_message(self, message: str, max_chars: int) -> List[str]:
        """Chunk message into smaller parts"""
        chunks = []
        current_chunk = ""
        
        lines = message.split('\n')
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    # Line is too long, split it
                    chunks.append(line[:max_chars])
                    current_chunk = line[max_chars:]
            else:
                current_chunk += "\n" + line if current_chunk else line
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
