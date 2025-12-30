"""
Unit tests for Agent Components

Tests the base agent infrastructure, message passing, and registry.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dev_pilot.agents.agent_message import (
    AgentMessage,
    AgentTask,
    MessageType,
    MessagePriority,
    TaskStatus,
)
from src.dev_pilot.agents.agent_registry import AgentRegistry, get_registry
from src.dev_pilot.orchestration.message_bus import InMemoryMessageBus
from src.dev_pilot.orchestration.task_queue import InMemoryTaskQueue
from src.dev_pilot.memory.context_manager import ContextManager, ProjectContext
from src.dev_pilot.memory.conversation_history import ConversationHistory, MessageRole


class TestAgentMessage:
    """Test AgentMessage dataclass."""
    
    def test_create_message(self):
        """Test creating an agent message."""
        message = AgentMessage(
            message_id="msg-001",
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,
            content={"task": "generate_stories"},
            timestamp=datetime.utcnow(),
        )
        
        assert message.message_id == "msg-001"
        assert message.sender_id == "agent-1"
        assert message.message_type == MessageType.REQUEST
    
    def test_message_priority_default(self):
        """Test default message priority."""
        message = AgentMessage(
            message_id="msg-001",
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,
            content={},
            timestamp=datetime.utcnow(),
        )
        
        assert message.priority == MessagePriority.NORMAL
    
    def test_message_to_dict(self):
        """Test message serialization."""
        message = AgentMessage(
            message_id="msg-001",
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,
            content={"test": "data"},
            timestamp=datetime.utcnow(),
        )
        
        data = message.to_dict()
        
        assert data["message_id"] == "msg-001"
        assert data["sender_id"] == "agent-1"
        assert data["content"] == {"test": "data"}
    
    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "message_id": "msg-001",
            "sender_id": "agent-1",
            "receiver_id": "agent-2",
            "message_type": "request",
            "content": {"test": "data"},
            "timestamp": datetime.utcnow().isoformat(),
            "priority": "normal",
            "correlation_id": None,
            "metadata": {},
        }
        
        message = AgentMessage.from_dict(data)
        
        assert message.message_id == "msg-001"
        assert message.message_type == MessageType.REQUEST


class TestAgentTask:
    """Test AgentTask dataclass."""
    
    def test_create_task(self):
        """Test creating an agent task."""
        task = AgentTask.create(
            task_type="generate_user_stories",
            input_data={"requirements": ["req1", "req2"]},
            assigned_agent="ba-agent",
        )
        
        assert task.task_type == "generate_user_stories"
        assert task.status == TaskStatus.PENDING
        assert "requirements" in task.input_data
    
    def test_task_id_generated(self):
        """Test task ID is auto-generated."""
        task = AgentTask.create(
            task_type="test_task",
            input_data={},
        )
        
        assert task.task_id is not None
        assert task.task_id.startswith("task-")
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = AgentTask.create(
            task_type="test_task",
            input_data={"key": "value"},
        )
        
        data = task.to_dict()
        
        assert data["task_type"] == "test_task"
        assert data["status"] == "pending"
        assert data["input_data"] == {"key": "value"}


class TestMessageTypes:
    """Test message type enumeration."""
    
    def test_message_types_exist(self):
        """Test all message types exist."""
        assert MessageType.REQUEST is not None
        assert MessageType.RESPONSE is not None
        assert MessageType.NOTIFICATION is not None
        assert MessageType.ERROR is not None
        assert MessageType.STATUS_UPDATE is not None
    
    def test_message_type_values(self):
        """Test message type string values."""
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.ERROR.value == "error"


class TestMessagePriority:
    """Test message priority enumeration."""
    
    def test_priority_ordering(self):
        """Test priority values are ordered correctly."""
        assert MessagePriority.LOW.value < MessagePriority.NORMAL.value
        assert MessagePriority.NORMAL.value < MessagePriority.HIGH.value
        assert MessagePriority.HIGH.value < MessagePriority.CRITICAL.value


class TestAgentRegistry:
    """Test AgentRegistry singleton."""
    
    def test_registry_singleton(self):
        """Test registry is a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2
    
    def test_registry_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        
        mock_agent = Mock()
        mock_agent.agent_id = "test-agent-1"
        mock_agent.agent_type = "test"
        mock_agent.state = Mock()
        mock_agent.state.value = "idle"
        
        registry.register(mock_agent)
        
        assert "test-agent-1" in registry._agents
    
    def test_registry_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        
        mock_agent = Mock()
        mock_agent.agent_id = "test-agent-2"
        mock_agent.agent_type = "test"
        mock_agent.state = Mock()
        mock_agent.state.value = "idle"
        
        registry.register(mock_agent)
        registry.unregister("test-agent-2")
        
        assert "test-agent-2" not in registry._agents
    
    def test_registry_get_agent(self):
        """Test getting an agent by ID."""
        registry = AgentRegistry()
        
        mock_agent = Mock()
        mock_agent.agent_id = "test-agent-3"
        mock_agent.agent_type = "test"
        mock_agent.state = Mock()
        mock_agent.state.value = "idle"
        
        registry.register(mock_agent)
        
        result = registry.get_agent("test-agent-3")
        assert result == mock_agent
    
    def test_registry_get_agents_by_type(self):
        """Test getting agents by type."""
        registry = AgentRegistry()
        
        for i in range(3):
            mock_agent = Mock()
            mock_agent.agent_id = f"ba-agent-{i}"
            mock_agent.agent_type = "business_analyst"
            mock_agent.state = Mock()
            mock_agent.state.value = "idle"
            registry.register(mock_agent)
        
        agents = registry.get_agents_by_type("business_analyst")
        assert len(agents) >= 3


