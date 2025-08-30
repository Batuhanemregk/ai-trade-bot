"""
Risk Management Agent for AiBotBS.
Performs risk assessment, position monitoring, and risk limit enforcement.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from domain.errors import AgentError
from domain.models import (
    Money,
    Position,
    PositionSide,
    Price,
    Quantity,
    RiskLevel,
)

from ..core.base import BaseAgent, Message, MessageType
from ..core.tools import Tool, ToolCategory


@dataclass
class RiskMetrics:
    """Risk metrics for a position or portfolio."""
    symbol: str
    timestamp: datetime
    position_size: float
    notional_value: float
    unrealized_pnl: float
    realized_pnl: float
    margin_used: float
    margin_ratio: float
    leverage: float
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    drawdown: float
    var_95: float  # Value at Risk (95% confidence)
    max_position_size: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAlert:
    """Risk alert for monitoring."""
    id: str
    symbol: str
    alert_type: str  # "margin_call", "stop_loss", "position_limit", "drawdown"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    timestamp: datetime
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size: float
    max_leverage: float
    max_drawdown: float
    max_margin_ratio: float
    max_risk_per_trade: float
    max_portfolio_risk: float
    stop_loss_threshold: float
    take_profit_threshold: float
    metadata: dict[str, Any] = field(default_factory=dict)


class RiskManagementAgent(BaseAgent):
    """Risk management agent that monitors positions and enforces risk limits."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "risk_agent", config)

        # Risk configuration
        self._risk_limits = RiskLimits(
            max_position_size=config.get("max_position_size", 100000.0),
            max_leverage=config.get("max_leverage", 10.0),
            max_drawdown=config.get("max_drawdown", 0.20),  # 20%
            max_margin_ratio=config.get("max_margin_ratio", 0.80),  # 80%
            max_risk_per_trade=config.get("max_risk_per_trade", 0.02),  # 2%
            max_portfolio_risk=config.get("max_portfolio_risk", 0.10),  # 10%
            stop_loss_threshold=config.get("stop_loss_threshold", 0.05),  # 5%
            take_profit_threshold=config.get("take_profit_threshold", 0.10)  # 10%
        )

        # Risk monitoring
        self._positions: dict[str, Position] = {}
        self._risk_metrics: dict[str, RiskMetrics] = {}
        self._active_alerts: dict[str, RiskAlert] = {}
        self._risk_history: list[RiskMetrics] = []

        # Performance tracking
        self._risk_checks_performed = 0
        self._alerts_generated = 0
        self._risk_violations = 0
        self._last_risk_check = None

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the risk agent."""
        self.logger.info("Initializing risk management agent")

        # Validate configuration
        self._validate_config()

        # Start risk monitoring loop
        asyncio.create_task(self._risk_monitoring_loop())

        # Start alert monitoring
        asyncio.create_task(self._alert_monitoring_loop())

        self.logger.info("Risk management agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up risk management agent")
        self.logger.info("Risk management agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register risk-specific tools."""
        from ..core.tools import get_tool_registry

        registry = get_tool_registry()
        registry.register_tool(RiskAssessmentTool(self), ToolCategory.ANALYSIS)
        registry.register_tool(RiskMonitoringTool(self), ToolCategory.MONITORING)
        registry.register_tool(RiskLimitTool(self), ToolCategory.UTILITY)

    def _validate_config(self) -> None:
        """Validate agent configuration."""
        if self._risk_limits.max_leverage <= 0:
            self.logger.warning("Max leverage must be positive")

        if self._risk_limits.max_drawdown <= 0 or self._risk_limits.max_drawdown >= 1.0:
            self.logger.warning("Max drawdown must be between 0 and 1")

        if self._risk_limits.max_margin_ratio <= 0 or self._risk_limits.max_margin_ratio >= 1.0:
            self.logger.warning("Max margin ratio must be between 0 and 1")

    async def _risk_monitoring_loop(self) -> None:
        """Main loop for risk monitoring."""
        while self._running:
            try:
                await self._perform_risk_assessment()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Risk monitoring loop error: {e}")
                await asyncio.sleep(60)

    async def _alert_monitoring_loop(self) -> None:
        """Main loop for alert monitoring."""
        while self._running:
            try:
                await self._process_alerts()
                await asyncio.sleep(30)  # Process alerts every 30 seconds
            except Exception as e:
                self.logger.error(f"Alert monitoring loop error: {e}")
                await asyncio.sleep(60)

    async def _perform_risk_assessment(self) -> None:
        """Perform comprehensive risk assessment."""
        try:
            self.logger.debug("Performing risk assessment")

            # Update positions if available
            await self._update_positions()

            # Calculate risk metrics for each position
            for symbol, position in self._positions.items():
                risk_metrics = await self._calculate_position_risk(position)
                self._risk_metrics[symbol] = risk_metrics

                # Check for risk violations
                violations = await self._check_risk_violations(risk_metrics)
                if violations:
                    await self._generate_risk_alerts(symbol, violations)

            # Calculate portfolio-level risk
            portfolio_risk = await self._calculate_portfolio_risk()

            # Update history
            self._risk_history.extend(list(self._risk_metrics.values()))
            if len(self._risk_history) > 1000:  # Keep last 1000 records
                self._risk_history = self._risk_history[-1000:]

            self._risk_checks_performed += 1
            self._last_risk_check = datetime.utcnow()

            self.logger.debug("Risk assessment completed")

        except Exception as e:
            self.logger.error(f"Risk assessment failed: {e}")

    async def _update_positions(self) -> None:
        """Update position information."""
        try:
            # This would typically fetch from exchange or portfolio manager
            # For now, we'll use mock data
            if not self._positions:
                await self._load_mock_positions()

        except Exception as e:
            self.logger.error(f"Failed to update positions: {e}")

    async def _load_mock_positions(self) -> None:
        """Load mock positions for testing."""
        mock_positions = {
            "BTC/USDT": Position(
                id="pos_btc_001",
                symbol="BTC/USDT",
                side=PositionSide.LONG,
                quantity=Quantity(Decimal('0.5')),
                entry_price=Price(Decimal('50000.0')),
                current_price=Price(Decimal('52000.0')),
                unrealized_pnl=Money(Decimal('1000.0'), "USDT"),
                realized_pnl=Money(Decimal('0.0'), "USDT"),
                margin=Money(Decimal('2500.0'), "USDT"),
                leverage=10.0
            ),
            "ETH/USDT": Position(
                id="pos_eth_001",
                symbol="ETH/USDT",
                side=PositionSide.SHORT,
                quantity=Quantity(Decimal('2.0')),
                entry_price=Price(Decimal('3000.0')),
                current_price=Price(Decimal('2800.0')),
                unrealized_pnl=Money(Decimal('400.0'), "USDT"),
                realized_pnl=Money(Decimal('0.0'), "USDT"),
                margin=Money(Decimal('300.0'), "USDT"),
                leverage=5.0
            )
        }

        self._positions.update(mock_positions)
        self.logger.info(f"Loaded {len(mock_positions)} mock positions")

    async def _calculate_position_risk(self, position: Position) -> RiskMetrics:
        """Calculate risk metrics for a position."""
        try:
            # Calculate basic metrics
            notional_value = float(position.quantity.value * position.current_price.value)
            margin_ratio = float(position.margin.amount) / notional_value if notional_value > 0 else 0.0

            # Calculate risk score (0.0 to 1.0)
            risk_score = 0.0

            # Leverage risk
            leverage_risk = min(position.leverage / self._risk_limits.max_leverage, 1.0)
            risk_score = max(risk_score, leverage_risk)

            # Margin ratio risk
            margin_risk = min(margin_ratio / self._risk_limits.max_margin_ratio, 1.0)
            risk_score = max(risk_score, margin_risk)

            # Position size risk
            size_risk = min(notional_value / self._risk_limits.max_position_size, 1.0)
            risk_score = max(risk_score, size_risk)

            # PnL risk
            pnl_risk = 0.0
            if position.unrealized_pnl < 0:
                pnl_risk = min(abs(position.unrealized_pnl) / (notional_value * 0.1), 1.0)
            risk_score = max(risk_score, pnl_risk)

            # Determine risk level
            if risk_score >= 0.8:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            elif risk_score >= 0.2:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.MINIMAL

            # Calculate drawdown
            drawdown = 0.0
            if position.unrealized_pnl < 0:
                drawdown = abs(position.unrealized_pnl) / position.margin_used

            # Calculate VaR (simplified)
            var_95 = notional_value * 0.02  # 2% of notional value

            return RiskMetrics(
                symbol=position.symbol,
                timestamp=datetime.utcnow(),
                position_size=float(position.quantity.value),
                notional_value=notional_value,
                unrealized_pnl=float(position.unrealized_pnl.amount),
                realized_pnl=float(position.realized_pnl.amount),
                margin_used=float(position.margin.amount),
                margin_ratio=margin_ratio,
                leverage=position.leverage,
                risk_score=risk_score,
                risk_level=risk_level,
                drawdown=drawdown,
                var_95=var_95,
                max_position_size=self._risk_limits.max_position_size
            )

        except Exception as e:
            self.logger.error(f"Failed to calculate position risk: {e}")
            # Return default risk metrics
            return RiskMetrics(
                symbol=position.symbol,
                timestamp=datetime.utcnow(),
                position_size=float(position.quantity.value),
                notional_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_used=0.0,
                margin_ratio=0.0,
                leverage=1.0,
                risk_score=1.0,
                risk_level=RiskLevel.CRITICAL,
                drawdown=0.0,
                var_95=0.0,
                max_position_size=self._risk_limits.max_position_size
            )

    async def _check_risk_violations(self, risk_metrics: RiskMetrics) -> list[str]:
        """Check for risk limit violations."""
        violations = []

        try:
            # Check leverage
            if risk_metrics.leverage > self._risk_limits.max_leverage:
                violations.append("leverage_exceeded")

            # Check margin ratio
            if risk_metrics.margin_ratio > self._risk_limits.max_margin_ratio:
                violations.append("margin_ratio_exceeded")

            # Check position size
            if risk_metrics.notional_value > self._risk_limits.max_position_size:
                violations.append("position_size_exceeded")

            # Check drawdown
            if risk_metrics.drawdown > self._risk_limits.max_drawdown:
                violations.append("drawdown_exceeded")

            # Check risk score
            if risk_metrics.risk_score > 0.8:
                violations.append("high_risk_score")

        except Exception as e:
            self.logger.error(f"Risk violation check failed: {e}")

        return violations

    async def _generate_risk_alerts(self, symbol: str, violations: list[str]) -> None:
        """Generate risk alerts for violations."""
        try:
            for violation in violations:
                alert_id = f"alert_{symbol}_{violation}_{uuid4().hex[:8]}"

                # Determine severity
                if violation in ["leverage_exceeded", "margin_ratio_exceeded"]:
                    severity = "critical"
                elif violation in ["position_size_exceeded", "drawdown_exceeded"]:
                    severity = "high"
                else:
                    severity = "medium"

                # Create alert message
                if violation == "leverage_exceeded":
                    message = f"Leverage limit exceeded for {symbol}"
                elif violation == "margin_ratio_exceeded":
                    message = f"Margin ratio limit exceeded for {symbol}"
                elif violation == "position_size_exceeded":
                    message = f"Position size limit exceeded for {symbol}"
                elif violation == "drawdown_exceeded":
                    message = f"Drawdown limit exceeded for {symbol}"
                elif violation == "high_risk_score":
                    message = f"High risk score for {symbol}"
                else:
                    message = f"Risk violation: {violation} for {symbol}"

                alert = RiskAlert(
                    id=alert_id,
                    symbol=symbol,
                    alert_type=violation,
                    severity=severity,
                    message=message,
                    timestamp=datetime.utcnow()
                )

                self._active_alerts[alert_id] = alert
                self._alerts_generated += 1

                self.logger.warning(f"Risk alert generated: {message}")

        except Exception as e:
            self.logger.error(f"Failed to generate risk alert: {e}")

    async def _calculate_portfolio_risk(self) -> dict[str, Any]:
        """Calculate portfolio-level risk metrics."""
        try:
            if not self._risk_metrics:
                return {}

            total_notional = sum(metrics.notional_value for metrics in self._risk_metrics.values())
            total_margin = sum(metrics.margin_used for metrics in self._risk_metrics.values())
            total_pnl = sum(metrics.unrealized_pnl for metrics in self._risk_metrics.values())

            # Calculate portfolio risk score
            portfolio_risk_score = 0.0
            if total_notional > 0:
                # Weighted average of position risk scores
                weighted_risk = sum(
                    metrics.risk_score * metrics.notional_value
                    for metrics in self._risk_metrics.values()
                )
                portfolio_risk_score = weighted_risk / total_notional

            # Check portfolio-level limits
            portfolio_violations = []

            if total_margin / total_notional > self._risk_limits.max_portfolio_risk:
                portfolio_violations.append("portfolio_risk_exceeded")

            if portfolio_risk_score > 0.7:
                portfolio_violations.append("high_portfolio_risk")

            return {
                "total_notional": total_notional,
                "total_margin": total_margin,
                "total_pnl": total_pnl,
                "portfolio_risk_score": portfolio_risk_score,
                "violations": portfolio_violations,
                "position_count": len(self._risk_metrics)
            }

        except Exception as e:
            self.logger.error(f"Portfolio risk calculation failed: {e}")
            return {}

    async def _process_alerts(self) -> None:
        """Process active risk alerts."""
        try:
            current_time = datetime.utcnow()

            for alert_id, alert in list(self._active_alerts.items()):
                if not alert.is_active:
                    continue

                # Check if alert should be escalated
                time_since_alert = current_time - alert.timestamp

                if alert.severity == "critical" and time_since_alert > timedelta(minutes=5):
                    await self._escalate_alert(alert)
                elif alert.severity == "high" and time_since_alert > timedelta(minutes=15):
                    await self._escalate_alert(alert)

                # Auto-resolve alerts for resolved violations
                if await self._is_violation_resolved(alert):
                    alert.is_active = False
                    self.logger.info(f"Risk alert resolved: {alert.message}")

        except Exception as e:
            self.logger.error(f"Alert processing failed: {e}")

    async def _escalate_alert(self, alert: RiskAlert) -> None:
        """Escalate a risk alert."""
        try:
            # This would typically send notifications, create tickets, etc.
            self.logger.critical(f"ESCALATING RISK ALERT: {alert.message}")

            # For now, just log the escalation
            # In production, this would trigger emergency procedures

        except Exception as e:
            self.logger.error(f"Alert escalation failed: {e}")

    async def _is_violation_resolved(self, alert: RiskAlert) -> bool:
        """Check if a risk violation has been resolved."""
        try:
            if alert.symbol not in self._risk_metrics:
                return True

            risk_metrics = self._risk_metrics[alert.symbol]

            if alert.alert_type == "leverage_exceeded":
                return risk_metrics.leverage <= self._risk_limits.max_leverage
            elif alert.alert_type == "margin_ratio_exceeded":
                return risk_metrics.margin_ratio <= self._risk_limits.max_margin_ratio
            elif alert.alert_type == "position_size_exceeded":
                return risk_metrics.notional_value <= self._risk_limits.max_position_size
            elif alert.alert_type == "drawdown_exceeded":
                return risk_metrics.drawdown <= self._risk_limits.max_drawdown
            elif alert.alert_type == "high_risk_score":
                return risk_metrics.risk_score <= 0.8

            return False

        except Exception as e:
            self.logger.error(f"Violation resolution check failed: {e}")
            return False

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "risk_assessment":
                result = await self._assess_risk(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="risk_assessment_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "risk_monitoring":
                result = await self._get_risk_status(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="risk_monitoring_result",
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

        if data_type == "position_update":
            await self._update_position_data(message.body)
        elif data_type == "market_data":
            await self._update_market_data(message.body)

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "get_status":
                result = self.get_status()
            elif command == "get_risk_limits":
                result = {
                    "max_position_size": self._risk_limits.max_position_size,
                    "max_leverage": self._risk_limits.max_leverage,
                    "max_drawdown": self._risk_limits.max_drawdown,
                    "max_margin_ratio": self._risk_limits.max_margin_ratio,
                    "max_risk_per_trade": self._risk_limits.max_risk_per_trade,
                    "max_portfolio_risk": self._risk_limits.max_portfolio_risk,
                    "stop_loss_threshold": self._risk_limits.stop_loss_threshold,
                    "take_profit_threshold": self._risk_limits.take_profit_threshold
                }
            elif command == "get_active_alerts":
                result = {
                    "active_alerts": [
                        {
                            "id": alert.id,
                            "symbol": alert.symbol,
                            "type": alert.alert_type,
                            "severity": alert.severity,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat()
                        }
                        for alert in self._active_alerts.values()
                        if alert.is_active
                    ]
                }
            elif command == "force_risk_check":
                await self._perform_risk_assessment()
                result = {"status": "completed", "timestamp": self._last_risk_check.isoformat() if self._last_risk_check else None}
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

    async def _assess_risk(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Assess risk for a specific symbol or position."""
        try:
            symbol = parameters.get("symbol")

            if not symbol:
                raise AgentError("Missing required parameter: symbol")

            if symbol not in self._risk_metrics:
                return {
                    "symbol": symbol,
                    "error": "No risk data available for symbol"
                }

            risk_metrics = self._risk_metrics[symbol]

            return {
                "symbol": symbol,
                "risk_score": risk_metrics.risk_score,
                "risk_level": risk_metrics.risk_level.value,
                "position_size": risk_metrics.position_size,
                "notional_value": risk_metrics.notional_value,
                "unrealized_pnl": risk_metrics.unrealized_pnl,
                "margin_ratio": risk_metrics.margin_ratio,
                "leverage": risk_metrics.leverage,
                "drawdown": risk_metrics.drawdown,
                "var_95": risk_metrics.var_95,
                "timestamp": risk_metrics.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Risk assessment failed: {e}")
            raise AgentError(f"Risk assessment failed: {e}")

    async def _get_risk_status(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get overall risk status."""
        try:
            portfolio_risk = await self._calculate_portfolio_risk()

            return {
                "portfolio_risk": portfolio_risk,
                "active_alerts_count": len([a for a in self._active_alerts.values() if a.is_active]),
                "critical_alerts": len([a for a in self._active_alerts.values() if a.is_active and a.severity == "critical"]),
                "high_alerts": len([a for a in self._active_alerts.values() if a.is_active and a.severity == "high"]),
                "risk_checks_performed": self._risk_checks_performed,
                "last_risk_check": self._last_risk_check.isoformat() if self._last_risk_check else None,
                "positions_monitored": len(self._risk_metrics)
            }

        except Exception as e:
            self.logger.error(f"Risk status retrieval failed: {e}")
            raise AgentError(f"Risk status retrieval failed: {e}")

    async def _update_position_data(self, data: dict[str, Any]) -> None:
        """Update position data from external source."""
        try:
            symbol = data.get("symbol")
            position_data = data.get("position", {})

            if symbol and position_data:
                # Update or create position
                side_str = position_data.get("side", "long")
                side = PositionSide.LONG if side_str == "long" else PositionSide.SHORT

                position = Position(
                    id=position_data.get("id", f"pos_{symbol}_{uuid4().hex[:8]}"),
                    symbol=symbol,
                    side=side,
                    quantity=Quantity(Decimal(str(position_data.get("size", 0.0)))),
                    entry_price=Price(Decimal(str(position_data.get("entry_price", 0.0)))),
                    current_price=Price(Decimal(str(position_data.get("current_price", 0.0)))),
                    unrealized_pnl=Money(Decimal(str(position_data.get("unrealized_pnl", 0.0))), "USDT"),
                    realized_pnl=Money(Decimal(str(position_data.get("realized_pnl", 0.0))), "USDT"),
                    margin=Money(Decimal(str(position_data.get("margin_used", 0.0))), "USDT"),
                    leverage=position_data.get("leverage", 1.0)
                )

                self._positions[symbol] = position
                self.logger.debug(f"Updated position data for {symbol}")

        except Exception as e:
            self.logger.error(f"Failed to update position data: {e}")

    async def _update_market_data(self, data: dict[str, Any]) -> None:
        """Update market data for risk calculations."""
        try:
            # This could trigger risk recalculations
            symbol = data.get("symbol")
            if symbol:
                self.logger.debug(f"Received market data update for {symbol}")

        except Exception as e:
            self.logger.error(f"Failed to update market data: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "risk_agent",
            "status": self.status.value,
            "risk_checks_performed": self._risk_checks_performed,
            "alerts_generated": self._alerts_generated,
            "risk_violations": self._risk_violations,
            "last_risk_check": self._last_risk_check.isoformat() if self._last_risk_check else None,
            "positions_monitored": len(self._positions),
            "active_alerts": len([a for a in self._active_alerts.values() if a.is_active]),
            "risk_limits": {
                "max_position_size": self._risk_limits.max_position_size,
                "max_leverage": self._risk_limits.max_leverage,
                "max_drawdown": self._risk_limits.max_drawdown,
                "max_margin_ratio": self._risk_limits.max_margin_ratio
            }
        }


# Tool classes for the Risk agent

class RiskAssessmentTool(Tool):
    """Tool for risk assessment."""

    def __init__(self, risk_agent: RiskManagementAgent):
        super().__init__("risk_assessment", "Assess risk for a trading symbol")
        self.risk_agent = risk_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute risk assessment."""
        return await self.risk_agent._assess_risk(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol to assess risk for"
            }
        }


class RiskMonitoringTool(Tool):
    """Tool for risk monitoring."""

    def __init__(self, risk_agent: RiskManagementAgent):
        super().__init__("risk_monitoring", "Get overall risk status and monitoring information")
        self.risk_agent = risk_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute risk monitoring."""
        return await self.risk_agent._get_risk_status(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {}


class RiskLimitTool(Tool):
    """Tool for managing risk limits."""

    def __init__(self, risk_agent: RiskManagementAgent):
        super().__init__("risk_limit", "Get and manage risk limits")
        self.risk_agent = risk_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute risk limit operation."""
        operation = parameters.get("operation")

        if operation == "get_limits":
            return {
                "max_position_size": self.risk_agent._risk_limits.max_position_size,
                "max_leverage": self.risk_agent._risk_limits.max_leverage,
                "max_drawdown": self.risk_agent._risk_limits.max_drawdown,
                "max_margin_ratio": self.risk_agent._risk_limits.max_margin_ratio
            }
        else:
            raise AgentError(f"Unknown operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["get_limits"],
                "description": "Risk limit operation to perform"
            }
        }
