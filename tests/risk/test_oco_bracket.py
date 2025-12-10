"""
Test OCO Bracket Implementation

Tests for the OCO (One-Cancels-Other) bracket order functionality.
When TP triggers, SL should be cancelled and vice versa.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestOCOBracket:
    """Tests for OCO bracket order creation."""
    
    @pytest.fixture
    def mock_exchange_adapter(self):
        """Create mock exchange adapter with OCO support."""
        adapter = MagicMock()
        adapter.create_oco_order = AsyncMock(return_value={
            'tp_algo_id': 'TP_12345',
            'sl_algo_id': 'SL_12345',
            'oco_link_id': 'OCO_1234567890',
            'status': 'live'
        })
        adapter.create_trigger_order = AsyncMock(return_value={
            'algoId': 'TRIGGER_12345',
            'status': 'live'
        })
        adapter.cancel_algo_order = AsyncMock(return_value={'success': True})
        return adapter
    
    @pytest.mark.asyncio
    async def test_create_oco_bracket_long(self, mock_exchange_adapter):
        """Test OCO bracket creation for LONG position."""
        from infrastructure.runtime import _create_oco_bracket
        
        result = await _create_oco_bracket(
            exchange_adapter=mock_exchange_adapter,
            symbol='BTC-USDT-SWAP',
            decision='LONG',
            tp_price=52000.0,
            sl_price=48000.0,
            entry_client_id='E:BTC:L:2024-01-01T12:00Z',
            position_size=0.01
        )
        
        assert 'oco_link_id' in result
        assert result.get('tp_algo_id') or result.get('tp_result')
        assert result.get('sl_algo_id') or result.get('sl_result')
    
    @pytest.mark.asyncio
    async def test_create_oco_bracket_short(self, mock_exchange_adapter):
        """Test OCO bracket creation for SHORT position."""
        from infrastructure.runtime import _create_oco_bracket
        
        result = await _create_oco_bracket(
            exchange_adapter=mock_exchange_adapter,
            symbol='ETH-USDT-SWAP',
            decision='SHORT',
            tp_price=3800.0,
            sl_price=4200.0,
            entry_client_id='E:ETH:S:2024-01-01T12:00Z',
            position_size=0.1
        )
        
        assert 'oco_link_id' in result
    
    @pytest.mark.asyncio
    async def test_oco_bracket_fallback_to_triggers(self):
        """Test fallback when exchange doesn't support native OCO."""
        from infrastructure.runtime import _create_oco_bracket
        
        # Adapter without native OCO but with trigger orders
        adapter = MagicMock()
        adapter.create_trigger_order = AsyncMock(return_value={
            'algoId': 'ALGO_FALLBACK_123',
            'status': 'live'
        })
        adapter.create_oco_order = None  # No native OCO
        delattr(adapter, 'create_oco_order')
        
        result = await _create_oco_bracket(
            exchange_adapter=adapter,
            symbol='SOL-USDT-SWAP',
            decision='LONG',
            tp_price=120.0,
            sl_price=100.0,
            entry_client_id='E:SOL:L:2024-01-01T12:00Z',
            position_size=1.0
        )
        
        # Should create linked triggers with OCO mapping
        assert 'oco_link_id' in result
        assert adapter.create_trigger_order.call_count == 2  # TP + SL
    
    @pytest.mark.asyncio
    async def test_cancel_oco_counterpart(self, mock_exchange_adapter):
        """Test cancelling counterpart when one side triggers."""
        from infrastructure.runtime import _cancel_oco_counterpart
        
        result = await _cancel_oco_counterpart(
            exchange_adapter=mock_exchange_adapter,
            symbol='BTC-USDT-SWAP',
            triggered_side='TP',
            oco_link_id='OCO_12345',
            counterpart_algo_id='SL_12345'
        )
        
        assert result is True
        mock_exchange_adapter.cancel_algo_order.assert_called_once()


class TestOCOIntegration:
    """Integration tests for OCO with trade execution."""
    
    @pytest.mark.asyncio
    async def test_execute_trade_creates_oco_bracket(self):
        """Test that _execute_trade creates OCO bracket in LIVE mode."""
        # This would require more extensive mocking of the full trade flow
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
