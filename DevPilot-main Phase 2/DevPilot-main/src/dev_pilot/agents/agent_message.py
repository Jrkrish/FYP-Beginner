"""
Agent Message Module

Defines the communication protocol between agents in the DevPilot system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid
import json


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""
    REQUEST = "request"          # Request an agent to perform a task
    RESPONSE = "response"        # Response to a request
    NOTIFY = "notify"            # Notification (no response expected)
    DELEGATE = "delegate"        # Delegate a task to another agent
    ERROR = "error"              # Error message
    STATUS = "status"            # Status update
    HANDOFF = "handoff"          # Handoff control to another agent
    BROADCAST = "broadcast"      # Broadcast to all agents


class MessagePriority(Enum):
    """Priority levels for messages."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class AgentMessage:
    """
    Represents a message exchanged between agents.
    
    Attributes:
        sender: The ID of the agent sending the message
        recipient: The ID of the receiving agent (or "BROADCAST" for all)
        message_type: The type of message
        payload: The actual message content
        priority: Message priority level
        context: Shared context data
        correlation_id: ID for tracking request-response pairs
        parent_id: ID of the parent message (for threading)
        timestamp: When the message was created
        metadata: Additional metadata
    """
    sender: str
    recipient: str
    message_type: MessageType
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    context: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and process message after initialization."""
        if isinstance(self.message_type, str):
            self.message_type = MessageType(self.message_type)
        if isinstance(self.priority, int):
            self.priority = MessagePriority(self.priority)
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=MessagePriority(data.get("priority", 3)),
            context=data.get("context", {}),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """Deserialize message from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def create_response(
        self, 
        sender: str, 
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.RESPONSE
    ) -> "AgentMessage":
        """Create a response message to this message."""
        return AgentMessage(
            sender=sender,
            recipient=self.sender,
            message_type=message_type,
            payload=payload,
            priority=self.priority,
            context=self.context,
            correlation_id=self.correlation_id,
            parent_id=self.correlation_id,
            metadata={"in_response_to": self.correlation_id},
        )
    
    def create_error_response(
        self,
        sender: str,
        error_message: str,
        error_code: Optional[str] = None
    ) -> "AgentMessage":
        """Create an error response to this message."""
        return AgentMessage(
            sender=sender,
            recipient=self.sender,
            message_type=MessageType.ERROR,
            payload={
                "error": error_message,
                "error_code": error_code,
                "original_payload": self.payload,
            },
            priority=MessagePriority.HIGH,
            context=self.context,
            correlation_id=self.correlation_id,
            parent_id=self.correlation_id,
        )
    
    @staticmethod
    def create_request(
        sender: str,
        recipient: str,
        action: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> "AgentMessage":
        """Factory method to create a request message."""
        return AgentMessage(
            sender=sender,
            recipient=recipient,
            message_type=MessageType.REQUEST,
            payload={"action": action, "data": data},
            priority=priority,
            context=context or {},
        )
    
    @staticmethod
    def create_notification(
        sender: str,
        recipient: str,
        event: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> "AgentMessage":
        """Factory method to create a notification message."""
        return AgentMessage(
            sender=sender,
            recipient=recipient,
            message_type=MessageType.NOTIFY,
            payload={"event": event, "data": data},
            priority=MessagePriority.LOW,
            context=context or {},
        )
    
    @staticmethod
    def create_broadcast(
        sender: str,
        event: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> "AgentMessage":
        """Factory method to create a broadcast message to all agents."""
        return AgentMessage(
            sender=sender,
            recipient="BROADCAST",
            message_type=MessageType.BROADCAST,
            payload={"event": event, "data": data},
            priority=MessagePriority.NORMAL,
            context=context or {},
        )


@dataclass
class AgentTask:
    """
    Represents a task assigned to an agent.
    
    Attributes:
        task_id: Unique task identifier
        task_type: Type of task to perform
        input_data: Input data for the task
        assigned_agent: The agent assigned to this task
        status: Current task status
        result: Task result (when completed)
        created_at: When the task was created
        started_at: When the task was started
        completed_at: When the task was completed
        parent_task_id: ID of parent task (for subtasks)
        dependencies: List of task IDs this task depends on
    """
    task_id: str
    task_type: str
    input_data: Dict[str, Any]
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed, blocked
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    dependencies: list = field(default_factory=list)
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def create(
        task_type: str,
        input_data: Dict[str, Any],
        assigned_agent: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        dependencies: Optional[list] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> "AgentTask":
        """Factory method to create a new task."""
        return AgentTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            input_data=input_data,
            assigned_agent=assigned_agent,
            parent_task_id=parent_task_id,
            dependencies=dependencies or [],
            priority=priority,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "input_data": self.input_data,
            "assigned_agent": self.assigned_agent,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_task_id": self.parent_task_id,
            "dependencies": self.dependencies,
            "priority": self.priority.value,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTask":
        """Create task from dictionary."""
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            input_data=data["input_data"],
            assigned_agent=data.get("assigned_agent"),
            status=data.get("status", "pending"),
            result=data.get("result"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            parent_task_id=data.get("parent_task_id"),
            dependencies=data.get("dependencies", []),
            priority=MessagePriority(data.get("priority", 3)),
            metadata=data.get("metadata", {}),
        )
    
    def mark_started(self):
        """Mark task as started."""
        self.status = "running"
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, result: Dict[str, Any]):
        """Mark task as completed with result."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = datetime.utcnow()
    
    def mark_blocked(self, reason: str):
        """Mark task as blocked."""
        self.status = "blocked"
        self.metadata["blocked_reason"] = reason
