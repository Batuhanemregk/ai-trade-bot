"""
Core protocol and base classes for the AiBotBS Runtime Agent System.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Message types for inter-agent communication."""
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    DATA_UPDATE = "data_update"
    COMMAND = "command"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Message:
    """Message for inter-agent communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK
    priority: MessagePriority = MessagePriority.NORMAL
    from_agent: str = ""
    to_agent: str = ""
    subject: str = ""
    body: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    reply_to: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation."""
        if not self.correlation_id:
            self.correlation_id = self.id

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "subject": self.subject,
            "body": self.body,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        data = data.copy()
        data["type"] = MessageType(data["type"])
        data["priority"] = MessagePriority(data["priority"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class Reply:
    """Reply message with status and metrics."""
    status: str  # "success", "error", "partial"
    payload: Any = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Context:
    """Context for agent execution."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)
    memory: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def now(self) -> datetime:
        """Get current timestamp."""
        return datetime.now(UTC)

    def get_policy(self, key: str, default: Any = None) -> Any:
        """Get policy value."""
        return self.policy.get(key, default)

    def get_tool(self, name: str) -> Any | None:
        """Get tool by name."""
        return self.tools.get(name)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)


@dataclass
class Task:
    """Task for agent execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    message: Message = field(default_factory=Message)
    context: Context = field(default_factory=Context)
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Any | None = None
    error: str | None = None


class Tool(ABC):
    """Abstract base class for agent tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute the tool with given parameters and context."""
        pass

    @abstractmethod
    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        pass

    def get_schema(self) -> dict[str, Any]:
        """Get complete tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameter_schema()
        }


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, agent_id: str, agent_type: str, config: dict[str, Any]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self._running = False
        self._message_handlers: dict[MessageType, list[Callable[[Message], Awaitable[None]]]] = {}
        self._tools: dict[str, Tool] = {}
        self.logger = logging.getLogger(f"agent.{agent_type}.{agent_id}")

        # Performance tracking
        self._messages_processed = 0
        self._errors_count = 0
        self._start_time = None
        self._last_activity = None

    async def start(self) -> None:
        """Start the agent."""
        try:
            self.logger.info(f"Starting {self.agent_type} agent")
            self.status = AgentStatus.INITIALIZING

            # Initialize agent-specific logic
            await self._initialize()

            self.status = AgentStatus.RUNNING
            self._running = True
            self._start_time = datetime.now(UTC)
            self._last_activity = self._start_time

            self.logger.info(f"{self.agent_type} agent started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start {self.agent_type} agent: {e}")
            self.status = AgentStatus.ERROR
            raise

    async def stop(self) -> None:
        """Stop the agent."""
        try:
            self.logger.info(f"Stopping {self.agent_type} agent")
            self.status = AgentStatus.STOPPING

            self._running = False

            # Cleanup agent-specific logic
            await self._cleanup()

            self.status = AgentStatus.STOPPED
            self.logger.info(f"{self.agent_type} agent stopped successfully")

        except Exception as e:
            self.logger.error(f"Failed to stop {self.agent_type} agent: {e}")
            self.status = AgentStatus.ERROR
            raise

    async def handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        try:
            self._last_activity = datetime.now(UTC)
            self._messages_processed += 1

            # Find appropriate handlers
            handlers = self._message_handlers.get(message.type, [])

            if not handlers:
                self.logger.warning(f"No handlers registered for message type: {message.type}")
                return

            # Execute handlers
            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error(f"Handler error: {e}")
                    self._errors_count += 1

        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
            self._errors_count += 1

    def register_message_handler(self, message_type: MessageType, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Register a message handler."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
        self.logger.debug(f"Registered handler for {message_type}")

    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the agent."""
        self._tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List available tool names."""
        return list(self._tools.keys())

    async def send_message(self, message: Message) -> None:
        """Send a message (to be implemented by concrete agents)."""
        # This is a placeholder - concrete agents should implement this
        self.logger.debug(f"Would send message: {message.subject}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status information."""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(UTC) - self._start_time).total_seconds()

        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "running": self._running,
            "messages_processed": self._messages_processed,
            "errors_count": self._errors_count,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "uptime_seconds": uptime,
            "tools_count": len(self._tools),
            "tools": list(self._tools.keys())
        }

    def describe(self) -> dict[str, Any]:
        """Describe the agent's capabilities."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "description": self.__doc__ or f"{self.agent_type} agent",
            "capabilities": {
                "message_types": [msg_type.value for msg_type in self._message_handlers.keys()],
                "tools": [tool.get_schema() for tool in self._tools.values()]
            },
            "config": self.config
        }

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize agent-specific logic."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup agent-specific logic."""
        pass

    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running and self.status == AgentStatus.RUNNING

    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        if not self.is_running():
            return False

        # Check if agent has been active recently (within last 5 minutes)
        if self._last_activity:
            time_since_activity = (datetime.now(UTC) - self._last_activity).total_seconds()
            return time_since_activity < 300  # 5 minutes

        return False


# Export key classes and enums
__all__ = [
    "BaseAgent",
    "Message",
    "MessageType",
    "MessagePriority",
    "AgentStatus",
    "Tool",
    "Context",
    "Reply"
]

