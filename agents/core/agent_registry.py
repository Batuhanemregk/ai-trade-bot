"""
Agent Registry for the AiBotBS Runtime Agent System.
Handles agent registration, discovery, and status management.
"""

import logging
from typing import Any, Dict, Optional
from .base import BaseAgent


class AgentRegistry:
    """Registry for managing agents."""
    
    def __init__(self):
        self.logger = logging.getLogger("agent_registry")
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_types: Dict[str, str] = {}  # agent_id -> agent_type
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the registry."""
        try:
            self._agents[agent.agent_id] = agent
            self._agent_types[agent.agent_id] = agent.agent_type
            self.logger.info(f"Registered agent: {agent.agent_id} ({agent.agent_type})")
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent.agent_id}: {e}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the registry."""
        try:
            if agent_id in self._agents:
                del self._agents[agent_id]
                del self._agent_types[agent_id]
                self.logger.info(f"Unregistered agent: {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_id}: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        return list(self._agents.keys())
    
    def list_agents_by_type(self, agent_type: str) -> list[str]:
        """List agent IDs by type."""
        return [aid for aid, atype in self._agent_types.items() if atype == agent_type]
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        agent = self.get_agent(agent_id)
        if agent:
            return agent.get_status()
        return None
    
    def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents."""
        return {aid: agent.get_status() for aid, agent in self._agents.items()}
    
    def get_agent_count(self) -> int:
        """Get total number of registered agents."""
        return len(self._agents)
    
    def get_agent_type_count(self, agent_type: str) -> int:
        """Get count of agents by type."""
        return len(self.list_agents_by_type(agent_type))
    
    def is_agent_registered(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents
    
    def get_agent_capabilities(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get capabilities of a specific agent."""
        agent = self.get_agent(agent_id)
        if agent:
            return agent.describe()
        return None
