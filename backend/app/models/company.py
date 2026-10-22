import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document


class Company(Base):
    """Company profile representing MSME credentials, turnover metrics, and certifications."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    registration_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    business_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SMALL",  # MICRO, SMALL, MEDIUM
    )
    sector: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    incorporation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    annual_turnover: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    certifications: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    work_experience: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
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
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="company",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="company",
        cascade="all, delete-orphan",
    )
