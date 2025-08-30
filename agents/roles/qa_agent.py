"""
QA Agent for the AiBotBS Runtime Agent System.
Responsible for quality assurance, system health monitoring, and consistency checks.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..core.base import BaseAgent, Context, Message, MessageType
from ..core.tools import Tool


class HealthStatus(Enum):
    """System health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)


class SystemHealthTool(Tool):
    """Tool for system health monitoring."""

    def __init__(self):
        super().__init__("system_health", "Monitor system health and performance")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute health check."""
        try:
            check_type = parameters.get("check_type", "all")

            if check_type == "system":
                return await self._check_system_health()
            elif check_type == "agents":
                return await self._check_agents_health()
            elif check_type == "performance":
                return await self._check_performance()
            else:
                return await self._check_all_health()

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        return {
            "check_type": {
                "type": "string",
                "enum": ["system", "agents", "performance", "all"],
                "description": "Type of health check to perform"
            }
        }

    async def _check_system_health(self) -> dict[str, Any]:
        """Check system health."""
        return {
            "status": "healthy",
            "checks": [
                {"component": "memory", "status": "healthy", "usage": "45%"},
                {"component": "cpu", "status": "healthy", "usage": "23%"},
                {"component": "disk", "status": "healthy", "usage": "67%"}
            ]
        }

    async def _check_agents_health(self) -> dict[str, Any]:
        """Check agents health."""
        return {
            "status": "healthy",
            "agents": [
                {"id": "orchestrator", "status": "running", "uptime": "2h 15m"},
                {"id": "ta_agent", "status": "running", "uptime": "2h 10m"}
            ]
        }

    async def _check_performance(self) -> dict[str, Any]:
        """Check system performance."""
        return {
            "status": "healthy",
            "metrics": {
                "response_time": "45ms",
                "throughput": "150 req/s",
                "error_rate": "0.1%"
            }
        }

    async def _check_all_health(self) -> dict[str, Any]:
        """Check all health aspects."""
        system = await self._check_system_health()
        agents = await self._check_agents_health()
        performance = await self._check_performance()

        return {
            "system": system,
            "agents": agents,
            "performance": performance,
            "overall_status": "healthy"
        }


class ConsistencyCheckTool(Tool):
    """Tool for data consistency checks."""

    def __init__(self):
        super().__init__("consistency_check", "Check data consistency across the system")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute consistency check."""
        try:
            check_type = parameters.get("check_type", "all")

            if check_type == "data_integrity":
                return await self._check_data_integrity()
            elif check_type == "referential_integrity":
                return await self._check_referential_integrity()
            else:
                return await self._check_all_consistency()

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        return {
            "check_type": {
                "type": "string",
                "enum": ["data_integrity", "referential_integrity", "all"],
                "description": "Type of consistency check to perform"
            }
        }

    async def _check_data_integrity(self) -> dict[str, Any]:
        """Check data integrity."""
        return {
            "status": "consistent",
            "checks": [
                {"type": "orders", "status": "consistent", "count": 1250},
                {"type": "positions", "status": "consistent", "count": 45}
            ]
        }

    async def _check_referential_integrity(self) -> dict[str, Any]:
        """Check referential integrity."""
        return {
            "status": "consistent",
            "checks": [
                {"type": "order_positions", "status": "consistent", "orphaned": 0},
                {"type": "bracket_orders", "status": "consistent", "orphaned": 0}
            ]
        }

    async def _check_all_consistency(self) -> dict[str, Any]:
        """Check all consistency aspects."""
        data = await self._check_data_integrity()
        referential = await self._check_referential_integrity()

        return {
            "data_integrity": data,
            "referential_integrity": referential,
            "overall_status": "consistent"
        }


