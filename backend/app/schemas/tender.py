import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TenderDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: Optional[uuid.UUID] = None
    original_filename: str
    document_category: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    total_pages: Optional[int] = None
    indexed_chunks: int = 0
    processing_status: str
    download_status: str = "DOWNLOADED"
    url_classification: Optional[str] = None
    extraction_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime


class FetchTenderDocumentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    status: str
    url_classification: str
    source_url: Optional[str] = None
    documents_retrieved: int = 0
    documents_indexed: int = 0
    documents: List[TenderDocumentResponse] = []
    official_portal_url: Optional[str] = None
    message: str
    error_details: Optional[str] = None


class TenderBase(BaseModel):
    tender_reference: str = Field(..., max_length=100, examples=["NTPC/ELECT/2026/0892"])
    title: str = Field(..., max_length=255, examples=["Procurement of Heavy-Duty Switchgear"])
    issuing_authority: str = Field(..., max_length=255, examples=["National Thermal Power Corporation"])
    sector: str = Field(..., max_length=100, examples=["Electrical Infrastructure"])
    estimated_budget_inr: Optional[Decimal] = Field(default=None, ge=0)
    emd_amount_inr: Optional[Decimal] = Field(default=None, ge=0)
    msme_emd_exemption: bool = True
    publication_date: Optional[datetime] = None
    submission_deadline: datetime
    official_portal_url: Optional[str] = Field(default=None, max_length=512)
    source_portal: str = Field(default="MANUAL", max_length=50, examples=["MANUAL", "GEM", "CPPP", "OPEN_GOV", "TENDERKART"])
    source_tender_id: Optional[str] = Field(default=None, max_length=100)
    last_synced_at: Optional[datetime] = None
    ingestion_metadata: Optional[Dict[str, Any]] = None
    structured_requirements: Optional[Dict[str, Any]] = None


class TenderCreate(TenderBase):
    pass


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    issuing_authority: Optional[str] = Field(default=None, max_length=255)
    sector: Optional[str] = Field(default=None, max_length=100)
    estimated_budget_inr: Optional[Decimal] = Field(default=None, ge=0)
    emd_amount_inr: Optional[Decimal] = Field(default=None, ge=0)
    msme_emd_exemption: Optional[bool] = None
    publication_date: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    official_portal_url: Optional[str] = Field(default=None, max_length=512)
    source_portal: Optional[str] = Field(default=None, max_length=50)
    source_tender_id: Optional[str] = Field(default=None, max_length=100)
    last_synced_at: Optional[datetime] = None
    ingestion_metadata: Optional[Dict[str, Any]] = None
    structured_requirements: Optional[Dict[str, Any]] = None


class TenderResponse(TenderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    processing_status: str
    proposed_requirements: Optional[Dict[str, Any]] = None
    requirements_approval_status: str = "APPROVED"
    created_by: Optional[uuid.UUID] = None
    documents: List[TenderDocumentResponse] = []
    created_at: datetime
    updated_at: datetime


class TenderListResponse(BaseModel):
    items: List[TenderResponse]
    total: int
    skip: int
    limit: int
    page: int = 1
    pages: int = 1


class TenderProcessingStatusResponse(BaseModel):
    tender_id: uuid.UUID
    processing_status: str
    total_documents: int
    documents: List[TenderDocumentResponse]


# ============================================================================
# Requirement Extraction & Approval Schemas (Phase 4)
# ============================================================================

class ProposedCriterionItem(BaseModel):
    criterion_type: str  # TURNOVER, EXPERIENCE, CERTIFICATION, MANDATORY_DOCUMENT, DEADLINE, EMD
    title: str
    extracted_value: Dict[str, Any]
    source_filename: str
    page_number: int
    document_id: Optional[str] = None
    supporting_excerpt: str
    status: str = "PROPOSED"  # PROPOSED, NEEDS_REVIEW, APPROVED, REJECTED
    confidence: float = 1.0
    review_notes: Optional[str] = None


class ProposedRequirementsBundle(BaseModel):
    tender_id: uuid.UUID
    extraction_status: str  # COMPLETED, PARTIAL, NEEDS_REVIEW, FAILED
    criteria: List[ProposedCriterionItem] = []
    conflicts: List[str] = []
    unsupported_clauses: List[str] = []
    normalized_preview: Optional[Dict[str, Any]] = None
    extracted_at: datetime


class ApproveRequirementsRequest(BaseModel):
    criteria_override: Optional[Dict[str, Any]] = None


# ============================================================================
# Tender Contextual Q&A Schemas (Phase 9)
# ============================================================================

class TenderQARequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


class QACitation(BaseModel):
    document_id: uuid.UUID
    source_filename: str
    page_number: int
    supporting_excerpt: str


class TenderQAResponse(BaseModel):
    tender_id: uuid.UUID
    question: str
    answer: str
    status: str  # ANSWERED, INSUFFICIENT_EVIDENCE, ERROR
    confidence: str  # HIGH, MEDIUM, LOW
    citations: List[QACitation] = []


# ============================================================================
# Extracted Tender Knowledge Schemas
# ============================================================================

class ExtractedChunkInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: uuid.UUID
    source_filename: str
    page_number: int
    chunk_index: int
    chunk_text: str
    extraction_method: str


class ExtractedDocumentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    original_filename: str
    document_category: str
    processing_status: str
    total_pages: Optional[int] = None
    indexed_chunks: int = 0
    extraction_metadata: Optional[Dict[str, Any]] = None


class TenderExtractedKnowledgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_reference: str
    title: str
    status: str
    total_documents: int
    total_chunks: int
    documents: List[ExtractedDocumentInfo] = []
    chunks: List[ExtractedChunkInfo] = []


