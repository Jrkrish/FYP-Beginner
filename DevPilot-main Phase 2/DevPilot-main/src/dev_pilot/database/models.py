"""
Database Models for DevPilot

Defines SQLAlchemy ORM models for users, teams, projects, and artifacts.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    Table,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.dev_pilot.database.config import Base


# ==================== Enums ====================

class UserRole(PyEnum):
    """User role enumeration."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class ProjectStatus(PyEnum):
    """Project status enumeration."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ArtifactType(PyEnum):
    """Artifact type enumeration."""
    REQUIREMENTS = "requirements"
    USER_STORIES = "user_stories"
    DESIGN_DOCUMENT = "design_document"
    CODE = "code"
    TEST_CASES = "test_cases"
    SECURITY_REPORT = "security_report"
    QA_REPORT = "qa_report"
    DEPLOYMENT_CONFIG = "deployment_config"


class SDLCStage(PyEnum):
    """SDLC stage enumeration."""
    INITIALIZATION = "initialization"
    REQUIREMENTS = "requirements"
    USER_STORIES = "user_stories"
    DESIGN = "design"
    DEVELOPMENT = "development"
    CODE_REVIEW = "code_review"
    SECURITY_REVIEW = "security_review"
    TESTING = "testing"
    QA = "qa"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"


# ==================== Association Tables ====================

# Team membership association
team_members = Table(
    "team_members",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column("role", Enum(UserRole), default=UserRole.DEVELOPER),
    Column("joined_at", DateTime, default=datetime.utcnow),
)

# Project team association
project_teams = Table(
    "project_teams",
    Base.metadata,
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
)


# ==================== Models ====================

class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Settings
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary=team_members,
        back_populates="members",
    )
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team",
        back_populates="owner",
        foreign_keys="Team.owner_id",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="Project.owner_id",
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Team(Base):
    """Team model for collaborative work."""
    
    __tablename__ = "teams"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Owner
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Settings
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_teams",
        foreign_keys=[owner_id],
    )
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary=team_members,
        back_populates="teams",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        secondary=project_teams,
        back_populates="teams",
    )
    
    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class Project(Base):
    """Project model for SDLC workflow."""
    
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Owner
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Status
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
    )
    current_stage: Mapped[SDLCStage] = mapped_column(
        Enum(SDLCStage),
        default=SDLCStage.INITIALIZATION,
    )
    
    # Requirements
    requirements: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Configuration
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Metadata
    metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
        foreign_keys=[owner_id],
    )
    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary=project_teams,
        back_populates="projects",
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
        UniqueConstraint("owner_id", "slug", name="uq_projects_owner_slug"),
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class Artifact(Base):
    """Artifact model for SDLC outputs."""
    
    __tablename__ = "artifacts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Type and name
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(50), default="markdown")
    
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("artifacts.id"), nullable=True)
    
    # Status
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="artifacts",
    )
    parent: Mapped[Optional["Artifact"]] = relationship(
        "Artifact",
        remote_side="Artifact.id",
        backref="versions",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_artifacts_project_type", "project_id", "artifact_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Artifact {self.name} v{self.version}>"


class WorkflowRun(Base):
    """Workflow execution run model."""
    
    __tablename__ = "workflow_runs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Run information
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    current_stage: Mapped[SDLCStage] = mapped_column(Enum(SDLCStage), nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="running")  # running, paused, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # State
    state: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    # Agent tracking
    active_agents: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    agent_logs: Mapped[Optional[List[Dict]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="workflow_runs",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_workflow_runs_project_status", "project_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<WorkflowRun {self.project_id}#{self.run_number}>"


class APIKey(Base):
    """API key model for programmatic access."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # For display
    
    # Permissions
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Usage
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
    )
    
    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}...>"


class AgentMessage(Base):
    """Agent message history for conversation tracking."""
    
    __tablename__ = "agent_messages"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Message info
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # request, response, notify, error
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Correlation
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reply_to: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_messages.id"), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("ix_agent_messages_workflow_agent", "workflow_run_id", "agent_id"),
        Index("ix_agent_messages_correlation", "correlation_id"),
    )
    
    def __repr__(self) -> str:
        return f"<AgentMessage {self.agent_id} {self.message_type}>"


class IntegrationConnection(Base):
    """External integration connection model."""
    
    __tablename__ = "integration_connections"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Integration info
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)  # slack, jira, github, webhook
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Configuration (encrypted in production)
    config: Mapped[Dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_integration_connections_user_type", "user_id", "integration_type"),
    )
    
    def __repr__(self) -> str:
        return f"<IntegrationConnection {self.integration_type}:{self.name}>"
