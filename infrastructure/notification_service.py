"""
Notification Service - Robust notification system with queue, retry, and backoff
"""

import asyncio
import os
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger

from adapters.telegram_client import TelegramClient


class NotificationService:
    """Robust notification service with queue, retry, and backoff"""
    
    def __init__(self, config_path: str = "configs/notifications.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.telegram_client = None
        self.is_initialized = False
        
        # Initialize if enabled
        if self.config.get('telegram', {}).get('enabled', False):
            self._initialize_telegram()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load notification configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    # Replace environment variables
                    config = self._replace_env_vars(config)
                    return config
            else:
                logger.warning(f"⚠️ Notification config not found: {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to load notification config: {e}")
            return {}
    
    def _replace_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace environment variables in config"""
        def replace_recursive(obj):
            if isinstance(obj, dict):
                return {k: replace_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_recursive(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
                env_var = obj[2:-1]
                return os.getenv(env_var, obj)
            else:
                return obj
        
        return replace_recursive(config)
    
    def _initialize_telegram(self):
        """Initialize Telegram client"""
        try:
            telegram_config = self.config.get('telegram', {})
            self.telegram_client = TelegramClient(telegram_config)
            self.is_initialized = True
            logger.info("✅ Notification service initialized with Telegram")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram client: {e}")
            self.is_initialized = False
    
    async def start(self):
        """Start the notification service"""
        if self.telegram_client and self.is_initialized:
            await self.telegram_client.start()
            logger.info("🚀 Notification service started")
    
    async def stop(self):
        """Stop the notification service"""
        if self.telegram_client:
            await self.telegram_client.stop()
            logger.info("🛑 Notification service stopped")
    
    async def send_entry_notification(self, symbol: str, direction: str, size: float, price: float, reason: str):
        """Send position entry notification"""
        if not self._is_notification_enabled('trade_events'):
            return
        
        template = self.config.get('templates', {}).get('entry', 
            "🚀 [ENTRY] {symbol} {direction} size={size} px={price} reason={reason}")
        
        message = template.format(
            symbol=symbol,
            direction=direction.upper(),
            size=f"{size:.6f}",
            price=f"{price:.2f}",
            reason=reason
        )
        
        await self._send_message(message, "high")
    
    async def send_exit_notification(self, symbol: str, reason: str, pnl: float, r_multiple: float):
        """Send position exit notification"""
        if not self._is_notification_enabled('trade_events'):
            return
        
        template = self.config.get('templates', {}).get('exit',
            "💰 [EXIT] {symbol} {reason} pnl={pnl} r={r_multiple}")
        
        message = template.format(
            symbol=symbol,
            reason=reason,
            pnl=f"{pnl:.2f}",
            r_multiple=f"{r_multiple:.2f}R"
        )
        
        await self._send_message(message, "high")
    
    async def send_reversal_notification(self, symbol: str, strength: float, confirm: int, result: str):
        """Send reversal check notification"""
        if not self._is_notification_enabled('trade_events'):
            return
        
        template = self.config.get('templates', {}).get('reversal',
            "🔄 [REVCHK] {symbol} strength={strength} confirm={confirm} → {result}")
        
        message = template.format(
            symbol=symbol,
            strength=f"{strength:.2f}",
            confirm=confirm,
            result=result
        )
        
        await self._send_message(message, "normal")
    
    async def send_trailing_notification(self, symbol: str, be_price: float, tightened: bool):
        """Send trailing stop notification"""
        if not self._is_notification_enabled('trade_events'):
            return
        
        template = self.config.get('templates', {}).get('trailing',
            "📈 [TRAIL] {symbol} moved to BE={be_price} tightened={tightened}")
        
        message = template.format(
            symbol=symbol,
            be_price=f"{be_price:.2f}",
            tightened="YES" if tightened else "NO"
        )
        
        await self._send_message(message, "normal")
    
    async def send_risk_notification(self, symbol: str, alert_type: str, details: str):
        """Send risk alert notification"""
        if not self._is_notification_enabled('risk_alerts'):
            return
        
        template = self.config.get('templates', {}).get('risk',
            "⚠️ [RISK] {symbol} {alert_type} {details}")
        
        message = template.format(
            symbol=symbol,
            alert_type=alert_type,
            details=details
        )
        
        await self._send_message(message, "high")
    
    async def send_news_notification(self, symbol: str, classification: str, confidence: float, title: str):
        """Send news alert notification"""
        if not self._is_notification_enabled('news_alerts'):
            return
        
        template = self.config.get('templates', {}).get('news',
            "📰 [NEWS] {symbol} {classification} conf={confidence} {title}")
        
        message = template.format(
            symbol=symbol,
            classification=classification,
            confidence=f"{confidence:.2f}",
            title=title[:50] + "..." if len(title) > 50 else title
        )
        
        await self._send_message(message, "normal")
    
    async def send_system_notification(self, status: str, details: str):
        """Send system status notification"""
        if not self._is_notification_enabled('system_status'):
            return
        
        template = self.config.get('templates', {}).get('system',
            "🔧 [SYSTEM] {status} {details}")
        
        message = template.format(
            status=status,
            details=details
        )
        
        await self._send_message(message, "normal")
    
    def _is_notification_enabled(self, notification_type: str) -> bool:
        """Check if notification type is enabled"""
        return self.config.get('notifications', {}).get(notification_type, True)
    
    async def _send_message(self, message: str, priority: str = "normal"):
        """Send message via Telegram"""
        if not self.telegram_client or not self.is_initialized:
            logger.warning("⚠️ Telegram client not initialized, message not sent")
            return
        
        success = await self.telegram_client.send_message(message, priority)
        if not success:
            logger.error(f"❌ Failed to queue Telegram message: {message[:50]}...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification service statistics"""
        stats = {
            'initialized': self.is_initialized,
            'config_loaded': bool(self.config),
            'telegram_enabled': self.config.get('telegram', {}).get('enabled', False)
        }
        
        if self.telegram_client:
            stats['telegram'] = self.telegram_client.get_queue_stats()
        
        return stats
