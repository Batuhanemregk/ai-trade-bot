"""
Unit tests for quantization functions.
Tests price and size quantization with tickSz and lotSz alignment.
"""

import pytest
from decimal import Decimal

from execution.quantize import quantize_price, quantize_size, bump_to_min_size


@pytest.mark.core
class TestQuantize:
    """Test quantization functions."""
    
    def test_quantize_price_btc_usdt(self, tmp_symbol_meta):
        """Test BTC-USDT price quantization."""
        meta = tmp_symbol_meta["BTC-USDT"]
        tick_sz = float(meta["tickSz"])
        
        # Test exact tick alignment
        assert quantize_price("BTC-USDT", 30000.0) == 30000.0
        assert quantize_price("BTC-USDT", 30000.1) == 30000.1
        
        # Test rounding to nearest tick
        assert quantize_price("BTC-USDT", 30000.05) == 30000.1  # Round up
        assert quantize_price("BTC-USDT", 30000.04) == 30000.0  # Round down
        
        # Test edge cases
        assert quantize_price("BTC-USDT", 0.0) == 0.0
        assert quantize_price("BTC-USDT", 100000.0) == 100000.0
    
    def test_quantize_price_eth_usdt(self, tmp_symbol_meta):
        """Test ETH-USDT price quantization."""
        meta = tmp_symbol_meta["ETH-USDT"]
        tick_sz = float(meta["tickSz"])
        
        # Test exact tick alignment
        assert quantize_price("ETH-USDT", 2000.0) == 2000.0
        assert quantize_price("ETH-USDT", 2000.01) == 2000.01
        
        # Test rounding to nearest tick
        assert quantize_price("ETH-USDT", 2000.005) == 2000.01  # Round up
        assert quantize_price("ETH-USDT", 2000.004) == 2000.0   # Round down
    
    def test_quantize_size_btc_usdt(self, tmp_symbol_meta):
        """Test BTC-USDT size quantization."""
        meta = tmp_symbol_meta["BTC-USDT"]
        lot_sz = float(meta["lotSz"])
        min_sz = float(meta["minSz"])
        
        # Test exact lot alignment
        assert quantize_size("BTC-USDT", 0.1) == 0.1
        assert quantize_size("BTC-USDT", 0.1001) == 0.1001
        
        # Test rounding to nearest lot
        assert quantize_size("BTC-USDT", 0.10005) == 0.1001  # Round up
        assert quantize_size("BTC-USDT", 0.10004) == 0.1     # Round down
        
        # Test minimum size enforcement
        assert quantize_size("BTC-USDT", 0.00005) == min_sz  # Below min
    
    def test_quantize_size_eth_usdt(self, tmp_symbol_meta):
        """Test ETH-USDT size quantization."""
        meta = tmp_symbol_meta["ETH-USDT"]
        lot_sz = float(meta["lotSz"])
        min_sz = float(meta["minSz"])
        
        # Test exact lot alignment
        assert quantize_size("ETH-USDT", 1.0) == 1.0
        assert quantize_size("ETH-USDT", 1.001) == 1.001
        
        # Test rounding to nearest lot
        assert quantize_size("ETH-USDT", 1.0005) == 1.001  # Round up
        assert quantize_size("ETH-USDT", 1.0004) == 1.0    # Round down
    
    def test_bump_to_min_size_long(self, tmp_symbol_meta):
        """Test bump_to_min_size for long positions."""
        meta = tmp_symbol_meta["BTC-USDT"]
        min_sz = float(meta["minSz"])
        
        # Test below minimum size
        assert bump_to_min_size("BTC-USDT", 0.00005, "buy") == min_sz
        
        # Test at minimum size
        assert bump_to_min_size("BTC-USDT", min_sz, "buy") == min_sz
        
        # Test above minimum size
        assert bump_to_min_size("BTC-USDT", 0.1, "buy") == 0.1
    
    def test_bump_to_min_size_short(self, tmp_symbol_meta):
        """Test bump_to_min_size for short positions."""
        meta = tmp_symbol_meta["BTC-USDT"]
        min_sz = float(meta["minSz"])
        
        # Test below minimum size
        assert bump_to_min_size("BTC-USDT", 0.00005, "sell") == min_sz
        
        # Test at minimum size
        assert bump_to_min_size("BTC-USDT", min_sz, "sell") == min_sz
        
        # Test above minimum size
        assert bump_to_min_size("BTC-USDT", 0.1, "sell") == 0.1
    
    def test_quantize_edge_cases(self):
        """Test quantization edge cases."""
        # Test None/None inputs
        with pytest.raises(ValueError):
            quantize_price(None, 100.0)
        
        with pytest.raises(ValueError):
            quantize_size(None, 1.0)
        
        # Test invalid symbol
        with pytest.raises(ValueError):
            quantize_price("INVALID-SYMBOL", 100.0)
        
        with pytest.raises(ValueError):
            quantize_size("INVALID-SYMBOL", 1.0)
