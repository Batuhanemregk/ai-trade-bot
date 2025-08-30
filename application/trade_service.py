"""
Trade service for order orchestration.
Contains order orchestration, TP/SL attach strategy, and retries.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

from execution.order_executor import OrderExecutor
from execution.position_executor import PositionManager
from execution.prevalidation import OrderPrevalidator
from execution.quantize import quantize_price, quantize_size, bump_to_min_size


class TradeService:
    """Service for orchestrating trade execution."""
    
    def __init__(self, exchange, policy, risk_service, logger=None):
        self.exchange = exchange
        self.policy = policy
        self.risk_service = risk_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize execution components
        self.order_executor = OrderExecutor(exchange, OrderPrevalidator(), None, logger)
        self.position_manager = PositionManager(exchange, logger)
        
        # Trading state
        self.last_trade_time: Dict[str, float] = {}
        self._processed_ticks = set()
        self._last_tick_cleanup = time.time()
        self._tick_locks: Dict[str, asyncio.Lock] = {}
    
    def _cleanup_old_ticks(self):
        """Clean up old tick records to prevent memory bloat."""
        current_time = time.time()
        if current_time - self._last_tick_cleanup > 300:  # 5 minutes
            self._processed_ticks.clear()
            self._last_tick_cleanup = current_time
    
    def _is_tick_processed(self, symbol: str, current_tick: int) -> bool:
        """Check if this symbol has already been processed in current tick."""
        self._cleanup_old_ticks()
        lock_key = f"{symbol}_{current_tick}"
        if lock_key in self._processed_ticks:
            return True
        self._processed_ticks.add(lock_key)
        return False
    
    async def _get_tick_lock(self, symbol: str) -> asyncio.Lock:
        """Get or create tick lock for symbol."""
        if symbol not in self._tick_locks:
            self._tick_locks[symbol] = asyncio.Lock()
        return self._tick_locks[symbol]
    
    async def execute_signal(self, symbol: str, side: str, qty: float, price: Optional[float] = None,
                           sl: Optional[float] = None, tp: Optional[float] = None, 
                           mode: str = "entry_then_attach") -> Dict[str, Any]:
        """Execute trading signal with proper orchestration."""
        try:
            # Get tick lock for idempotency
            tick_lock = await self._get_tick_lock(symbol)
            async with tick_lock:
                # Check if already processed
                current_tick = int(time.time() * 1000)
                if self._is_tick_processed(symbol, current_tick):
                    return {"status": "skipped", "reason": "already_processed"}
                
                # Validate and quantize order parameters
                qty, price = await self.order_executor.ensure_min_and_quantize(symbol, side, qty, price)
                
                # Place entry order
                entry_result = await self.order_executor.place_entry(
                    symbol=symbol,
                    side=side,
                    type_="market" if price is None else "limit",
                    amount=qty,
                    price=price
                )
                
                if entry_result.get("status") != "success":
                    return entry_result
                
                # Handle TP/SL attachment based on mode
                if mode == "entry_then_attach" and (tp is not None or sl is not None):
                    # Wait for entry fill then attach bracket
                    await self._wait_for_entry_fill(entry_result["order_id"], symbol)
                    
                    # Attach bracket orders
                    bracket_result = await self.position_manager.attach_bracket(
                        symbol=symbol,
                        side_close="sell" if side == "buy" else "buy",
                        ref_price=price or entry_result.get("fill_price"),
                        tp=tp,
                        sl=sl,
                        reduce_only=True
                    )
                    
                    return {
                        "status": "success",
                        "entry": entry_result,
                        "bracket": bracket_result,
                        "mode": mode
                    }
                
                return {
                    "status": "success",
                    "entry": entry_result,
                    "mode": mode
                }
                
        except Exception as e:
            self.logger.error(f"Failed to execute signal for {symbol}: {e}")
            return {"status": "error", "reason": str(e)}
    
    async def _wait_for_entry_fill(self, order_id: str, symbol: str, timeout: int = 30):
        """Wait for entry order to be filled."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                order_status = await self.exchange.fetch_order(order_id, symbol)
                if order_status.get("status") == "closed":
                    return order_status
                await asyncio.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Error checking order status: {e}")
                await asyncio.sleep(1)
        
        raise TimeoutError(f"Entry order {order_id} not filled within {timeout}s")
    
    async def cancel_open(self, symbol: str, reason: str) -> int:
        """Cancel all open orders for a symbol."""
        try:
            open_orders = await self.exchange.fetch_open_orders(symbol)
            cancelled_count = 0
            
            for order in open_orders:
                try:
                    await self.exchange.cancel_order(order["id"], symbol)
                    cancelled_count += 1
                    self.logger.info(f"Cancelled order {order['id']} for {symbol}: {reason}")
                except Exception as e:
                    self.logger.warning(f"Failed to cancel order {order['id']}: {e}")
            
            return cancelled_count
            
        except Exception as e:
            self.logger.error(f"Failed to cancel open orders for {symbol}: {e}")
            return 0


__all__ = ["TradeService"]
