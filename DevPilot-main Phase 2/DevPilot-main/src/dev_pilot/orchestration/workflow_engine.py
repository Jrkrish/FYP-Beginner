"""
Workflow Engine Module

Manages the execution of multi-step workflows with agent orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentState
from src.dev_pilot.agents.agent_message import AgentTask, AgentMessage, MessageType, MessagePriority
from src.dev_pilot.agents.agent_registry import AgentRegistry, get_registry
from src.dev_pilot.orchestration.message_bus import MessageBus, InMemoryMessageBus
from src.dev_pilot.orchestration.task_queue import TaskQueue, InMemoryTaskQueue, DependencyTracker


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(Enum):
    """Types of workflow steps."""
    AGENT_TASK = "agent_task"        # Execute a task with an agent
    PARALLEL = "parallel"             # Execute multiple steps in parallel
    CONDITIONAL = "conditional"       # Conditional execution
    HUMAN_REVIEW = "human_review"     # Wait for human approval
    LOOP = "loop"                     # Loop over items
    WAIT = "wait"                     # Wait for a condition


@dataclass
class WorkflowStep:
    """
    Represents a step in a workflow.
    """
    step_id: str
    name: str
    step_type: StepType
    agent_type: Optional[str] = None
    task_type: Optional[str] = None
    input_mapping: Dict[str, str] = field(default_factory=dict)  # Maps workflow context to task input
    output_mapping: Dict[str, str] = field(default_factory=dict)  # Maps task output to workflow context
    condition: Optional[Callable] = None  # For conditional steps
    sub_steps: List["WorkflowStep"] = field(default_factory=list)  # For parallel/loop steps
    retry_count: int = 3
    timeout_seconds: int = 300
    on_failure: str = "fail"  # "fail", "skip", "retry"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def create_agent_step(
        name: str,
        agent_type: str,
        task_type: str,
        input_mapping: Optional[Dict[str, str]] = None,
        output_mapping: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> "WorkflowStep":
        """Factory for creating an agent task step."""
        return WorkflowStep(
            step_id=str(uuid.uuid4()),
            name=name,
            step_type=StepType.AGENT_TASK,
            agent_type=agent_type,
            task_type=task_type,
            input_mapping=input_mapping or {},
            output_mapping=output_mapping or {},
            **kwargs
        )
    
    @staticmethod
    def create_human_review_step(
        name: str,
        review_type: str,
        **kwargs
    ) -> "WorkflowStep":
        """Factory for creating a human review step."""
        return WorkflowStep(
            step_id=str(uuid.uuid4()),
            name=name,
            step_type=StepType.HUMAN_REVIEW,
            metadata={"review_type": review_type},
            **kwargs
        )
    
    @staticmethod
    def create_parallel_step(
        name: str,
        sub_steps: List["WorkflowStep"],
        **kwargs
    ) -> "WorkflowStep":
        """Factory for creating a parallel execution step."""
        return WorkflowStep(
            step_id=str(uuid.uuid4()),
            name=name,
            step_type=StepType.PARALLEL,
            sub_steps=sub_steps,
            **kwargs
        )


@dataclass
class WorkflowExecution:
    """
    Represents an execution instance of a workflow.
    """
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    context: Dict[str, Any]  # Shared context/state
    current_step_index: int = 0
    step_results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "context": self.context,
            "current_step_index": self.current_step_index,
            "step_results": self.step_results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Workflow:
    """
    Represents a workflow definition.
    """
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    @staticmethod
    def create(
        name: str,
        description: str,
        steps: List[WorkflowStep],
        initial_context: Optional[Dict[str, Any]] = None
    ) -> "Workflow":
        """Factory method to create a workflow."""
        return Workflow(
            workflow_id=str(uuid.uuid4()),
            name=name,
            description=description,
            steps=steps,
            initial_context=initial_context or {},
        )


class WorkflowEngine:
    """
    Orchestrates workflow execution with agents.
    
    Responsible for:
    - Executing workflow steps
    - Managing agent coordination
    - Handling human-in-the-loop checkpoints
    - Managing workflow state
    """
    
    def __init__(
        self,
        message_bus: Optional[MessageBus] = None,
        task_queue: Optional[TaskQueue] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        self.message_bus = message_bus or InMemoryMessageBus()
        self.task_queue = task_queue or InMemoryTaskQueue()
        self.registry = registry or get_registry()
        
        # Workflow storage
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        
        # Pending approvals
        self._pending_approvals: Dict[str, WorkflowExecution] = {}
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Dependency tracking
        self._dependency_tracker = DependencyTracker()
        
        logger.info("WorkflowEngine initialized")
    
    async def start(self):
        """Start the workflow engine."""
        await self.message_bus.start()
        logger.info("WorkflowEngine started")
    
    async def stop(self):
        """Stop the workflow engine."""
        await self.message_bus.stop()
        logger.info("WorkflowEngine stopped")
    
    def register_workflow(self, workflow: Workflow):
        """Register a workflow definition."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"Workflow registered: {workflow.name} ({workflow.workflow_id})")
    
    async def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Start executing a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            context: Initial context/inputs for the workflow
            
        Returns:
            WorkflowExecution instance
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Create execution instance
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            context={**workflow.initial_context, **(context or {})},
            started_at=datetime.utcnow(),
        )
        
        self._executions[execution.execution_id] = execution
        
        logger.info(f"Starting workflow execution: {execution.execution_id}")
        
        # Start execution
        await self._run_workflow(execution, workflow)
        
        return execution
    
    async def _run_workflow(self, execution: WorkflowExecution, workflow: Workflow):
        """Run workflow steps sequentially."""
        execution.status = WorkflowStatus.RUNNING
        await self._emit_event("workflow_started", execution)
        
        try:
            while execution.current_step_index < len(workflow.steps):
                step = workflow.steps[execution.current_step_index]
                
                logger.info(f"Executing step {execution.current_step_index + 1}/{len(workflow.steps)}: {step.name}")
                
                # Execute the step
                result = await self._execute_step(execution, step)
                
                # Store result
                execution.step_results[step.step_id] = result
                
                # Check if we need to wait for approval
                if execution.status == WorkflowStatus.WAITING_APPROVAL:
                    logger.info(f"Workflow paused for approval at step: {step.name}")
                    self._pending_approvals[execution.execution_id] = execution
                    await self._emit_event("approval_required", {
                        "execution": execution,
                        "step": step,
                    })
                    return
                
                # Check for failure
                if execution.status == WorkflowStatus.FAILED:
                    break
                
                # Move to next step
                execution.current_step_index += 1
            
            # Workflow completed
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                logger.info(f"Workflow completed: {execution.execution_id}")
                await self._emit_event("workflow_completed", execution)
                
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Workflow failed: {execution.execution_id} - {e}")
            await self._emit_event("workflow_failed", {"execution": execution, "error": str(e)})
    
    async def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a single workflow step."""
        await self._emit_event("step_started", {"execution": execution, "step": step})
        
        try:
            if step.step_type == StepType.AGENT_TASK:
                result = await self._execute_agent_step(execution, step)
            elif step.step_type == StepType.HUMAN_REVIEW:
                result = await self._execute_human_review_step(execution, step)
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel_step(execution, step)
            elif step.step_type == StepType.CONDITIONAL:
                result = await self._execute_conditional_step(execution, step)
            else:
                raise ValueError(f"Unknown step type: {step.step_type}")
            
            # Apply output mapping
            if step.output_mapping:
                for output_key, context_key in step.output_mapping.items():
                    if result and output_key in result:
                        execution.context[context_key] = result[output_key]
            
            await self._emit_event("step_completed", {
                "execution": execution, 
                "step": step, 
                "result": result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Step failed: {step.name} - {e}")
            await self._emit_event("step_failed", {
                "execution": execution, 
                "step": step, 
                "error": str(e)
            })
            
            if step.on_failure == "skip":
                return {"skipped": True, "error": str(e)}
            elif step.on_failure == "retry":
                # Retry logic would go here
                pass
            else:
                execution.status = WorkflowStatus.FAILED
                execution.error = str(e)
                raise
    
    async def _execute_agent_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Execute an agent task step."""
        # Get an available agent
        agent = self.registry.get_best_agent(step.agent_type)
        
        if not agent:
            raise RuntimeError(f"No available agent of type: {step.agent_type}")
        
        # Prepare task input from context
        task_input = {}
        for input_key, context_key in step.input_mapping.items():
            if context_key in execution.context:
                task_input[input_key] = execution.context[context_key]
        
        # Include full context if not specified
        if not step.input_mapping:
            task_input = execution.context.copy()
        
        # Create and execute task
        task = AgentTask.create(
            task_type=step.task_type,
            input_data=task_input,
            assigned_agent=agent.agent_id,
        )
        
        # Execute the task
        result = await agent.execute_task(task)
        
        return result
    
    async def _execute_human_review_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a human review step (pauses for approval)."""
        execution.status = WorkflowStatus.WAITING_APPROVAL
        execution.metadata["pending_review"] = {
            "step_id": step.step_id,
            "review_type": step.metadata.get("review_type"),
            "requested_at": datetime.utcnow().isoformat(),
        }
        
        # Will be resumed via approve_step or reject_step
        return {"status": "waiting_approval"}
    
    async def _execute_parallel_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Execute multiple steps in parallel."""
        tasks = []
        for sub_step in step.sub_steps:
            task = asyncio.create_task(self._execute_step(execution, sub_step))
            tasks.append((sub_step.step_id, task))
        
        results = {}
        for step_id, task in tasks:
            try:
                result = await task
                results[step_id] = result
            except Exception as e:
                results[step_id] = {"error": str(e)}
        
        return results
    
    async def _execute_conditional_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a conditional step."""
        if step.condition and step.condition(execution.context):
            # Execute sub-steps if condition is true
            results = {}
            for sub_step in step.sub_steps:
                result = await self._execute_step(execution, sub_step)
                results[sub_step.step_id] = result
            return results
        else:
            return {"skipped": True, "reason": "condition_not_met"}
    
    async def approve_step(
        self, 
        execution_id: str, 
        feedback: Optional[str] = None,
        context_updates: Optional[Dict[str, Any]] = None
    ):
        """
        Approve a pending human review step.
        
        Args:
            execution_id: ID of the workflow execution
            feedback: Optional feedback to include
            context_updates: Optional updates to workflow context
        """
        execution = self._pending_approvals.get(execution_id)
        if not execution:
            raise ValueError(f"No pending approval for execution: {execution_id}")
        
        workflow = self._workflows.get(execution.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {execution.workflow_id}")
        
        # Apply context updates
        if context_updates:
            execution.context.update(context_updates)
        
        # Store approval info
        execution.step_results[f"approval_{execution.current_step_index}"] = {
            "approved": True,
            "feedback": feedback,
            "approved_at": datetime.utcnow().isoformat(),
        }
        
        # Remove from pending
        del self._pending_approvals[execution_id]
        
        # Move to next step
        execution.current_step_index += 1
        execution.status = WorkflowStatus.RUNNING
        
        logger.info(f"Step approved for execution: {execution_id}")
        
        # Continue workflow
        await self._run_workflow(execution, workflow)
    
    async def reject_step(
        self, 
        execution_id: str, 
        feedback: str,
        context_updates: Optional[Dict[str, Any]] = None
    ):
        """
        Reject a pending human review step.
        
        Args:
            execution_id: ID of the workflow execution
            feedback: Feedback/reason for rejection
            context_updates: Optional updates to workflow context
        """
        execution = self._pending_approvals.get(execution_id)
        if not execution:
            raise ValueError(f"No pending approval for execution: {execution_id}")
        
        workflow = self._workflows.get(execution.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {execution.workflow_id}")
        
        # Apply context updates
        if context_updates:
            execution.context.update(context_updates)
        
        # Store rejection info
        current_step = workflow.steps[execution.current_step_index]
        execution.context[f"{current_step.name}_feedback"] = feedback
        execution.context[f"{current_step.name}_review_status"] = "rejected"
        
        execution.step_results[f"approval_{execution.current_step_index}"] = {
            "approved": False,
            "feedback": feedback,
            "rejected_at": datetime.utcnow().isoformat(),
        }
        
        # Remove from pending
        del self._pending_approvals[execution_id]
        
        # Go back to previous step (regenerate)
        # Find the generating step for this review
        if execution.current_step_index > 0:
            execution.current_step_index -= 1
        
        execution.status = WorkflowStatus.RUNNING
        
        logger.info(f"Step rejected for execution: {execution_id}, going back to regenerate")
        
        # Continue workflow (will regenerate)
        await self._run_workflow(execution, workflow)
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get a workflow execution by ID."""
        return self._executions.get(execution_id)
    
    def get_pending_approvals(self) -> List[WorkflowExecution]:
        """Get all executions waiting for approval."""
        return list(self._pending_approvals.values())
    
    def on_event(self, event_name: str, handler: Callable):
        """Register an event handler."""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
    
    async def _emit_event(self, event_name: str, data: Any):
        """Emit an event to all registered handlers."""
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get workflow engine status."""
        return {
            "registered_workflows": len(self._workflows),
            "active_executions": len([e for e in self._executions.values() 
                                     if e.status == WorkflowStatus.RUNNING]),
            "pending_approvals": len(self._pending_approvals),
            "completed_executions": len([e for e in self._executions.values() 
                                        if e.status == WorkflowStatus.COMPLETED]),
            "failed_executions": len([e for e in self._executions.values() 
                                     if e.status == WorkflowStatus.FAILED]),
        }


# SDLC Workflow Builder
class SDLCWorkflowBuilder:
    """
    Builder for creating standard SDLC workflows.
    """
    
    @staticmethod
    def build_standard_sdlc_workflow() -> Workflow:
        """Build the standard SDLC workflow."""
        steps = [
            # Step 1: Generate User Stories
            WorkflowStep.create_agent_step(
                name="generate_user_stories",
                agent_type="business_analyst",
                task_type="generate_user_stories",
                input_mapping={"project_name": "project_name", "requirements": "requirements"},
                output_mapping={"user_stories": "user_stories"},
            ),
            
            # Step 2: Review User Stories
            WorkflowStep.create_human_review_step(
                name="review_user_stories",
                review_type="user_stories",
            ),
            
            # Step 3: Create Design Documents
            WorkflowStep.create_agent_step(
                name="create_design_documents",
                agent_type="architect",
                task_type="create_design_documents",
                input_mapping={
                    "project_name": "project_name",
                    "requirements": "requirements",
                    "user_stories": "user_stories",
                },
                output_mapping={"design_documents": "design_documents"},
            ),
            
            # Step 4: Review Design Documents
            WorkflowStep.create_human_review_step(
                name="review_design_documents",
                review_type="design_documents",
            ),
            
            # Step 5: Generate Code
            WorkflowStep.create_agent_step(
                name="generate_code",
                agent_type="developer",
                task_type="generate_code",
                input_mapping={
                    "project_name": "project_name",
                    "requirements": "requirements",
                    "user_stories": "user_stories",
                    "design_documents": "design_documents",
                },
                output_mapping={"code_generated": "code_generated"},
            ),
            
            # Step 6: Code Review
            WorkflowStep.create_human_review_step(
                name="code_review",
                review_type="code",
            ),
            
            # Step 7: Security Review (parallel with code review agent)
            WorkflowStep.create_agent_step(
                name="security_review",
                agent_type="security",
                task_type="security_review",
                input_mapping={"code_generated": "code_generated"},
                output_mapping={"security_recommendations": "security_recommendations"},
            ),
            
            # Step 8: Human Security Review
            WorkflowStep.create_human_review_step(
                name="human_security_review",
                review_type="security",
            ),
            
            # Step 9: Write Test Cases
            WorkflowStep.create_agent_step(
                name="write_test_cases",
                agent_type="qa",
                task_type="write_test_cases",
                input_mapping={
                    "code_generated": "code_generated",
                    "user_stories": "user_stories",
                },
                output_mapping={"test_cases": "test_cases"},
            ),
            
            # Step 10: Review Test Cases
            WorkflowStep.create_human_review_step(
                name="review_test_cases",
                review_type="test_cases",
            ),
            
            # Step 11: QA Testing
            WorkflowStep.create_agent_step(
                name="qa_testing",
                agent_type="qa",
                task_type="qa_testing",
                input_mapping={
                    "code_generated": "code_generated",
                    "test_cases": "test_cases",
                },
                output_mapping={"qa_testing_comments": "qa_testing_comments"},
            ),
            
            # Step 12: QA Review
            WorkflowStep.create_human_review_step(
                name="qa_review",
                review_type="qa_testing",
            ),
            
            # Step 13: Deployment
            WorkflowStep.create_agent_step(
                name="deployment",
                agent_type="devops",
                task_type="deployment",
                input_mapping={"code_generated": "code_generated"},
                output_mapping={
                    "deployment_status": "deployment_status",
                    "deployment_feedback": "deployment_feedback",
                },
            ),
        ]
        
        return Workflow.create(
            name="Standard SDLC Workflow",
            description="Complete software development lifecycle from requirements to deployment",
            steps=steps,
        )
