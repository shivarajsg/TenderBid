import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid_application import BidApplication
from app.models.company import Company
from app.models.notification import Notification
from app.models.tender import Tender
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Notification Provider Interface & Implementations
# ============================================================================

class NotificationProvider(ABC):
    """Abstract interface for dispatching notifications across delivery channels."""

    @abstractmethod
    async def dispatch(self, notification: Notification) -> bool:
        """Deliver the notification record. Returns True if delivered or queued."""
        pass


class InAppNotificationProvider(NotificationProvider):
    """Primary provider: records persistent notification in PostgreSQL."""

    async def dispatch(self, notification: Notification) -> bool:
        # In-app notifications are persisted directly via SQLAlchemy session
        return True


class EmailNotificationProvider(NotificationProvider):
    """
    Extensible email delivery provider.
    Currently unconfigured (requires SMTP_HOST, SENDGRID_API_KEY, or AWS SES).
    Documents missing configuration without falsely asserting delivery.
    """

    def __init__(self, smtp_host: Optional[str] = None):
        self.smtp_host = smtp_host

    async def dispatch(self, notification: Notification) -> bool:
        if not self.smtp_host:
            logger.info(
                f"[EmailNotificationProvider] External email channel not configured. "
                f"In-app notification persisted for company {notification.company_id}."
            )
            return False
        # External SMTP dispatch logic would execute here
        return True


# ============================================================================
# Proactive Deadline Alert Service
# ============================================================================

