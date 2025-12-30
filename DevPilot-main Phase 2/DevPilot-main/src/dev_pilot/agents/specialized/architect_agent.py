"""
Architect Agent Module

Handles system design and technical architecture.
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


class DesignDocument(BaseModel):
    """Structured design document model."""
    functional: str = Field(description="Functional design document content")
    technical: str = Field(description="Technical design document content")


@register_agent_type("architect")
class ArchitectAgent(BaseAgent):
    """
    Architect Agent responsible for system design and technical architecture.
    
    Capabilities:
    - Create system architecture designs
    - Define technology stack
    - Design database schemas
    - Specify API contracts
    - Create functional and technical design documents
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        config = AgentConfig(
            agent_id=f"architect-{uuid.uuid4().hex[:8]}",
            agent_type="architect",
            name="Architect Agent",
            description="Creates system architecture and design documents",
            capabilities=[
                AgentCapability(
                    name="create_design_documents",
                    description="Create functional and technical design documents"
                ),
                AgentCapability(
                    name="design_architecture",
                    description="Design system architecture"
                ),
                AgentCapability(
                    name="define_tech_stack",
                    description="Define and justify technology stack"
                ),
                AgentCapability(
                    name="design_database",
                    description="Design database schema"
                ),
            ],
        )
        
        super().__init__(
            config=config,
            llm=llm,
            message_bus=message_bus,
            context_manager=context_manager,
        )
        
        logger.info("ArchitectAgent initialized")
    
    def get_system_prompt(self) -> str:
        """Get the Architect agent's system prompt."""
        return """You are a Senior Software Architect Agent with expertise in system design and architecture.

Your expertise includes:
1. Designing scalable, maintainable system architectures
2. Selecting appropriate technology stacks based on requirements
3. Creating comprehensive functional and technical design documents
4. Designing database schemas and data models
5. Specifying API contracts and integration points
6. Considering security, performance, and scalability
7. Following industry best practices and design patterns

When creating design documents:
- Use proper Markdown formatting with headers and sections
- Include diagrams described in text form
- Provide clear justifications for design decisions
- Consider both functional and non-functional requirements
- Address scalability, security, and maintainability

Always be thorough, detailed, and consider edge cases in your designs."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process an architecture task."""
        task_type = task.task_type
        input_data = task.input_data
        
        logger.info(f"Architect Agent processing task: {task_type}")
        
        if task_type == "create_design_documents":
            return await self._create_design_documents(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
                user_stories=input_data.get("user_stories"),
                feedback=input_data.get("feedback"),
            )
        elif task_type == "design_architecture":
            return await self._design_architecture(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
            )
        elif task_type == "design_database":
            return await self._design_database(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
                user_stories=input_data.get("user_stories"),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _create_design_documents(
        self,
        project_name: str,
        requirements: List[str],
        user_stories: Any,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create comprehensive design documents.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            user_stories: User stories from BA
            feedback: Optional feedback for refinement
            
        Returns:
            Design documents
        """
        # Generate functional design document
        functional_doc = await self._generate_functional_design(
            project_name, requirements, user_stories, feedback
        )
        
        # Generate technical design document
        technical_doc = await self._generate_technical_design(
            project_name, requirements, user_stories, feedback
        )
        
        design_documents = DesignDocument(
            functional=functional_doc,
            technical=technical_doc,
        )
        
        return {
            "design_documents": design_documents,
            "functional": functional_doc,
            "technical": technical_doc,
        }
    
    async def _generate_functional_design(
        self,
        project_name: str,
        requirements: List[str],
        user_stories: Any,
        feedback: Optional[str] = None,
    ) -> str:
        """Generate functional design document."""
        prompt = f"""Create a comprehensive functional design document for {project_name} in Markdown format.

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements)}

**User Stories:**
{user_stories}

{f"**Feedback to Address:** {feedback}" if feedback else ""}

**Document Structure:**
# Functional Design Document: {project_name}

## 1. Introduction and Purpose
## 2. Project Scope
## 3. User Roles and Permissions
## 4. Functional Requirements Breakdown
## 5. User Interface Design Guidelines
## 6. Business Process Flows
## 7. Data Entities and Relationships
## 8. Validation Rules
## 9. Reporting Requirements
## 10. Integration Points

Use proper Markdown formatting with headers, bullet points, and tables where appropriate."""
        
        return await self.think(prompt)
    
    async def _generate_technical_design(
        self,
        project_name: str,
        requirements: List[str],
        user_stories: Any,
        feedback: Optional[str] = None,
    ) -> str:
        """Generate technical design document."""
        prompt = f"""Create a comprehensive technical design document for {project_name} in Markdown format.

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements)}

**User Stories:**
{user_stories}

{f"**Feedback to Address:** {feedback}" if feedback else ""}

**Document Structure:**
# Technical Design Document: {project_name}

## 1. System Architecture
## 2. Technology Stack and Justification
## 3. Database Schema
## 4. API Specifications
## 5. Security Considerations
## 6. Performance Considerations
## 7. Scalability Approach
## 8. Deployment Strategy
## 9. Third-party Integrations
## 10. Development, Testing, and Deployment Environments

Use proper Markdown formatting. For code examples, use ```language syntax.
For database schemas, use Markdown tables."""
        
        return await self.think(prompt)
    
    async def _design_architecture(
        self,
        project_name: str,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """Design system architecture."""
        prompt = f"""Design a comprehensive system architecture for {project_name}:

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements)}

Provide:
1. High-level architecture diagram (described in text)
2. Component breakdown
3. Communication patterns
4. Data flow
5. Technology recommendations
6. Scalability considerations"""
        
        architecture = await self.think(prompt)
        return {"architecture": architecture}
    
    async def _design_database(
        self,
        project_name: str,
        requirements: List[str],
        user_stories: Any,
    ) -> Dict[str, Any]:
        """Design database schema."""
        prompt = f"""Design a database schema for {project_name}:

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements)}

**User Stories:**
{user_stories}

Provide:
1. Entity-Relationship Diagram (described in text)
2. Table definitions with columns and types
3. Primary and foreign keys
4. Indexes
5. Constraints
6. Sample SQL CREATE statements"""
        
        schema = await self.think(prompt)
        return {"database_schema": schema}
