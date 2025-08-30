"""
Unit tests for OKX symbol utilities.
Tests normalize/convert between OKX and CCXT formats.
"""

import pytest

from execution.okx_symbol import normalize_symbol, convert_to_ccxt, convert_from_ccxt


@pytest.mark.core
class TestOKXSymbol:
    """Test OKX symbol conversion functions."""
    
    def test_normalize_symbol_spot(self):
        """Test spot symbol normalization."""
        # OKX format to normalized
        assert normalize_symbol("BTC-USDT") == "BTC/USDT"
        assert normalize_symbol("ETH-USDT") == "ETH/USDT"
        assert normalize_symbol("ADA-USDT") == "ADA/USDT"
        
        # Already normalized should remain unchanged
        assert normalize_symbol("BTC/USDT") == "BTC/USDT"
        assert normalize_symbol("ETH/USDT") == "ETH/USDT"
    
    def test_normalize_symbol_swap(self):
        """Test swap symbol normalization."""
        # OKX swap format to normalized
        assert normalize_symbol("BTC-USDT-SWAP") == "BTC/USDT:USDT"
        assert normalize_symbol("ETH-USDT-SWAP") == "ETH/USDT:USDT"
        assert normalize_symbol("ADA-USDT-SWAP") == "ADA/USDT:USDT"
        
        # Already normalized should remain unchanged
        assert normalize_symbol("BTC/USDT:USDT") == "BTC/USDT:USDT"
        assert normalize_symbol("ETH/USDT:USDT") == "ETH/USDT:USDT"
    
    def test_normalize_symbol_futures(self):
        """Test futures symbol normalization."""
        # OKX futures format to normalized
        assert normalize_symbol("BTC-USDT-240628") == "BTC/USDT:USDT-240628"
        assert normalize_symbol("ETH-USDT-240628") == "ETH/USDT:USDT-240628"
        
        # Already normalized should remain unchanged
        assert normalize_symbol("BTC/USDT:USDT-240628") == "BTC/USDT:USDT-240628"
    
    def test_convert_to_ccxt_spot(self):
        """Test conversion from OKX to CCXT format."""
        # Spot symbols
        assert convert_to_ccxt("BTC-USDT") == "BTC/USDT"
        assert convert_to_ccxt("ETH-USDT") == "ETH/USDT"
        
        # Swap symbols
        assert convert_to_ccxt("BTC-USDT-SWAP") == "BTC/USDT:USDT"
        assert convert_to_ccxt("ETH-USDT-SWAP") == "ETH/USDT:USDT"
        
        # Futures symbols
        assert convert_to_ccxt("BTC-USDT-240628") == "BTC/USDT:USDT-240628"
    
    def test_convert_from_ccxt_spot(self):
        """Test conversion from CCXT to OKX format."""
        # Spot symbols
        assert convert_from_ccxt("BTC/USDT") == "BTC-USDT"
        assert convert_from_ccxt("ETH/USDT") == "ETH-USDT"
        
        # Swap symbols
        assert convert_from_ccxt("BTC/USDT:USDT") == "BTC-USDT-SWAP"
        assert convert_from_ccxt("ETH/USDT:USDT") == "ETH-USDT-SWAP"
        
        # Futures symbols
        assert convert_from_ccxt("BTC/USDT:USDT-240628") == "BTC-USDT-240628"
    
    def test_idempotent_normalization(self):
        """Test that normalization is idempotent."""
        symbols = [
            "BTC-USDT",
            "ETH-USDT-SWAP",
            "ADA-USDT-240628",
            "BTC/USDT",
            "ETH/USDT:USDT",
            "ADA/USDT:USDT-240628"
        ]
        
        for symbol in symbols:
            normalized = normalize_symbol(symbol)
            # Normalizing again should give same result
            assert normalize_symbol(normalized) == normalized
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty string
        with pytest.raises(ValueError):
            normalize_symbol("")
        
        # None value
        with pytest.raises(ValueError):
            normalize_symbol(None)
        
        # Invalid format
        with pytest.raises(ValueError):
            normalize_symbol("INVALID")
        
        # Too many parts
        with pytest.raises(ValueError):
            normalize_symbol("BTC-USDT-EXTRA-INVALID")
    
    def test_symbol_roundtrip(self):
        """Test roundtrip conversion OKX ↔ CCXT."""
        okx_symbols = [
            "BTC-USDT",
            "ETH-USDT-SWAP",
            "ADA-USDT-240628"
        ]
        
        for okx_symbol in okx_symbols:
            # OKX → CCXT → OKX
            ccxt_symbol = convert_to_ccxt(okx_symbol)
            back_to_okx = convert_from_ccxt(ccxt_symbol)
            assert back_to_okx == okx_symbol
            
            # CCXT → OKX → CCXT
            back_to_ccxt = convert_to_ccxt(back_to_okx)
            assert back_to_ccxt == ccxt_symbol
    
    def test_common_symbols(self):
        """Test common trading symbols."""
        common_pairs = [
            ("BTC-USDT", "BTC/USDT"),
            ("ETH-USDT", "ETH/USDT"),
            ("BNB-USDT", "BNB/USDT"),
            ("ADA-USDT", "ADA/USDT"),
            ("SOL-USDT", "SOL/USDT"),
            ("DOT-USDT", "DOT/USDT"),
            ("LINK-USDT", "LINK/USDT"),
            ("UNI-USDT", "UNI/USDT"),
            ("LTC-USDT", "LTC/USDT"),
            ("BCH-USDT", "BCH/USDT")
        ]
        
        for okx_symbol, expected_ccxt in common_pairs:
            assert normalize_symbol(okx_symbol) == expected_ccxt
            assert convert_to_ccxt(okx_symbol) == expected_ccxt
            assert convert_from_ccxt(expected_ccxt) == okx_symbol
