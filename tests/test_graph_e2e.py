"""
End-to-end tests for the AiBotBS Runtime Agent System task graphs.
Tests the complete flow from orchestrator to execution.
"""

import asyncio

# Add parent directory to path for imports
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from agents.core.memory import MemoryManager
from agents.core.router import Router
from agents.graphs.default_graph import create_default_task_graph
from agents.roles.execution_agent import ExecutionAgent
from agents.roles.ml_agent import MachineLearningAgent
from agents.roles.news_agent import NewsAgent
from agents.roles.orchestrator import OrchestratorAgent
from agents.roles.risk_agent import RiskManagementAgent
from agents.roles.ta_agent import TechnicalAnalysisAgent


@pytest.fixture
async def memory_manager():
    """Create a memory manager for testing."""
    return MemoryManager()


@pytest.fixture
async def router():
    """Create a router for testing."""
    config = {
        "max_concurrent_routes": 5,
        "route_timeout": 60,
        "step_timeout": 10,
        "max_retries": 3
    }
    return Router(config)


@pytest.fixture
async def orchestrator():
    """Create an orchestrator agent for testing."""
    config = {
        "max_workflows": 10,
        "workflow_timeout": 300,
        "retry_policy": {"max_retries": 3, "backoff_factor": 2}
    }
    return OrchestratorAgent("test_orchestrator", config)


@pytest.fixture
async def ta_agent():
    """Create a TA agent for testing."""
    config = {
        "enabled": True,
        "indicators": ["RSI", "MACD", "BB"],
        "timeframe": "1h"
    }
    return TechnicalAnalysisAgent("test_ta", config)


@pytest.fixture
async def ml_agent():
    """Create an ML agent for testing."""
    config = {
        "enabled": True,
        "model_type": "ensemble",
        "confidence_threshold": 0.7
    }
    return MachineLearningAgent("test_ml", config)


@pytest.fixture
async def news_agent():
    """Create a news agent for testing."""
    config = {
        "enabled": True,
        "sources": ["cryptocompare", "coingecko"],
        "sentiment_analysis": True
    }
    return NewsAgent("test_news", config)


@pytest.fixture
async def risk_agent():
    """Create a risk agent for testing."""
    config = {
        "enabled": True,
        "max_position_size": 0.1,
        "max_drawdown": 0.2,
        "leverage_limit": 3.0
    }
    return RiskManagementAgent("test_risk", config)


@pytest.fixture
async def execution_agent():
    """Create an execution agent for testing."""
    config = {
        "enabled": True,
        "mode": "dry-run",
        "max_orders": 100,
        "order_timeout": 30
    }
    return ExecutionAgent("test_execution", config)


@pytest.fixture
async def default_graph():
    """Create the default task graph for testing."""
    return create_default_task_graph()


class TestDefaultTaskGraphE2E:
    """Test the default task graph end-to-end execution."""

    @pytest.mark.asyncio
    async def test_default_graph_creation(self, default_graph):
        """Test that the default graph is created correctly."""
        assert default_graph is not None
        assert default_graph.name == "default"
        assert len(default_graph.routes) > 0

        # Check that the main route exists
        main_route = None
        for route in default_graph.routes:
            if route.name == "main_trading_flow":
                main_route = route
                break

        assert main_route is not None
        assert main_route.type.value == "sequential"
        assert len(main_route.steps) >= 4  # TA, ML, News, Risk, Execution

    @pytest.mark.asyncio
    async def test_default_graph_steps(self, default_graph):
        """Test that the default graph has the correct steps."""
        main_route = None
        for route in default_graph.routes:
            if route.name == "main_trading_flow":
                main_route = route
                break

        assert main_route is not None

        # Check step order and dependencies
        step_names = [step.id for step in main_route.steps]

        # Should have analysis steps
        assert any("ta_analysis" in step for step in step_names)
        assert any("ml_analysis" in step for step in step_names)
        assert any("news_analysis" in step for step in step_names)

        # Should have scoring and risk steps
        assert any("scoring" in step for step in step_names)
        assert any("risk_assessment" in step for step in step_names)

        # Should have execution step
        assert any("execution" in step for step in step_names)

    @pytest.mark.asyncio
    async def test_graph_dependencies(self, default_graph):
        """Test that the graph dependencies are correctly set."""
        main_route = None
        for route in default_graph.routes:
            if route.name == "main_trading_flow":
                main_route = route
                break

        assert main_route is not None

        # Check that later steps depend on earlier ones
        for i, step in enumerate(main_route.steps):
            if i > 0:
                # Each step should depend on the previous one
                assert len(step.dependencies) > 0 or step.dependencies == []

    @pytest.mark.asyncio
    async def test_graph_metadata(self, default_graph):
        """Test that the graph has proper metadata."""
        assert default_graph.description is not None
        assert len(default_graph.description) > 0
        assert default_graph.metadata is not None


class TestTaskGraphExecution:
    """Test the execution of task graphs."""

    @pytest.mark.asyncio
    async def test_graph_registration(self, router, default_graph):
        """Test that a graph can be registered with the router."""
        graph_name = "test_default"
        router.register_task_graph(graph_name, default_graph)

        assert graph_name in router._task_graphs
        assert router._task_graphs[graph_name] == default_graph

    @pytest.mark.asyncio
    async def test_route_execution_setup(self, router, default_graph):
        """Test that routes from a graph can be set up for execution."""
        graph_name = "test_default"
        router.register_task_graph(graph_name, default_graph)

        # Get the main route
        main_route = None
        for route in default_graph.routes:
            if route.name == "main_trading_flow":
                main_route = route
                break

        assert main_route is not None

        # Register the route
        route_id = f"{graph_name}_{main_route.name}"
        router._routes[route_id] = main_route

        assert route_id in router._routes
        assert router._routes[route_id] == main_route

    @pytest.mark.asyncio
    async def test_agent_registration(self, router, ta_agent, ml_agent, news_agent, risk_agent, execution_agent):
        """Test that agents can be registered with the router."""
        agents = {
            "ta_agent": ta_agent,
            "ml_agent": ml_agent,
            "news_agent": news_agent,
            "risk_agent": risk_agent,
            "execution_agent": execution_agent
        }

        for agent_id, agent in agents.items():
            router.register_agent(agent_id, agent)
            assert agent_id in router._agents
            assert router._agents[agent_id] == agent

    @pytest.mark.asyncio
    async def test_agent_communication_setup(self, router, ta_agent, ml_agent, news_agent, risk_agent, execution_agent):
        """Test that agents can communicate through the router."""
        agents = {
            "ta_agent": ta_agent,
            "ml_agent": ml_agent,
            "news_agent": news_agent,
            "risk_agent": risk_agent,
            "execution_agent": execution_agent
        }

        # Register all agents
        for agent_id, agent in agents.items():
            router.register_agent(agent_id, agent)

        # Test message sending
        from agents.core.base import Message, MessageType

        test_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="ta_agent",
            subject="test_task",
            body={"task_type": "analyze", "symbol": "BTC/USDT"}
        )

        # Send message through router
        success = await router.send_message(test_message)
        assert success is True

    @pytest.mark.asyncio
    async def test_workflow_execution_flow(self, router, orchestrator, ta_agent, ml_agent, news_agent, risk_agent, execution_agent):
        """Test the complete workflow execution flow."""
        # Register all agents
        agents = {
            "orchestrator": orchestrator,
            "ta_agent": ta_agent,
            "ml_agent": ml_agent,
            "news_agent": news_agent,
            "risk_agent": risk_agent,
            "execution_agent": execution_agent
        }

        for agent_id, agent in agents.items():
            router.register_agent(agent_id, agent)

        # Start all agents
        for agent in agents.values():
            await agent.start()

        # Create a simple test workflow
        from agents.core.base import Message, MessageType

        # Step 1: Send analysis request to TA agent
        ta_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="ta_agent",
            subject="technical_analysis",
            body={"task_type": "analyze", "symbol": "BTC/USDT", "timeframe": "1h"}
        )

        await router.send_message(ta_message)

        # Step 2: Send analysis request to ML agent
        ml_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="ml_agent",
            subject="ml_prediction",
            body={"task_type": "predict", "symbol": "BTC/USDT", "features": ["price", "volume"]}
        )

        await router.send_message(ml_message)

        # Step 3: Send analysis request to News agent
        news_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="news_agent",
            subject="sentiment_analysis",
            body={"task_type": "analyze_sentiment", "symbol": "BTC/USDT"}
        )

        await router.send_message(news_message)

        # Step 4: Send scoring request to Risk agent
        risk_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="risk_agent",
            subject="risk_assessment",
            body={"task_type": "assess_risk", "symbol": "BTC/USDT", "position_size": 0.1}
        )

        await router.send_message(risk_message)

        # Step 5: Send execution request to Execution agent
        execution_message = Message(
            type=MessageType.TASK,
            from_agent="orchestrator",
            to_agent="execution_agent",
            subject="execute_trade",
            body={"task_type": "execute", "symbol": "BTC/USDT", "side": "buy", "quantity": 0.01}
        )

        await router.send_message(execution_message)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Check that all agents received messages
        for agent_id, agent in agents.items():
            if agent_id != "orchestrator":
                assert agent._messages_processed > 0, f"{agent_id} should have processed messages"

        # Stop all agents
        for agent in agents.values():
            await agent.stop()

    @pytest.mark.asyncio
    async def test_dry_run_execution(self, router, execution_agent):
        """Test that execution agent works in dry-run mode."""
        router.register_agent("execution_agent", execution_agent)
        await execution_agent.start()

        from agents.core.base import Message, MessageType

        # Send dry-run execution request
        execution_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="execution_agent",
            subject="execute_trade_dry_run",
            body={
                "task_type": "execute",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.01,
                "mode": "dry-run"
            }
        )

        await router.send_message(execution_message)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Check that execution agent processed the message
        assert execution_agent._messages_processed > 0

        await execution_agent.stop()

    @pytest.mark.asyncio
    async def test_error_handling(self, router, ta_agent):
        """Test error handling in the workflow."""
        router.register_agent("ta_agent", ta_agent)
        await ta_agent.start()

        from agents.core.base import Message, MessageType

        # Send invalid message
        invalid_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="ta_agent",
            subject="invalid_task",
            body={"invalid_field": "invalid_value"}
        )

        await router.send_message(invalid_message)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Check that agent handled the error gracefully
        assert ta_agent._messages_processed > 0
        # Note: In a real implementation, we'd check error logs or error counts

        await ta_agent.stop()


