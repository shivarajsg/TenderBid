import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import EmbeddingFunction

from app.core.config import get_settings
from app.services.chunking_service import DocumentChunk
from app.services.embedding_service import (
    BaseEmbeddingService,
    DefaultChromaEmbeddingService,
    MockEmbeddingService,
    get_embedding_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreError(Exception):
    """Base exception for ChromaDB vector store operations."""
    pass


class ChromaVectorStoreService:
    """Persistent ChromaDB vector store manager supporting multi-tenant metadata filtering."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
        client: Optional[ClientAPI] = None,
    ):
        self.persist_dir = Path(persist_directory or settings.CHROMA_PERSIST_DIRECTORY).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.embedding_service = embedding_service or get_embedding_service()

        if client is not None:
            self._client = client
        else:
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))

        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> Collection:
        """Initialize or retrieve the target ChromaDB collection."""
        metadata = {"hnsw:space": "cosine"}

        # If the embedding service provides a native Chroma EmbeddingFunction, pass it
        if hasattr(self.embedding_service, "get_chroma_function"):
            ef_func = self.embedding_service.get_chroma_function()
            return self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=ef_func,
                metadata=metadata,
            )
        elif isinstance(self.embedding_service, EmbeddingFunction):
            return self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_service,
                metadata=metadata,
            )
        else:
            return self._client.get_or_create_collection(
                name=self.collection_name,
                metadata=metadata,
            )

    def delete_document_chunks(self, document_id: str) -> int:
        """
        Idempotent purge: removes all existing chunks for a document before re-indexing.
        Returns count of deleted items.
        """
        try:
            # Query existing chunks first to measure deleted count
            existing = self._collection.get(where={"document_id": str(document_id)})
            count = len(existing.get("ids", []))
            if count > 0:
                self._collection.delete(where={"document_id": str(document_id)})
                logger.info(f"Purged {count} existing vector chunks for document {document_id}")
            return count
        except Exception as e:
            logger.error(f"Error purging chunks for document {document_id}: {e}")
            raise VectorStoreError(f"Failed to purge chunks: {e}")

    def index_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Index or upsert chunks into ChromaDB with metadata.
        """
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]

        try:
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Successfully indexed {len(chunks)} chunks into collection '{self.collection_name}'")
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed to index chunks into ChromaDB: {e}")
            raise VectorStoreError(f"Vector indexing failed: {e}")

    def query(
        self,
        query_text: str,
        tender_id: Optional[str] = None,
        document_id: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query vector collection with metadata filtering (scoped to tender_id or document_id).
        """
        where_filter: Optional[Dict[str, Any]] = None

        if tender_id and document_id:
            where_filter = {
                "$and": [
                    {"tender_id": str(tender_id)},
                    {"document_id": str(document_id)},
                ]
            }
        elif tender_id:
            where_filter = {"tender_id": str(tender_id)}
        elif document_id:
            where_filter = {"document_id": str(document_id)}

        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            formatted_results = []
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                ids = results["ids"][0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]

                for i, chunk_id in enumerate(ids):
                    formatted_results.append({
                        "chunk_id": chunk_id,
                        "text": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": dists[i] if i < len(dists) else 0.0,
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            raise VectorStoreError(f"Vector query failed: {e}")

    def count(self) -> int:
        """Return total number of items in collection."""
        return self._collection.count()


_vector_store_service: Optional[ChromaVectorStoreService] = None


def get_vector_store_service() -> ChromaVectorStoreService:
    """Dependency provider returning singleton ChromaVectorStoreService."""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = ChromaVectorStoreService()
    return _vector_store_service
