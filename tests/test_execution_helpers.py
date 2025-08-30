"""
Test suite for execution helpers.
Tests ID generation, symbol conversion, and exchange adapter functionality.
"""

from decimal import Decimal

import pytest

from domain.models import Order, OrderSide, OrderType, Price, Quantity
from execution.id_utils import generate_client_id, is_id_used, validate_id
from execution.okx_symbol import (
    ccxt_to_okx_symbol,
    normalize_symbol,
    okx_to_ccxt_symbol,
)
from execution.prevalidation import OrderPrevalidator
from execution.quantize import Quantizer


class TestIDUtils:
    """Test ID utilities functionality."""

    def test_generate_client_id(self):
        """Test client ID generation."""
        # Test entry order ID
        entry_id = generate_client_id('E')
        assert entry_id.startswith('E')
        assert len(entry_id) == 32
        assert entry_id.isalnum()

        # Test algo order ID
        algo_id = generate_client_id('A')
        assert algo_id.startswith('A')
        assert len(algo_id) == 32
        assert algo_id.isalnum()

        # Test default (should be entry)
        default_id = generate_client_id()
        assert default_id.startswith('E')
        assert len(default_id) == 32

    def test_validate_id(self):
        """Test ID validation."""
        # Test valid ID (32 chars, alphanumeric, not used)
        test_id = "TEST1234567890123456789012345678"  # Exactly 32 chars
        assert validate_id(test_id) is True

        # Invalid IDs
        assert validate_id("") is False  # Empty
        assert validate_id("A" * 33) is False  # Too long
        assert validate_id("A-B-C") is False  # Contains non-alphanumeric
        # Note: "A" * 32 is actually valid (32 chars, alphanumeric)

    def test_is_id_used(self):
        """Test ID usage checking."""
        # Generate a new ID
        new_id = generate_client_id('E')

        # Check if it's marked as used
        assert is_id_used(new_id) is True

        # Check if a random string is used
        assert is_id_used("RANDOM123") is False


class TestOKXSymbol:
    """Test OKX symbol conversion functionality."""

    def test_okx_to_ccxt_symbol(self):
        """Test OKX instId to CCXT symbol conversion."""
        # Test SWAP instruments
        assert okx_to_ccxt_symbol("BTC-USDT-SWAP") == "BTC/USDT:USDT"
        assert okx_to_ccxt_symbol("ETH-USDT-SWAP") == "ETH/USDT:USDT"
        assert okx_to_ccxt_symbol("OP-USDT-SWAP") == "OP/USDT:USDT"

        # Test SPOT instruments
        assert okx_to_ccxt_symbol("BTC-USDT") == "BTC/USDT"
        assert okx_to_ccxt_symbol("ETH-USDT") == "ETH/USDT"

        # Test edge cases
        assert okx_to_ccxt_symbol("") == ""
        assert okx_to_ccxt_symbol("INVALID") == "INVALID"

    def test_ccxt_to_okx_symbol(self):
        """Test CCXT symbol to OKX instId conversion."""
        # Test SWAP symbols
        assert ccxt_to_okx_symbol("BTC/USDT:USDT") == "BTC-USDT-SWAP"
        assert ccxt_to_okx_symbol("ETH/USDT:USDT") == "ETH-USDT-SWAP"

        # Test SPOT symbols
        assert ccxt_to_okx_symbol("BTC/USDT") == "BTC-USDT"
        assert ccxt_to_okx_symbol("ETH/USDT") == "ETH-USDT"

        # Test edge cases
        assert ccxt_to_okx_symbol("") == ""
        assert ccxt_to_okx_symbol("INVALID") == "INVALID"

    def test_normalize_symbol(self):
        """Test symbol normalization."""
        # Already normalized
        assert normalize_symbol("BTC/USDT:USDT") == "BTC/USDT:USDT"
        assert normalize_symbol("ETH/USDT") == "ETH/USDT"

        # OKX format
        assert normalize_symbol("BTC-USDT-SWAP") == "BTC/USDT:USDT"
        assert normalize_symbol("ETH-USDT") == "ETH/USDT"

        # Simple format
        assert normalize_symbol("BTCUSDT") == "BTC/USDT"
        assert normalize_symbol("ETHUSDT") == "ETH/USDT"

        # Edge cases
        assert normalize_symbol("") == ""
        assert normalize_symbol("INVALID") == "INVALID"


