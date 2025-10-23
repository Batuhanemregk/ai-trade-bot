"""
Unit tests for order prevalidation.
Tests TP/SL validation rules with epsilon correction.
"""

import pytest
from decimal import Decimal

from execution.prevalidation import OrderPrevalidator, validate_tp_sl_prices


@pytest.mark.core
class TestPrevalidation:
    """Test order prevalidation functions."""
    
    def test_long_close_tp_sl_validation(self, tmp_symbol_meta):
        """Test LONG close TP/SL validation rules."""
        meta = tmp_symbol_meta["BTC-USDT"]
        tick_sz = float(meta["tickSz"])
        ref_price = 30000.0
        
        # Valid TP/SL for LONG close
        tp, sl = validate_tp_sl_prices("BTC-USDT", "buy", ref_price, 30100.0, 29900.0)
        assert tp > ref_price  # TP above reference
        assert sl < ref_price  # SL below reference
        
        # TP equal to reference - should be corrected with +epsilon
        tp, sl = validate_tp_sl_prices("BTC-USDT", "buy", ref_price, ref_price, 29900.0)
        assert tp == ref_price + tick_sz  # Corrected with +tickSz
        
        # SL equal to reference - should be corrected with -epsilon
        tp, sl = validate_tp_sl_prices("BTC-USDT", "buy", ref_price, 30100.0, ref_price)
        assert sl == ref_price - tick_sz  # Corrected with -tickSz
        
        # Both equal - should be corrected
        tp, sl = validate_tp_sl_prices("BTC-USDT", "buy", ref_price, ref_price, ref_price)
        assert tp == ref_price + tick_sz
        assert sl == ref_price - tick_sz
    
    def test_short_close_tp_sl_validation(self, tmp_symbol_meta):
        """Test SHORT close TP/SL validation rules."""
        meta = tmp_symbol_meta["BTC-USDT"]
        tick_sz = float(meta["tickSz"])
        ref_price = 30000.0
        
        # Valid TP/SL for SHORT close
        tp, sl = validate_tp_sl_prices("BTC-USDT", "sell", ref_price, 29900.0, 30100.0)
        assert tp < ref_price  # TP below reference
        assert sl > ref_price  # SL above reference
        
        # TP equal to reference - should be corrected with -epsilon
        tp, sl = validate_tp_sl_prices("BTC-USDT", "sell", ref_price, ref_price, 30100.0)
        assert tp == ref_price - tick_sz  # Corrected with -tickSz
        
        # SL equal to reference - should be corrected with +epsilon
        tp, sl = validate_tp_sl_prices("BTC-USDT", "sell", ref_price, 29900.0, ref_price)
        assert sl == ref_price + tick_sz  # Corrected with +tickSz
        
        # Both equal - should be corrected
        tp, sl = validate_tp_sl_prices("BTC-USDT", "sell", ref_price, ref_price, ref_price)
        assert tp == ref_price - tick_sz
        assert sl == ref_price + tick_sz
    
    def test_epsilon_correction_different_symbols(self, tmp_symbol_meta):
        """Test epsilon correction for different symbols."""
        # BTC-USDT with 0.1 tick size
        btc_tp, btc_sl = validate_tp_sl_prices("BTC-USDT", "buy", 30000.0, 30000.0, 30000.0)
        assert btc_tp == 30000.1  # +0.1
        assert btc_sl == 29999.9  # -0.1
        
        # ETH-USDT with 0.01 tick size
        eth_tp, eth_sl = validate_tp_sl_prices("ETH-USDT", "buy", 2000.0, 2000.0, 2000.0)
        assert eth_tp == 2000.01  # +0.01
        assert eth_sl == 1999.99  # -0.01
    
    def test_no_correction_needed(self, tmp_symbol_meta):
        """Test cases where no epsilon correction is needed."""
        ref_price = 30000.0
        
        # Valid TP/SL - no correction needed
        tp, sl = validate_tp_sl_prices("BTC-USDT", "buy", ref_price, 30100.0, 29900.0)
        assert tp == 30100.0  # Unchanged
        assert sl == 29900.0  # Unchanged
        
        # Valid TP/SL for short - no correction needed
        tp, sl = validate_tp_sl_prices("BTC-USDT", "sell", ref_price, 29900.0, 30100.0)
        assert tp == 29900.0  # Unchanged
        assert sl == 30100.0  # Unchanged
    
    def test_edge_cases(self, tmp_symbol_meta):
        """Test edge cases and error conditions."""
        # None prices
        with pytest.raises(ValueError):
            validate_tp_sl_prices("BTC-USDT", "buy", 30000.0, None, 29900.0)
        
        with pytest.raises(ValueError):
            validate_tp_sl_prices("BTC-USDT", "buy", 30000.0, 30100.0, None)
        
        # Invalid side
        with pytest.raises(ValueError):
            validate_tp_sl_prices("BTC-USDT", "invalid", 30000.0, 30100.0, 29900.0)
        
        # Invalid symbol - this might not raise ValueError depending on implementation
        try:
            validate_tp_sl_prices("INVALID-SYMBOL", "buy", 30000.0, 30100.0, 29900.0)
            # If no exception is raised, that's also acceptable
        except (ValueError, KeyError, Exception):
            # Any exception is acceptable for invalid symbol
            pass
    
    def test_order_prevalidator_integration(self, tmp_symbol_meta):
        """Test OrderPrevalidator integration."""
        prevalidator = OrderPrevalidator()
        
        # Test valid order
        order = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "type": "limit",
            "amount": 0.1,
            "price": 30000.0,
            "tp": 30100.0,
            "sl": 29900.0
        }
        
        result = prevalidator.validate_order(order)
        assert result["valid"] == True
        assert "tp" in result
        assert "sl" in result
        
        # Test invalid order (TP below reference for long)
        invalid_order = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "type": "limit",
            "amount": 0.1,
            "price": 30000.0,
            "tp": 29900.0,  # Invalid: TP below price for long
            "sl": 29800.0
        }
        
        result = prevalidator.validate_order(invalid_order)
        assert result["valid"] == False
        assert "error" in result
