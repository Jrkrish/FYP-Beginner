"""
Integration tests for AgenticGraphExecutor

Tests the bridge between the new multi-agent system and the existing GraphExecutor interface.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dev_pilot.graph.agentic_executor import AgenticGraphExecutor
from src.dev_pilot.state.sdlc_state import UserStoryList, UserStory
import src.dev_pilot.utils.constants as const


class TestAgenticGraphExecutor:
    """Test suite for AgenticGraphExecutor."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock()
        llm.invoke = Mock(return_value=Mock(content="Test response"))
        return llm
    
    @pytest.fixture
    def mock_graph(self):
        """Create a mock legacy graph."""
        graph = Mock()
        graph.stream = Mock(return_value=[{"test": "state"}])
        graph.get_state = Mock(return_value={"test": "state"})
        graph.update_state = Mock()
        return graph
    
    @pytest.fixture
    def executor_with_fallback(self, mock_llm, mock_graph):
        """Create an executor with fallback graph."""
        return AgenticGraphExecutor(
            llm=mock_llm,
            use_agents=False,  # Test fallback mode
            fallback_graph=mock_graph,
        )
    
    @pytest.fixture
    def executor_agent_mode(self, mock_llm, mock_graph):
        """Create an executor in agent mode."""
        return AgenticGraphExecutor(
            llm=mock_llm,
            use_agents=True,
            fallback_graph=mock_graph,
        )
    
    def test_executor_creation(self, mock_llm):
        """Test executor can be created."""
        executor = AgenticGraphExecutor(llm=mock_llm)
        assert executor is not None
        assert executor.llm == mock_llm
    
    def test_executor_fallback_mode(self, executor_with_fallback):
        """Test executor in fallback mode."""
        assert executor_with_fallback.use_agents == False
        assert executor_with_fallback.fallback_graph is not None
    
    def test_get_thread(self, executor_with_fallback):
        """Test thread configuration generation."""
        task_id = "test-task-123"
        thread = executor_with_fallback.get_thread(task_id)
        
        assert thread == {"configurable": {"thread_id": task_id}}
    
    @patch('src.dev_pilot.graph.agentic_executor.flush_redis_cache')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_start_workflow_fallback(self, mock_save, mock_flush, executor_with_fallback):
        """Test starting workflow in fallback mode."""
        project_name = "Test Project"
        
        result = executor_with_fallback.start_workflow(project_name)
        
        assert "task_id" in result
        assert result["task_id"].startswith("sdlc-session-")
        assert "state" in result
        mock_flush.assert_called_once()
    
    @patch('src.dev_pilot.graph.agentic_executor.flush_redis_cache')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_start_workflow_creates_initial_state(self, mock_save, mock_flush, mock_llm):
        """Test initial state structure."""
        executor = AgenticGraphExecutor(
            llm=mock_llm,
            use_agents=False,
            fallback_graph=None,
        )
        
        result = executor.start_workflow("Test Project")
        state = result["state"]
        
        assert state["project_name"] == "Test Project"
        assert state["requirements"] == []
        assert state["user_stories"] is None
        assert state["design_documents"] is None
        assert "next_node" in state
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_generate_stories_updates_state(self, mock_save, mock_get, executor_with_fallback):
        """Test generate_stories updates state correctly."""
        task_id = "test-task-123"
        requirements = ["Requirement 1", "Requirement 2"]
        
        mock_get.return_value = {
            "project_name": "Test",
            "requirements": [],
        }
        
        result = executor_with_fallback.generate_stories(task_id, requirements)
        
        assert "task_id" in result
        assert "state" in result
    
    def test_convert_user_stories(self, executor_with_fallback):
        """Test user story conversion."""
        result = {
            "user_stories": [
                {
                    "id": 1,
                    "title": "Story 1",
                    "description": "Description 1",
                    "priority": "High",
                    "acceptance_criteria": "Criteria 1",
                },
                {
                    "id": 2,
                    "title": "Story 2",
                    "description": "Description 2",
                    "priority": "Medium",
                    "acceptance_criteria": "Criteria 2",
                },
            ]
        }
        
        user_stories = executor_with_fallback._convert_user_stories(result)
        
        assert isinstance(user_stories, UserStoryList)
        assert len(user_stories.user_stories) == 2
        assert user_stories.user_stories[0].title == "Story 1"
        assert user_stories.user_stories[1].priority == "Medium"
    
    def test_create_mock_user_stories(self, executor_with_fallback):
        """Test mock user story creation."""
        requirements = ["User login feature", "Dashboard view"]
        
        stories = executor_with_fallback._create_mock_user_stories(requirements)
        
        assert isinstance(stories, UserStoryList)
        assert len(stories.user_stories) == 2
        assert "login" in stories.user_stories[0].description.lower()
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_graph_review_flow_approved(self, mock_save, mock_get, executor_with_fallback):
        """Test review flow with approval."""
        task_id = "test-task-123"
        mock_get.return_value = {
            "project_name": "Test",
            "next_node": const.REVIEW_USER_STORIES,
        }
        
        result = executor_with_fallback.graph_review_flow(
            task_id=task_id,
            status="approved",
            feedback=None,
            review_type=const.REVIEW_USER_STORIES,
        )
        
        assert result["task_id"] == task_id
        assert "state" in result
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_graph_review_flow_feedback(self, mock_save, mock_get, executor_with_fallback):
        """Test review flow with feedback."""
        task_id = "test-task-123"
        mock_get.return_value = {
            "project_name": "Test",
            "next_node": const.REVIEW_USER_STORIES,
        }
        
        result = executor_with_fallback.graph_review_flow(
            task_id=task_id,
            status="feedback",
            feedback="Please improve the stories",
            review_type=const.REVIEW_USER_STORIES,
        )
        
        assert result["task_id"] == task_id
        state = result["state"]
        assert state.get("user_stories_feedback") == "Please improve the stories"
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    def test_get_updated_state(self, mock_get, executor_with_fallback):
        """Test getting updated state."""
        task_id = "test-task-123"
        mock_get.return_value = {"test": "state"}
        
        result = executor_with_fallback.get_updated_state(task_id)
        
        assert result["task_id"] == task_id
        assert result["state"] == {"test": "state"}
    
    def test_get_agent_status_no_agents(self, executor_with_fallback):
        """Test agent status when not using agents."""
        status = executor_with_fallback.get_agent_status()
        
        assert status["agents"] == {}
        assert status["use_agents"] == False
    
    def test_is_using_agents_false(self, executor_with_fallback):
        """Test is_using_agents returns False in fallback mode."""
        assert executor_with_fallback.is_using_agents() == False
    
    def test_get_session_info_empty(self, executor_with_fallback):
        """Test session info for non-existent task."""
        info = executor_with_fallback.get_session_info("non-existent")
        assert info is None