class DeadlineAlertService:
    """
    Evaluates closing tender deadlines against active tracked bids (and explicit watches),
    generating persistent, idempotent notifications 48 hours prior to closing.
    """

    def __init__(
        self,
        session: AsyncSession,
        clock_fn: Optional[Callable[[], datetime]] = None,
        provider: Optional[NotificationProvider] = None,
    ):
        self.session = session
        self.clock_fn = clock_fn or (lambda: datetime.now(timezone.utc))
        self.provider = provider or InAppNotificationProvider()

    async def scan_and_generate_alerts(self, threshold_hours: int = 48) -> int:
        """
        Scan active tracked applications (IDENTIFIED, PREPARING, READY),
        calculate UTC time to deadline, and generate alerts idempotently.
        """
        now_utc = self.clock_fn()
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        # 1. Fetch active bids with attached tender
        stmt = (
            select(BidApplication)
            .join(Tender, BidApplication.tender_id == Tender.id)
            .where(BidApplication.status.in_(["IDENTIFIED", "PREPARING", "READY"]))
        )
        res = await self.session.execute(stmt)
        active_bids = list(res.scalars().all())

        created_count = 0

        for bid in active_bids:
            tender = bid.tender
            if not tender or not tender.submission_deadline:
                continue

            deadline = tender.submission_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)

            time_delta = deadline - now_utc
            hours_remaining = time_delta.total_seconds() / 3600.0

            # Case A: Tender closing within threshold (e.g., 48 hours)
            if 0.0 <= hours_remaining <= float(threshold_hours):
                alert_created = await self._create_alert_idempotent(
                    company_id=bid.company_id,
                    tender_id=tender.id,
                    notification_type="DEADLINE_48H",
                    title=f"Deadline Approaching: {tender.tender_reference}",
                    message=(
                        f"Tender '{tender.title}' closes on {deadline.strftime('%Y-%m-%d %H:%M')} UTC "
                        f"(approximately {max(1, int(hours_remaining))} hours remaining). "
                        f"Please ensure all required documents and proofs are uploaded and verified."
                    ),
                )
                if alert_created:
                    created_count += 1

            # Case B: Tender is overdue / closed
            elif hours_remaining < 0.0:
                alert_created = await self._create_alert_idempotent(
                    company_id=bid.company_id,
                    tender_id=tender.id,
                    notification_type="DEADLINE_OVERDUE",
                    title=f"Submission Closed: {tender.tender_reference}",
                    message=(
                        f"The submission window for tender '{tender.title}' closed on "
                        f"{deadline.strftime('%Y-%m-%d %H:%M')} UTC."
                    ),
                )
                if alert_created:
                    created_count += 1

        if created_count > 0:
            await self.session.commit()

        return created_count

    async def _create_alert_idempotent(
        self,
        company_id: uuid.UUID,
        tender_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
    ) -> bool:
        """Insert notification only if not already present for this company, tender, and alert type."""
        # Check existing notification
        stmt = select(Notification).where(
            Notification.company_id == company_id,
            Notification.tender_id == tender_id,
            Notification.notification_type == notification_type,
        )
        res = await self.session.execute(stmt)
        if res.scalars().first():
            return False

        notification = Notification(
            id=uuid.uuid4(),
            company_id=company_id,
            tender_id=tender_id,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=False,
            created_at=self.clock_fn(),
        )
        self.session.add(notification)
        try:
            await self.session.flush()
            await self.provider.dispatch(notification)
            return True
        except IntegrityError:
            # Caught duplicate in concurrent execution
            await self.session.rollback()
            return False

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> NotificationListResponse:
        """Fetch notifications for authenticated MSME company."""
        company_stmt = select(Company).where(Company.owner_id == user_id)
        comp_res = await self.session.execute(company_stmt)
        company = comp_res.scalars().first()
        if not company:
            return NotificationListResponse(items=[], total=0, unread_count=0)

        # Base query
        query = (
            select(Notification)
            .where(Notification.company_id == company.id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        res = await self.session.execute(query)
        notifications = list(res.scalars().all())

        # Count total unread
        unread_stmt = (
            select(func.count(Notification.id))
            .where(
                Notification.company_id == company.id,
                Notification.is_read.is_(False),
            )
        )
        unread_res = await self.session.execute(unread_stmt)
        unread_count = unread_res.scalar() or 0

        items = [
            NotificationResponse(
                id=n.id,
                company_id=n.company_id,
                tender_id=n.tender_id,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at,
                tender_title=n.tender.title if n.tender else None,
                submission_deadline=n.tender.submission_deadline if n.tender else None,
            )
            for n in notifications
        ]

        return NotificationListResponse(
            items=items,
            total=len(items),
            unread_count=unread_count,
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Quick scalar count of unread notifications for badge display."""
        company_stmt = select(Company).where(Company.owner_id == user_id)
        comp_res = await self.session.execute(company_stmt)
        company = comp_res.scalars().first()
        if not company:
            return 0

        stmt = (
            select(func.count(Notification.id))
            .where(
                Notification.company_id == company.id,
                Notification.is_read.is_(False),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def mark_as_read(
        self,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> Optional[NotificationResponse]:
        """Mark single notification as read with tenant isolation."""
        company_stmt = select(Company).where(Company.owner_id == user_id)
        comp_res = await self.session.execute(company_stmt)
        company = comp_res.scalars().first()
        if not company:
            return None

        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.company_id == company.id,
        )
        res = await self.session.execute(stmt)
        notif = res.scalars().first()
        if not notif:
            return None

        notif.is_read = True
        await self.session.commit()
        await self.session.refresh(notif)

        return NotificationResponse(
            id=notif.id,
            company_id=notif.company_id,
            tender_id=notif.tender_id,
            notification_type=notif.notification_type,
            title=notif.title,
            message=notif.message,
            is_read=notif.is_read,
            created_at=notif.created_at,
            tender_title=notif.tender.title if notif.tender else None,
            submission_deadline=notif.tender.submission_deadline if notif.tender else None,
        )

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for current user's company."""
        company_stmt = select(Company).where(Company.owner_id == user_id)
        comp_res = await self.session.execute(company_stmt)
        company = comp_res.scalars().first()
        if not company:
            return 0

        stmt = (
            update(Notification)
            .where(
                Notification.company_id == company.id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount
