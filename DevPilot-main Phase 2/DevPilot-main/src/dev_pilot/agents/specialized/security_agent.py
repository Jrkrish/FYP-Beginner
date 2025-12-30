"""
Security Agent Module

Handles security analysis and vulnerability detection.
"""

from typing import Any, Dict, Optional
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentConfig, AgentCapability
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


@register_agent_type("security")
class SecurityAgent(BaseAgent):
    """
    Security Agent responsible for security analysis and recommendations.
    
    Capabilities:
    - Perform SAST analysis
    - Identify OWASP Top 10 vulnerabilities
    - Recommend security fixes
    - Review authentication/authorization
    """
    
    def __init__(self, llm: Any, message_bus: Optional[Any] = None, context_manager: Optional[Any] = None):
        config = AgentConfig(
            agent_id=f"security-{uuid.uuid4().hex[:8]}",
            agent_type="security",
            name="Security Agent",
            description="Analyzes code for security vulnerabilities",
            capabilities=[
                AgentCapability(name="security_review", description="Comprehensive security analysis"),
                AgentCapability(name="owasp_check", description="Check for OWASP Top 10 vulnerabilities"),
            ],
        )
        super().__init__(config=config, llm=llm, message_bus=message_bus, context_manager=context_manager)
        logger.info("SecurityAgent initialized")
    
    def get_system_prompt(self) -> str:
        return """You are a Security Expert Agent specializing in application security.

Your expertise includes:
1. OWASP Top 10 vulnerabilities (Injection, XSS, CSRF, etc.)
2. Authentication and authorization flaws
3. Secure coding practices
4. Data protection and encryption
5. Input validation and sanitization
6. Secure API design

When reviewing code:
- Identify specific security vulnerabilities with code locations
- Explain the potential impact and attack vectors
- Provide concrete remediation steps with code examples
- Prioritize findings by severity (Critical, High, Medium, Low)

Be thorough but practical in your recommendations."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "security_review":
            return await self._security_review(input_data.get("code_generated", ""))
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _security_review(self, code: str) -> Dict[str, Any]:
        prompt = f"""Perform a comprehensive security review of the following code:

```
{code}
```

Analyze for:
1. **Injection Vulnerabilities**: SQL, Command, LDAP injection
2. **Cross-Site Scripting (XSS)**: Reflected, Stored, DOM-based
3. **Authentication Issues**: Weak passwords, session management
4. **Authorization Flaws**: Privilege escalation, IDOR
5. **Data Exposure**: Sensitive data handling, encryption
6. **Input Validation**: Missing or inadequate validation
7. **Error Handling**: Information leakage through errors
8. **Dependency Issues**: Known vulnerable components

For each finding, provide:
- Severity (Critical/High/Medium/Low)
- Location in code
- Description of vulnerability
- Remediation recommendation

End with overall status: APPROVED or NEEDS_FEEDBACK"""
        
        review = await self.think(prompt)
        status = "approved" if "APPROVED" in review.upper() else "needs_feedback"
        return {"security_recommendations": review, "status": status}
