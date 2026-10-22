from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentCategory(str, Enum):
    FINANCIAL_AUDIT = "FINANCIAL_AUDIT"
    TAX_RECORD = "TAX_RECORD"
    CERTIFICATION = "CERTIFICATION"
    WORK_ORDER = "WORK_ORDER"
    TENDER_RFP = "TENDER_RFP"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    METADATA_EXTRACTED = "METADATA_EXTRACTED"
    VERIFIED_VALID = "VERIFIED_VALID"
    EXPIRED = "EXPIRED"


class DocumentMetadataCreate(BaseModel):
    """Payload to register a document metadata record in the vault."""
    document_category: DocumentCategory
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(default="application/pdf", max_length=100)
    file_size_bytes: int = Field(gt=0, description="Size in bytes")
    sha256_hash: str = Field(min_length=64, max_length=64, description="Hex-encoded SHA-256")
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


class DocumentResponse(BaseModel):
    """Outbound representation of document vault metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    uploaded_by: Optional[UUID] = None
    document_category: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    verification_status: str
    processing_status: Optional[str] = None
    total_pages: Optional[int] = None
    indexed_chunks: Optional[int] = 0
    created_at: datetime
    updated_at: datetime
