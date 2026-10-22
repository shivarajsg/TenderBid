import logging
import re
import uuid
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunkModel
from app.schemas.evidence import EvidenceCitation

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "this", "that", "these", "those", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "the", "a", "an", "and",
    "or", "but", "if", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down", "in",
    "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "will", "just", "should", "now", "tell", "give", "please", "would", "could",
}


def extract_keywords(query: str) -> List[str]:
    """
    Extract meaningful alphanumeric keywords from user query, stripping punctuation and stop words.
    """
    tokens = re.findall(r'[a-zA-Z0-9_\-]+', query)
    filtered = [t for t in tokens if len(t) > 2 and t.lower() not in STOP_WORDS]
    if not filtered:
        filtered = [t for t in tokens if len(t) > 1]
    return filtered


class LexicalRetriever:
    """PostgreSQL-backed lexical search retriever with strict tenant isolation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        tender_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> List[EvidenceCitation]:
        """
        Execute keyword/lexical search against stored document chunks.
        Strict isolation: requires either tender_id or company_id.
        """
        if not tender_id and not company_id:
            raise ValueError("Lexical search requires either tender_id or company_id for security isolation.")

        stmt = select(DocumentChunkModel)
        filters = []

        if tender_id:
            filters.append(DocumentChunkModel.tender_id == tender_id)
        if company_id:
            filters.append(DocumentChunkModel.company_id == company_id)

        # Keyword matching with sanitized tokens
        keywords = extract_keywords(query)
        if keywords:
            keyword_filters = [DocumentChunkModel.chunk_text.ilike(f"%{kw}%") for kw in keywords]
            filters.append(or_(*keyword_filters))

        stmt = stmt.where(*filters).limit(limit * 3)
        result = await self.session.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            return []

        # Score chunks by count of distinct keywords matching in chunk_text
        def compute_score(c: DocumentChunkModel) -> float:
            txt = c.chunk_text.lower()
            matches = sum(1 for kw in keywords if kw.lower() in txt)
            return float(matches)

        ranked_chunks = sorted(chunks, key=compute_score, reverse=True)[:limit]

        citations: List[EvidenceCitation] = []
        for i, c in enumerate(ranked_chunks):
            src_type = "TENDER_DOCUMENT" if c.tender_id else "COMPANY_DOCUMENT"
            raw_score = compute_score(c)
            # Normalized score proxy
            score = max(0.1, min(1.0, (raw_score / max(1, len(keywords))) * 0.9 + 0.1))
            cit = EvidenceCitation(
                evidence_id=f"lex_{c.id}",
                source_type=src_type,
                document_id=c.document_id,
                source_filename=c.source_filename,
                page_number=c.page_number,
                excerpt=c.chunk_text[:500],
                char_start=c.char_start,
                char_end=c.char_end,
                chunk_id=c.id,
                retrieval_method="lexical",
                relevance_score=round(score, 4),
                sha256_hash=c.sha256_hash,
            )
            citations.append(cit)

        return citations
