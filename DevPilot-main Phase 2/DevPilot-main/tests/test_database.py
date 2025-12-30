"""
Database Tests for DevPilot

Tests for database models, repositories, and operations.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.dev_pilot.database.config import (
    Base,
    DatabaseConfig,
    DatabaseManager,
    get_db_manager,
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
    UserRepository,
    TeamRepository,
    ProjectRepository,
    ArtifactRepository,
    WorkflowRunRepository,
    AgentMessageRepository,
    IntegrationConnectionRepository,
    APIKeyRepository,
)


# ==================== Fixtures ====================

@pytest.fixture
def db_config():
    """Create test database config."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="devpilot_test",
        username="test",
        password="test",
    )


@pytest.fixture
def db_manager():
    """Create test database manager using SQLite."""
    manager = DatabaseManager(use_sqlite=True)
    return manager


@pytest.fixture
def sample_user_data():
    """Create sample user data."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "hashed_password_123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def sample_project_data(sample_user_data):
    """Create sample project data."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "A test project",
        "slug": "test-project",
        "owner_id": sample_user_data["id"],
        "status": ProjectStatus.DRAFT,
        "current_stage": SDLCStage.INITIALIZATION,
        "requirements": ["Requirement 1", "Requirement 2"],
    }


@pytest.fixture
def sample_artifact_data(sample_project_data):
    """Create sample artifact data."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": sample_project_data["id"],
        "artifact_type": ArtifactType.USER_STORIES,
        "name": "User Stories v1",
        "content": "# User Stories\n\n- Story 1\n- Story 2",
        "version": 1,
    }


# ==================== Database Config Tests ====================

class TestDatabaseConfig:
    """Tests for DatabaseConfig."""
    
    def test_config_creation(self, db_config):
        """Test config is created correctly."""
        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.database == "devpilot_test"
    
    def test_async_url(self, db_config):
        """Test async URL generation."""
        url = db_config.async_url
        assert "postgresql+asyncpg://" in url
        assert "devpilot_test" in url
    
    def test_sync_url(self, db_config):
        """Test sync URL generation."""
        url = db_config.sync_url
        assert "postgresql+psycopg2://" in url
        assert "devpilot_test" in url
    
    def test_sqlite_url(self, db_config):
        """Test SQLite URL generation."""
        url = db_config.sqlite_url
        assert "sqlite+aiosqlite://" in url
    
    def test_from_env(self):
        """Test config from environment."""
        with patch.dict('os.environ', {
            'DB_HOST': 'testhost',
            'DB_PORT': '5433',
            'DB_NAME': 'testdb',
        }):
            config = DatabaseConfig.from_env()
            assert config.host == "testhost"
            assert config.port == 5433
            assert config.database == "testdb"


class TestDatabaseManager:
    """Tests for DatabaseManager."""
    
    def test_initialization(self, db_manager):
        """Test manager initialization."""
        assert db_manager.use_sqlite is True
        assert db_manager._async_engine is None
    
    def test_get_url_sqlite(self, db_manager):
        """Test URL generation for SQLite."""
        url = db_manager._get_url(async_mode=True)
        assert "sqlite+aiosqlite://" in url
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self, db_manager):
        """Test session context manager."""
        # Create tables first
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            assert session is not None
        
        # Cleanup
        await db_manager.drop_tables()
        await db_manager.close()


# ==================== Model Tests ====================

class TestUserModel:
    """Tests for User model."""
    
    def test_user_creation(self, sample_user_data):
        """Test user model creation."""
        user = User(**sample_user_data)
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
    
    def test_user_repr(self, sample_user_data):
        """Test user string representation."""
        user = User(**sample_user_data)
        assert "testuser" in repr(user)


class TestProjectModel:
    """Tests for Project model."""
    
    def test_project_creation(self, sample_project_data):
        """Test project model creation."""
        project = Project(**sample_project_data)
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.DRAFT
        assert project.current_stage == SDLCStage.INITIALIZATION
    
    def test_project_requirements(self, sample_project_data):
        """Test project requirements field."""
        project = Project(**sample_project_data)
        assert len(project.requirements) == 2
        assert "Requirement 1" in project.requirements


class TestArtifactModel:
    """Tests for Artifact model."""
    
    def test_artifact_creation(self, sample_artifact_data):
        """Test artifact model creation."""
        artifact = Artifact(**sample_artifact_data)
        assert artifact.artifact_type == ArtifactType.USER_STORIES
        assert artifact.version == 1
        assert "User Stories" in artifact.content


class TestWorkflowRunModel:
    """Tests for WorkflowRun model."""
    
    def test_workflow_run_creation(self, sample_project_data):
        """Test workflow run model creation."""
        run = WorkflowRun(
            id=str(uuid.uuid4()),
            project_id=sample_project_data["id"],
            run_number=1,
            current_stage=SDLCStage.REQUIREMENTS,
            status="running",
        )
        assert run.run_number == 1
        assert run.status == "running"


# ==================== Enum Tests ====================

class TestEnums:
    """Tests for model enums."""
    
    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.DEVELOPER.value == "developer"
    
    def test_project_status_values(self):
        """Test ProjectStatus enum values."""
        assert ProjectStatus.DRAFT.value == "draft"
        assert ProjectStatus.COMPLETED.value == "completed"
    
    def test_artifact_type_values(self):
        """Test ArtifactType enum values."""
        assert ArtifactType.REQUIREMENTS.value == "requirements"
        assert ArtifactType.CODE.value == "code"
    
    def test_sdlc_stage_values(self):
        """Test SDLCStage enum values."""
        assert SDLCStage.INITIALIZATION.value == "initialization"
        assert SDLCStage.DEPLOYMENT.value == "deployment"


# ==================== Repository Tests ====================

class TestBaseRepository:
    """Tests for base repository functionality."""
    
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_manager, sample_user_data):
        """Test create and get operations."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            repo = UserRepository(session)
            
            # Create user
            user = await repo.create(sample_user_data)
            assert user.id == sample_user_data["id"]
            
            # Get user
            retrieved = await repo.get(user.id)
            assert retrieved is not None
            assert retrieved.email == sample_user_data["email"]
        
        await db_manager.drop_tables()
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_update(self, db_manager, sample_user_data):
        """Test update operation."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            repo = UserRepository(session)
            
            # Create user
            await repo.create(sample_user_data)
            
            # Update user
            updated = await repo.update(
                sample_user_data["id"],
                {"full_name": "Updated Name"}
            )
            assert updated.full_name == "Updated Name"
        
        await db_manager.drop_tables()
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_delete(self, db_manager, sample_user_data):
        """Test delete operation."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            repo = UserRepository(session)
            
            # Create user
            await repo.create(sample_user_data)
            
            # Delete user
            result = await repo.delete(sample_user_data["id"])
            assert result is True
            
            # Verify deletion
            retrieved = await repo.get(sample_user_data["id"])
            assert retrieved is None
        
        await db_manager.drop_tables()
        await db_manager.close()


