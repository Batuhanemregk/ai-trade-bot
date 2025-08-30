"""
Execution Agent for AiBotBS.
Performs order execution, position management, and bracket order handling.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from domain.errors import AgentError
from domain.models import Order, OrderSide, OrderStatus, OrderType

from ..core.base import BaseAgent, Message, MessageType
from ..core.tools import Tool, ToolCategory


@dataclass
class ExecutionRequest:
    """Request for order execution."""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None = None
    stop_price: float | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    leverage: float | None = None
    reduce_only: bool = False
    post_only: bool = False
    time_in_force: str = "GTC"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of order execution."""
    request_id: str
    order_id: str
    status: OrderStatus
    filled_quantity: float
    average_price: float
    commission: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BracketOrder:
    """Bracket order with TP/SL."""
    id: str
    main_order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    take_profit_price: float
    stop_loss_price: float
    status: str  # "pending", "active", "completed", "cancelled"
    created_at: datetime
    take_profit_order_id: str | None = None
    stop_loss_order_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionAgent(BaseAgent):
    """Execution agent that handles order execution and position management."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "execution_agent", config)

        # Execution configuration
        self._exchange_name = config.get("exchange", "okx")
        self._testnet = config.get("testnet", True)
        self._max_retries = config.get("max_retries", 3)
        self._retry_delay = config.get("retry_delay", 1.0)
        self._execution_timeout = config.get("execution_timeout", 30.0)

        # Order management
        self._pending_orders: dict[str, ExecutionRequest] = {}
        self._active_orders: dict[str, Order] = {}
        self._completed_orders: dict[str, Order] = {}
        self._bracket_orders: dict[str, BracketOrder] = {}

        # Performance tracking
        self._orders_executed = 0
        self._orders_filled = 0
        self._orders_cancelled = 0
        self._total_volume = 0.0
        self._last_execution = None

        # Mock exchange client (would be real in production)
        self._exchange_client = None

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the execution agent."""
        self.logger.info("Initializing execution agent")

        # Validate configuration
        self._validate_config()

        # Initialize exchange client
        await self._initialize_exchange_client()

        # Start order monitoring loop
        asyncio.create_task(self._order_monitoring_loop())

        # Start bracket order monitoring
        asyncio.create_task(self._bracket_order_monitoring_loop())

        self.logger.info("Execution agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up execution agent")

        # Cancel all pending orders
        await self._cancel_all_pending_orders()

        self.logger.info("Execution agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register execution-specific tools."""
        from ..core.tools import get_tool_registry

        registry = get_tool_registry()
        registry.register_tool(OrderExecutionTool(self), ToolCategory.EXECUTION)
        registry.register_tool(PositionManagementTool(self), ToolCategory.EXECUTION)
        registry.register_tool(BracketOrderTool(self), ToolCategory.EXECUTION)

    def _validate_config(self) -> None:
        """Validate agent configuration."""
        if self._max_retries < 0:
            self.logger.warning("Max retries must be non-negative")

        if self._retry_delay < 0:
            self.logger.warning("Retry delay must be non-negative")

        if self._execution_timeout < 1:
            self.logger.warning("Execution timeout too low")

    async def _initialize_exchange_client(self) -> None:
        """Initialize the exchange client."""
        try:
            # This would initialize a real exchange client
            # For now, we'll use a mock client
            self._exchange_client = MockExchangeClient()
            self.logger.info(f"Initialized {self._exchange_name} exchange client")

        except Exception as e:
            self.logger.error(f"Failed to initialize exchange client: {e}")
            raise AgentError(f"Exchange client initialization failed: {e}")

    async def _order_monitoring_loop(self) -> None:
        """Main loop for monitoring orders."""
        while self._running:
            try:
                await self._update_order_statuses()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Order monitoring loop error: {e}")
                await asyncio.sleep(10)

    async def _bracket_order_monitoring_loop(self) -> None:
        """Main loop for monitoring bracket orders."""
        while self._running:
            try:
                await self._update_bracket_orders()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                self.logger.error(f"Bracket order monitoring loop error: {e}")
                await asyncio.sleep(30)

    async def _update_order_statuses(self) -> None:
        """Update status of all active orders."""
        try:
            for order_id, order in list(self._active_orders.items()):
                try:
                    # Fetch updated order status from exchange
                    updated_order = await self._fetch_order_status(order_id)
                    if updated_order:
                        self._active_orders[order_id] = updated_order

                        # Check if order is completed
                        if updated_order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                            # Move to completed orders
                            self._completed_orders[order_id] = updated_order
                            del self._active_orders[order_id]

                            # Handle bracket order activation if needed
                            if updated_order.status == OrderStatus.FILLED:
                                await self._handle_order_fill(updated_order)

                            self.logger.info(f"Order {order_id} completed with status: {updated_order.status}")

                except Exception as e:
                    self.logger.error(f"Failed to update order {order_id}: {e}")

        except Exception as e:
            self.logger.error(f"Order status update failed: {e}")

    async def _fetch_order_status(self, order_id: str) -> Order | None:
        """Fetch order status from exchange."""
        try:
            # This would be a real API call to the exchange
            # For now, we'll simulate order updates
            if order_id in self._active_orders:
                order = self._active_orders[order_id]

                # Simulate order progression
                if order.status == OrderStatus.PENDING:
                    # Simulate some orders being filled
                    if order_id.endswith("_fill"):
                        order.status = OrderStatus.FILLED
                        order.filled_at = datetime.utcnow()
                        order.filled_quantity = order.quantity
                        order.average_price = order.price or 0.0
                    # Simulate some orders being cancelled
                    elif order_id.endswith("_cancel"):
                        order.status = OrderStatus.CANCELLED
                        order.cancelled_at = datetime.utcnow()

                return order

            return None

        except Exception as e:
            self.logger.error(f"Failed to fetch order status: {e}")
            return None

    async def _handle_order_fill(self, order: Order) -> None:
        """Handle order fill events."""
        try:
            # Update statistics
            self._orders_filled += 1
            self._total_volume += order.filled_quantity
            self._last_execution = datetime.utcnow()

            # Check if this order is part of a bracket order
            bracket_order = await self._find_bracket_order_by_main_order(order.id)
            if bracket_order:
                await self._activate_bracket_orders(bracket_order)

            # Send fill notification
            await self._send_fill_notification(order)

        except Exception as e:
            self.logger.error(f"Failed to handle order fill: {e}")

    async def _find_bracket_order_by_main_order(self, order_id: str) -> BracketOrder | None:
        """Find bracket order by main order ID."""
        for bracket_order in self._bracket_orders.values():
            if bracket_order.main_order_id == order_id:
                return bracket_order
        return None

    async def _activate_bracket_orders(self, bracket_order: BracketOrder) -> None:
        """Activate TP/SL orders for a bracket order."""
        try:
            if bracket_order.status != "active":
                return

            # Create take profit order
            if bracket_order.take_profit_price:
                tp_order = await self._create_order(
                    symbol=bracket_order.symbol,
                    side=OrderSide.SELL if bracket_order.side == OrderSide.BUY else OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=bracket_order.quantity,
                    price=bracket_order.take_profit_price,
                    reduce_only=True
                )

                if tp_order:
                    bracket_order.take_profit_order_id = tp_order.id
                    self.logger.info(f"Created TP order {tp_order.id} for bracket {bracket_order.id}")

            # Create stop loss order
            if bracket_order.stop_loss_price:
                sl_order = await self._create_order(
                    symbol=bracket_order.symbol,
                    side=OrderSide.SELL if bracket_order.side == OrderSide.BUY else OrderSide.BUY,
                    order_type=OrderType.STOP_MARKET,
                    quantity=bracket_order.quantity,
                    stop_price=bracket_order.stop_loss_price,
                    reduce_only=True
                )

                if sl_order:
                    bracket_order.stop_loss_order_id = sl_order.id
                    self.logger.info(f"Created SL order {sl_order.id} for bracket {bracket_order.id}")

        except Exception as e:
            self.logger.error(f"Failed to activate bracket orders: {e}")

    async def _send_fill_notification(self, order: Order) -> None:
        """Send order fill notification."""
        try:
            # This would send notifications to other agents or external systems
            self.logger.info(f"Order filled: {order.id} - {order.symbol} {order.side.value} {order.filled_quantity}")

        except Exception as e:
            self.logger.error(f"Failed to send fill notification: {e}")

    async def _update_bracket_orders(self) -> None:
        """Update bracket order statuses."""
        try:
            for bracket_id, bracket_order in list(self._bracket_orders.items()):
                if bracket_order.status != "active":
                    continue

                # Check if bracket order should be completed
                if await self._should_complete_bracket_order(bracket_order):
                    bracket_order.status = "completed"
                    self.logger.info(f"Bracket order {bracket_id} completed")

                # Check if bracket order should be cancelled
                if await self._should_cancel_bracket_order(bracket_order):
                    await self._cancel_bracket_order(bracket_order)

        except Exception as e:
            self.logger.error(f"Bracket order update failed: {e}")

    async def _should_complete_bracket_order(self, bracket_order: BracketOrder) -> bool:
        """Check if a bracket order should be completed."""
        try:
            # Check if TP or SL order was filled
            if bracket_order.take_profit_order_id:
                tp_order = self._active_orders.get(bracket_order.take_profit_order_id)
                if tp_order and tp_order.status == OrderStatus.FILLED:
                    return True

            if bracket_order.stop_loss_order_id:
                sl_order = self._active_orders.get(bracket_order.stop_loss_order_id)
                if sl_order and sl_order.status == OrderStatus.FILLED:
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Bracket completion check failed: {e}")
            return False

    async def _should_cancel_bracket_order(self, bracket_order: BracketOrder) -> bool:
        """Check if a bracket order should be cancelled."""
        try:
            # Check if main order was cancelled
            main_order = self._active_orders.get(bracket_order.main_order_id)
            if main_order and main_order.status == OrderStatus.CANCELLED:
                return True

            # Check if bracket order is too old (e.g., > 24 hours)
            if datetime.utcnow() - bracket_order.created_at > timedelta(hours=24):
                return True

            return False

        except Exception as e:
            self.logger.error(f"Bracket cancellation check failed: {e}")
            return False

    async def _cancel_bracket_order(self, bracket_order: BracketOrder) -> None:
        """Cancel a bracket order and its associated orders."""
        try:
            # Cancel TP order if exists
            if bracket_order.take_profit_order_id:
                await self._cancel_order(bracket_order.take_profit_order_id)

            # Cancel SL order if exists
            if bracket_order.stop_loss_order_id:
                await self._cancel_order(bracket_order.stop_loss_order_id)

            # Mark bracket order as cancelled
            bracket_order.status = "cancelled"
            self.logger.info(f"Bracket order {bracket_order.id} cancelled")

        except Exception as e:
            self.logger.error(f"Failed to cancel bracket order: {e}")

    async def _cancel_all_pending_orders(self) -> None:
        """Cancel all pending orders."""
        try:
            for order_id in list(self._active_orders.keys()):
                await self._cancel_order(order_id)

        except Exception as e:
            self.logger.error(f"Failed to cancel all pending orders: {e}")

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "order_execution":
                result = await self._execute_order(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="order_execution_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "bracket_order":
                result = await self._create_bracket_order(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="bracket_order_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Error handling task message: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="task_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        data_type = message.body.get("data_type")

        if data_type == "market_data":
            await self._process_market_data(message.body)
        elif data_type == "position_update":
            await self._process_position_update(message.body)

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "get_status":
                result = self.get_status()
            elif command == "get_orders":
                result = {
                    "pending_orders": len(self._pending_orders),
                    "active_orders": len(self._active_orders),
                    "completed_orders": len(self._completed_orders),
                    "bracket_orders": len(self._bracket_orders)
                }
            elif command == "cancel_order":
                order_id = parameters.get("order_id")
                if not order_id:
                    raise AgentError("Missing order_id parameter")

                success = await self._cancel_order(order_id)
                result = {"status": "cancelled" if success else "failed", "order_id": order_id}

            elif command == "get_order_status":
                order_id = parameters.get("order_id")
                if not order_id:
                    raise AgentError("Missing order_id parameter")

                order = self._active_orders.get(order_id) or self._completed_orders.get(order_id)
                if order:
                    result = {
                        "order_id": order.id,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "status": order.status.value,
                        "quantity": order.quantity,
                        "filled_quantity": order.filled_quantity,
                        "price": order.price,
                        "average_price": order.average_price
                    }
                else:
                    result = {"error": f"Order not found: {order_id}"}

            else:
                result = {"error": f"Unknown command: {command}"}

            response = Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject=f"command_response_{command}",
                body=result,
                reply_to=message.id
            )
            await self.send_message(response)

        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="command_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _execute_order(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute an order."""
        try:
            # Create execution request
            request = ExecutionRequest(
                id=f"req_{uuid4().hex[:8]}",
                symbol=parameters.get("symbol"),
                side=OrderSide(parameters.get("side", "buy")),
                order_type=OrderType(parameters.get("order_type", "market")),
                quantity=parameters.get("quantity", 0.0),
                price=parameters.get("price"),
                stop_price=parameters.get("stop_price"),
                leverage=parameters.get("leverage"),
                reduce_only=parameters.get("reduce_only", False),
                post_only=parameters.get("post_only", False),
                metadata=parameters.get("metadata", {})
            )

            # Validate request
            if not request.symbol or request.quantity <= 0:
                raise AgentError("Invalid order parameters")

            # Create order
            order = await self._create_order(
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                stop_price=request.stop_price,
                leverage=request.leverage,
                reduce_only=request.reduce_only,
                post_only=request.post_only
            )

            if not order:
                raise AgentError("Failed to create order")

            # Store request and order
            self._pending_orders[request.id] = request
            self._active_orders[order.id] = order

            # Update statistics
            self._orders_executed += 1
            self._last_execution = datetime.utcnow()

            return {
                "request_id": request.id,
                "order_id": order.id,
                "status": order.status.value,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "price": order.price,
                "timestamp": order.created_at.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Order execution failed: {e}")
            raise AgentError(f"Order execution failed: {e}")

    async def _create_order(self, **kwargs) -> Order | None:
        """Create an order on the exchange."""
        try:
            # This would be a real API call to the exchange
            # For now, we'll create a mock order

            order_id = f"order_{kwargs['symbol'].replace('/', '_')}_{uuid4().hex[:8]}"

            order = Order(
                id=order_id,
                symbol=kwargs["symbol"],
                side=kwargs["side"],
                order_type=kwargs["order_type"],
                quantity=kwargs["quantity"],
                price=kwargs.get("price"),
                stop_price=kwargs.get("stop_price"),
                status=OrderStatus.PENDING,
                leverage=kwargs.get("leverage", 1.0)
            )

            self.logger.info(f"Created order: {order_id} - {order.symbol} {order.side.value} {order.quantity}")
            return order

        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            return None

    async def _cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            if order_id in self._active_orders:
                order = self._active_orders[order_id]
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.utcnow()

                # Move to completed orders
                self._completed_orders[order_id] = order
                del self._active_orders[order_id]

                self._orders_cancelled += 1
                self.logger.info(f"Cancelled order: {order_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def _create_bracket_order(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Create a bracket order with TP/SL."""
        try:
            symbol = parameters.get("symbol")
            side = parameters.get("side", "buy")
            quantity = parameters.get("quantity", 0.0)
            entry_price = parameters.get("entry_price", 0.0)
            take_profit = parameters.get("take_profit")
            stop_loss = parameters.get("stop_loss")

            if not symbol or quantity <= 0 or entry_price <= 0:
                raise AgentError("Invalid bracket order parameters")

            # Create main order
            main_order = await self._create_order(
                symbol=symbol,
                side=OrderSide(side),
                order_type=OrderType.MARKET,
                quantity=quantity
            )

            if not main_order:
                raise AgentError("Failed to create main order")

            # Create bracket order
            bracket_id = f"bracket_{uuid4().hex[:8]}"
            bracket_order = BracketOrder(
                id=bracket_id,
                main_order_id=main_order.id,
                symbol=symbol,
                side=OrderSide(side),
                quantity=quantity,
                entry_price=entry_price,
                take_profit_price=take_profit,
                stop_loss_price=stop_loss,
                status="pending",
                created_at=datetime.utcnow()
            )

            # Store bracket order
            self._bracket_orders[bracket_id] = bracket_order

            # Store main order
            self._active_orders[main_order.id] = main_order

            return {
                "bracket_id": bracket_id,
                "main_order_id": main_order.id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "status": "pending",
                "timestamp": bracket_order.created_at.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Bracket order creation failed: {e}")
            raise AgentError(f"Bracket order creation failed: {e}")

    async def _process_market_data(self, data: dict[str, Any]) -> None:
        """Process market data updates."""
        try:
            # This could trigger order modifications or other actions
            symbol = data.get("symbol")
            if symbol:
                self.logger.debug(f"Received market data for {symbol}")

        except Exception as e:
            self.logger.error(f"Failed to process market data: {e}")

    async def _process_position_update(self, data: dict[str, Any]) -> None:
        """Process position updates."""
        try:
            # This could trigger risk management actions
            symbol = data.get("symbol")
            if symbol:
                self.logger.debug(f"Received position update for {symbol}")

        except Exception as e:
            self.logger.error(f"Failed to process position update: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "execution_agent",
            "status": self.status.value,
            "orders_executed": self._orders_executed,
            "orders_filled": self._orders_filled,
            "orders_cancelled": self._orders_cancelled,
            "total_volume": self._total_volume,
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
            "pending_orders": len(self._pending_orders),
            "active_orders": len(self._active_orders),
            "completed_orders": len(self._completed_orders),
            "bracket_orders": len(self._bracket_orders),
            "exchange": self._exchange_name,
            "testnet": self._testnet
        }


# Mock exchange client for testing
class MockExchangeClient:
    """Mock exchange client for testing purposes."""

    def __init__(self):
        self.name = "MockExchange"
        self.testnet = True

    async def create_order(self, **kwargs):
        """Mock order creation."""
        return {"id": f"mock_order_{uuid4().hex[:8]}"}

    async def cancel_order(self, order_id: str):
        """Mock order cancellation."""
        return {"status": "cancelled"}

    async def get_order(self, order_id: str):
        """Mock order retrieval."""
        return {"id": order_id, "status": "pending"}


# Tool classes for the Execution agent

class OrderExecutionTool(Tool):
    """Tool for order execution."""

    def __init__(self, execution_agent: ExecutionAgent):
        super().__init__("order_execution", "Execute trading orders")
        self.execution_agent = execution_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute order execution."""
        return await self.execution_agent._execute_order(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol"
            },
            "side": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "Order side"
            },
            "order_type": {
                "type": "string",
                "enum": ["market", "limit", "stop", "stop_limit"],
                "description": "Order type"
            },
            "quantity": {
                "type": "number",
                "description": "Order quantity"
            },
            "price": {
                "type": "number",
                "description": "Order price (for limit orders)"
            },
            "stop_price": {
                "type": "number",
                "description": "Stop price (for stop orders)"
            }
        }


class PositionManagementTool(Tool):
    """Tool for position management."""

    def __init__(self, execution_agent: ExecutionAgent):
        super().__init__("position_management", "Manage trading positions")
        self.execution_agent = execution_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute position management operation."""
        operation = parameters.get("operation")

        if operation == "get_positions":
            return {
                "active_orders": len(self.execution_agent._active_orders),
                "completed_orders": len(self.execution_agent._completed_orders)
            }
        else:
            raise AgentError(f"Unknown operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["get_positions"],
                "description": "Position management operation to perform"
            }
        }


class BracketOrderTool(Tool):
    """Tool for bracket order management."""

    def __init__(self, execution_agent: ExecutionAgent):
        super().__init__("bracket_order", "Create and manage bracket orders")
        self.execution_agent = execution_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute bracket order operation."""
        return await self.execution_agent._create_bracket_order(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol"
            },
            "side": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "Order side"
            },
            "quantity": {
                "type": "number",
                "description": "Order quantity"
            },
            "entry_price": {
                "type": "number",
                "description": "Entry price"
            },
            "take_profit": {
                "type": "number",
                "description": "Take profit price"
            },
            "stop_loss": {
                "type": "number",
                "description": "Stop loss price"
            }
        }
