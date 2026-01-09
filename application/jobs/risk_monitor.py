"""
Risk Monitor Job (1m)
Handles position monitoring, SL/TP checks, and API health every minute
NO daily loss limits or consecutive loss tracking
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger

from .base_job import BaseJob


class RiskMonitorJob(BaseJob):
    """1-minute risk monitoring job for position safety."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.circuit_breaker = None
        self.api_health_status = {}
        
    async def initialize(self):
        """Initialize risk monitoring components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            # Initialize circuit breaker
            from application.circuit_breaker import CircuitBreaker
            self.circuit_breaker = CircuitBreaker(self.policy)
            
            logger.info("✅ RiskMonitorJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RiskMonitorJob: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup risk monitor resources"""
        try:
            if hasattr(self, 'exchange_adapter') and self.exchange_adapter:
                await self.exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter for RiskMonitorJob")
        except Exception as e:
            logger.error(f"❌ RiskMonitorJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute 1-minute risk monitoring."""
        try:
            logger.info("[JOB] risk_monitor starting execution")
            
            # Check API health
            await self._check_api_health()
            
            # Check active positions
            await self._check_active_positions()
            
            # Check system health
            await self._check_system_health()
            
            # Check circuit breaker conditions
            if self.circuit_breaker:
                await self._check_circuit_breaker()
            
            logger.info("[JOB] risk_monitor completed successfully")
            
        except Exception as e:
            logger.error(f"❌ RiskMonitorJob execution failed: {e}")
            raise
    
    async def _check_api_health(self):
        """Check API connectivity and latency."""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Test API connectivity with a simple call
            await self.exchange_adapter.fetch_ticker('BTC-USDT-SWAP')
            
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            self.api_health_status = {
                'status': 'healthy',
                'latency_ms': latency,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
            if latency > 5000:  # 5 seconds
                logger.warning(f"[RISK] API latency high: {latency:.0f}ms")
            else:
                logger.debug(f"[RISK] API health OK: {latency:.0f}ms")
                
        except Exception as e:
            self.api_health_status = {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            logger.error(f"[RISK] API health check failed: {e}")
    
    async def _check_active_positions(self):
        """Check active positions for immediate risk issues."""
        try:
            # Get active positions
            active_positions = await self._get_active_positions()
            
            if not active_positions:
                logger.debug("[RISK] No active positions to monitor")
                return
            
            logger.info(f"[RISK] Monitoring {len(active_positions)} active positions")
            
            for symbol in active_positions:
                try:
                    await self._check_position_risk(symbol)
                except Exception as e:
                    logger.error(f"❌ Failed to check position risk for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Failed to check active positions: {e}")
    
    async def _get_active_positions(self) -> List[str]:
        """Get list of symbols with active positions using real position monitor."""
        try:
            # Import and use real position monitor
            from application.position_monitor import PositionMonitor
            from application.portfolio_service import PortfolioService
            from application.risk_service import RiskService
            
            portfolio_service = PortfolioService(self.exchange_adapter)
            risk_service = RiskService(self.policy)
            
            position_monitor = PositionMonitor(
                portfolio_service=portfolio_service,
                risk_service=risk_service,
                exchange_adapter=self.exchange_adapter,
                config={},
                policy=self.policy
            )
            
            active_positions = await position_monitor.get_active_positions()
            return [pos['symbol'] for pos in active_positions] if active_positions else []
            
        except Exception as e:
            logger.error(f"❌ Failed to get active positions: {e}")
            return []
    
    async def _check_position_risk(self, symbol: str):
        """Check individual position for immediate risk issues."""
        try:
            # Get position info
            position = await self._get_position_info(symbol)
            if not position:
                return
            
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.warning(f"[RISK] Could not get current price for {symbol}")
                return
            
            # Check if stop loss is hit
            if self._is_stop_loss_hit(position, current_price):
                logger.warning(f"[RISK] {symbol} STOP LOSS HIT! Closing position immediately")
                await self._emergency_close_position(symbol, "Stop loss hit")
                return
            
            # Check if take profit is hit
            if self._is_take_profit_hit(position, current_price):
                logger.info(f"[RISK] {symbol} TAKE PROFIT HIT! Closing position")
                await self._close_position(symbol, "Take profit hit")
                return
            
            # Check position age
            position_age_hours = self._get_position_age_hours(position)
            max_age = self.get_risk_config('max_position_age_hours')
            
            if position_age_hours > max_age:
                logger.warning(f"[RISK] {symbol} position age {position_age_hours:.1f}h > {max_age}h, closing")
                await self._close_position(symbol, f"Position age limit exceeded ({position_age_hours:.1f}h)")
                return
            
            logger.debug(f"[RISK] {symbol} position OK (age: {position_age_hours:.1f}h)")
            
        except Exception as e:
            logger.error(f"❌ Failed to check position risk for {symbol}: {e}")
    
    async def _get_position_info(self, symbol: str) -> Dict[str, Any]:
        """Get position information for a symbol."""
        try:
            # This would typically fetch from exchange or position manager
            # For now, return None as we don't have active positions yet
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get position info for {symbol}: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        try:
            ticker = await self.exchange_adapter.fetch_ticker(symbol)
            return float(ticker['last'])
            
        except Exception as e:
            logger.error(f"❌ Failed to get current price for {symbol}: {e}")
            return None
    
    def _is_stop_loss_hit(self, position: Dict[str, Any], current_price: float) -> bool:
        """Check if stop loss is hit."""
        try:
            stop_loss = position.get('stop_loss')
            if not stop_loss:
                return False
            
            side = position['side']
            if side == 'long':
                return current_price <= stop_loss
            else:
                return current_price >= stop_loss
                
        except Exception as e:
            logger.error(f"❌ Failed to check stop loss: {e}")
            return False
    
    def _is_take_profit_hit(self, position: Dict[str, Any], current_price: float) -> bool:
        """Check if take profit is hit."""
        try:
            take_profit = position.get('take_profit')
            if not take_profit:
                return False
            
            side = position['side']
            if side == 'long':
                return current_price >= take_profit
            else:
                return current_price <= take_profit
                
        except Exception as e:
            logger.error(f"❌ Failed to check take profit: {e}")
            return False
    
    def _get_position_age_hours(self, position: Dict[str, Any]) -> float:
        """Get position age in hours."""
        try:
            entry_time = position.get('entry_time')
            if not entry_time:
                return 0.0
            
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            
            age = datetime.now(timezone.utc) - entry_time
            return age.total_seconds() / 3600.0
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate position age: {e}")
            return 0.0
    
    async def _emergency_close_position(self, symbol: str, reason: str):
        """Emergency close position (immediate execution)."""
        try:
            logger.warning(f"[EMERGENCY] {symbol} position closed: {reason}")
            # Here you would execute immediate close order on the exchange
            
        except Exception as e:
            logger.error(f"❌ Failed to emergency close position for {symbol}: {e}")
            raise
    
    async def _close_position(self, symbol: str, reason: str):
        """Close position normally."""
        try:
            logger.info(f"[CLOSE] {symbol} position closed: {reason}")
            # Here you would execute close order on the exchange
            
        except Exception as e:
            logger.error(f"❌ Failed to close position for {symbol}: {e}")
            raise
    
    async def _check_system_health(self):
        """Check overall system health."""
        try:
            # Check memory usage
            import psutil
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > 90:
                logger.warning(f"[RISK] High memory usage: {memory_percent:.1f}%")
            else:
                logger.debug(f"[RISK] Memory usage OK: {memory_percent:.1f}%")
            
            # Check disk space
            disk_percent = psutil.disk_usage('/').percent
            
            if disk_percent > 90:
                logger.warning(f"[RISK] High disk usage: {disk_percent:.1f}%")
            else:
                logger.debug(f"[RISK] Disk usage OK: {disk_percent:.1f}%")
                
        except Exception as e:
            logger.error(f"❌ Failed to check system health: {e}")
    
    def get_api_health_status(self) -> Dict[str, Any]:
        """Get current API health status."""
        return self.api_health_status
    
    async def _check_circuit_breaker(self):
        """Check circuit breaker conditions."""
        try:
            # Get portfolio state
            try:
                balance = await self.exchange_adapter.fetch_balance()
                total_value = float(balance.get('USDT', {}).get('total', 0))
                
                # Get positions for PnL
                positions = await self.exchange_adapter.fetch_positions()
                total_pnl = sum(float(pos.get('unrealizedPnl', 0)) for pos in positions if pos.get('contracts', 0) != 0)
                
                # Simple drawdown estimation
                max_drawdown = abs(min(0, total_pnl / total_value)) if total_value > 0 else 0
                
                portfolio = {
                    'total_value': total_value,
                    'total_pnl': total_pnl,
                    'max_drawdown': max_drawdown
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch portfolio for circuit breaker: {e}")
                return
            
            # Get recent trades from history
            recent_trades = await self._get_recent_trades()
            
            # Check circuit breaker
            state = await self.circuit_breaker.check_conditions(portfolio, recent_trades)
            
            if state != 'normal':
                logger.warning(f"⚠️ Circuit breaker state: {state}")
            else:
                logger.debug(f"✅ Circuit breaker: {state}")
            
        except Exception as e:
            logger.error(f"❌ Circuit breaker check failed: {e}")
    
    async def _get_recent_trades(self) -> list:
        """Get recent trades for streak analysis using TradeHistory."""
        try:
            # Use TradeHistory module for consolidated trade tracking
            from application.trade_history import get_trade_history
            trade_history = get_trade_history()
            return trade_history.get_recent_trades(limit=10)
        except Exception as e:
            logger.warning(f"Failed to get recent trades: {e}")
            return []


