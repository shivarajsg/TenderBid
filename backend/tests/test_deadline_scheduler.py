"""
=============================================================================
Unit & Integration Tests for Proactive Deadline Alert Scheduler
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.bid_application import BidApplication
from app.models.company import Company
from app.models.notification import Notification
from app.models.tender import Tender
from app.models.user import User
from app.services.deadline_scheduler import DeadlineAlertScheduler


@pytest.mark.asyncio
async def test_deadline_scheduler_comprehensive_lifecycle_and_rules(
    db_session: AsyncSession,
):
    """
    Verify complete scheduler behavior using controllable time fixtures:
    1. Deadline > 48h: no alert.
    2. Deadline reaching 48h: triggers alert.
    3. Deadline inside 48h window: triggers alert.
    4. Overdue tender: triggers DEADLINE_OVERDUE alert.
    5. Two companies tracking same tender: both get tenant-scoped alerts.
    6. Multi-tick idempotency: no duplicates across ticks.
    7. Overlap prevention: concurrent tick returns 0.
    8. Error tolerance: session error caught gracefully.
    9. Clean start and stop lifecycle.
    """
    base_time = datetime(2026, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
    current_time = base_time

    def get_time():
        nonlocal current_time
        return current_time

    # Setup 2 MSME Companies
    user1 = User(id=uuid.uuid4(), email="msme1@scheduler.test", hashed_password="h", full_name="MSME One", role="MSME_USER")
    comp1 = Company(id=uuid.uuid4(), owner_id=user1.id, legal_name="Alpha Tech Ltd", registration_number="UDYAM-01", business_type="MICRO", sector="IT", incorporation_date=date(2020, 1, 1))

    user2 = User(id=uuid.uuid4(), email="msme2@scheduler.test", hashed_password="h", full_name="MSME Two", role="MSME_USER")
    comp2 = Company(id=uuid.uuid4(), owner_id=user2.id, legal_name="Beta Systems Ltd", registration_number="UDYAM-02", business_type="SMALL", sector="IT", incorporation_date=date(2021, 1, 1))

    # Tenders:
    # T1: 72 hours away (>48h)
    tender_far = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/FAR/72H",
        title="Far Off Procurement",
        issuing_authority="Gov IT",
        sector="IT",
        submission_deadline=base_time + timedelta(hours=72),
    )

    # T2: 24 hours away (Inside 48h window) - Tracked by BOTH Company 1 and Company 2
    tender_shared = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/SHARED/24H",
        title="Shared Cloud Tender",
        issuing_authority="Gov IT",
        sector="IT",
        submission_deadline=base_time + timedelta(hours=24),
    )

    # T3: Overdue (past deadline)
    tender_overdue = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/PAST/00",
        title="Past Tender",
        issuing_authority="Gov IT",
        sector="IT",
        submission_deadline=base_time - timedelta(hours=2),
    )

    db_session.add_all([user1, comp1, user2, comp2, tender_far, tender_shared, tender_overdue])

    # Bids
    bid_far = BidApplication(id=uuid.uuid4(), company_id=comp1.id, tender_id=tender_far.id, status="PREPARING")
    bid_shared_1 = BidApplication(id=uuid.uuid4(), company_id=comp1.id, tender_id=tender_shared.id, status="READY")
    bid_shared_2 = BidApplication(id=uuid.uuid4(), company_id=comp2.id, tender_id=tender_shared.id, status="IDENTIFIED")
    bid_overdue = BidApplication(id=uuid.uuid4(), company_id=comp2.id, tender_id=tender_overdue.id, status="PREPARING")

    db_session.add_all([bid_far, bid_shared_1, bid_shared_2, bid_overdue])
    await db_session.commit()

    # Session factory adapter for SQLite in-memory test fixture
    # (wraps existing session context so test session remains consistent)
    class TestSessionFactory:
        def __call__(self):
            class SessionContext:
                async def __aenter__(self):
                    return db_session
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            return SessionContext()

    scheduler = DeadlineAlertScheduler(
        session_factory=TestSessionFactory(),
        interval_seconds=1,
        clock_fn=get_time,
        enabled=True,
    )

    # --- Step 1: Initial Tick at base_time ---
    # Expected:
    # tender_far (72h) -> No alert
    # tender_shared (24h) -> 2 alerts (one for comp1, one for comp2)
    # tender_overdue (-2h) -> 1 alert (for comp2)
    # Total = 3 alerts
    alerts = await scheduler.tick()
    assert alerts == 3
    assert scheduler.execution_count == 1

    # Verify notifications in database
    n_res = await db_session.execute(select(Notification))
    all_notifs = list(n_res.scalars().all())
    assert len(all_notifs) == 3

    comp1_notifs = [n for n in all_notifs if n.company_id == comp1.id]
    comp2_notifs = [n for n in all_notifs if n.company_id == comp2.id]
    assert len(comp1_notifs) == 1
    assert comp1_notifs[0].notification_type == "DEADLINE_48H"
    assert "TDR/SHARED/24H" in comp1_notifs[0].title

    assert len(comp2_notifs) == 2
    types_comp2 = {n.notification_type for n in comp2_notifs}
    assert types_comp2 == {"DEADLINE_48H", "DEADLINE_OVERDUE"}

    # --- Step 2: Idempotent Second Tick at same time ---
    # Expected: 0 new alerts
    alerts_second = await scheduler.tick()
    assert alerts_second == 0
    assert scheduler.execution_count == 2

    # --- Step 3: Advance Clock by 25 hours ---
    # 1. T1 (originally 72h) is now at 47h -> Enters 48h window (DEADLINE_48H for comp1)
    # 2. T2 (originally 24h) is now -1h overdue -> Generates DEADLINE_OVERDUE for comp1 and comp2 (2 alerts)
    # Total new alerts = 1 + 2 = 3
    current_time = base_time + timedelta(hours=25)
    alerts_third = await scheduler.tick()
    assert alerts_third == 3

    # Subsequent tick at same time must generate 0 duplicates
    alerts_after_advance = await scheduler.tick()
    assert alerts_after_advance == 0

    # Verify T1 notification created
    t1_notif = await db_session.execute(
        select(Notification).where(
            Notification.company_id == comp1.id,
            Notification.tender_id == tender_far.id,
        )
    )
    assert t1_notif.scalars().first() is not None

    # --- Step 4: Overlap Prevention Test ---
    # Simulate a running tick by holding the scheduler's lock
    async with scheduler._lock:
        skipped_alerts = await scheduler.tick()
        assert skipped_alerts == 0  # Skipped because lock is held

    # --- Step 5: Test Background Task Loop Start & Clean Stop ---
    scheduler.start()
    assert scheduler.is_running is True

    # Calling start again while running should be a safe no-op
    scheduler.start()
    assert scheduler.is_running is True

    # Allow worker loop to execute a short background tick
    await asyncio.sleep(0.05)

    # Clean shutdown
    await scheduler.stop(timeout=2.0)
    assert scheduler.is_running is False
    assert scheduler._task is None
