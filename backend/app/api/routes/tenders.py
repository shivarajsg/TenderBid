import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.security import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.tender import (
    ApproveRequirementsRequest,
    ExtractedChunkInfo,
    ExtractedDocumentInfo,
    FetchTenderDocumentsResponse,
    ProposedRequirementsBundle,
    TenderCreate,
    TenderDocumentResponse,
    TenderExtractedKnowledgeResponse,
    TenderImageMetaResponse,
    TenderListResponse,
    TenderProcessingStatusResponse,
    TenderQARequest,
    TenderQAResponse,
    TenderResponse,
    TenderUpdate,
)
from app.schemas.ingestion import (
    IngestionPortalStatus,
    IngestionRunResponse,
    IngestionStatusOverviewResponse,
    IngestionTriggerRequest,
)
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.services.compliance.requirement_extraction_service import RequirementExtractionService
from app.services.compliance.requirement_normalizer import RequirementNormalizer
from app.services.retrieval.tender_qa_service import TenderQAService
from app.services.document_retrieval_service import TenderDocumentRetrievalService
from app.services.ingestion.ingestion_service import TenderIngestionService
from app.services.ingestion_scheduler import get_ingestion_scheduler
from sqlalchemy import select
from app.services.tender_image_service import get_tender_image_service, TENDER_IMAGES_DIR
from app.services.tender_service import (
    DocumentNotFoundError,
    TenderNotFoundError,
    TenderService,
    TenderServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tenders"])


# ============================================================================
# Authenticated Public / MSME Tender Endpoints
# ============================================================================

@router.get(
    "/tenders",
    response_model=TenderListResponse,
    summary="List tender opportunities with filtering and search",
)
async def list_tenders(
    page: Optional[int] = Query(None, ge=1, description="1-based page number (alternative to skip)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sector: Optional[str] = Query(None, description="Filter by domain sector"),
    min_budget: Optional[Decimal] = Query(None, ge=0, description="Minimum estimated budget (INR)"),
    max_budget: Optional[Decimal] = Query(None, ge=0, description="Maximum estimated budget (INR)"),
    deadline_after: Optional[datetime] = Query(None, description="Tenders closing after UTC datetime"),
    search: Optional[str] = Query(None, description="Text search in title, reference, or authority"),
    source_portal: Optional[str] = Query(None, description="Filter by official source portal: GEM, CPPP, OPEN_GOV, TENDERKART, APIFY, MANUAL"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve paginated tenders matching MSME search criteria."""
    # Compute effective skip if page parameter is provided
    effective_skip = (page - 1) * limit if page is not None else skip

    service = TenderService(session)
    items, total = await service.list_tenders(
        skip=effective_skip,
        limit=limit,
        sector=sector,
        min_budget=min_budget,
        max_budget=max_budget,
        deadline_after=deadline_after,
        search=search,
        source_portal=source_portal,
    )

    # Compute 1-based page number and total pages
    calculated_page = (effective_skip // limit) + 1 if limit > 0 else 1
    total_pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1

    return TenderListResponse(
        items=[TenderResponse.model_validate(t) for t in items],
        total=total,
        skip=effective_skip,
        limit=limit,
        page=calculated_page,
        pages=total_pages,
    )


# ============================================================================
# Government Tender Automated Ingestion Endpoints (Phase 11)
# ============================================================================

@router.get(
    "/tenders/ingestion/status",
    response_model=IngestionStatusOverviewResponse,
    summary="Get government tender ingestion portal health and synchronization status",
)
async def get_ingestion_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Inspect real-time health, access mode, and synchronization status for official portals."""
    ingestion_scheduler = get_ingestion_scheduler()
    service = TenderIngestionService(session)
    return await service.get_overview(
        scheduler_running=ingestion_scheduler.is_running,
        scheduler_interval_seconds=ingestion_scheduler.interval_seconds,
    )


@router.post(
    "/tenders/refresh",
    response_model=IngestionRunResponse,
    summary="Refresh live tender listing from official government portals",
)
async def refresh_tenders(
    source_portal: Optional[str] = Query("ALL", description="Filter source portal: ALL, GEM, CPPP, etc."),
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Max tenders to sync per portal"),
    force: bool = Query(False, description="Force update existing records"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Fetch current live tender listings from public GeM / government providers,
    normalize metadata, and update PostgreSQL without duplicating tenders or destroying existing documents.
    Accessible to all authenticated users (MSMEs and Admins).
    """
    service = TenderIngestionService(session)
    run = await service.sync_portal(
        source_portal=source_portal or "ALL",
        limit=limit or 50,
        force=force,
    )
    return IngestionRunResponse.model_validate(run)


@router.post(
    "/tenders/ingestion/sync",
    response_model=IngestionRunResponse,
    summary="Trigger automated government tender ingestion tick (Admin only)",
)
async def trigger_ingestion_sync(
    body: IngestionTriggerRequest = IngestionTriggerRequest(),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Manually trigger discovery, normalization, deduplication, and PostgreSQL sync."""
    service = TenderIngestionService(session)
    run = await service.sync_portal(
        source_portal=body.source_portal or "ALL",
        limit=body.batch_size or 50,
        force=body.force,
    )
    return IngestionRunResponse.model_validate(run)


@router.get(
    "/tenders/{tender_id}",
    response_model=TenderResponse,
    summary="Get tender details and attached documents",
)
async def get_tender_detail(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch complete metadata and document notices for a specific tender."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
        return TenderResponse.model_validate(tender)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tenders/{tender_id}/fetch-documents",
    response_model=FetchTenderDocumentsResponse,
    summary="Trigger automatic document retrieval and verification for a tender",
)
async def fetch_tender_documents(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Examine source URLs, download verified public PDFs, run integrity checks,
    and index document content into the vector store and relational chunk database.
    """
    retrieval_service = TenderDocumentRetrievalService(session)
    return await retrieval_service.fetch_tender_documents(tender_id, user=current_user)


@router.get(
    "/tenders/{tender_id}/documents/{document_id}/view",
    summary="Stream an attached tender document PDF for in-app inline viewing",
)
async def view_tender_document(
    tender_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Stream authorized tender notice or RFP document with inline disposition for in-app viewing."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    docs_stmt = select(Document).where(Document.tender_id == tender.id, Document.id == document_id)
    docs_res = await session.execute(docs_stmt)
    doc = docs_res.scalar_one_or_none()
    if not doc:
        doc = next((d for d in tender.documents if str(d.id) == str(document_id)), None)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found on this tender")

    try:
        file_path = service.storage.get_file_path(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file missing from storage")

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


@router.get(
    "/tenders/{tender_id}/documents/{document_id}/download",
    summary="Download an attached tender document PDF",
)
async def download_tender_document(
    tender_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Stream authorized tender notice or RFP document."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    docs_stmt = select(Document).where(Document.tender_id == tender.id, Document.id == document_id)
    docs_res = await session.execute(docs_stmt)
    doc = docs_res.scalar_one_or_none()
    if not doc:
        doc = next((d for d in tender.documents if str(d.id) == str(document_id)), None)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found on this tender")

    try:
        file_path = service.storage.get_file_path(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file missing from storage")

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type="application/pdf",
    )


@router.get(
    "/tenders/{tender_id}/extracted-knowledge",
    response_model=TenderExtractedKnowledgeResponse,
    summary="Get extracted document knowledge for this tender (pages, chunks, text)",
)
async def get_tender_extracted_knowledge(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve authoritative extracted document knowledge for this tender.
    If downloaded documents have not yet been extracted, automatically processes them.
    Returns documents, chunk count, and extracted chunks for AI contextual evaluation.
    """
    tender_service = TenderService(session)
    try:
        tender = await tender_service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Auto-extract if any documents exist and are not yet INDEXED
    unindexed = [d for d in tender.documents if d.processing_status != "INDEXED" or (d.indexed_chunks or 0) == 0]
    if unindexed:
        try:
            await tender_service.process_tender_documents(tender_id=tender.id)
            tender = await tender_service.get_tender(tender_id)
        except Exception as e:
            logger.warning(f"Failed to auto-process unindexed documents: {e}")

    # Fetch document chunks for this tender
    chunk_stmt = (
        select(DocumentChunkModel)
        .where(DocumentChunkModel.tender_id == tender.id)
        .order_by(DocumentChunkModel.page_number, DocumentChunkModel.chunk_index)
        .limit(100)
    )
    chunk_res = await session.execute(chunk_stmt)
    chunks = list(chunk_res.scalars().all())

    doc_infos = [
        ExtractedDocumentInfo(
            document_id=d.id,
            original_filename=d.original_filename,
            document_category=d.document_category,
            processing_status=d.processing_status,
            total_pages=d.total_pages,
            indexed_chunks=d.indexed_chunks or 0,
            extraction_metadata=d.extraction_metadata,
        )
        for d in tender.documents
    ]

    chunk_infos = [
        ExtractedChunkInfo(
            chunk_id=str(c.id),
            document_id=c.document_id,
            source_filename=c.source_filename,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            chunk_text=c.chunk_text,
            extraction_method=c.extraction_method or "pymupdf_direct",
        )
        for c in chunks
    ]

    return TenderExtractedKnowledgeResponse(
        tender_id=tender.id,
        tender_reference=tender.tender_reference,
        title=tender.title,
        status=tender.processing_status,
        total_documents=len(tender.documents),
        total_chunks=len(chunks),
        documents=doc_infos,
        chunks=chunk_infos,
    )


@router.get(
    "/tenders/{tender_id}/image-meta",
    response_model=TenderImageMetaResponse,
    summary="Get resolved image metadata and provenance for a tender",
)
async def get_tender_image_meta(
    tender_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Returns image provenance for the tender:
    - Prioritizes authentic document-extracted technical photo
    - Secondary: cached permitted image
    - Tertiary: curated category technical SVG
    """
    tender_service = TenderService(session)
    try:
        tender = await tender_service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Check if a downloaded PDF exists for this tender
    downloaded_pdf = None
    if tender.documents:
        for doc in tender.documents:
            if doc.storage_path and doc.processing_status == "INDEXED":
                try:
                    p = tender_service.storage.get_file_path(doc.storage_path)
                    if p.exists():
                        downloaded_pdf = str(p)
                        break
                except Exception:
                    pass

    image_service = get_tender_image_service()
    meta = await image_service.get_tender_image_meta(
        tender_id=str(tender.id),
        title=tender.title,
        sector=tender.sector,
        downloaded_pdf_path=downloaded_pdf,
    )

    return TenderImageMetaResponse(
        tender_id=tender.id,
        image_url=meta["image_url"],
        category_key=meta["category_key"],
        source=meta["source"],
        query=meta["query"],
        attribution=meta.get("attribution"),
        license=meta.get("license"),
    )


@router.get(
    "/tenders/{tender_id}/image",
    summary="Serve the cached or document-extracted image for a tender",
)
async def get_tender_image(
    tender_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Serve the local image file for the given tender with persistent cache headers."""
    # Check if extracted image exists
    extracted_file = TENDER_IMAGES_DIR / f"{tender_id}_extracted.jpg"
    if extracted_file.exists():
        return FileResponse(
            path=str(extracted_file),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=604800"},
        )

    # Resolve tender category and check query cache
    tender_service = TenderService(session)
    try:
        tender = await tender_service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    image_service = get_tender_image_service()
    meta = await image_service.get_tender_image_meta(
        tender_id=str(tender.id),
        title=tender.title,
        sector=tender.sector,
    )

    # If it's a cached file, serve it
    if meta["source"] in ("DOCUMENT_EXTRACTED", "LOCAL_CACHE"):
        filename = meta["image_url"].split("/")[-1]
        file_path = TENDER_IMAGES_DIR / filename
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=604800"},
            )

    # Return category SVG fallback
    cat_key = meta["category_key"]
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/images/tender-categories/{cat_key}.svg")


@router.get(
    "/tender-images/{filename}",
    summary="Serve a locally cached tender product image",
)
async def get_cached_tender_image(filename: str):
    """Serve locally cached image file with strict path safety."""
    safe_name = os.path.basename(filename)
    file_path = TENDER_IMAGES_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    ext = safe_name.split(".")[-1].lower()
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=604800"},
    )


@router.post(
    "/tenders/{tender_id}/qa",
    response_model=TenderQAResponse,
    summary="Ask a document-grounded question about a tender (Phase 9)",
)
async def ask_tender_question(
    tender_id: uuid.UUID,
    request: TenderQARequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Perform hybrid retrieval over the selected tender's authorized document corpus,
    validate physical citation bounds, and synthesize an evidence-backed answer.
    """
    qa_service = TenderQAService(session)
    response = await qa_service.answer_question(tender_id=tender_id, question=request.question)
    if response.status == "ERROR":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.answer)
    return response


# ============================================================================
# Administrative Tender Management Endpoints (ADMIN Role Only)
# ============================================================================

@router.post(
    "/admin/tenders",
    response_model=TenderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tender opportunity (Admin only)",
)
async def create_tender(
    tender_in: TenderCreate,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Create a new tender record with deterministic eligibility criteria."""
    service = TenderService(session)
    try:
        tender = await service.create_tender(tender_in, created_by=current_admin.id)
        return TenderResponse.model_validate(tender)
    except TenderServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/admin/tenders/{tender_id}",
    response_model=TenderResponse,
    summary="Update tender details (Admin only)",
)
async def update_tender(
    tender_id: uuid.UUID,
    tender_in: TenderUpdate,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Update tender metadata and requirements."""
    service = TenderService(session)
    try:
        tender = await service.update_tender(tender_id, tender_in)
        return TenderResponse.model_validate(tender)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/admin/tenders/{tender_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tender and purge vector indexes (Admin only)",
)
async def delete_tender(
    tender_id: uuid.UUID,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Delete tender, cascade documents, and purge associated ChromaDB vectors."""
    service = TenderService(session)
    try:
        await service.delete_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/admin/tenders/{tender_id}/upload-docs",
    response_model=List[TenderDocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload tender PDF attachments (Admin only)",
)
async def upload_tender_documents(
    tender_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Upload one or more PDF notices or specifications for a tender."""
    service = TenderService(session)
    try:
        created_docs = await service.upload_tender_documents(
            tender_id=tender_id,
            files=files,
            user_id=current_admin.id,
        )
        return [TenderDocumentResponse.model_validate(d) for d in created_docs]
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TenderServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/admin/tenders/{tender_id}/process",
    response_model=TenderResponse,
    summary="Trigger text extraction and ChromaDB vector indexing (Admin only)",
)
async def process_tender_documents(
    tender_id: uuid.UUID,
    document_id: Optional[uuid.UUID] = Query(None, description="Optional specific document to reprocess"),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Extract text from PDF pages, run OCR if needed, chunk, and index into ChromaDB."""
    service = TenderService(session)
    try:
        tender = await service.process_tender_documents(tender_id=tender_id, document_id=document_id)
        return TenderResponse.model_validate(tender)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Processing failed: {e}")


@router.get(
    "/admin/tenders/{tender_id}/processing-status",
    response_model=TenderProcessingStatusResponse,
    summary="Get processing status and extraction breakdown (Admin only)",
)
async def get_tender_processing_status(
    tender_id: uuid.UUID,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Check indexing status, page count, and extraction metadata for tender documents."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
        return TenderProcessingStatusResponse(
            tender_id=tender.id,
            processing_status=tender.processing_status,
            total_documents=len(tender.documents),
            documents=[TenderDocumentResponse.model_validate(d) for d in tender.documents],
        )
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# Administrative Automated Requirement Extraction & Approval Workflow (Phase 4)
# ============================================================================

@router.post(
    "/admin/tenders/{tender_id}/extract-requirements",
    response_model=ProposedRequirementsBundle,
    summary="Trigger automated criteria extraction from indexed tender documents",
)
async def extract_tender_requirements(
    tender_id: uuid.UUID,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """
    Extract structured eligibility criteria from physical document pages.
    Preserves document page numbers and excerpts, detects conflicts, and saves
    proposed criteria pending administrator approval.
    """
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Retrieve all document chunks for this tender
    stmt = (
        select(DocumentChunkModel)
        .where(DocumentChunkModel.tender_id == tender.id)
        .order_by(DocumentChunkModel.page_number, DocumentChunkModel.chunk_index)
    )
    result = await session.execute(stmt)
    chunks = list(result.scalars().all())

    extractor = RequirementExtractionService()
    bundle = extractor.extract_from_chunks(tender=tender, chunks=chunks)

    # Persist proposed requirements and update status to PENDING_REVIEW
    tender.proposed_requirements = bundle.model_dump(mode="json")
    tender.requirements_approval_status = "PENDING_REVIEW"
    await session.commit()
    await session.refresh(tender)

    return bundle


@router.get(
    "/admin/tenders/{tender_id}/proposed-requirements",
    response_model=Optional[ProposedRequirementsBundle],
    summary="Get proposed requirements and extraction provenance for review",
)
async def get_proposed_requirements(
    tender_id: uuid.UUID,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve proposed requirements, supporting excerpts, and detected conflicts."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not tender.proposed_requirements:
        return None
    return ProposedRequirementsBundle.model_validate(tender.proposed_requirements)


@router.post(
    "/admin/tenders/{tender_id}/approve-requirements",
    response_model=TenderResponse,
    summary="Approve proposed requirements to become authoritative for deterministic evaluation",
)
async def approve_tender_requirements(
    tender_id: uuid.UUID,
    body: Optional[ApproveRequirementsRequest] = None,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """
    Promote proposed requirements (or provided overrides) to authoritative
    structured_requirements used by the deterministic compliance engine.
    """
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Determine criteria payload: explicit override or proposed normalized preview
    criteria_payload = None
    if body and body.criteria_override:
        criteria_payload = body.criteria_override
    elif tender.proposed_requirements and "normalized_preview" in tender.proposed_requirements:
        criteria_payload = tender.proposed_requirements["normalized_preview"]

    if not criteria_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No proposed requirements found to approve and no criteria override provided.",
        )

    # Validate against strict typed NormalizedTenderRequirements
    try:
        normalized = RequirementNormalizer.normalize(criteria_payload, tender_deadline=tender.submission_deadline)
        authoritative_dict = normalized.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Proposed criteria failed validation against authoritative schema: {e}",
        )

    tender.structured_requirements = authoritative_dict
    tender.requirements_approval_status = "APPROVED"
    await session.commit()
    await session.refresh(tender)

    return TenderResponse.model_validate(tender)


@router.post(
    "/admin/tenders/{tender_id}/reject-requirements",
    response_model=TenderResponse,
    summary="Reject proposed requirements without updating authoritative criteria",
)
async def reject_tender_requirements(
    tender_id: uuid.UUID,
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Mark proposed criteria as REJECTED. Preserves existing structured_requirements untouched."""
    service = TenderService(session)
    try:
        tender = await service.get_tender(tender_id)
    except TenderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    tender.requirements_approval_status = "REJECTED"
    await session.commit()
    await session.refresh(tender)

    return TenderResponse.model_validate(tender)

