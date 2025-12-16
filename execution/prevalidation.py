"""
Order prevalidation utilities.
Handles TP/SL validation, price policy checks, and order constraints.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
from loguru import logger
import asyncio


class ValidationError(Exception):
    """Raised when order validation fails."""
    pass


def ceil_to_step(x: float, step: float) -> float:
    """Round up to the nearest step."""
    if step is None or step == 0:
        return x
    # step ondalık ise yukarı yuvarla
    n = int(-(-x // step))  # ceiling division for floats' step (approx)
    return round(n * step, 12)


async def _get_dynamic_minimum_cost(exchange, symbol: str, price: float) -> float:
    """Get dynamic minimum cost based on exchange rules.
    
    Note: With ctVal fix in place, this function is simplified and mainly
    returns sensible defaults without making additional API calls.
    """
    try:
        # Use provided price instead of fetching orderbook
        current_price = price if price and price > 0 else 100.0
        
        # OKX specific minimum cost rules based on symbol type
        # Extract base currency from symbol (e.g., "BTC/USDT:USDT" -> "BTC")
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
        else:
            base_currency = symbol.split('-')[0]
        
        # Different minimum costs for different asset classes
        if base_currency in ['BTC', 'ETH']:
            min_cost_usdt = 5.0
        elif base_currency in ['SOL', 'ADA', 'DOT', 'MATIC', 'AVAX']:
            min_cost_usdt = 2.0
        elif base_currency in ['DOGE', 'SHIB', 'PEPE']:
            min_cost_usdt = 1.0
        else:
            min_cost_usdt = 1.0
        
        # Adjust based on price (higher priced assets may need higher minimum)
        if current_price > 1000:
            min_cost_usdt *= 2
        elif current_price > 100:
            min_cost_usdt *= 1.5
        
        logger.info(f"📊 {symbol} dynamic minimum cost: ${min_cost_usdt:.2f}")
        return min_cost_usdt
        
    except Exception as e:
        logger.error(f"❌ Failed to get dynamic minimum cost for {symbol}: {e}")
        return 1.0  # Fallback


async def compute_required_amount(exchange, symbol: str, price: float) -> dict:
    """Compute required minimum amount for a symbol."""
    try:
        # Load policy overrides
        try:
            from infrastructure.bootstrap import load_policy
            policy = load_policy()
            symbol_overrides = policy.get('exchange', {}).get('symbol_overrides', {}).get(symbol, {})
        except:
            symbol_overrides = {}
        
        # Load markets if not loaded
        if not hasattr(exchange, 'markets') or not exchange.markets:
            exchange.load_markets()
        
        m = exchange.market(symbol)
        limits = m.get('limits', {}) or {}
        prec = m.get('precision', {}) or {}

        # amount step & min
        amount_step = None
        amount_min = (limits.get('amount') or {}).get('min')
        amount_step = (limits.get('amount') or {}).get('step')

        # bazı OKX marketlerinde info altında minSz/lotSz olur
        info = m.get('info', {}) or {}
        min_sz = info.get('minSz')
        lot_sz = info.get('lotSz')
        tick_sz = info.get('tickSz')

        # cost min
        min_cost = (limits.get('cost') or {}).get('min') or m.get('minCost')
        
        # Note: OKX minimum cost is typically handled by position size calculation
        # No need to override min_cost here as position size should be sufficient

        # amount_step'i türet (elde yoksa lot_sz veya precision'dan)
        if amount_step in (None, 0):
            if lot_sz not in (None, ''):
                try:
                    amount_step = float(lot_sz)
                except:
                    amount_step = None
        if amount_step in (None, 0) and 'amount' in prec and prec['amount'] is not None:
            # precision -> step
            # ör: precision.amount = 3 ise step = 0.001
            try:
                amount_step = 10 ** (-int(prec['amount']))
            except:
                amount_step = None

        # amount_min'i türet (elde yoksa min_sz veya step'e düş)
        if amount_min in (None, 0):
            if min_sz not in (None, ''):
                try:
                    amount_min = float(min_sz)
                except:
                    amount_min = None
        
        # CRITICAL FIX: Always apply ctVal (contract value) multiplication
        # OKX perpetual swaps use: real_min = minSz × ctVal, real_step = lotSz × ctVal
        # e.g., ETH: minSz=0.01, ctVal=0.1 → real_min = 0.001 ETH, real_step = 0.001
        # e.g., BTC: minSz=0.01, ctVal=0.01 → real_min = 0.0001 BTC, real_step = 0.0001
        # The limits.amount.min from CCXT is already set to 0.01, but it doesn't
        # account for ctVal, so we MUST apply the adjustment here.
        ct_val = info.get('ctVal')
        logger.debug(f"[CTVAL-DEBUG] {symbol}: amount_min={amount_min}, amount_step={amount_step}, ctVal={ct_val}")
        
        if ct_val:
            try:
                ct_val_float = float(ct_val)
                if ct_val_float != 1.0:
                    # Apply to amount_min
                    if amount_min:
                        original_min = amount_min
                        amount_min = amount_min * ct_val_float
                        logger.info(f"📊 {symbol} ctVal adjustment min: {original_min} × {ct_val_float} = {amount_min}")
                    
                    # ALSO apply to amount_step for correct rounding
                    if amount_step:
                        original_step = amount_step
                        amount_step = amount_step * ct_val_float
                        logger.info(f"📊 {symbol} ctVal adjustment step: {original_step} × {ct_val_float} = {amount_step}")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} ctVal conversion failed: {e}")

        # Apply symbol overrides
        if symbol_overrides:
            if 'min_amount' in symbol_overrides:
                amount_min = symbol_overrides['min_amount']
            if 'min_cost_usdt' in symbol_overrides:
                min_cost = symbol_overrides['min_cost_usdt']

        # Fiyat yoksa min_cost kullanamayız
        need_by_cost = 0.0
        if price and min_cost:
            need_by_cost = min_cost / float(price)
        
        # NOTE: ctVal adjustment above already gives correct minimum amounts:
        # ETH: 0.01 × 0.1 = 0.001 ETH
        # BTC: 0.01 × 0.01 = 0.0001 BTC
        # SOL: 0.01 × 1 = 0.01 SOL
        # No need for dynamic cost override - use the actual exchange minimums

        base_need = max(need_by_cost, amount_min or 0.0)

        # step'e yukarı yuvarla
        if amount_step and base_need:
            base_need = ceil_to_step(base_need, amount_step)

        return {
            "amount_step": amount_step,
            "amount_min": amount_min,
            "min_cost": min_cost,
            "required_amount": base_need,
            "tick_sz": tick_sz,
            "raw_info": {"minSz": min_sz, "lotSz": lot_sz},
            "overrides_applied": bool(symbol_overrides)
        }
    except Exception as e:
        logger.error(f"Error computing required amount for {symbol}: {e}")
        return {
            "amount_step": 0.001,
            "amount_min": 0.001,
            "min_cost": 5.0,
            "required_amount": 0.001,
            "tick_sz": 0.01,
            "raw_info": {},
            "overrides_applied": False
        }


async def ensure_minimums(exchange, symbol: str, price: float, requested_amount: float):
    """Ensure order meets minimum requirements."""
    try:
        meta = await compute_required_amount(exchange, symbol, price)
        required = meta["required_amount"] or 0.0
        if requested_amount is None:
            return required, meta, (required if required > 0 else None)

        adj = requested_amount
        # step yukarı yuvarlama
        step = meta["amount_step"]
        if step and step > 0:
            adj = ceil_to_step(adj, step)

        # min kontrol
        if required and adj < required:
            adj = required

        return adj, meta, (None if adj >= required else required)
    except Exception as e:
        logger.error(f"Error ensuring minimums for {symbol}: {e}")
        return requested_amount, {}, None


@dataclass
class OrderPrevalidator:
    """Order prevalidator for TP/SL validation and price policy checks."""
    
    def validate_order(self, order_dict_or_symbol=None, side=None, type_=None, amount=None, price=None, **kwargs) -> dict:
        """Validate order with flexible signature (dict or keyword args)."""
        if isinstance(order_dict_or_symbol, dict):
            # Dict-based call (test compatibility)
            order_dict = order_dict_or_symbol
            symbol = order_dict.get("symbol")
            side = order_dict.get("side")
            price = order_dict.get("price")
            tp_price = order_dict.get("tp")
            sl_price = order_dict.get("sl")
        else:
            # Keyword-based call (executor compatibility)
            symbol = order_dict_or_symbol or kwargs.get("symbol")
            side = side or kwargs.get("side")
            price = price or kwargs.get("price")
            tp_price = kwargs.get("tp")
            sl_price = kwargs.get("sl")
        

        
        if not symbol or not side:
            return {
                'valid': False,
                'errors': ['Missing required fields: symbol, side']
            }
        
        try:
            # Validate TP/SL logic before correction
            if tp_price is not None and sl_price is not None:
                # Check for invalid TP/SL before correction
                if side == 'buy':  # LONG position
                    if tp_price <= price:  # TP should be above price for long
                        return {
                            'valid': False,
                            'error': f'TP price ({tp_price}) must be greater than entry price ({price}) for buy order'
                        }
                    if sl_price >= price:  # SL should be below price for long
                        return {
                            'valid': False,
                            'error': f'SL price ({sl_price}) must be less than entry price ({price}) for buy order'
                        }
                elif side == 'sell':  # SHORT position
                    if tp_price >= price:  # TP should be below price for short
                        return {
                            'valid': False,
                            'error': f'TP price ({tp_price}) must be less than entry price ({price}) for sell order'
                        }
                    if sl_price <= price:  # SL should be above price for short
                        return {
                            'valid': False,
                            'error': f'SL price ({sl_price}) must be greater than entry price ({price}) for sell order'
                        }
                
                # If validation passes, correct with epsilon nudging
                corrected_tp, corrected_sl = validate_tp_sl_prices(
                    symbol, side, price, tp_price, sl_price
                )
                return {
                    'valid': True,
                    'tp': corrected_tp,
                    'sl': corrected_sl
                }
            else:
                return {'valid': True}
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def validate_order_legacy(self, side_close: str, ref_price: float, tp_trigger: float = None, 
                      sl_trigger: float = None, tick_sz: float = 0.01, 
                      epsilon_ticks: int = 1) -> dict:
        """Validate order parameters (legacy method)."""
        result = {
            'valid': True,
            'errors': [],
            'tp_trigger': tp_trigger,
            'sl_trigger': sl_trigger
        }
        
        # Validate TP/SL prices
        if tp_trigger is not None or sl_trigger is not None:
            tp_valid, sl_valid = self.validate_tp_sl_prices(
                side_close, ref_price, tp_trigger, sl_trigger, tick_sz, epsilon_ticks
            )
            result['tp_trigger'] = tp_valid
            result['sl_trigger'] = sl_valid
        
        # Validate price policy
        if tp_trigger is not None:
            result['tp_price'] = self.validate_order_price_policy(
                side_close, tp_trigger, None, tick_sz
            )
        
        if sl_trigger is not None:
            result['sl_price'] = self.validate_order_price_policy(
                side_close, sl_trigger, None, tick_sz
            )
        
        return result
    
    def validate_tp_sl_prices(self, side_close: str, ref_price: float, tp_trigger: float = None,
                             sl_trigger: float = None, tick_sz: float = 0.01, 
                             epsilon_ticks: int = 1) -> Tuple[Optional[float], Optional[float]]:
        """Validate TP/SL prices and adjust if needed."""
        epsilon = epsilon_ticks * tick_sz
        
        if side_close == 'LONG':  # Reduce SELL: tp > ref, sl < ref
            if tp_trigger is not None and tp_trigger <= ref_price:
                tp_trigger = ref_price + epsilon
                tp_trigger = round(tp_trigger / tick_sz) * tick_sz
            
            if sl_trigger is not None and sl_trigger >= ref_price:
                sl_trigger = ref_price - epsilon
                sl_trigger = round(sl_trigger / tick_sz) * tick_sz
                
        elif side_close == 'SHORT':  # Reduce BUY: tp < ref, sl > ref
            if tp_trigger is not None and tp_trigger >= ref_price:
                tp_trigger = ref_price - epsilon
                tp_trigger = round(tp_trigger / tick_sz) * tick_sz
            
            if sl_trigger is not None and sl_trigger <= ref_price:
                sl_trigger = ref_price + epsilon
                sl_trigger = round(sl_trigger / tick_sz) * tick_sz
        
        return tp_trigger, sl_trigger
    
    def validate_order_price_policy(self, side_close: str, trigger: float, 
                                  ord_px: float = None, tick_sz: float = 0.01) -> Optional[float]:
        """Validate order price policy."""
        if ord_px == -1:  # Market sentinel
            return -1
        
        if ord_px is None:
            return None
        
        # SELL: ordPx ≤ trigger; BUY: ordPx ≥ trigger
        if side_close == 'LONG':  # SELL
            if ord_px > trigger:
                ord_px = trigger
        elif side_close == 'SHORT':  # BUY
            if ord_px < trigger:
                ord_px = trigger
        
        # Quantize to tick size
        if ord_px is not None:
            ord_px = round(ord_px / tick_sz) * tick_sz
        
        return ord_px


def validate_tp_sl_prices(symbol: str, side: str, ref_price: float, tp_price: float, sl_price: float) -> Tuple[float, float]:
    """
    Validate and correct TP/SL prices with epsilon nudging.
    
    Args:
        symbol: Trading symbol (e.g., "BTC-USDT")
        side: 'buy' or 'sell' (position side)
        ref_price: Reference price for validation
        tp_price: Take Profit price
        sl_price: Stop Loss price
    
    Returns:
        Tuple of corrected (tp_price, sl_price)
    """
    if tp_price is None or sl_price is None:
        raise ValueError("TP and SL prices cannot be None")
    
    if side not in ['buy', 'sell']:
        raise ValueError("Invalid side. Must be 'buy' or 'sell'")
    
    # Validate symbol format
    if not symbol or "-" not in symbol:
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    # Get symbol metadata for tick size
    try:
        from adapters import get_fallback_tick_size
        tick_sz = get_fallback_tick_size(symbol)
    except ImportError:
        # Fallback tick sizes based on symbol
        if "BTC" in symbol:
            tick_sz = 0.1
        elif "ETH" in symbol:
            tick_sz = 0.01
        elif symbol in ["BTC-USDT", "ETH-USDT", "BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
            tick_sz = 0.1 if "BTC" in symbol else 0.01
        else:
            # Invalid symbol - should raise error
            raise ValueError(f"Unknown symbol: {symbol}")
    except Exception as e:
        # Symbol not found or other error
        raise ValueError(f"Symbol validation failed for {symbol}: {e}")
    
    epsilon = tick_sz
    
    if side == 'buy':  # LONG position
        # For LONG: TP > ref_price, SL < ref_price
        if tp_price <= ref_price:
            tp_price = ref_price + epsilon
        if sl_price >= ref_price:
            sl_price = ref_price - epsilon
    elif side == 'sell':  # SHORT position
        # For SHORT: TP < ref_price, SL > ref_price
        if tp_price >= ref_price:
            tp_price = ref_price - epsilon
        if sl_price <= ref_price:
            sl_price = ref_price + epsilon
    
    # Quantize to tick size with proper precision
    from decimal import Decimal, ROUND_HALF_UP
    
    # Convert to Decimal for precise arithmetic
    tick_decimal = Decimal(str(tick_sz))
    tp_decimal = Decimal(str(tp_price))
    sl_decimal = Decimal(str(sl_price))
    
    # Quantize to tick size
    tp_price = float(tp_decimal.quantize(tick_decimal, rounding=ROUND_HALF_UP))
    sl_price = float(sl_decimal.quantize(tick_decimal, rounding=ROUND_HALF_UP))
    
    return tp_price, sl_price


def validate_tp_sl_prices_legacy(side: str, entry_price: float, tp_price: float, sl_price: float) -> Tuple[bool, List[str]]:
    """
    Legacy: Validate Take Profit and Stop Loss prices relative to entry price.
    
    Args:
        side: 'buy' or 'sell'
        entry_price: The entry price of the position
        tp_price: The Take Profit price
        sl_price: The Stop Loss price
    
    Returns:
        A tuple (is_valid, errors_list)
    """
    errors: List[str] = []
    
    if side == 'buy':
        # For buy, TP > Entry > SL
        if not (tp_price > entry_price):
            errors.append(f"TP price ({tp_price}) must be greater than entry price ({entry_price}) for buy order.")
        if not (entry_price > sl_price):
            errors.append(f"Entry price ({entry_price}) must be greater than SL price ({sl_price}) for buy order.")
    elif side == 'sell':
        # For sell, SL > Entry > TP
        if not (sl_price > entry_price):
            errors.append(f"SL price ({sl_price}) must be greater than entry price ({entry_price}) for sell order.")
        if not (entry_price > tp_price):
            errors.append(f"Entry price ({entry_price}) must be greater than TP price ({tp_price}) for sell order.")
    else:
        errors.append("Invalid side. Must be 'buy' or 'sell'.")
    
    return len(errors) == 0, errors


def validate_order_price_policy(current_price: float, order_price: float) -> Tuple[bool, List[str]]:
    """
    Validate if an order price is within acceptable spread from current market price.
    
    Args:
        current_price: The current market price
        order_price: The price at which the order is to be placed
    
    Returns:
        A tuple (is_valid, errors_list)
    """
    errors: List[str] = []
    
    if current_price <= 0:
        errors.append("Current price must be positive for price policy validation.")
        return False, errors
    
    spread_pct = abs((order_price - current_price) / current_price)
    
    # Check if spread is within acceptable range (0.1% to 10%)
    if spread_pct < 0.001:
        errors.append(f"Order price ({order_price}) is too close to current price ({current_price}). "
                      f"Spread {spread_pct:.4f}% is below minimum 0.1%.")
    if spread_pct > 0.1:
        errors.append(f"Order price ({order_price}) is too far from current price ({current_price}). "
                      f"Spread {spread_pct:.4f}% is above maximum 10%.")
    
    return len(errors) == 0, errors


def validate_order_size_constraints(size: float, min_size: float, max_size: float, 
                                  lot_size: float, available_balance: float,
                                  price: float, leverage: float = 1.0) -> Tuple[bool, List[str]]:
    """
    Validate order size constraints.
    
    Args:
        size: Order size
        min_size: Minimum order size
        max_size: Maximum order size
        lot_size: Lot size increment
        available_balance: Available balance
        price: Order price
        leverage: Leverage (default 1.0)
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check minimum size
    if size < min_size:
        errors.append(f"Order size {size} below minimum {min_size}")
    
    # Check maximum size
    if size > max_size:
        errors.append(f"Order size {size} above maximum {max_size}")
    
    # Check lot size alignment
    if lot_size > 0 and abs(size % lot_size) > 1e-10:
        errors.append(f"Order size {size} not aligned with lot size {lot_size}")
    
    # Check balance sufficiency
    required_margin = (size * price) / leverage
    if required_margin > available_balance:
        errors.append(f"Insufficient balance. Required: {required_margin}, Available: {available_balance}")
    
    return len(errors) == 0, errors


