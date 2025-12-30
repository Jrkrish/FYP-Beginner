"""
Integration tests for FastAPI v2 Agent-Based Endpoints

Tests the new API endpoints that use the multi-agent system.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPIv2Endpoints:
    """Test suite for API v2 endpoints."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock()
        llm.invoke = Mock(return_value=Mock(content="Test response"))
        return llm
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.GEMINI_API_KEY = "test-gemini-key"
        settings.GROQ_API_KEY = "test-groq-key"
        return settings
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock agentic executor."""
        executor = Mock()
        executor.start_workflow = Mock(return_value={
            "task_id": "test-task-123",
            "state": {"project_name": "Test Project"},
        })
        executor.generate_stories = Mock(return_value={
            "task_id": "test-task-123",
            "state": {"user_stories": []},
        })
        executor.get_updated_state = Mock(return_value={
            "task_id": "test-task-123",
            "state": {"next_node": "review_user_stories"},
        })
        executor.graph_review_flow = Mock(return_value={
            "task_id": "test-task-123",
            "state": {},
        })
        executor.get_session_info = Mock(return_value={
            "project_id": "project-123",
            "project_name": "Test",
        })
        executor.get_agent_status = Mock(return_value={
            "agents": {},
            "projects_count": 0,
        })
        executor.is_using_agents = Mock(return_value=True)
        return executor
    
    @pytest.fixture
    def client(self, mock_llm, mock_settings, mock_executor):
        """Create test client with mocked dependencies."""
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "GROQ_API_KEY": "test-key",
        }):
            with patch('src.dev_pilot.api.fastapi_app.GeminiLLM') as mock_gemini:
                mock_gemini.return_value.get_llm_model.return_value = mock_llm
                
                with patch('src.dev_pilot.api.fastapi_app.GraphBuilder') as mock_builder:
                    mock_graph = Mock()
                    mock_builder.return_value.setup_graph.return_value = mock_graph
                    
                    with patch('src.dev_pilot.api.fastapi_app.GraphExecutor') as mock_graph_executor:
                        mock_graph_executor.return_value = Mock()
                        
                        with patch('src.dev_pilot.api.fastapi_app.AgenticGraphExecutor') as mock_agentic:
                            mock_agentic.return_value = mock_executor
                            
                            from src.dev_pilot.api.fastapi_app import app
                            client = TestClient(app)
                            yield client


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_returns_200(self):
        """Test health endpoint returns 200."""
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "GROQ_API_KEY": "test-key",
        }):
            with patch('src.dev_pilot.api.fastapi_app.GeminiLLM'):
                with patch('src.dev_pilot.api.fastapi_app.GraphBuilder'):
                    with patch('src.dev_pilot.api.fastapi_app.GraphExecutor'):
                        with patch('src.dev_pilot.api.fastapi_app.AgenticGraphExecutor'):
                            from src.dev_pilot.api.fastapi_app import app
                            client = TestClient(app)
                            
                            response = client.get("/health")
                            assert response.status_code == 200
                            data = response.json()
                            assert data["status"] == "healthy"


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_returns_welcome(self):
        """Test root endpoint returns welcome message."""
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "GROQ_API_KEY": "test-key",
        }):
            with patch('src.dev_pilot.api.fastapi_app.GeminiLLM'):
                with patch('src.dev_pilot.api.fastapi_app.GraphBuilder'):
                    with patch('src.dev_pilot.api.fastapi_app.GraphExecutor'):
                        with patch('src.dev_pilot.api.fastapi_app.AgenticGraphExecutor'):
                            from src.dev_pilot.api.fastapi_app import app
                            client = TestClient(app)
                            
                            response = client.get("/")
                            assert response.status_code == 200
                            data = response.json()
                            assert "Welcome to DevPilot API" in data["message"]


class TestWebSocketManager:
    """Test WebSocket connection manager."""
    
    def test_connection_manager_creation(self):
        """Test connection manager can be created."""
        from src.dev_pilot.api.fastapi_app import ConnectionManager
        
        manager = ConnectionManager()
        assert manager.active_connections == []
        assert manager.task_subscriptions == {}


class TestRequestModels:
    """Test request/response models."""
    
    def test_create_project_request(self):
        """Test CreateProjectRequest model."""
        from src.dev_pilot.api.fastapi_app import CreateProjectRequest
        
        request = CreateProjectRequest(
            project_name="Test Project",
            requirements=["Req 1", "Req 2"],
            use_agents=True,
        )
        
        assert request.project_name == "Test Project"
        assert len(request.requirements) == 2
        assert request.use_agents == True
    
    def test_create_project_request_defaults(self):
        """Test CreateProjectRequest default values."""
        from src.dev_pilot.api.fastapi_app import CreateProjectRequest
        
        request = CreateProjectRequest(project_name="Test")
        
        assert request.requirements is None
        assert request.use_agents == True
    
    def test_project_response(self):
        """Test ProjectResponse model."""
        from src.dev_pilot.api.fastapi_app import ProjectResponse
        
        response = ProjectResponse(
            status="success",
            project_id="proj-123",
            task_id="task-123",
            message="Created",
            data={"key": "value"},
        )
        
        assert response.status == "success"
        assert response.project_id == "proj-123"
    
    def test_approve_stage_request(self):
        """Test ApproveStageRequest model."""
        from src.dev_pilot.api.fastapi_app import ApproveStageRequest
        
        request = ApproveStageRequest(
            task_id="task-123",
            feedback="Looks good!",
        )
        
        assert request.task_id == "task-123"
        assert request.feedback == "Looks good!"
    
    def test_reject_stage_request(self):
        """Test RejectStageRequest model."""
        from src.dev_pilot.api.fastapi_app import RejectStageRequest
        
        request = RejectStageRequest(
            task_id="task-123",
            feedback="Needs improvement",
        )
        
        assert request.task_id == "task-123"
        assert request.feedback == "Needs improvement"


class TestModelLists:
    """Test model configuration lists."""
    
    def test_groq_models_no_deprecated(self):
        """Test Groq models list doesn't contain deprecated models."""
        from src.dev_pilot.api.fastapi_app import groq_models
        
        deprecated_models = ["gemma2-9b-it", "llama3-70b-8192"]
        
        for model in deprecated_models:
            assert model not in groq_models, f"Deprecated model {model} found in groq_models"
    
    def test_groq_models_has_valid_models(self):
        """Test Groq models list has valid models."""
        from src.dev_pilot.api.fastapi_app import groq_models
        
        assert len(groq_models) > 0
        assert "llama-3.3-70b-versatile" in groq_models
    
    def test_gemini_models_list(self):
        """Test Gemini models list."""
        from src.dev_pilot.api.fastapi_app import gemini_models
        
        assert len(gemini_models) > 0
        assert any("gemini" in model for model in gemini_models)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