class TestUserRepository:
    """Tests for UserRepository."""
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, db_manager, sample_user_data):
        """Test get user by email."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            repo = UserRepository(session)
            await repo.create(sample_user_data)
            
            user = await repo.get_by_email(sample_user_data["email"])
            assert user is not None
            assert user.username == sample_user_data["username"]
        
        await db_manager.drop_tables()
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_get_by_username(self, db_manager, sample_user_data):
        """Test get user by username."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            repo = UserRepository(session)
            await repo.create(sample_user_data)
            
            user = await repo.get_by_username(sample_user_data["username"])
            assert user is not None
            assert user.email == sample_user_data["email"]
        
        await db_manager.drop_tables()
        await db_manager.close()


class TestProjectRepository:
    """Tests for ProjectRepository."""
    
    @pytest.mark.asyncio
    async def test_get_user_projects(self, db_manager, sample_user_data, sample_project_data):
        """Test get projects by user."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            user_repo = UserRepository(session)
            project_repo = ProjectRepository(session)
            
            await user_repo.create(sample_user_data)
            await project_repo.create(sample_project_data)
            
            projects = await project_repo.get_user_projects(sample_user_data["id"])
            assert len(projects) == 1
            assert projects[0].name == sample_project_data["name"]
        
        await db_manager.drop_tables()
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_update_stage(self, db_manager, sample_user_data, sample_project_data):
        """Test update project stage."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            user_repo = UserRepository(session)
            project_repo = ProjectRepository(session)
            
            await user_repo.create(sample_user_data)
            await project_repo.create(sample_project_data)
            
            updated = await project_repo.update_stage(
                sample_project_data["id"],
                SDLCStage.REQUIREMENTS
            )
            assert updated.current_stage == SDLCStage.REQUIREMENTS
        
        await db_manager.drop_tables()
        await db_manager.close()


class TestArtifactRepository:
    """Tests for ArtifactRepository."""
    
    @pytest.mark.asyncio
    async def test_create_version(self, db_manager, sample_user_data, sample_project_data):
        """Test create artifact version."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            user_repo = UserRepository(session)
            project_repo = ProjectRepository(session)
            artifact_repo = ArtifactRepository(session)
            
            await user_repo.create(sample_user_data)
            await project_repo.create(sample_project_data)
            
            # Create first version
            v1 = await artifact_repo.create_version(
                project_id=sample_project_data["id"],
                artifact_type=ArtifactType.USER_STORIES,
                name="User Stories",
                content="Version 1 content",
            )
            assert v1.version == 1
            
            # Create second version
            v2 = await artifact_repo.create_version(
                project_id=sample_project_data["id"],
                artifact_type=ArtifactType.USER_STORIES,
                name="User Stories",
                content="Version 2 content",
            )
            assert v2.version == 2
            assert v2.parent_id == v1.id
        
        await db_manager.drop_tables()
        await db_manager.close()


class TestWorkflowRunRepository:
    """Tests for WorkflowRunRepository."""
    
    @pytest.mark.asyncio
    async def test_create_run(self, db_manager, sample_user_data, sample_project_data):
        """Test create workflow run."""
        await db_manager.create_tables()
        
        async with db_manager.session() as session:
            user_repo = UserRepository(session)
            project_repo = ProjectRepository(session)
            run_repo = WorkflowRunRepository(session)
            
            await user_repo.create(sample_user_data)
            await project_repo.create(sample_project_data)
            
            # Create first run
            run1 = await run_repo.create_run(sample_project_data["id"])
            assert run1.run_number == 1
            
            # Create second run
            run2 = await run_repo.create_run(sample_project_data["id"])
            assert run2.run_number == 2
        
        await db_manager.drop_tables()
        await db_manager.close()


# ==================== Global Function Tests ====================

class TestGlobalFunctions:
    """Tests for global database functions."""
    
    def test_get_db_manager_singleton(self):
        """Test database manager singleton."""
        manager1 = get_db_manager()
        manager2 = get_db_manager()
        # Note: They should be the same instance
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
