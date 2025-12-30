"""
Agentic System Module

Main system that bootstraps and orchestrates the multi-agent SDLC platform.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import asyncio
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent
from src.dev_pilot.agents.agent_registry import get_registry, AgentRegistry
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.orchestration.message_bus import MessageBus, InMemoryMessageBus
from src.dev_pilot.orchestration.workflow_engine import WorkflowEngine, SDLCWorkflowBuilder
from src.dev_pilot.orchestration.task_queue import TaskQueue, InMemoryTaskQueue
from src.dev_pilot.memory.context_manager import ContextManager, ProjectContext
from src.dev_pilot.memory.conversation_history import ConversationHistory, MessageRole
from src.dev_pilot.core.agent_factory import AgentFactory


class AgenticSystem:
    """
    Main system for the DevPilot multi-agent SDLC platform.
    
    Provides:
    - System initialization and bootstrapping
    - Workflow execution
    - Project management
    - Agent coordination
    """
    
    def __init__(
        self,
        llm: Any,
        storage_backend: str = "memory",
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize the agentic system.
        
        Args:
            llm: Language model instance
            storage_backend: "memory" or "redis"
            redis_client: Redis client for redis backend
        """
        self.llm = llm
        self._storage_backend = storage_backend
        self._redis = redis_client
        
        # Initialize components
        self.message_bus = InMemoryMessageBus()
        self.task_queue = InMemoryTaskQueue()
        self.context_manager = ContextManager(storage_backend, redis_client)
        self.registry = get_registry()
        
        # Initialize factory and workflow engine
        self.agent_factory = AgentFactory(
            llm=llm,
            message_bus=self.message_bus,
            context_manager=self.context_manager,
            registry=self.registry,
        )
        
        self.workflow_engine = WorkflowEngine(
            message_bus=self.message_bus,
            task_queue=self.task_queue,
            registry=self.registry,
        )
        
        # Project tracking
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._conversation_histories: Dict[str, ConversationHistory] = {}
        
        # System state
        self._initialized = False
        self._agents: Dict[str, BaseAgent] = {}
        
        logger.info("AgenticSystem created")
    
    async def initialize(self) -> bool:
        """
        Initialize and bootstrap the system.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            # Start message bus
            await self.message_bus.start()
            
            # Create SDLC team
            self._agents = self.agent_factory.create_sdlc_team()
            
            # Register standard SDLC workflow
            sdlc_workflow = SDLCWorkflowBuilder.build_standard_sdlc_workflow()
            self.workflow_engine.register_workflow(sdlc_workflow)
            
            # Setup event handlers
            self._setup_event_handlers()
            
            self._initialized = True
            logger.info("AgenticSystem initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the system."""
        try:
            await self.message_bus.stop()
            self.agent_factory.shutdown_all()
            self._initialized = False
            logger.info("AgenticSystem shutdown")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _setup_event_handlers(self):
        """Setup event handlers for workflow events."""
        self.workflow_engine.on_event("workflow_started", self._on_workflow_started)
        self.workflow_engine.on_event("workflow_completed", self._on_workflow_completed)
        self.workflow_engine.on_event("step_completed", self._on_step_completed)
        self.workflow_engine.on_event("approval_required", self._on_approval_required)
    
    async def _on_workflow_started(self, execution):
        """Handle workflow started event."""
        logger.info(f"Workflow started: {execution.execution_id}")
    
    async def _on_workflow_completed(self, execution):
        """Handle workflow completed event."""
        logger.info(f"Workflow completed: {execution.execution_id}")
    
    async def _on_step_completed(self, data):
        """Handle step completed event."""
        step = data.get("step")
        logger.info(f"Step completed: {step.name if step else 'unknown'}")
    
    async def _on_approval_required(self, data):
        """Handle approval required event."""
        execution = data.get("execution")
        step = data.get("step")
        logger.info(f"Approval required for {step.name if step else 'unknown'}")
    
    # ============ Project Management ============
    
    async def create_project(
        self,
        project_name: str,
        requirements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            project_name: Name of the project
            requirements: Optional list of requirements
            
        Returns:
            Project information
        """
        project_id = f"project-{uuid.uuid4().hex[:8]}"
        
        # Create project context
        context = await self.context_manager.create_project_context(
            project_id=project_id,
            project_name=project_name,
            requirements=requirements,
        )
        
        # Create conversation history
        self._conversation_histories[project_id] = ConversationHistory(project_id)
        
        # Store project info
        self._projects[project_id] = {
            "project_id": project_id,
            "project_name": project_name,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "workflow_execution_id": None,
        }
        
        logger.info(f"Project created: {project_name} ({project_id})")
        
        return self._projects[project_id]
    
    async def start_project_workflow(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Start the SDLC workflow for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Workflow execution info
        """
        if project_id not in self._projects:
            raise ValueError(f"Project not found: {project_id}")
        
        project = self._projects[project_id]
        context = await self.context_manager.get_project_context(project_id)
        
        if not context:
            raise ValueError(f"Project context not found: {project_id}")
        
        # Get the SDLC workflow
        workflows = list(self.workflow_engine._workflows.values())
        if not workflows:
            raise RuntimeError("No workflow registered")
        
        workflow = workflows[0]  # Standard SDLC workflow
        
        # Execute workflow
        execution = await self.workflow_engine.execute_workflow(
            workflow_id=workflow.workflow_id,
            context=context.to_dict(),
        )
        
        project["workflow_execution_id"] = execution.execution_id
        project["status"] = "in_progress"
        
        return {
            "project_id": project_id,
            "execution_id": execution.execution_id,
            "status": execution.status.value,
        }
    
    async def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get project status."""
        if project_id not in self._projects:
            raise ValueError(f"Project not found: {project_id}")
        
        project = self._projects[project_id]
        context = await self.context_manager.get_project_context(project_id)
        
        execution_id = project.get("workflow_execution_id")
        execution = None
        if execution_id:
            execution = self.workflow_engine.get_execution(execution_id)
        
        return {
            "project": project,
            "context": context.to_dict() if context else None,
            "execution": execution.to_dict() if execution else None,
            "current_phase": context.current_phase if context else None,
        }
    
    # ============ Workflow Actions ============
    
    async def submit_requirements(
        self,
        project_id: str,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """
        Submit requirements for a project.
        
        Args:
            project_id: Project ID
            requirements: List of requirements
            
        Returns:
            Updated project state
        """
        context = await self.context_manager.update_project_context(
            project_id,
            requirements=requirements,
            current_phase="requirements_submitted",
        )
        
        # Add to conversation history
        history = self._conversation_histories.get(project_id)
        if history:
            history.add_user_message(
                f"Requirements submitted: {requirements}",
                metadata={"type": "requirements"}
            )
        
        return {"status": "requirements_submitted", "context": context.to_dict()}
    
    async def approve_stage(
        self,
        project_id: str,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approve the current stage.
        
        Args:
            project_id: Project ID
            feedback: Optional feedback
            
        Returns:
            Updated status
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        
        execution_id = project.get("workflow_execution_id")
        if not execution_id:
            raise ValueError("No active workflow execution")
        
        await self.workflow_engine.approve_step(
            execution_id=execution_id,
            feedback=feedback,
        )
        
        return {"status": "approved", "feedback": feedback}
    
    async def reject_stage(
        self,
        project_id: str,
        feedback: str,
    ) -> Dict[str, Any]:
        """
        Reject the current stage with feedback.
        
        Args:
            project_id: Project ID
            feedback: Feedback/reason for rejection
            
        Returns:
            Updated status
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        
        execution_id = project.get("workflow_execution_id")
        if not execution_id:
            raise ValueError("No active workflow execution")
        
        await self.workflow_engine.reject_step(
            execution_id=execution_id,
            feedback=feedback,
        )
        
        return {"status": "rejected", "feedback": feedback}
    
    # ============ Direct Agent Interaction ============
    
    async def execute_agent_task(
        self,
        agent_type: str,
        task_type: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a task with a specific agent type.
        
        Args:
            agent_type: Type of agent to use
            task_type: Type of task
            input_data: Task input data
            
        Returns:
            Task result
        """
        agent = self.registry.get_best_agent(agent_type)
        if not agent:
            raise ValueError(f"No available agent of type: {agent_type}")
        
        task = AgentTask.create(
            task_type=task_type,
            input_data=input_data,
            assigned_agent=agent.agent_id,
        )
        
        result = await agent.execute_task(task)
        return result
    
    # ============ System Information ============
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "initialized": self._initialized,
            "agents": {
                agent_type: {
                    "id": agent.agent_id,
                    "name": agent.name,
                    "state": agent.state.value,
                    "metrics": agent.get_metrics(),
                }
                for agent_type, agent in self._agents.items()
            },
            "projects_count": len(self._projects),
            "message_bus": self.message_bus.get_metrics(),
            "workflow_engine": self.workflow_engine.get_status(),
            "registry": self.registry.get_registry_status(),
        }
    
    def get_agent_status(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        agent = self._agents.get(agent_type)
        if agent:
            return agent.get_status()
        return None
    
    def get_conversation_history(self, project_id: str) -> Optional[ConversationHistory]:
        """Get conversation history for a project."""
        return self._conversation_histories.get(project_id)
