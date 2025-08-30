"""
Position manager for post-fill TP/SL management.
Contains post-fill TP/SL via REST/algo, OCO emulation.
"""

import logging
from typing import Any, Dict, Optional

from execution.prevalidation import OrderPrevalidator


class PositionManager:
    """Manager for position-related operations including TP/SL attachment."""
    
    def __init__(self, rest_adapter, logger=None):
        self.rest_adapter = rest_adapter
        self.logger = logger or logging.getLogger(__name__)
        self.prevalidator = OrderPrevalidator()
    
    async def attach_bracket(self, symbol: str, side_close: str, ref_price: float, 
                           tp: Optional[float], sl: Optional[float], 
                           reduce_only: bool = True) -> Dict[str, Any]:
        """Attach take profit and stop loss orders to an existing position."""
        try:
            if tp is None and sl is None:
                return {
                    "status": "skipped",
                    "reason": "No TP/SL provided"
                }
            
            # Validate TP/SL prices
            validation_result = self._validate_tp_sl_prices(
                symbol, side_close, ref_price, tp, sl
            )
            
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "reason": f"TP/SL validation failed: {validation_result['errors']}"
                }
            
            # Prepare bracket orders
            bracket_orders = []
            
            # Take Profit order
            if tp is not None:
                tp_order = await self._create_tp_order(
                    symbol, side_close, tp, reduce_only
                )
                if tp_order.get("status") == "success":
                    bracket_orders.append({
                        "type": "take_profit",
                        "order": tp_order
                    })
            
            # Stop Loss order
            if sl is not None:
                sl_order = await self._create_sl_order(
                    symbol, side_close, sl, reduce_only
                )
                if sl_order.get("status") == "success":
                    bracket_orders.append({
                        "type": "stop_loss",
                        "order": sl_order
                    })
            
            if not bracket_orders:
                return {
                    "status": "error",
                    "reason": "Failed to create any bracket orders"
                }
            
            self.logger.info(f"Bracket attached to {symbol}: {len(bracket_orders)} orders")
            
            return {
                "status": "success",
                "bracket_orders": bracket_orders,
                "symbol": symbol,
                "side_close": side_close,
                "ref_price": ref_price
            }
            
        except Exception as e:
            self.logger.error(f"Failed to attach bracket to {symbol}: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def _create_tp_order(self, symbol: str, side: str, price: float, 
                              reduce_only: bool) -> Dict[str, Any]:
        """Create take profit order."""
        try:
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": "limit",
                "price": price,
                "params": {
                    "reduceOnly": reduce_only,
                    "orderType": "conditional"
                }
            }
            
            # Try to place via REST adapter
            if hasattr(self.rest_adapter, "place_order"):
                result = await self.rest_adapter.place_order(**order_params)
            else:
                # Fallback to CCXT
                result = await self.rest_adapter.create_order(**order_params)
            
            return {
                "status": "success",
                "order_id": result.get("id"),
                "price": price,
                "type": "take_profit"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create TP order: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def _create_sl_order(self, symbol: str, side: str, price: float, 
                              reduce_only: bool) -> Dict[str, Any]:
        """Create stop loss order."""
        try:
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": "stop",
                "price": price,
                "params": {
                    "reduceOnly": reduce_only,
                    "orderType": "conditional"
                }
            }
            
            # Try to place via REST adapter
            if hasattr(self.rest_adapter, "place_order"):
                result = await self.rest_adapter.place_order(**order_params)
            else:
                # Fallback to CCXT
                result = await self.rest_adapter.create_order(**order_params)
            
            return {
                "status": "success",
                "order_id": result.get("id"),
                "price": price,
                "type": "stop_loss"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create SL order: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def _validate_tp_sl_prices(self, symbol: str, side_close: str, ref_price: float, 
                              tp: Optional[float], sl: Optional[float]) -> Dict[str, Any]:
        """Validate TP/SL prices against reference price."""
        try:
            errors = []
            
            # Validate reference price
            if ref_price <= 0:
                errors.append("Invalid reference price")
            
            # Validate TP price
            if tp is not None:
                if tp <= 0:
                    errors.append("Invalid TP price")
                else:
                    # LONG position close (sell): TP should be > ref_price
                    # SHORT position close (buy): TP should be < ref_price
                    if side_close == "sell":  # Closing LONG position
                        if tp <= ref_price:
                            errors.append("TP must be > reference price for LONG position close")
                    else:  # Closing SHORT position
                        if tp >= ref_price:
                            errors.append("TP must be < reference price for SHORT position close")
            
            # Validate SL price
            if sl is not None:
                if sl <= 0:
                    errors.append("Invalid SL price")
                else:
                    # LONG position close (sell): SL should be < ref_price
                    # SHORT position close (buy): SL should be > ref_price
                    if side_close == "sell":  # Closing LONG position
                        if sl >= ref_price:
                            errors.append("SL must be < reference price for LONG position close")
                    else:  # Closing SHORT position
                        if sl <= ref_price:
                            errors.append("SL must be > reference price for SHORT position close")
            
            # Validate TP/SL relationship
            if tp is not None and sl is not None:
                if side_close == "sell":  # LONG position close
                    if tp <= sl:
                        errors.append("TP must be > SL for LONG position close")
                else:  # SHORT position close
                    if tp >= sl:
                        errors.append("TP must be < SL for SHORT position close")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"]
            }
    
    async def cancel_bracket(self, symbol: str) -> Dict[str, Any]:
        """Cancel all bracket orders for a symbol."""
        try:
            # Get open orders for the symbol
            open_orders = await self.rest_adapter.fetch_open_orders(symbol)
            
            cancelled_count = 0
            cancelled_orders = []
            
            for order in open_orders:
                # Check if it's a bracket order (TP/SL)
                order_type = order.get("type", "")
                if order_type in ["limit", "stop"] and order.get("reduceOnly"):
                    try:
                        await self.rest_adapter.cancel_order(order["id"], symbol)
                        cancelled_count += 1
                        cancelled_orders.append({
                            "order_id": order["id"],
                            "type": order_type,
                            "price": order.get("price")
                        })
                        self.logger.info(f"Cancelled bracket order {order['id']} for {symbol}")
                    except Exception as e:
                        self.logger.warning(f"Failed to cancel bracket order {order['id']}: {e}")
            
            return {
                "status": "success",
                "cancelled_count": cancelled_count,
                "cancelled_orders": cancelled_orders,
                "symbol": symbol
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cancel bracket for {symbol}: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }


__all__ = ["PositionManager"]
