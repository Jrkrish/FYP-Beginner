"""
Embedding Service Module

Provides text embedding generation for semantic memory.
"""

import os
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class EmbeddingProvider(Enum):
    """Embedding provider types."""
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    model: str
    dimensions: int


class BaseEmbedding(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name."""
        pass


class SentenceTransformerEmbedding(BaseEmbedding):
    """
    Sentence Transformer embedding provider.
    
    Uses local models for fast, free embeddings.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize Sentence Transformer embedding.
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self._model_name = model_name
        self._model = None
        self._dimensions = None
    
    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                # Get dimensions from a test embedding
                test_embedding = self._model.encode("test")
                self._dimensions = len(test_embedding)
                logger.info(f"Loaded SentenceTransformer model: {self._model_name}")
            except ImportError:
                raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        self._load_model()
        embedding = self._model.encode(text)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        self._load_model()
        embeddings = self._model.encode(texts)
        return embeddings.tolist()
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        self._load_model()
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._model_name


class OpenAIEmbedding(BaseEmbedding):
    """
    OpenAI embedding provider.
    
    Uses OpenAI's text-embedding models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-ada-002",
    ):
        """
        Initialize OpenAI embedding.
        
        Args:
            api_key: OpenAI API key
            model_name: Embedding model name
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model_name = model_name
        self._client = None
        
        # Model dimensions
        self._model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai is required. Install with: pip install openai")
        return self._client
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        client = self._get_client()
        response = client.embeddings.create(
            input=text,
            model=self._model_name,
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        client = self._get_client()
        response = client.embeddings.create(
            input=texts,
            model=self._model_name,
        )
        return [item.embedding for item in response.data]
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._model_dimensions.get(self._model_name, 1536)
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._model_name


class GoogleEmbedding(BaseEmbedding):
    """
    Google embedding provider.
    
    Uses Google's text embedding models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/embedding-001",
    ):
        """
        Initialize Google embedding.
        
        Args:
            api_key: Google API key
            model_name: Embedding model name
        """
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._model_name = model_name
        self._genai = None
    
    def _get_genai(self):
        """Get or configure Google Generative AI."""
        if self._genai is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._genai = genai
            except ImportError:
                raise ImportError("google-generativeai is required. Install with: pip install google-generativeai")
        return self._genai
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        genai = self._get_genai()
        result = genai.embed_content(
            model=self._model_name,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return 768  # Default for embedding-001
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._model_name


class EmbeddingService:
    """
    Unified embedding service.
    
    Supports multiple embedding providers with fallback.
    """
    
    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMER,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize embedding service.
        
        Args:
            provider: Embedding provider to use
            model_name: Model name (optional, uses provider default)
            api_key: API key for cloud providers
        """
        self.provider = provider
        self._embedding: BaseEmbedding = self._create_embedding(provider, model_name, api_key)
    
    def _create_embedding(
        self,
        provider: EmbeddingProvider,
        model_name: Optional[str],
        api_key: Optional[str],
    ) -> BaseEmbedding:
        """Create embedding provider instance."""
        if provider == EmbeddingProvider.SENTENCE_TRANSFORMER:
            return SentenceTransformerEmbedding(
                model_name=model_name or "all-MiniLM-L6-v2"
            )
        elif provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbedding(
                api_key=api_key,
                model_name=model_name or "text-embedding-ada-002",
            )
        elif provider == EmbeddingProvider.GOOGLE:
            return GoogleEmbedding(
                api_key=api_key,
                model_name=model_name or "models/embedding-001",
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with embedding vector
        """
        embedding = self._embedding.embed(text)
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self._embedding.model_name,
            dimensions=self._embedding.dimensions,
        )
    
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: Texts to embed
            
        Returns:
            List of EmbeddingResults
        """
        embeddings = self._embedding.embed_batch(texts)
        return [
            EmbeddingResult(
                text=text,
                embedding=embedding,
                model=self._embedding.model_name,
                dimensions=self._embedding.dimensions,
            )
            for text, embedding in zip(texts, embeddings)
        ]
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._embedding.dimensions
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._embedding.model_name


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    provider: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMER,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> EmbeddingService:
    """
    Get or create global embedding service.
    
    Args:
        provider: Embedding provider
        model_name: Model name
        api_key: API key
        
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService(provider, model_name, api_key)
    
    return _embedding_service
