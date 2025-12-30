"""
Context Manager Module

Manages shared context and state for the multi-agent system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
from loguru import logger


@dataclass
class ProjectContext:
    """
    Holds all context for a project workflow.
    """
    project_id: str
    project_name: str
    requirements: List[str] = field(default_factory=list)
    user_stories: Any = None
    design_documents: Any = None
    code_generated: str = ""
    code_review_comments: str = ""
    security_recommendations: str = ""
    test_cases: str = ""
    qa_testing_comments: str = ""
    deployment_status: str = ""
    deployment_feedback: str = ""
    artifacts: Dict[str, str] = field(default_factory=dict)
    
    # Review states
    user_stories_review_status: str = "pending"
    design_documents_review_status: str = "pending"
    code_review_status: str = "pending"
    security_review_status: str = "pending"
    test_case_review_status: str = "pending"
    qa_testing_status: str = "pending"
    
    # Feedback
    user_stories_feedback: str = ""
    design_documents_feedback: str = ""
    code_review_feedback: str = ""
    security_review_comments: str = ""
    test_case_review_feedback: str = ""
    qa_testing_feedback: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    current_phase: str = "initialization"
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "requirements": self.requirements,
            "user_stories": self._serialize_value(self.user_stories),
            "design_documents": self._serialize_value(self.design_documents),
            "code_generated": self.code_generated,
            "code_review_comments": self.code_review_comments,
            "security_recommendations": self.security_recommendations,
            "test_cases": self.test_cases,
            "qa_testing_comments": self.qa_testing_comments,
            "deployment_status": self.deployment_status,
            "deployment_feedback": self.deployment_feedback,
            "artifacts": self.artifacts,
            "user_stories_review_status": self.user_stories_review_status,
            "design_documents_review_status": self.design_documents_review_status,
            "code_review_status": self.code_review_status,
            "security_review_status": self.security_review_status,
            "test_case_review_status": self.test_case_review_status,
            "qa_testing_status": self.qa_testing_status,
            "current_phase": self.current_phase,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON storage."""
        if value is None:
            return None
        if hasattr(value, 'model_dump'):
            return value.model_dump()
        if hasattr(value, 'to_dict'):
            return value.to_dict()
        return value
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectContext":
        """Create from dictionary."""
        return cls(
            project_id=data["project_id"],
            project_name=data["project_name"],
            requirements=data.get("requirements", []),
            user_stories=data.get("user_stories"),
            design_documents=data.get("design_documents"),
            code_generated=data.get("code_generated", ""),
            code_review_comments=data.get("code_review_comments", ""),
            security_recommendations=data.get("security_recommendations", ""),
            test_cases=data.get("test_cases", ""),
            qa_testing_comments=data.get("qa_testing_comments", ""),
            deployment_status=data.get("deployment_status", ""),
            deployment_feedback=data.get("deployment_feedback", ""),
            artifacts=data.get("artifacts", {}),
            current_phase=data.get("current_phase", "initialization"),
            version=data.get("version", 1),
        )
    
    def update(self, **kwargs):
        """Update context fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        self.version += 1


class ContextManager:
    """
    Manages shared context for the multi-agent system.
    
    Provides:
    - Project context storage and retrieval
    - State management across agents
    - Context versioning
    - Persistence (in-memory, Redis, or database)
    """
    
    def __init__(self, storage_backend: str = "memory", redis_client: Any = None):
        """
        Initialize context manager.
        
        Args:
            storage_backend: "memory" or "redis"
            redis_client: Redis client instance for redis backend
        """
        self._storage_backend = storage_backend
        self._redis = redis_client
        
        # In-memory storage
        self._contexts: Dict[str, ProjectContext] = {}
        self._global_context: Dict[str, Any] = {}
        
        # Context history for versioning
        self._context_history: Dict[str, List[Dict]] = {}
        
        logger.info(f"ContextManager initialized with {storage_backend} backend")
    
    async def create_project_context(
        self,
        project_id: str,
        project_name: str,
        requirements: Optional[List[str]] = None,
    ) -> ProjectContext:
        """Create a new project context."""
        context = ProjectContext(
            project_id=project_id,
            project_name=project_name,
            requirements=requirements or [],
        )
        
        self._contexts[project_id] = context
        self._context_history[project_id] = [context.to_dict()]
        
        await self._persist(project_id, context)
        
        logger.info(f"Created project context: {project_id}")
        return context
    
    async def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get project context by ID."""
        # Try in-memory first
        if project_id in self._contexts:
            return self._contexts[project_id]
        
        # Try loading from storage
        context = await self._load(project_id)
        if context:
            self._contexts[project_id] = context
            return context
        
        return None
    
    async def update_project_context(
        self,
        project_id: str,
        **updates
    ) -> Optional[ProjectContext]:
        """Update project context."""
        context = await self.get_project_context(project_id)
        if not context:
            return None
        
        context.update(**updates)
        
        # Save to history
        if project_id not in self._context_history:
            self._context_history[project_id] = []
        self._context_history[project_id].append(context.to_dict())
        
        # Persist
        await self._persist(project_id, context)
        
        logger.debug(f"Updated project context: {project_id}")
        return context
    
    async def get(self, key: str) -> Any:
        """Get a value from global context."""
        return self._global_context.get(key)
    
    async def set(self, key: str, value: Any):
        """Set a value in global context."""
        self._global_context[key] = value
    
    async def get_context_history(
        self,
        project_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get context version history."""
        history = self._context_history.get(project_id, [])
        return history[-limit:]
    
    async def rollback_context(
        self,
        project_id: str,
        version: int
    ) -> Optional[ProjectContext]:
        """Rollback context to a specific version."""
        history = self._context_history.get(project_id, [])
        
        for state in history:
            if state.get("version") == version:
                context = ProjectContext.from_dict(state)
                self._contexts[project_id] = context
                await self._persist(project_id, context)
                logger.info(f"Rolled back context {project_id} to version {version}")
                return context
        
        return None
    
    async def _persist(self, project_id: str, context: ProjectContext):
        """Persist context to storage backend."""
        if self._storage_backend == "redis" and self._redis:
            key = f"devpilot:context:{project_id}"
            await self._redis.set(key, json.dumps(context.to_dict()))
    
    async def _load(self, project_id: str) -> Optional[ProjectContext]:
        """Load context from storage backend."""
        if self._storage_backend == "redis" and self._redis:
            key = f"devpilot:context:{project_id}"
            data = await self._redis.get(key)
            if data:
                return ProjectContext.from_dict(json.loads(data))
        return None
    
    def get_all_projects(self) -> List[str]:
        """Get all project IDs."""
        return list(self._contexts.keys())
    
    def clear(self, project_id: Optional[str] = None):
        """Clear context(s)."""
        if project_id:
            self._contexts.pop(project_id, None)
            self._context_history.pop(project_id, None)
        else:
            self._contexts.clear()
            self._context_history.clear()
            self._global_context.clear()
