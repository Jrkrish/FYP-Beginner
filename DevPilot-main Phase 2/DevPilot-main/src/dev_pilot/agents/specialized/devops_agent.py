"""
DevOps Agent Module

Handles deployment configuration and CI/CD.
"""

from typing import Any, Dict, Optional
import uuid
from loguru import logger

from src.dev_pilot.agents.base_agent import BaseAgent, AgentConfig, AgentCapability
from src.dev_pilot.agents.agent_message import AgentTask
from src.dev_pilot.agents.agent_registry import register_agent_type


@register_agent_type("devops")
class DevOpsAgent(BaseAgent):
    """
    DevOps Agent responsible for deployment and operations.
    
    Capabilities:
    - Create deployment configurations
    - Generate CI/CD pipelines
    - Define infrastructure as code
    - Plan deployment strategies
    """
    
    def __init__(self, llm: Any, message_bus: Optional[Any] = None, context_manager: Optional[Any] = None):
        config = AgentConfig(
            agent_id=f"devops-{uuid.uuid4().hex[:8]}",
            agent_type="devops",
            name="DevOps Agent",
            description="Handles deployment and CI/CD configuration",
            capabilities=[
                AgentCapability(name="deployment", description="Create deployment configuration"),
                AgentCapability(name="cicd_pipeline", description="Generate CI/CD pipeline"),
            ],
        )
        super().__init__(config=config, llm=llm, message_bus=message_bus, context_manager=context_manager)
        logger.info("DevOpsAgent initialized")
    
    def get_system_prompt(self) -> str:
        return """You are a DevOps Expert Agent specializing in deployment and infrastructure.

Your expertise includes:
1. CI/CD pipeline design (GitHub Actions, GitLab CI, Jenkins)
2. Containerization (Docker, Kubernetes)
3. Infrastructure as Code (Terraform, CloudFormation)
4. Cloud platforms (AWS, GCP, Azure)
5. Deployment strategies (Blue-Green, Canary, Rolling)
6. Monitoring and observability

When creating deployment configurations:
- Use industry best practices
- Consider scalability and reliability
- Include proper environment configurations
- Add health checks and monitoring
- Document deployment procedures

Generate production-ready configurations with proper comments."""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "deployment":
            return await self._create_deployment(input_data.get("code_generated", ""))
        elif task_type == "cicd_pipeline":
            return await self._create_cicd_pipeline(input_data.get("code_generated", ""))
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _create_deployment(self, code: str) -> Dict[str, Any]:
        prompt = f"""Create deployment configuration for the following code:

```
{code}
```

Generate:
1. **Dockerfile**: Multi-stage build, optimized image
2. **docker-compose.yml**: Local development setup
3. **Kubernetes manifests**: Deployment, Service, ConfigMap
4. **Deployment checklist**: Pre-deployment verification

Also provide:
- Deployment Status: [Success/Failed]
- Deployment Steps
- Environment Variables needed
- Health check endpoints
- Rollback procedure"""
        
        deployment = await self.think(prompt)
        status = "success" if "SUCCESS" in deployment.upper() else "failed"
        return {
            "deployment_feedback": deployment,
            "deployment_status": status,
        }
    
    async def _create_cicd_pipeline(self, code: str) -> Dict[str, Any]:
        prompt = f"""Create a CI/CD pipeline configuration for the following code:

```
{code}
```

Generate GitHub Actions workflow that includes:
1. **Build Stage**: Install dependencies, run linters
2. **Test Stage**: Run unit and integration tests
3. **Security Scan**: Basic security scanning
4. **Build Docker Image**: Create and tag container
5. **Deploy Stage**: Deploy to staging/production

Include proper:
- Trigger conditions
- Environment secrets handling
- Caching for faster builds
- Notification on failures"""
        
        pipeline = await self.think(prompt)
        return {"cicd_pipeline": pipeline}
