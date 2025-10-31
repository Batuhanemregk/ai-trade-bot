"""
Price and size quantization utilities.
Handles tick size, lot size, and minimum quantity constraints.
"""

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, Union, List
from loguru import logger


class QuantizationConfig:
    """Configuration for quantization rules."""
    
    def __init__(self, tick_size: float = 0.01, lot_size: float = 0.01, 
                 min_size: float = 0.001, contract_value: float = 1.0):
        self.tick_size = tick_size
        self.lot_size = lot_size
        self.min_size = min_size
        self.contract_value = contract_value
    
    def __repr__(self):
        return (f"QuantizationConfig(tick_size={self.tick_size}, "
                f"lot_size={self.lot_size}, min_size={self.min_size}, "
                f"contract_value={self.contract_value})")


class Quantizer:
    """Handles price and size quantization according to exchange constraints."""
    
    def __init__(self, config: QuantizationConfig):
        self.config = config
    
    def quantize_price(self, price: Union[float, Decimal]) -> float:
        """
        Quantize price to nearest valid tick size.
        
        Args:
            price: Raw price value
        
        Returns:
            Quantized price
        """
        if isinstance(price, Decimal):
            price = float(price)
        
        if self.config.tick_size <= 0:
            return price
        
        # Use Decimal for precise arithmetic
        price_decimal = Decimal(str(price))
        tick_decimal = Decimal(str(self.config.tick_size))
        
        # Round to nearest tick
        ticks = (price_decimal / tick_decimal).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        result = float(ticks * tick_decimal)
        
        return result
    
    def quantize_size(self, size: Union[float, Decimal]) -> float:
        """
        Quantize size to nearest valid lot size.
        
        Args:
            size: Raw size value
        
        Returns:
            Quantized size
        """
        if isinstance(size, Decimal):
            size = float(size)
        
        # Ensure lot_size is a float
        lot_size = self.config.lot_size
        if isinstance(lot_size, str):
            lot_size = float(lot_size)
        
        if lot_size <= 0:
            return size
        
        # Use Decimal for precise arithmetic
        size_decimal = Decimal(str(size))
        lot_decimal = Decimal(str(lot_size))
        
        # Round to nearest lot
        lots = (size_decimal / lot_decimal).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        result = float(lots * lot_decimal)
        
        return result
    
    def bump_to_min(self, size: Union[float, Decimal]) -> float:
        """
        Bump size up to minimum if below threshold.
        
        Args:
            size: Raw size value
        
        Returns:
            Size bumped to minimum if needed
        """
        if isinstance(size, Decimal):
            size = float(size)
        
        if size < self.config.min_size:
            return self.config.min_size
        return size


# Global quantizer instance
_quantizer: Optional[Quantizer] = None


def get_quantizer(config: Optional[QuantizationConfig] = None) -> Quantizer:
    """
    Get the global Quantizer instance. If config is provided, it will update the global instance.
    """
    global _quantizer
    if _quantizer is None or config is not None:
        if config is None and _quantizer is not None:
            # If no new config, but quantizer exists, use its config
            config = _quantizer.config
        elif config is None:
            # Default config if no quantizer and no config provided
            config = QuantizationConfig()
        _quantizer = Quantizer(config)
    return _quantizer


