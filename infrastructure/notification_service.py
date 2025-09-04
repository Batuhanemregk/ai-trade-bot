"""
Notification Manager - Handles all system notifications.
Follows Single Responsibility Principle by only handling notifications.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from telegram_bot.bot import TelegramBot


class NotificationManager:
    """
    Notification manager that handles all system notifications.
    
    Responsibilities:
    - Manage notification queuing and delivery
    - Handle different notification types
    - Rate limiting and batching
    - Notification history and retry logic
    """
    
    def __init__(
        self,
        telegram_bot: TelegramBot,
        config: Dict[str, Any]
    ):
        self.telegram_bot = telegram_bot
        self.config = config
        
        # Notification settings
        self.notifications_enabled = config.get('notifications', {}).get('telegram_enabled', True)
        self.risk_alerts_enabled = config.get('notifications', {}).get('risk_alerts', True)
        self.trade_notifications_enabled = config.get('notifications', {}).get('trade_notifications', True)
        self.system_notifications_enabled = config.get('notifications', {}).get('system_notifications', True)
        
        # Rate limiting
        self.max_notifications_per_minute = 10
        self.max_notifications_per_hour = 100
        self.notification_cooldown = 5  # seconds between notifications
        
        # Notification state
        self.notification_queue = []
        self.notification_history = []
        self.last_notification_time = datetime.now()
        self.notifications_this_minute = 0
        self.notifications_this_hour = 0
        self.last_minute_reset = datetime.now()
        self.last_hour_reset = datetime.now()
        
        # Priority levels
        self.priority_levels = {
            "critical": 1,
            "error": 2,
            "warning": 3,
            "info": 4,
            "success": 5
        }
        
        # Notification templates
        self.templates = self._load_notification_templates()
        
        logger.info("Notification Manager initialized")
    
    async def send_notification(
        self, 
        title: str, 
        message: str, 
        level: str = "info",
        priority: Optional[int] = None,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification with rate limiting and queuing.
        
        Args:
            title: Notification title
            message: Notification message
            level: Notification level (critical, error, warning, info, success)
            priority: Custom priority (lower = higher priority)
            category: Notification category
            metadata: Additional metadata
            
        Returns:
            True if notification was sent/queued, False otherwise
        """
        try:
            if not self.notifications_enabled:
                logger.debug("Notifications disabled, skipping")
                return False
            
            # Check category-specific settings
            if not self._is_category_enabled(category):
                logger.debug(f"Category {category} disabled, skipping")
                return False
            
            # Create notification object
            notification = {
                "id": self._generate_notification_id(),
                "title": title,
                "message": message,
                "level": level,
                "priority": priority or self.priority_levels.get(level, 5),
                "category": category,
                "metadata": metadata or {},
                "timestamp": datetime.now(),
                "status": "queued"
            }
            
            # Add to queue
            self.notification_queue.append(notification)
            
            # Process queue
            await self._process_notification_queue()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue notification: {e}")
            return False
    
    async def send_risk_alert(
        self, 
        symbol: str, 
        risk_level: str, 
        risk_factors: List[str],
        recommendations: List[str]
    ) -> bool:
        """Send a risk alert notification."""
        try:
            if not self.risk_alerts_enabled:
                return False
            
            title = f"🚨 Risk Alert: {symbol}"
            message = self._format_risk_alert(symbol, risk_level, risk_factors, recommendations)
            
            return await self.send_notification(
                title=title,
                message=message,
                level="warning" if risk_level == "medium" else "error",
                category="risk",
                metadata={
                    "symbol": symbol,
                    "risk_level": risk_level,
                    "risk_factors": risk_factors,
                    "recommendations": recommendations
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send risk alert: {e}")
            return False
    
    async def send_trade_notification(
        self, 
        symbol: str, 
        action: str, 
        side: str, 
        size: float, 
        price: float,
        pnl: Optional[float] = None
    ) -> bool:
        """Send a trade notification."""
        try:
            if not self.trade_notifications_enabled:
                return False
            
            title = f"📊 Trade {action.title()}: {symbol}"
            message = self._format_trade_notification(symbol, action, side, size, price, pnl)
            
            level = "success" if action in ["opened", "closed"] else "info"
            
            return await self.send_notification(
                title=title,
                message=message,
                level=level,
                category="trade",
                metadata={
                    "symbol": symbol,
                    "action": action,
                    "side": side,
                    "size": size,
                    "price": price,
                    "pnl": pnl
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send trade notification: {e}")
            return False
    
    async def send_system_notification(
        self, 
        title: str, 
        message: str, 
        level: str = "info"
    ) -> bool:
        """Send a system notification."""
        try:
            if not self.system_notifications_enabled:
                return False
            
            return await self.send_notification(
                title=title,
                message=message,
                level=level,
                category="system"
            )
            
        except Exception as e:
            logger.error(f"Failed to send system notification: {e}")
            return False
    
    async def send_portfolio_update(
        self, 
        portfolio_summary: Dict[str, Any]
    ) -> bool:
        """Send a portfolio update notification."""
        try:
            title = "📊 Portfolio Update"
            message = self._format_portfolio_update(portfolio_summary)
            
            return await self.send_notification(
                title=title,
                message=message,
                level="info",
                category="portfolio",
                metadata={"portfolio_summary": portfolio_summary}
            )
            
        except Exception as e:
            logger.error(f"Failed to send portfolio update: {e}")
            return False
    
    async def send_performance_report(
        self, 
        performance_data: Dict[str, Any],
        period: str = "daily"
    ) -> bool:
        """Send a performance report notification."""
        try:
            title = f"📈 {period.title()} Performance Report"
            message = self._format_performance_report(performance_data, period)
            
            return await self.send_notification(
                title=title,
                message=message,
                level="info",
                category="performance",
                metadata={"performance_data": performance_data, "period": period}
            )
            
        except Exception as e:
            logger.error(f"Failed to send performance report: {e}")
            return False
    
    async def _process_notification_queue(self):
        """Process the notification queue with rate limiting."""
        try:
            if not self.notification_queue:
                return
            
            # Check rate limits
            if not self._can_send_notification():
                return
            
            # Sort by priority (lower number = higher priority)
            self.notification_queue.sort(key=lambda x: x["priority"])
            
            # Send highest priority notification
            notification = self.notification_queue.pop(0)
            
            # Send through Telegram
            success = await self._send_telegram_notification(notification)
            
            # Update status
            notification["status"] = "sent" if success else "failed"
            notification["sent_at"] = datetime.now()
            
            # Add to history
            self.notification_history.append(notification)
            
            # Update rate limiting counters
            self._update_rate_limit_counters()
            
            # Clean up old history
            self._cleanup_notification_history()
            
            logger.debug(f"Processed notification: {notification['title']}")
            
        except Exception as e:
            logger.error(f"Failed to process notification queue: {e}")
    
    async def _send_telegram_notification(self, notification: Dict[str, Any]) -> bool:
        """Send notification through Telegram.
        Falls back to direct Bot API if the bot application isn't running.
        """
        try:
            # Format message
            formatted_message = self._format_notification_message(notification)

            # Preferred path: use running TelegramBot application (rich formatting, lifecycle)
            try:
                if getattr(self.telegram_bot, "application", None):
                    await self.telegram_bot.send_notification(
                        notification["title"],
                        formatted_message,
                        notification["level"]
                    )
                    return True
            except Exception as e:
                logger.warning(f"Primary Telegram send path failed, will try direct Bot API: {e}")

            # Fallback path: use direct Bot API without starting polling application
            try:
                import os
                from telegram import Bot as TelegramCoreBot

                token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_CHAT_ID")

                if not token or not chat_id:
                    logger.warning("Telegram token or chat_id not set; skipping send")
                    return False

                # Build full message including title/level like send_notification does
                title = notification.get("title", "Notification")
                level = notification.get("level", "info")
                prefix = "ℹ️ "
                if level == "success":
                    prefix = "✅ "
                elif level == "warning":
                    prefix = "⚠️ "
                elif level == "error":
                    prefix = "❌ "

                full_message = f"{prefix}<b>{title}</b>\n\n{formatted_message}"

                core_bot = TelegramCoreBot(token=token)
                await core_bot.send_message(chat_id=chat_id, text=full_message, parse_mode='HTML')
                logger.info("Telegram message sent via direct Bot API fallback")
                return True
            except Exception as e:
                logger.error(f"Direct Bot API send failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def _can_send_notification(self) -> bool:
        """Check if we can send a notification based on rate limits."""
        now = datetime.now()
        
        # Reset counters if needed
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.notifications_this_minute = 0
            self.last_minute_reset = now
        
        if (now - self.last_hour_reset).total_seconds() >= 3600:
            self.notifications_this_hour = 0
            self.last_hour_reset = now
        
        # Check limits
        if self.notifications_this_minute >= self.max_notifications_per_minute:
            return False
        
        if self.notifications_this_hour >= self.max_notifications_per_hour:
            return False
        
        # Check cooldown
        if (now - self.last_notification_time).total_seconds() < self.notification_cooldown:
            return False
        
        return True
    
    def _update_rate_limit_counters(self):
        """Update rate limiting counters."""
        self.notifications_this_minute += 1
        self.notifications_this_hour += 1
        self.last_notification_time = datetime.now()
    
    def _is_category_enabled(self, category: str) -> bool:
        """Check if a notification category is enabled."""
        category_settings = {
            "risk": self.risk_alerts_enabled,
            "trade": self.trade_notifications_enabled,
            "system": self.system_notifications_enabled,
            "portfolio": True,  # Always enabled
            "performance": True,  # Always enabled
            "general": True      # Always enabled
        }
        
        return category_settings.get(category, True)
    
    def _generate_notification_id(self) -> str:
        """Generate a unique notification ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"notif_{timestamp}"
    
    def _format_notification_message(self, notification: Dict[str, Any]) -> str:
        """Format notification message using templates."""
        try:
            template = self.templates.get(notification["category"], {})
            format_func = template.get(notification["level"], self._default_format)
            
            return format_func(notification)
            
        except Exception as e:
            logger.error(f"Failed to format notification message: {e}")
            return self._default_format(notification)
    
    def _format_risk_alert(
        self, 
        symbol: str, 
        risk_level: str, 
        risk_factors: List[str], 
        recommendations: List[str]
    ) -> str:
        """Format risk alert message."""
        message = f"Symbol: {symbol}\n"
        message += f"Risk Level: {risk_level.upper()}\n\n"
        
        if risk_factors:
            message += "Risk Factors:\n"
            for factor in risk_factors[:5]:  # Limit to 5 factors
                message += f"• {factor}\n"
            message += "\n"
        
        if recommendations:
            message += "Recommendations:\n"
            for rec in recommendations[:3]:  # Limit to 3 recommendations
                message += f"• {rec}\n"
        
        return message
    
    def _format_trade_notification(
        self, 
        symbol: str, 
        action: str, 
        side: str, 
        size: float, 
        price: float,
        pnl: Optional[float]
    ) -> str:
        """Format trade notification message."""
        message = f"Symbol: {symbol}\n"
        message += f"Action: {action.title()}\n"
        message += f"Side: {side.upper()}\n"
        message += f"Size: {size:.4f}\n"
        message += f"Price: ${price:.2f}\n"
        
        if pnl is not None:
            message += f"PnL: ${pnl:.2f}"
        
        return message
    
    def _format_portfolio_update(self, portfolio_summary: Dict[str, Any]) -> str:
        """Format portfolio update message."""
        try:
            overview = portfolio_summary.get("overview", {})
            positions = portfolio_summary.get("positions", {})
            
            message = "Portfolio Summary:\n"
            message += f"Total Balance: ${overview.get('total_balance', 0):,.2f}\n"
            message += f"Total PnL: ${overview.get('total_pnl', 0):,.2f}\n"
            message += f"Daily PnL: ${overview.get('daily_pnl', 0):,.2f}\n"
            message += f"Positions: {positions.get('count', 0)}\n"
            message += f"Exposure: {positions.get('exposure_ratio', 0):.1%}"
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to format portfolio update: {e}")
            return "Portfolio update available"
    
    def _format_performance_report(
        self, 
        performance_data: Dict[str, Any], 
        period: str
    ) -> str:
        """Format performance report message."""
        try:
            message = f"{period.title()} Performance:\n"
            
            if "total_return" in performance_data:
                message += f"Total Return: {performance_data['total_return']:.2%}\n"
            
            if "daily_return" in performance_data:
                message += f"Daily Return: {performance_data['daily_return']:.2%}\n"
            
            if "total_pnl" in performance_data:
                message += f"Total PnL: ${performance_data['total_pnl']:,.2f}\n"
            
            if "position_count" in performance_data:
                message += f"Active Positions: {performance_data['position_count']}"
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to format performance report: {e}")
            return f"{period.title()} performance report available"
    
    def _default_format(self, notification: Dict[str, Any]) -> str:
        """Default notification format."""
        message = notification["message"]
        
        if notification["metadata"]:
            message += "\n\nMetadata:"
            for key, value in notification["metadata"].items():
                if isinstance(value, (str, int, float)):
                    message += f"\n{key}: {value}"
        
        return message
    
    def _load_notification_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load notification templates."""
        return {
            "risk": {
                "error": self._format_risk_alert,
                "warning": self._format_risk_alert
            },
            "trade": {
                "success": self._format_trade_notification,
                "info": self._format_trade_notification
            },
            "portfolio": {
                "info": self._format_portfolio_update
            },
            "performance": {
                "info": self._format_performance_report
            }
        }
    
    def _cleanup_notification_history(self):
        """Clean up old notification history."""
        try:
            # Keep only last 1000 notifications
            if len(self.notification_history) > 1000:
                self.notification_history = self.notification_history[-1000:]
            
            # Remove notifications older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            self.notification_history = [
                n for n in self.notification_history
                if n.get("timestamp", datetime.now()) > cutoff_date
            ]
            
        except Exception as e:
            logger.error(f"Failed to cleanup notification history: {e}")
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        try:
            now = datetime.now()
            
            # Count by level
            level_counts = {}
            for notification in self.notification_history:
                level = notification.get("level", "unknown")
                level_counts[level] = level_counts.get(level, 0) + 1
            
            # Count by category
            category_counts = {}
            for notification in self.notification_history:
                category = notification.get("category", "unknown")
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by status
            status_counts = {}
            for notification in self.notification_history:
                status = notification.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_notifications": len(self.notification_history),
                "queued_notifications": len(self.notification_queue),
                "notifications_this_minute": self.notifications_this_minute,
                "notifications_this_hour": self.notifications_this_hour,
                "level_counts": level_counts,
                "category_counts": category_counts,
                "status_counts": status_counts,
                "last_notification": self.last_notification_time,
                "rate_limits": {
                    "max_per_minute": self.max_notifications_per_minute,
                    "max_per_hour": self.max_notifications_per_hour,
                    "cooldown_seconds": self.notification_cooldown
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {"error": str(e)}
    
    async def flush_notification_queue(self) -> int:
        """Flush all queued notifications (for testing/debugging)."""
        try:
            count = len(self.notification_queue)
            
            while self.notification_queue:
                await self._process_notification_queue()
                await asyncio.sleep(0.1)  # Small delay between notifications
            
            logger.info(f"Flushed {count} notifications from queue")
            return count
            
        except Exception as e:
            logger.error(f"Failed to flush notification queue: {e}")
            return 0
