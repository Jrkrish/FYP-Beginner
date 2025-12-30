"""
Vector Store Module

Provides vector storage and semantic search using ChromaDB.
"""

import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from loguru import logger


class CollectionType(Enum):
    """Vector collection types."""
    REQUIREMENTS = "requirements"
    USER_STORIES = "user_stories"
    DESIGN_DOCS = "design_docs"
    CODE = "code"
    TEST_CASES = "test_cases"
    CONVERSATIONS = "conversations"
    AGENT_MEMORY = "agent_memory"


@dataclass
class VectorDocument:
    """Represents a document for vector storage."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Represents a search result."""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # Distance score (lower is more similar)


class VectorStoreConfig:
    """Configuration for vector store."""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: str = "all-MiniLM-L6-v2",
        use_openai_embeddings: bool = False,
        openai_api_key: Optional[str] = None,
        collection_prefix: str = "devpilot",
    ):
        """
        Initialize vector store configuration.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            embedding_model: Sentence transformer model for embeddings
            use_openai_embeddings: Use OpenAI embeddings instead of local
            openai_api_key: OpenAI API key (required if use_openai_embeddings)
            collection_prefix: Prefix for collection names
        """
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self.use_openai_embeddings = use_openai_embeddings
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.collection_prefix = collection_prefix
    
    @classmethod
    def from_env(cls) -> "VectorStoreConfig":
        """Create config from environment variables."""
        return cls(
            persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            use_openai_embeddings=os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            collection_prefix=os.getenv("CHROMA_COLLECTION_PREFIX", "devpilot"),
        )


