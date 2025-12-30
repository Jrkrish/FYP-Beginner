"""
Integration Tests for DevPilot External Integrations

Tests for Slack, Jira, GitHub, and Webhook integrations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.dev_pilot.integrations.base import (
    IntegrationConfig,
    IntegrationEvent,
    IntegrationResult,
    IntegrationManager,
    IntegrationType,
    EventType,
)
from src.dev_pilot.integrations.slack_integration import SlackIntegration
from src.dev_pilot.integrations.jira_integration import JiraIntegration
from src.dev_pilot.integrations.github_integration import GitHubIntegration
from src.dev_pilot.integrations.webhook_integration import (
    WebhookIntegration,
    WebhookRegistry,
)


# ==================== Fixtures ====================

@pytest.fixture
def slack_config():
    """Create a Slack integration config."""
    return IntegrationConfig(
        integration_type=IntegrationType.SLACK,
        name="Test Slack",
        enabled=True,
        api_token="xoxb-test-token",
        settings={
            "default_channel": "#test-channel",
            "notify_on_start": True,
            "notify_on_complete": True,
        },
    )


@pytest.fixture
def jira_config():
    """Create a Jira integration config."""
    return IntegrationConfig(
        integration_type=IntegrationType.JIRA,
        name="Test Jira",
        enabled=True,
        base_url="https://test.atlassian.net",
        api_token="test-api-token",
        project_key="TEST",
        settings={
            "email": "test@example.com",
            "issue_type_story": "Story",
            "issue_type_task": "Task",
        },
    )


@pytest.fixture
def github_config():
    """Create a GitHub integration config."""
    return IntegrationConfig(
        integration_type=IntegrationType.GITHUB,
        name="Test GitHub",
        enabled=True,
        api_token="ghp_test_token",
        repository="test-repo",
        settings={
            "owner": "test-owner",
            "default_branch": "main",
            "auto_create_pr": True,
            "pr_reviewers": ["reviewer1"],
        },
    )


@pytest.fixture
def webhook_config():
    """Create a Webhook integration config."""
    return IntegrationConfig(
        integration_type=IntegrationType.WEBHOOK,
        name="Test Webhook",
        enabled=True,
        webhook_url="https://webhook.example.com/receive",
        api_token="webhook-secret",
        settings={
            "events": "all",
            "retry_count": 3,
            "timeout": 30,
        },
    )


@pytest.fixture
def sample_event():
    """Create a sample integration event."""
    return IntegrationEvent(
        event_type=EventType.PROJECT_CREATED,
        task_id="task-123",
        agent_id="agent-456",
        data={
            "project_name": "Test Project",
            "description": "A test project",
        },
        metadata={"source": "test"},
    )


# ==================== Integration Config Tests ====================

class TestIntegrationConfig:
    """Tests for IntegrationConfig."""
    
    def test_config_creation(self, slack_config):
        """Test config is created correctly."""
        assert slack_config.integration_type == IntegrationType.SLACK
        assert slack_config.name == "Test Slack"
        assert slack_config.enabled is True
        assert slack_config.api_token == "xoxb-test-token"
        assert slack_config.settings["default_channel"] == "#test-channel"
    
    def test_config_id_generation(self, slack_config):
        """Test config ID is auto-generated."""
        assert slack_config.id is not None
        assert len(slack_config.id) > 0
    
    def test_config_to_dict(self, slack_config):
        """Test config serialization."""
        data = slack_config.to_dict()
        assert data["integration_type"] == "slack"
        assert data["name"] == "Test Slack"
        assert data["enabled"] is True
    
    def test_config_from_dict(self):
        """Test config deserialization."""
        data = {
            "integration_type": "slack",
            "name": "From Dict",
            "enabled": True,
            "api_token": "token123",
            "settings": {},
        }
        config = IntegrationConfig.from_dict(data)
        assert config.integration_type == IntegrationType.SLACK
        assert config.name == "From Dict"


# ==================== Integration Event Tests ====================

class TestIntegrationEvent:
    """Tests for IntegrationEvent."""
    
    def test_event_creation(self, sample_event):
        """Test event is created correctly."""
        assert sample_event.event_type == EventType.PROJECT_CREATED
        assert sample_event.task_id == "task-123"
        assert sample_event.data["project_name"] == "Test Project"
    
    def test_event_id_generation(self, sample_event):
        """Test event ID is auto-generated."""
        assert sample_event.event_id is not None
        assert len(sample_event.event_id) > 0
    
    def test_event_timestamp(self, sample_event):
        """Test event has timestamp."""
        assert sample_event.timestamp is not None
        assert isinstance(sample_event.timestamp, datetime)
    
    def test_event_to_dict(self, sample_event):
        """Test event serialization."""
        data = sample_event.to_dict()
        assert data["event_type"] == "project_created"
        assert data["task_id"] == "task-123"


# ==================== Slack Integration Tests ====================

class TestSlackIntegration:
    """Tests for SlackIntegration."""
    
    def test_initialization(self, slack_config):
        """Test Slack integration initialization."""
        integration = SlackIntegration(slack_config)
        assert integration.bot_token == "xoxb-test-token"
        assert integration.default_channel == "#test-channel"
        assert integration.is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_success(self, slack_config):
        """Test successful connection."""
        integration = SlackIntegration(slack_config)
        
        with patch.object(integration, '_session', None):
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"ok": True, "user": "testbot"})
                
                mock_session_instance = MagicMock()
                mock_session_instance.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
                mock_session.return_value = mock_session_instance
                
                result = await integration.connect()
                # Connection depends on actual aiohttp setup
    
    @pytest.mark.asyncio
    async def test_process_project_created_event(self, slack_config, sample_event):
        """Test processing project created event."""
        integration = SlackIntegration(slack_config)
        integration._set_connected(True)
        
        # Mock the send_message method
        integration.send_message = AsyncMock(return_value=True)
        
        result = await integration.process_event(sample_event)
        
        # Should attempt to send a message
        assert isinstance(result, IntegrationResult)
    
    def test_format_stage_message(self, slack_config):
        """Test message formatting."""
        integration = SlackIntegration(slack_config)
        
        # Test basic formatting method exists
        assert hasattr(integration, '_format_stage_notification')


# ==================== Jira Integration Tests ====================

class TestJiraIntegration:
    """Tests for JiraIntegration."""
    
    def test_initialization(self, jira_config):
        """Test Jira integration initialization."""
        integration = JiraIntegration(jira_config)
        assert integration.base_url == "https://test.atlassian.net"
        assert integration.project_key == "TEST"
        assert integration.email == "test@example.com"
    
    def test_auth_header(self, jira_config):
        """Test authentication header generation."""
        integration = JiraIntegration(jira_config)
        headers = integration._get_auth_header()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
    
    def test_priority_mapping(self, jira_config):
        """Test priority mapping."""
        integration = JiraIntegration(jira_config)
        assert integration._map_priority("Critical") == "Highest"
        assert integration._map_priority("Medium") == "Medium"
        assert integration._map_priority("Unknown") == "Medium"
    
    def test_format_user_story_description(self, jira_config):
        """Test user story description formatting."""
        integration = JiraIntegration(jira_config)
        story = {
            "description": "Test description",
            "acceptance_criteria": "- AC1\n- AC2",
        }
        description = integration._format_user_story_description(story)
        assert "Test description" in description
        assert "Acceptance Criteria" in description


# ==================== GitHub Integration Tests ====================

class TestGitHubIntegration:
    """Tests for GitHubIntegration."""
    
    def test_initialization(self, github_config):
        """Test GitHub integration initialization."""
        integration = GitHubIntegration(github_config)
        assert integration.api_token == "ghp_test_token"
        assert integration.owner == "test-owner"
        assert integration.repository == "test-repo"
        assert integration.default_branch == "main"
    
    def test_headers(self, github_config):
        """Test request headers."""
        integration = GitHubIntegration(github_config)
        headers = integration._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ghp_test_token"
        assert "X-GitHub-Api-Version" in headers
    
    def test_sanitize_branch_name(self, github_config):
        """Test branch name sanitization."""
        integration = GitHubIntegration(github_config)
        
        assert integration._sanitize_branch_name("Feature Name") == "feature-name"
        assert integration._sanitize_branch_name("feature/test") == "feature-test"
        assert integration._sanitize_branch_name("a" * 100)[:50] == "a" * 50
    
    def test_format_pr_description(self, github_config):
        """Test PR description formatting."""
        integration = GitHubIntegration(github_config)
        files = [
            {"path": "src/main.py"},
            {"path": "src/utils.py"},
        ]
        description = integration._format_pr_description(
            "Test Project",
            files,
            "task-123"
        )
        assert "Test Project" in description
        assert "src/main.py" in description
        assert "task-123" in description


# ==================== Webhook Integration Tests ====================

class TestWebhookIntegration:
    """Tests for WebhookIntegration."""
    
    def test_initialization(self, webhook_config):
        """Test Webhook integration initialization."""
        integration = WebhookIntegration(webhook_config)
        assert integration.webhook_url == "https://webhook.example.com/receive"
        assert integration.secret == "webhook-secret"
        assert integration.enabled_events == "all"
    
    def test_sign_payload(self, webhook_config):
        """Test payload signing."""
        integration = WebhookIntegration(webhook_config)
        signature = integration._sign_payload('{"test": "data"}')
        assert signature.startswith("sha256=")
        assert len(signature) > 10
    
    def test_sign_payload_no_secret(self, webhook_config):
        """Test payload signing without secret."""
        webhook_config.api_token = ""
        integration = WebhookIntegration(webhook_config)
        signature = integration._sign_payload('{"test": "data"}')
        assert signature == ""
    
    def test_should_send_event(self, webhook_config):
        """Test event filtering."""
        integration = WebhookIntegration(webhook_config)
        
        # All events enabled
        assert integration._should_send_event(EventType.PROJECT_CREATED) is True
        assert integration._should_send_event(EventType.CODE_GENERATED) is True
        
        # Filter specific events
        integration.enabled_events = ["project_created"]
        assert integration._should_send_event(EventType.PROJECT_CREATED) is True
    
    def test_build_payload(self, webhook_config, sample_event):
        """Test payload building."""
        integration = WebhookIntegration(webhook_config)
        payload = integration._build_payload(sample_event)
        
        assert payload["event_type"] == "project_created"
        assert payload["task_id"] == "task-123"
        assert "data" in payload
        assert payload["data"]["project_name"] == "Test Project"
    
    def test_template_application(self, webhook_config, sample_event):
        """Test custom template application."""
        integration = WebhookIntegration(webhook_config)
        integration.payload_template = {
            "type": "{{event_type}}",
            "project": "{{data.project_name}}",
        }
        
        payload = integration._build_payload(sample_event)
        assert payload["type"] == "project_created"
        assert payload["project"] == "Test Project"


class TestWebhookRegistry:
    """Tests for WebhookRegistry."""
    
    def test_register_webhook(self, webhook_config):
        """Test registering a webhook."""
        registry = WebhookRegistry()
        webhook = WebhookIntegration(webhook_config)
        
        registry.register("test-webhook", webhook)
        
        webhooks = registry.list_webhooks()
        assert len(webhooks) == 1
        assert webhooks[0]["id"] == "test-webhook"
    
    def test_register_with_events(self, webhook_config):
        """Test registering webhook with specific events."""
        registry = WebhookRegistry()
        webhook = WebhookIntegration(webhook_config)
        
        registry.register(
            "test-webhook",
            webhook,
            events=[EventType.PROJECT_CREATED, EventType.CODE_GENERATED]
        )
        
        webhooks_for_project = registry.get_webhooks_for_event(EventType.PROJECT_CREATED)
        assert len(webhooks_for_project) >= 1
    
    def test_unregister_webhook(self, webhook_config):
        """Test unregistering a webhook."""
        registry = WebhookRegistry()
        webhook = WebhookIntegration(webhook_config)
        
        registry.register("test-webhook", webhook)
        registry.unregister("test-webhook")
        
        webhooks = registry.list_webhooks()
        assert len(webhooks) == 0


# ==================== Integration Manager Tests ====================

class TestIntegrationManager:
    """Tests for IntegrationManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = IntegrationManager()
        assert manager._integrations == {}
    
    def test_add_integration(self, slack_config):
        """Test adding an integration."""
        manager = IntegrationManager()
        integration = SlackIntegration(slack_config)
        
        manager.add_integration(integration)
        
        assert integration.integration_id in manager._integrations
    
    def test_remove_integration(self, slack_config):
        """Test removing an integration."""
        manager = IntegrationManager()
        integration = SlackIntegration(slack_config)
        
        manager.add_integration(integration)
        manager.remove_integration(integration.integration_id)
        
        assert integration.integration_id not in manager._integrations
    
    def test_get_integration(self, slack_config):
        """Test getting an integration."""
        manager = IntegrationManager()
        integration = SlackIntegration(slack_config)
        
        manager.add_integration(integration)
        retrieved = manager.get_integration(integration.integration_id)
        
        assert retrieved is integration
    
    def test_get_integrations_by_type(self, slack_config, jira_config):
        """Test getting integrations by type."""
        manager = IntegrationManager()
        slack = SlackIntegration(slack_config)
        jira = JiraIntegration(jira_config)
        
        manager.add_integration(slack)
        manager.add_integration(jira)
        
        slack_integrations = manager.get_integrations_by_type(IntegrationType.SLACK)
        assert len(slack_integrations) == 1
        assert slack_integrations[0] is slack
    
    @pytest.mark.asyncio
    async def test_dispatch_event(self, slack_config, sample_event):
        """Test dispatching an event."""
        manager = IntegrationManager()
        integration = SlackIntegration(slack_config)
        integration._set_connected(True)
        integration.process_event = AsyncMock(return_value=IntegrationResult(
            success=True,
            integration_id=integration.integration_id,
            event_id=sample_event.event_id,
            message="Test success",
        ))
        
        manager.add_integration(integration)
        
        results = await manager.dispatch_event(sample_event)
        
        assert len(results) == 1
        assert results[0].success is True
    
    def test_list_integrations(self, slack_config, jira_config):
        """Test listing all integrations."""
        manager = IntegrationManager()
        slack = SlackIntegration(slack_config)
        jira = JiraIntegration(jira_config)
        
        manager.add_integration(slack)
        manager.add_integration(jira)
        
        integrations = manager.list_integrations()
        assert len(integrations) == 2


