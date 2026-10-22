import logging
import uuid
from typing import List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid_application import BidApplication
from app.models.company import Company
from app.models.compliance_report import ComplianceReport
from app.models.tender import Tender
from app.schemas.bid_application import (
    BidApplicationCreate,
    BidApplicationResponse,
    BidApplicationUpdate,
)

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS = {
    "IDENTIFIED": {"PREPARING", "REJECTED"},
    "PREPARING": {"READY", "REJECTED", "IDENTIFIED"},
    "READY": {"SUBMITTED", "PREPARING", "REJECTED"},
    "SUBMITTED": {"AWARDED", "REJECTED"},
    "AWARDED": set(),
    "REJECTED": {"IDENTIFIED", "PREPARING"},
}


class BidTrackingError(Exception):
    """Base exception for bid tracking operations."""
    pass


class InvalidStateTransitionError(BidTrackingError):
    """Raised when an illegal lifecycle transition is attempted."""
    pass


class BidApplicationNotFoundError(BidTrackingError):
    """Raised when application is not found or inaccessible."""
    pass


class BidApplicationConflictError(BidTrackingError):
    """Raised when duplicate tracking is attempted."""
    pass


class BidTrackingService:
    """Manages the MSME internal bid preparation lifecycle with strict tenant isolation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_user_company(self, user_id: uuid.UUID) -> Company:
        """Resolve authenticated user's company profile. Never trusts client input."""
        stmt = select(Company).where(Company.owner_id == user_id)
        res = await self.session.execute(stmt)
        company = res.scalars().first()
        if not company:
            raise BidTrackingError("Company profile must be created before tracking tender applications.")
        return company

    async def create_bid_application(
        self,
        user_id: uuid.UUID,
        app_in: BidApplicationCreate,
    ) -> BidApplicationResponse:
        """Create a new tracked bid in IDENTIFIED stage for the authenticated MSME."""
        company = await self._get_user_company(user_id)

        # Verify tender exists
        tender_stmt = select(Tender).where(Tender.id == app_in.tender_id)
        tender_res = await self.session.execute(tender_stmt)
        tender = tender_res.scalars().first()
        if not tender:
            raise BidApplicationNotFoundError(f"Tender with ID '{app_in.tender_id}' not found.")

        # Check for duplicate tracking
        dup_stmt = select(BidApplication).where(
            BidApplication.company_id == company.id,
            BidApplication.tender_id == tender.id,
        )
        dup_res = await self.session.execute(dup_stmt)
        if dup_res.scalars().first():
            raise BidApplicationConflictError(
                f"Tender '{tender.tender_reference}' is already tracked in your application pipeline."
            )

        bid_app = BidApplication(
            id=uuid.uuid4(),
            company_id=company.id,
            tender_id=tender.id,
            status="IDENTIFIED",
            notes=app_in.notes,
            target_submission_date=app_in.target_submission_date,
        )
        self.session.add(bid_app)
        await self.session.commit()
        await self.session.refresh(bid_app)

        return await self._build_response(bid_app, tender, company.id)

    async def list_bid_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[BidApplicationResponse]:
        """List all tracked bids for the authenticated MSME company."""
        try:
            company = await self._get_user_company(user_id)
        except BidTrackingError:
            return []

        query = (
            select(BidApplication)
            .where(BidApplication.company_id == company.id)
            .order_by(desc(BidApplication.updated_at))
        )
        if status:
            query = query.where(BidApplication.status == status.upper())

        res = await self.session.execute(query)
        applications = list(res.scalars().all())

        results = []
        for app in applications:
            results.append(await self._build_response(app, app.tender, company.id))
        return results

    async def get_bid_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> BidApplicationResponse:
        """Fetch a single tracked application enforcing tenant ownership."""
        company = await self._get_user_company(user_id)

        stmt = select(BidApplication).where(
            BidApplication.id == application_id,
            BidApplication.company_id == company.id,
        )
        res = await self.session.execute(stmt)
        bid_app = res.scalars().first()
        if not bid_app:
            raise BidApplicationNotFoundError(f"Tracked application '{application_id}' not found.")

        return await self._build_response(bid_app, bid_app.tender, company.id)

    async def update_bid_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        app_update: BidApplicationUpdate,
    ) -> BidApplicationResponse:
        """Validate and apply state changes, notes, and target dates."""
        company = await self._get_user_company(user_id)

        stmt = select(BidApplication).where(
            BidApplication.id == application_id,
            BidApplication.company_id == company.id,
        )
        res = await self.session.execute(stmt)
        bid_app = res.scalars().first()
        if not bid_app:
            raise BidApplicationNotFoundError(f"Tracked application '{application_id}' not found.")

        # Validate stage transition
        if app_update.status:
            target_status = app_update.status.upper()
            if target_status != bid_app.status:
                allowed = ALLOWED_TRANSITIONS.get(bid_app.status, set())
                if target_status not in allowed:
                    raise InvalidStateTransitionError(
                        f"Cannot transition application from '{bid_app.status}' to '{target_status}'. "
                        f"Allowed next stages: {sorted(allowed) if allowed else 'None (Terminal state)'}."
                    )
                bid_app.status = target_status

        if app_update.notes is not None:
            bid_app.notes = app_update.notes
        if app_update.target_submission_date is not None:
            bid_app.target_submission_date = app_update.target_submission_date

        await self.session.commit()
        await self.session.refresh(bid_app)

        return await self._build_response(bid_app, bid_app.tender, company.id)

    async def delete_bid_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> None:
        """Remove a tracked bid from the pipeline (tenant-isolated)."""
        company = await self._get_user_company(user_id)

        stmt = select(BidApplication).where(
            BidApplication.id == application_id,
            BidApplication.company_id == company.id,
        )
        res = await self.session.execute(stmt)
        bid_app = res.scalars().first()
        if not bid_app:
            raise BidApplicationNotFoundError(f"Tracked application '{application_id}' not found.")

        await self.session.delete(bid_app)
        await self.session.commit()

    async def _build_response(
        self,
        app: BidApplication,
        tender: Optional[Tender],
        company_id: uuid.UUID,
    ) -> BidApplicationResponse:
        """Enrich BidApplicationResponse with latest tender and compliance metrics."""
        # Find latest compliance report for this company & tender
        rep_stmt = (
            select(ComplianceReport)
            .where(
                ComplianceReport.company_id == company_id,
                ComplianceReport.tender_id == app.tender_id,
            )
            .order_by(desc(ComplianceReport.created_at))
            .limit(1)
        )
        rep_res = await self.session.execute(rep_stmt)
        latest_rep = rep_res.scalars().first()

        return BidApplicationResponse(
            id=app.id,
            company_id=app.company_id,
            tender_id=app.tender_id,
            status=app.status,
            notes=app.notes,
            target_submission_date=app.target_submission_date,
            created_at=app.created_at,
            updated_at=app.updated_at,
            tender_title=tender.title if tender else None,
            tender_reference=tender.tender_reference if tender else None,
            submission_deadline=tender.submission_deadline if tender else None,
            estimated_budget_inr=tender.estimated_budget_inr if tender else None,
            sector=tender.sector if tender else None,
            latest_report_id=latest_rep.id if latest_rep else None,
            latest_compliance_status=latest_rep.overall_status if latest_rep else None,
            latest_compliance_score=latest_rep.overall_score if latest_rep else None,
        )
