import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company import Company
    from app.models.tender import Tender


class Document(Base):
    """Metadata record for corporate compliance documents and tender attachments."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    tender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        default="TENDER",
        nullable=False,  # "COMPANY" or "TENDER"
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    document_category: Mapped[str] = mapped_column(
        String(50),
        default="TENDER_NOTICE",
        nullable=False,  # FINANCIAL_AUDIT, TAX_RECORD, CERTIFICATION, WORK_ORDER, TENDER_NOTICE, TENDER_SPECIFICATION, TENDER_CORRIGENDUM
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    valid_from: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    valid_until: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNVERIFIED",  # UNVERIFIED, METADATA_EXTRACTED, VERIFIED_VALID, EXPIRED
    )

    # Document intelligence and vector indexing metadata (Phase 3)
    total_pages: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    indexed_chunks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        nullable=False,  # PENDING, EXTRACTING, INDEXED, PARTIALLY_INDEXED, FAILED
    )
    extraction_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        back_populates="documents",
    )
    tender: Mapped[Optional["Tender"]] = relationship(
        "Tender",
        back_populates="documents",
    )
    uploader: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="uploaded_documents",
    )
