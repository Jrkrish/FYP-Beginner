"""
Base Integration Module

Defines the abstract base class and interfaces for all external integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from loguru import logger


class EventType(Enum):
    """Types of events that can trigger integrations."""
    
    # Project lifecycle events
    PROJECT_CREATED = "project_created"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_FAILED = "project_failed"
    
    # Stage events
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    
    # Approval events
    APPROVAL_REQUIRED = "approval_required"
    STAGE_APPROVED = "stage_approved"
    STAGE_REJECTED = "stage_rejected"
    
    # Agent events
    AGENT_TASK_STARTED = "agent_task_started"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    AGENT_TASK_FAILED = "agent_task_failed"
    
    # Artifact events
    USER_STORIES_GENERATED = "user_stories_generated"
    DESIGN_DOCS_GENERATED = "design_docs_generated"
    CODE_GENERATED = "code_generated"
    TEST_CASES_GENERATED = "test_cases_generated"
    
    # Custom events
    CUSTOM = "custom"


class IntegrationStatus(Enum):
    """Status of an integration."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    
    integration_id: str
    integration_type: str  # slack, jira, github, webhook
    name: str
    enabled: bool = True
    
    # Authentication
    api_key: Optional[str] = None
    api_token: Optional[str] = None
    webhook_url: Optional[str] = None
    oauth_token: Optional[str] = None
    
    # Connection settings
    base_url: Optional[str] = None
    workspace: Optional[str] = None
    project_key: Optional[str] = None
    repository: Optional[str] = None
    
    # Event subscriptions
    subscribed_events: List[EventType] = field(default_factory=list)
    
    # Additional settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "integration_id": self.integration_id,
            "integration_type": self.integration_type,
            "name": self.name,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "workspace": self.workspace,
            "project_key": self.project_key,
            "repository": self.repository,
            "subscribed_events": [e.value for e in self.subscribed_events],
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrationConfig":
        """Create from dictionary."""
        events = [EventType(e) for e in data.get("subscribed_events", [])]
        return cls(
            integration_id=data["integration_id"],
            integration_type=data["integration_type"],
            name=data["name"],
            enabled=data.get("enabled", True),
            api_key=data.get("api_key"),
            api_token=data.get("api_token"),
            webhook_url=data.get("webhook_url"),
            oauth_token=data.get("oauth_token"),
            base_url=data.get("base_url"),
            workspace=data.get("workspace"),
            project_key=data.get("project_key"),
            repository=data.get("repository"),
            subscribed_events=events,
            settings=data.get("settings", {}),
        )


@dataclass
class IntegrationEvent:
    """An event to be processed by integrations."""
    
    event_id: str
    event_type: EventType
    project_id: Optional[str]
    task_id: Optional[str]
    timestamp: datetime
    
    # Event payload
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Source information
    source_agent: Optional[str] = None
    source_stage: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "IntegrationEvent":
        """Create a new event."""
        return cls(
            event_id=f"event-{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            project_id=project_id,
            task_id=task_id,
            timestamp=datetime.utcnow(),
            data=data or {},
            **kwargs,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source_agent": self.source_agent,
            "source_stage": self.source_stage,
            "metadata": self.metadata,
        }


@dataclass
class IntegrationResult:
    """Result of an integration operation."""
    
    success: bool
    integration_id: str
    event_id: str
    message: str
    
    # Response data
    response_data: Optional[Dict[str, Any]] = None
    
    # Error information
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Timestamps
    processed_at: datetime = field(default_factory=datetime.utcnow)


class BaseIntegration(ABC):
    """
    Abstract base class for all external integrations.
    
    Subclasses must implement:
    - connect(): Establish connection to external service
    - disconnect(): Close connection
    - process_event(): Handle an integration event
    - health_check(): Verify integration is working
    """
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize the integration.
        
        Args:
            config: Integration configuration
        """
        self.config = config
        self._status = IntegrationStatus.INACTIVE
        self._connected = False
        self._error_count = 0
        self._last_error: Optional[str] = None
        
        logger.info(f"Integration created: {config.name} ({config.integration_type})")
    
    @property
    def integration_id(self) -> str:
        """Get integration ID."""
        return self.config.integration_id
    
    @property
    def integration_type(self) -> str:
        """Get integration type."""
        return self.config.integration_type
    
    @property
    def name(self) -> str:
        """Get integration name."""
        return self.config.name
    
    @property
    def status(self) -> IntegrationStatus:
        """Get current status."""
        return self._status
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected
    
    @property
    def is_enabled(self) -> bool:
        """Check if enabled."""
        return self.config.enabled
    
    def should_process_event(self, event: IntegrationEvent) -> bool:
        """
        Check if this integration should process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if the event should be processed
        """
        if not self.is_enabled:
            return False
        
        if not self._connected:
            return False
        
        # Check if subscribed to this event type
        if not self.config.subscribed_events:
            return True  # No filter = process all
        
        return event.event_type in self.config.subscribed_events
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to external service.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection to external service.
        
        Returns:
            True if disconnection successful
        """
        pass
    
    @abstractmethod
    async def process_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Process an integration event.
        
        Args:
            event: The event to process
            
        Returns:
            Result of the operation
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify integration is working properly.
        
        Returns:
            True if healthy
        """
        pass
    
    async def send_notification(
        self,
        title: str,
        message: str,
        **kwargs,
    ) -> IntegrationResult:
        """
        Send a notification via this integration.
        
        Args:
            title: Notification title
            message: Notification message
            **kwargs: Additional arguments
            
        Returns:
            Result of the operation
        """
        event = IntegrationEvent.create(
            event_type=EventType.CUSTOM,
            data={
                "title": title,
                "message": message,
                "notification": True,
                **kwargs,
            },
        )
        return await self.process_event(event)
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "integration_id": self.integration_id,
            "name": self.name,
            "type": self.integration_type,
            "status": self._status.value,
            "connected": self._connected,
            "enabled": self.is_enabled,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "subscribed_events": [e.value for e in self.config.subscribed_events],
        }
    
    def _set_connected(self, connected: bool):
        """Update connection status."""
        self._connected = connected
        self._status = IntegrationStatus.ACTIVE if connected else IntegrationStatus.INACTIVE
    
    def _set_error(self, error: str):
        """Record an error."""
        self._error_count += 1
        self._last_error = error
        self._status = IntegrationStatus.ERROR
        logger.error(f"Integration error ({self.name}): {error}")
    
    def _clear_error(self):
        """Clear error status."""
        self._last_error = None
        if self._connected:
            self._status = IntegrationStatus.ACTIVE
