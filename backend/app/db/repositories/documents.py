from datetime import date
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    """Repository handling database operations for the Document Vault entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, document_id: UUID, company_id: UUID) -> Optional[Document]:
        """Fetch document by UUID, strictly enforcing owning company isolation."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.company_id == company_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_company(
        self,
        company_id: UUID,
        category: Optional[str] = None,
    ) -> List[Document]:
        """List documents belonging exclusively to the specified company tenant."""
        stmt = select(Document).where(Document.company_id == company_id)
        if category:
            stmt = stmt.where(Document.document_category == category.upper())
        stmt = stmt.order_by(Document.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_hash(self, company_id: UUID, sha256_hash: str) -> Optional[Document]:
        """Check for existing duplicate document in the company's vault by SHA-256 hash."""
        stmt = (
            select(Document)
            .where(Document.company_id == company_id)
            .where(Document.sha256_hash == sha256_hash.strip().lower())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        company_id: UUID,
        uploaded_by: Optional[UUID],
        document_category: str,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        file_size_bytes: int,
        sha256_hash: str,
        valid_from: Optional[date] = None,
        valid_until: Optional[date] = None,
        verification_status: str = "METADATA_EXTRACTED",
    ) -> Document:
        """Create and persist a new document metadata record."""
        doc = Document(
            company_id=company_id,
            uploaded_by=uploaded_by,
            document_category=document_category,
            original_filename=original_filename.strip(),
            storage_path=storage_path.strip(),
            mime_type=mime_type.strip().lower(),
            file_size_bytes=file_size_bytes,
            sha256_hash=sha256_hash.strip().lower(),
            valid_from=valid_from,
            valid_until=valid_until,
            verification_status=verification_status,
        )
        self.session.add(doc)
        await self.session.flush()
        await self.session.refresh(doc)
        return doc

    async def delete(self, document: Document) -> None:
        """Remove a document record from the database."""
        await self.session.delete(document)
        await self.session.flush()
