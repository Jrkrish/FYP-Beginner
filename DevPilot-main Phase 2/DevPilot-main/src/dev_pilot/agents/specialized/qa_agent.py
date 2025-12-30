"""
QA Agent Module

Handles test case generation and quality assurance.
"""

from typing import Any, Dict, Optional
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentConfig, AgentCapability
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


@register_agent_type("qa")
class QAAgent(BaseAgent):
    """
    QA Agent responsible for testing and quality assurance.
    
    Capabilities:
    - Generate comprehensive test cases
    - Create unit, integration, and E2E tests
    - Simulate test execution
    - Report test coverage
    """
    
    def __init__(self, llm: Any, message_bus: Optional[Any] = None, context_manager: Optional[Any] = None):
        config = AgentConfig(
            agent_id=f"qa-{uuid.uuid4().hex[:8]}",
            agent_type="qa",
            name="QA Agent",
            description="Generates test cases and performs QA testing",
            capabilities=[
                AgentCapability(name="write_test_cases", description="Generate comprehensive test cases"),
                AgentCapability(name="qa_testing", description="Perform QA testing simulation"),
            ],
        )
        super().__init__(config=config, llm=llm, message_bus=message_bus, context_manager=context_manager)
        logger.info("QAAgent initialized")
    
    def get_system_prompt(self) -> str:
        return """You are a QA Testing Expert Agent specializing in comprehensive software testing.

Your expertise includes:
1. Writing unit tests, integration tests, and E2E tests
2. Test-driven development (TDD) principles
3. Edge case identification and boundary testing
4. Code coverage analysis
5. Test automation frameworks (pytest, unittest, jest)
6. Performance and load testing concepts

When generating test cases:
- Cover all happy paths and edge cases
- Include both positive and negative test scenarios
- Write clear test names describing the scenario
- Use proper assertions and mocking
- Group tests logically
- Aim for high code coverage

Use Python's unittest or pytest framework for test code."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "write_test_cases":
            return await self._write_test_cases(
                input_data.get("code_generated", ""),
                input_data.get("user_stories"),
            )
        elif task_type == "qa_testing":
            return await self._qa_testing(
                input_data.get("code_generated", ""),
                input_data.get("test_cases", ""),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _write_test_cases(self, code: str, user_stories: Any) -> Dict[str, Any]:
        prompt = f"""Generate comprehensive test cases for the following code:

**Code:**
```
{code}
```

**User Stories:**
{user_stories}

Generate:
1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **Edge Cases**: Boundary conditions and error scenarios
4. **Validation Tests**: Input validation tests

Use Python's unittest or pytest framework. Include:
- Clear test class and method names
- Setup and teardown where needed
- Appropriate assertions
- Mocking for external dependencies
- Comments explaining test purpose"""
        
        test_cases = await self.think(prompt)
        return {"test_cases": test_cases}
    
    async def _qa_testing(self, code: str, test_cases: str) -> Dict[str, Any]:
        prompt = f"""Simulate running the test cases and provide QA feedback:

**Code:**
```
{code}
```

**Test Cases:**
```
{test_cases}
```

Simulate test execution and provide:
1. Test Results (Pass/Fail for each test)
2. Coverage Analysis (estimated)
3. Failed Test Details (if any)
4. Bugs Found
5. Recommendations for code fixes
6. Overall QA Status

Format as:
- Test Case ID: [ID]
- Status: [Pass/Fail]
- Feedback: [Details if failed]

End with overall verdict: APPROVED or NEEDS_FEEDBACK"""
        
        qa_comments = await self.think(prompt)
        status = "approved" if "APPROVED" in qa_comments.upper() else "needs_feedback"
        return {"qa_testing_comments": qa_comments, "status": status}
