"""
DevPilot Vector Store Module

Provides vector storage, embeddings, and semantic memory capabilities.
"""

from src.dev_pilot.vectorstore.chroma_store import (
    VectorStore,
    VectorStoreConfig,
    VectorDocument,
    SearchResult,
    CollectionType,
    get_vector_store,
)
from src.dev_pilot.vectorstore.embeddings import (
    EmbeddingService,
    EmbeddingProvider,
    EmbeddingResult,
    BaseEmbedding,
    SentenceTransformerEmbedding,
    OpenAIEmbedding,
    GoogleEmbedding,
    get_embedding_service,
)
from src.dev_pilot.vectorstore.semantic_memory import (
    SemanticMemory,
    ConversationMemory,
    Memory,
    MemoryType,
    RetrievedMemory,
    get_semantic_memory,
)


__all__ = [
    # Vector Store
    "VectorStore",
    "VectorStoreConfig",
    "VectorDocument",
    "SearchResult",
    "CollectionType",
    "get_vector_store",
    # Embeddings
    "EmbeddingService",
    "EmbeddingProvider",
    "EmbeddingResult",
    "BaseEmbedding",
    "SentenceTransformerEmbedding",
    "OpenAIEmbedding",
    "GoogleEmbedding",
    "get_embedding_service",
    # Semantic Memory
    "SemanticMemory",
    "ConversationMemory",
    "Memory",
    "MemoryType",
    "RetrievedMemory",
    "get_semantic_memory",
]
