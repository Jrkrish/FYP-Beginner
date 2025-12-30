"""
DevPilot Multi-Agent System

This module contains the core agent infrastructure for the DevPilot SDLC automation platform.
"""

from src.dev_pilot.agents.base_agent import BaseAgent, AgentState, AgentConfig, AgentCapability
from src.dev_pilot.agents.agent_message import AgentMessage, AgentTask, MessageType, MessagePriority
from src.dev_pilot.agents.agent_registry import AgentRegistry, get_registry, register_agent_type
from src.dev_pilot.agents.supervisor_agent import SupervisorAgent

# Import specialized agents
from src.dev_pilot.agents.specialized.ba_agent import BusinessAnalystAgent
from src.dev_pilot.agents.specialized.architect_agent import ArchitectAgent
from src.dev_pilot.agents.specialized.developer_agent import DeveloperAgent
from src.dev_pilot.agents.specialized.code_review_agent import CodeReviewAgent
from src.dev_pilot.agents.specialized.security_agent import SecurityAgent
from src.dev_pilot.agents.specialized.qa_agent import QAAgent
from src.dev_pilot.agents.specialized.devops_agent import DevOpsAgent

__all__ = [
    # Core
    "BaseAgent",
    "AgentState",
    "AgentConfig",
    "AgentCapability",
    "AgentMessage",
    "AgentTask",
    "MessageType",
    "MessagePriority",
    "AgentRegistry",
    "get_registry",
    "register_agent_type",
    # Agents
    "SupervisorAgent",
    "BusinessAnalystAgent",
    "ArchitectAgent",
    "DeveloperAgent",
    "CodeReviewAgent",
    "SecurityAgent",
    "QAAgent",
    "DevOpsAgent",
]
