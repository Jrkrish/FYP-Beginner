"""
Agent Registry Module

Manages the lifecycle and discovery of agents in the DevPilot system.
"""

from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import asyncio
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentConfig, AgentState


class AgentRegistry:
    """
    Registry for managing agents in the DevPilot system.
    
    Provides:
    - Agent registration and discovery
    - Lifecycle management
    - Load balancing for agent selection
    - Health monitoring
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure single registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the registry."""
        if self._initialized:
            return
            
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_types: Dict[str, List[str]] = {}  # type -> [agent_ids]
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}  # type -> class
        self._health_check_interval = 30  # seconds
        self._initialized = True
        
        logger.info("AgentRegistry initialized")
    
    def register_agent_class(self, agent_type: str, agent_class: Type[BaseAgent]):
        """
        Register an agent class for a specific type.
        
        Args:
            agent_type: Type identifier for the agent
            agent_class: The agent class to register
        """
        self._agent_classes[agent_type] = agent_class
        logger.info(f"Registered agent class: {agent_type} -> {agent_class.__name__}")
    
    def register_agent(self, agent: BaseAgent) -> str:
        """
        Register an agent instance.
        
        Args:
            agent: The agent instance to register
            
        Returns:
            The agent's ID
        """
        agent_id = agent.agent_id
        agent_type = agent.agent_type
        
        self._agents[agent_id] = agent
        
        if agent_type not in self._agent_types:
            self._agent_types[agent_type] = []
        self._agent_types[agent_type].append(agent_id)
        
        # Register state change callback
        agent.register_state_callback(self._on_agent_state_change)
        
        logger.info(f"Registered agent: {agent.name} (ID: {agent_id}, Type: {agent_type})")
        return agent_id
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of the agent to unregister
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent not found: {agent_id}")
            return
        
        agent = self._agents[agent_id]
        agent_type = agent.agent_type
        
        del self._agents[agent_id]
        
        if agent_type in self._agent_types:
            self._agent_types[agent_type].remove(agent_id)
            if not self._agent_types[agent_type]:
                del self._agent_types[agent_type]
        
        logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: The agent's ID
            
        Returns:
            The agent instance or None
        """
        return self._agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseAgent]:
        """
        Get all agents of a specific type.
        
        Args:
            agent_type: The type of agents to retrieve
            
        Returns:
            List of agents of the specified type
        """
        agent_ids = self._agent_types.get(agent_type, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_available_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """
        Get an available agent of a specific type.
        
        Uses simple load balancing - returns the first available agent.
        
        Args:
            agent_type: The type of agent needed
            
        Returns:
            An available agent or None
        """
        agents = self.get_agents_by_type(agent_type)
        
        for agent in agents:
            if agent.is_available:
                return agent
        
        return None
    
    def get_best_agent(
        self, 
        agent_type: str, 
        task_type: Optional[str] = None
    ) -> Optional[BaseAgent]:
        """
        Get the best available agent for a task.
        
        Considers:
        - Availability
        - Current workload (via metrics)
        - Capability match
        
        Args:
            agent_type: The type of agent needed
            task_type: Optional specific task type for capability matching
            
        Returns:
            The best available agent or None
        """
        agents = self.get_agents_by_type(agent_type)
        available_agents = [a for a in agents if a.is_available]
        
        if not available_agents:
            return None
        
        if len(available_agents) == 1:
            return available_agents[0]
        
        # Score agents based on metrics
        def score_agent(agent: BaseAgent) -> float:
            metrics = agent.get_metrics()
            # Lower score is better
            score = 0.0
            
            # Prefer agents with lower failure rate
            total_tasks = metrics["tasks_completed"] + metrics["tasks_failed"]
            if total_tasks > 0:
                failure_rate = metrics["tasks_failed"] / total_tasks
                score += failure_rate * 100
            
            # Prefer agents with lower average processing time
            if metrics["tasks_completed"] > 0:
                avg_time = metrics["total_processing_time"] / metrics["tasks_completed"]
                score += avg_time * 0.1
            
            return score
        
        # Return agent with lowest score
        return min(available_agents, key=score_agent)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_all_agent_ids(self) -> List[str]:
        """Get all registered agent IDs."""
        return list(self._agents.keys())
    
    def get_agent_types(self) -> List[str]:
        """Get all registered agent types."""
        return list(self._agent_types.keys())
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get the current status of the registry."""
        type_counts = {
            agent_type: len(agent_ids) 
            for agent_type, agent_ids in self._agent_types.items()
        }
        
        state_counts = {}
        for agent in self._agents.values():
            state = agent.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            "total_agents": len(self._agents),
            "agent_types": type_counts,
            "agent_states": state_counts,
            "registered_classes": list(self._agent_classes.keys()),
        }
    
    def create_agent(
        self,
        agent_type: str,
        llm: Any,
        config_overrides: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create and register a new agent instance.
        
        Args:
            agent_type: Type of agent to create
            llm: Language model for the agent
            config_overrides: Optional config overrides
            **kwargs: Additional arguments for agent creation
            
        Returns:
            The created agent instance
        """
        if agent_type not in self._agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self._agent_classes[agent_type]
        
        # Create agent
        agent = agent_class(llm=llm, **kwargs)
        
        # Apply config overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(agent.config, key):
                    setattr(agent.config, key, value)
        
        # Register the agent
        self.register_agent(agent)
        
        return agent
    
    def _on_agent_state_change(
        self, 
        agent: BaseAgent, 
        old_state: AgentState, 
        new_state: AgentState
    ):
        """Callback for agent state changes."""
        logger.debug(
            f"Registry: Agent {agent.name} state changed from "
            f"{old_state.value} to {new_state.value}"
        )
        # Could broadcast this event via message bus if needed
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all agents.
        
        Returns:
            Health status for each agent
        """
        health_status = {}
        
        for agent_id, agent in self._agents.items():
            try:
                status = agent.get_status()
                health_status[agent_id] = {
                    "healthy": True,
                    "state": status["state"],
                    "metrics": status["metrics"],
                }
            except Exception as e:
                health_status[agent_id] = {
                    "healthy": False,
                    "error": str(e),
                }
        
        return health_status
    
    async def start_health_monitoring(self):
        """Start periodic health monitoring."""
        while True:
            await asyncio.sleep(self._health_check_interval)
            health = await self.health_check()
            
            # Log any unhealthy agents
            unhealthy = [
                aid for aid, status in health.items() 
                if not status.get("healthy", True)
            ]
            if unhealthy:
                logger.warning(f"Unhealthy agents detected: {unhealthy}")
    
    def reset(self):
        """Reset the registry (useful for testing)."""
        self._agents.clear()
        self._agent_types.clear()
        logger.info("AgentRegistry reset")
    
    def __len__(self) -> int:
        return len(self._agents)
    
    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents
    
    def __iter__(self):
        return iter(self._agents.values())


# Global registry instance
_registry = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def register_agent_type(agent_type: str):
    """
    Decorator to register an agent class.
    
    Usage:
        @register_agent_type("supervisor")
        class SupervisorAgent(BaseAgent):
            ...
    """
    def decorator(cls: Type[BaseAgent]):
        get_registry().register_agent_class(agent_type, cls)
        return cls
    return decorator
