import logging
import uuid
from typing import List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.evidence import EvidenceCitation

logger = logging.getLogger(__name__)


class CitationValidationError(Exception):
    """Raised when an evidence citation fails integrity or authorization validation."""
    pass


class CitationValidator:
    """Verifies that evidence citations refer to authentic, accessible documents."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_citations(
        self,
        citations: List[EvidenceCitation],
        authorized_tender_id: uuid.UUID,
        authorized_company_id: uuid.UUID,
    ) -> Tuple[List[EvidenceCitation], List[str]]:
        """
        Validate list of citations against database records and authorization scope.
        Returns: (valid_citations, validation_warnings)
        """
        if not citations:
            return [], []

        valid_citations: List[EvidenceCitation] = []
        warnings: List[str] = []

        doc_ids: Set[uuid.UUID] = {c.document_id for c in citations}
        stmt = select(Document).where(Document.id.in_(doc_ids))
        res = await self.session.execute(stmt)
        docs_by_id = {d.id: d for d in res.scalars().all()}

        for cit in citations:
            doc = docs_by_id.get(cit.document_id)
            if not doc:
                warnings.append(f"Citation Rejected: Document {cit.document_id} does not exist in authoritative records.")
                continue

            # Check authorization: must belong to authorized tender or authorized company
            is_valid_tender = doc.tender_id == authorized_tender_id
            is_valid_company = doc.company_id == authorized_company_id

            if not (is_valid_tender or is_valid_company):
                warnings.append(
                    f"Security Alert: Citation for document {cit.document_id} belongs to unauthorized scope. Dropped."
                )
                continue

            # Verify physical page number bounds
            if doc.total_pages and (cit.page_number < 1 or cit.page_number > doc.total_pages):
                warnings.append(
                    f"Citation Warning: Page number {cit.page_number} is out of bounds for document '{doc.original_filename}' (total: {doc.total_pages})."
                )
                continue

            # Verify filename matches authoritative record
            if cit.source_filename != doc.original_filename:
                cit.source_filename = doc.original_filename  # Correct to authoritative filename

            valid_citations.append(cit)

        return valid_citations, warnings
