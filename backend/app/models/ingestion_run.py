import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionRun(Base):
    """Authoritative audit record of automated government tender ingestion executions."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_portal: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,  # ALL, GEM, CPPP, OPEN_GOV
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="RUNNING",
        index=True,
        nullable=False,  # RUNNING, SUCCESS, PARTIAL, FAILED
    )
    tenders_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tenders_ingested: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tenders_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tenders_skipped: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    run_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