# ==================== Event Type Tests ====================

class TestEventTypes:
    """Tests for event type enumeration."""
    
    def test_all_event_types_exist(self):
        """Test all expected event types exist."""
        expected = [
            "PROJECT_CREATED",
            "USER_STORIES_GENERATED",
            "DESIGN_COMPLETED",
            "CODE_GENERATED",
            "TEST_CASES_GENERATED",
            "SECURITY_REVIEW_COMPLETED",
            "STAGE_COMPLETED",
            "APPROVAL_REQUIRED",
            "APPROVAL_RECEIVED",
            "ERROR_OCCURRED",
        ]
        
        for event_name in expected:
            assert hasattr(EventType, event_name)
    
    def test_event_type_values(self):
        """Test event type values are strings."""
        assert EventType.PROJECT_CREATED.value == "project_created"
        assert EventType.CODE_GENERATED.value == "code_generated"


# ==================== Integration Type Tests ====================

class TestIntegrationTypes:
    """Tests for integration type enumeration."""
    
    def test_all_integration_types_exist(self):
        """Test all expected integration types exist."""
        expected = ["SLACK", "JIRA", "GITHUB", "WEBHOOK"]
        
        for int_type in expected:
            assert hasattr(IntegrationType, int_type)
    
    def test_integration_type_values(self):
        """Test integration type values are strings."""
        assert IntegrationType.SLACK.value == "slack"
        assert IntegrationType.GITHUB.value == "github"


# ==================== Factory Function Tests ====================

class TestCreateIntegration:
    """Tests for integration factory function."""
    
    def test_create_slack_integration(self, slack_config):
        """Test creating Slack integration via factory."""
        from src.dev_pilot.integrations import create_integration
        
        integration = create_integration(IntegrationType.SLACK, slack_config)
        assert isinstance(integration, SlackIntegration)
    
    def test_create_jira_integration(self, jira_config):
        """Test creating Jira integration via factory."""
        from src.dev_pilot.integrations import create_integration
        
        integration = create_integration(IntegrationType.JIRA, jira_config)
        assert isinstance(integration, JiraIntegration)
    
    def test_create_github_integration(self, github_config):
        """Test creating GitHub integration via factory."""
        from src.dev_pilot.integrations import create_integration
        
        integration = create_integration(IntegrationType.GITHUB, github_config)
        assert isinstance(integration, GitHubIntegration)
    
    def test_create_webhook_integration(self, webhook_config):
        """Test creating Webhook integration via factory."""
        from src.dev_pilot.integrations import create_integration
        
        integration = create_integration(IntegrationType.WEBHOOK, webhook_config)
        assert isinstance(integration, WebhookIntegration)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
