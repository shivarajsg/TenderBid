import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.tender import Tender
    from app.models.company import Company


class DocumentChunkModel(Base):
    """Authoritative relational record for document chunks used for lexical search and provenance."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    source_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    char_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    char_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    extraction_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pymupdf_direct",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", lazy="selectin")
    tender: Mapped[Optional["Tender"]] = relationship("Tender", lazy="selectin")
    company: Mapped[Optional["Company"]] = relationship("Company", lazy="selectin")
