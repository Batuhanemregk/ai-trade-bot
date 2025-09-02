"""
Unit test for OKX CCXT entry order methods.
Tests the create_market_order and create_limit_order methods.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

from adapters.exchange_okx_ccxt import OKXCCXTAdapter


class TestOKXCCXTEntry:
    """Test OKX CCXT entry order methods."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance with mocked CCXT client."""
        adapter = OKXCCXTAdapter("test_key", "test_secret", "test_pass")
        adapter.ccxt_client = AsyncMock()
        return adapter
    
    @pytest.mark.asyncio
    async def test_create_market_order_basic(self, adapter):
        """Test basic market order creation."""
        # Mock CCXT response
        mock_response = {
            'id': '12345',
            'status': 'filled',
            'price': 50000.0
        }
        adapter.ccxt_client.create_order.return_value = mock_response
        
        # Mock quantization functions
        with patch('execution.quantize.quantize_size', return_value=0.001), \
             patch('execution.quantize.bump_to_min_size', return_value=0.001), \
             patch('execution.id_utils.generate_client_id', return_value='TEST123'), \
             patch('execution.okx_symbol.okx_to_ccxt_symbol', return_value='BTC/USDT:USDT'):
            
            result = await adapter.create_market_order(
                symbol='BTC-USDT-SWAP',
                side='buy',
                amount=0.001
            )
        
        # Verify CCXT call
        adapter.ccxt_client.create_order.assert_called_once()
        call_args = adapter.ccxt_client.create_order.call_args
        
        assert call_args[0][0] == 'BTC/USDT:USDT'  # ccxt_symbol
        assert call_args[0][1] == 'market'         # order_type
        assert call_args[0][2] == 'buy'            # side
        assert call_args[0][3] == 0.001            # amount
        assert call_args[0][4] is None             # price (None for market)
        
        # Verify params
        params = call_args[0][5]
        assert params['tdMode'] == 'cross'
        assert params['reduceOnly'] is False
        assert params['clientOrderId'] == 'TEST123'
        assert params['clOrdId'] == 'TEST123'
        
        # Verify result
        assert result['id'] == '12345'
        assert result['status'] == 'filled'
        assert result['symbol'] == 'BTC-USDT-SWAP'
        assert result['side'] == 'buy'
        assert result['type'] == 'market'
        assert result['amount'] == 0.001
        assert result['clientOrderId'] == 'TEST123'
    
    @pytest.mark.asyncio
    async def test_create_limit_order_basic(self, adapter):
        """Test basic limit order creation."""
        # Mock CCXT response
        mock_response = {
            'id': '67890',
            'status': 'open',
            'price': 49000.0
        }
        adapter.ccxt_client.create_order.return_value = mock_response
        
        # Mock quantization functions
        with patch('execution.quantize.quantize_size', return_value=0.001), \
             patch('execution.quantize.bump_to_min_size', return_value=0.001), \
             patch('execution.quantize.quantize_price', return_value=49000.0), \
             patch('execution.id_utils.generate_client_id', return_value='TEST456'), \
             patch('execution.okx_symbol.okx_to_ccxt_symbol', return_value='BTC/USDT:USDT'):
            
            result = await adapter.create_limit_order(
                symbol='BTC-USDT-SWAP',
                side='sell',
                amount=0.001,
                price=49000.0
            )
        
        # Verify CCXT call
        adapter.ccxt_client.create_order.assert_called_once()
        call_args = adapter.ccxt_client.create_order.call_args
        
        assert call_args[0][0] == 'BTC/USDT:USDT'  # ccxt_symbol
        assert call_args[0][1] == 'limit'          # order_type
        assert call_args[0][2] == 'sell'           # side
        assert call_args[0][3] == 0.001            # amount
        assert call_args[0][4] == 49000.0          # price
        
        # Verify params
        params = call_args[0][5]
        assert params['tdMode'] == 'cross'
        assert params['reduceOnly'] is False
        assert params['clientOrderId'] == 'TEST456'
        assert params['clOrdId'] == 'TEST456'
        
        # Verify result
        assert result['id'] == '67890'
        assert result['status'] == 'open'
        assert result['symbol'] == 'BTC-USDT-SWAP'
        assert result['side'] == 'sell'
        assert result['type'] == 'limit'
        assert result['amount'] == 0.001
        assert result['price'] == 49000.0
        assert result['clientOrderId'] == 'TEST456'
    
    @pytest.mark.asyncio
    async def test_hedge_mode_params(self, adapter):
        """Test hedge mode parameter handling."""
        # Mock environment
        with patch.dict(os.environ, {'OKX_HEDGE_MODE': '1'}), \
             patch('execution.quantize.quantize_size', return_value=0.001), \
             patch('execution.quantize.bump_to_min_size', return_value=0.001), \
             patch('execution.id_utils.generate_client_id', return_value='TEST789'), \
             patch('execution.okx_symbol.okx_to_ccxt_symbol', return_value='BTC/USDT:USDT'):
            
            adapter.ccxt_client.create_order.return_value = {'id': '99999', 'status': 'filled'}
            
            await adapter.create_market_order('BTC-USDT-SWAP', 'buy', 0.001)
            
            # Verify hedge mode params
            call_args = adapter.ccxt_client.create_order.call_args
            params = call_args[0][5]
            assert params['posSide'] == 'long'  # buy -> long in hedge mode
    
    @pytest.mark.asyncio
    async def test_custom_client_id(self, adapter):
        """Test custom client ID handling."""
        with patch('execution.quantize.quantize_size', return_value=0.001), \
             patch('execution.quantize.bump_to_min_size', return_value=0.001), \
             patch('execution.okx_symbol.okx_to_ccxt_symbol', return_value='BTC/USDT:USDT'):
            
            adapter.ccxt_client.create_order.return_value = {'id': '11111', 'status': 'filled'}
            
            await adapter.create_market_order(
                'BTC-USDT-SWAP', 'sell', 0.001, client_id='CUSTOM123'
            )
            
            # Verify custom client ID
            call_args = adapter.ccxt_client.create_order.call_args
            params = call_args[0][5]
            assert params['clientOrderId'] == 'CUSTOM123'
            assert params['clOrdId'] == 'CUSTOM123'
