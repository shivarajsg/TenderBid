import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document


class Tender(Base):
    """Authoritative relational model for public tender notices and procurement criteria."""

    __tablename__ = "tenders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tender_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issuing_authority: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sector: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    estimated_budget_inr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    emd_amount_inr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    msme_emd_exemption: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    publication_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    official_portal_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    source_portal: Mapped[str] = mapped_column(
        String(50),
        default="MANUAL",
        server_default="MANUAL",
        index=True,
        nullable=False,  # MANUAL, GEM, CPPP, OPEN_GOV
    )
    source_tender_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ingestion_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    structured_requirements: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    proposed_requirements: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    requirements_approval_status: Mapped[str] = mapped_column(
        String(50),
        default="APPROVED",
        index=True,
        nullable=False,  # APPROVED, PENDING_REVIEW, REJECTED, NOT_REQUESTED
    )
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        nullable=False,  # PENDING, EXTRACTING, INDEXED, PARTIALLY_INDEXED, FAILED
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
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
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="tender",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )
