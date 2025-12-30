"""
Developer Agent Module

Handles code generation and implementation.
"""

from typing import Any, Dict, List, Optional
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import (
    BaseAgent, 
    AgentConfig, 
    AgentCapability
)
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


@register_agent_type("developer")
class DeveloperAgent(BaseAgent):
    """
    Developer Agent responsible for code generation and implementation.
    
    Capabilities:
    - Generate production-ready code
    - Follow design documents and specifications
    - Create modular, testable code
    - Implement design patterns
    - Handle multiple programming languages
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        config = AgentConfig(
            agent_id=f"developer-{uuid.uuid4().hex[:8]}",
            agent_type="developer",
            name="Developer Agent",
            description="Generates production-ready code based on designs",
            capabilities=[
                AgentCapability(
                    name="generate_code",
                    description="Generate complete code implementation"
                ),
                AgentCapability(
                    name="refactor_code",
                    description="Refactor and improve existing code"
                ),
                AgentCapability(
                    name="fix_code",
                    description="Fix bugs and implement feedback"
                ),
            ],
        )
        
        super().__init__(
            config=config,
            llm=llm,
            message_bus=message_bus,
            context_manager=context_manager,
        )
        
        logger.info("DeveloperAgent initialized")
    
    def get_system_prompt(self) -> str:
        """Get the Developer agent's system prompt."""
        return """You are a Senior Software Developer Agent with expertise in multiple programming languages and frameworks.

Your expertise includes:
1. Writing clean, maintainable, production-ready code
2. Following design documents and technical specifications
3. Implementing design patterns and best practices
4. Creating modular, testable code structures
5. Writing clear documentation and comments
6. Handling edge cases and error scenarios
7. Optimizing for performance and scalability

When generating code:
- Structure output as multiple files with clear names
- Use proper formatting and indentation
- Include necessary imports and dependencies
- Add meaningful comments and docstrings
- Follow the language's style guide
- Implement error handling
- Make code testable

Supported languages: Python, JavaScript, TypeScript, Java, Go, and more.

Always produce complete, working code that follows the technical design."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a development task."""
        task_type = task.task_type
        input_data = task.input_data
        
        logger.info(f"Developer Agent processing task: {task_type}")
        
        if task_type == "generate_code":
            return await self._generate_code(
                project_name=input_data.get("project_name"),
                requirements=input_data.get("requirements", []),
                user_stories=input_data.get("user_stories"),
                design_documents=input_data.get("design_documents"),
                code_feedback=input_data.get("code_feedback"),
                security_feedback=input_data.get("security_feedback"),
            )
        elif task_type == "fix_code":
            return await self._fix_code(
                code=input_data.get("code"),
                feedback=input_data.get("feedback"),
                security_recommendations=input_data.get("security_recommendations"),
            )
        elif task_type == "refactor_code":
            return await self._refactor_code(
                code=input_data.get("code"),
                improvements=input_data.get("improvements"),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _generate_code(
        self,
        project_name: str,
        requirements: List[str],
        user_stories: Any,
        design_documents: Any,
        code_feedback: Optional[str] = None,
        security_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete code implementation.
        
        Args:
            project_name: Name of the project
            requirements: List of requirements
            user_stories: User stories
            design_documents: Design documents from architect
            code_feedback: Optional feedback from code review
            security_feedback: Optional security recommendations
            
        Returns:
            Generated code
        """
        # Extract design doc content
        functional_doc = ""
        technical_doc = ""
        if design_documents:
            if hasattr(design_documents, 'functional'):
                functional_doc = design_documents.functional
                technical_doc = design_documents.technical
            elif isinstance(design_documents, dict):
                functional_doc = design_documents.get('functional', '')
                technical_doc = design_documents.get('technical', '')
        
        prompt = f"""Generate a complete Python project organized as multiple code files.

**Project Name:** {project_name}

**Requirements:**
{chr(10).join(f"- {req}" for req in requirements) if requirements else "See design documents"}

**User Stories:**
{user_stories}

**Functional Design:**
{functional_doc}

**Technical Design:**
{technical_doc}

{f"**Code Review Feedback to Address:** {code_feedback}" if code_feedback else ""}
{f"**Security Recommendations to Apply:** {security_feedback}" if security_feedback else ""}

**Instructions:**
- Structure the output as multiple code files (main.py, models.py, utils.py, etc.)
- Each file should be clearly separated with filename headers
- Include all necessary imports and dependencies
- Add comprehensive docstrings and comments
- Implement proper error handling
- Make code modular and testable
- Follow Python best practices (PEP 8)
- Ensure code is syntactically correct and ready to run

Generate only code files without explanations outside the code."""
        
        code_generated = await self.think(prompt)
        
        # Also generate code review comments
        review_comments = await self._get_self_review(code_generated)
        
        return {
            "code_generated": code_generated,
            "code_review_comments": review_comments,
        }
    
    async def _get_self_review(self, code: str) -> str:
        """Generate self-review comments for the code."""
        prompt = f"""Review the following code and provide feedback:

```
{code}
```

Focus on:
1. Code quality and best practices
2. Potential bugs or edge cases
3. Performance considerations
4. Security concerns

Provide constructive feedback with specific recommendations."""
        
        return await self.think(prompt)
    
    async def _fix_code(
        self,
        code: str,
        feedback: str,
        security_recommendations: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fix code based on feedback."""
        prompt = f"""Fix the following code based on the provided feedback:

**Current Code:**
```
{code}
```

**Feedback to Address:**
{feedback}

{f"**Security Recommendations:** {security_recommendations}" if security_recommendations else ""}

Generate the corrected code files. Address all feedback points and ensure the code is production-ready."""
        
        fixed_code = await self.think(prompt)
        return {"code_generated": fixed_code}
    
    async def _refactor_code(
        self,
        code: str,
        improvements: List[str],
    ) -> Dict[str, Any]:
        """Refactor code with improvements."""
        prompt = f"""Refactor the following code with the specified improvements:

**Current Code:**
```
{code}
```

**Improvements to Make:**
{chr(10).join(f"- {imp}" for imp in improvements)}

Generate the refactored code maintaining all functionality while applying improvements."""
        
        refactored = await self.think(prompt)
        return {"code_generated": refactored}
