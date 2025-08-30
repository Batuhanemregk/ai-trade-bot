"""
Portfolio Agent for the AiBotBS Runtime Agent System.
Responsible for portfolio management, position tracking, and PnL calculations.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from domain.models import Money, Portfolio, Position, Price, Quantity

from ..core.base import BaseAgent, Context, Message, MessageType
from ..core.tools import Tool


class PortfolioStatus(Enum):
    """Portfolio status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"


class RiskLevel(Enum):
    """Portfolio risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_value: Money
    total_pnl: Money
    daily_pnl: Money
    weekly_pnl: Money
    monthly_pnl: Money
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    open_positions: int
    risk_level: RiskLevel
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PositionUpdate:
    """Position update event."""
    position_id: str
    symbol: str
    side: str
    size: Quantity
    entry_price: Price
    current_price: Price
    unrealized_pnl: Money
    realized_pnl: Money
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PortfolioAnalysisTool(Tool):
    """Tool for portfolio analysis."""

    def __init__(self):
        super().__init__("portfolio_analysis", "Analyze portfolio performance and risk")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute portfolio analysis."""
        try:
            analysis_type = parameters.get("analysis_type")

            if analysis_type == "performance":
                return await self._analyze_performance(parameters)
            elif analysis_type == "risk":
                return await self._analyze_risk(parameters)
            elif analysis_type == "allocation":
                return await self._analyze_allocation(parameters)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "analysis_type": {
                "type": "string",
                "enum": ["performance", "risk", "allocation"],
                "description": "Type of portfolio analysis to perform"
            },
            "timeframe": {
                "type": "string",
                "description": "Analysis timeframe (e.g., 1d, 1w, 1m, 1y)"
            },
            "include_closed": {
                "type": "boolean",
                "description": "Include closed positions in analysis"
            }
        }

    async def _analyze_performance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Analyze portfolio performance."""
        # Mock performance analysis
        return {
            "total_return": 0.15,
            "annualized_return": 0.18,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.5,
            "max_drawdown": -0.08,
            "win_rate": 0.65,
            "profit_factor": 1.8,
            "average_trade": 0.02
        }

    async def _analyze_risk(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Analyze portfolio risk."""
        # Mock risk analysis
        return {
            "var_95": -0.03,
            "var_99": -0.05,
            "expected_shortfall": -0.04,
            "volatility": 0.25,
            "beta": 0.8,
            "correlation": 0.6,
            "concentration_risk": "medium",
            "liquidity_risk": "low"
        }

    async def _analyze_allocation(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Analyze portfolio allocation."""
        # Mock allocation analysis
        return {
            "by_asset": {
                "BTC": 0.4,
                "ETH": 0.3,
                "USDT": 0.2,
                "Other": 0.1
            },
            "by_sector": {
                "DeFi": 0.5,
                "Layer1": 0.3,
                "Stablecoins": 0.2
            },
            "by_geography": {
                "Global": 1.0
            }
        }


class PositionManagementTool(Tool):
    """Tool for position management."""

    def __init__(self):
        super().__init__("position_management", "Manage portfolio positions")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute position management operation."""
        try:
            operation = parameters.get("operation")

            if operation == "get_positions":
                return await self._get_positions(parameters)
            elif operation == "close_position":
                return await self._close_position(parameters)
            elif operation == "adjust_position":
                return await self._adjust_position(parameters)
            elif operation == "get_position_history":
                return await self._get_position_history(parameters)
            else:
                raise ValueError(f"Unknown position operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["get_positions", "close_position", "adjust_position", "get_position_history"],
                "description": "Position management operation to perform"
            },
            "position_id": {
                "type": "string",
                "description": "Position ID for close/adjust operations"
            },
            "symbol": {
                "type": "string",
                "description": "Trading symbol for filtering positions"
            },
            "adjustment": {
                "type": "object",
                "description": "Position adjustment parameters"
            }
        }

    async def _get_positions(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get current positions."""
        # Mock positions
        positions = [
            {
                "id": "pos_001",
                "symbol": "BTC/USDT",
                "side": "long",
                "size": 0.1,
                "entry_price": 50000.0,
                "current_price": 52000.0,
                "unrealized_pnl": 200.0,
                "margin": 5000.0
            },
            {
                "id": "pos_002",
                "symbol": "ETH/USDT",
                "side": "short",
                "size": 2.0,
                "entry_price": 3000.0,
                "current_price": 2900.0,
                "unrealized_pnl": 200.0,
                "margin": 3000.0
            }
        ]

        return {
            "positions": positions,
            "count": len(positions),
            "total_unrealized_pnl": 400.0
        }

    async def _close_position(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Close a position."""
        position_id = parameters.get("position_id")
        if not position_id:
            return {"error": "Position ID is required"}

        # Mock position closure
        return {
            "position_id": position_id,
            "status": "closed",
            "closed_at": datetime.now(UTC).isoformat(),
            "realized_pnl": 150.0
        }

    async def _adjust_position(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Adjust a position."""
        position_id = parameters.get("position_id")
        adjustment = parameters.get("adjustment", {})

        if not position_id:
            return {"error": "Position ID is required"}
        if not adjustment:
            return {"error": "Adjustment parameters are required"}

        # Mock position adjustment
        return {
            "position_id": position_id,
            "status": "adjusted",
            "adjustment": adjustment,
            "adjusted_at": datetime.now(UTC).isoformat()
        }

    async def _get_position_history(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get position history."""
        # Mock position history
        history = [
            {
                "id": "pos_001",
                "symbol": "BTC/USDT",
                "side": "long",
                "size": 0.1,
                "entry_price": 50000.0,
                "exit_price": 52000.0,
                "realized_pnl": 200.0,
                "duration_hours": 24
            }
        ]

        return {
            "history": history,
            "count": len(history),
            "total_realized_pnl": 200.0
        }


class PortfolioAgent(BaseAgent):
    """Agent responsible for portfolio management and monitoring."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "portfolio_agent", config)
        self._portfolio: Portfolio | None = None
        self._positions: dict[str, Position] = {}
        self._position_history: list[Position] = []
        self._metrics_history: list[PortfolioMetrics] = []

        # Register message handlers
        self.register_message_handler(MessageType.TASK, self._handle_task)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

        # Register tools
        self.register_tool(PortfolioAnalysisTool())
        self.register_tool(PositionManagementTool())

    async def _initialize(self) -> None:
        """Initialize the portfolio agent."""
        self.logger.info("Initializing portfolio agent")

        # Load configuration
        self._load_config()

        # Initialize portfolio
        await self._initialize_portfolio()

        # Initialize positions
        await self._initialize_positions()

        self.logger.info("Portfolio agent initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup the portfolio agent."""
        self.logger.info("Cleaning up portfolio agent")

        # Save portfolio state
        await self._save_portfolio_state()

        # Save position history
        await self._save_position_history()

        self.logger.info("Portfolio agent cleanup completed")

    def _load_config(self) -> None:
        """Load agent configuration."""
        self._max_positions = self.config.get("max_positions", 20)
        self._max_position_size = self.config.get("max_position_size", 0.1)
        self._max_drawdown = self.config.get("max_drawdown", 0.2)
        self._rebalance_threshold = self.config.get("rebalance_threshold", 0.1)
        self._update_interval = self.config.get("update_interval", 60)

    async def _initialize_portfolio(self) -> None:
        """Initialize portfolio."""
        try:
            # In a real implementation, this would load from a database
            # For now, create a mock portfolio
            self._portfolio = Portfolio(
                id="portfolio_001",
                total_value=Money(amount=10000, currency="USDT"),
                available_balance=Money(amount=10000, currency="USDT")
            )

            self.logger.info(f"Initialized portfolio: {self._portfolio.id}")

        except Exception as e:
            self.logger.error(f"Failed to initialize portfolio: {e}")
            raise

    async def _initialize_positions(self) -> None:
        """Initialize positions."""
        try:
            # In a real implementation, this would load from a database
            # For now, start with empty positions
            self._positions = {}
            self.logger.info("Initialized empty position tracking")

        except Exception as e:
            self.logger.error(f"Failed to initialize positions: {e}")
            raise

    async def _handle_task(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "analyze_portfolio":
                await self._analyze_portfolio(message)
            elif task_type == "manage_position":
                await self._manage_position(message)
            elif task_type == "rebalance_portfolio":
                await self._rebalance_portfolio(message)
            elif task_type == "get_portfolio_status":
                await self._get_portfolio_status(message)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Task handling error: {e}")

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        try:
            data_type = message.body.get("data_type")

            if data_type == "position_update":
                await self._process_position_update(message)
            elif data_type == "market_data":
                await self._process_market_data(message)
            elif data_type == "trade_execution":
                await self._process_trade_execution(message)
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
            elif command == "positions":
                await self._send_positions(message)
            elif command == "metrics":
                await self._send_metrics(message)
            elif command == "rebalance":
                await self._rebalance_portfolio(message)
            else:
                self.logger.warning(f"Unknown command: {command}")

        except Exception as e:
            self.logger.error(f"Command handling error: {e}")

    async def _analyze_portfolio(self, message: Message) -> None:
        """Analyze portfolio performance and risk."""
        try:
            analysis_type = message.body.get("analysis_type", "all")

            tool = self.get_tool("portfolio_analysis")
            if tool:
                results = {}

                if analysis_type in ["all", "performance"]:
                    perf_result = await tool.execute({"analysis_type": "performance"}, Context())
                    if "error" not in perf_result:
                        results["performance"] = perf_result

                if analysis_type in ["all", "risk"]:
                    risk_result = await tool.execute({"analysis_type": "risk"}, Context())
                    if "error" not in risk_result:
                        results["risk"] = risk_result

                if analysis_type in ["all", "allocation"]:
                    alloc_result = await tool.execute({"analysis_type": "allocation"}, Context())
                    if "error" not in alloc_result:
                        results["allocation"] = alloc_result

                # Send results back
                await self.send_message(Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="portfolio_analysis",
                    body=results,
                    reply_to=message.id
                ))

                # Update metrics history
                await self._update_portfolio_metrics(results)

            else:
                self.logger.error("Portfolio analysis tool not found")

        except Exception as e:
            self.logger.error(f"Portfolio analysis error: {e}")

    async def _manage_position(self, message: Message) -> None:
        """Manage portfolio positions."""
        try:
            operation = message.body.get("operation")

            tool = self.get_tool("position_management")
            if tool:
                result = await tool.execute({
                    "operation": operation,
                    **message.body
                }, Context())

                if "error" not in result:
                    self.logger.info(f"Position {operation} successful")

                    # Send result back
                    await self.send_message(Message(
                        type=MessageType.RESULT,
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        subject="position_managed",
                        body=result,
                        reply_to=message.id
                    ))

                    # Update local state if needed
                    if operation == "close_position":
                        await self._remove_position(result.get("position_id"))
                    elif operation == "adjust_position":
                        await self._update_position(result.get("position_id"), result.get("adjustment"))

                else:
                    self.logger.error(f"Position management failed: {result['error']}")
            else:
                self.logger.error("Position management tool not found")

        except Exception as e:
            self.logger.error(f"Position management error: {e}")

    async def _rebalance_portfolio(self, message: Message) -> None:
        """Rebalance portfolio based on target allocation."""
        try:
            target_allocation = message.body.get("target_allocation", {})

            if not target_allocation:
                # Use default allocation
                target_allocation = {
                    "BTC": 0.4,
                    "ETH": 0.3,
                    "USDT": 0.2,
                    "Other": 0.1
                }

            # Calculate current allocation
            current_allocation = await self._calculate_current_allocation()

            # Calculate rebalancing trades
            rebalancing_trades = await self._calculate_rebalancing_trades(
                current_allocation, target_allocation
            )

            # Send rebalancing plan
            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="portfolio_rebalanced",
                body={
                    "current_allocation": current_allocation,
                    "target_allocation": target_allocation,
                    "rebalancing_trades": rebalancing_trades,
                    "estimated_cost": self._estimate_rebalancing_cost(rebalancing_trades)
                },
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Portfolio rebalancing error: {e}")

    async def _get_portfolio_status(self, message: Message) -> None:
        """Get current portfolio status."""
        try:
            status = {
                "portfolio": self._portfolio.to_dict() if self._portfolio else None,
                "positions_count": len(self._positions),
                "total_value": await self._calculate_total_value(),
                "unrealized_pnl": await self._calculate_unrealized_pnl(),
                "last_update": self._last_activity.isoformat() if self._last_activity else None
            }

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="portfolio_status",
                body=status,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Portfolio status error: {e}")

    async def _process_position_update(self, message: Message) -> None:
        """Process position updates."""
        try:
            position_data = message.body.get("position")
            if position_data:
                position_id = position_data.get("id")

                if position_id in self._positions:
                    # Update existing position
                    await self._update_position_data(position_id, position_data)
                else:
                    # Add new position
                    await self._add_position(position_data)

                # Check risk limits
                await self._check_risk_limits()

        except Exception as e:
            self.logger.error(f"Position update processing error: {e}")

    async def _process_market_data(self, message: Message) -> None:
        """Process market data updates."""
        try:
            symbol = message.body.get("symbol")
            price = message.body.get("price")

            if symbol and price:
                # Update position prices
                await self._update_position_prices(symbol, price)

                # Check if rebalancing is needed
                await self._check_rebalancing_needed()

        except Exception as e:
            self.logger.error(f"Market data processing error: {e}")

    async def _process_trade_execution(self, message: Message) -> None:
        """Process trade execution updates."""
        try:
            trade_data = message.body.get("trade")
            if trade_data:
                # Update portfolio balance
                await self._update_portfolio_balance(trade_data)

                # Update position if applicable
                if "position_id" in trade_data:
                    await self._update_position_from_trade(trade_data)

                # Log trade
                self.logger.info(f"Trade executed: {trade_data.get('id')}")

        except Exception as e:
            self.logger.error(f"Trade execution processing error: {e}")

    async def _update_position_data(self, position_id: str, data: dict[str, Any]) -> None:
        """Update position data."""
        try:
            if position_id in self._positions:
                position = self._positions[position_id]

                # Update position fields
                for key, value in data.items():
                    if hasattr(position, key):
                        setattr(position, key, value)

                self.logger.debug(f"Updated position: {position_id}")

        except Exception as e:
            self.logger.error(f"Position update error: {e}")

    async def _add_position(self, position_data: dict[str, Any]) -> None:
        """Add new position."""
        try:
            position_id = position_data.get("id")
            if position_id and position_id not in self._positions:
                # Create position object
                position = Position(**position_data)
                self._positions[position_id] = position

                self.logger.info(f"Added new position: {position_id}")

                # Check position limits
                await self._check_position_limits()

        except Exception as e:
            self.logger.error(f"Add position error: {e}")

    async def _remove_position(self, position_id: str) -> None:
        """Remove position."""
        try:
            if position_id in self._positions:
                position = self._positions.pop(position_id)

                # Add to history
                self._position_history.append(position)

                self.logger.info(f"Removed position: {position_id}")

        except Exception as e:
            self.logger.error(f"Remove position error: {e}")

    async def _update_position_prices(self, symbol: str, price: float) -> None:
        """Update position prices for a symbol."""
        try:
            for position in self._positions.values():
                if position.symbol == symbol:
                    # Update current price
                    if hasattr(position, 'current_price'):
                        position.current_price = Price(amount=price, currency="USDT")

                    # Recalculate unrealized PnL
                    if hasattr(position, 'entry_price') and hasattr(position, 'size'):
                        entry_price = float(position.entry_price.amount)
                        size = float(position.size.amount)

                        if position.side == "long":
                            unrealized_pnl = (price - entry_price) * size
                        else:
                            unrealized_pnl = (entry_price - price) * size

                        if hasattr(position, 'unrealized_pnl'):
                            position.unrealized_pnl = Money(amount=unrealized_pnl, currency="USDT")

        except Exception as e:
            self.logger.error(f"Position price update error: {e}")

    async def _check_risk_limits(self) -> None:
        """Check portfolio risk limits."""
        try:
            total_value = await self._calculate_total_value()
            unrealized_pnl = await self._calculate_unrealized_pnl()

            # Check drawdown
            if total_value > 0:
                drawdown = abs(unrealized_pnl / total_value)
                if drawdown > self._max_drawdown:
                    self.logger.warning(f"Risk limit exceeded: drawdown {drawdown:.2%} > {self._max_drawdown:.2%}")

                    # Send risk alert
                    await self.send_message(Message(
                        type=MessageType.DATA_UPDATE,
                        from_agent=self.agent_id,
                        to_agent="risk_agent",
                        subject="risk_limit_exceeded",
                        body={
                            "risk_type": "drawdown",
                            "current_value": drawdown,
                            "limit": self._max_drawdown,
                            "portfolio_id": self._portfolio.id if self._portfolio else None
                        }
                    ))

        except Exception as e:
            self.logger.error(f"Risk limit check error: {e}")

    async def _check_position_limits(self) -> None:
        """Check position size limits."""
        try:
            for position_id, position in self._positions.items():
                if hasattr(position, 'size'):
                    size = float(position.size.amount)
                    if size > self._max_position_size:
                        self.logger.warning(f"Position size limit exceeded: {size} > {self._max_position_size}")

                        # Send position limit alert
                        await self.send_message(Message(
                            type=MessageType.DATA_UPDATE,
                            from_agent=self.agent_id,
                            to_agent="risk_agent",
                            subject="position_limit_exceeded",
                            body={
                                "position_id": position_id,
                                "current_size": size,
                                "limit": self._max_position_size
                            }
                        ))

        except Exception as e:
            self.logger.error(f"Position limit check error: {e}")

    async def _check_rebalancing_needed(self) -> None:
        """Check if portfolio rebalancing is needed."""
        try:
            current_allocation = await self._calculate_current_allocation()
            target_allocation = {
                "BTC": 0.4,
                "ETH": 0.3,
                "USDT": 0.2,
                "Other": 0.1
            }

            for asset, target_weight in target_allocation.items():
                current_weight = current_allocation.get(asset, 0)
                if abs(current_weight - target_weight) > self._rebalance_threshold:
                    self.logger.info(f"Rebalancing needed for {asset}: {current_weight:.2%} vs {target_weight:.2%}")

                    # Send rebalancing notification
                    await self.send_message(Message(
                        type=MessageType.DATA_UPDATE,
                        from_agent=self.agent_id,
                        to_agent="orchestrator",
                        subject="rebalancing_needed",
                        body={
                            "asset": asset,
                            "current_weight": current_weight,
                            "target_weight": target_weight,
                            "threshold": self._rebalance_threshold
                        }
                    ))
                    break

        except Exception as e:
            self.logger.error(f"Rebalancing check error: {e}")

    async def _calculate_current_allocation(self) -> dict[str, float]:
        """Calculate current portfolio allocation."""
        try:
            total_value = await self._calculate_total_value()
            if total_value <= 0:
                return {}

            allocation = {}
            for position in self._positions.values():
                if hasattr(position, 'symbol') and hasattr(position, 'unrealized_pnl'):
                    symbol = position.symbol.split('/')[0]  # Extract base asset
                    position_value = float(position.unrealized_pnl.amount)
                    allocation[symbol] = allocation.get(symbol, 0) + position_value

            # Normalize to percentages
            for asset in allocation:
                allocation[asset] = allocation[asset] / total_value

            return allocation

        except Exception as e:
            self.logger.error(f"Allocation calculation error: {e}")
            return {}

    async def _calculate_rebalancing_trades(self, current: dict[str, float], target: dict[str, float]) -> list[dict[str, Any]]:
        """Calculate rebalancing trades needed."""
        try:
            trades = []
            total_value = await self._calculate_total_value()

            for asset, target_weight in target.items():
                current_weight = current.get(asset, 0)
                weight_diff = target_weight - current_weight

                if abs(weight_diff) > self._rebalance_threshold:
                    trade_value = weight_diff * total_value
                    trades.append({
                        "asset": asset,
                        "action": "buy" if trade_value > 0 else "sell",
                        "value": abs(trade_value),
                        "current_weight": current_weight,
                        "target_weight": target_weight
                    })

            return trades

        except Exception as e:
            self.logger.error(f"Rebalancing trade calculation error: {e}")
            return []

    def _estimate_rebalancing_cost(self, trades: list[dict[str, Any]]) -> float:
        """Estimate cost of rebalancing trades."""
        try:
            total_cost = 0.0
            for trade in trades:
                # Assume 0.1% trading fee
                fee = trade["value"] * 0.001
                total_cost += fee

            return total_cost

        except Exception as e:
            self.logger.error(f"Cost estimation error: {e}")
            return 0.0

    async def _calculate_total_value(self) -> float:
        """Calculate total portfolio value."""
        try:
            if not self._portfolio:
                return 0.0

            base_value = float(self._portfolio.current_balance.amount)
            position_value = sum(
                float(pos.unrealized_pnl.amount) if hasattr(pos, 'unrealized_pnl') else 0
                for pos in self._positions.values()
            )

            return base_value + position_value

        except Exception as e:
            self.logger.error(f"Total value calculation error: {e}")
            return 0.0

    async def _calculate_unrealized_pnl(self) -> float:
        """Calculate total unrealized PnL."""
        try:
            return sum(
                float(pos.unrealized_pnl.amount) if hasattr(pos, 'unrealized_pnl') else 0
                for pos in self._positions.values()
            )

        except Exception as e:
            self.logger.error(f"Unrealized PnL calculation error: {e}")
            return 0.0

    async def _update_portfolio_metrics(self, analysis_results: dict[str, Any]) -> None:
        """Update portfolio metrics."""
        try:
            total_value = await self._calculate_total_value()
            unrealized_pnl = await self._calculate_unrealized_pnl()

            metrics = PortfolioMetrics(
                total_value=Money(amount=total_value, currency="USDT"),
                total_pnl=Money(amount=unrealized_pnl, currency="USDT"),
                daily_pnl=Money(amount=0, currency="USDT"),  # Would calculate from history
                weekly_pnl=Money(amount=0, currency="USDT"),
                monthly_pnl=Money(amount=0, currency="USDT"),
                sharpe_ratio=analysis_results.get("performance", {}).get("sharpe_ratio", 0.0),
                max_drawdown=analysis_results.get("performance", {}).get("max_drawdown", 0.0),
                win_rate=analysis_results.get("performance", {}).get("win_rate", 0.0),
                total_trades=len(self._position_history),
                open_positions=len(self._positions),
                risk_level=RiskLevel.MEDIUM  # Would calculate from risk analysis
            )

            self._metrics_history.append(metrics)

            # Keep only last 1000 metrics
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-1000:]

        except Exception as e:
            self.logger.error(f"Metrics update error: {e}")

    async def _send_status(self, message: Message) -> None:
        """Send agent status."""
        try:
            status = {
                "portfolio_id": self._portfolio.id if self._portfolio else None,
                "positions_count": len(self._positions),
                "total_value": await self._calculate_total_value(),
                "unrealized_pnl": await self._calculate_unrealized_pnl(),
                "last_update": self._last_activity.isoformat() if self._last_activity else None
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

    async def _send_positions(self, message: Message) -> None:
        """Send current positions."""
        try:
            positions_data = []
            for position in self._positions.values():
                positions_data.append(position.to_dict())

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="positions",
                body={
                    "positions": positions_data,
                    "count": len(positions_data)
                },
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Positions send error: {e}")

    async def _send_metrics(self, message: Message) -> None:
        """Send portfolio metrics."""
        try:
            if self._metrics_history:
                latest_metrics = self._metrics_history[-1]
                metrics_data = {
                    "current": latest_metrics.__dict__,
                    "history_count": len(self._metrics_history)
                }
            else:
                metrics_data = {"current": None, "history_count": 0}

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="metrics",
                body=metrics_data,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Metrics send error: {e}")

    async def _save_portfolio_state(self) -> None:
        """Save portfolio state to storage."""
        try:
            # In a real implementation, this would save to a database
            self.logger.debug("Portfolio state saved to storage")

        except Exception as e:
            self.logger.error(f"Portfolio state save error: {e}")

    async def _save_position_history(self) -> None:
        """Save position history to storage."""
        try:
            # In a real implementation, this would save to a database
            self.logger.debug("Position history saved to storage")

        except Exception as e:
            self.logger.error(f"Position history save error: {e}")
