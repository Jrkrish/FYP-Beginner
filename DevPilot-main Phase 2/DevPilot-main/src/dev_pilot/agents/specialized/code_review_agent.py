"""
Code Review Agent Module

Handles code quality review and best practices validation.
"""

from typing import Any, Dict, List, Optional
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentConfig, AgentCapability
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


@register_agent_type("code_review")
class CodeReviewAgent(BaseAgent):
    """
    Code Review Agent responsible for code quality assurance.
    
    Capabilities:
    - Review code for best practices
    - Identify bugs and anti-patterns
    - Suggest improvements
    - Ensure coding standards compliance
    """
    
    def __init__(self, llm: Any, message_bus: Optional[Any] = None, context_manager: Optional[Any] = None):
        config = AgentConfig(
            agent_id=f"code-review-{uuid.uuid4().hex[:8]}",
            agent_type="code_review",
            name="Code Review Agent",
            description="Reviews code for quality and best practices",
            capabilities=[
                AgentCapability(name="review_code", description="Comprehensive code review"),
                AgentCapability(name="check_standards", description="Check coding standards compliance"),
            ],
        )
        super().__init__(config=config, llm=llm, message_bus=message_bus, context_manager=context_manager)
        logger.info("CodeReviewAgent initialized")
    
    def get_system_prompt(self) -> str:
        return """You are a Senior Code Review Agent with expertise in code quality and best practices.

Your responsibilities:
1. Review code for bugs, anti-patterns, and potential issues
2. Check adherence to coding standards and style guides
3. Evaluate code readability and maintainability
4. Identify performance bottlenecks
5. Suggest concrete improvements
6. Verify proper error handling

Always provide specific, actionable feedback with code examples when suggesting changes."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "review_code":
            return await self._review_code(input_data.get("code", ""))
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _review_code(self, code: str) -> Dict[str, Any]:
        prompt = f"""Review the following code comprehensively:

```
{code}
```

Provide detailed feedback on:
1. **Code Quality**: Best practices, clean code principles
2. **Bugs**: Potential bugs or edge cases not handled
3. **Performance**: Any performance concerns
4. **Security**: Security vulnerabilities (brief, detailed in security review)
5. **Maintainability**: Code structure and organization
6. **Recommendations**: Specific improvements with examples

End with an overall verdict: APPROVED or NEEDS_FEEDBACK"""
        
        review = await self.think(prompt)
        status = "approved" if "APPROVED" in review.upper() else "needs_feedback"
        return {"review_comments": review, "status": status}