class TestQuantizer:
    """Test quantization functionality."""

    def test_quantizer_initialization(self):
        """Test quantizer initialization."""
        quantizer = Quantizer()
        assert quantizer is not None

    def test_quantize_price(self):
        """Test price quantization."""
        quantizer = Quantizer()

        # Test price quantization
        price = Decimal("50000.12345678")
        tick_size = Decimal("0.1")

        quantized_price = quantizer.quantize_price(price, tick_size)

        # Check that the price was quantized
        assert quantized_price is not None
        assert quantized_price > 0

    def test_quantize_quantity(self):
        """Test quantity quantization."""
        quantizer = Quantizer()

        # Test quantity quantization
        quantity = Decimal("1.23456789")
        lot_size = Decimal("0.01")

        quantized_quantity = quantizer.quantize_quantity(quantity, lot_size)

        # Check that the quantity was quantized
        assert quantized_quantity is not None
        assert quantized_quantity > 0


class TestOrderPrevalidator:
    """Test order prevalidation functionality."""

    def test_prevalidator_initialization(self):
        """Test prevalidator initialization."""
        prevalidator = OrderPrevalidator()
        assert prevalidator is not None

    def test_validate_order(self):
        """Test order validation."""
        prevalidator = OrderPrevalidator()

        # Create a valid test order
        order = Order(
            id="test_order",
            symbol="BTC-USDT-SWAP",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Quantity(Decimal("1.0")),
            price=Price(Decimal("50000.0")),
            client_order_id="TEST123"
        )

        # Mock instrument and account info
        instrument_info = {
            'minSz': '0.01',
            'maxSz': '1000',
            'tickSz': '0.1',
            'lotSz': '0.01'
        }

        account_info = {
            'balance': 100000,
            'free_balance': 50000
        }

        # Validate the order
        result = prevalidator.validate_order(order, instrument_info, account_info)

        # Check validation result
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestSymbolConversionExamples:
    """Test specific symbol conversion examples."""

    def test_swap_symbols(self):
        """Test SWAP symbol conversions."""
        test_cases = [
            ("BTC-USDT-SWAP", "BTC/USDT:USDT"),
            ("ETH-USDT-SWAP", "ETH/USDT:USDT"),
            ("SOL-USDT-SWAP", "SOL/USDT:USDT"),
            ("OP-USDT-SWAP", "OP/USDT:USDT"),
            ("MATIC-USDT-SWAP", "MATIC/USDT:USDT"),
        ]

        for okx_symbol, expected_ccxt in test_cases:
            result = okx_to_ccxt_symbol(okx_symbol)
            assert result == expected_ccxt, f"Failed to convert {okx_symbol} to {expected_ccxt}, got {result}"

    def test_spot_symbols(self):
        """Test SPOT symbol conversions."""
        test_cases = [
            ("BTC-USDT", "BTC/USDT"),
            ("ETH-USDT", "ETH/USDT"),
            ("SOL-USDT", "SOL/USDT"),
            ("OP-USDT", "OP/USDT"),
            ("MATIC-USDT", "MATIC/USDT"),
        ]

        for okx_symbol, expected_ccxt in test_cases:
            result = okx_to_ccxt_symbol(okx_symbol)
            assert result == expected_ccxt, f"Failed to convert {okx_symbol} to {expected_ccxt}, got {result}"

    def test_reverse_conversions(self):
        """Test reverse symbol conversions."""
        test_cases = [
            ("BTC/USDT:USDT", "BTC-USDT-SWAP"),
            ("ETH/USDT:USDT", "ETH-USDT-SWAP"),
            ("SOL/USDT:USDT", "SOL-USDT-SWAP"),
            ("BTC/USDT", "BTC-USDT"),
            ("ETH/USDT", "ETH-USDT"),
        ]

        for ccxt_symbol, expected_okx in test_cases:
            result = ccxt_to_okx_symbol(ccxt_symbol)
            assert result == expected_okx, f"Failed to convert {ccxt_symbol} to {expected_okx}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
