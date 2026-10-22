from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.document import DocumentMetadataCreate, DocumentResponse
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentValidationError,
)

router = APIRouter(prefix="/company/vault/documents", tags=["Company Document Vault"])


@router.post(
    "",
    response_model=ResponseEnvelope[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register_vault_document(
    request: DocumentMetadataCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Register document metadata in the company's protected document vault."""
    service = DocumentService(session)
    try:
        doc = await service.register_metadata(current_user, request)
        return ResponseEnvelope(
            success=True,
            message="Document metadata registered in vault",
            data=doc,
        )
    except DocumentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=ResponseEnvelope[List[DocumentResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_vault_documents(
    category: Optional[str] = Query(default=None, description="Filter by document category"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List all documents owned by the authenticated company."""
    service = DocumentService(session)
    try:
        docs = await service.list_documents(current_user, category)
        return ResponseEnvelope(
            success=True,
            data=docs,
        )
    except DocumentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{document_id}",
    response_model=ResponseEnvelope[DocumentResponse],
    status_code=status.HTTP_200_OK,
)
async def get_vault_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve metadata for a specific document, strictly verifying tenant ownership."""
    service = DocumentService(session)
    try:
        doc = await service.get_document(current_user, document_id)
        return ResponseEnvelope(
            success=True,
            data=doc,
        )
    except (DocumentNotFoundError, DocumentValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )



@router.delete(
    "/{document_id}",
    response_model=ResponseEnvelope[dict],
    status_code=status.HTTP_200_OK,
)
async def delete_vault_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a document record from the company's vault."""
    service = DocumentService(session)
    try:
        await service.delete_document(current_user, document_id)
        return ResponseEnvelope(
            success=True,
            message="Document removed from vault",
            data={"document_id": str(document_id)},
        )
    except (DocumentNotFoundError, DocumentValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/upload",
    response_model=ResponseEnvelope[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload, extract, chunk, and index an MSME company vault PDF document",
)
async def upload_vault_document_file(
    file: UploadFile = File(...),
    document_category: str = Form("FINANCIAL_AUDIT"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Physically upload a PDF document to company vault, triggering extraction and vector indexing."""
    service = DocumentService(session)
    try:
        doc = await service.upload_vault_document(
            user=current_user,
            file=file,
            document_category=document_category,
        )
        return ResponseEnvelope(
            success=True,
            message="Document uploaded and indexed in company vault",
            data=doc,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


