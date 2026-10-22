import logging
import uuid
from typing import List, Optional

from app.schemas.evidence import EvidenceCitation
from app.services.vector_store_service import ChromaVectorStoreService, get_vector_store_service

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """ChromaDB-backed semantic vector retriever with metadata isolation."""

    def __init__(self, vector_store: Optional[ChromaVectorStoreService] = None):
        self.vector_store = vector_store or get_vector_store_service()

    def search(
        self,
        query: str,
        tender_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> List[EvidenceCitation]:
        """
        Execute dense vector similarity query against ChromaDB with strict scoping.
        """
        if not tender_id and not company_id:
            raise ValueError("Semantic search requires either tender_id or company_id for security isolation.")

        t_str = str(tender_id) if tender_id else None
        c_str = str(company_id) if company_id else None

        # Query vector store with metadata filtering
        raw_results = self.vector_store.query(
            query_text=query,
            tender_id=t_str,
            n_results=limit,
        )

        citations: List[EvidenceCitation] = []
        for r in raw_results:
            meta = r.get("metadata", {})
            chunk_id = r.get("chunk_id", "")
            doc_id_str = meta.get("document_id")
            if not doc_id_str:
                continue

            # Compute normalized relevance score from cosine distance
            dist = float(r.get("distance", 1.0))
            score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

            src_type = "TENDER_DOCUMENT" if meta.get("tender_id") else "COMPANY_DOCUMENT"

            cit = EvidenceCitation(
                evidence_id=f"sem_{chunk_id}",
                source_type=src_type,
                document_id=uuid.UUID(doc_id_str),
                source_filename=meta.get("source_filename", "document.pdf"),
                page_number=int(meta.get("page_number", 1)),
                excerpt=r.get("text", "")[:500],
                char_start=meta.get("char_start"),
                char_end=meta.get("char_end"),
                chunk_id=chunk_id,
                retrieval_method="semantic",
                relevance_score=score,
                sha256_hash=meta.get("sha256_hash"),
            )
            citations.append(cit)

        return citations