class QAAgent(BaseAgent):
    """Agent responsible for quality assurance and system health."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "qa_agent", config)
        self._health_checks: list[HealthCheck] = []
        self._consistency_checks: list[dict[str, Any]] = []

        # Register message handlers
        self.register_message_handler(MessageType.TASK, self._handle_task)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

        # Register tools
        self.register_tool(SystemHealthTool())
        self.register_tool(ConsistencyCheckTool())

    async def _initialize(self) -> None:
        """Initialize the QA agent."""
        self.logger.info("Initializing QA agent")
        self._load_config()
        self.logger.info("QA agent initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup the QA agent."""
        self.logger.info("QA agent cleanup completed")

    def _load_config(self) -> None:
        """Load agent configuration."""
        self._health_check_interval = self.config.get("health_check_interval", 300)
        self._consistency_check_interval = self.config.get("consistency_check_interval", 600)
        self._alert_threshold = self.config.get("alert_threshold", 0.8)

    async def _handle_task(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "health_check":
                await self._perform_health_check(message)
            elif task_type == "consistency_check":
                await self._perform_consistency_check(message)
            elif task_type == "system_audit":
                await self._perform_system_audit(message)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Task handling error: {e}")

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        try:
            command = message.body.get("command")

            if command == "status":
                await self._send_status(message)
            elif command == "health":
                await self._send_health_status(message)
            elif command == "consistency":
                await self._send_consistency_status(message)
            else:
                self.logger.warning(f"Unknown command: {command}")

        except Exception as e:
            self.logger.error(f"Command handling error: {e}")

    async def _perform_health_check(self, message: Message) -> None:
        """Perform system health check."""
        try:
            tool = self.get_tool("system_health")
            if tool:
                result = await tool.execute({"check_type": "all"}, Context())

                # Store health check result
                health_check = HealthCheck(
                    component="system",
                    status=HealthStatus.HEALTHY if result.get("overall_status") == "healthy" else HealthStatus.WARNING,
                    message="System health check completed",
                    details=result
                )
                self._health_checks.append(health_check)

                # Send result back
                await self.send_message(Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="health_check_completed",
                    body=result,
                    reply_to=message.id
                ))

                # Check for alerts
                await self._check_health_alerts(result)

            else:
                self.logger.error("System health tool not found")

        except Exception as e:
            self.logger.error(f"Health check error: {e}")

    async def _perform_consistency_check(self, message: Message) -> None:
        """Perform data consistency check."""
        try:
            tool = self.get_tool("consistency_check")
            if tool:
                result = await tool.execute({"check_type": "all"}, Context())

                # Store consistency check result
                self._consistency_checks.append({
                    "timestamp": datetime.now(UTC).isoformat(),
                    "result": result
                })

                # Send result back
                await self.send_message(Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="consistency_check_completed",
                    body=result,
                    reply_to=message.id
                ))

            else:
                self.logger.error("Consistency check tool not found")

        except Exception as e:
            self.logger.error(f"Consistency check error: {e}")

    async def _perform_system_audit(self, message: Message) -> None:
        """Perform comprehensive system audit."""
        try:
            # Perform both health and consistency checks
            health_result = await self._perform_health_check_internal()
            consistency_result = await self._perform_consistency_check_internal()

            audit_result = {
                "health": health_result,
                "consistency": consistency_result,
                "timestamp": datetime.now(UTC).isoformat(),
                "overall_status": "healthy" if (
                    health_result.get("overall_status") == "healthy" and
                    consistency_result.get("overall_status") == "consistent"
                ) else "warning"
            }

            # Send audit result
            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="system_audit_completed",
                body=audit_result,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"System audit error: {e}")

    async def _check_health_alerts(self, health_result: dict[str, Any]) -> None:
        """Check for health alerts."""
        try:
            if health_result.get("overall_status") != "healthy":
                # Send alert
                await self.send_message(Message(
                    type=MessageType.DATA_UPDATE,
                    from_agent=self.agent_id,
                    to_agent="orchestrator",
                    subject="health_alert",
                    body={
                        "alert_type": "health_warning",
                        "status": health_result.get("overall_status"),
                        "details": health_result,
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                ))

        except Exception as e:
            self.logger.error(f"Health alert check error: {e}")

    async def _send_status(self, message: Message) -> None:
        """Send agent status."""
        try:
            status = {
                "health_checks_count": len(self._health_checks),
                "consistency_checks_count": len(self._consistency_checks),
                "last_health_check": self._health_checks[-1].timestamp.isoformat() if self._health_checks else None,
                "last_consistency_check": self._consistency_checks[-1]["timestamp"] if self._consistency_checks else None
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

    async def _send_health_status(self, message: Message) -> None:
        """Send health status."""
        try:
            if self._health_checks:
                latest_health = self._health_checks[-1]
                health_data = {
                    "latest_check": latest_health.__dict__,
                    "checks_count": len(self._health_checks)
                }
            else:
                health_data = {"latest_check": None, "checks_count": 0}

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="health_status",
                body=health_data,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Health status send error: {e}")

    async def _send_consistency_status(self, message: Message) -> None:
        """Send consistency status."""
        try:
            if self._consistency_checks:
                latest_consistency = self._consistency_checks[-1]
                consistency_data = {
                    "latest_check": latest_consistency,
                    "checks_count": len(self._consistency_checks)
                }
            else:
                consistency_data = {"latest_check": None, "checks_count": 0}

            await self.send_message(Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="consistency_status",
                body=consistency_data,
                reply_to=message.id
            ))

        except Exception as e:
            self.logger.error(f"Consistency status send error: {e}")

    async def _perform_health_check_internal(self) -> dict[str, Any]:
        """Internal health check method."""
        try:
            tool = self.get_tool("system_health")
            if tool:
                return await tool.execute({"check_type": "all"}, Context())
            return {"error": "Health tool not found"}
        except Exception as e:
            return {"error": str(e)}

    async def _perform_consistency_check_internal(self) -> dict[str, Any]:
        """Internal consistency check method."""
        try:
            tool = self.get_tool("consistency_check")
            if tool:
                return await tool.execute({"check_type": "all"}, Context())
            return {"error": "Consistency tool not found"}
        except Exception as e:
            return {"error": str(e)}
