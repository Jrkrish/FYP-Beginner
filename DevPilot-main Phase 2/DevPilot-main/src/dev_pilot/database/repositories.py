"""
Database Repository Layer

Provides repository pattern implementations for database operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from datetime import datetime
import uuid

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from src.dev_pilot.database.config import Base
from src.dev_pilot.database.models import (
    User,
    Team,
    Project,
    Artifact,
    WorkflowRun,
    APIKey,
    AgentMessage,
    IntegrationConnection,
    ProjectStatus,
    SDLCStage,
    ArtifactType,
)


# Generic type for models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """
    Abstract base repository providing common CRUD operations.
    
    All repositories should inherit from this class.
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        Initialize repository.
        
        Args:
            session: Database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
    
    async def get(self, id: str) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """Get all records with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record by ID."""
        data["updated_at"] = datetime.utcnow()
        
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
        )
        await self.session.flush()
        
        return await self.get(id)
    
    async def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0
    
    async def count(self) -> int:
        """Count total records."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0
    
    async def exists(self, id: str) -> bool:
        """Check if a record exists."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_with_teams(self, user_id: str) -> Optional[User]:
        """Get user with teams loaded."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.teams))
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.utcnow())
        )
        await self.session.flush()
    
    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """Get all active users."""
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class TeamRepository(BaseRepository[Team]):
    """Repository for Team operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Team)
    
    async def get_by_slug(self, slug: str) -> Optional[Team]:
        """Get team by slug."""
        result = await self.session.execute(
            select(Team).where(Team.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_with_members(self, team_id: str) -> Optional[Team]:
        """Get team with members loaded."""
        result = await self.session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members))
        )
        return result.scalar_one_or_none()
    
    async def get_user_teams(self, user_id: str) -> List[Team]:
        """Get all teams a user belongs to."""
        result = await self.session.execute(
            select(Team)
            .join(Team.members)
            .where(User.id == user_id)
        )
        return list(result.scalars().all())
    
    async def get_owned_teams(self, owner_id: str) -> List[Team]:
        """Get teams owned by a user."""
        result = await self.session.execute(
            select(Team).where(Team.owner_id == owner_id)
        )
        return list(result.scalars().all())


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Project)
    
    async def get_by_slug(self, owner_id: str, slug: str) -> Optional[Project]:
        """Get project by owner and slug."""
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .where(Project.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_with_artifacts(self, project_id: str) -> Optional[Project]:
        """Get project with artifacts loaded."""
        result = await self.session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.artifacts))
        )
        return result.scalar_one_or_none()
    
    async def get_user_projects(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Project]:
        """Get projects owned by a user."""
        query = select(Project).where(Project.owner_id == owner_id)
        
        if status:
            query = query.where(Project.status == status)
        
        query = query.order_by(Project.updated_at.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_stage(
        self,
        project_id: str,
        stage: SDLCStage,
    ) -> Optional[Project]:
        """Update project's current SDLC stage."""
        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(current_stage=stage, updated_at=datetime.utcnow())
        )
        await self.session.flush()
        return await self.get(project_id)
    
    async def update_status(
        self,
        project_id: str,
        status: ProjectStatus,
    ) -> Optional[Project]:
        """Update project status."""
        values = {"status": status, "updated_at": datetime.utcnow()}
        if status == ProjectStatus.COMPLETED:
            values["completed_at"] = datetime.utcnow()
        
        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(**values)
        )
        await self.session.flush()
        return await self.get(project_id)
    
    async def search(
        self,
        query: str,
        owner_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Project]:
        """Search projects by name or description."""
        stmt = select(Project).where(
            (Project.name.ilike(f"%{query}%")) |
            (Project.description.ilike(f"%{query}%"))
        )
        
        if owner_id:
            stmt = stmt.where(Project.owner_id == owner_id)
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ArtifactRepository(BaseRepository[Artifact]):
    """Repository for Artifact operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Artifact)
    
    async def get_project_artifacts(
        self,
        project_id: str,
        artifact_type: Optional[ArtifactType] = None,
    ) -> List[Artifact]:
        """Get all artifacts for a project."""
        query = select(Artifact).where(Artifact.project_id == project_id)
        
        if artifact_type:
            query = query.where(Artifact.artifact_type == artifact_type)
        
        query = query.order_by(Artifact.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_latest_artifact(
        self,
        project_id: str,
        artifact_type: ArtifactType,
    ) -> Optional[Artifact]:
        """Get the latest artifact of a specific type."""
        result = await self.session.execute(
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .where(Artifact.artifact_type == artifact_type)
            .order_by(Artifact.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def create_version(
        self,
        project_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> Artifact:
        """Create a new version of an artifact."""
        # Get latest version number
        latest = await self.get_latest_artifact(project_id, artifact_type)
        version = (latest.version + 1) if latest else 1
        parent_id = latest.id if latest else None
        
        return await self.create({
            "project_id": project_id,
            "artifact_type": artifact_type,
            "name": name,
            "content": content,
            "version": version,
            "parent_id": parent_id,
            "metadata": metadata or {},
        })
    
    async def approve_artifact(
        self,
        artifact_id: str,
        approved_by: str,
    ) -> Optional[Artifact]:
        """Mark an artifact as approved."""
        await self.session.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(
                is_approved=True,
                approved_by=approved_by,
                approved_at=datetime.utcnow(),
            )
        )
        await self.session.flush()
        return await self.get(artifact_id)


class WorkflowRunRepository(BaseRepository[WorkflowRun]):
    """Repository for WorkflowRun operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkflowRun)
    
    async def get_project_runs(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowRun]:
        """Get all workflow runs for a project."""
        result = await self.session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.project_id == project_id)
            .order_by(WorkflowRun.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_latest_run(self, project_id: str) -> Optional[WorkflowRun]:
        """Get the latest workflow run for a project."""
        result = await self.session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.project_id == project_id)
            .order_by(WorkflowRun.run_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def create_run(
        self,
        project_id: str,
        initial_state: Optional[Dict] = None,
    ) -> WorkflowRun:
        """Create a new workflow run."""
        latest = await self.get_latest_run(project_id)
        run_number = (latest.run_number + 1) if latest else 1
        
        return await self.create({
            "project_id": project_id,
            "run_number": run_number,
            "current_stage": SDLCStage.INITIALIZATION,
            "state": initial_state or {},
        })
    
    async def update_state(
        self,
        run_id: str,
        state: Dict[str, Any],
        stage: Optional[SDLCStage] = None,
    ) -> Optional[WorkflowRun]:
        """Update workflow run state."""
        values = {"state": state}
        if stage:
            values["current_stage"] = stage
        
        await self.session.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .values(**values)
        )
        await self.session.flush()
        return await self.get(run_id)
    
    async def complete_run(
        self,
        run_id: str,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> Optional[WorkflowRun]:
        """Mark a workflow run as complete."""
        values = {
            "status": status,
            "completed_at": datetime.utcnow(),
        }
        if error_message:
            values["error_message"] = error_message
        
        await self.session.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .values(**values)
        )
        await self.session.flush()
        return await self.get(run_id)


