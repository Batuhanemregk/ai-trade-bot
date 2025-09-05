"""
Telegram Client - Robust notification system with queue, retry, and backoff
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger
import aiohttp


class TelegramClient:
    """Robust Telegram client with queue, retry, and backoff"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')
        self.timeout = config.get('timeout_sec', 10)
        self.retries = config.get('retries', 3)
        self.backoff_seconds = config.get('backoff_seconds', [2, 4, 8])
        
        # Queue configuration
        queue_config = config.get('queue', {})
        self.max_queue_size = queue_config.get('max_size', 100)
        self.drop_oldest = queue_config.get('drop_oldest', True)
        self.worker_interval = queue_config.get('worker_interval', 1.0)
        
        # State
        self.message_queue: List[Dict[str, Any]] = []
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Validation
        self.enabled = self._validate_config()
        
        if self.enabled:
            logger.info("✅ Telegram client initialized")
        else:
            logger.warning("⚠️ Telegram client disabled - invalid configuration")
    
    def _validate_config(self) -> bool:
        """Validate Telegram configuration"""
        if not self.bot_token or self.bot_token == "${TELEGRAM_BOT_TOKEN}":
            logger.warning("⚠️ Telegram bot token not configured")
            return False
        
        if not self.chat_id or self.chat_id == "${TELEGRAM_CHAT_ID}":
            logger.warning("⚠️ Telegram chat ID not configured")
            return False
        
        return True
    
    async def start(self):
        """Start the Telegram client worker"""
        if not self.enabled:
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("🚀 Telegram client worker started")
    
    async def stop(self):
        """Stop the Telegram client worker"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Telegram client worker stopped")
    
    async def send_message(self, text: str, priority: str = "normal") -> bool:
        """Send a message via Telegram (queued)"""
        if not self.enabled:
            return False
        
        message = {
            'text': text,
            'priority': priority,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'retry_count': 0
        }
        
        # Add to queue
        if len(self.message_queue) >= self.max_queue_size:
            if self.drop_oldest:
                self.message_queue.pop(0)  # Remove oldest
                logger.warning("⚠️ Telegram queue full, dropping oldest message")
            else:
                logger.warning("⚠️ Telegram queue full, message dropped")
                return False
        
        self.message_queue.append(message)
        return True
    
    async def _worker_loop(self):
        """Worker loop to process queued messages"""
        while self.is_running:
            try:
                if self.message_queue:
                    message = self.message_queue.pop(0)
                    success = await self._send_message_with_retry(message)
                    
                    if not success:
                        logger.error(f"❌ Failed to send Telegram message after {self.retries} retries")
                
                await asyncio.sleep(self.worker_interval)
                
            except Exception as e:
                logger.error(f"❌ Telegram worker error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _send_message_with_retry(self, message: Dict[str, Any]) -> bool:
        """Send message with retry and backoff"""
        text = message['text']
        retry_count = message['retry_count']
        
        for attempt in range(self.retries):
            try:
                success = await self._send_direct_message(text)
                if success:
                    return True
                
                # Wait before retry
                if attempt < self.retries - 1:
                    backoff_time = self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)]
                    logger.warning(f"⚠️ Telegram send failed (attempt {attempt + 1}/{self.retries}), retrying in {backoff_time}s")
                    await asyncio.sleep(backoff_time)
                
            except Exception as e:
                logger.error(f"❌ Telegram send error (attempt {attempt + 1}): {e}")
                if attempt < self.retries - 1:
                    backoff_time = self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)]
                    await asyncio.sleep(backoff_time)
        
        return False
    
    async def _send_direct_message(self, text: str) -> bool:
        """Send message directly to Telegram API"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("✅ Telegram message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram API error {response.status}: {error_text}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("❌ Telegram send timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queue_size': len(self.message_queue),
            'max_queue_size': self.max_queue_size,
            'enabled': self.enabled,
            'is_running': self.is_running
        }