class TestInMemoryMessageBus:
    """Test InMemoryMessageBus."""
    
    @pytest.fixture
    def message_bus(self):
        """Create message bus for testing."""
        return InMemoryMessageBus()
    
    @pytest.mark.asyncio
    async def test_start_stop(self, message_bus):
        """Test starting and stopping message bus."""
        await message_bus.start()
        assert message_bus._running == True
        
        await message_bus.stop()
        assert message_bus._running == False
    
    @pytest.mark.asyncio
    async def test_subscribe_publish(self, message_bus):
        """Test subscribe and publish."""
        await message_bus.start()
        
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        await message_bus.subscribe("test-topic", handler)
        await message_bus.publish("test-topic", {"test": "data"})
        
        # Give time for async processing
        await asyncio.sleep(0.1)
        
        await message_bus.stop()
        
        assert len(received_messages) == 1
        assert received_messages[0] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, message_bus):
        """Test unsubscribe."""
        await message_bus.start()
        
        async def handler(message):
            pass
        
        await message_bus.subscribe("test-topic", handler)
        await message_bus.unsubscribe("test-topic", handler)
        
        assert handler not in message_bus._subscribers.get("test-topic", [])
        
        await message_bus.stop()
    
    def test_get_metrics(self, message_bus):
        """Test getting metrics."""
        metrics = message_bus.get_metrics()
        
        assert "messages_published" in metrics
        assert "subscribers_count" in metrics


class TestInMemoryTaskQueue:
    """Test InMemoryTaskQueue."""
    
    @pytest.fixture
    def task_queue(self):
        """Create task queue for testing."""
        return InMemoryTaskQueue()
    
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, task_queue):
        """Test enqueue and dequeue."""
        task = AgentTask.create(
            task_type="test",
            input_data={},
        )
        
        await task_queue.enqueue(task)
        
        result = await task_queue.dequeue()
        
        assert result.task_id == task.task_id
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, task_queue):
        """Test tasks are dequeued by priority."""
        low_task = AgentTask.create(task_type="low", input_data={})
        low_task.priority = MessagePriority.LOW
        
        high_task = AgentTask.create(task_type="high", input_data={})
        high_task.priority = MessagePriority.HIGH
        
        # Enqueue low first, then high
        await task_queue.enqueue(low_task)
        await task_queue.enqueue(high_task)
        
        # High priority should come out first
        first = await task_queue.dequeue()
        assert first.task_type == "high"
    
    @pytest.mark.asyncio
    async def test_queue_size(self, task_queue):
        """Test queue size tracking."""
        assert await task_queue.size() == 0
        
        task = AgentTask.create(task_type="test", input_data={})
        await task_queue.enqueue(task)
        
        assert await task_queue.size() == 1