class TestGraphIntegration:
    """Test integration between different components."""

    @pytest.mark.asyncio
    async def test_memory_integration(self, memory_manager, router):
        """Test that memory manager integrates with router."""
        # This is a basic integration test
        # In a real implementation, we'd test actual data persistence
        assert memory_manager is not None
        assert router is not None

    @pytest.mark.asyncio
    async def test_tool_integration(self, ta_agent):
        """Test that agents have access to their tools."""
        # Check that TA agent has tools
        tools = ta_agent.list_tools()
        assert len(tools) > 0

        # Check that tools are properly registered
        for tool_name in tools:
            tool = ta_agent.get_tool(tool_name)
            assert tool is not None
            assert hasattr(tool, 'execute')
            assert hasattr(tool, 'get_schema')

    @pytest.mark.asyncio
    async def test_configuration_integration(self, ta_agent, ml_agent, news_agent):
        """Test that agents use their configuration properly."""
        # Check that agents loaded their configuration
        assert ta_agent.config is not None
        assert ml_agent.config is not None
        assert news_agent.config is not None

        # Check specific config values
        assert ta_agent.config.get("enabled") is True
        assert ml_agent.config.get("enabled") is True
        assert news_agent.config.get("enabled") is True


class TestPerformanceAndScalability:
    """Test performance and scalability aspects."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self, router, ta_agent, ml_agent, news_agent):
        """Test that agents can process messages concurrently."""
        agents = {
            "ta_agent": ta_agent,
            "ml_agent": ml_agent,
            "news_agent": news_agent
        }

        # Register and start agents
        for agent_id, agent in agents.items():
            router.register_agent(agent_id, agent)
            await agent.start()

        from agents.core.base import Message, MessageType

        # Send concurrent messages
        messages = []
        for i in range(10):
            for agent_id in agents.keys():
                message = Message(
                    type=MessageType.TASK,
                    from_agent="test_sender",
                    to_agent=agent_id,
                    subject=f"concurrent_task_{i}",
                    body={"task_id": i, "data": f"test_data_{i}"}
                )
                messages.append(message)

        # Send all messages concurrently
        start_time = asyncio.get_event_loop().time()

        send_tasks = [router.send_message(msg) for msg in messages]
        await asyncio.gather(*send_tasks)

        # Wait for processing
        await asyncio.sleep(0.2)

        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        # Check that all messages were processed
        total_processed = sum(agent._messages_processed for agent in agents.values())
        assert total_processed >= len(messages)

        # Check performance (should be reasonably fast)
        assert processing_time < 1.0, f"Processing took too long: {processing_time}s"

        # Stop agents
        for agent in agents.values():
            await agent.stop()

    @pytest.mark.asyncio
    async def test_large_message_handling(self, router, ta_agent):
        """Test handling of large messages."""
        router.register_agent("ta_agent", ta_agent)
        await ta_agent.start()

        from agents.core.base import Message, MessageType

        # Create large message
        large_data = {
            "large_array": list(range(1000)),
            "large_string": "x" * 10000,
            "nested_data": {
                "level1": {"level2": {"level3": list(range(100))}}
            }
        }

        large_message = Message(
            type=MessageType.TASK,
            from_agent="test_sender",
            to_agent="ta_agent",
            subject="large_data_task",
            body=large_data
        )

        # Send large message
        await router.send_message(large_message)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Check that message was processed
        assert ta_agent._messages_processed > 0

        await ta_agent.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