def quantize_price(symbol_or_price: Union[str, float], price_or_tick_size: Union[float, None] = None, client=None) -> float:
    """
    Quantize price with flexible signature.
    
    Args:
        symbol_or_price: Symbol name (e.g., "BTC-USDT") or price value
        price_or_tick_size: Price value (if first arg is symbol) or tick_size (if first arg is price)
    
    Returns:
        Quantized price
    """
    if symbol_or_price is None:
        raise ValueError("First argument cannot be None")
    
    if isinstance(symbol_or_price, str):
        # New signature: quantize_price("BTC-USDT", 30000.0)
        symbol = symbol_or_price
        price = price_or_tick_size
        
        if price is None:
            raise ValueError("Price cannot be None")
        
        # Validate symbol format
        if not symbol or "-" not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        # Use client precision if available
        if client:
            try:
                ccxt_symbol = _norm_symbol(symbol, client)
                return float(client.price_to_precision(ccxt_symbol, price))
            except Exception as e:
                logger.warning(f"Could not use client precision for {symbol}: {e}")
        
        # Use fallback tick sizes (okx_client_facade deleted)
        if "BTC" in symbol:
            tick_size = 0.1
        elif "ETH" in symbol:
            tick_size = 0.01
        elif symbol in ["BTC-USDT", "ETH-USDT", "BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
            tick_size = 0.1 if "BTC" in symbol else 0.01
        else:
            tick_size = 0.01  # Default fallback
        
        config = QuantizationConfig(tick_size=tick_size)
        return Quantizer(config).quantize_price(price)
    else:
        # Legacy signature: quantize_price(30000.0, 0.1)
        price = symbol_or_price
        tick_size = price_or_tick_size
        
        if tick_size is None:
            raise ValueError("Tick size cannot be None")
        
        config = QuantizationConfig(tick_size=tick_size)
        return Quantizer(config).quantize_price(price)


def quantize_size(symbol_or_size: Union[str, float], size_or_lot_size: Union[float, None] = None, client=None) -> float:
    """
    Quantize size with flexible signature.
    
    Args:
        symbol_or_size: Symbol name (e.g., "BTC-USDT") or size value
        size_or_lot_size: Size value (if first arg is symbol) or lot_size (if first arg is size)
    
    Returns:
        Quantized size
    """
    if symbol_or_size is None:
        raise ValueError("First argument cannot be None")
    
    if isinstance(symbol_or_size, str):
        # New signature: quantize_size("BTC-USDT", 0.1)
        symbol = symbol_or_size
        size = size_or_lot_size
        
        if size is None:
            raise ValueError("Size cannot be None")
        
        # Ensure size is a float
        if isinstance(size, str):
            size = float(size)
        
        # Validate symbol format
        if not symbol or "-" not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        # Use new robust min requirements if client is provided
        if client:
            return ensure_min_requirements(symbol, size, price=None, client=client)
        
        # Fallback to old logic if no client
        # Use fallback lot sizes (okx_client_facade deleted)
        if "BTC" in symbol:
            lot_size = 0.0001
            min_size = 0.0001
        elif "ETH" in symbol:
            lot_size = 0.001
            min_size = 0.001
        elif symbol in ["BTC-USDT", "ETH-USDT", "BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
            lot_size = 0.0001 if "BTC" in symbol else 0.001
            min_size = 0.0001 if "BTC" in symbol else 0.001
        else:
            lot_size = 0.001  # Default fallback
            min_size = 0.001   # Default fallback
        
        config = QuantizationConfig(lot_size=lot_size, min_size=min_size)
        quantized_size = Quantizer(config).quantize_size(size)
        
        # Apply minimum size enforcement
        if quantized_size < min_size:
            quantized_size = min_size
            
        return quantized_size
    else:
        # Legacy signature: quantize_size(0.1, 0.0001)
        size = symbol_or_size
        lot_size = size_or_lot_size
        
        if lot_size is None:
            raise ValueError("Lot size cannot be None")
        
        config = QuantizationConfig(lot_size=lot_size)
        return Quantizer(config).quantize_size(size)


def bump_to_min_size(symbol_or_size: Union[str, float], size_or_min_size: Union[float, None] = None, side: str = None) -> float:
    """
    Bump size to minimum with flexible signature.
    
    Args:
        symbol_or_size: Symbol name (e.g., "BTC-USDT") or size value
        size_or_min_size: Size value (if first arg is symbol) or min_size (if first arg is size)
        side: Trading side ('buy' or 'sell') - for compatibility, not used in logic
    
    Returns:
        Size bumped to minimum if needed
    """
    if isinstance(symbol_or_size, str):
        # New signature: bump_to_min_size("BTC-USDT", 0.00005, "buy")
        symbol = symbol_or_size
        size = size_or_min_size
        
        # Use fallback min sizes (adapters module not available)
        if "BTC" in symbol:
            min_size = 0.0001
        elif "ETH" in symbol:
            min_size = 0.001
        else:
            min_size = 0.001
        
        # Ensure size is a float
        if isinstance(size, str):
            size = float(size)
        
        if size < min_size:
            return min_size
        return size
    else:
        # Legacy signature: bump_to_min_size(0.00005, 0.0001)
        size = symbol_or_size
        min_size = size_or_min_size
        if size < min_size:
            return min_size
        return size


def should_skip_order(size: float, min_size: float) -> bool:
    """
    Check if order should be skipped due to size constraints.
    
    Args:
        size: Order size
        min_size: Minimum order size
    
    Returns:
        True if order should be skipped, False otherwise
    """
    return size < min_size


def check_min_quantize_guard(size: float, min_size: float, min_notional: float, 
                           price: float, mode: str = "PAPER") -> Tuple[bool, str]:
    """
    Check min/quantize guard and return skip decision with reason.
    
    Args:
        size: Order size
        min_size: Minimum order size
        min_notional: Minimum notional value
        price: Order price
        mode: Trading mode (LIVE/PAPER/DRY-RUN)
    
    Returns:
        Tuple of (should_skip, reason)
    """
    # Check size constraints
    if size < min_size:
        return True, "below_min_size"
    
    # Check notional constraints
    notional_value = size * price
    if notional_value < min_notional:
        return True, "below_min_notional"
    
    return False, "ok"


def calculate_contract_size(size: float, contract_value: float) -> float:
    """Calculate contract size from position size."""
    return size / contract_value


def calculate_dynamic_size(base_size: float, price: float, target_notional: float) -> float:
    """Calculate dynamic size based on target notional value."""
    if price <= 0:
        return base_size
    return target_notional / price


def validate_quantization_constraints(price: float, size: float, 
                                    tick_size: float, lot_size: float, min_size: float) -> Tuple[bool, List[str]]:
    """Validate quantization constraints."""
    errors = []
    
    if tick_size > 0 and abs(price % tick_size) > 1e-10:
        errors.append(f"Price {price} not aligned with tick size {tick_size}")
    
    if lot_size > 0 and abs(size % lot_size) > 1e-10:
        errors.append(f"Size {size} not aligned with lot size {lot_size}")
    
    if size < min_size:
        errors.append(f"Size {size} below minimum {min_size}")
    
    return len(errors) == 0, errors


def get_quantization_info(tick_size: float, lot_size: float, min_size: float) -> Dict[str, Any]:
    """Get quantization information."""
    return {
        'tick_size': tick_size,
        'lot_size': lot_size,
        'min_size': min_size,
        'price_precision': _get_precision(tick_size),
        'size_precision': _get_precision(lot_size)
    }


def apply_quantization_corrections(price: float, size: float, 
                                 tick_size: float, lot_size: float, min_size: float) -> Tuple[float, float]:
    """Apply quantization corrections to price and size."""
    corrected_price = quantize_price(price, tick_size)
    corrected_size = quantize_size(size, lot_size)
    
    if corrected_size < min_size:
        corrected_size = min_size
    
    return corrected_price, corrected_size


def _get_precision(value: float) -> int:
    """Get precision (number of decimal places)."""
    if value <= 0:
        return 8
    
    value_str = f"{value:.10f}".rstrip('0')
    if '.' in value_str:
        return len(value_str.split('.')[1])
    return 0


def create_quantizer_from_instrument(instrument_info: Dict) -> Quantizer:
    """
    Create quantizer from instrument information.
    
    Args:
        instrument_info: Dictionary with tickSz, lotSz, minSz, ctVal
    
    Returns:
        Configured Quantizer instance
    """
    config = QuantizationConfig(
        tick_size=float(instrument_info.get('tickSz', 0.01)),
        lot_size=float(instrument_info.get('lotSz', 0.01)),
        min_size=float(instrument_info.get('minSz', 0.001)),
        contract_value=float(instrument_info.get('ctVal', 1.0))
    )
    return Quantizer(config)


def calculate_notional_value(size: float, price: float, contract_value: float = 1.0) -> float:
    """
    Calculate notional value of a position.
    
    Args:
        size: Position size
        price: Price per unit
        contract_value: Contract value multiplier
    
    Returns:
        Notional value
    """
    return size * price * contract_value


def round_decimal(value: Union[float, Decimal], places: int = 8) -> Decimal:
    """
    Round decimal value to specified places.
    
    Args:
        value: Value to round
        places: Number of decimal places
    
    Returns:
        Rounded Decimal value
    """
    if isinstance(value, float):
        value = Decimal(str(value))
    
    return value.quantize(Decimal('0.1') ** places, rounding=ROUND_HALF_UP)


def _norm_symbol(symbol: str, client=None) -> str:
    """Normalize symbol to CCXT format."""
    if '/' in symbol:
        # Already CCXT format
        return symbol
    else:
        # OKX format, convert to CCXT
        from execution.okx_symbol import okx_to_ccxt_symbol
        return okx_to_ccxt_symbol(symbol)


def get_market(symbol: str, client) -> dict:
    """Get market info from CCXT client."""
    if not client:
        raise ValueError("CCXT client is required")
    
    ccxt_symbol = _norm_symbol(symbol, client)
    
    # Ensure markets are loaded
    if not hasattr(client, 'markets') or not client.markets:
        client.load_markets()
    
    return client.market(ccxt_symbol)


def ensure_min_requirements(symbol: str, amount: float, price: Optional[float] = None, client=None) -> float:
    """Ensure amount meets exchange minimum requirements."""
    try:
        ccxt_symbol = _norm_symbol(symbol, client)
        m = get_market(ccxt_symbol, client)
        
        # Get minimum amount
        min_amt = m.get('limits', {}).get('amount', {}).get('min') or m.get('minAmount') or 0
        lot = m.get('lot')  # sometimes exists
        prec_amt = (m.get('precision', {}) or {}).get('amount')
        
        q_amt = max(amount, float(min_amt or 0.0))
        
        # Enforce minimum cost if price is provided or min_cost exists
        if price is not None or m.get('limits', {}).get('cost', {}).get('min'):
            try:
                last = price or (client.fetch_ticker(ccxt_symbol).get('last') or 
                               client.price_to_precision(ccxt_symbol, 0) or 0)
                min_cost = m.get('limits', {}).get('cost', {}).get('min')
                
                if min_cost and last:
                    need = float(min_cost) / float(last)
                    if q_amt * float(last) < float(min_cost):
                        q_amt = max(q_amt, need)
            except Exception as e:
                logger.warning(f"Could not enforce min cost for {symbol}: {e}")
        
        # Final quantization
        if prec_amt is not None:
            q_amt = float(client.amount_to_precision(ccxt_symbol, q_amt))
        
        if lot:
            if q_amt < lot:
                q_amt = lot
            else:
                q_amt = math.floor(q_amt / lot) * lot
                if q_amt < min_amt:
                    q_amt = min_amt
        
        # Defensive logging for amount < 1 cases
        if q_amt < 1 and min_amt == 1:
            logger.warning(f"Forcing amount to 1 for {symbol} (was {q_amt}, min_amt={min_amt})")
            q_amt = 1.0
        
        return q_amt
        
    except Exception as e:
        logger.error(f"Error ensuring min requirements for {symbol}: {e}")
        return amount