class VectorStore:
    """
    Vector store for semantic memory using ChromaDB.
    
    Provides:
    - Document storage with embeddings
    - Semantic similarity search
    - Project-scoped collections
    - Multiple collection types for different artifacts
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Initialize vector store.
        
        Args:
            config: Vector store configuration
        """
        self.config = config or VectorStoreConfig.from_env()
        
        # Initialize ChromaDB client
        self._client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.config.persist_directory,
            anonymized_telemetry=False,
        ))
        
        # Initialize embedding function
        self._embedding_fn = self._create_embedding_function()
        
        # Cache for collections
        self._collections: Dict[str, chromadb.Collection] = {}
        
        logger.info(f"VectorStore initialized with persist_directory={self.config.persist_directory}")
    
    def _create_embedding_function(self):
        """Create the embedding function based on config."""
        if self.config.use_openai_embeddings and self.config.openai_api_key:
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.config.openai_api_key,
                model_name="text-embedding-ada-002",
            )
        else:
            # Use local sentence transformer
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.config.embedding_model,
            )
    
    def _get_collection_name(
        self,
        collection_type: CollectionType,
        project_id: Optional[str] = None,
    ) -> str:
        """Generate collection name."""
        base_name = f"{self.config.collection_prefix}_{collection_type.value}"
        if project_id:
            return f"{base_name}_{project_id}"
        return base_name
    
    def get_or_create_collection(
        self,
        collection_type: CollectionType,
        project_id: Optional[str] = None,
    ) -> chromadb.Collection:
        """
        Get or create a collection.
        
        Args:
            collection_type: Type of collection
            project_id: Optional project ID for scoping
            
        Returns:
            ChromaDB collection
        """
        name = self._get_collection_name(collection_type, project_id)
        
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._embedding_fn,
                metadata={"type": collection_type.value, "project_id": project_id or "global"},
            )
        
        return self._collections[name]
    
    def add_document(
        self,
        collection_type: CollectionType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        """
        Add a document to a collection.
        
        Args:
            collection_type: Type of collection
            content: Document content
            metadata: Optional metadata
            doc_id: Optional document ID (auto-generated if not provided)
            project_id: Optional project ID for scoping
            
        Returns:
            Document ID
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        doc_id = doc_id or str(uuid.uuid4())
        metadata = metadata or {}
        metadata["project_id"] = project_id or "global"
        
        collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
        )
        
        logger.debug(f"Added document {doc_id} to collection {collection.name}")
        return doc_id
    
    def add_documents(
        self,
        collection_type: CollectionType,
        documents: List[VectorDocument],
        project_id: Optional[str] = None,
    ) -> List[str]:
        """
        Add multiple documents to a collection.
        
        Args:
            collection_type: Type of collection
            documents: List of documents
            project_id: Optional project ID for scoping
            
        Returns:
            List of document IDs
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        ids = []
        contents = []
        metadatas = []
        
        for doc in documents:
            doc_id = doc.id or str(uuid.uuid4())
            ids.append(doc_id)
            contents.append(doc.content)
            
            metadata = doc.metadata.copy()
            metadata["project_id"] = project_id or "global"
            metadatas.append(metadata)
        
        collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
        )
        
        logger.debug(f"Added {len(ids)} documents to collection {collection.name}")
        return ids
    
    def search(
        self,
        collection_type: CollectionType,
        query: str,
        n_results: int = 5,
        project_id: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            collection_type: Type of collection
            query: Search query
            n_results: Number of results to return
            project_id: Optional project ID for scoping
            filter_metadata: Optional metadata filter
            
        Returns:
            List of search results
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        # Build where clause
        where = None
        if filter_metadata:
            where = filter_metadata
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        
        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append(SearchResult(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=results["distances"][0][i] if results["distances"] else 0.0,
                ))
        
        return search_results
    
    def get_document(
        self,
        collection_type: CollectionType,
        doc_id: str,
        project_id: Optional[str] = None,
    ) -> Optional[VectorDocument]:
        """
        Get a document by ID.
        
        Args:
            collection_type: Type of collection
            doc_id: Document ID
            project_id: Optional project ID for scoping
            
        Returns:
            Document or None
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        results = collection.get(ids=[doc_id])
        
        if results and results["ids"]:
            return VectorDocument(
                id=results["ids"][0],
                content=results["documents"][0] if results["documents"] else "",
                metadata=results["metadatas"][0] if results["metadatas"] else {},
            )
        
        return None
    
    def update_document(
        self,
        collection_type: CollectionType,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Update a document.
        
        Args:
            collection_type: Type of collection
            doc_id: Document ID
            content: New content (optional)
            metadata: New metadata (optional)
            project_id: Optional project ID for scoping
            
        Returns:
            True if updated successfully
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        try:
            update_kwargs = {"ids": [doc_id]}
            if content:
                update_kwargs["documents"] = [content]
            if metadata:
                update_kwargs["metadatas"] = [metadata]
            
            collection.update(**update_kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def delete_document(
        self,
        collection_type: CollectionType,
        doc_id: str,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a document.
        
        Args:
            collection_type: Type of collection
            doc_id: Document ID
            project_id: Optional project ID for scoping
            
        Returns:
            True if deleted successfully
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        try:
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def delete_collection(
        self,
        collection_type: CollectionType,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Delete an entire collection.
        
        Args:
            collection_type: Type of collection
            project_id: Optional project ID for scoping
            
        Returns:
            True if deleted successfully
        """
        name = self._get_collection_name(collection_type, project_id)
        
        try:
            self._client.delete_collection(name)
            if name in self._collections:
                del self._collections[name]
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            return False
    
    def get_collection_stats(
        self,
        collection_type: CollectionType,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Args:
            collection_type: Type of collection
            project_id: Optional project ID for scoping
            
        Returns:
            Collection statistics
        """
        collection = self.get_or_create_collection(collection_type, project_id)
        
        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata,
        }
    
    def persist(self) -> None:
        """Persist the database to disk."""
        self._client.persist()
        logger.info("Vector store persisted to disk")


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(config: Optional[VectorStoreConfig] = None) -> VectorStore:
    """
    Get or create the global vector store instance.
    
    Args:
        config: Optional configuration
        
    Returns:
        VectorStore instance
    """
    global _vector_store
    
    if _vector_store is None:
        _vector_store = VectorStore(config)
    
    return _vector_store
