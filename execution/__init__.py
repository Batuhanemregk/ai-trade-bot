"""
Execution Module for AiBotBS
Handles order execution, symbol management, and trading utilities.
"""

from .okx_symbol import okx_to_ccxt_symbol, normalize_symbol_for_route
from .id_utils import generate_client_id, generate_algo_id, validate_client_id
from .quantize import (
    quantize_price, quantize_size, bump_to_min_size, should_skip_order,
    calculate_contract_size, calculate_dynamic_size, validate_quantization_constraints,
    get_quantization_info, apply_quantization_corrections
)
from .prevalidation import (
    validate_tp_sl_prices, validate_order_price_policy, validate_order_size_constraints,
    validate_market_order_params, get_prevalidation_summary,
    log_prevalidation_report
)


__all__ = [
    # Symbol management
    'okx_to_ccxt_symbol',
    'normalize_symbol_for_route',
    
    # ID utilities
    'generate_client_id',
    'generate_algo_id', 
    'validate_client_id',
    
    # Quantization
    'quantize_price',
    'quantize_size',
    'bump_to_min_size',
    'should_skip_order',
    'calculate_contract_size',
    'calculate_dynamic_size',
    'validate_quantization_constraints',
    'get_quantization_info',
    'apply_quantization_corrections',
    
    # Prevalidation
    'validate_tp_sl_prices',
    'validate_order_price_policy',
    'validate_order_size_constraints',
    'validate_market_order_params',
    'get_prevalidation_summary',
    'log_prevalidation_report',
    

]
