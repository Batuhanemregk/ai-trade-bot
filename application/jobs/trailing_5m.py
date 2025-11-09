"""
Trailing Stops Job (5m)
Handles SL/TP/trailing stop updates every 5 minutes
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger

from .base_job import BaseJob


class Trailing5mJob(BaseJob):
    """5-minute trailing stops job for position management."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.position_monitor = None
        
    async def initialize(self):
        """Initialize trailing stops components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            # Initialize position monitor with real services
            from application.position_monitor import PositionMonitor
            from application.portfolio_service import PortfolioService
            from application.risk_service import RiskService
            
            portfolio_service = PortfolioService(self.exchange_adapter)
            risk_service = RiskService(self.policy)
            
            self.position_monitor = PositionMonitor(
                portfolio_service=portfolio_service,
                risk_service=risk_service,
                exchange_adapter=self.exchange_adapter,
                config={},
                policy=self.policy
            )
            
            logger.info("✅ Trailing5mJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trailing5mJob: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup trailing stops resources"""
        try:
            if hasattr(self, 'exchange_adapter') and self.exchange_adapter:
                await self.exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter for Trailing5mJob")
        except Exception as e:
            logger.error(f"❌ Trailing5mJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute 5-minute trailing stops update."""
        if not self.start_run('5m'):
            return
        
        bar_id = self.current_bar_id
        try:
            logger.info(f"[JOB] trailing_5m run_id={self.run_id} bar={bar_id} starting execution")
            
            # Get all active positions
            active_positions = await self._get_active_positions()
            
            if not active_positions:
                logger.info("[TRAIL] No active positions to monitor")
                self.finish_run("SUCCESS")
                return
            
            logger.info(f"[TRAIL] Monitoring {len(active_positions)} active positions")
            
            processed_count = 0
            for symbol in active_positions:
                try:
                    # Check bar idempotency
                    if self.is_bar_already_processed(symbol, '5m'):
                        logger.debug(f"[BAR] {symbol} 5m bar already processed, skipping")
                        continue
                    
                    # Process trailing stops for this position
                    await self._process_trailing_stops(symbol)
                    
                    # Mark bar as processed
                    self.mark_bar_processed(symbol, '5m')
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process trailing stops for {symbol}: {e}")
                    continue
            
            logger.info(
                f"[JOB] trailing_5m run_id={self.run_id} bar={bar_id} "
                f"completed {processed_count}/{len(active_positions)} positions"
            )
            self.mark_bar_processed(self.job_id, '5m')
            self.finish_run("SUCCESS")
            
        except Exception as e:
            logger.error(f"❌ Trailing5mJob execution failed: {e}")
            self.finish_run("FAILED", str(e))
            raise
    
    async def _get_active_positions(self) -> List[str]:
        """Get list of symbols with active positions using real position monitor."""
        try:
            # Use the real position monitor to get active positions
            active_positions = await self.position_monitor.get_active_positions()
            return [pos['symbol'] for pos in active_positions] if active_positions else []
            
        except Exception as e:
            logger.error(f"❌ Failed to get active positions: {e}")
            return []
    
    async def _process_trailing_stops(self, symbol: str):
        """Process trailing stops for a specific position."""
        try:
            logger.info(f"[TRAIL] Processing trailing stops for {symbol}")
            
            # Get current position info
            position = await self._get_position_info(symbol)
            if not position:
                logger.warning(f"[TRAIL] No position found for {symbol}")
                return
            
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.warning(f"[TRAIL] Could not get current price for {symbol}")
                return
            
            # Calculate R-multiple
            r_multiple = self._calculate_r_multiple(position, current_price)
            
            logger.info(f"[TRAIL] {symbol} R-multiple: {r_multiple:.2f}")
            
            # Check if trailing should be activated
            activation_r = 0.5  # 0.5R activation threshold
            if r_multiple >= activation_r:
                await self._update_trailing_stop(symbol, position, current_price, r_multiple)
            else:
                logger.info(f"[TRAIL] {symbol} R-multiple {r_multiple:.2f} < {activation_r}, trailing not activated")
            
        except Exception as e:
            logger.error(f"❌ Failed to process trailing stops for {symbol}: {e}")
            raise
    
    async def _get_position_info(self, symbol: str) -> Dict[str, Any]:
        """Get position information for a symbol using real position monitor."""
        try:
            # Use the real position monitor to get position info
            position = await self.position_monitor.get_position_info(symbol)
            return position
            
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
    
    def _calculate_r_multiple(self, position: Dict[str, Any], current_price: float) -> float:
        """Calculate R-multiple for a position."""
        try:
            entry_price = position['entry_price']
            side = position['side']
            
            if side == 'long':
                return (current_price - entry_price) / entry_price
            else:
                return (entry_price - current_price) / entry_price
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate R-multiple: {e}")
            return 0.0
    
    async def _update_trailing_stop(self, symbol: str, position: Dict[str, Any], current_price: float, r_multiple: float):
        """Update trailing stop for a position."""
        try:
            side = position['side']
            entry_price = position['entry_price']
            
            # Calculate new stop price based on R-multiple
            if r_multiple >= 1.5:
                # Tight trailing stop (0.8R)
                if side == 'long':
                    new_stop = current_price * 0.98  # 2% trailing
                else:
                    new_stop = current_price * 1.02  # 2% trailing
                logger.info(f"[TRAIL] {symbol} tight trailing stop: {new_stop:.4f}")
                
            elif r_multiple >= 1.0:
                # Breakeven + 0.3R
                if side == 'long':
                    new_stop = entry_price * 1.03  # Breakeven + 3%
                else:
                    new_stop = entry_price * 0.97  # Breakeven - 3%
                logger.info(f"[TRAIL] {symbol} breakeven+ trailing stop: {new_stop:.4f}")
                
            else:
                # Normal trailing stop (0.5R+)
                if side == 'long':
                    new_stop = current_price * 0.98  # 2% trailing
                else:
                    new_stop = current_price * 1.02  # 2% trailing
                logger.info(f"[TRAIL] {symbol} normal trailing stop: {new_stop:.4f}")
            
            # Check if stop is hit
            if self._is_stop_hit(side, current_price, new_stop):
                logger.warning(f"[TRAIL] {symbol} STOP HIT! Closing position at {current_price:.4f}")
                await self._close_position(symbol, "Trailing stop hit")
            else:
                logger.info(f"[TRAIL] {symbol} trailing stop updated to {new_stop:.4f}")
                # Here you would update the stop order on the exchange
            
        except Exception as e:
            logger.error(f"❌ Failed to update trailing stop for {symbol}: {e}")
            raise
    
    def _is_stop_hit(self, side: str, current_price: float, stop_price: float) -> bool:
        """Check if trailing stop is hit."""
        if side == 'long':
            return current_price <= stop_price
        else:
            return current_price >= stop_price
    
    async def _close_position(self, symbol: str, reason: str):
        """Close a position."""
        try:
            logger.info(f"[CLOSE] {symbol} position closed: {reason}")
            # Here you would execute the close order on the exchange
            
        except Exception as e:
            logger.error(f"❌ Failed to close position for {symbol}: {e}")
            raise
