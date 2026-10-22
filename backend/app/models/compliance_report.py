import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tender import Tender
    from app.models.company import Company
    from app.models.user import User
    from app.models.compliance_finding import ComplianceFinding


class ComplianceReport(Base):
    """Immutable, versioned evaluation report produced by the compliance engine."""

    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    generated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    overall_status: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,  # ELIGIBLE, NOT_ELIGIBLE, PARTIALLY_ELIGIBLE, NEEDS_REVIEW
    )
    overall_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    rule_engine_version: Mapped[str] = mapped_column(
        String(50),
        default="1.0.0",
        nullable=False,
    )
    tender_version_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    company_version_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    processing_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", lazy="selectin")
    company: Mapped["Company"] = relationship("Company", lazy="selectin")
    generator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[generated_by], lazy="selectin")
    findings: Mapped[List["ComplianceFinding"]] = relationship(
        "ComplianceFinding",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