class TestAgentMapping:
    """Test agent mapping configurations."""
    
    @pytest.fixture
    def executor(self):
        mock_llm = Mock()
        return AgenticGraphExecutor(llm=mock_llm, use_agents=False)
    
    def test_get_next_agent_after_user_stories(self, executor):
        """Test next agent after user stories review."""
        next_agent = executor._get_next_agent(const.REVIEW_USER_STORIES)
        
        assert next_agent is not None
        assert next_agent["agent"] == "architect"
        assert next_agent["task"] == "create_design_document"
    
    def test_get_next_agent_after_design(self, executor):
        """Test next agent after design review."""
        next_agent = executor._get_next_agent(const.REVIEW_DESIGN_DOCUMENTS)
        
        assert next_agent is not None
        assert next_agent["agent"] == "developer"
    
    def test_get_next_agent_after_code(self, executor):
        """Test next agent after code review."""
        next_agent = executor._get_next_agent(const.REVIEW_CODE)
        
        assert next_agent is not None
        assert next_agent["agent"] == "security"
    
    def test_get_next_agent_after_security(self, executor):
        """Test next agent after security review."""
        next_agent = executor._get_next_agent(const.REVIEW_SECURITY_RECOMMENDATIONS)
        
        assert next_agent is not None
        assert next_agent["agent"] == "qa"
    
    def test_get_next_agent_after_test_cases(self, executor):
        """Test next agent after test cases review."""
        next_agent = executor._get_next_agent(const.REVIEW_TEST_CASES)
        
        assert next_agent is not None
        assert next_agent["agent"] == "qa"
        assert next_agent["task"] == "qa_testing"
    
    def test_get_next_agent_after_qa(self, executor):
        """Test next agent after QA review."""
        next_agent = executor._get_next_agent(const.REVIEW_QA_TESTING)
        
        assert next_agent is not None
        assert next_agent["agent"] == "devops"


class TestReviewTypes:
    """Test all review type mappings."""
    
    @pytest.fixture
    def executor(self):
        mock_llm = Mock()
        return AgenticGraphExecutor(llm=mock_llm, use_agents=False)
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    @patch('src.dev_pilot.graph.agentic_executor.save_state_to_redis')
    def test_all_review_types_valid(self, mock_save, mock_get, executor):
        """Test all review types are handled."""
        review_types = [
            const.REVIEW_USER_STORIES,
            const.REVIEW_DESIGN_DOCUMENTS,
            const.REVIEW_CODE,
            const.REVIEW_SECURITY_RECOMMENDATIONS,
            const.REVIEW_TEST_CASES,
            const.REVIEW_QA_TESTING,
        ]
        
        mock_get.return_value = {"project_name": "Test"}
        
        for review_type in review_types:
            result = executor.graph_review_flow(
                task_id="test",
                status="approved",
                feedback=None,
                review_type=review_type,
            )
            assert "task_id" in result
    
    @patch('src.dev_pilot.graph.agentic_executor.get_state_from_redis')
    def test_invalid_review_type_raises(self, mock_get, executor):
        """Test invalid review type raises error."""
        mock_get.return_value = {"project_name": "Test"}
        
        with pytest.raises(ValueError, match="Unsupported review type"):
            executor.graph_review_flow(
                task_id="test",
                status="approved",
                feedback=None,
                review_type="invalid_review_type",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
