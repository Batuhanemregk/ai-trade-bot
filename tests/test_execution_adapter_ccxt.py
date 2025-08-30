"""
Test suite for CCXT execution adapter.
Tests clientOrderId generation, symbol mapping, and error logging.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from domain.models import Order, OrderSide, OrderType, Price, Quantity
from execution.okx_symbol import okx_to_ccxt_symbol


class TestOKXExchangeAdapter:
    """Test the OKX exchange adapter functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "mode": "dry-run",
            "sandbox": True,
            "timeout": 30,
            "max_retries": 3
        }

    @pytest.fixture
    def mock_order(self):
        """Create a mock order for testing."""
        return Order(
            id="test_order_001",
            symbol="BTC-USDT-SWAP",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Quantity(Decimal("0.1")),
            price=Price(Decimal("50000.0")),
            client_order_id="test_client_id"
        )

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, mock_config):
        """Test adapter initialization."""
        adapter = OKXExchangeAdapter(mock_config)

        assert adapter.mode == "dry-run"
        assert adapter.sandbox is True
        assert adapter.default_timeout == 30
        assert adapter.max_retries == 3
        assert adapter._orders_sent == 0
        assert adapter._errors_count == 0

        await adapter.close()

    @pytest.mark.asyncio
    async def test_symbol_mapping_in_place_order(self, mock_config, mock_order):
        """Test that instId is properly mapped to CCXT symbol in place_order."""
        adapter = OKXExchangeAdapter(mock_config)

        # Mock the logger to capture log messages
        with patch.object(adapter.logger, 'info') as mock_logger:
            result = await adapter.place_order(mock_order)

            # Verify symbol mapping occurred
            assert result["client_order_id"] is not None
            assert result["status"] == "open"

            # Check that the log message contains symbol mapping info
            mock_logger.assert_called()
            log_call = mock_logger.call_args[0][0]

            # Verify log contains original and normalized symbols
            assert "original_symbol=BTC-USDT-SWAP" in log_call
            assert "symbol_norm=" in log_call

            # Verify the normalized symbol is correct
            expected_ccxt_symbol = okx_to_ccxt_symbol("BTC-USDT-SWAP")
            assert expected_ccxt_symbol == "BTC/USDT:USDT"

        await adapter.close()

    @pytest.mark.asyncio
    async def test_client_order_id_generation(self, mock_config, mock_order):
        """Test that clientOrderId is properly generated and set."""
        adapter = OKXExchangeAdapter(mock_config)

        result = await adapter.place_order(mock_order)

        # Verify clientOrderId is generated
        assert "client_order_id" in result
        client_order_id = result["client_order_id"]

        # Verify format: starts with 'E' and is 32 characters
        assert client_order_id.startswith('E')
        assert len(client_order_id) == 32
        assert client_order_id.isalnum()

        # Verify it's different from the input order's client_order_id
        assert client_order_id != mock_order.client_order_id

        await adapter.close()

    @pytest.mark.asyncio
    async def test_rich_logging_format(self, mock_config, mock_order):
        """Test that rich logging includes all required fields."""
        adapter = OKXExchangeAdapter(mock_config)

        with patch.object(adapter.logger, 'info') as mock_logger:
            await adapter.place_order(mock_order)

            # Verify log message format
            mock_logger.assert_called()
            log_call = mock_logger.call_args[0][0]

            # Check for required fields: {id_field, id_len, symbol_norm, attempt}
            assert "clientOrderId=" in log_call
            assert "(len=" in log_call
            assert "symbol_norm=" in log_call
            assert "original_symbol=" in log_call

            # Verify log structure
            log_parts = log_call.split(", ")
            assert len(log_parts) >= 3  # At least 3 parts in the log

        await adapter.close()

    @pytest.mark.asyncio
    async def test_symbol_mapping_in_cancel_order(self, mock_config):
        """Test symbol mapping in cancel_order method."""
        adapter = OKXExchangeAdapter(mock_config)

        with patch.object(adapter.logger, 'info') as mock_logger:
            result = await adapter.cancel_order("test_order_id", "ETH-USDT-SWAP")

            # Verify cancellation was successful
            assert result["status"] == "cancelled"

            # Check log message contains symbol mapping
            mock_logger.assert_called()
            log_call = mock_logger.call_args[0][0]

            assert "symbol_norm=" in log_call
            assert "original_symbol=ETH-USDT-SWAP" in log_call

            # Verify the normalized symbol is correct
            expected_ccxt_symbol = okx_to_ccxt_symbol("ETH-USDT-SWAP")
            assert expected_ccxt_symbol == "ETH/USDT:USDT"

        await adapter.close()

    @pytest.mark.asyncio
    async def test_symbol_mapping_in_fetch_ohlcv(self, mock_config):
        """Test symbol mapping in fetch_ohlcv method."""
        adapter = OKXExchangeAdapter(mock_config)

        with patch.object(adapter.logger, 'info') as mock_logger:
            result = await adapter.fetch_ohlcv("SOL-USDT-SWAP", "1h", 100)

            # Verify OHLCV data is returned
            assert len(result) == 100

            # Check log message contains symbol mapping
            mock_logger.assert_called()
            log_call = mock_logger.call_args[0][0]

            assert "symbol_norm=" in log_call
            assert "original_symbol=SOL-USDT-SWAP" in log_call

            # Verify the normalized symbol is correct
            expected_ccxt_symbol = okx_to_ccxt_symbol("SOL-USDT-SWAP")
            assert expected_ccxt_symbol == "SOL/USDT:USDT"

        await adapter.close()

    @pytest.mark.asyncio
    async def test_error_logging_captured(self, mock_config, mock_order):
        """Test that error logs are properly captured."""
        adapter = OKXExchangeAdapter(mock_config)

        # Force an error by mocking okx_to_ccxt_symbol to raise an exception
        with patch('adapters.exchange_okx_ccxt.okx_to_ccxt_symbol') as mock_symbol_converter:
            mock_symbol_converter.side_effect = Exception("Symbol conversion failed")

            with patch.object(adapter.logger, 'error') as mock_error_logger:
                try:
                    await adapter.place_order(mock_order)
                except Exception:
                    pass  # Expected to fail

                # Verify error was logged
                mock_error_logger.assert_called()
                error_call = mock_error_logger.call_args[0][0]
                assert "Order placement failed" in error_call

                # Verify error count increased
                assert adapter._errors_count > 0

        await adapter.close()

    @pytest.mark.asyncio
    async def test_bracket_orders_symbol_mapping(self, mock_config, mock_order):
        """Test symbol mapping in bracket order placement."""
        adapter = OKXExchangeAdapter(mock_config)

        result = await adapter.place_bracket_orders(
            mock_order,
            take_profit_price=55000.0,
            stop_loss_price=45000.0
        )

        # Verify bracket order was created
        assert "bracket_id" in result
        assert "entry_order" in result
        assert "take_profit_order" in result
        assert "stop_loss_order" in result
        assert result["status"] == "active"

        # Verify all orders have proper client order IDs
        assert result["entry_order"]["client_order_id"] is not None
        assert result["take_profit_order"]["client_order_id"] is not None
        assert result["stop_loss_order"]["client_order_id"] is not None

        await adapter.close()

    @pytest.mark.asyncio
    async def test_adapter_status_tracking(self, mock_config, mock_order):
        """Test that adapter properly tracks status and metrics."""
        adapter = OKXExchangeAdapter(mock_config)

        # Place an order to increment counters
        await adapter.place_order(mock_order)

        # Get adapter status
        status = adapter.get_adapter_status()

        # Verify metrics are tracked
        assert status["mode"] == "dry-run"
        assert status["sandbox"] is True
        assert status["orders_sent"] == 1
        assert status["orders_filled"] == 0
        assert status["orders_cancelled"] == 0
        assert status["errors_count"] == 0
        assert status["exchange_initialized"] is True
        assert status["last_activity"] is not None

        await adapter.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

