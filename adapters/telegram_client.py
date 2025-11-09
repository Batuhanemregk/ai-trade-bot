"""
Telegram Client - Robust notification system with queue, retry, and backoff
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import aiohttp

from infrastructure.feature_flags import TELEGRAM_MOCK_ENABLED


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
        
        # Persistent session for connection reuse
        self._session: Optional[aiohttp.ClientSession] = None
        self._mock_message_id = 10_000
        
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
        
        # Initialize persistent session
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
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
        
        # Close persistent session
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        logger.info("🛑 Telegram client worker stopped")
    
    async def send_message(self, text: str, priority: str = "normal", reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Send a message via Telegram (queued)"""
        if not self.enabled:
            return False
        
        message = {
            'text': text,
            'priority': priority,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'retry_count': 0,
            'reply_markup': reply_markup,
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
        reply_markup = message.get('reply_markup')
        
        for attempt in range(self.retries):
            try:
                success, _ = await self._send_direct_message_json(text, reply_markup=reply_markup)
                success, _ = await self._send_direct_message_json(text, reply_markup=reply_markup)
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
    
    async def _send_direct_message_json(
        self,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Send message directly to Telegram API and return response JSON."""
        if TELEGRAM_MOCK_ENABLED:
            self._mock_message_id += 1
            logger.info(f"[MOCK] Telegram send message_id={self._mock_message_id} text={text[:48]}...")
            response = {
                'ok': True,
                'result': {
                    'message_id': self._mock_message_id,
                    'chat': {'id': self.chat_id},
                    'date': int(time.time()),
                    'text': text,
                }
            }
            return True, response
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            # Use persistent session if available, otherwise create temporary one
            if hasattr(self, '_session') and self._session and not self._session.closed:
                session = self._session
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except Exception:
                            data = {'ok': True}
                        logger.debug("✅ Telegram message sent successfully")
                        return True, data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram API error {response.status}: {error_text}")
                        return False, None
            else:
                # Create temporary session for single request
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                            except Exception:
                                data = {'ok': True}
                            logger.debug("✅ Telegram message sent successfully")
                            return True, data
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Telegram API error {response.status}: {error_text}")
                            return False, None
                        
        except asyncio.TimeoutError:
            logger.error("❌ Telegram send timeout")
            return False, None
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
            return False, None
    
    async def _send_direct_message(self, text: str) -> bool:
        """Backward-compatible helper returning boolean only."""
        success, _ = await self._send_direct_message_json(text)
        return success

    async def send_text_immediate(
        self,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Send a message immediately and return (success, response_json)."""
        if not self.enabled and not TELEGRAM_MOCK_ENABLED:
            return False, None
        return await self._send_direct_message_json(text, reply_markup=reply_markup)

    async def edit_message(
        self,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Edit an existing Telegram message."""
        if TELEGRAM_MOCK_ENABLED:
            logger.info(f"[MOCK] Telegram edit message_id={message_id} text={text[:48]}...")
            return True
        if not self.enabled:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        payload = {
            'chat_id': self.chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            if self._session and not self._session.closed:
                async with self._session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    error_text = await response.text()
                    logger.error(f"❌ Telegram edit error {response.status}: {error_text}")
                    return False
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            return True
                        error_text = await response.text()
                        logger.error(f"❌ Telegram edit error {response.status}: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Telegram edit exception: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queue_size': len(self.message_queue),
            'max_queue_size': self.max_queue_size,
            'enabled': self.enabled,
            'is_running': self.is_running
        }
