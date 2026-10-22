import os
import uuid
from typing import List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.config import get_settings
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.documents import DocumentRepository
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.user import User
from app.schemas.document import DocumentMetadataCreate, DocumentResponse
from app.services.chunking_service import get_chunking_service
from app.services.extraction_service import get_extraction_service
from app.services.storage_service import get_storage_service
from app.services.vector_store_service import get_vector_store_service

logger = logging.getLogger(__name__)

settings = get_settings()


class DocumentNotFoundError(Exception):
    """Raised when a requested document does not exist or does not belong to the tenant."""
    pass


class DocumentValidationError(Exception):
    """Raised when document payload fails business constraints."""
    pass


class DocumentService:
    """Service handling corporate document metadata, category tagging, and vault operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.company_repo = CompanyRepository(session)

    async def _get_user_company_id(self, user: User) -> UUID:
        """Resolve company UUID owned by user, or raise error."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise DocumentValidationError("You must create a company profile before uploading documents")
        return company.id

    @staticmethod
    def _to_response(doc: Document) -> DocumentResponse:
        """Convert Document model to DocumentResponse (omitting internal storage_path)."""
        return DocumentResponse(
            id=doc.id,
            company_id=doc.company_id,
            uploaded_by=doc.uploaded_by,
            document_category=doc.document_category,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            sha256_hash=doc.sha256_hash,
            valid_from=doc.valid_from,
            valid_until=doc.valid_until,
            verification_status=doc.verification_status,
            processing_status=getattr(doc, "processing_status", None),
            total_pages=getattr(doc, "total_pages", None),
            indexed_chunks=getattr(doc, "indexed_chunks", 0),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def register_metadata(
        self,
        user: User,
        request: DocumentMetadataCreate,
    ) -> DocumentResponse:
        """Register a new document metadata record in the company's isolated vault."""
        company_id = await self._get_user_company_id(user)

        # Enforce PDF format constraint
        if request.mime_type.lower() != "application/pdf":
            raise DocumentValidationError("Only PDF documents (application/pdf) are supported")

        # Check for existing duplicate file in this company's vault
        existing = await self.doc_repo.get_by_hash(company_id, request.sha256_hash)
        if existing:
            # Return existing metadata record rather than creating a duplicate
            return self._to_response(existing)

        # Generate sandboxed internal storage path
        random_file_id = uuid.uuid4()
        storage_rel_path = os.path.join(
            "vault",
            str(company_id),
            f"{random_file_id}.pdf",
        ).replace("\\", "/")

        doc = await self.doc_repo.create(
            company_id=company_id,
            uploaded_by=user.id,
            document_category=request.document_category.value,
            original_filename=request.original_filename,
            storage_path=storage_rel_path,
            mime_type=request.mime_type,
            file_size_bytes=request.file_size_bytes,
            sha256_hash=request.sha256_hash,
            valid_from=request.valid_from,
            valid_until=request.valid_until,
            verification_status="METADATA_EXTRACTED",
        )
        return self._to_response(doc)

    async def list_documents(
        self,
        user: User,
        category: Optional[str] = None,
    ) -> List[DocumentResponse]:
        """List documents owned exclusively by the authenticated user's company."""
        company_id = await self._get_user_company_id(user)
        docs = await self.doc_repo.list_by_company(company_id, category)
        return [self._to_response(d) for d in docs]

    async def get_document(self, user: User, document_id: UUID) -> DocumentResponse:
        """Fetch a single document strictly verifying tenant ownership."""
        company_id = await self._get_user_company_id(user)
        doc = await self.doc_repo.get_by_id(document_id, company_id)
        if not doc:
            raise DocumentNotFoundError("Document not found in your company vault")
        return self._to_response(doc)

    async def delete_document(self, user: User, document_id: UUID) -> None:
        """Delete document record strictly verifying tenant ownership."""
        company_id = await self._get_user_company_id(user)
        doc = await self.doc_repo.get_by_id(document_id, company_id)
        if not doc:
            raise DocumentNotFoundError("Document not found in your company vault")
        await self.doc_repo.delete(doc)

    async def upload_vault_document(
        self,
        user: User,
        file: UploadFile,
        document_category: str = "FINANCIAL_AUDIT",
    ) -> DocumentResponse:
        """Physically upload, extract, chunk, and index an MSME company vault document."""
        company_id = await self._get_user_company_id(user)
        doc_id = uuid.uuid4()
        storage_rel_path = f"companies/{company_id}/{doc_id}.pdf"

        storage = get_storage_service()
        saved_path, file_size, sha256_hash = await storage.save_pdf_stream(
            file_obj=file.file,
            target_relative_path=storage_rel_path,
        )

        doc = Document(
            id=doc_id,
            company_id=company_id,
            tender_id=None,
            entity_type="COMPANY",
            uploaded_by=user.id,
            document_category=document_category,
            original_filename=file.filename or f"{document_category}.pdf",
            storage_path=saved_path,
            mime_type="application/pdf",
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            processing_status="EXTRACTING",
            verification_status="UNVERIFIED",
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        try:
            extraction_svc = get_extraction_service()
            chunking_svc = get_chunking_service()
            vector_store = get_vector_store_service()

            abs_path = storage.get_file_path(saved_path)
            res = extraction_svc.extract_document(abs_path)
            chunks = chunking_svc.chunk_document_pages(
                pages=res.pages,
                tender_id=uuid.UUID(int=0),
                document_id=doc.id,
                source_filename=doc.original_filename,
            )

            for c in chunks:
                c.metadata["company_id"] = str(company_id)
                c.metadata["tender_id"] = None

            vector_store.delete_document_chunks(str(doc.id))
            indexed_count = vector_store.index_chunks(chunks)

            for c in chunks:
                chunk_row = DocumentChunkModel(
                    id=c.chunk_id,
                    document_id=doc.id,
                    tender_id=None,
                    company_id=company_id,
                    source_filename=doc.original_filename,
                    page_number=c.metadata.get("page_number", 1),
                    chunk_index=c.metadata.get("chunk_index", 0),
                    char_start=c.metadata.get("char_start", 0),
                    char_end=c.metadata.get("char_end", len(c.text)),
                    sha256_hash=c.metadata.get("sha256_hash", ""),
                    chunk_text=c.text,
                    extraction_method=c.metadata.get("extraction_method", "pymupdf_direct"),
                )
                self.session.add(chunk_row)

            doc.total_pages = res.total_pages
            doc.indexed_chunks = indexed_count
            doc.extraction_metadata = res.to_metadata_dict()
            doc.processing_status = "INDEXED"
            await self.session.commit()
            await self.session.refresh(doc)
        except Exception as e:
            logger.error(f"Failed to process company document {doc.id}: {e}", exc_info=True)
            doc.processing_status = "FAILED"
            doc.error_message = str(e)[:1000]
            await self.session.commit()

        return self._to_response(doc)
