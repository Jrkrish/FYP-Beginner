"""
Supervisor Agent Module

The Supervisor Agent orchestrates the SDLC workflow by coordinating specialized agents.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
from loguru import logger
from pydantic import BaseModel, Field

from src.dev_pilot.agents.base_agent import (
    BaseAgent, 
    AgentConfig, 
    AgentState, 
    AgentCapability
)
from src.dev_pilot.agents.agent_message import (
    AgentMessage, 
    AgentTask, 
    MessageType, 
    MessagePriority
)
from src.dev_pilot.agents.agent_registry import register_agent_type, get_registry


class ExecutionPlan(BaseModel):
    """Structured output for execution plan."""
    phases: List[Dict[str, Any]] = Field(
        description="List of phases in the execution plan"
    )
    estimated_duration: str = Field(
        description="Estimated total duration"
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Potential risk factors identified"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for the project"
    )


class TaskAssignment(BaseModel):
    """Structured output for task assignment."""
    agent_type: str = Field(description="Type of agent to assign")
    task_type: str = Field(description="Type of task to execute")
    priority: int = Field(default=3, description="Task priority (1-5)")
    input_requirements: List[str] = Field(
        default_factory=list,
        description="Required inputs for the task"
    )
    expected_outputs: List[str] = Field(
        default_factory=list,
        description="Expected outputs from the task"
    )


@register_agent_type("supervisor")
class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent that orchestrates the entire SDLC workflow.
    
    Responsibilities:
    - Analyze project requirements
    - Create execution plans
    - Delegate tasks to specialized agents
    - Monitor progress
    - Handle conflicts and errors
    - Adapt workflow based on context
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        config = AgentConfig(
            agent_id=f"supervisor-{uuid.uuid4().hex[:8]}",
            agent_type="supervisor",
            name="Supervisor Agent",
            description="Orchestrates the SDLC workflow and coordinates specialized agents",
            capabilities=[
                AgentCapability(
                    name="analyze_project",
                    description="Analyze project requirements and create execution plan"
                ),
                AgentCapability(
                    name="delegate_task",
                    description="Delegate tasks to appropriate specialized agents"
                ),
                AgentCapability(
                    name="monitor_progress",
                    description="Monitor and track workflow progress"
                ),
                AgentCapability(
                    name="resolve_conflicts",
                    description="Handle conflicts and make decisions"
                ),
            ],
        )
        
        super().__init__(
            config=config,
            llm=llm,
            message_bus=message_bus,
            context_manager=context_manager,
        )
        
        # Workflow state
        self._current_workflow: Optional[Dict[str, Any]] = None
        self._execution_plan: Optional[ExecutionPlan] = None
        self._active_tasks: Dict[str, AgentTask] = {}
        self._completed_phases: List[str] = []
        
        # Register tools
        self._register_supervisor_tools()
        
        logger.info("SupervisorAgent initialized")
    
    def _register_supervisor_tools(self):
        """Register supervisor-specific tools."""
        self.register_tool(
            "analyze_project",
            self._analyze_project,
            "Analyze project requirements and create execution plan"
        )
        self.register_tool(
            "delegate_task",
            self._delegate_task,
            "Delegate a task to a specialized agent"
        )
        self.register_tool(
            "check_progress",
            self._check_progress,
            "Check the progress of current workflow"
        )
    
    def get_system_prompt(self) -> str:
        """Get the supervisor agent's system prompt."""
        return """You are the Supervisor Agent for DevPilot, an AI-powered SDLC automation platform.

Your role is to orchestrate the entire software development lifecycle by:
1. Analyzing project requirements and understanding the scope
2. Creating comprehensive execution plans
3. Delegating tasks to specialized agents (BA, Architect, Developer, Security, QA, DevOps)
4. Monitoring progress and ensuring quality
5. Handling conflicts and making strategic decisions
6. Adapting the workflow based on feedback and context

You have access to the following specialized agents:
- Business Analyst Agent: Requirements analysis, user story generation
- Architect Agent: System design, technical documentation
- Developer Agent: Code generation, implementation
- Code Review Agent: Code quality review
- Security Agent: Security analysis and recommendations
- QA Agent: Test case generation, quality assurance
- DevOps Agent: Deployment configuration, CI/CD

When creating execution plans, consider:
- Dependencies between tasks
- Parallel execution opportunities
- Risk factors and mitigation strategies
- Human review checkpoints

Always maintain clear communication and provide detailed reasoning for your decisions."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a task assigned to the supervisor."""
        task_type = task.task_type
        input_data = task.input_data
        
        logger.info(f"Supervisor processing task: {task_type}")
        
        if task_type == "analyze_project":
            return await self._analyze_project(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
            )
        elif task_type == "create_execution_plan":
            return await self._create_execution_plan(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
            )
        elif task_type == "delegate_to_agent":
            return await self._delegate_task(
                agent_type=input_data.get("agent_type"),
                task_type=input_data.get("task_type"),
                task_input=input_data.get("task_input", {}),
            )
        elif task_type == "handle_feedback":
            return await self._handle_feedback(
                phase=input_data.get("phase"),
                feedback=input_data.get("feedback"),
                status=input_data.get("status"),
            )
        elif task_type == "orchestrate_workflow":
            return await self._orchestrate_workflow(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _analyze_project(
        self, 
        project_name: str, 
        requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze project requirements and provide insights.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            
        Returns:
            Analysis results
        """
        prompt = f"""Analyze the following project and provide insights:

Project Name: {project_name}

Requirements:
{chr(10).join(f"- {req}" for req in requirements)}

Provide a comprehensive analysis including:
1. Project Complexity Assessment (Low/Medium/High)
2. Key Technical Challenges
3. Recommended Technology Stack
4. Estimated Development Phases
5. Risk Factors
6. Critical Success Factors

Be specific and actionable in your recommendations."""
        
        analysis = await self.think(prompt)
        
        return {
            "project_name": project_name,
            "analysis": analysis,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    async def _create_execution_plan(
        self,
        project_name: str,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """
        Create a detailed execution plan for the project.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            
        Returns:
            Execution plan
        """
        prompt = f"""Create a detailed execution plan for the following project:

Project Name: {project_name}

Requirements:
{chr(10).join(f"- {req}" for req in requirements)}

Create an execution plan with the following phases:
1. Requirements Analysis & User Stories
2. System Design & Architecture
3. Code Generation
4. Code Review
5. Security Review
6. Test Case Generation
7. QA Testing
8. Deployment

For each phase, specify:
- Agent responsible
- Input requirements
- Expected outputs
- Estimated duration
- Dependencies on other phases
- Human review points"""
        
        try:
            plan = await self.think_structured(prompt, ExecutionPlan)
            self._execution_plan = plan
            return plan.model_dump()
        except Exception as e:
            # Fallback to non-structured response
            logger.warning(f"Structured output failed, using fallback: {e}")
            plan_text = await self.think(prompt)
            return {
                "plan_text": plan_text,
                "phases": self._get_default_phases(),
            }
    
    def _get_default_phases(self) -> List[Dict[str, Any]]:
        """Get default SDLC phases."""
        return [
            {
                "name": "requirements_analysis",
                "agent": "business_analyst",
                "description": "Generate user stories from requirements",
                "human_review": True,
            },
            {
                "name": "system_design",
                "agent": "architect",
                "description": "Create system design documents",
                "human_review": True,
            },
            {
                "name": "code_generation",
                "agent": "developer",
                "description": "Generate code based on design",
                "human_review": True,
            },
            {
                "name": "security_review",
                "agent": "security",
                "description": "Review code for security issues",
                "human_review": True,
            },
            {
                "name": "test_generation",
                "agent": "qa",
                "description": "Generate test cases",
                "human_review": True,
            },
            {
                "name": "qa_testing",
                "agent": "qa",
                "description": "Perform QA testing",
                "human_review": True,
            },
            {
                "name": "deployment",
                "agent": "devops",
                "description": "Deploy the application",
                "human_review": False,
            },
        ]
    
    async def _delegate_task(
        self,
        agent_type: str,
        task_type: str,
        task_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Delegate a task to a specialized agent.
        
        Args:
            agent_type: Type of agent to delegate to
            task_type: Type of task to execute
            task_input: Input data for the task
            
        Returns:
            Delegation result
        """
        registry = get_registry()
        
        # Find available agent
        agent = registry.get_best_agent(agent_type)
        
        if not agent:
            return {
                "success": False,
                "error": f"No available agent of type: {agent_type}",
            }
        
        # Create task
        task = AgentTask.create(
            task_type=task_type,
            input_data=task_input,
            assigned_agent=agent.agent_id,
        )
        
        self._active_tasks[task.task_id] = task
        
        logger.info(f"Delegating task {task_type} to {agent.name}")
        
        # Send request to agent via message bus
        if self.message_bus:
            message = AgentMessage.create_request(
                sender=self.agent_id,
                recipient=agent.agent_id,
                action=task_type,
                data=task_input,
                priority=MessagePriority.NORMAL,
            )
            await self.send_message(message)
        
        # For synchronous execution, directly execute
        try:
            result = await agent.execute_task(task)
            self._active_tasks.pop(task.task_id, None)
            
            return {
                "success": True,
                "task_id": task.task_id,
                "agent_id": agent.agent_id,
                "result": result,
            }
        except Exception as e:
            self._active_tasks.pop(task.task_id, None)
            return {
                "success": False,
                "task_id": task.task_id,
                "error": str(e),
            }
    
    async def _handle_feedback(
        self,
        phase: str,
        feedback: str,
        status: str,  # "approved" or "rejected"
    ) -> Dict[str, Any]:
        """
        Handle human feedback for a phase.
        
        Args:
            phase: The phase being reviewed
            feedback: Feedback text
            status: Approval status
            
        Returns:
            Next action to take
        """
        prompt = f"""Human feedback received for phase: {phase}
Status: {status}
Feedback: {feedback}

Based on this feedback, determine:
1. What specific changes need to be made?
2. Which agent should handle the revisions?
3. What additional context should be provided?

Provide actionable next steps."""
        
        analysis = await self.think(prompt)
        
        if status == "approved":
            self._completed_phases.append(phase)
            return {
                "action": "proceed_to_next_phase",
                "completed_phase": phase,
                "analysis": analysis,
            }
        else:
            return {
                "action": "revise_current_phase",
                "phase": phase,
                "feedback": feedback,
                "analysis": analysis,
            }
    
    async def _orchestrate_workflow(
        self,
        project_name: str,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """
        Orchestrate the complete SDLC workflow.
        
        This is the main entry point for running a complete workflow.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            
        Returns:
            Workflow initialization result
        """
        # Initialize workflow state
        self._current_workflow = {
            "project_name": project_name,
            "requirements": requirements,
            "started_at": datetime.utcnow().isoformat(),
            "current_phase": "initialization",
            "context": {
                "project_name": project_name,
                "requirements": requirements,
            },
        }
        
        # Analyze project
        analysis = await self._analyze_project(project_name, requirements)
        self._current_workflow["analysis"] = analysis
        
        # Create execution plan
        plan = await self._create_execution_plan(project_name, requirements)
        self._current_workflow["execution_plan"] = plan
        
        # Broadcast workflow started
        if self.message_bus:
            await self.send_message(AgentMessage.create_broadcast(
                sender=self.agent_id,
                event="workflow_started",
                data={
                    "project_name": project_name,
                    "execution_plan": plan,
                },
            ))
        
        return {
            "status": "initialized",
            "workflow_id": str(uuid.uuid4()),
            "project_name": project_name,
            "analysis": analysis,
            "execution_plan": plan,
        }
    
    async def _check_progress(self) -> Dict[str, Any]:
        """Check the progress of the current workflow."""
        if not self._current_workflow:
            return {"status": "no_active_workflow"}
        
        return {
            "workflow": self._current_workflow,
            "completed_phases": self._completed_phases,
            "active_tasks": len(self._active_tasks),
            "execution_plan": self._execution_plan.model_dump() if self._execution_plan else None,
        }
    
    async def decide_next_action(
        self,
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Decide the next action based on current state.
        
        Uses LLM reasoning to make strategic decisions.
        
        Args:
            current_state: Current workflow state
            
        Returns:
            Decision with next action
        """
        prompt = f"""Given the current SDLC workflow state, decide the next action:

Current State:
- Project: {current_state.get('project_name', 'Unknown')}
- Current Phase: {current_state.get('current_phase', 'Unknown')}
- Completed Phases: {current_state.get('completed_phases', [])}
- Active Tasks: {current_state.get('active_tasks', 0)}
- Last Result: {current_state.get('last_result', 'None')}

Available Actions:
1. delegate_to_ba - Send to Business Analyst for user stories
2. delegate_to_architect - Send to Architect for design
3. delegate_to_developer - Send to Developer for code generation
4. delegate_to_security - Send to Security for review
5. delegate_to_qa - Send to QA for testing
6. delegate_to_devops - Send to DevOps for deployment
7. request_human_review - Request human approval
8. complete_workflow - Mark workflow as complete

What should be the next action and why?"""
        
        decision = await self.think(prompt)
        
        return {
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # Message handlers
    async def _handle_response(self, message: AgentMessage):
        """Handle response from delegated agents."""
        result = message.payload.get("result")
        task_id = message.metadata.get("task_id")
        
        logger.info(f"Received response for task: {task_id}")
        
        # Update workflow state
        if self._current_workflow:
            self._current_workflow["last_result"] = result
        
        # Remove from active tasks
        if task_id in self._active_tasks:
            task = self._active_tasks.pop(task_id)
            task.mark_completed(result)
    
    async def _handle_error(self, message: AgentMessage):
        """Handle error from delegated agents."""
        error = message.payload.get("error")
        task_id = message.metadata.get("task_id")
        
        logger.error(f"Task {task_id} failed: {error}")
        
        # Decide how to handle the error
        if self._current_workflow:
            await self._handle_task_failure(task_id, error)
    
    async def _handle_task_failure(self, task_id: str, error: str):
        """Handle a failed task."""
        task = self._active_tasks.get(task_id)
        if not task:
            return
        
        # Decide retry strategy
        prompt = f"""A task has failed:
Task Type: {task.task_type}
Error: {error}

Should we:
1. Retry the task with the same agent
2. Retry with a different agent
3. Skip this task and proceed
4. Abort the workflow

What is the best course of action?"""
        
        decision = await self.think(prompt)
        
        logger.info(f"Error handling decision: {decision}")
        
        # For now, mark as failed
        task.mark_failed(error)
        self._active_tasks.pop(task_id, None)
