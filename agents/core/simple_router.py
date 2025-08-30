"""
Simplified Router for the AiBotBS Runtime Agent System.
Follows SOLID principles with minimal, focused functionality.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Dict
from uuid import uuid4

from .base import BaseAgent, Message, MessageType, MessagePriority
from .queue import MessageQueue
from .agent_registry import AgentRegistry


class SimpleRouter:
    """Simplified router for agent coordination."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("simple_router")
        
        # Core components
        self._agent_registry = AgentRegistry()
        self._message_queue = MessageQueue()
        
        # State
        self._running = False
        self._start_time = None
        
        # Statistics
        self._messages_processed = 0
    
    async def start(self) -> None:
        """Start the router."""
        try:
            self.logger.info("Starting simple router")
            self._running = True
            self._start_time = datetime.now(UTC)
            
            # Load and register agents
            await self._load_agents()
            
            # Start message processing
            asyncio.create_task(self._process_messages())
            
            self.logger.info("Simple router started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start router: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the router."""
        try:
            self.logger.info("Stopping simple router")
            self._running = False
            self.logger.info("Simple router stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop router: {e}")
            raise
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agent_registry.register_agent(agent)
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        self._agent_registry.unregister_agent(agent_id)
    
    async def enqueue(self, message_type: str, body: Dict[str, Any]) -> None:
        """Enqueue a message."""
        await self._message_queue.enqueue(message_type, body)
    
    async def post_tick(self) -> None:
        """Post a heartbeat tick."""
        try:
            await self.enqueue("TICK", {
                "type": "heartbeat", 
                "timestamp": datetime.now(UTC).isoformat()
            })
            self.logger.debug("Heartbeat tick posted")
            
        except Exception as e:
            self.logger.warning(f"Failed to post heartbeat tick: {e}")
    
    async def _process_messages(self) -> None:
        """Process messages from queues."""
        while self._running:
            try:
                # Process high priority first
                message = await self._message_queue.dequeue_high_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # Then normal priority
                message = await self._message_queue.dequeue_normal_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # Finally low priority
                message = await self._message_queue.dequeue_low_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # No messages, sleep briefly
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
                await asyncio.sleep(1)
    
    async def _load_agents(self) -> None:
        """Load and register available agents."""
        try:
            self.logger.info("Loading agents...")
            
            # Import and register each agent type
            agent_modules = [
                ("orchestrator", "OrchestratorAgent"),
                ("ta_agent", "TechnicalAnalysisAgent"),
                ("ml_agent", "MachineLearningAgent"),
                ("news_agent", "NewsAgent"),
                ("signal_agent", "SignalAgent"),
                ("risk_agent", "RiskManagementAgent"),
                ("portfolio_agent", "PortfolioAgent"),
                ("execution_agent", "ExecutionAgent"),
                ("qa_agent", "QAAgent")
            ]
            
            for module_name, class_name in agent_modules:
                try:
                    # Import agent module
                    module = __import__(f"agents.roles.{module_name}", fromlist=[class_name])
                    agent_class = getattr(module, class_name)
                    
                    # Create agent instance with proper config
                    agent_config = {
                        "agent_id": f"{module_name}_agent",
                        "agent_type": module_name,
                        "enabled": True,
                        "max_concurrent_tasks": 5
                    }
                    agent = agent_class(f"{module_name}_agent", agent_config)
                    
                    # Register agent
                    self.register_agent(agent)
                    
                    self.logger.info(f"✅ Loaded agent: {module_name}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to load {module_name}: {e}")
            
            self.logger.info(f"Agent loading complete. Total: {self._agent_registry.get_agent_count()}")
            
        except Exception as e:
            self.logger.error(f"Failed to load agents: {e}")
    
    async def _handle_message(self, message: Message) -> None:
        """Handle a single message."""
        try:
            self._messages_processed += 1
            self.logger.debug(f"Processing message: {message.subject}")
            
            # Simple message handling - just log for now
            if message.subject == "TICK":
                self.logger.debug("HB tick processed")
            else:
                self.logger.debug(f"Message processed: {message.subject}")
                
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(UTC) - self._start_time).total_seconds()
        
        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "messages_processed": self._messages_processed,
            "agent_count": self._agent_registry.get_agent_count(),
            "queue_stats": self._message_queue.get_stats()
        }


# Global simple router instance
_simple_router_instance = None

def get_simple_router() -> SimpleRouter:
    """Get the global simple router instance."""
    global _simple_router_instance
    if _simple_router_instance is None:
        config = {
            "max_concurrent_routes": 5,
            "route_timeout": 300,
            "enable_monitoring": True
        }
        _simple_router_instance = SimpleRouter(config)
    return _simple_router_instance
