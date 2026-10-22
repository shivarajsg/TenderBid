import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceCitation(BaseModel):
    """Standardized evidence citation model referencing verified document excerpts with provenance."""
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str = Field(..., description="Unique identifier for the evidence citation")
    source_type: str = Field(..., description="'TENDER_DOCUMENT' or 'COMPANY_DOCUMENT'")
    document_id: uuid.UUID = Field(..., description="Authoritative database document UUID")
    source_filename: str = Field(..., description="Original physical filename")
    page_number: int = Field(..., ge=1, description="1-based physical document page number")
    excerpt: str = Field(..., min_length=1, description="Exact textual excerpt from source document")
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    chunk_id: Optional[str] = None
    retrieval_method: str = Field(default="hybrid", description="'semantic', 'lexical', or 'hybrid'")
    relevance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sha256_hash: Optional[str] = None
