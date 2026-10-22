import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tender import Tender
from app.schemas.tender import TenderCreate, TenderUpdate


class TenderRepository:
    """Async database repository for managing Tender relational entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tender_in: TenderCreate, created_by: Optional[uuid.UUID] = None) -> Tender:
        """Create a new Tender opportunity."""
        tender = Tender(
            tender_reference=tender_in.tender_reference,
            title=tender_in.title,
            issuing_authority=tender_in.issuing_authority,
            sector=tender_in.sector,
            estimated_budget_inr=tender_in.estimated_budget_inr,
            emd_amount_inr=tender_in.emd_amount_inr,
            msme_emd_exemption=tender_in.msme_emd_exemption,
            publication_date=tender_in.publication_date,
            submission_deadline=tender_in.submission_deadline,
            official_portal_url=tender_in.official_portal_url,
            source_portal=getattr(tender_in, "source_portal", "MANUAL") or "MANUAL",
            source_tender_id=getattr(tender_in, "source_tender_id", None),
            last_synced_at=getattr(tender_in, "last_synced_at", None),
            ingestion_metadata=getattr(tender_in, "ingestion_metadata", None),
            structured_requirements=tender_in.structured_requirements,
            created_by=created_by,
        )
        self.session.add(tender)
        await self.session.commit()
        await self.session.refresh(tender)
        return tender

    async def get_by_id(self, tender_id: uuid.UUID) -> Optional[Tender]:
        """Retrieve a tender by UUID including attached documents."""
        stmt = (
            select(Tender)
            .options(selectinload(Tender.documents))
            .where(Tender.id == tender_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> Optional[Tender]:
        """Retrieve a tender by unique reference identifier."""
        stmt = (
            select(Tender)
            .options(selectinload(Tender.documents))
            .where(Tender.tender_reference == reference)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_portal_and_id(self, source_portal: str, source_tender_id: str) -> Optional[Tender]:
        """Retrieve a tender by source portal and external source tender identifier."""
        stmt = (
            select(Tender)
            .options(selectinload(Tender.documents))
            .where(
                Tender.source_portal == source_portal,
                Tender.source_tender_id == source_tender_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 20,
        sector: Optional[str] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        deadline_after: Optional[datetime] = None,
        search: Optional[str] = None,
        source_portal: Optional[str] = None,
    ) -> Tuple[List[Tender], int]:
        """List tenders with optional filtering, search, and pagination."""
        query = select(Tender).options(selectinload(Tender.documents))
        count_query = select(func.count()).select_from(Tender)

        filters = []
        if source_portal:
            filters.append(Tender.source_portal == source_portal.upper())
        if sector:
            filters.append(Tender.sector.ilike(f"%{sector}%"))
        if min_budget is not None:
            filters.append(Tender.estimated_budget_inr >= min_budget)
        if max_budget is not None:
            filters.append(Tender.estimated_budget_inr <= max_budget)
        if deadline_after is not None:
            filters.append(Tender.submission_deadline >= deadline_after)
        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    Tender.title.ilike(search_pattern),
                    Tender.tender_reference.ilike(search_pattern),
                    Tender.issuing_authority.ilike(search_pattern),
                )
            )

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        # Count total
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Sort by submission_deadline ascending
        query = query.order_by(Tender.submission_deadline.asc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update(self, tender: Tender, update_data: Dict[str, Any]) -> Tender:
        """Update fields of an existing tender."""
        for field, value in update_data.items():
            if hasattr(tender, field) and value is not None:
                setattr(tender, field, value)

        await self.session.commit()
        await self.session.refresh(tender)
        return tender

    async def delete(self, tender: Tender) -> None:
        """Delete tender and cascade delete associated documents."""
        await self.session.delete(tender)
        await self.session.commit()
