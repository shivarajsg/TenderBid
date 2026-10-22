import abc
import hashlib
import math
from typing import Any, List, Optional
import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
import chromadb.utils.embedding_functions as ef

from app.core.config import get_settings

settings = get_settings()


class BaseEmbeddingService(abc.ABC):
    """Abstract interface for embedding text chunks and search queries."""

    @abc.abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a batch of document chunks."""
        pass

    @abc.abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate a vector embedding for a single search query."""
        pass


class DefaultChromaEmbeddingService(BaseEmbeddingService):
    """ChromaDB's built-in ONNX all-MiniLM-L6-v2 embedding function."""

    def __init__(self):
        self._ef = ef.DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self._ef(texts)

    def embed_query(self, input: Optional[Any] = None, text: Optional[str] = None) -> Any:
        target = input if input is not None else text
        if isinstance(target, list):
            return self._ef.embed_query(input=target)
        return self._ef.embed_query(input=[target])[0]

    def get_chroma_function(self) -> EmbeddingFunction:
        """Return the raw ChromaDB embedding function compatible with collection definition."""
        return self._ef


class MockEmbeddingService(EmbeddingFunction[Documents], BaseEmbeddingService):
    """Deterministic, fast mock embedding service for unit tests without network or ONNX overhead."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        """Generate a deterministic pseudo-random normalized float vector from text hash."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = [math.sin(seed + i) for i in range(self.dimension)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def __call__(self, input: Documents) -> Embeddings:
        return [self._hash_to_vector(t) for t in input]

    @staticmethod
    def name() -> str:
        return "mock_embedding_service"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self(texts)

    def embed_query(self, input: Optional[Any] = None, text: Optional[str] = None) -> Any:
        target = input if input is not None else text
        if target is None:
            return []
        if isinstance(target, list):
            return [self._hash_to_vector(str(t)) for t in target]
        return [self._hash_to_vector(str(target))]

    def get_chroma_function(self) -> "MockEmbeddingService":
        return self


def get_embedding_service(provider: Optional[str] = None) -> BaseEmbeddingService:
    """Factory returning configured or mock embedding service."""
    selected = (provider or settings.EMBEDDING_PROVIDER).lower()
    if selected == "mock":
        return MockEmbeddingService()
    return DefaultChromaEmbeddingService()
