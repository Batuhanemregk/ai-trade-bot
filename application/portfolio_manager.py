"""
Portfolio Manager - Handles portfolio tracking and management.
Follows Single Responsibility Principle by only handling portfolio operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from domain.models import Position, PortfolioState, Balance, PnLUpdate
from application.portfolio_service import PortfolioService
from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from telegram_bot.bot import TelegramBot


class PortfolioManager:
    """
    Portfolio manager that tracks positions, balances, and performance.
    
    Responsibilities:
    - Track portfolio positions and balances
    - Calculate PnL and performance metrics
    - Manage portfolio state persistence
    - Generate portfolio reports
    """
    
    def __init__(
        self,
        portfolio_service: PortfolioService,
        exchange_adapter: OKXExchangeAdapter,
        telegram_bot: TelegramBot,
        config: Dict[str, Any]
    ):
        self.portfolio_service = portfolio_service
        self.exchange_adapter = exchange_adapter
        self.telegram_bot = telegram_bot
        self.config = config
        
        # Portfolio state
        self.portfolio_state = PortfolioState()
        self.positions = {}
        self.balances = {}
        self.performance_history = []
        
        # Update intervals
        self.position_update_interval = config.get('trading', {}).get('position_update_interval', 60)
        self.balance_update_interval = 300  # 5 minutes
        self.performance_update_interval = 3600  # 1 hour
        
        # Performance tracking
        self.start_date = datetime.now()
        self.initial_balance = 0.0
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.daily_pnl = 0.0
        
        # State persistence
        self.last_save = datetime.now()
        self.save_interval = 300  # 5 minutes
        
        logger.info("Portfolio Manager initialized")
    
    async def start_monitoring(self):
        """Start portfolio monitoring loop."""
        logger.info("Starting portfolio monitoring...")
        
        while True:
            try:
                await self._update_portfolio_state()
                await asyncio.sleep(self.position_update_interval)
                
            except Exception as e:
                logger.error(f"Portfolio monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _update_portfolio_state(self):
        """Update portfolio state from exchange."""
        try:
            # Update positions
            await self._update_positions()
            
            # Update balances
            await self._update_balances()
            
            # Update performance metrics
            await self._update_performance_metrics()
            
            # Save state if needed
            await self._save_portfolio_state()
            
            # Update portfolio service
            await self._sync_with_portfolio_service()
            
        except Exception as e:
            logger.error(f"Portfolio state update failed: {e}")
    
    async def _update_positions(self):
        """Update position information from exchange."""
        try:
            # Get positions from exchange
            exchange_positions = await self.exchange_adapter.fetch_positions()
            if not exchange_positions:
                return
            
            # Process each position
            current_positions = {}
            total_unrealized_pnl = 0.0
            
            for pos_data in exchange_positions:
                symbol = pos_data.get('symbol')
                if not symbol or not pos_data.get('size'):
                    continue
                
                # Create position object
                position = Position(
                    symbol=symbol,
                    side=pos_data.get('side', 'long'),
                    size=float(pos_data.get('size', 0)),
                    entry_price=float(pos_data.get('avgPrice', 0)),
                    current_price=float(pos_data.get('markPrice', 0)),
                    unrealized_pnl=float(pos_data.get('unrealizedPnl', 0)),
                    margin=float(pos_data.get('margin', 0)),
                    leverage=float(pos_data.get('leverage', 1)),
                    timestamp=datetime.now()
                )
                
                current_positions[symbol] = position
                total_unrealized_pnl += position.unrealized_pnl
            
            # Update positions
            self.positions = current_positions
            self.total_unrealized_pnl = total_unrealized_pnl
            
            # Check for position changes
            await self._check_position_changes()
            
            logger.debug(f"Updated {len(current_positions)} positions")
            
        except Exception as e:
            logger.error(f"Position update failed: {e}")
    
    async def _update_balances(self):
        """Update balance information from exchange."""
        try:
            # Get account balance
            account_balance = await self.exchange_adapter.get_account_balance()
            if not account_balance:
                return
            
            # Process balances
            current_balances = {}
            total_balance_usd = 0.0
            
            for balance_data in account_balance:
                currency = balance_data.get('currency')
                if not currency:
                    continue
                
                balance = Balance(
                    currency=currency,
                    available=float(balance_data.get('available', 0)),
                    total=float(balance_data.get('total', 0)),
                    frozen=float(balance_data.get('frozen', 0)),
                    timestamp=datetime.now()
                )
                
                current_balances[currency] = balance
                
                # Convert to USD if possible
                if currency == 'USDT':
                    total_balance_usd += balance.total
                elif currency in ['BTC', 'ETH']:
                    # Simple conversion (in real system, use current rates)
                    if currency == 'BTC':
                        total_balance_usd += balance.total * 50000  # Approximate
                    elif currency == 'ETH':
                        total_balance_usd += balance.total * 3000  # Approximate
            
            # Update balances
            self.balances = current_balances
            
            # Update portfolio state
            if self.initial_balance == 0:
                self.initial_balance = total_balance_usd
            
            self.portfolio_state.total_balance = total_balance_usd
            self.portfolio_state.available_balance = total_balance_usd - self.total_unrealized_pnl
            
            logger.debug(f"Updated balances for {len(current_balances)} currencies")
            
        except Exception as e:
            logger.error(f"Balance update failed: {e}")
    
    async def _update_performance_metrics(self):
        """Update performance metrics."""
        try:
            # Calculate total PnL
            total_pnl = self.total_realized_pnl + self.total_unrealized_pnl
            
            # Calculate daily PnL
            today = datetime.now().date()
            today_pnl = 0.0
            
            # Get today's realized PnL from history
            for entry in self.performance_history:
                if entry.get('date') == today:
                    today_pnl += entry.get('realized_pnl', 0)
            
            today_pnl += self.total_unrealized_pnl
            self.daily_pnl = today_pnl
            
            # Calculate performance metrics
            if self.initial_balance > 0:
                total_return = total_pnl / self.initial_balance
                daily_return = today_pnl / self.initial_balance
            else:
                total_return = 0.0
                daily_return = 0.0
            
            # Update portfolio state
            self.portfolio_state.total_pnl = total_pnl
            self.portfolio_state.daily_pnl = today_pnl
            self.portfolio_state.total_return = total_return
            self.portfolio_state.daily_return = daily_return
            self.portfolio_state.position_count = len(self.positions)
            self.portfolio_state.last_update = datetime.now()
            
            # Calculate exposure
            total_exposure = sum(pos.size * pos.current_price for pos in self.positions.values())
            self.portfolio_state.total_exposure = total_exposure
            
            if self.portfolio_state.total_balance > 0:
                self.portfolio_state.exposure_ratio = total_exposure / self.portfolio_state.total_balance
            else:
                self.portfolio_state.exposure_ratio = 0.0
            
            logger.debug(f"Updated performance metrics: Total PnL: ${total_pnl:.2f}, Daily: ${today_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Performance metrics update failed: {e}")
    
    async def _check_position_changes(self):
        """Check for significant position changes."""
        try:
            for symbol, position in self.positions.items():
                # Check for significant PnL changes
                await self._check_pnl_changes(symbol, position)
                
                # Check for position size changes
                await self._check_position_size_changes(symbol, position)
                
        except Exception as e:
            logger.error(f"Position change check failed: {e}")
    
    async def _check_pnl_changes(self, symbol: str, position: Position):
        """Check for significant PnL changes."""
        try:
            # Get previous PnL from portfolio service
            previous_pnl = await self.portfolio_service.get_position_pnl(symbol)
            if previous_pnl is None:
                return
            
            pnl_change = position.unrealized_pnl - previous_pnl
            pnl_change_percent = abs(pnl_change) / abs(previous_pnl) if previous_pnl != 0 else 0
            
            # Alert if PnL change is significant (>5%)
            if pnl_change_percent > 0.05:
                await self._send_pnl_alert(symbol, position, pnl_change, pnl_change_percent)
                
        except Exception as e:
            logger.error(f"PnL change check failed for {symbol}: {e}")
    
    async def _check_position_size_changes(self, symbol: str, position: Position):
        """Check for position size changes."""
        try:
            # Get previous position size from portfolio service
            previous_size = await self.portfolio_service.get_position_size(symbol)
            if previous_size is None:
                return
            
            size_change = abs(position.size - previous_size)
            size_change_percent = size_change / previous_size if previous_size > 0 else 0
            
            # Alert if size change is significant (>10%)
            if size_change_percent > 0.10:
                await self._send_position_size_alert(symbol, position, size_change, size_change_percent)
                
        except Exception as e:
            logger.error(f"Position size change check failed for {symbol}: {e}")
    
    async def _send_pnl_alert(self, symbol: str, position: Position, pnl_change: float, change_percent: float):
        """Send PnL change alert."""
        try:
            alert_message = (
                f"📊 PnL ALERT: {symbol}\n"
                f"Side: {position.side.upper()}\n"
                f"Size: {position.size:.4f}\n"
                f"Current PnL: ${position.unrealized_pnl:.2f}\n"
                f"Change: ${pnl_change:.2f} ({change_percent:.1%})\n"
                f"Entry Price: ${position.entry_price:.2f}\n"
                f"Current Price: ${position.current_price:.2f}"
            )
            
            await self.telegram_bot.send_notification(
                "PnL Change Alert",
                alert_message,
                "info"
            )
            
        except Exception as e:
            logger.error(f"Failed to send PnL alert: {e}")
    
    async def _send_position_size_alert(self, symbol: str, position: Position, size_change: float, change_percent: float):
        """Send position size change alert."""
        try:
            alert_message = (
                f"📏 POSITION SIZE ALERT: {symbol}\n"
                f"Previous Size: {position.size - size_change:.4f}\n"
                f"New Size: {position.size:.4f}\n"
                f"Change: {size_change:.4f} ({change_percent:.1%})\n"
                f"Current Price: ${position.current_price:.2f}\n"
                f"Position Value: ${position.size * position.current_price:.2f}"
            )
            
            await self.telegram_bot.send_notification(
                "Position Size Alert",
                alert_message,
                "warning"
            )
            
        except Exception as e:
            logger.error(f"Failed to send position size alert: {e}")
    
    async def _save_portfolio_state(self):
        """Save portfolio state to persistent storage."""
        try:
            now = datetime.now()
            if (now - self.last_save).total_seconds() < self.save_interval:
                return
            
            # Save to portfolio service
            await self.portfolio_service.save_portfolio_state(self.portfolio_state)
            
            # Save performance history
            performance_entry = {
                'date': now.date(),
                'total_balance': self.portfolio_state.total_balance,
                'total_pnl': self.portfolio_state.total_pnl,
                'daily_pnl': self.portfolio_state.daily_pnl,
                'position_count': self.portfolio_state.position_count,
                'exposure_ratio': self.portfolio_state.exposure_ratio,
                'timestamp': now
            }
            
            self.performance_history.append(performance_entry)
            
            # Keep only last 30 days
            if len(self.performance_history) > 30:
                self.performance_history = self.performance_history[-30:]
            
            self.last_save = now
            logger.debug("Portfolio state saved")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")
    
    async def _sync_with_portfolio_service(self):
        """Sync local state with portfolio service."""
        try:
            # Update portfolio service with current state
            await self.portfolio_service.update_portfolio_state({
                "total_balance": self.portfolio_state.total_balance,
                "available_balance": self.portfolio_state.available_balance,
                "total_pnl": self.portfolio_state.total_pnl,
                "daily_pnl": self.portfolio_state.daily_pnl,
                "total_return": self.portfolio_state.total_return,
                "daily_return": self.portfolio_state.daily_return,
                "position_count": self.portfolio_state.position_count,
                "total_exposure": self.portfolio_state.total_exposure,
                "exposure_ratio": self.portfolio_state.exposure_ratio,
                "last_update": self.portfolio_state.last_update
            })
            
            # Update positions in portfolio service
            for symbol, position in self.positions.items():
                await self.portfolio_service.update_position(symbol, position)
                
        except Exception as e:
            logger.error(f"Failed to sync with portfolio service: {e}")
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        try:
            return {
                "overview": {
                    "total_balance": self.portfolio_state.total_balance,
                    "available_balance": self.portfolio_state.available_balance,
                    "total_pnl": self.portfolio_state.total_pnl,
                    "daily_pnl": self.portfolio_state.daily_pnl,
                    "total_return": self.portfolio_state.total_return,
                    "daily_return": self.portfolio_state.daily_return
                },
                "positions": {
                    "count": len(self.positions),
                    "total_exposure": self.portfolio_state.total_exposure,
                    "exposure_ratio": self.portfolio_state.exposure_ratio,
                    "symbols": list(self.positions.keys())
                },
                "balances": {
                    "currencies": len(self.balances),
                    "total_currencies": list(self.balances.keys())
                },
                "performance": {
                    "start_date": self.start_date,
                    "initial_balance": self.initial_balance,
                    "total_realized_pnl": self.total_realized_pnl,
                    "total_unrealized_pnl": self.total_unrealized_pnl,
                    "history_days": len(self.performance_history)
                },
                "last_update": self.portfolio_state.last_update
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {e}")
            return {"error": str(e)}
    
    async def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific position."""
        try:
            position = self.positions.get(symbol)
            if not position:
                return None
            
            # Calculate additional metrics
            position_value = position.size * position.current_price
            pnl_percent = (position.unrealized_pnl / position_value) * 100 if position_value > 0 else 0
            
            return {
                "symbol": symbol,
                "side": position.side,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "pnl_percent": pnl_percent,
                "position_value": position_value,
                "margin": position.margin,
                "leverage": position.leverage,
                "timestamp": position.timestamp,
                "duration": (datetime.now() - position.timestamp).total_seconds() / 3600  # hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get position details for {symbol}: {e}")
            return None
    
    async def close_position(self, symbol: str, reason: str = "manual") -> bool:
        """Close a specific position."""
        try:
            position = self.positions.get(symbol)
            if not position:
                logger.warning(f"No position found for {symbol}")
                return False
            
            # Close position through exchange
            success = await self.exchange_adapter.close_position(symbol)
            if success:
                # Calculate realized PnL
                realized_pnl = position.unrealized_pnl
                self.total_realized_pnl += realized_pnl
                
                # Remove from positions
                del self.positions[symbol]
                
                # Update portfolio state
                self.portfolio_state.position_count = len(self.positions)
                
                # Send notification
                await self._send_position_closed_alert(symbol, position, realized_pnl, reason)
                
                logger.info(f"Position closed for {symbol}: Realized PnL: ${realized_pnl:.2f}")
                return True
            else:
                logger.error(f"Failed to close position for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to close position for {symbol}: {e}")
            return False
    
    async def _send_position_closed_alert(self, symbol: str, position: Position, realized_pnl: float, reason: str):
        """Send position closed alert."""
        try:
            alert_message = (
                f"🔒 POSITION CLOSED: {symbol}\n"
                f"Reason: {reason}\n"
                f"Side: {position.side.upper()}\n"
                f"Size: {position.size:.4f}\n"
                f"Entry Price: ${position.entry_price:.2f}\n"
                f"Exit Price: ${position.current_price:.2f}\n"
                f"Realized PnL: ${realized_pnl:.2f}"
            )
            
            await self.telegram_bot.send_notification(
                "Position Closed",
                alert_message,
                "info"
            )
            
        except Exception as e:
            logger.error(f"Failed to send position closed alert: {e}")
    
    def get_performance_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get performance history for specified number of days."""
        try:
            if days <= 0:
                return []
            
            # Return last N days of performance
            return self.performance_history[-days:]
            
        except Exception as e:
            logger.error(f"Failed to get performance history: {e}")
            return []
    
    async def reset_daily_metrics(self):
        """Reset daily metrics."""
        try:
            self.daily_pnl = 0.0
            self.portfolio_state.daily_pnl = 0.0
            self.portfolio_state.daily_return = 0.0
            
            logger.info("Daily metrics reset")
            
        except Exception as e:
            logger.error(f"Failed to reset daily metrics: {e}")