class AgentMessageRepository(BaseRepository[AgentMessage]):
    """Repository for AgentMessage operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentMessage)
    
    async def get_run_messages(
        self,
        workflow_run_id: str,
        agent_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[AgentMessage]:
        """Get all messages for a workflow run."""
        query = select(AgentMessage).where(
            AgentMessage.workflow_run_id == workflow_run_id
        )
        
        if agent_id:
            query = query.where(AgentMessage.agent_id == agent_id)
        
        query = query.order_by(AgentMessage.created_at).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_correlation(
        self,
        correlation_id: str,
    ) -> List[AgentMessage]:
        """Get all messages with a correlation ID."""
        result = await self.session.execute(
            select(AgentMessage)
            .where(AgentMessage.correlation_id == correlation_id)
            .order_by(AgentMessage.created_at)
        )
        return list(result.scalars().all())


class IntegrationConnectionRepository(BaseRepository[IntegrationConnection]):
    """Repository for IntegrationConnection operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, IntegrationConnection)
    
    async def get_user_integrations(
        self,
        user_id: str,
        integration_type: Optional[str] = None,
    ) -> List[IntegrationConnection]:
        """Get all integrations for a user."""
        query = select(IntegrationConnection).where(
            IntegrationConnection.user_id == user_id
        )
        
        if integration_type:
            query = query.where(
                IntegrationConnection.integration_type == integration_type
            )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_active_integrations(
        self,
        user_id: str,
    ) -> List[IntegrationConnection]:
        """Get all active integrations for a user."""
        result = await self.session.execute(
            select(IntegrationConnection)
            .where(IntegrationConnection.user_id == user_id)
            .where(IntegrationConnection.is_active == True)
        )
        return list(result.scalars().all())


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for APIKey operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, APIKey)
    
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.key_hash == key_hash)
            .where(APIKey.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def get_user_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def record_usage(self, key_id: str) -> None:
        """Record API key usage."""
        await self.session.execute(
            update(APIKey)
            .where(APIKey.id == key_id)
            .values(
                last_used_at=datetime.utcnow(),
                usage_count=APIKey.usage_count + 1,
            )
        )
        await self.session.flush()
