"""
Base Agent Module

Defines the abstract base class for all agents in the DevPilot system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import asyncio
import uuid
from loguru import logger

from src.dev_pilot.agents.agent_message import (
    AgentMessage, 
    AgentTask, 
    MessageType, 
    MessagePriority
)


class AgentState(Enum):
    """Possible states an agent can be in."""
    IDLE = "idle"              # Agent is ready to accept tasks
    WORKING = "working"        # Agent is processing a task
    REVIEWING = "reviewing"    # Agent is reviewing/waiting for approval
    COMPLETED = "completed"    # Agent has completed its task
    BLOCKED = "blocked"        # Agent is blocked waiting for dependency
    ERROR = "error"            # Agent encountered an error
    PAUSED = "paused"          # Agent is paused


@dataclass
class AgentCapability:
    """Describes a capability/skill of an agent."""
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    

@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    model_name: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the DevPilot system.
    
    Agents are autonomous units that can:
    - Process tasks assigned to them
    - Communicate with other agents via messages
    - Maintain their own state
    - Use tools/capabilities to accomplish tasks
    - Access shared context and memory
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm: Any,
        message_bus: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            config: Agent configuration
            llm: Language model to use for reasoning
            message_bus: Message bus for inter-agent communication
            context_manager: Manager for shared context/memory
        """
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        self.name = config.name
        self.llm = llm
        self.message_bus = message_bus
        self.context_manager = context_manager
        
        # State management
        self._state = AgentState.IDLE
        self._current_task: Optional[AgentTask] = None
        self._task_history: List[AgentTask] = []
        self._message_queue: List[AgentMessage] = []
        
        # Callbacks
        self._state_change_callbacks: List[Callable] = []
        self._message_handlers: Dict[MessageType, Callable] = {}
        
        # Tools/Capabilities
        self._tools: Dict[str, Callable] = {}
        
        # Metrics
        self._metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "total_processing_time": 0.0,
        }
        
        # Register default message handlers
        self._register_default_handlers()
        
        logger.info(f"Agent initialized: {self.name} ({self.agent_type})")
    
    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state
    
    @state.setter
    def state(self, new_state: AgentState):
        """Set agent state and trigger callbacks."""
        old_state = self._state
        self._state = new_state
        logger.debug(f"Agent {self.name} state changed: {old_state.value} -> {new_state.value}")
        for callback in self._state_change_callbacks:
            try:
                callback(self, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available to accept tasks."""
        return self._state in [AgentState.IDLE, AgentState.COMPLETED]
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self._message_handlers[MessageType.REQUEST] = self._handle_request
        self._message_handlers[MessageType.RESPONSE] = self._handle_response
        self._message_handlers[MessageType.NOTIFY] = self._handle_notification
        self._message_handlers[MessageType.ERROR] = self._handle_error
        self._message_handlers[MessageType.STATUS] = self._handle_status
        self._message_handlers[MessageType.BROADCAST] = self._handle_broadcast
    
    def register_tool(self, name: str, func: Callable, description: str = ""):
        """Register a tool/capability for the agent to use."""
        self._tools[name] = func
        self.config.capabilities.append(
            AgentCapability(name=name, description=description)
        )
        logger.debug(f"Agent {self.name} registered tool: {name}")
    
    def register_state_callback(self, callback: Callable):
        """Register a callback for state changes."""
        self._state_change_callbacks.append(callback)
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a custom message handler."""
        self._message_handlers[message_type] = handler
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Process a task assigned to this agent.
        
        This is the main method that subclasses must implement.
        
        Args:
            task: The task to process
            
        Returns:
            Result of the task processing
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        
        Returns:
            The system prompt defining the agent's persona and capabilities
        """
        pass
    
    # ==================== Task Management ====================
    
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task with full lifecycle management.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        if not self.is_available:
            raise RuntimeError(f"Agent {self.name} is not available (state: {self.state.value})")
        
        self._current_task = task
        task.mark_started()
        self.state = AgentState.WORKING
        
        start_time = datetime.utcnow()
        
        try:
            # Check dependencies
            if task.dependencies:
                if not await self._check_dependencies(task.dependencies):
                    task.mark_blocked("Dependencies not satisfied")
                    self.state = AgentState.BLOCKED
                    return {"status": "blocked", "reason": "Dependencies not satisfied"}
            
            # Process the task
            result = await self.process_task(task)
            
            # Mark completed
            task.mark_completed(result)
            self._task_history.append(task)
            self._metrics["tasks_completed"] += 1
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            self._metrics["total_processing_time"] += processing_time
            
            self.state = AgentState.COMPLETED
            logger.info(f"Agent {self.name} completed task {task.task_id} in {processing_time:.2f}s")
            
            # Notify completion
            await self._notify_task_completion(task, result)
            
            return result
            
        except Exception as e:
            task.mark_failed(str(e))
            self._metrics["tasks_failed"] += 1
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.name} failed task {task.task_id}: {e}")
            
            # Notify failure
            await self._notify_task_failure(task, str(e))
            
            raise
        finally:
            self._current_task = None
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all task dependencies are satisfied."""
        # This would typically check with a task registry
        # For now, return True
        return True
    
    async def _notify_task_completion(self, task: AgentTask, result: Dict[str, Any]):
        """Notify other agents/systems of task completion."""
        if self.message_bus:
            message = AgentMessage.create_broadcast(
                sender=self.agent_id,
                event="task_completed",
                data={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "result": result,
                }
            )
            await self.send_message(message)
    
    async def _notify_task_failure(self, task: AgentTask, error: str):
        """Notify other agents/systems of task failure."""
        if self.message_bus:
            message = AgentMessage.create_broadcast(
                sender=self.agent_id,
                event="task_failed",
                data={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "error": error,
                }
            )
            await self.send_message(message)
    
    # ==================== Message Handling ====================
    
    async def send_message(self, message: AgentMessage):
        """Send a message to another agent or broadcast."""
        if self.message_bus:
            await self.message_bus.publish(message)
            self._metrics["messages_sent"] += 1
            logger.debug(f"Agent {self.name} sent message to {message.recipient}")
        else:
            logger.warning(f"Agent {self.name} has no message bus configured")
    
    async def receive_message(self, message: AgentMessage):
        """Process a received message."""
        self._metrics["messages_received"] += 1
        logger.debug(f"Agent {self.name} received message from {message.sender}")
        
        handler = self._message_handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await self._send_error_response(message, str(e))
        else:
            logger.warning(f"No handler for message type: {message.message_type}")
    
    async def _handle_request(self, message: AgentMessage):
        """Handle incoming request messages."""
        action = message.payload.get("action")
        data = message.payload.get("data", {})
        
        logger.debug(f"Agent {self.name} handling request: {action}")
        
        # Create a task from the request
        task = AgentTask.create(
            task_type=action,
            input_data=data,
            assigned_agent=self.agent_id,
        )
        
        try:
            result = await self.execute_task(task)
            response = message.create_response(
                sender=self.agent_id,
                payload={"status": "success", "result": result}
            )
            await self.send_message(response)
        except Exception as e:
            error_response = message.create_error_response(
                sender=self.agent_id,
                error_message=str(e)
            )
            await self.send_message(error_response)
    
    async def _handle_response(self, message: AgentMessage):
        """Handle incoming response messages."""
        logger.debug(f"Agent {self.name} received response for {message.correlation_id}")
        # Subclasses can override to handle responses
    
    async def _handle_notification(self, message: AgentMessage):
        """Handle incoming notification messages."""
        event = message.payload.get("event")
        logger.debug(f"Agent {self.name} received notification: {event}")
        # Subclasses can override to handle specific notifications
    
    async def _handle_error(self, message: AgentMessage):
        """Handle incoming error messages."""
        error = message.payload.get("error")
        logger.error(f"Agent {self.name} received error: {error}")
    
    async def _handle_status(self, message: AgentMessage):
        """Handle incoming status messages."""
        logger.debug(f"Agent {self.name} received status update")
    
    async def _handle_broadcast(self, message: AgentMessage):
        """Handle broadcast messages."""
        event = message.payload.get("event")
        logger.debug(f"Agent {self.name} received broadcast: {event}")
    
    async def _send_error_response(self, original_message: AgentMessage, error: str):
        """Send an error response to a message."""
        error_response = original_message.create_error_response(
            sender=self.agent_id,
            error_message=error
        )
        await self.send_message(error_response)
    
    # ==================== Tool Execution ====================
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        
        tool_func = self._tools[tool_name]
        logger.debug(f"Agent {self.name} executing tool: {tool_name}")
        
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**kwargs)
        else:
            return tool_func(**kwargs)
    
    # ==================== Context Management ====================
    
    async def get_context(self, key: str) -> Any:
        """Get a value from shared context."""
        if self.context_manager:
            return await self.context_manager.get(key)
        return None
    
    async def set_context(self, key: str, value: Any):
        """Set a value in shared context."""
        if self.context_manager:
            await self.context_manager.set(key, value)
    
    async def get_project_context(self) -> Dict[str, Any]:
        """Get the full project context."""
        if self.context_manager:
            return await self.context_manager.get_project_context()
        return {}
    
    # ==================== LLM Interaction ====================
    
    async def think(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Use the LLM to think/reason about something.
        
        Args:
            prompt: The prompt to send to the LLM
            context: Additional context to include
            
        Returns:
            LLM response
        """
        full_prompt = self._build_prompt(prompt, context)
        
        try:
            response = self.llm.invoke(full_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM error in agent {self.name}: {e}")
            raise
    
    async def think_structured(
        self, 
        prompt: str, 
        output_schema: Type,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Use the LLM to generate structured output.
        
        Args:
            prompt: The prompt to send to the LLM
            output_schema: Pydantic model or schema for structured output
            context: Additional context to include
            
        Returns:
            Structured LLM response
        """
        full_prompt = self._build_prompt(prompt, context)
        
        try:
            llm_with_structure = self.llm.with_structured_output(output_schema)
            response = llm_with_structure.invoke(full_prompt)
            return response
        except Exception as e:
            logger.error(f"Structured LLM error in agent {self.name}: {e}")
            raise
    
    def _build_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build a full prompt with system prompt and context."""
        system_prompt = self.get_system_prompt()
        
        parts = [system_prompt, "", prompt]
        
        if context:
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            parts.insert(2, f"\nContext:\n{context_str}\n")
        
        return "\n".join(parts)
    
    # ==================== Utility Methods ====================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return {
            **self._metrics,
            "current_state": self._state.value,
            "tasks_in_history": len(self._task_history),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "state": self._state.value,
            "is_available": self.is_available,
            "current_task": self._current_task.to_dict() if self._current_task else None,
            "metrics": self.get_metrics(),
        }
    
    def reset(self):
        """Reset agent to initial state."""
        self._state = AgentState.IDLE
        self._current_task = None
        self._message_queue.clear()
        logger.info(f"Agent {self.name} reset to IDLE state")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} state={self._state.value}>"
