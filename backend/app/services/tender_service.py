import logging
import uuid
from decimal import Decimal
from datetime import datetime
from typing import BinaryIO, Dict, List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.tenders import TenderRepository
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.tender import Tender
from app.schemas.tender import TenderCreate, TenderUpdate
from app.services.chunking_service import RecursiveCharacterChunker, get_chunking_service
from app.services.extraction_service import DocumentExtractionService, get_extraction_service
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.vector_store_service import ChromaVectorStoreService, get_vector_store_service

logger = logging.getLogger(__name__)


class TenderServiceError(Exception):
    """Base exception for tender business operations."""
    pass


class TenderNotFoundError(TenderServiceError):
    """Raised when a tender cannot be found by ID."""
    pass


class DocumentNotFoundError(TenderServiceError):
    """Raised when an attached document cannot be found."""
    pass


class TenderService:
    """Orchestrates tender lifecycle, document uploads, text extraction, and vector indexing."""

    def __init__(
        self,
        session: AsyncSession,
        storage_service: Optional[LocalStorageService] = None,
        extraction_service: Optional[DocumentExtractionService] = None,
        chunking_service: Optional[RecursiveCharacterChunker] = None,
        vector_store_service: Optional[ChromaVectorStoreService] = None,
    ):
        self.session = session
        self.repository = TenderRepository(session)
        self.storage = storage_service or get_storage_service()
        self.extraction = extraction_service or get_extraction_service()
        self.chunker = chunking_service or get_chunking_service()
        self.vector_store = vector_store_service or get_vector_store_service()

    async def create_tender(self, tender_in: TenderCreate, created_by: Optional[uuid.UUID] = None) -> Tender:
        """Create a new tender record."""
        existing = await self.repository.get_by_reference(tender_in.tender_reference)
        if existing:
            raise TenderServiceError(f"Tender reference '{tender_in.tender_reference}' already exists.")
        return await self.repository.create(tender_in, created_by=created_by)

    async def get_tender(self, tender_id: uuid.UUID) -> Tender:
        """Fetch a tender by UUID or raise TenderNotFoundError."""
        tender = await self.repository.get_by_id(tender_id)
        if not tender:
            raise TenderNotFoundError(f"Tender with ID '{tender_id}' not found.")
        return tender

    async def list_tenders(
        self,
        skip: int = 0,
        limit: int = 20,
        sector: Optional[str] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        deadline_after: Optional[datetime] = None,
        search: Optional[str] = None,
        source_portal: Optional[str] = None,
    ) -> Tuple[List[Tender], int]:
        """List tenders with query filters."""
        return await self.repository.list(
            skip=skip,
            limit=limit,
            sector=sector,
            min_budget=min_budget,
            max_budget=max_budget,
            deadline_after=deadline_after,
            search=search,
            source_portal=source_portal,
        )

    async def update_tender(self, tender_id: uuid.UUID, tender_in: TenderUpdate) -> Tender:
        """Update tender metadata."""
        tender = await self.get_tender(tender_id)
        update_data = tender_in.model_dump(exclude_unset=True)
        return await self.repository.update(tender, update_data)

    async def delete_tender(self, tender_id: uuid.UUID) -> None:
        """Delete tender, purge associated ChromaDB vectors, and remove physical files."""
        tender = await self.get_tender(tender_id)

        # Purge vector index for each attached document
        for doc in tender.documents:
            try:
                self.vector_store.delete_document_chunks(str(doc.id))
            except Exception as e:
                logger.warning(f"Error purging vectors for doc {doc.id}: {e}")
            self.storage.delete_file(doc.storage_path)

        await self.repository.delete(tender)

    async def upload_tender_documents(
        self,
        tender_id: uuid.UUID,
        files: List[UploadFile],
        user_id: Optional[uuid.UUID] = None,
        category: str = "TENDER_NOTICE",
    ) -> List[Document]:
        """Validate, store, and record metadata for uploaded tender PDF documents."""
        tender = await self.get_tender(tender_id)
        created_documents: List[Document] = []

        for file in files:
            doc_id = uuid.uuid4()
            rel_target_path = f"tenders/{tender_id}/{doc_id}.pdf"

            try:
                saved_path, file_size, sha256_hash = await self.storage.save_pdf_stream(
                    file_obj=file.file,
                    target_relative_path=rel_target_path,
                )

                doc = Document(
                    id=doc_id,
                    tender_id=tender.id,
                    company_id=None,
                    entity_type="TENDER",
                    uploaded_by=user_id,
                    document_category=category,
                    original_filename=file.filename or "tender_notice.pdf",
                    storage_path=saved_path,
                    mime_type="application/pdf",
                    file_size_bytes=file_size,
                    sha256_hash=sha256_hash,
                    processing_status="PENDING",
                    verification_status="UNVERIFIED",
                )
                self.session.add(doc)
                created_documents.append(doc)

            except Exception as e:
                logger.error(f"Failed to upload document {file.filename}: {e}")
                # Clean up any already saved files in this batch
                for created_doc in created_documents:
                    self.storage.delete_file(created_doc.storage_path)
                await self.session.rollback()
                raise

        await self.session.commit()
        for doc in created_documents:
            await self.session.refresh(doc)

        return created_documents

    async def process_tender_documents(
        self,
        tender_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
    ) -> Tender:
        """
        Execute document intelligence pipeline:
        1. Extract text page by page (with OCR fallback for low-density/scanned pages).
        2. Recursively chunk extracted pages preserving page provenance.
        3. Index chunks into persistent ChromaDB vector store.
        4. Update document and tender processing states.
        """
        tender = await self.get_tender(tender_id)
        if document_id is not None:
            docs_stmt = select(Document).where(Document.tender_id == tender.id, Document.id == document_id)
            docs_res = await self.session.execute(docs_stmt)
            docs_to_process = list(docs_res.scalars().all())
            if not docs_to_process:
                docs_to_process = [d for d in tender.documents if str(d.id) == str(document_id)]
        else:
            docs_stmt = select(Document).where(Document.tender_id == tender.id)
            docs_res = await self.session.execute(docs_stmt)
            docs_to_process = list(docs_res.scalars().all())

        if not docs_to_process:
            return tender

        # Update tender status
        tender.processing_status = "EXTRACTING"
        await self.session.commit()

        any_failed = False
        any_success = False

        for doc in docs_to_process:
            doc.processing_status = "EXTRACTING"
            await self.session.commit()

            try:
                abs_file_path = self.storage.get_file_path(doc.storage_path)

                # Step 1: Text extraction
                extraction_result = self.extraction.extract_document(abs_file_path)

                # Step 2: Recursive chunking with page provenance
                chunks = self.chunker.chunk_document_pages(
                    pages=extraction_result.pages,
                    tender_id=tender.id,
                    document_id=doc.id,
                    source_filename=doc.original_filename,
                )

                # Step 3: Idempotent ChromaDB indexing and PostgreSQL document_chunks persistence
                self.vector_store.delete_document_chunks(str(doc.id))
                indexed_count = self.vector_store.index_chunks(chunks)

                await self.session.execute(delete(DocumentChunkModel).where(DocumentChunkModel.document_id == doc.id))
                for c in chunks:
                    chunk_row = DocumentChunkModel(
                        id=c.chunk_id,
                        document_id=doc.id,
                        tender_id=tender.id,
                        company_id=None,
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

                # Step 4: Update document record
                doc.total_pages = extraction_result.total_pages
                doc.indexed_chunks = indexed_count
                doc.extraction_metadata = extraction_result.to_metadata_dict()
                doc.error_message = None

                if extraction_result.degraded_pages_count > 0 and indexed_count == 0:
                    doc.processing_status = "PARTIALLY_INDEXED"
                else:
                    doc.processing_status = "INDEXED"

                any_success = True

            except Exception as e:
                logger.error(f"Processing failed for document {doc.id}: {e}", exc_info=True)
                doc.processing_status = "FAILED"
                doc.error_message = str(e)[:1000]
                any_failed = True

            await self.session.commit()
            await self.session.refresh(doc)

        # Recalculate overall tender status
        all_docs_stmt = select(Document).where(Document.tender_id == tender.id)
        all_docs_res = await self.session.execute(all_docs_stmt)
        all_docs = list(all_docs_res.scalars().all())

        if not all_docs:
            tender.processing_status = "PENDING"
        elif all(d.processing_status == "INDEXED" for d in all_docs):
            tender.processing_status = "INDEXED"
        elif all(d.processing_status == "FAILED" for d in all_docs):
            tender.processing_status = "FAILED"
        elif any(d.processing_status in ("INDEXED", "PARTIALLY_INDEXED") for d in all_docs):
            tender.processing_status = "PARTIALLY_INDEXED"
        else:
            tender.processing_status = "PENDING"

        await self.session.commit()
        await self.session.refresh(tender)
        return tender
