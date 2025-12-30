"""
Conversation History Module

Tracks conversation history for agents and projects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import json
from loguru import logger


class MessageRole(Enum):
    """Role of the message sender."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a single message in conversation history."""
    role: MessageRole
    content: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            agent_id=data.get("agent_id"),
            agent_name=data.get("agent_name"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )


class ConversationHistory:
    """
    Manages conversation history for a project or session.
    
    Provides:
    - Message storage and retrieval
    - Agent conversation tracking
    - History export
    """
    
    def __init__(self, project_id: str, max_messages: int = 1000):
        self.project_id = project_id
        self.max_messages = max_messages
        self._messages: List[Message] = []
        self._agent_messages: Dict[str, List[Message]] = {}
        
    def add_message(
        self,
        role: MessageRole,
        content: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to history."""
        message = Message(
            role=role,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        
        self._messages.append(message)
        
        # Track by agent
        if agent_id:
            if agent_id not in self._agent_messages:
                self._agent_messages[agent_id] = []
            self._agent_messages[agent_id].append(message)
        
        # Trim if exceeds max
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]
        
        return message
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add a user message."""
        return self.add_message(MessageRole.USER, content, metadata=metadata)
    
    def add_agent_message(
        self,
        content: str,
        agent_id: str,
        agent_name: str,
        metadata: Optional[Dict] = None,
    ) -> Message:
        """Add an agent message."""
        return self.add_message(
            MessageRole.AGENT,
            content,
            agent_id=agent_id,
            agent_name=agent_name,
            metadata=metadata,
        )
    
    def add_system_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add a system message."""
        return self.add_message(MessageRole.SYSTEM, content, metadata=metadata)
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get all messages, optionally limited."""
        if limit:
            return self._messages[-limit:]
        return self._messages.copy()
    
    def get_agent_messages(self, agent_id: str) -> List[Message]:
        """Get messages from a specific agent."""
        return self._agent_messages.get(agent_id, []).copy()
    
    def get_recent_context(self, num_messages: int = 10) -> str:
        """Get recent messages as context string."""
        recent = self._messages[-num_messages:]
        lines = []
        for msg in recent:
            prefix = msg.agent_name or msg.role.value.title()
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)
    
    def clear(self):
        """Clear all history."""
        self._messages.clear()
        self._agent_messages.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "project_id": self.project_id,
            "messages": [m.to_dict() for m in self._messages],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationHistory":
        """Import from dictionary."""
        history = cls(project_id=data["project_id"])
        for msg_data in data.get("messages", []):
            msg = Message.from_dict(msg_data)
            history._messages.append(msg)
            if msg.agent_id:
                if msg.agent_id not in history._agent_messages:
                    history._agent_messages[msg.agent_id] = []
                history._agent_messages[msg.agent_id].append(msg)
        return history
    
    def export_markdown(self) -> str:
        """Export history as Markdown."""
        lines = [f"# Conversation History - {self.project_id}\n"]
        
        for msg in self._messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            sender = msg.agent_name or msg.role.value.title()
            lines.append(f"## [{timestamp}] {sender}\n")
            lines.append(f"{msg.content}\n")
            lines.append("---\n")
        
        return "\n".join(lines)
    
    def __len__(self) -> int:
        return len(self._messages)
