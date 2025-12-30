"""
DevPilot Database Module

Provides database configuration, models, and repository pattern implementations.
"""

from src.dev_pilot.database.config import (
    Base,
    DatabaseConfig,
    DatabaseManager,
    get_db_manager,
    get_session,
)
from src.dev_pilot.database.models import (
    User,
    Team,
    Project,
    Artifact,
    WorkflowRun,
    APIKey,
    AgentMessage,
    IntegrationConnection,
    UserRole,
    ProjectStatus,
    ArtifactType,
    SDLCStage,
)
from src.dev_pilot.database.repositories import (
    BaseRepository,
    UserRepository,
    TeamRepository,
    ProjectRepository,
    ArtifactRepository,
    WorkflowRunRepository,
    AgentMessageRepository,
    IntegrationConnectionRepository,
    APIKeyRepository,
)


__all__ = [
    # Config
    "Base",
    "DatabaseConfig",
    "DatabaseManager",
    "get_db_manager",
    "get_session",
    # Models
    "User",
    "Team",
    "Project",
    "Artifact",
    "WorkflowRun",
    "APIKey",
    "AgentMessage",
    "IntegrationConnection",
    # Enums
    "UserRole",
    "ProjectStatus",
    "ArtifactType",
    "SDLCStage",
    # Repositories
    "BaseRepository",
    "UserRepository",
    "TeamRepository",
    "ProjectRepository",
    "ArtifactRepository",
    "WorkflowRunRepository",
    "AgentMessageRepository",
    "IntegrationConnectionRepository",
    "APIKeyRepository",
]
