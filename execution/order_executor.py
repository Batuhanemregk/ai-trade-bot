"""
Order executor for OKX CCXT entry path.
Contains order execution logic and parameter validation.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from execution.prevalidation import OrderPrevalidator
from execution.quantize import quantize_price, quantize_size, bump_to_min_size


class OrderExecutor:
    """Executor for placing and managing orders via CCXT."""
    
    def __init__(self, exchange, prevalidator, quantizer, logger=None):
        self.exchange = exchange
        self.prevalidator = prevalidator or OrderPrevalidator()
        self.quantizer = quantizer
        self.logger = logger or logging.getLogger(__name__)
    
    async def place_entry(self, symbol: str, side: str, type_: str, amount: float, 
                         price: Optional[float] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Place entry order with proper validation and execution."""
        try:
            # Validate order parameters
            validation_result = await self._validate_order_params(symbol, side, type_, amount, price)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "reason": f"Validation failed: {validation_result['errors']}"
                }
            
            # Prepare order parameters
            order_params = {
                "symbol": symbol,
                "type": type_,
                "side": side,
                "amount": amount,
                "params": params or {}
            }
            
            if price is not None:
                order_params["price"] = price
            
            # Add client order ID for tracking
            if "clientOrderId" not in order_params["params"]:
                order_params["params"]["clientOrderId"] = self._generate_client_order_id(symbol)
            
            # Place order via exchange
            self.logger.info(f"Placing {type_} order: {side} {amount} {symbol} @ {price}")
            
            order_result = await self.exchange.create_order(**order_params)
            
            # Normalize response
            normalized_result = {
                "status": "success",
                "order_id": order_result.get("id"),
                "client_order_id": order_result.get("clientOrderId"),
                "symbol": order_result.get("symbol"),
                "side": order_result.get("side"),
                "type": order_result.get("type"),
                "amount": order_result.get("amount"),
                "price": order_result.get("price"),
                "order_status": order_result.get("status"),
                "timestamp": order_result.get("timestamp"),
                "raw": order_result
            }
            
            self.logger.info(f"Order placed successfully: {normalized_result['order_id']}")
            return normalized_result
            
        except Exception as e:
            self.logger.error(f"Failed to place entry order: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }
    
    async def ensure_min_and_quantize(self, symbol: str, side: str, amount: float, 
                                    price: Optional[float]) -> Tuple[float, Optional[float]]:
        """Ensure minimum size and quantize order parameters."""
        try:
            # Get instrument information for quantization
            instrument_info = await self._get_instrument_info(symbol)
            
            if not instrument_info:
                self.logger.warning(f"Instrument info not available for {symbol}, using defaults")
                return amount, price
            
            # Quantize size
            min_size = instrument_info.get("min_size", 0.001)
            size_precision = instrument_info.get("size_precision", 6)
            
            quantized_amount = quantize_size(amount, size_precision)
            if quantized_amount < min_size:
                quantized_amount = bump_to_min_size(amount, min_size)
            
            # Quantize price if provided
            quantized_price = None
            if price is not None:
                price_precision = instrument_info.get("price_precision", 2)
                quantized_price = quantize_price(price, price_precision)
            
            self.logger.debug(f"Quantized {symbol}: amount {amount} -> {quantized_amount}, price {price} -> {quantized_price}")
            
            return quantized_amount, quantized_price
            
        except Exception as e:
            self.logger.error(f"Failed to quantize order parameters: {e}")
            return amount, price
    
    async def _validate_order_params(self, symbol: str, side: str, type_: str, 
                                   amount: float, price: Optional[float]) -> Dict[str, Any]:
        """Validate order parameters using prevalidator."""
        try:
            # Basic validation
            if not symbol or not side or not type_ or amount <= 0:
                return {
                    "valid": False,
                    "errors": ["Invalid basic parameters"]
                }
            
            # Validate side
            if side not in ["buy", "sell"]:
                return {
                    "valid": False,
                    "errors": [f"Invalid side: {side}"]
                }
            
            # Validate order type
            if type_ not in ["market", "limit", "stop", "stop_limit"]:
                return {
                    "valid": False,
                    "errors": [f"Invalid order type: {type_}"]
                }
            
            # Validate price for limit orders
            if type_ in ["limit", "stop_limit"] and price is None:
                return {
                    "valid": False,
                    "errors": ["Price required for limit orders"]
                }
            
            # Use prevalidator if available
            if hasattr(self.prevalidator, "validate_order"):
                validation_result = self.prevalidator.validate_order(
                    symbol=symbol,
                    side=side,
                    type_=type_,
                    amount=amount,
                    price=price or 0.0
                )
                
                if not validation_result.get("valid", True):
                    return validation_result
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"]
            }
    
    async def _get_instrument_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get instrument information for quantization."""
        try:
            # Try to get from exchange
            if hasattr(self.exchange, "fetch_instrument"):
                return await self.exchange.fetch_instrument(symbol)
            
            # Try to get from market info
            if hasattr(self.exchange, "fetch_market"):
                market = await self.exchange.fetch_market(symbol)
                if market:
                    return {
                        "min_size": market.get("limits", {}).get("amount", {}).get("min", 0.001),
                        "size_precision": market.get("precision", {}).get("amount", 6),
                        "price_precision": market.get("precision", {}).get("price", 2)
                    }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get instrument info for {symbol}: {e}")
            return None
    
    def _generate_client_order_id(self, symbol: str) -> str:
        """Generate unique client order ID."""
        import time
        import random
        import string
        
        timestamp = int(time.time() * 1000)
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{symbol}_{timestamp}_{random_suffix}"


__all__ = ["OrderExecutor"]
