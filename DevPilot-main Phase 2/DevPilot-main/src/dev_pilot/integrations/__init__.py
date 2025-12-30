"""
DevPilot Integrations Module

Provides integrations with external services like Slack, Jira, GitHub, and custom webhooks.
"""

from src.dev_pilot.integrations.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationEvent,
    IntegrationResult,
    IntegrationStatus,
    EventType,
)
from src.dev_pilot.integrations.manager import (
    IntegrationManager,
    get_integration_manager,
)
from src.dev_pilot.integrations.slack_integration import SlackIntegration
from src.dev_pilot.integrations.jira_integration import JiraIntegration
from src.dev_pilot.integrations.github_integration import GitHubIntegration
from src.dev_pilot.integrations.webhook_integration import (
    WebhookIntegration,
    WebhookRegistry,
)


__all__ = [
    # Base classes
    "BaseIntegration",
    "IntegrationConfig",
    "IntegrationEvent",
    "IntegrationResult",
    "IntegrationStatus",
    "IntegrationManager",
    "get_integration_manager",
    "EventType",
    # Integrations
    "SlackIntegration",
    "JiraIntegration",
    "GitHubIntegration",
    "WebhookIntegration",
    "WebhookRegistry",
]


def create_integration(
    integration_type: str,
    config: IntegrationConfig,
) -> BaseIntegration:
    """
    Factory function to create an integration instance.
    
    Args:
        integration_type: Type of integration to create (slack, jira, github, webhook)
        config: Integration configuration
        
    Returns:
        Integration instance
        
    Raises:
        ValueError: If integration type is not supported
    """
    integrations = {
        "slack": SlackIntegration,
        "jira": JiraIntegration,
        "github": GitHubIntegration,
        "webhook": WebhookIntegration,
    }
    
    integration_class = integrations.get(integration_type.lower())
    if not integration_class:
        raise ValueError(f"Unsupported integration type: {integration_type}")
    
    return integration_class(config)
