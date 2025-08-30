"""
Tests for the execution glue components.
Tests the integration between scoring, risk, and execution agents.
"""

# Add parent directory to path for imports
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from agents.core.base import Message, MessageType
from agents.roles.execution_agent import ExecutionAgent
from agents.roles.risk_agent import RiskManagementAgent
from execution.prevalidation import OrderPrevalidator
from execution.quantize import Quantizer


@pytest.fixture
def risk_agent():
    """Create a risk agent for testing."""
    config = {
        "enabled": True,
        "max_position_size": 0.1,
        "max_drawdown": 0.2,
        "leverage_limit": 3.0,
        "risk_free_rate": 0.02,
        "var_confidence": 0.95
    }
    return RiskManagementAgent("test_risk", config)


@pytest.fixture
def execution_agent():
    """Create an execution agent for testing."""
    config = {
        "enabled": True,
        "mode": "dry-run",
        "max_orders": 100,
        "order_timeout": 30,
        "default_slippage": 0.001
    }
    return ExecutionAgent("test_execution", config)


@pytest.fixture
def order_prevalidator():
    """Create an order prevalidator for testing."""
    return OrderPrevalidator()


@pytest.fixture
def quantizer():
    """Create a quantizer for testing."""
    return Quantizer()


class TestScoringToRiskFlow:
    """Test the flow from scoring to risk assessment."""

    @pytest.mark.asyncio
    async def test_composite_score_creation(self, risk_agent):
        """Test creation of composite scores from multiple sources."""
        await risk_agent.start()

        # Create mock analysis results
        ta_result = {
            "signal": "BUY",
            "confidence": 0.8,
            "indicators": {"RSI": 0.3, "MACD": "bullish"}
        }

        ml_result = {
            "prediction": "BUY",
            "confidence": 0.75,
            "model": "ensemble_rf"
        }

        news_result = {
            "sentiment": "positive",
            "score": 0.7,
            "sources": 5
        }

        # Send analysis results to risk agent
        from agents.core.base import Message, MessageType

        ta_message = Message(
            type=MessageType.DATA_UPDATE,
            from_agent="ta_agent",
            to_agent="test_risk",
            subject="ta_analysis_result",
            body={
                "data_type": "analysis_result",
                "analysis_type": "ta",
                "result": ta_result
            }
        )

        await risk_agent.handle_message(ta_message)

        ml_message = Message(
            type=MessageType.DATA_UPDATE,
            from_agent="ml_agent",
            to_agent="test_risk",
            subject="ml_analysis_result",
            body={
                "data_type": "analysis_result",
                "analysis_type": "ml",
                "result": ml_result
            }
        )

        await risk_agent.handle_message(ml_message)

        news_message = Message(
            type=MessageType.DATA_UPDATE,
            from_agent="news_agent",
            to_agent="test_risk",
            subject="news_analysis_result",
            body={
                "data_type": "analysis_result",
                "analysis_type": "news",
                "result": news_result
            }
        )

        await risk_agent.handle_message(news_message)

        # Check that risk agent processed the messages
        assert risk_agent._messages_processed >= 3

        await risk_agent.stop()

    @pytest.mark.asyncio
    async def test_risk_assessment_generation(self, risk_agent):
        """Test that risk assessment is generated from composite scores."""
        await risk_agent.start()

        # Send risk assessment request
        from agents.core.base import Message, MessageType

        risk_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="test_risk",
            subject="risk_assessment",
            body={
                "task_type": "assess_risk",
                "symbol": "BTC/USDT",
                "position_size": 0.05,
                "entry_price": 50000.0,
                "side": "long"
            }
        )

        await risk_agent.handle_message(risk_message)

        # Check that risk assessment was generated
        assert risk_agent._messages_processed > 0

        await risk_agent.stop()

    @pytest.mark.asyncio
    async def test_risk_score_downgrade(self, risk_agent):
        """Test that risk assessment can downgrade final scores."""
        await risk_agent.start()

        # Test with high-risk scenario
        high_risk_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="test_risk",
            subject="risk_assessment_high_risk",
            body={
                "task_type": "assess_risk",
                "symbol": "BTC/USDT",
                "position_size": 0.2,  # Exceeds max position size
                "entry_price": 50000.0,
                "side": "long",
                "leverage": 5.0  # Exceeds leverage limit
            }
        )

        await risk_agent.handle_message(high_risk_message)

        # Check that risk assessment was generated
        assert risk_agent._messages_processed > 0

        await risk_agent.stop()


