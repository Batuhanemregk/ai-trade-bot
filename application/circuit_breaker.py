"""
Circuit Breaker - Emergency stop and trading pause system
Follows Single Responsibility: Only handles emergency trading controls
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class CircuitBreakerState:
    """Circuit breaker state enumeration."""
    NORMAL = "normal"
    WARNING = "warning"
    SIZE_REDUCED = "size_reduced"  # New: 2 consecutive losses
    PAUSED = "paused"
    EMERGENCY = "emergency"


class CircuitBreaker:
    """
    Manages emergency trading controls and circuit breaker logic.
    
    Responsibilities:
    - Monitor dangerous conditions (daily loss, drawdown, consecutive losses)
    - Trigger emergency stops
    - Pause/resume trading
    - Track circuit breaker state
    """
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.state = CircuitBreakerState.NORMAL
        self.state_file = Path('data/circuit_breaker_state.json')
        
        # Thresholds from policy
        risk_config = policy.get('trading', {}).get('risk', {})
        self.daily_loss_limit = risk_config.get('max_daily_loss', 0.25)  # 25% default
        self.max_drawdown = risk_config.get('max_drawdown', 0.15)  # 15% default
        
        # Kademeli streak guard seviyeleri
        streak_config = risk_config.get('streak_guard', {})
        self.streak_levels = streak_config.get('levels', [
            {'losses': 2, 'action': 'reduce_size', 'reduction_pct': 50},
            {'losses': 3, 'action': 'cooldown', 'cooldown_hours': 2},
            {'losses': 5, 'action': 'cooldown', 'cooldown_hours': 6},
            {'losses': 7, 'action': 'full_stop', 'cooldown_hours': 24, 'notify_admin': True}
        ])
        self.max_consecutive_losses = streak_config.get('max_losses', 3)  # Eski uyumluluk
        self.cooldown_hours = streak_config.get('cooldown_hours', 24)  # Eski uyumluluk
        
        # State tracking
        self.daily_start_balance = None
        self.daily_start_time = None
        self.consecutive_losses = 0
        self.paused_until = None
        self.emergency_triggered = False
        
        # Yeni: Position size reduction tracking
        self.size_reduction_active = False
        self.size_reduction_pct = 0
        self.size_reduction_until = None
        self.last_win_time = None
        
        # Load previous state
        self._load_state()
        
        logger.info(f"✅ Circuit Breaker initialized (state={self.state})")
    
    async def check_conditions(self, portfolio: Dict[str, Any], recent_trades: list = None) -> str:
        """
        Check circuit breaker conditions.
        
        Args:
            portfolio: Current portfolio state
            recent_trades: Recent trades for streak analysis
            
        Returns:
            Current state: NORMAL, WARNING, PAUSED, EMERGENCY
        """
        try:
            # Check if paused
            if self.paused_until:
                if datetime.now(timezone.utc) < self.paused_until:
                    logger.info(f"⏸️ Trading paused until {self.paused_until}")
                    return CircuitBreakerState.PAUSED
                else:
                    # Pause expired
                    await self._resume_trading("Pause period expired")
            
            # Check if emergency already triggered
            if self.emergency_triggered:
                logger.warning("🚨 Emergency stop active")
                return CircuitBreakerState.EMERGENCY
            
            # Initialize daily tracking
            await self._check_daily_reset(portfolio)
            
            # Check 1: Daily loss limit
            if await self._check_daily_loss(portfolio):
                await self._trigger_emergency("Daily loss limit exceeded")
                return CircuitBreakerState.EMERGENCY
            
            # Check 2: Max drawdown
            if await self._check_drawdown(portfolio):
                await self._trigger_warning("High drawdown detected")
                return CircuitBreakerState.WARNING
            
            # Check 3: Consecutive losses
            if recent_trades and await self._check_consecutive_losses(recent_trades):
                await self._trigger_pause(self.cooldown_hours, "Consecutive loss limit")
                return CircuitBreakerState.PAUSED
            
            return CircuitBreakerState.NORMAL
            
        except Exception as e:
            logger.error(f"❌ Circuit breaker check failed: {e}")
            return self.state
    
    async def _check_daily_reset(self, portfolio: Dict[str, Any]):
        """Check if we need to reset daily tracking."""
        now = datetime.now(timezone.utc)
        
        # Initialize on first run or new day
        if (self.daily_start_time is None or 
            now.date() > self.daily_start_time.date()):
            
            self.daily_start_balance = portfolio.get('total_value', 0)
            self.daily_start_time = now
            self._save_state()
            
            logger.info(f"📅 Daily reset: balance=${self.daily_start_balance:.2f}")
    
    async def _check_daily_loss(self, portfolio: Dict[str, Any]) -> bool:
        """Check daily loss limit."""
        if not self.daily_start_balance or self.daily_start_balance == 0:
            return False
        
        current_value = portfolio.get('total_value', 0)
        daily_pnl = current_value - self.daily_start_balance
        daily_pnl_pct = daily_pnl / self.daily_start_balance
        
        logger.debug(f"💰 Daily PnL: ${daily_pnl:.2f} ({daily_pnl_pct:.2%})")
        
        if daily_pnl_pct < -abs(self.daily_loss_limit):
            logger.critical(
                f"🚨 DAILY LOSS LIMIT EXCEEDED: {daily_pnl_pct:.2%} < {-abs(self.daily_loss_limit):.2%}"
            )
            return True
        
        return False
    
    async def _check_drawdown(self, portfolio: Dict[str, Any]) -> bool:
        """Check drawdown limit."""
        drawdown = portfolio.get('max_drawdown', 0)
        
        if drawdown > self.max_drawdown:
            logger.warning(f"⚠️ High drawdown: {drawdown:.2%} > {self.max_drawdown:.2%}")
            return True
        
        return False
    
    async def _check_consecutive_losses(self, recent_trades: list) -> bool:
        """Check consecutive loss streak with tiered response."""
        if not recent_trades:
            return False
        
        # Count consecutive losses (most recent first)
        consecutive = 0
        for trade in reversed(recent_trades[-10:]):  # Last 10 trades
            pnl = trade.get('pnl', 0)
            if pnl < 0:
                consecutive += 1
            else:
                # Kazanç görüldü - size reduction'ı sıfırla
                if self.size_reduction_active:
                    await self._reset_size_reduction("Winning trade detected")
                break
        
        self.consecutive_losses = consecutive
        self._save_state()
        
        # Kademeli streak kontrolü
        action_taken = await self._apply_streak_action(consecutive)
        
        return action_taken
    
    async def _apply_streak_action(self, consecutive: int) -> bool:
        """Apply appropriate action based on consecutive loss count."""
        # En yüksek eşiği bul
        applicable_level = None
        for level in sorted(self.streak_levels, key=lambda x: x['losses'], reverse=True):
            if consecutive >= level['losses']:
                applicable_level = level
                break
        
        if not applicable_level:
            # Streak seviyesinin altında - size reduction varsa ve 2 saat geçtiyse sıfırla
            if self.size_reduction_active and self.size_reduction_until:
                if datetime.now(timezone.utc) >= self.size_reduction_until:
                    await self._reset_size_reduction("2 hour timeout expired")
            return False
        
        action = applicable_level['action']
        losses_threshold = applicable_level['losses']
        
        logger.warning(f"⚠️ Streak Guard: {consecutive} kayıp >= {losses_threshold} eşiği, aksiyon: {action}")
        
        if action == 'reduce_size':
            reduction_pct = applicable_level.get('reduction_pct', 50)
            await self._activate_size_reduction(reduction_pct, consecutive)
            return False  # Trading devam eder, sadece size azalır
        
        elif action == 'cooldown':
            hours = applicable_level.get('cooldown_hours', 2)
            await self._trigger_pause(hours, f"{consecutive} consecutive losses")
            return True
        
        elif action == 'full_stop':
            hours = applicable_level.get('cooldown_hours', 24)
            notify = applicable_level.get('notify_admin', True)
            await self._trigger_pause(hours, f"{consecutive} consecutive losses - FULL STOP")
            if notify:
                await self._send_telegram_alert(
                    "🚨 STREAK GUARD: FULL STOP",
                    f"**{consecutive} ardışık kayıp!**\n"
                    f"Trading 24 saat durduruldu.\n"
                    f"Manuel inceleme gerekli."
                )
            return True
        
        return False
    
    async def _activate_size_reduction(self, reduction_pct: int, consecutive: int):
        """Activate position size reduction."""
        self.size_reduction_active = True
        self.size_reduction_pct = reduction_pct
        self.size_reduction_until = datetime.now(timezone.utc) + timedelta(hours=2)
        self.state = CircuitBreakerState.SIZE_REDUCED
        self._save_state()
        
        logger.warning(f"📉 Position size %{reduction_pct} azaltıldı ({consecutive} kayıp). "
                      f"1 kazanç veya 2 saat sonra normale döner.")
        
        await self._send_telegram_alert(
            "📉 Position Size Azaltıldı",
            f"**{consecutive} ardışık kayıp tespit edildi**\n"
            f"Position size %{reduction_pct} azaltıldı.\n"
            f"Sıfırlama: 1 kazanç veya 2 saat"
        )
    
    async def _reset_size_reduction(self, reason: str):
        """Reset position size reduction."""
        self.size_reduction_active = False
        self.size_reduction_pct = 0
        self.size_reduction_until = None
        if self.state == CircuitBreakerState.SIZE_REDUCED:
            self.state = CircuitBreakerState.NORMAL
        self._save_state()
        
        logger.info(f"✅ Position size normale döndü: {reason}")
    
    def get_position_size_multiplier(self) -> float:
        """Get current position size multiplier (for use by trading logic)."""
        if self.size_reduction_active:
            return 1.0 - (self.size_reduction_pct / 100.0)  # e.g., 0.5 for 50% reduction
        return 1.0
    
    async def _trigger_emergency(self, reason: str):
        """Trigger emergency stop."""
        logger.critical(f"🚨 EMERGENCY STOP TRIGGERED: {reason}")
        
        self.state = CircuitBreakerState.EMERGENCY
        self.emergency_triggered = True
        self._save_state()
        
        # Send Telegram alert
        await self._send_telegram_alert(
            "🚨 EMERGENCY STOP",
            f"**Reason:** {reason}\n"
            f"**Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"**Action:** All positions should be closed\n"
            f"**Status:** Trading halted\n\n"
            f"Use `/resume` command to restart after investigating."
        )
    
    async def _trigger_warning(self, reason: str):
        """Trigger warning state."""
        logger.warning(f"⚠️ CIRCUIT BREAKER WARNING: {reason}")
        
        if self.state == CircuitBreakerState.NORMAL:
            self.state = CircuitBreakerState.WARNING
            self._save_state()
            
            await self._send_telegram_alert(
                "⚠️ Trading Warning",
                f"**Reason:** {reason}\n"
                f"**Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"**Action:** Trading continues with caution\n"
                f"**Recommendation:** Monitor closely"
            )
    
    async def _trigger_pause(self, hours: int, reason: str):
        """Trigger trading pause."""
        logger.warning(f"⏸️ TRADING PAUSED: {reason} (duration: {hours}h)")
        
        self.state = CircuitBreakerState.PAUSED
        self.paused_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        self._save_state()
        
        await self._send_telegram_alert(
            "⏸️ Trading Paused",
            f"**Reason:** {reason}\n"
            f"**Duration:** {hours} hours\n"
            f"**Paused until:** {self.paused_until.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"**Action:** Trading suspended\n\n"
            f"Use `/resume` to restart early."
        )
    
    async def _resume_trading(self, reason: str):
        """Resume trading after pause."""
        logger.info(f"▶️ TRADING RESUMED: {reason}")
        
        self.state = CircuitBreakerState.NORMAL
        self.paused_until = None
        self.consecutive_losses = 0
        self._save_state()
        
        await self._send_telegram_alert(
            "▶️ Trading Resumed",
            f"**Reason:** {reason}\n"
            f"**Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"**Status:** Normal operation"
        )
    
    async def manual_stop(self, reason: str = "Manual stop via command"):
        """Manually trigger emergency stop (from Telegram command)."""
        await self._trigger_emergency(reason)
    
    async def manual_pause(self, hours: int = 24, reason: str = "Manual pause"):
        """Manually pause trading (from Telegram command)."""
        await self._trigger_pause(hours, reason)
    
    async def manual_resume(self, reason: str = "Manual resume"):
        """Manually resume trading (from Telegram command)."""
        if self.emergency_triggered:
            logger.warning("⚠️ Cannot resume from EMERGENCY state without reset")
            return False
        
        await self._resume_trading(reason)
        return True
    
    async def reset_emergency(self):
        """Reset emergency state (admin only)."""
        logger.info("🔄 Resetting emergency state")
        
        self.state = CircuitBreakerState.NORMAL
        self.emergency_triggered = False
        self.paused_until = None
        self.consecutive_losses = 0
        self._save_state()
        
        await self._send_telegram_alert(
            "🔄 Circuit Breaker Reset",
            "Emergency state has been reset.\nTrading can resume."
        )
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        if self.emergency_triggered:
            return False
        
        if self.paused_until and datetime.now(timezone.utc) < self.paused_until:
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            'state': self.state,
            'trading_allowed': self.is_trading_allowed(),
            'emergency_triggered': self.emergency_triggered,
            'paused_until': self.paused_until.isoformat() if self.paused_until else None,
            'consecutive_losses': self.consecutive_losses,
            'daily_start_balance': self.daily_start_balance,
            'thresholds': {
                'daily_loss_limit': self.daily_loss_limit,
                'max_drawdown': self.max_drawdown,
                'max_consecutive_losses': self.max_consecutive_losses
            }
        }
    
    async def _send_telegram_alert(self, title: str, message: str):
        """Send Telegram alert."""
        try:
            from adapters.telegram_client import TelegramClient
            
            # Get Telegram config
            telegram_config = self.policy.get('telegram', {})
            if not telegram_config.get('enabled', False):
                logger.info(f"Telegram disabled, skipping alert: {title}")
                return
            
            # Send message
            telegram = TelegramClient(telegram_config)
            await telegram.send_message(f"**{title}**\n\n{message}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
    
    def _save_state(self):
        """Save circuit breaker state to disk."""
        try:
            state = {
                'state': self.state,
                'emergency_triggered': self.emergency_triggered,
                'paused_until': self.paused_until.isoformat() if self.paused_until else None,
                'consecutive_losses': self.consecutive_losses,
                'daily_start_balance': self.daily_start_balance,
                'daily_start_time': self.daily_start_time.isoformat() if self.daily_start_time else None,
                'last_update': datetime.now(timezone.utc).isoformat()
            }
            
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.debug(f"💾 Circuit breaker state saved")
            
        except Exception as e:
            logger.error(f"❌ Failed to save circuit breaker state: {e}")
    
    def _load_state(self):
        """Load circuit breaker state from disk."""
        try:
            if not self.state_file.exists():
                logger.info("📋 No previous circuit breaker state")
                return
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.state = state.get('state', CircuitBreakerState.NORMAL)
            self.emergency_triggered = state.get('emergency_triggered', False)
            self.consecutive_losses = state.get('consecutive_losses', 0)
            self.daily_start_balance = state.get('daily_start_balance')
            
            # Parse timestamps
            if state.get('paused_until'):
                self.paused_until = datetime.fromisoformat(state['paused_until'].replace('Z', '+00:00'))
            
            if state.get('daily_start_time'):
                self.daily_start_time = datetime.fromisoformat(state['daily_start_time'].replace('Z', '+00:00'))
            
            logger.info(f"✅ Circuit breaker state loaded: {self.state}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load circuit breaker state: {e}")


# Global instance
_circuit_breaker = None


def get_circuit_breaker(policy: Dict[str, Any] = None) -> CircuitBreaker:
    """Get global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        if policy is None:
            from infrastructure.bootstrap import load_policy
            policy = load_policy()
        _circuit_breaker = CircuitBreaker(policy)
    return _circuit_breaker