def validate_bracket_order(entry_price: float, tp_price: float, sl_price: float,
                          side: str, min_distance: float = 0.005) -> Tuple[bool, List[str]]:
    """
    Validate bracket order parameters.
    
    Args:
        entry_price: Entry order price
        tp_price: Take profit price
        sl_price: Stop loss price
        side: Position direction - 'buy' means LONG position, 'sell' means SHORT position
              (This is the ENTRY order side, which determines position direction)
        min_distance: Minimum distance as percentage
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    
    Note:
        - For LONG (buy entry): We want to sell at higher price for profit
          So: sl < entry < tp (TP above entry)
        - For SHORT (sell entry): We want to buy back at lower price for profit
          So: tp < entry < sl (TP below entry)
    """
    errors = []
    
    # Normalize side to lowercase
    side_lower = side.lower() if side else 'buy'
    
    if side_lower == 'buy':
        # LONG position: Entry is BUY, we exit by selling
        # Profit when price goes UP: TP should be ABOVE entry
        # Loss when price goes DOWN: SL should be BELOW entry
        # Valid: sl < entry < tp
        if not (sl_price < entry_price < tp_price):
            errors.append(f"LONG bracket invalid: expected sl {sl_price:.4f} < entry {entry_price:.4f} < tp {tp_price:.4f}")
    else:
        # SHORT position: Entry is SELL, we exit by buying
        # Profit when price goes DOWN: TP should be BELOW entry
        # Loss when price goes UP: SL should be ABOVE entry
        # Valid: tp < entry < sl
        if not (tp_price < entry_price < sl_price):
            errors.append(f"SHORT bracket invalid: expected tp {tp_price:.4f} < entry {entry_price:.4f} < sl {sl_price:.4f}")
    
    # Check minimum distances
    entry_tp_distance = abs(tp_price - entry_price) / entry_price
    entry_sl_distance = abs(sl_price - entry_price) / entry_price
    
    if entry_tp_distance < min_distance:
        errors.append(f"TP distance {entry_tp_distance:.4f} below minimum {min_distance}")
    
    if entry_sl_distance < min_distance:
        errors.append(f"SL distance {entry_sl_distance:.4f} below minimum {min_distance}")
    
    return len(errors) == 0, errors


