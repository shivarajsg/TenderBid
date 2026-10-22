import logging
import uuid
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunkModel
from app.schemas.evidence import EvidenceCitation

logger = logging.getLogger(__name__)


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

        # Keyword matching
        keywords = [k.strip() for k in query.split() if len(k.strip()) > 2]
        if keywords:
            keyword_filters = [DocumentChunkModel.chunk_text.ilike(f"%{kw}%") for kw in keywords]
            filters.append(or_(*keyword_filters))

        stmt = stmt.where(*filters).limit(limit)
        result = await self.session.execute(stmt)
        chunks = list(result.scalars().all())

        citations: List[EvidenceCitation] = []
        for i, c in enumerate(chunks):
            src_type = "TENDER_DOCUMENT" if c.tender_id else "COMPANY_DOCUMENT"
            score = 1.0 / (1.0 + i)  # Simple rank-based relevance proxy
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
                relevance_score=score,
                sha256_hash=c.sha256_hash,
            )
            citations.append(cit)

        return citations
