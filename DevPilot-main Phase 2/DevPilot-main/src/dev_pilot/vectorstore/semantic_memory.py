"""
Semantic Memory Module

Provides semantic memory storage and retrieval for agents.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

from loguru import logger

from src.dev_pilot.vectorstore.chroma_store import (
    VectorStore,
    VectorDocument,
    SearchResult,
    CollectionType,
    get_vector_store,
)


class MemoryType(Enum):
    """Types of semantic memory."""
    EPISODIC = "episodic"  # Specific events/interactions
    SEMANTIC = "semantic"  # General knowledge/facts
    PROCEDURAL = "procedural"  # How to do things
    WORKING = "working"  # Current task context


@dataclass
class Memory:
    """Represents a memory item."""
    id: str
    content: str
    memory_type: MemoryType
    importance: float  # 0.0 to 1.0
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            importance=data.get("importance", 0.5),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            metadata=data.get("metadata", {}),
            agent_id=data.get("agent_id"),
            project_id=data.get("project_id"),
            task_id=data.get("task_id"),
            tags=data.get("tags", []),
        )


@dataclass
class RetrievedMemory:
    """A memory retrieved with relevance score."""
    memory: Memory
    relevance_score: float  # 0.0 to 1.0 (higher is more relevant)
    
    def __repr__(self) -> str:
        return f"<RetrievedMemory score={self.relevance_score:.2f} content='{self.memory.content[:50]}...'>"


class SemanticMemory:
    """
    Semantic memory system for agents.
    
    Provides:
    - Long-term memory storage with vector embeddings
    - Semantic similarity search
    - Memory importance ranking
    - Memory consolidation
    - Context-aware retrieval
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        max_memories_per_query: int = 10,
        relevance_threshold: float = 0.3,
    ):
        """
        Initialize semantic memory.
        
        Args:
            vector_store: Vector store instance
            max_memories_per_query: Maximum memories to retrieve
            relevance_threshold: Minimum relevance score (0.0-1.0)
        """
        self.vector_store = vector_store or get_vector_store()
        self.max_memories_per_query = max_memories_per_query
        self.relevance_threshold = relevance_threshold
    
    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: float = 0.5,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """
        Store a new memory.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score (0.0-1.0)
            agent_id: Associated agent ID
            project_id: Associated project ID
            task_id: Associated task ID
            tags: Tags for categorization
            metadata: Additional metadata
            
        Returns:
            Created Memory object
        """
        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
            agent_id=agent_id,
            project_id=project_id,
            task_id=task_id,
            tags=tags or [],
        )
        
        # Store in vector store
        vector_metadata = {
            "memory_type": memory_type.value,
            "importance": importance,
            "agent_id": agent_id or "",
            "task_id": task_id or "",
            "tags": json.dumps(tags or []),
            "created_at": memory.created_at.isoformat(),
        }
        
        self.vector_store.add_document(
            collection_type=CollectionType.AGENT_MEMORY,
            content=content,
            metadata=vector_metadata,
            doc_id=memory.id,
            project_id=project_id,
        )
        
        logger.debug(f"Stored memory {memory.id} with importance {importance}")
        return memory
    
    def retrieve(
        self,
        query: str,
        n_results: Optional[int] = None,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        min_importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> List[RetrievedMemory]:
        """
        Retrieve relevant memories.
        
        Args:
            query: Search query
            n_results: Number of results (default: max_memories_per_query)
            project_id: Filter by project
            agent_id: Filter by agent
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            tags: Filter by tags
            
        Returns:
            List of retrieved memories with relevance scores
        """
        n_results = n_results or self.max_memories_per_query
        
        # Build metadata filter
        filter_metadata = {}
        if agent_id:
            filter_metadata["agent_id"] = agent_id
        if memory_type:
            filter_metadata["memory_type"] = memory_type.value
        
        # Search vector store
        results = self.vector_store.search(
            collection_type=CollectionType.AGENT_MEMORY,
            query=query,
            n_results=n_results * 2,  # Get more for filtering
            project_id=project_id,
            filter_metadata=filter_metadata if filter_metadata else None,
        )
        
        # Convert to RetrievedMemory and apply additional filters
        retrieved = []
        for result in results:
            # Calculate relevance score (invert distance, normalize to 0-1)
            relevance = max(0, 1 - result.score)
            
            # Apply relevance threshold
            if relevance < self.relevance_threshold:
                continue
            
            # Check importance filter
            importance = result.metadata.get("importance", 0.5)
            if min_importance and importance < min_importance:
                continue
            
            # Check tags filter
            if tags:
                memory_tags = json.loads(result.metadata.get("tags", "[]"))
                if not any(tag in memory_tags for tag in tags):
                    continue
            
            # Create Memory object
            memory = Memory(
                id=result.id,
                content=result.content,
                memory_type=MemoryType(result.metadata.get("memory_type", "episodic")),
                importance=importance,
                created_at=datetime.fromisoformat(result.metadata.get("created_at", datetime.utcnow().isoformat())),
                metadata=result.metadata,
                agent_id=result.metadata.get("agent_id") or None,
                project_id=project_id,
                task_id=result.metadata.get("task_id") or None,
                tags=json.loads(result.metadata.get("tags", "[]")),
            )
            
            retrieved.append(RetrievedMemory(
                memory=memory,
                relevance_score=relevance,
            ))
        
        # Sort by combined relevance and importance
        retrieved.sort(
            key=lambda x: x.relevance_score * 0.7 + x.memory.importance * 0.3,
            reverse=True,
        )
        
        return retrieved[:n_results]
    
    def get_context(
        self,
        query: str,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        Get formatted context from relevant memories.
        
        Args:
            query: Search query
            project_id: Project ID
            agent_id: Agent ID
            max_tokens: Maximum tokens (approximate)
            
        Returns:
            Formatted context string
        """
        memories = self.retrieve(
            query=query,
            project_id=project_id,
            agent_id=agent_id,
            n_results=20,
        )
        
        if not memories:
            return ""
        
        # Build context string
        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4  # Approximate chars per token
        
        for rm in memories:
            memory_text = f"[{rm.memory.memory_type.value.upper()}] {rm.memory.content}"
            
            if total_chars + len(memory_text) > char_limit:
                break
            
            context_parts.append(memory_text)
            total_chars += len(memory_text)
        
        return "\n\n".join(context_parts)
    
    def update_importance(
        self,
        memory_id: str,
        importance: float,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Update memory importance score.
        
        Args:
            memory_id: Memory ID
            importance: New importance score
            project_id: Project ID
            
        Returns:
            True if updated successfully
        """
        return self.vector_store.update_document(
            collection_type=CollectionType.AGENT_MEMORY,
            doc_id=memory_id,
            metadata={"importance": importance},
            project_id=project_id,
        )
    
    def forget(
        self,
        memory_id: str,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: Memory ID
            project_id: Project ID
            
        Returns:
            True if deleted successfully
        """
        return self.vector_store.delete_document(
            collection_type=CollectionType.AGENT_MEMORY,
            doc_id=memory_id,
            project_id=project_id,
        )
    
    def consolidate(
        self,
        project_id: Optional[str] = None,
        min_memories: int = 10,
        similarity_threshold: float = 0.9,
    ) -> int:
        """
        Consolidate similar memories.
        
        Merges very similar memories to reduce redundancy.
        
        Args:
            project_id: Project ID
            min_memories: Minimum memories before consolidation
            similarity_threshold: Threshold for considering memories similar
            
        Returns:
            Number of memories consolidated
        """
        # This is a simplified implementation
        # A full implementation would cluster similar memories
        logger.info("Memory consolidation not yet fully implemented")
        return 0
    
    def get_stats(
        self,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Args:
            project_id: Project ID
            
        Returns:
            Statistics dictionary
        """
        stats = self.vector_store.get_collection_stats(
            collection_type=CollectionType.AGENT_MEMORY,
            project_id=project_id,
        )
        
        return {
            "total_memories": stats.get("count", 0),
            "collection_name": stats.get("name"),
        }


class ConversationMemory:
    """
    Short-term conversation memory.
    
    Manages conversation history with automatic summarization.
    """
    
    def __init__(
        self,
        semantic_memory: Optional[SemanticMemory] = None,
        max_turns: int = 20,
        summarize_after: int = 10,
    ):
        """
        Initialize conversation memory.
        
        Args:
            semantic_memory: Semantic memory for long-term storage
            max_turns: Maximum conversation turns to keep
            summarize_after: Summarize after this many turns
        """
        self.semantic_memory = semantic_memory or SemanticMemory()
        self.max_turns = max_turns
        self.summarize_after = summarize_after
        
        # In-memory conversation storage
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        self._summaries: Dict[str, str] = {}
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        self._conversations[conversation_id].append(message)
        
        # Trim if over max turns
        if len(self._conversations[conversation_id]) > self.max_turns:
            # Store older messages to semantic memory
            old_messages = self._conversations[conversation_id][:-self.max_turns]
            self._archive_messages(conversation_id, old_messages)
            self._conversations[conversation_id] = self._conversations[conversation_id][-self.max_turns:]
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation messages.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        messages = self._conversations.get(conversation_id, [])
        if limit:
            messages = messages[-limit:]
        return messages
    
    def get_context(
        self,
        conversation_id: str,
        include_summary: bool = True,
    ) -> str:
        """
        Get conversation context as formatted string.
        
        Args:
            conversation_id: Conversation ID
            include_summary: Include summary of older messages
            
        Returns:
            Formatted context string
        """
        parts = []
        
        # Add summary if available
        if include_summary and conversation_id in self._summaries:
            parts.append(f"[Previous conversation summary]\n{self._summaries[conversation_id]}\n")
        
        # Add recent messages
        messages = self.get_messages(conversation_id)
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            parts.append(f"{role}: {content}")
        
        return "\n".join(parts)
    
    def clear(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
        if conversation_id in self._summaries:
            del self._summaries[conversation_id]
    
    def _archive_messages(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
    ) -> None:
        """Archive old messages to semantic memory."""
        if not messages:
            return
        
        # Create a combined memory of the archived messages
        combined_content = "\n".join([
            f"{m['role']}: {m['content']}" for m in messages
        ])
        
        self.semantic_memory.store(
            content=f"Conversation history from {conversation_id}:\n{combined_content}",
            memory_type=MemoryType.EPISODIC,
            importance=0.3,
            metadata={"conversation_id": conversation_id, "archived": True},
        )


# Global semantic memory instance
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Get or create global semantic memory instance."""
    global _semantic_memory
    
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    
    return _semantic_memory