def validate_market_order_params(symbol: str, side: str, size: float, 
                               min_size: float, max_size: float) -> Tuple[bool, List[str]]:
    """
    Validate market order parameters.
    
    Args:
        symbol: Trading symbol
        side: Order side ('buy' or 'sell')
        size: Order size
        min_size: Minimum order size
        max_size: Maximum order size
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Basic validation
    if not symbol or not isinstance(symbol, str):
        errors.append("Symbol must be a non-empty string")
    
    if side not in ['buy', 'sell']:
        errors.append("Side must be 'buy' or 'sell'")
    
    if not isinstance(size, (int, float)) or size <= 0:
        errors.append("Size must be a positive number")
    
    # Size constraints
    if size < min_size:
        errors.append(f"Order size {size} below minimum {min_size}")
    
    if size > max_size:
        errors.append(f"Order size {size} above maximum {max_size}")
    
    return len(errors) == 0, errors


def get_prevalidation_summary() -> Dict[str, Any]:
    """Get prevalidation configuration summary."""
    return {
        'min_spread_pct': 0.001,
        'max_spread_pct': 0.1,
        'min_tp_sl_distance': 0.005,
        'default_min_size': 0.001,
        'default_max_size': 1000000.0
    }


def log_prevalidation_report(validation_result: Tuple[bool, List[str]], 
                           order_details: Dict[str, Any]) -> None:
    """
    Log prevalidation report.
    
    Args:
        validation_result: Tuple of (is_valid, list_of_errors)
        order_details: Order details for logging
    """
    is_valid, errors = validation_result
    
    if is_valid:
        print(f"✅ Order validation passed: {order_details}")
    else:
        print(f"❌ Order validation failed: {order_details}")
        for error in errors:
            print(f"  - {error}")


def log_tp_sl_validation_report(validation_result: Tuple[bool, List[str]], 
                               tp_sl_details: Dict[str, Any]) -> None:
    """
    Log TP/SL validation report.
    
    Args:
        validation_result: Tuple of (is_valid, list_of_errors)
        tp_sl_details: TP/SL details for logging
    """
    is_valid, errors = validation_result
    
    if is_valid:
        print(f"✅ TP/SL validation passed: {tp_sl_details}")
    else:
        print(f"❌ TP/SL validation failed: {tp_sl_details}")
        for error in errors:
            print(f"  - {error}")


def get_order_prevalidator() -> OrderPrevalidator:
    """Get order prevalidator instance."""
    return OrderPrevalidator()


def create_prevalidator_from_instrument(instrument: Dict[str, Any]) -> OrderPrevalidator:
    """Create a prevalidator instance from instrument data."""
    return OrderPrevalidator()


def validate_order(symbol: str, side: str, size: float, price: float, order_type: str,
                  tp_price: Optional[float] = None, sl_price: Optional[float] = None) -> Tuple[bool, List[str]]:
    """Validate order using the global prevalidator."""
    prevalidator = get_order_prevalidator()
    return prevalidator.validate_order(symbol, side, size, price, order_type, tp_price, sl_price)


__all__ = [
    "ValidationError",
    "OrderPrevalidator",
    "validate_tp_sl_prices",
    "validate_order_price_policy",
    "validate_order_size_constraints",
    "validate_bracket_order",
    "validate_market_order_params",
    "get_prevalidation_summary",
    "log_prevalidation_report",
    "log_tp_sl_validation_report",
    "get_order_prevalidator",
    "create_prevalidator_from_instrument",
    "validate_order",
]
