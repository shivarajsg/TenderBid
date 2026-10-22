import logging
import uuid
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.evidence import EvidenceCitation
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.semantic_retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines lexical search (PostgreSQL document_chunks) and semantic search (ChromaDB)
    using Reciprocal Rank Fusion (RRF) to produce deduplicated, high-precision evidence citations.
    """

    def __init__(
        self,
        session: AsyncSession,
        lexical_retriever: Optional[LexicalRetriever] = None,
        semantic_retriever: Optional[SemanticRetriever] = None,
        rrf_k: int = 60,
    ):
        self.session = session
        self.lexical = lexical_retriever or LexicalRetriever(session)
        self.semantic = semantic_retriever or SemanticRetriever()
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        tender_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> List[EvidenceCitation]:
        """
        Execute hybrid search and merge candidates using Reciprocal Rank Fusion.
        """
        lexical_results: List[EvidenceCitation] = []
        semantic_results: List[EvidenceCitation] = []

        try:
            lexical_results = await self.lexical.search(
                query=query, tender_id=tender_id, company_id=company_id, limit=limit * 2
            )
        except Exception as e:
            logger.warning(f"Lexical retrieval failed or degraded: {e}")

        try:
            semantic_results = self.semantic.search(
                query=query, tender_id=tender_id, company_id=company_id, limit=limit * 2
            )
        except Exception as e:
            logger.warning(f"Semantic retrieval failed or degraded: {e}")

        # Reciprocal Rank Fusion calculation
        # RRF(d) = sum(1 / (k + rank_i))
        scores: Dict[str, float] = {}
        citation_map: Dict[str, EvidenceCitation] = {}

        # 1. Score lexical rank
        for rank, cit in enumerate(lexical_results):
            key = cit.chunk_id or cit.evidence_id
            scores[key] = scores.get(key, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            citation_map[key] = cit

        # 2. Score semantic rank
        for rank, cit in enumerate(semantic_results):
            key = cit.chunk_id or cit.evidence_id
            scores[key] = scores.get(key, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            if key in citation_map:
                # Upgraded to hybrid
                citation_map[key].retrieval_method = "hybrid"
            else:
                citation_map[key] = cit

        # Sort candidate keys by descending RRF score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)[:limit]

        final_citations: List[EvidenceCitation] = []
        for rank, key in enumerate(sorted_keys):
            cit = citation_map[key]
            cit.relevance_score = round(scores[key], 4)
            final_citations.append(cit)

        return final_citations