class TestContextManager:
    """Test ContextManager."""
    
    @pytest.fixture
    def context_manager(self):
        """Create context manager for testing."""
        return ContextManager(storage_backend="memory")
    
    @pytest.mark.asyncio
    async def test_create_project_context(self, context_manager):
        """Test creating project context."""
        context = await context_manager.create_project_context(
            project_id="proj-001",
            project_name="Test Project",
            requirements=["req1"],
        )
        
        assert context.project_id == "proj-001"
        assert context.project_name == "Test Project"
    
    @pytest.mark.asyncio
    async def test_get_project_context(self, context_manager):
        """Test getting project context."""
        await context_manager.create_project_context(
            project_id="proj-002",
            project_name="Test",
        )
        
        context = await context_manager.get_project_context("proj-002")
        
        assert context is not None
        assert context.project_id == "proj-002"
    
    @pytest.mark.asyncio
    async def test_update_project_context(self, context_manager):
        """Test updating project context."""
        await context_manager.create_project_context(
            project_id="proj-003",
            project_name="Test",
        )
        
        updated = await context_manager.update_project_context(
            "proj-003",
            current_phase="design",
        )
        
        assert updated.current_phase == "design"


class TestConversationHistory:
    """Test ConversationHistory."""
    
    def test_create_history(self):
        """Test creating conversation history."""
        history = ConversationHistory(project_id="proj-001")
        
        assert history.project_id == "proj-001"
        assert len(history.messages) == 0
    
    def test_add_message(self):
        """Test adding messages."""
        history = ConversationHistory(project_id="proj-001")
        
        history.add_user_message("Hello")
        history.add_assistant_message("Hi there")
        history.add_system_message("System initialized")
        
        assert len(history.messages) == 3
    
    def test_get_recent_messages(self):
        """Test getting recent messages."""
        history = ConversationHistory(project_id="proj-001")
        
        for i in range(10):
            history.add_user_message(f"Message {i}")
        
        recent = history.get_recent_messages(5)
        
        assert len(recent) == 5
        assert "Message 9" in recent[-1].content
    
    def test_clear_history(self):
        """Test clearing history."""
        history = ConversationHistory(project_id="proj-001")
        
        history.add_user_message("Test")
        history.clear()
        
        assert len(history.messages) == 0


class TestProjectContext:
    """Test ProjectContext dataclass."""
    
    def test_create_context(self):
        """Test creating project context."""
        context = ProjectContext(
            project_id="proj-001",
            project_name="Test Project",
        )
        
        assert context.project_id == "proj-001"
        assert context.artifacts == {}
    
    def test_context_to_dict(self):
        """Test context serialization."""
        context = ProjectContext(
            project_id="proj-001",
            project_name="Test",
            requirements=["req1", "req2"],
        )
        
        data = context.to_dict()
        
        assert data["project_id"] == "proj-001"
        assert len(data["requirements"]) == 2
    
    def test_context_from_dict(self):
        """Test context deserialization."""
        data = {
            "project_id": "proj-001",
            "project_name": "Test",
            "requirements": ["req1"],
            "current_phase": "design",
            "artifacts": {},
            "metadata": {},
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        context = ProjectContext.from_dict(data)
        
        assert context.project_id == "proj-001"
        assert context.current_phase == "design"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
