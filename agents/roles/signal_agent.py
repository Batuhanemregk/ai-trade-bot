"""
Signal Agent for the AiBotBS Runtime Agent System.
Responsible for generating, managing, and distributing trading signals.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from domain.models import OrderSide, Signal, SignalType

from ..core.base import BaseAgent, Context, Message, MessageType
from ..core.tools import Tool


class SignalStatus(Enum):
    """Signal status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignalPriority(Enum):
    """Signal priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SignalRequest:
    """Request for signal generation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    timeframe: str = "1h"
    analysis_type: str = "composite"  # ta, ml, news, composite
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: SignalPriority = SignalPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


@dataclass
class SignalResult:
    """Result of signal generation."""
    signal: Signal
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SignalGenerationTool(Tool):
    """Tool for generating trading signals."""

    def __init__(self):
        super().__init__("signal_generation", "Generate trading signals based on analysis")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute signal generation."""
        try:
            symbol = parameters.get("symbol")
            analysis_type = parameters.get("analysis_type", "composite")

            if not symbol:
                return {"error": "Symbol is required"}

            # Mock signal generation for now
            signal = self._generate_mock_signal(symbol, analysis_type)

            return {
                "signal": signal.to_dict(),
                "analysis_type": analysis_type,
                "generated_at": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol (e.g., BTC/USDT)"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["ta", "ml", "news", "composite"],
                "description": "Type of analysis to use for signal generation"
            },
            "timeframe": {
                "type": "string",
                "description": "Timeframe for analysis (e.g., 1m, 5m, 1h, 1d)"
            }
        }

    def _generate_mock_signal(self, symbol: str, analysis_type: str) -> Signal:
        """Generate a mock signal for testing."""
        import random

        # Random signal generation
        signal_types = [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        signal_type = random.choice(signal_types)

        if signal_type == SignalType.HOLD:
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=0.5,
                metadata={"analysis_type": analysis_type, "mock": True}
            )

        # Generate buy/sell signal
        side = OrderSide.BUY if signal_type == SignalType.BUY else OrderSide.SELL
        confidence = random.uniform(0.6, 0.95)

        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            side=side,
            confidence=confidence,
            entry_price=random.uniform(40000, 60000) if "BTC" in symbol else random.uniform(2000, 4000),
            stop_loss=random.uniform(0.95, 0.98),
            take_profit=random.uniform(1.02, 1.05),
            metadata={
                "analysis_type": analysis_type,
                "mock": True,
                "generated_by": "signal_agent"
            }
        )


class SignalManagementTool(Tool):
    """Tool for managing signal lifecycle."""

    def __init__(self):
        super().__init__("signal_management", "Manage signal lifecycle and status")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute signal management operation."""
        try:
            operation = parameters.get("operation")

            if operation == "activate":
                return await self._activate_signal(parameters)
            elif operation == "deactivate":
                return await self._deactivate_signal(parameters)
            elif operation == "update":
                return await self._update_signal(parameters)
            elif operation == "list":
                return await self._list_signals(parameters)
            else:
                raise ValueError(f"Unknown signal management operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["activate", "deactivate", "update", "list"],
                "description": "Signal management operation to perform"
            },
            "signal_id": {
                "type": "string",
                "description": "Signal ID for activate/deactivate/update operations"
            },
            "status": {
                "type": "string",
                "enum": ["active", "inactive", "expired"],
                "description": "New status for update operation"
            },
            "filter": {
                "type": "object",
                "description": "Filter criteria for list operation"
            }
        }

    async def _activate_signal(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Activate a signal."""
        signal_id = parameters.get("signal_id")
        if not signal_id:
            return {"error": "Signal ID is required"}

        # Mock activation
        return {
            "signal_id": signal_id,
            "status": "activated",
            "activated_at": datetime.now(UTC).isoformat()
        }

    async def _deactivate_signal(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Deactivate a signal."""
        signal_id = parameters.get("signal_id")
        if not signal_id:
            return {"error": "Signal ID is required"}

        # Mock deactivation
        return {
            "signal_id": signal_id,
            "status": "deactivated",
            "deactivated_at": datetime.now(UTC).isoformat()
        }

    async def _update_signal(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Update signal status."""
        signal_id = parameters.get("signal_id")
        status = parameters.get("status")

        if not signal_id:
            return {"error": "Signal ID is required"}
        if not status:
            return {"error": "Status is required"}

        # Mock update
        return {
            "signal_id": signal_id,
            "status": status,
            "updated_at": datetime.now(UTC).isoformat()
        }

    async def _list_signals(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List signals based on filter."""
        # Mock signal list
        signals = [
            {
                "id": "sig_001",
                "symbol": "BTC/USDT",
                "type": "BUY",
                "status": "active",
                "confidence": 0.85,
                "created_at": datetime.now(UTC).isoformat()
            },
            {
                "id": "sig_002",
                "symbol": "ETH/USDT",
                "type": "SELL",
                "status": "pending",
                "confidence": 0.72,
                "created_at": datetime.now(UTC).isoformat()
            }
        ]

        return {
            "signals": signals,
            "count": len(signals),
            "filter": parameters.get("filter", {})
        }


class SignalAgent(BaseAgent):
    """Agent responsible for signal generation and management."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "signal_agent", config)
        self._active_signals: dict[str, Signal] = {}
        self._signal_requests: dict[str, SignalRequest] = {}
        self._signal_history: list[SignalResult] = []

        # Register message handlers
        self.register_message_handler(MessageType.TASK, self._handle_task)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

        # Register tools
        self.register_tool(SignalGenerationTool())
        self.register_tool(SignalManagementTool())

    async def _initialize(self) -> None:
        """Initialize the signal agent."""
        self.logger.info("Initializing signal agent")

        # Load configuration
        self._load_config()

        # Initialize signal storage
        self._initialize_storage()

        self.logger.info("Signal agent initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup the signal agent."""
        self.logger.info("Cleaning up signal agent")

        # Save active signals
        self._save_active_signals()

        # Save signal history
        self._save_signal_history()

        self.logger.info("Signal agent cleanup completed")

    def _load_config(self) -> None:
        """Load agent configuration."""
        # Load configuration from config
        self._max_active_signals = self.config.get("max_active_signals", 100)
        self._signal_expiry_hours = self.config.get("signal_expiry_hours", 24)
        self._min_confidence = self.config.get("min_confidence", 0.6)
        self._auto_expiry = self.config.get("auto_expiry", True)

    def _initialize_storage(self) -> None:
        """Initialize signal storage."""
        # In a real implementation, this would connect to a database
        # For now, we'll use in-memory storage
        self.logger.info("Initialized in-memory signal storage")

    async def _handle_task(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "generate_signal":
                await self._generate_signal(message)
            elif task_type == "manage_signal":
                await self._manage_signal(message)
            elif task_type == "get_signals":
                await self._get_signals(message)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Task handling error: {e}")

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        try:
            data_type = message.body.get("data_type")

            if data_type == "market_data":
                await self._process_market_data(message)
            elif data_type == "analysis_result":
                await self._process_analysis_result(message)
            else:
                self.logger.debug(f"Unhandled data update type: {data_type}")

        except Exception as e:
            self.logger.error(f"Data update handling error: {e}")

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        try:
            command = message.body.get("command")

            if command == "status":
                await self._send_status(message)
            elif command == "clear_expired":
                await self._clear_expired_signals(message)
            elif command == "get_stats":
                await self._send_stats(message)
            else:
                self.logger.warning(f"Unknown command: {command}")

        except Exception as e:
            self.logger.error(f"Command handling error: {e}")

    async def _generate_signal(self, message: Message) -> None:
        """Generate a new signal."""
        try:
            symbol = message.body.get("symbol")
            analysis_type = message.body.get("analysis_type", "composite")

            if not symbol:
                self.logger.error("Symbol is required for signal generation")
                return

            # Create signal request
            request = SignalRequest(
                symbol=symbol,
                analysis_type=analysis_type,
                parameters=message.body.get("parameters", {})
            )

            self._signal_requests[request.id] = request

            # Generate signal using tool
            tool = self.get_tool("signal_generation")
            if tool:
                result = await tool.execute({
                    "symbol": symbol,
                    "analysis_type": analysis_type
                }, Context())

                if "error" not in result:
                    signal_data = result["signal"]
                    signal = Signal(**signal_data)

                    # Store signal
                    self._active_signals[signal.id] = signal

                    # Add to history
                    signal_result = SignalResult(
                        signal=signal,
                        confidence=signal.confidence,
                        metadata=result
                    )
                    self._signal_history.append(signal_result)

                    self.logger.info(f"Generated signal: {signal.id} for {symbol}")

                    # Send result back
                    await self.send_message(Message(
                        type=MessageType.RESULT,
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        subject="signal_generated",
                        body={
                            "signal": signal.to_dict(),
                            "request_id": request.id
                        },
                        reply_to=message.id
                    ))
                else:
                    self.logger.error(f"Signal generation failed: {result['error']}")
            else:
                self.logger.error("Signal generation tool not found")

        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")

    async def _manage_signal(self, message: Message) -> None:
        """Manage an existing signal."""
        try:
            signal_id = message.body.get("signal_id")
            operation = message.body.get("operation")

            if not signal_id or not operation:
                self.logger.error("Signal ID and operation are required")
                return

            tool = self.get_tool("signal_management")
            if tool:
                result = await tool.execute({
                    "operation": operation,
                    "signal_id": signal_id
                }, Context())

                if "error" not in result:
                    self.logger.info(f"Signal {signal_id} {operation} successful")

                    # Send result back
                    await self.send_message(Message(
                        type=MessageType.RESULT,
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        subject="signal_managed",
                        body=result,
                        reply_to=message.id
                    ))
                else:
                    self.logger.error(f"Signal management failed: {result['error']}")
            else:
                self.logger.error("Signal management tool not found")

        except Exception as e:
            self.logger.error(f"Signal management error: {e}")

    async def _get_signals(self, message: Message) -> None:
        """Get signals based on criteria."""
        try:
            filter_criteria = message.body.get("filter", {})

            tool = self.get_tool("signal_management")
            if tool:
                result = await tool.execute({
                    "operation": "list",
                    "filter": filter_criteria
                }, Context())

                # Send result back
                await self.send_message(Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="signals_retrieved",
                    body=result,
                    reply_to=message.id
                ))
            else:
                self.logger.error("Signal management tool not found")

        except Exception as e:
            self.logger.error(f"Get signals error: {e}")

    async def _process_market_data(self, message: Message) -> None:
        """Process market data updates."""
        try:
            symbol = message.body.get("symbol")
            price = message.body.get("price")

            if symbol and price:
                # Check if any active signals need to be triggered
                await self._check_signal_triggers(symbol, price)

        except Exception as e:
            self.logger.error(f"Market data processing error: {e}")

    async def _process_analysis_result(self, message: Message) -> None:
        """Process analysis results from other agents."""
        try:
            analysis_type = message.body.get("analysis_type")
            result = message.body.get("result")

            if analysis_type and result:
                # Store analysis result for signal generation
                self.logger.debug(f"Stored {analysis_type} analysis result")

        except Exception as e:
            self.logger.error(f"Analysis result processing error: {e}")

    async def _check_signal_triggers(self, symbol: str, price: float) -> None:
        """Check if any signals should be triggered."""
        try:
            for signal_id, signal in self._active_signals.items():
                if signal.symbol == symbol:
                    # Check entry price trigger
                    if signal.signal_type == SignalType.BUY and price <= signal.entry_price:
                        await self._trigger_signal(signal_id, "entry_triggered", price)
                    elif signal.signal_type == SignalType.SELL and price >= signal.entry_price:
                        await self._trigger_signal(signal_id, "entry_triggered", price)

                    # Check stop loss and take profit
                    if hasattr(signal, 'stop_loss') and hasattr(signal, 'take_profit'):
                        if price <= signal.stop_loss:
                            await self._trigger_signal(signal_id, "stop_loss_triggered", price)
                        elif price >= signal.take_profit:
                            await self._trigger_signal(signal_id, "take_profit_triggered", price)

        except Exception as e:
            self.logger.error(f"Signal trigger check error: {e}")

    async def _trigger_signal(self, signal_id: str, trigger_type: str, price: float) -> None:
        """Trigger a signal."""
        try:
            signal = self._active_signals.get(signal_id)
            if signal:
                self.logger.info(f"Signal {signal_id} {trigger_type} at price {price}")

                # Update signal status
                signal.metadata["triggered"] = True
                signal.metadata["trigger_type"] = trigger_type
                signal.metadata["trigger_price"] = price
                signal.metadata["triggered_at"] = datetime.now(UTC).isoformat()

                # Send notification
                await self.send_message(Message(
                    type=MessageType.DATA_UPDATE,
                    from_agent=self.agent_id,
                    to_agent="orchestrator",
                    subject="signal_triggered",
                    body={
                        "signal_id": signal_id,
                        "trigger_type": trigger_type,
                        "price": price,
                        "signal": signal.to_dict()
                    }
                ))

        except Exception as e:
            self.logger.error(f"Signal trigger error: {e}")

    async def _send_status(self, message: Message) -> None:
        """Send agent status."""
        try:
            status = {
                "active_signals": len(self._active_signals),
                "pending_requests": len(self._signal_requests),
                "signal_history": len(self._signal_history),
                "last_activity": self._last_activity.isoformat() if self._last_activity else None
            }

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="status",
                body=status,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Status send error: {e}")

    async def _clear_expired_signals(self, message: Message) -> None:
        """Clear expired signals."""
        try:
            if not self._auto_expiry:
                return

            current_time = datetime.now(UTC)
            expired_signals = []

            for signal_id, signal in self._active_signals.items():
                if hasattr(signal, 'created_at'):
                    created_at = signal.created_at
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)

                    if (current_time - created_at).total_seconds() > (self._signal_expiry_hours * 3600):
                        expired_signals.append(signal_id)

            for signal_id in expired_signals:
                del self._active_signals[signal_id]

            self.logger.info(f"Cleared {len(expired_signals)} expired signals")

            # Send result back
            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="expired_signals_cleared",
                body={"cleared_count": len(expired_signals)},
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Clear expired signals error: {e}")

    async def _send_stats(self, message: Message) -> None:
        """Send agent statistics."""
        try:
            stats = {
                "total_signals_generated": len(self._signal_history),
                "active_signals": len(self._active_signals),
                "signals_by_type": self._get_signals_by_type(),
                "average_confidence": self._calculate_average_confidence(),
                "uptime_seconds": (datetime.now(UTC) - self._start_time).total_seconds() if self._start_time else 0
            }

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="stats",
                body=stats,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Stats send error: {e}")

    def _get_signals_by_type(self) -> dict[str, int]:
        """Get count of signals by type."""
        counts = {}
        for signal in self._active_signals.values():
            signal_type = signal.signal_type.value
            counts[signal_type] = counts.get(signal_type, 0) + 1
        return counts

    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence of active signals."""
        if not self._active_signals:
            return 0.0

        total_confidence = sum(signal.confidence for signal in self._active_signals.values())
        return total_confidence / len(self._active_signals)

    def _save_active_signals(self) -> None:
        """Save active signals to storage."""
        # In a real implementation, this would save to a database
        self.logger.debug("Active signals saved to storage")

    def _save_signal_history(self) -> None:
        """Save signal history to storage."""
        # In a real implementation, this would save to a database
        self.logger.debug("Signal history saved to storage")