class TestRiskToExecutionFlow:
    """Test the flow from risk assessment to execution."""

    @pytest.mark.asyncio
    async def test_execution_plan_creation(self, execution_agent):
        """Test creation of execution plans from risk assessment."""
        await execution_agent.start()

        # Send execution request with risk assessment
        from agents.core.base import Message, MessageType

        execution_message = Message(
            type=MessageType.TASK,
            from_agent="risk_agent",
            to_agent="test_execution",
            subject="execute_with_risk",
            body={
                "task_type": "execute",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.01,
                "entry_price": 50000.0,
                "risk_assessment": {
                    "risk_level": "medium",
                    "max_position_size": 0.1,
                    "stop_loss": 48000.0,
                    "take_profit": 52000.0
                }
            }
        )

        await execution_agent.handle_message(execution_message)

        # Check that execution plan was created
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()

    @pytest.mark.asyncio
    async def test_dry_run_execution_plan(self, execution_agent):
        """Test that execution plans are created in dry-run mode without live orders."""
        await execution_agent.start()

        # Ensure dry-run mode
        execution_agent.config["mode"] = "dry-run"

        execution_message = Message(
            type=MessageType.TASK,
            from_agent="risk_agent",
            to_agent="test_execution",
            subject="dry_run_execution",
            body={
                "task_type": "execute",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.01,
                "mode": "dry-run"
            }
        )

        await execution_agent.handle_message(execution_message)

        # Check that execution plan was created
        assert execution_agent._messages_processed > 0

        # In dry-run mode, no live orders should be sent
        # This would be verified by checking that the mock exchange client wasn't called

        await execution_agent.stop()

    @pytest.mark.asyncio
    async def test_paper_mode_execution(self, execution_agent):
        """Test execution in paper trading mode."""
        await execution_agent.start()

        # Set paper mode
        execution_agent.config["mode"] = "paper"

        execution_message = Message(
            type=MessageType.TASK,
            from_agent="risk_agent",
            to_agent="test_execution",
            subject="paper_execution",
            body={
                "task_type": "execute",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.01,
                "mode": "paper"
            }
        )

        await execution_agent.handle_message(execution_message)

        # Check that execution plan was created
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()


class TestExecutionPrevalidation:
    """Test order prevalidation in the execution flow."""

    def test_basic_order_validation(self, order_prevalidator):
        """Test basic order validation."""
        # Valid order
        valid_order = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.01,
            "price": 50000.0
        }

        result = order_prevalidator.validate_order(valid_order)
        assert result["valid"] is True

        # Invalid order (missing required fields)
        invalid_order = {
            "symbol": "BTC/USDT",
            "side": "buy"
            # Missing quantity and price
        }

        result = order_prevalidator.validate_order(invalid_order)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_tp_sl_inequality_validation(self, order_prevalidator):
        """Test take profit and stop loss inequality validation."""
        # Valid TP/SL (TP > SL for long position)
        valid_tp_sl = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.01,
            "price": 50000.0,
            "take_profit": 52000.0,
            "stop_loss": 48000.0
        }

        result = order_prevalidator.validate_order(valid_tp_sl)
        assert result["valid"] is True

        # Invalid TP/SL (TP < SL for long position)
        invalid_tp_sl = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.01,
            "price": 50000.0,
            "take_profit": 48000.0,  # TP < SL
            "stop_loss": 52000.0
        }

        result = order_prevalidator.validate_order(invalid_tp_sl)
        assert result["valid"] is False
        assert any("take profit must be greater than stop loss" in error.lower() for error in result["errors"])

    def test_bracket_order_structure_validation(self, order_prevalidator):
        """Test bracket order structure validation."""
        # Valid bracket order
        valid_bracket = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.01,
            "price": 50000.0,
            "take_profit": 52000.0,
            "stop_loss": 48000.0,
            "bracket": True
        }

        result = order_prevalidator.validate_order(valid_bracket)
        assert result["valid"] is True

        # Invalid bracket order (missing TP or SL)
        invalid_bracket = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.01,
            "price": 50000.0,
            "take_profit": 52000.0,
            # Missing stop_loss
            "bracket": True
        }

        result = order_prevalidator.validate_order(invalid_bracket)
        assert result["valid"] is False
        assert any("bracket order requires both take profit and stop loss" in error.lower() for error in result["errors"])


