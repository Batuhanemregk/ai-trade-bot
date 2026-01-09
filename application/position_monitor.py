"""
Enhanced Position Monitor - Handles position monitoring, PnL updates, and trailing stops.
Follows Single Responsibility Principle by only handling position monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from domain.models import Position, PositionUpdate, PnLUpdate
from application.portfolio_service import PortfolioService
from application.risk_service import RiskService
from application.position_state_manager import PositionStateManager, PositionInfo
from application.reversal_manager import ReversalManager
from adapters.exchange_okx_ccxt import OKXExchangeAdapter


class PositionMonitor:
    """
    Position monitor that tracks active positions and updates PnL.
    
    Responsibilities:
    - Monitor active positions
    - Update position PnL
    - Track position changes
    - Notify about position updates
    """
    
    def __init__(
        self,
        portfolio_service: PortfolioService,
        risk_service: RiskService,
        exchange_adapter: OKXExchangeAdapter,
        config: Dict[str, Any],
        policy: Dict[str, Any]
    ):
        self.portfolio_service = portfolio_service
        self.risk_service = risk_service
        self.exchange_adapter = exchange_adapter
        self.config = config
        self.policy = policy
        
        # Enhanced monitoring state
        self.active_positions = {}
        self.position_history = []
        self.last_pnl_update = {}
        self.monitoring_interval = config.get('position_update_interval', 60)  # 1 minute
        
        # PnL tracking
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.position_count = 0
        
        # Enhanced position tracking
        self.position_metrics = {}  # symbol -> {holding_bars, r_multiple, consecutive_losses}
        self.trailing_stops = {}    # symbol -> {active, stop_price, activation_r}
        
        # Risk thresholds from policy (NO daily loss limits)
        self.max_position_size = policy['trading']['scoring']['risk_management']['max_position_size_pct']
        self.max_position_age_hours = policy['trading']['scoring']['risk_management']['max_position_age_hours']
        self.pnl_alert_threshold = config.get('pnl_alert_threshold', 0.02)  # 2% PnL change
        
        # Initialize enhanced components - USE SINGLETON for consistent state
        from application.position_state_manager import get_state_manager
        self.state_manager = get_state_manager(policy)
        self.reversal_manager = ReversalManager(policy)
        
        logger.info("Enhanced Position Monitor initialized with state management and reversal logic")
    
    async def start_monitoring(self):
        """Start position monitoring loop."""
        logger.info("Starting position monitoring...")
        
        while True:
            try:
                await self._monitor_positions()
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _monitor_positions(self):
        """Main position monitoring logic."""
        try:
            # Get current positions from exchange
            exchange_positions = await self.exchange_adapter.fetch_positions()
            if not exchange_positions:
                return
            
            # Update local position state
            await self._update_position_state(exchange_positions)
            
            # Update PnL for all positions
            await self._update_all_positions_pnl()
            
            # Check for position changes
            await self._check_position_changes()
            
            # Update portfolio state
            await self._update_portfolio_state()
            
            # Check risk limits
            await self._check_risk_limits()
            
        except Exception as e:
            logger.error(f"Position monitoring failed: {e}")
    
    async def _update_position_state(self, exchange_positions: List[Dict[str, Any]]):
        """Update local position state with exchange data."""
        try:
            current_positions = {}
            
            for pos_data in exchange_positions:
                symbol = pos_data.get('symbol')
                if not symbol or not pos_data.get('size'):
                    continue
                
                # Create or update position
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
                
                # Track position history
                if symbol not in self.active_positions:
                    self.position_history.append({
                        "action": "opened",
                        "position": position,
                        "timestamp": datetime.now()
                    })
            
            # Check for closed positions
            closed_positions = set(self.active_positions.keys()) - set(current_positions.keys())
            for symbol in closed_positions:
                old_position = self.active_positions[symbol]
                self.position_history.append({
                    "action": "closed",
                    "position": old_position,
                    "timestamp": datetime.now()
                })
                
                # Calculate realized PnL
                realized_pnl = await self._calculate_realized_pnl(symbol, old_position)
                if realized_pnl:
                    await self._notify_position_closed(symbol, realized_pnl)
            
            # Update active positions
            self.active_positions = current_positions
            self.position_count = len(current_positions)
            
        except Exception as e:
            logger.error(f"Failed to update position state: {e}")
    
    async def _update_all_positions_pnl(self):
        """Update PnL for all active positions with enhanced metrics."""
        try:
            for symbol, position in self.active_positions.items():
                # Get current market price
                current_price = await self.exchange_adapter.get_mark_price(symbol)
                if not current_price:
                    continue
                
                # Update position with current price
                old_pnl = position.unrealized_pnl
                position.current_price = current_price
                
                # Calculate new PnL
                if position.side == 'long':
                    position.unrealized_pnl = (current_price - position.entry_price) * position.size
                else:
                    position.unrealized_pnl = (position.entry_price - current_price) * position.size
                
                # Update enhanced metrics
                await self._update_position_metrics(symbol, position, current_price)
                
                # Check trailing stops
                await self._check_trailing_stops(symbol, position, current_price)
                
                # Check partial take profit levels
                await self._check_partial_tp(symbol, position, current_price)
                
                # Check time-based exit
                await self._check_time_exit(symbol, position)
                
                # Check TP/SL health (orders exist)
                await self._check_tpsl_health(symbol, position)
                
                # Dynamically adjust TP/SL based on volatility changes
                await self._adjust_tpsl_for_volatility(symbol, position, current_price)
                
                # Check if PnL change is significant
                pnl_change = abs(position.unrealized_pnl - old_pnl)
                if pnl_change > (position.entry_price * position.size * self.pnl_alert_threshold):
                    await self._notify_significant_pnl_change(symbol, position, old_pnl)
                
                # Update last PnL update time
                self.last_pnl_update[symbol] = datetime.now()
                
        except Exception as e:
            logger.error(f"Failed to update positions PnL: {e}")
    
    async def _update_position_metrics(self, symbol: str, position: Position, current_price: float):
        """Update enhanced position metrics."""
        try:
            # Initialize metrics if not exists
            if symbol not in self.position_metrics:
                self.position_metrics[symbol] = {
                    'holding_bars': 0,
                    'r_multiple': 0.0,
                    'consecutive_losses': 0,
                    'entry_time': position.timestamp,
                    'last_update': datetime.now()
                }
            
            metrics = self.position_metrics[symbol]
            
            # Update holding bars (15-minute bars)
            time_diff = datetime.now() - metrics['entry_time']
            metrics['holding_bars'] = int(time_diff.total_seconds() / (15 * 60))  # 15 minutes per bar
            
            # Calculate R-multiple
            if position.side == 'long':
                metrics['r_multiple'] = (current_price - position.entry_price) / position.entry_price
            else:
                metrics['r_multiple'] = (position.entry_price - current_price) / position.entry_price
            
            # Update state manager
            self.state_manager.update_position_metrics(
                symbol, current_price, metrics['holding_bars']
            )
            
            metrics['last_update'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to update position metrics for {symbol}: {e}")
    
    async def _check_trailing_stops(self, symbol: str, position: Position, current_price: float):
        """Check and update trailing stops."""
        try:
            # Check if trailing stops are enabled in policy
            trailing_config = self.policy.get('trading', {}).get('scoring', {}).get('trailing', {})
            if not trailing_config.get('enabled', False):
                return
            
            metrics = self.position_metrics.get(symbol, {})
            r_multiple = metrics.get('r_multiple', 0.0)
            
            # Check if trailing should be activated
            should_activate = self.reversal_manager.should_activate_trailing(position.side, r_multiple)
            
            if should_activate and symbol not in self.trailing_stops:
                # Activate trailing stop
                trailing_stop_price = self.reversal_manager.get_trailing_stop_price(
                    position.side, position.entry_price, current_price, r_multiple
                )
                
                self.trailing_stops[symbol] = {
                    'active': True,
                    'stop_price': trailing_stop_price,
                    'activation_r': r_multiple,
                    'last_update': datetime.now()
                }
                
                logger.info(f"[TRAIL] {symbol} trailing stop activated at {trailing_stop_price:.4f} "
                           f"(R={r_multiple:.2f})")
            
            elif symbol in self.trailing_stops:
                # Update existing trailing stop
                trailing = self.trailing_stops[symbol]
                new_stop_price = self.reversal_manager.get_trailing_stop_price(
                    position.side, position.entry_price, current_price, r_multiple
                )
                
                # Only update if new stop is better (closer to current price)
                if position.side == 'long':
                    if new_stop_price > trailing['stop_price']:
                        trailing['stop_price'] = new_stop_price
                        trailing['last_update'] = datetime.now()
                        logger.info(f"[TRAIL] {symbol} trailing stop updated to {new_stop_price:.4f}")
                else:
                    if new_stop_price < trailing['stop_price']:
                        trailing['stop_price'] = new_stop_price
                        trailing['last_update'] = datetime.now()
                        logger.info(f"[TRAIL] {symbol} trailing stop updated to {new_stop_price:.4f}")
                
                # Check if trailing stop is hit
                if self._is_trailing_stop_hit(symbol, position, current_price):
                    await self._execute_trailing_stop_close(symbol, position, current_price)
            
        except Exception as e:
            logger.error(f"Failed to check trailing stops for {symbol}: {e}")
    
    def _is_trailing_stop_hit(self, symbol: str, position: Position, current_price: float) -> bool:
        """Check if trailing stop is hit."""
        if symbol not in self.trailing_stops:
            return False
        
        trailing = self.trailing_stops[symbol]
        stop_price = trailing['stop_price']
        
        if position.side == 'long':
            return current_price <= stop_price
        else:
            return current_price >= stop_price
    
    async def _execute_trailing_stop_close(self, symbol: str, position: Position, current_price: float):
        """Execute trailing stop close."""
        try:
            logger.info(f"[TRAIL] {symbol} trailing stop hit at {current_price:.4f}, closing position")
            
            # Close position via exchange
            success = await self.exchange_adapter.close_position(symbol, position.side, position.size)
            
            if success:
                # Update state manager
                self.state_manager.close_position(symbol, "Trailing Stop")
                
                # Remove from tracking
                if symbol in self.trailing_stops:
                    del self.trailing_stops[symbol]
                if symbol in self.position_metrics:
                    del self.position_metrics[symbol]
                
                # Calculate realized PnL
                realized_pnl = position.unrealized_pnl
                await self._notify_position_closed(symbol, realized_pnl)
                
            else:
                logger.error(f"Failed to close position {symbol} via trailing stop")
                
        except Exception as e:
            logger.error(f"Failed to execute trailing stop close for {symbol}: {e}")
    
    async def check_reversal_opportunity(self, symbol: str, signal: Dict, ohlcv_data: Dict) -> bool:
        """Check if reversal opportunity exists."""
        try:
            if symbol not in self.active_positions:
                return False
            
            position = self.active_positions[symbol]
            metrics = self.position_metrics.get(symbol, {})
            
            # Check reversal eligibility
            reversal_check = self.reversal_manager.check_reversal_eligibility(
                symbol, signal, ohlcv_data, position.side, 
                metrics.get('holding_bars', 0), position.current_price
            )
            
            if reversal_check.is_eligible:
                logger.info(f"[REVCHK] {symbol} reversal eligible: {reversal_check.reason}")
                
                # Create reversal signal
                reversal_signal = self.reversal_manager.create_reversal_signal(
                    symbol, signal, reversal_check, position.side
                )
                
                if reversal_signal.is_valid:
                    await self._execute_reversal(symbol, reversal_signal)
                    return True
            else:
                logger.debug(f"[REVCHK] {symbol} reversal not eligible: {reversal_check.reason}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check reversal opportunity for {symbol}: {e}")
            return False
    
    async def _execute_reversal(self, symbol: str, reversal_signal):
        """Execute position reversal."""
        try:
            logger.info(f"[REVERSE] {symbol} executing {reversal_signal.from_direction} -> "
                       f"{reversal_signal.to_direction} reversal")
            
            # Close current position
            position = self.active_positions[symbol]
            close_success = await self.exchange_adapter.close_position(
                symbol, position.side, position.size
            )
            
            if close_success:
                # Update state manager
                self.state_manager.close_position(symbol, "Reversal")
                
                # Remove from tracking
                if symbol in self.trailing_stops:
                    del self.trailing_stops[symbol]
                if symbol in self.position_metrics:
                    del self.position_metrics[symbol]
                
                # Calculate realized PnL
                realized_pnl = position.unrealized_pnl
                await self._notify_position_closed(symbol, realized_pnl)
                
                logger.info(f"[REVERSE] {symbol} reversal completed, PnL: {realized_pnl:.2f}")
                
            else:
                logger.error(f"Failed to close position {symbol} for reversal")
                
        except Exception as e:
            logger.error(f"Failed to execute reversal for {symbol}: {e}")
    
    def get_enhanced_position_summary(self) -> Dict[str, Any]:
        """Get enhanced summary of current positions."""
        summary = self.get_position_summary()
        
        # Add enhanced metrics
        summary.update({
            "trailing_stops_active": len(self.trailing_stops),
            "position_metrics": {
                symbol: {
                    "holding_bars": metrics.get('holding_bars', 0),
                    "r_multiple": metrics.get('r_multiple', 0.0),
                    "consecutive_losses": metrics.get('consecutive_losses', 0),
                    "position_age_hours": (datetime.now() - metrics.get('entry_time', datetime.now())).total_seconds() / 3600
                }
                for symbol, metrics in self.position_metrics.items()
            },
            "trailing_stops": {
                symbol: {
                    "stop_price": trailing['stop_price'],
                    "activation_r": trailing['activation_r'],
                    "last_update": trailing['last_update']
                }
                for symbol, trailing in self.trailing_stops.items()
            }
        })
        
        return summary
    
    async def _check_position_changes(self):
        """Check for significant position changes."""
        try:
            for symbol, position in self.active_positions.items():
                # Check position size changes
                await self._check_position_size_changes(symbol, position)
                
                # Check margin utilization
                await self._check_margin_utilization(symbol, position)
                
                # Check leverage changes
                await self._check_leverage_changes(symbol, position)
                
        except Exception as e:
            logger.error(f"Failed to check position changes: {e}")
    
    async def _check_position_size_changes(self, symbol: str, position: Position):
        """Check if position size has changed significantly."""
        try:
            # Get portfolio value
            portfolio_value = await self.portfolio_service.get_portfolio_value()
            if not portfolio_value:
                return
            
            # Calculate position size as percentage
            position_value = position.size * position.current_price
            position_percentage = position_value / portfolio_value if portfolio_value > 0 else 0
            
            # Check if position size exceeds limits
            if position_percentage > self.max_position_size:
                await self._notify_position_size_warning(symbol, position, position_percentage)
                
        except Exception as e:
            logger.error(f"Failed to check position size changes: {e}")
    
    async def _check_margin_utilization(self, symbol: str, position: Position):
        """Check margin utilization for position."""
        try:
            # Get account margin info
            margin_info = await self.exchange_adapter.get_margin_info()
            if not margin_info:
                return
            
            # Calculate margin ratio
            total_margin = margin_info.get('totalMargin', 0)
            used_margin = margin_info.get('usedMargin', 0)
            margin_ratio = used_margin / total_margin if total_margin > 0 else 0
            
            # Check if margin utilization is high
            if margin_ratio > 0.8:  # 80% threshold
                await self._notify_high_margin_utilization(symbol, position, margin_ratio)
                
        except Exception as e:
            logger.error(f"Failed to check margin utilization: {e}")
    
    async def _check_leverage_changes(self, symbol: str, position: Position):
        """Check if leverage has changed."""
        try:
            # Get current leverage from exchange
            current_leverage = await self.exchange_adapter.get_position_leverage(symbol)
            if not current_leverage:
                return
            
            # Check if leverage changed
            if abs(current_leverage - position.leverage) > 0.1:  # 10% threshold
                await self._notify_leverage_change(symbol, position, current_leverage)
                position.leverage = current_leverage
                
        except Exception as e:
            logger.error(f"Failed to check leverage changes: {e}")
    
    async def _update_portfolio_state(self):
        """Update portfolio state with current position information."""
        try:
            # Calculate total PnL
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.active_positions.values())
            
            # Update portfolio service
            await self.portfolio_service.update_portfolio_state({
                "total_positions": self.position_count,
                "total_unrealized_pnl": total_unrealized_pnl,
                "active_symbols": list(self.active_positions.keys()),
                "last_update": datetime.now()
            })
            
            # Update risk service
            await self.risk_service.update_portfolio_risk({
                "position_count": self.position_count,
                "total_exposure": sum(pos.size * pos.current_price for pos in self.active_positions.values()),
                "max_position_size": max((pos.size * pos.current_price for pos in self.active_positions.values()), default=0)
            })
            
        except Exception as e:
            logger.error(f"Failed to update portfolio state: {e}")
    
    async def _check_risk_limits(self):
        """Check if any risk limits are exceeded."""
        try:
            # Check daily loss limit
            if self.daily_pnl < -(self.config.get('max_daily_loss', 0.05)):
                await self._notify_daily_loss_limit_exceeded()
            
            # Check total position count
            if self.position_count > self.config.get('max_active_positions', 10):
                await self._notify_max_positions_exceeded()
                
        except Exception as e:
            logger.error(f"Failed to check risk limits: {e}")
    
    async def _calculate_realized_pnl(self, symbol: str, position: Position) -> Optional[float]:
        """Calculate realized PnL for closed position."""
        try:
            # Get trade history for symbol
            trades = await self.exchange_adapter.fetch_trades(symbol)
            if not trades:
                return None
            
            # Find closing trades
            closing_trades = [t for t in trades if t.get('side') != position.side]
            if not closing_trades:
                return None
            
            # Calculate realized PnL
            realized_pnl = sum(float(t.get('amount', 0)) * (float(t.get('price', 0)) - position.entry_price) 
                              for t in closing_trades)
            
            return realized_pnl if position.side == 'long' else -realized_pnl
            
        except Exception as e:
            logger.error(f"Failed to calculate realized PnL for {symbol}: {e}")
            return None
    
    async def _notify_position_closed(self, symbol: str, realized_pnl: float, 
                                       direction: str = None, entry_price: float = 0):
        """Notify about position closure and record to trade history."""
        try:
            logger.info(f"Position closed for {symbol}: Realized PnL: {realized_pnl:.2f}")
            
            # Update portfolio PnL
            self.total_pnl += realized_pnl
            self.daily_pnl += realized_pnl
            
            # Record to TradeHistory for per-symbol streak tracking
            try:
                from application.trade_history import get_trade_history
                trade_history = get_trade_history()
                result = trade_history.record_trade(
                    symbol=symbol,
                    direction=direction or 'unknown',
                    pnl=realized_pnl,
                    entry_price=entry_price
                )
                
                # Log streak status
                if result['new_streak'] >= 2:
                    logger.warning(f"⚠️ [{symbol}] Streak: {result['new_streak']} ardışık kayıp!")
                    
            except Exception as e:
                logger.warning(f"Failed to record trade to history: {e}")
            
            # Notify risk service
            await self.risk_service.on_position_closed(symbol, realized_pnl)
            
        except Exception as e:
            logger.error(f"Failed to notify position closure: {e}")
    
    async def _notify_significant_pnl_change(self, symbol: str, position: Position, old_pnl: float):
        """Notify about significant PnL change."""
        try:
            pnl_change = position.unrealized_pnl - old_pnl
            logger.info(f"Significant PnL change for {symbol}: {pnl_change:.2f}")
            
            # Notify risk service
            await self.risk_service.on_pnl_change(symbol, pnl_change)
            
        except Exception as e:
            logger.error(f"Failed to notify PnL change: {e}")
    
    async def _notify_position_size_warning(self, symbol: str, position: Position, percentage: float):
        """Notify about position size warning."""
        try:
            logger.warning(f"Position size warning for {symbol}: {percentage:.2%} of portfolio")
            
            # Notify risk service
            await self.risk_service.on_position_size_warning(symbol, percentage)
            
        except Exception as e:
            logger.error(f"Failed to notify position size warning: {e}")
    
    async def _notify_high_margin_utilization(self, symbol: str, position: Position, margin_ratio: float):
        """Notify about high margin utilization."""
        try:
            logger.warning(f"High margin utilization for {symbol}: {margin_ratio:.2%}")
            
            # Notify risk service
            await self.risk_service.on_high_margin_utilization(symbol, margin_ratio)
            
        except Exception as e:
            logger.error(f"Failed to notify margin utilization: {e}")
    
    async def _notify_leverage_change(self, symbol: str, position: Position, new_leverage: float):
        """Notify about leverage change."""
        try:
            logger.info(f"Leverage changed for {symbol}: {position.leverage} -> {new_leverage}")
            
            # Notify risk service
            await self.risk_service.on_leverage_change(symbol, new_leverage)
            
        except Exception as e:
            logger.error(f"Failed to notify leverage change: {e}")
    
    async def _notify_daily_loss_limit_exceeded(self):
        """Notify about daily loss limit exceeded."""
        try:
            logger.error(f"Daily loss limit exceeded: {self.daily_pnl:.2f}")
            
            # Notify risk service
            await self.risk_service.on_daily_loss_limit_exceeded(self.daily_pnl)
            
        except Exception as e:
            logger.error(f"Failed to notify daily loss limit: {e}")
    
    async def _notify_max_positions_exceeded(self):
        """Notify about max positions exceeded."""
        try:
            logger.warning(f"Max positions exceeded: {self.position_count}")
            
            # Notify risk service
            await self.risk_service.on_max_positions_exceeded(self.position_count)
            
        except Exception as e:
            logger.error(f"Failed to notify max positions: {e}")
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of current positions."""
        return {
            "total_positions": self.position_count,
            "active_symbols": list(self.active_positions.keys()),
            "total_unrealized_pnl": sum(pos.unrealized_pnl for pos in self.active_positions.values()),
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "last_update": max(self.last_pnl_update.values()) if self.last_pnl_update else None,
            "monitoring_interval": self.monitoring_interval
        }
    
    def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific position."""
        position = self.active_positions.get(symbol)
        if not position:
            return None
        
        return {
            "symbol": symbol,
            "side": position.side,
            "size": position.size,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "unrealized_pnl": position.unrealized_pnl,
            "margin": position.margin,
            "leverage": position.leverage,
            "timestamp": position.timestamp,
            "last_pnl_update": self.last_pnl_update.get(symbol)
        }
    
    async def get_active_positions(self) -> List[Dict[str, Any]]:
        """Get list of all active positions."""
        try:
            positions = []
            for symbol, position in self.active_positions.items():
                position_info = {
                    "symbol": symbol,
                    "side": position.side,
                    "size": position.size,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "margin": position.margin,
                    "leverage": position.leverage,
                    "timestamp": position.timestamp
                }
                positions.append(position_info)
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Failed to get active positions: {e}")
            return []
    
    async def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position information for a specific symbol."""
        return self.get_position_details(symbol)
    
    # ==================== PARTIAL TAKE PROFIT ====================
    
    async def _check_partial_tp(self, symbol: str, position: Position, current_price: float):
        """Check and execute partial take profit levels."""
        try:
            partial_tp_config = self.policy.get('trading', {}).get('scoring', {}).get('partial_tp', {})
            if not partial_tp_config.get('enabled', False):
                return
            
            metrics = self.position_metrics.get(symbol, {})
            r_multiple = metrics.get('r_multiple', 0.0)
            
            # Track filled levels per symbol
            if symbol not in hasattr(self, '_partial_tp_filled'):
                self._partial_tp_filled = {}
            if symbol not in self._partial_tp_filled:
                self._partial_tp_filled[symbol] = set()
            
            filled_levels = self._partial_tp_filled[symbol]
            levels = partial_tp_config.get('levels', [])
            
            for level in levels:
                level_r = level.get('r_multiple', 0)
                close_pct = level.get('close_pct', 0)
                
                # Skip if already filled this level
                if level_r in filled_levels:
                    continue
                
                # Check if R-multiple reached this level
                if r_multiple >= level_r:
                    logger.info(f"[PARTIAL-TP] {symbol}: R={r_multiple:.2f} reached level {level_r}R, closing {close_pct*100:.0f}%")
                    
                    # Calculate amount to close
                    close_amount = position.size * close_pct
                    
                    # Execute partial close
                    await self._execute_partial_close(symbol, position, close_amount, level_r)
                    
                    # Mark level as filled
                    filled_levels.add(level_r)
                    
        except Exception as e:
            logger.error(f"Failed to check partial TP for {symbol}: {e}")
    
    async def _execute_partial_close(self, symbol: str, position: Position, close_amount: float, level_r: float):
        """Execute partial position close."""
        try:
            close_side = 'buy' if position.side == 'short' else 'sell'
            
            logger.info(f"[PARTIAL-TP] Executing: {symbol} close {close_amount:.4f} at {level_r}R")
            
            result = await self.exchange_adapter.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=close_amount,
                params={'reduceOnly': True}
            )
            
            logger.info(f"✅ [PARTIAL-TP] {symbol}: Closed {close_amount:.4f} at {level_r}R (order: {result.get('id', 'N/A')})")
            
        except Exception as e:
            logger.error(f"❌ [PARTIAL-TP] Failed to execute partial close for {symbol}: {e}")
    
    # ==================== TIME-BASED EXIT ====================
    
    async def _check_time_exit(self, symbol: str, position: Position):
        """Check if position should be closed due to age."""
        try:
            time_exit_config = self.policy.get('trading', {}).get('scoring', {}).get('time_exit', {})
            if not time_exit_config.get('enabled', False):
                return
            
            max_age_hours = time_exit_config.get('max_position_age_hours', 24)
            warning_hours = time_exit_config.get('warning_hours', 20)
            action = time_exit_config.get('stale_position_action', 'close')
            
            # Calculate position age
            if hasattr(position, 'timestamp') and position.timestamp:
                position_age = datetime.now() - position.timestamp
                age_hours = position_age.total_seconds() / 3600
            else:
                return  # Can't determine age
            
            # Check warning threshold
            if age_hours >= warning_hours and age_hours < max_age_hours:
                if not hasattr(self, '_time_exit_warned'):
                    self._time_exit_warned = set()
                if symbol not in self._time_exit_warned:
                    logger.warning(f"⚠️ [TIME-EXIT] {symbol}: Position age {age_hours:.1f}h, will close at {max_age_hours}h")
                    self._time_exit_warned.add(symbol)
            
            # Check exit threshold
            if age_hours >= max_age_hours:
                logger.info(f"🕐 [TIME-EXIT] {symbol}: Position age {age_hours:.1f}h >= {max_age_hours}h, action={action}")
                
                if action == 'close':
                    await self._execute_time_exit(symbol, position)
                elif action == 'reduce':
                    # Close 50% of position
                    await self._execute_partial_close(symbol, position, position.size * 0.5, 0)
                elif action == 'alert':
                    logger.warning(f"🔔 [TIME-EXIT] ALERT: {symbol} stale position ({age_hours:.1f}h)")
                    
        except Exception as e:
            logger.error(f"Failed to check time exit for {symbol}: {e}")
    
    async def _execute_time_exit(self, symbol: str, position: Position):
        """Execute time-based position close."""
        try:
            close_side = 'buy' if position.side == 'short' else 'sell'
            
            logger.info(f"🕐 [TIME-EXIT] Closing stale position: {symbol} {position.size}")
            
            result = await self.exchange_adapter.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=position.size,
                params={'reduceOnly': True}
            )
            
            logger.info(f"✅ [TIME-EXIT] {symbol}: Position closed (order: {result.get('id', 'N/A')})")
            
            # Clean up warning set
            if hasattr(self, '_time_exit_warned') and symbol in self._time_exit_warned:
                self._time_exit_warned.remove(symbol)
                
        except Exception as e:
            logger.error(f"❌ [TIME-EXIT] Failed to close stale position {symbol}: {e}")
    
    # ==================== TP/SL HEALTH CHECK ====================
    
    async def _check_tpsl_health(self, symbol: str, position: Position):
        """Check if TP and SL orders exist for position, recreate if missing."""
        try:
            # Get open orders for this symbol
            if hasattr(self.exchange_adapter, 'fetch_open_orders'):
                orders = await self.exchange_adapter.fetch_open_orders(symbol)
            else:
                orders = await self.exchange_adapter.ccxt_client.fetch_open_orders(symbol)
            
            # Check for TP and SL orders
            has_tp = any(o.get('type', '').lower() in ['take_profit', 'limit'] or 'tp' in o.get('clientOrderId', '').lower() for o in orders)
            has_sl = any(o.get('type', '').lower() in ['stop_loss', 'stop'] or 'sl' in o.get('clientOrderId', '').lower() for o in orders)
            
            if not has_tp or not has_sl:
                logger.warning(f"⚠️ [HEALTH] {symbol}: Missing TP={not has_tp}, SL={not has_sl}")
                
                # Recreate missing orders using ATR-based calculation
                await self._recreate_missing_tpsl(symbol, position, has_tp, has_sl)
                
        except Exception as e:
            logger.error(f"Failed to check TP/SL health for {symbol}: {e}")
    
    async def _recreate_missing_tpsl(self, symbol: str, position: Position, has_tp: bool, has_sl: bool):
        """Recreate missing TP or SL orders."""
        try:
            entry_price = position.entry_price
            current_price = position.current_price
            
            # Calculate ATR-based levels (fallback to 3% TP, 1.5% SL)
            if position.side == 'long':
                tp_price = entry_price * 1.03  # 3% profit
                sl_price = entry_price * 0.985  # 1.5% loss
            else:  # short
                tp_price = entry_price * 0.97  # 3% profit
                sl_price = entry_price * 1.015  # 1.5% loss
            
            close_side = 'buy' if position.side == 'short' else 'sell'
            
            if not has_tp:
                logger.info(f"🔧 [HEALTH] Recreating TP order for {symbol} at {tp_price}")
                try:
                    await self.exchange_adapter.create_order(
                        symbol=symbol,
                        order_type='limit',
                        side=close_side,
                        amount=position.size,
                        price=tp_price,
                        params={'reduceOnly': True}
                    )
                except Exception as e:
                    logger.error(f"Failed to recreate TP: {e}")
            
            if not has_sl:
                logger.info(f"🔧 [HEALTH] Recreating SL order for {symbol} at {sl_price}")
                try:
                    # Use trigger order for stop loss
                    await self.exchange_adapter.create_order(
                        symbol=symbol,
                        order_type='stop',
                        side=close_side,
                        amount=position.size,
                        price=sl_price,
                        params={'reduceOnly': True, 'stopPrice': sl_price}
                    )
                except Exception as e:
                    logger.error(f"Failed to recreate SL: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to recreate TP/SL for {symbol}: {e}")
    
    # ==================== OCO CLEANUP (ORPHAN ORDERS) ====================
    
    async def cleanup_orphan_orders(self):
        """Cancel orders that don't have corresponding positions (orphan orders)."""
        try:
            logger.info("🧹 [OCO-CLEANUP] Checking for orphan orders...")
            
            # Get all open orders
            if hasattr(self.exchange_adapter, 'fetch_open_orders'):
                all_orders = await self.exchange_adapter.fetch_open_orders()
            else:
                all_orders = await self.exchange_adapter.ccxt_client.fetch_open_orders()
            
            # Get all open positions
            if hasattr(self.exchange_adapter, 'fetch_positions'):
                positions = await self.exchange_adapter.fetch_positions()
            else:
                positions = await self.exchange_adapter.ccxt_client.fetch_positions()
            
            # Get symbols with real positions
            position_symbols = set()
            for pos in positions:
                contracts = float(pos.get('contracts', 0) or pos.get('info', {}).get('pos', 0) or 0)
                if contracts != 0:
                    pos_symbol = pos.get('symbol', '') or pos.get('info', {}).get('instId', '')
                    # Normalize symbol
                    pos_symbol_normalized = pos_symbol.replace('/', '-').replace(':USDT', '-SWAP').replace(':USD', '-SWAP')
                    position_symbols.add(pos_symbol_normalized)
                    position_symbols.add(pos_symbol)
            
            # Find and cancel orphan orders
            cancelled = 0
            for order in all_orders:
                order_symbol = order.get('symbol', '') or order.get('info', {}).get('instId', '')
                order_symbol_normalized = order_symbol.replace('/', '-').replace(':USDT', '-SWAP').replace(':USD', '-SWAP')
                
                # Check if order has no corresponding position
                if order_symbol not in position_symbols and order_symbol_normalized not in position_symbols:
                    order_id = order.get('id', order.get('info', {}).get('ordId', ''))
                    logger.info(f"🧹 [OCO-CLEANUP] Cancelling orphan order: {order_symbol} ID={order_id}")
                    
                    try:
                        await self.exchange_adapter.cancel_order(order_id, order_symbol)
                        cancelled += 1
                    except Exception as e:
                        logger.warning(f"Failed to cancel orphan order {order_id}: {e}")
            
            if cancelled > 0:
                logger.info(f"✅ [OCO-CLEANUP] Cancelled {cancelled} orphan orders")
            else:
                logger.debug("[OCO-CLEANUP] No orphan orders found")
                
        except Exception as e:
            logger.error(f"Failed to cleanup orphan orders: {e}")
    
    # ==================== DYNAMIC TP/SL ADJUSTMENT ====================
    
    async def _adjust_tpsl_for_volatility(self, symbol: str, position: Position, current_price: float):
        """Adjust TP/SL levels based on current volatility changes."""
        try:
            # Features are directly under trading, not trading.scoring
            dynamic_tpsl_config = self.policy.get('trading', {}).get('dynamic_tpsl', {})
            if not dynamic_tpsl_config.get('enabled', False):
                return
            
            # Track volatility changes
            if not hasattr(self, '_last_volatility'):
                self._last_volatility = {}
            
            # Get current ATR/volatility from exchange
            try:
                ticker = await self.exchange_adapter.fetch_ticker(symbol)
                current_volatility = abs(ticker.get('percentage', 0)) / 100  # Daily % change
            except:
                return
            
            last_vol = self._last_volatility.get(symbol, current_volatility)
            vol_change = abs(current_volatility - last_vol) / (last_vol + 0.0001)
            
            # If volatility changed significantly (>20%), adjust TP/SL
            if vol_change > 0.20:
                logger.info(f"📊 [DYNAMIC-TPSL] {symbol}: Volatility changed {vol_change:.1%}, considering TP/SL adjustment")
                
                # Update volatility tracking
                self._last_volatility[symbol] = current_volatility
                
                # For now, log the recommendation (actual adjustment requires order modification)
                if current_volatility > last_vol:
                    logger.info(f"💡 [DYNAMIC-TPSL] {symbol}: Volatility UP - consider widening TP/SL")
                else:
                    logger.info(f"💡 [DYNAMIC-TPSL] {symbol}: Volatility DOWN - consider tightening TP/SL")
                    
        except Exception as e:
            logger.error(f"Failed to adjust TP/SL for volatility: {e}")


