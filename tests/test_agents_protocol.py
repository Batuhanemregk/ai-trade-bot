"""
Test suite for AiBotBS Runtime Agent System protocol.
Tests message passing, agent communication, and core agent functionality.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from agents.core.base import (
    BaseAgent,
    Context,
    Message,
    MessagePriority,
    MessageType,
    Tool,
)
from agents.core.memory import MemoryManager
from agents.core.router import Route, Router, RouteType, TaskGraph
from agents.core.tools import ToolCategory, ToolRegistry


class DummyAgent(BaseAgent):
    """Concrete test agent for testing BaseAgent functionality."""

    async def _initialize(self) -> None:
        """Initialize test agent."""
        pass

    async def _cleanup(self) -> None:
        """Cleanup test agent."""
        pass

    async def handle_message(self, message: Message) -> bool:
        """Handle incoming message."""
        return True


class TestMessageProtocol:
    """Test the message protocol between agents."""

    def test_message_creation(self):
        """Test message creation with all fields."""
        message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="ta_agent",
            subject="analyze",
            body={"symbol": "BTC-USDT", "timeframe": "1h"},
            priority=MessagePriority.HIGH,
            timestamp=datetime.now(UTC)
        )

        assert message.type == MessageType.TASK
        assert message.from_agent == "orchestrator"
        assert message.to_agent == "ta_agent"
        assert message.subject == "analyze"
        assert message.body["symbol"] == "BTC-USDT"
        assert message.priority == MessagePriority.HIGH
        assert message.timestamp is not None

    def test_message_defaults(self):
        """Test message creation with default values."""
        message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="ta_agent",
            subject="analyze",
            body={}
        )

        assert message.priority == MessagePriority.NORMAL
        assert message.timestamp is not None
        assert message.id is not None


class TestContext:
    """Test the context object for agent communication."""

    def test_context_creation(self):
        """Test context creation and data storage."""
        context = Context()
        context.set_metadata("symbol", "BTC-USDT")
        context.set_metadata("timeframe", "1h")

        assert context.get_metadata("symbol") == "BTC-USDT"
        assert context.get_metadata("timeframe") == "1h"
        assert context.get_metadata("nonexistent") is None


class TestToolSystem:
    """Test the tool system for agent capabilities."""

    def test_tool_registry(self):
        """Test tool registration and discovery."""
        registry = ToolRegistry()

        # Create mock tool
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.category = ToolCategory.UTILITY
        mock_tool.description = "A test tool"

        # Register tool with category
        registry.register_tool(mock_tool, ToolCategory.UTILITY)

        # Discover tools
        tools = registry.get_tools_by_category(ToolCategory.UTILITY)
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

        # Get tool by name
        tool = registry.get_tool("test_tool")
        assert tool == mock_tool


class TestBaseAgent:
    """Test the base agent functionality."""

    @pytest.mark.asyncio
    async def test_base_agent_creation(self):
        """Test base agent creation and initialization."""
        config = {"test_config": "value"}
        agent = DummyAgent("test_agent", "TestAgent", config)

        assert agent.agent_id == "test_agent"
        assert agent.agent_type == "TestAgent"
        assert agent.status.value == "initializing"
        assert agent._start_time is None

    @pytest.mark.asyncio
    async def test_base_agent_start_stop(self):
        """Test agent start and stop methods."""
        config = {"test_config": "value"}
        agent = DummyAgent("test_agent", "TestAgent", config)

        # Start agent
        await agent.start()
        assert agent.status.value == "running"
        assert agent._start_time is not None

        # Stop agent
        await agent.stop()
        assert agent.status.value == "stopped"


class TestRouter:
    """Test the router for task execution."""

    @pytest.mark.asyncio
    async def test_router_creation(self):
        """Test router creation and initialization."""
        config = {"max_concurrent_routes": 5}
        router = Router(config)

        assert router._max_concurrent_routes == 5
        assert router._running is False
        assert len(router._agents) == 0
        assert len(router._routes) == 0

        # Clean up
        await router.stop()

    @pytest.mark.asyncio
    async def test_router_agent_registration(self):
        """Test agent registration with router."""
        config = {"max_concurrent_routes": 5}
        router = Router(config)

        # Create mock agent
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.agent_id = "test_agent"

        # Register agent
        router.register_agent(mock_agent)

        assert "test_agent" in router._agents
        assert router._agents["test_agent"] == mock_agent

        # Clean up
        await router.stop()

    @pytest.mark.asyncio
    async def test_router_message_routing(self):
        """Test message routing between agents."""
        config = {"max_concurrent_routes": 5}
        router = Router(config)

        # Create and register agents
        agent1 = Mock(spec=BaseAgent)
        agent1.agent_id = "agent1"
        agent1.handle_message = Mock()

        agent2 = Mock(spec=BaseAgent)
        agent2.agent_id = "agent2"
        agent2.handle_message = Mock()

        router.register_agent(agent1)
        router.register_agent(agent2)

        # Create message
        message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="agent1",
            subject="test_task",
            body={}
        )

        # Route message
        router.route_message(message)

        # Check if agent1 received the message
        agent1.handle_message.assert_called_once()
        received_message = agent1.handle_message.call_args[0][0]
        assert received_message.to_agent == "agent1"

        # Clean up
        await router.stop()


class TestTaskGraph:
    """Test the task graph functionality."""

    def test_task_graph_creation(self):
        """Test task graph creation and initialization."""
        graph = TaskGraph(
            id="test_graph",
            name="Test Graph",
            description="A test task graph",
            routes=[]
        )

        assert graph.id == "test_graph"
        assert graph.name == "Test Graph"
        assert graph.description == "A test task graph"
        assert len(graph.routes) == 0

    def test_route_creation(self):
        """Test route creation and initialization."""
        route = Route(
            id="test_route",
            name="Test Route",
            description="A test route",
            steps=[],
            type=RouteType.SEQUENTIAL
        )

        assert route.id == "test_route"
        assert route.name == "Test Route"
        assert route.type == RouteType.SEQUENTIAL
        assert len(route.steps) == 0


class TestMemoryManager:
    """Test memory manager functionality."""

    @pytest.mark.asyncio
    async def test_memory_manager_lifecycle(self):
        """Test memory manager start and stop."""
        config = {"persistent_memory": False}
        memory_manager = MemoryManager(config)

        # Start memory manager
        await memory_manager.start()
        assert memory_manager._running is True

        # Stop memory manager
        await memory_manager.stop()
        assert memory_manager._running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