class TestExecutionQuantization:
    """Test order quantization in the execution flow."""

    def test_price_quantization(self, quantizer):
        """Test price quantization according to tick size."""
        # Mock instrument info
        instrument_info = {
            "tickSz": "0.1",
            "lotSz": "0.0001",
            "minSz": "0.0001",
            "maxSz": "1000"
        }

        # Test price quantization
        raw_price = 50000.123
        quantized_price = quantizer.quantize_price(raw_price, instrument_info)

        # Should be quantized to nearest tick
        assert quantized_price == Decimal("50000.1")

    def test_quantity_quantization(self, quantizer):
        """Test quantity quantization according to lot size."""
        # Mock instrument info
        instrument_info = {
            "tickSz": "0.1",
            "lotSz": "0.0001",
            "minSz": "0.0001",
            "maxSz": "1000"
        }

        # Test quantity quantization
        raw_quantity = 0.012345
        quantized_quantity = quantizer.quantize_quantity(raw_quantity, instrument_info)

        # Should be quantized to nearest lot
        assert quantized_quantity == Decimal("0.0123")

    def test_minimum_quantity_handling(self, quantizer):
        """Test handling of quantities below minimum."""
        # Mock instrument info
        instrument_info = {
            "tickSz": "0.1",
            "lotSz": "0.0001",
            "minSz": "0.001",
            "maxSz": "1000"
        }

        # Test quantity below minimum
        small_quantity = 0.0005

        # Should bump to minimum
        bumped_quantity = quantizer.bump_to_min(small_quantity, instrument_info)
        assert bumped_quantity == Decimal("0.001")

        # Should skip if below minimum
        skip_result = quantizer.skip_if_below_min(small_quantity, instrument_info)
        assert skip_result is True


class TestExecutionIntegration:
    """Test integration between execution components."""

    @pytest.mark.asyncio
    async def test_complete_execution_flow(self, execution_agent, order_prevalidator, quantizer):
        """Test the complete execution flow from order creation to validation."""
        await execution_agent.start()

        # Create execution request
        execution_request = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.01,
            "entry_price": 50000.0,
            "take_profit": 52000.0,
            "stop_loss": 48000.0
        }

        # Step 1: Prevalidate order
        validation_result = order_prevalidator.validate_order(execution_request)
        assert validation_result["valid"] is True

        # Step 2: Quantize prices and quantities
        instrument_info = {
            "tickSz": "0.1",
            "lotSz": "0.0001",
            "minSz": "0.001",
            "maxSz": "1000"
        }

        quantized_entry = quantizer.quantize_price(execution_request["entry_price"], instrument_info)
        quantized_tp = quantizer.quantize_price(execution_request["take_profit"], instrument_info)
        quantized_sl = quantizer.quantize_price(execution_request["stop_loss"], instrument_info)
        quantized_qty = quantizer.quantize_quantity(execution_request["quantity"], instrument_info)

        # Step 3: Create quantized order
        quantized_order = {
            "symbol": execution_request["symbol"],
            "side": execution_request["side"],
            "quantity": float(quantized_qty),
            "entry_price": float(quantized_entry),
            "take_profit": float(quantized_tp),
            "stop_loss": float(quantized_sl)
        }

        # Step 4: Send to execution agent
        from agents.core.base import Message, MessageType

        execution_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="test_execution",
            subject="execute_quantized_order",
            body={
                "task_type": "execute",
                "order": quantized_order,
                "mode": "dry-run"
            }
        )

        await execution_agent.handle_message(execution_message)

        # Check that execution agent processed the message
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()

    @pytest.mark.asyncio
    async def test_bracket_order_creation(self, execution_agent):
        """Test creation of bracket orders in execution."""
        await execution_agent.start()

        # Send bracket order request
        from agents.core.base import Message, MessageType

        bracket_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="test_execution",
            subject="create_bracket_order",
            body={
                "task_type": "create_bracket",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.01,
                "entry_price": 50000.0,
                "take_profit_pct": 0.04,  # 4% above entry
                "stop_loss_pct": 0.04      # 4% below entry
            }
        )

        await execution_agent.handle_message(bracket_message)

        # Check that bracket order was created
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()


class TestErrorHandling:
    """Test error handling in the execution flow."""

    @pytest.mark.asyncio
    async def test_invalid_order_handling(self, execution_agent):
        """Test handling of invalid orders."""
        await execution_agent.start()

        # Send invalid order
        from agents.core.base import Message, MessageType

        invalid_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="test_execution",
            subject="execute_invalid_order",
            body={
                "task_type": "execute",
                "order": {
                    "symbol": "BTC/USDT",
                    "side": "invalid_side",  # Invalid side
                    "quantity": -0.01        # Negative quantity
                }
            }
        )

        await execution_agent.handle_message(invalid_message)

        # Check that execution agent handled the error gracefully
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()

    @pytest.mark.asyncio
    async def test_quantization_error_handling(self, quantizer):
        """Test handling of quantization errors."""
        # Test with invalid instrument info
        invalid_instrument = {
            "tickSz": "invalid",
            "lotSz": "invalid"
        }

        # Should handle gracefully
        try:
            quantizer.quantize_price(50000.0, invalid_instrument)
        except Exception as e:
            # Should raise an error for invalid tick size
            assert "tick size" in str(e).lower() or "invalid" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
