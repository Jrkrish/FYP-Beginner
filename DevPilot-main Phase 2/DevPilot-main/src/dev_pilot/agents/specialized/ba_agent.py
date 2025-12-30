"""
Business Analyst Agent Module

Handles requirements analysis and user story generation.
"""

from typing import Any, Dict, List, Optional
import uuid
from loguru import logger
from pydantic import BaseModel, Field

from src.dev_pilot.agents.base_agent import (
    BaseAgent, 
    AgentConfig, 
    AgentCapability
)
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


class UserStory(BaseModel):
    """Structured user story model."""
    id: str = Field(description="Unique identifier (e.g., US-001)")
    title: str = Field(description="Short title of the user story")
    description: str = Field(description="Detailed description in 'As a... I want... So that...' format")
    priority: int = Field(description="Priority level (1=Critical, 2=High, 3=Medium, 4=Low)")
    acceptance_criteria: str = Field(description="Acceptance criteria as bullet points")


class UserStoryList(BaseModel):
    """List of user stories."""
    user_stories: List[UserStory] = Field(description="List of generated user stories")


@register_agent_type("business_analyst")
class BusinessAnalystAgent(BaseAgent):
    """
    Business Analyst Agent responsible for requirements analysis and user story generation.
    
    Capabilities:
    - Extract and analyze requirements
    - Generate detailed user stories
    - Create acceptance criteria
    - Prioritize features
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        config = AgentConfig(
            agent_id=f"ba-{uuid.uuid4().hex[:8]}",
            agent_type="business_analyst",
            name="Business Analyst Agent",
            description="Analyzes requirements and generates user stories",
            capabilities=[
                AgentCapability(
                    name="generate_user_stories",
                    description="Generate detailed user stories from requirements"
                ),
                AgentCapability(
                    name="analyze_requirements",
                    description="Analyze and clarify requirements"
                ),
                AgentCapability(
                    name="prioritize_features",
                    description="Prioritize features using MoSCoW method"
                ),
            ],
        )
        
        super().__init__(
            config=config,
            llm=llm,
            message_bus=message_bus,
            context_manager=context_manager,
        )
        
        logger.info("BusinessAnalystAgent initialized")
    
    def get_system_prompt(self) -> str:
        """Get the BA agent's system prompt."""
        return """You are a Senior Business Analyst Agent specializing in Agile SDLC and user story generation.

Your expertise includes:
1. Extracting clear requirements from vague descriptions
2. Writing detailed user stories in the standard format
3. Defining measurable acceptance criteria
4. Prioritizing features using MoSCoW or similar methods
5. Identifying edge cases and potential issues
6. Ensuring requirements are testable and achievable

When generating user stories:
- Use the format: "As a [user role], I want [goal] so that [benefit]"
- Assign unique identifiers (US-001, US-002, etc.)
- Set appropriate priority levels
- Write specific, testable acceptance criteria
- Consider both functional and non-functional requirements

Always be thorough, specific, and user-focused in your analysis."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a BA task."""
        task_type = task.task_type
        input_data = task.input_data
        
        logger.info(f"BA Agent processing task: {task_type}")
        
        if task_type == "generate_user_stories":
            return await self._generate_user_stories(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
                feedback=input_data.get("feedback"),
            )
        elif task_type == "analyze_requirements":
            return await self._analyze_requirements(
                requirements=input_data.get("requirements", []),
            )
        elif task_type == "refine_user_stories":
            return await self._refine_user_stories(
                user_stories=input_data.get("user_stories"),
                feedback=input_data.get("feedback"),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _generate_user_stories(
        self,
        project_name: str,
        requirements: List[str],
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate user stories from requirements.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            feedback: Optional feedback for refinement
            
        Returns:
            Generated user stories
        """
        prompt = f"""Generate detailed user stories for the following project:

**Project Name:** {project_name}

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements)}

{f"**Previous Feedback to Address:** {feedback}" if feedback else ""}

**Instructions:**
- Create one user story per distinct requirement
- Assign unique identifiers (US-001, US-002, etc.)
- Use the format: "As a [user role], I want [goal] so that [benefit]"
- Assign priority (1=Critical, 2=High, 3=Medium, 4=Low)
- Write clear, testable acceptance criteria

Generate comprehensive user stories that cover all requirements."""

        try:
            result = await self.think_structured(prompt, UserStoryList)
            return {
                "user_stories": result,
                "count": len(result.user_stories),
            }
        except Exception as e:
            logger.warning(f"Structured output failed: {e}")
            # Fallback to unstructured
            response = await self.think(prompt)
            return {
                "user_stories_text": response,
                "error": "Structured output failed, returned text format",
            }
    
    async def _analyze_requirements(
        self,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """Analyze requirements for clarity and completeness."""
        prompt = f"""Analyze the following requirements:

{chr(10).join(f"- {req}" for req in requirements)}

Provide:
1. Clarity Assessment: Are requirements clear and unambiguous?
2. Completeness Check: What's missing or needs clarification?
3. Potential Conflicts: Any conflicting requirements?
4. Recommendations: Suggestions for improvement
5. Questions: Questions to ask stakeholders"""
        
        analysis = await self.think(prompt)
        return {"analysis": analysis}
    
    async def _refine_user_stories(
        self,
        user_stories: Any,
        feedback: str,
    ) -> Dict[str, Any]:
        """Refine user stories based on feedback."""
        prompt = f"""Refine the following user stories based on feedback:

**Current User Stories:**
{user_stories}

**Feedback:**
{feedback}

Update the user stories addressing all feedback points. Maintain the same format."""
        
        try:
            result = await self.think_structured(prompt, UserStoryList)
            return {"user_stories": result}
        except Exception:
            response = await self.think(prompt)
            return {"user_stories_text": response}
