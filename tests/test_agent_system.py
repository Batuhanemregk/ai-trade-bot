"""
Test the agent system components.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.core.base import BaseAgent, Context, Message, MessageType
from agents.core.memory import MemoryManager, MemoryType
from agents.core.router import Route, Router, RouteStep, RouteType
from agents.core.tools import get_tool_registry
from agents.graphs.default_graph import create_default_task_graph, get_available_graphs
from agents.roles.orchestrator import OrchestratorAgent


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    async def _initialize(self) -> None:
        """Initialize the mock agent."""
        self.logger.info("Mock agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup the mock agent."""
        self.logger.info("Mock agent cleaned up")

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        self.logger.info(f"Mock agent received task: {message.subject}")

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status update messages."""
        self.logger.info(f"Mock agent received status update: {message.subject}")

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        self.logger.info(f"Mock agent received data update: {message.subject}")


class TestAgentSystem:
    """Test the agent system components."""

    @pytest.fixture
    async def memory_manager(self):
        """Create a memory manager for testing."""
        config = {"persistent_memory": False}  # Use in-memory only for tests
        manager = MemoryManager(config)
        yield manager
        await manager.shutdown()

    @pytest.fixture
    async def router(self):
        """Create a router for testing."""
        config = {}
        router = Router(config)
        await router.start()
        yield router
        await router.stop()

    @pytest.fixture
    async def orchestrator(self):
        """Create an orchestrator agent for testing."""
        config = {
            "workflows": {
                "test_workflow": {
                    "description": "Test workflow",
                    "steps": [],
                    "enabled": True
                }
            }
        }
        agent = OrchestratorAgent("test_orchestrator", config)
        await agent.start()
        yield agent
        await agent.stop()

    def test_message_creation(self):
        """Test message creation and serialization."""
        message = Message(
            type=MessageType.TASK,
            from_agent="test_agent",
            to_agent="target_agent",
            subject="test_task",
            body={"test": "data"}
        )

        assert message.type == MessageType.TASK
        assert message.from_agent == "test_agent"
        assert message.to_agent == "target_agent"
        assert message.subject == "test_task"
        assert message.body["test"] == "data"

        # Test serialization
        message_dict = message.to_dict()
        assert message_dict["type"] == "task"
        assert message_dict["from_agent"] == "test_agent"

        # Test deserialization
        restored_message = Message.from_dict(message_dict)
        assert restored_message.type == message.type
        assert restored_message.from_agent == message.from_agent

    def test_context_operations(self):
        """Test context operations."""
        context = Context(
            agent_id="test_agent",
            agent_type="test_type",
            session_id="test_session"
        )

        # Test data operations
        context.set_data("test_key", "test_value")
        assert context.get_data("test_key") == "test_value"
        assert context.get_data("nonexistent_key", "default") == "default"

        # Test update operations
        context.update(user_id="test_user")
        assert context.user_id == "test_user"

    def test_route_creation(self):
        """Test route creation and management."""
        route = Route(
            name="test_route",
            description="Test route",
            route_type=RouteType.SEQUENTIAL
        )

        step1 = RouteStep(
            name="step1",
            agent_type="test_agent",
            parameters={"param1": "value1"}
        )

        step2 = RouteStep(
            name="step2",
            agent_type="test_agent",
            parameters={"param2": "value2"},
            depends_on=["step1"]
        )

        route.add_step(step1)
        route.add_step(step2)

        assert len(route.steps) == 2
        assert route.get_step("step1") == step1
        assert route.get_step("step2") == step2

        # Test dependency checking
        assert route.get_dependencies_met(step1, set())
        assert not route.get_dependencies_met(step2, set())
        assert route.get_dependencies_met(step2, {"step1"})

    def test_task_graph_creation(self):
        """Test task graph creation."""
        task_graph = create_default_task_graph()

        assert task_graph.name == "default_trading_workflow"
        assert len(task_graph.routes) > 0

        # Check that routes have steps
        for route in task_graph.routes:
            assert len(route.steps) > 0

    def test_available_graphs(self):
        """Test available graphs listing."""
        available_graphs = get_available_graphs()

        assert "default_trading_workflow" in available_graphs
        assert "quick_market_analysis" in available_graphs
        assert "strategy_backtest" in available_graphs
        assert "continuous_risk_monitoring" in available_graphs

    @pytest.mark.asyncio
    async def test_memory_operations(self, memory_manager):
        """Test memory operations."""
        # Test set and get
        await memory_manager.set("test_key", "test_value", MemoryType.EPHEMERAL)
        value = await memory_manager.get("test_key", MemoryType.EPHEMERAL)
        assert value == "test_value"

        # Test exists
        exists = await memory_manager.exists("test_key", MemoryType.EPHEMERAL)
        assert exists is True

        # Test keys
        keys = await memory_manager.keys(MemoryType.EPHEMERAL)
        assert "test_key" in keys

        # Test delete
        await memory_manager.delete("test_key", MemoryType.EPHEMERAL)
        value = await memory_manager.get("test_key", MemoryType.EPHEMERAL)
        assert value is None

    @pytest.mark.asyncio
    async def test_router_operations(self, router):
        """Test router operations."""
        # Test agent registration
        mock_agent = MockAgent("test_agent", "test_type", {})
        router.register_agent(mock_agent)

        # Test route registration
        route = Route(name="test_route", description="Test route")
        router.register_route(route)

        # Test task graph registration
        task_graph = create_default_task_graph()
        router.register_task_graph(task_graph)

        # Check registrations
        agent_status = router.get_agent_status()
        assert "test_agent" in agent_status

        route_status = router.get_route_status()
        assert "test_route" in route_status

    @pytest.mark.asyncio
    async def test_orchestrator_operations(self, orchestrator):
        """Test orchestrator operations."""
        # Test workflow status
        status = orchestrator.get_workflow_status()
        assert status["total_workflows"] > 0

        # Test command handling
        from agents.core.base import Message, MessageType

        command_message = Message(
            type=MessageType.COMMAND,
            from_agent="test_client",
            to_agent=orchestrator.agent_id,
            subject="test_command",
            body={
                "command": "list_workflows",
                "parameters": {}
            }
        )

        # Simulate receiving command
        await orchestrator.receive_message(command_message)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Check that orchestrator is running
        assert orchestrator.status.value == "running"

    def test_tool_registry(self):
        """Test tool registry operations."""
        registry = get_tool_registry()

        # Check that default tools are registered
        all_tools = registry.get_all_tools()
        assert len(all_tools) > 0

        # Check tool categories
        categories = registry.list_categories()
        assert len(categories) > 0

        # Check tool schemas
        schemas = registry.get_tool_schemas()
        assert len(schemas) > 0


@pytest.mark.asyncio
async def test_agent_system_integration():
    """Test the complete agent system integration."""
    # Create components
    memory_manager = MemoryManager({"persistent_memory": False})
    router = Router({})
    orchestrator = OrchestratorAgent("test_orchestrator", {"workflows": {}})

    try:
        # Start components
        await memory_manager.start()
        await router.start()
        await orchestrator.start()

        # Register orchestrator with router
        router.register_agent(orchestrator)

        # Create and register a task graph
        task_graph = create_default_task_graph()
        router.register_task_graph(task_graph)

        # Test execution
        execution_id = await router.execute_task_graph("default_trading_workflow")
        assert execution_id is not None

        # Check status
        status = await router.get_execution_status(execution_id)
        assert status["status"] in ["pending", "running", "completed", "failed"]

    finally:
        # Cleanup
        await orchestrator.stop()
        await router.stop()
        await memory_manager.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
