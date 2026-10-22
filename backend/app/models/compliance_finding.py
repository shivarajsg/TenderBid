import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.compliance_report import ComplianceReport


class ComplianceFinding(Base):
    """Detailed evaluation finding for a specific tender criterion."""

    __tablename__ = "compliance_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requirement_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    rule_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,  # TURNOVER, EXPERIENCE, CERTIFICATION, MANDATORY_DOCUMENT, DEADLINE, OTHER
    )
    requirement_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    required_value: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    observed_value: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,  # PASS, FAIL, MISSING_EVIDENCE, NEEDS_REVIEW, NOT_APPLICABLE
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    ai_explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence_citations: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    report: Mapped["ComplianceReport"] = relationship(
        "ComplianceReport",
        back_populates="findings",
    )
