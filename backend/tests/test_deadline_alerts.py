import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.bid_application import BidApplication
from app.models.company import Company
from app.models.tender import Tender
from app.models.user import User
from app.services.alert_service import DeadlineAlertService


@pytest.mark.asyncio
async def test_deadline_alerts_48h_threshold_and_duplicate_prevention(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test that:
    1. Tenders closing within 48h trigger DEADLINE_48H notification.
    2. Tenders closing in 72h do NOT trigger notification yet.
    3. Running the check multiple times is idempotent (no duplicates).
    """
    fixed_now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    user = User(id=uuid.uuid4(), email="msme_alert@example.com", hashed_password="h", full_name="MSME Alert User", role="MSME_USER")
    company = Company(id=uuid.uuid4(), owner_id=user.id, legal_name="Alert Co", registration_number="REG-ALT-1", business_type="MICRO", sector="Civil", incorporation_date=date(2020, 1, 1))

    # Tender 1: Closes in 24 hours (Within 48h -> SHOULD ALERT)
    tender_urgent = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/URGENT/01",
        title="Urgent Road Repair",
        issuing_authority="PWD",
        sector="Civil",
        submission_deadline=fixed_now + timedelta(hours=24),
    )

    # Tender 2: Closes in 96 hours (Outside 48h -> SHOULD NOT ALERT)
    tender_later = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/LATER/02",
        title="Highway Expansion 2027",
        issuing_authority="NHAI",
        sector="Civil",
        submission_deadline=fixed_now + timedelta(hours=96),
    )

    db_session.add_all([user, company, tender_urgent, tender_later])

    # Track both tenders
    bid_urgent = BidApplication(id=uuid.uuid4(), company_id=company.id, tender_id=tender_urgent.id, status="PREPARING")
    bid_later = BidApplication(id=uuid.uuid4(), company_id=company.id, tender_id=tender_later.id, status="IDENTIFIED")
    db_session.add_all([bid_urgent, bid_later])
    await db_session.commit()

    # Run alert service with mock clock
    alert_service = DeadlineAlertService(session=db_session, clock_fn=lambda: fixed_now)
    alerts_generated = await alert_service.scan_and_generate_alerts(threshold_hours=48)
    assert alerts_generated == 1  # Only tender_urgent generated an alert

    # Run again immediately (idempotency test -> should generate 0 duplicates)
    alerts_second_run = await alert_service.scan_and_generate_alerts(threshold_hours=48)
    assert alerts_second_run == 0

    # Test API: Authenticated MSME lists notifications
    token = create_access_token(subject=str(user.id), role="MSME_USER")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    notif = data["items"][0]
    assert notif["notification_type"] == "DEADLINE_48H"
    assert "TDR/URGENT/01" in notif["title"]
    assert notif["is_read"] is False

    # Check unread count endpoint
    count_resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] == 1

    # Mark as read
    patch_resp = await client.patch(f"/api/v1/notifications/{notif['id']}/read", headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_read"] is True

    # Check unread count is now 0
    count_resp2 = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_deadline_alerts_overdue_handling(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that tenders with past deadlines trigger DEADLINE_OVERDUE notification."""
    fixed_now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    user = User(id=uuid.uuid4(), email="msme_overdue@example.com", hashed_password="h", full_name="MSME Overdue User", role="MSME_USER")
    company = Company(id=uuid.uuid4(), owner_id=user.id, legal_name="Overdue Co", registration_number="REG-OVD-1", business_type="MICRO", sector="IT", incorporation_date=date(2020, 1, 1))

    tender_expired = Tender(
        id=uuid.uuid4(),
        tender_reference="TDR/EXPIRED/99",
        title="Completed Software Tender",
        issuing_authority="NIC",
        sector="IT",
        submission_deadline=fixed_now - timedelta(hours=5),  # 5 hours ago
    )

    db_session.add_all([user, company, tender_expired])
    bid_expired = BidApplication(id=uuid.uuid4(), company_id=company.id, tender_id=tender_expired.id, status="PREPARING")
    db_session.add(bid_expired)
    await db_session.commit()

    alert_service = DeadlineAlertService(session=db_session, clock_fn=lambda: fixed_now)
    generated = await alert_service.scan_and_generate_alerts(threshold_hours=48)
    assert generated == 1

    token = create_access_token(subject=str(user.id), role="MSME_USER")
    resp = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["notification_type"] == "DEADLINE_OVERDUE"
    assert "Submission Closed" in items[0]["title"]
