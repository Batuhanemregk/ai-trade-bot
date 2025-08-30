"""
OKX symbol normalization and mapping utilities.
Handles instId ↔ CCXT symbol conversion and route-specific normalization.
"""

import re
from typing import Optional


def okx_to_ccxt_symbol(inst_id: str) -> str:
    """
    Convert OKX instId to CCXT symbol format.
    
    Examples:
        OP-USDT-SWAP -> OP/USDT:USDT
        BTC-USDT-SWAP -> BTC/USDT:USDT
        ETH-USDT -> ETH/USDT
        BTC-USDT-240628 -> BTC/USDT:USDT-240628
    """
    if not inst_id:
        raise ValueError("instId cannot be empty")
    
    # Handle SWAP contracts
    if inst_id.endswith('-SWAP'):
        base_quote = inst_id[:-5]  # Remove -SWAP suffix
        if '-' in base_quote:
            base, quote = base_quote.rsplit('-', 1)
            return f"{base}/{quote}:{quote}"
    
    # Handle futures contracts (e.g., BTC-USDT-240628)
    if '-' in inst_id and not inst_id.endswith('-SWAP'):
        parts = inst_id.split('-')
        if len(parts) >= 3:
            # Check if last part looks like a date (YYYYMMDD) or contract code
            last_part = parts[-1]
            if len(last_part) == 6 and last_part.isdigit():  # YYYYMMDD format
                base = parts[0]
                quote = parts[1]
                contract = '-'.join(parts[2:])  # Keep all remaining parts
                return f"{base}/{quote}:{quote}-{contract}"
    
    # Handle spot trading
    if '-' in inst_id:
        base, quote = inst_id.rsplit('-', 1)
        return f"{base}/{quote}"
    
    # Handle single symbol (fallback)
    return inst_id


def ccxt_to_okx_symbol(ccxt_symbol: str) -> str:
    """
    Convert CCXT symbol to OKX instId format.
    
    Examples:
        OP/USDT:USDT -> OP-USDT-SWAP
        BTC/USDT:USDT -> BTC-USDT-SWAP
        ETH/USDT -> ETH-USDT
    """
    if not ccxt_symbol:
        raise ValueError("CCXT symbol cannot be empty")
    
    # Handle perpetual contracts
    if ':' in ccxt_symbol:
        base_quote, contract = ccxt_symbol.split(':', 1)
        if '/' in base_quote:
            base, quote = base_quote.split('/', 1)
            # Check if contract is just "USDT" (SWAP) or has additional parts (futures)
            if contract == "USDT":
                return f"{base}-{quote}-SWAP"
            elif contract.startswith("USDT-"):
                # Futures contract (e.g., USDT-240628) -> BTC-USDT-240628
                contract_part = contract[5:]  # Remove "USDT-" prefix
                return f"{base}-{quote}-{contract_part}"
            else:
                # Other contract types
                return f"{base}-{quote}-{contract}"
    
    # Handle spot trading
    if '/' in ccxt_symbol:
        base, quote = ccxt_symbol.split('/', 1)
        return f"{base}-{quote}"
    
    # Handle single symbol (fallback)
    return ccxt_symbol


def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol to standard format.
    
    Args:
        symbol: Input symbol (OKX instId or CCXT format)
    
    Returns:
        Normalized symbol in CCXT format
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    
    if symbol is None:
        raise ValueError("Symbol cannot be None")
    
    # Basic validation - symbol should have some structure
    if not any(c in symbol for c in ['-', '/', ':']):
        raise ValueError("Invalid symbol format")
    
    # Check for too many parts in OKX format
    if '-' in symbol:
        parts = symbol.split('-')
        if len(parts) > 3:
            raise ValueError("Invalid symbol format: too many parts")
    
    return normalize_symbol_for_route(symbol, 'ccxt')


def normalize_symbol_for_route(symbol: str, route: str = 'ccxt') -> str:
    """
    Normalize symbol for specific execution route.
    
    Args:
        symbol: Input symbol (OKX instId or CCXT format)
        route: Execution route ('ccxt', 'rest', 'websocket')
    
    Returns:
        Normalized symbol for the specified route
    """
    if route == 'ccxt':
        # Convert OKX instId to CCXT format
        if ':' in symbol:
            # Already CCXT format with contract (e.g., BTC/USDT:USDT-240628)
            return symbol
        elif '-' in symbol and not symbol.endswith('-SWAP'):
            # Likely OKX format, convert to CCXT
            return okx_to_ccxt_symbol(symbol)
        elif symbol.endswith('-SWAP'):
            # OKX SWAP format, convert to CCXT
            return okx_to_ccxt_symbol(symbol)
        else:
            # Already CCXT format or single symbol
            return symbol
    
    elif route == 'rest':
        # Convert CCXT to OKX format for REST API
        if '/' in symbol:
            return ccxt_to_okx_symbol(symbol)
        else:
            # Already OKX format or single symbol
            return symbol
    
    else:
        # Default: return as-is
        return symbol


def convert_to_ccxt(symbol: str) -> str:
    """Convert OKX symbol to CCXT format (alias for okx_to_ccxt_symbol)."""
    return okx_to_ccxt_symbol(symbol)


def convert_from_ccxt(symbol: str) -> str:
    """Convert CCXT symbol to OKX format (alias for ccxt_to_okx_symbol)."""
    return ccxt_to_okx_symbol(symbol)


def is_swap_contract(symbol: str) -> bool:
    """Check if symbol represents a SWAP contract."""
    return symbol.endswith('-SWAP') or ':' in symbol


def is_spot_symbol(symbol: str) -> bool:
    """Check if symbol represents spot trading."""
    return not is_swap_contract(symbol)


def extract_base_quote(symbol: str) -> tuple[str, str]:
    """
    Extract base and quote from symbol.
    
    Returns:
        Tuple of (base, quote)
    """
    # Handle OKX format
    if '-' in symbol:
        if symbol.endswith('-SWAP'):
            base_quote = symbol[:-5]
            if '-' in base_quote:
                return base_quote.rsplit('-', 1)
        else:
            return symbol.rsplit('-', 1)
    
    # Handle CCXT format
    if '/' in symbol:
        if ':' in symbol:
            base_quote = symbol.split(':', 1)[0]
            return base_quote.split('/', 1)
        else:
            return symbol.split('/', 1)
    
    # Single symbol (fallback)
    return symbol, ""


def validate_symbol_format(symbol: str, expected_format: str = 'auto') -> bool:
    """
    Validate symbol format.
    
    Args:
        symbol: Symbol to validate
        expected_format: Expected format ('okx', 'ccxt', 'auto')
    
    Returns:
        True if valid, False otherwise
    """
    if expected_format == 'auto':
        # Auto-detect format
        if '-' in symbol:
            return True  # OKX format
        elif '/' in symbol:
            return True  # CCXT format
        else:
            return len(symbol) > 0  # Single symbol
    
    elif expected_format == 'okx':
        return '-' in symbol
    
    elif expected_format == 'ccxt':
        return '/' in symbol
    
    return False


__all__ = [
    "okx_to_ccxt_symbol",
    "ccxt_to_okx_symbol",
    "normalize_symbol",
    "normalize_symbol_for_route",
    "convert_to_ccxt",
    "convert_from_ccxt",
    "is_swap_contract",
    "is_spot_symbol",
    "extract_base_quote",
    "validate_symbol_format",
]
