"""
Agent Factory Module

Creates and configures agents for the multi-agent system.
"""

from typing import Any, Dict, List, Optional, Type
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent
from src.dev_pilot.agents.agent_registry import get_registry, AgentRegistry
from src.dev_pilot.agents.supervisor_agent import SupervisorAgent
from src.dev_pilot.agents.specialized.ba_agent import BusinessAnalystAgent
from src.dev_pilot.agents.specialized.architect_agent import ArchitectAgent
from src.dev_pilot.agents.specialized.developer_agent import DeveloperAgent
from src.dev_pilot.agents.specialized.code_review_agent import CodeReviewAgent
from src.dev_pilot.agents.specialized.security_agent import SecurityAgent
from src.dev_pilot.agents.specialized.qa_agent import QAAgent
from src.dev_pilot.agents.specialized.devops_agent import DevOpsAgent
from src.dev_pilot.orchestration.message_bus import MessageBus, InMemoryMessageBus
from src.dev_pilot.memory.context_manager import ContextManager


# Agent type to class mapping
AGENT_CLASSES: Dict[str, Type[BaseAgent]] = {
    "supervisor": SupervisorAgent,
    "business_analyst": BusinessAnalystAgent,
    "architect": ArchitectAgent,
    "developer": DeveloperAgent,
    "code_review": CodeReviewAgent,
    "security": SecurityAgent,
    "qa": QAAgent,
    "devops": DevOpsAgent,
}


class AgentFactory:
    """
    Factory for creating and configuring agents.
    
    Provides:
    - Agent instantiation with proper configuration
    - Automatic registration with registry
    - Message bus and context manager injection
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Optional[MessageBus] = None,
        context_manager: Optional[ContextManager] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        """
        Initialize agent factory.
        
        Args:
            llm: Language model instance to use for agents
            message_bus: Message bus for agent communication
            context_manager: Context manager for shared state
            registry: Agent registry (uses global if not provided)
        """
        self.llm = llm
        self.message_bus = message_bus or InMemoryMessageBus()
        self.context_manager = context_manager or ContextManager()
        self.registry = registry or get_registry()
        
        self._created_agents: Dict[str, BaseAgent] = {}
        
        logger.info("AgentFactory initialized")
    
    def create_agent(
        self,
        agent_type: str,
        register: bool = True,
    ) -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Type of agent to create
            register: Whether to register with registry
            
        Returns:
            Created agent instance
        """
        if agent_type not in AGENT_CLASSES:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = AGENT_CLASSES[agent_type]
        
        agent = agent_class(
            llm=self.llm,
            message_bus=self.message_bus,
            context_manager=self.context_manager,
        )
        
        if register:
            self.registry.register_agent(agent)
            # Register direct message handler
            self.message_bus.register_direct_handler(
                agent.agent_id,
                agent.receive_message
            )
        
        self._created_agents[agent.agent_id] = agent
        
        logger.info(f"Created agent: {agent.name} ({agent_type})")
        return agent
    
    def create_all_agents(self) -> Dict[str, BaseAgent]:
        """
        Create one instance of each agent type.
        
        Returns:
            Dictionary mapping agent type to agent instance
        """
        agents = {}
        
        for agent_type in AGENT_CLASSES.keys():
            agent = self.create_agent(agent_type)
            agents[agent_type] = agent
        
        logger.info(f"Created {len(agents)} agents")
        return agents
    
    def create_sdlc_team(self) -> Dict[str, BaseAgent]:
        """
        Create a complete SDLC team with all required agents.
        
        Returns:
            Dictionary of agents by type
        """
        team = {}
        
        # Create supervisor first
        team["supervisor"] = self.create_agent("supervisor")
        
        # Create specialized agents
        team["business_analyst"] = self.create_agent("business_analyst")
        team["architect"] = self.create_agent("architect")
        team["developer"] = self.create_agent("developer")
        team["code_review"] = self.create_agent("code_review")
        team["security"] = self.create_agent("security")
        team["qa"] = self.create_agent("qa")
        team["devops"] = self.create_agent("devops")
        
        logger.info("SDLC team created with 8 agents")
        return team
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._created_agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseAgent]:
        """Get all agents of a specific type."""
        return [
            agent for agent in self._created_agents.values()
            if agent.agent_type == agent_type
        ]
    
    def shutdown_all(self):
        """Shutdown all created agents."""
        for agent in self._created_agents.values():
            agent.reset()
            self.message_bus.unregister_direct_handler(agent.agent_id)
        
        self._created_agents.clear()
        logger.info("All agents shutdown")
