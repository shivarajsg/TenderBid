import uuid
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.company import Company
from app.models.tender import Tender
from app.models.user import User


@pytest.mark.asyncio
async def test_bid_application_lifecycle_and_state_transitions(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test full bid lifecycle from IDENTIFIED to AWARDED with legal stage transitions."""
    user = User(
        id=uuid.uuid4(),
        email="msme_bid@example.com",
        hashed_password="hash",
        full_name="MSME Bidder",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)

    company = Company(
        id=uuid.uuid4(),
        owner_id=user.id,
        legal_name="Apex Power Systems Pvt Ltd",
        registration_number="APEX-PWR-9988",
        business_type="SMALL",
        sector="Electrical",
        incorporation_date=date(2018, 1, 1),
    )
    db_session.add(company)

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="BID/TRK/001",
        title="Solar Plant Inverter Supply",
        issuing_authority="SECI",
        sector="Solar",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(tender)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), role="MSME_USER")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create tracked bid application
    create_payload = {
        "tender_id": str(tender.id),
        "notes": "Targeting joint venture with local installer.",
    }
    resp = await client.post("/api/v1/applications", headers=headers, json=create_payload)
    assert resp.status_code == 201
    app_data = resp.json()
    assert app_data["status"] == "IDENTIFIED"
    assert app_data["tender_title"] == "Solar Plant Inverter Supply"
    app_id = app_data["id"]

    # 2. Attempt duplicate tracking -> 409 Conflict
    dup_resp = await client.post("/api/v1/applications", headers=headers, json=create_payload)
    assert dup_resp.status_code == 409

    # 3. Transition IDENTIFIED -> PREPARING (Legal)
    prep_resp = await client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "PREPARING", "notes": "Compiling financial balance sheets."},
    )
    assert prep_resp.status_code == 200
    assert prep_resp.json()["status"] == "PREPARING"

    # 4. Attempt illegal jump: PREPARING -> AWARDED (Must fail with 422)
    illegal_resp = await client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "AWARDED"},
    )
    assert illegal_resp.status_code == 422
    assert "Cannot transition" in illegal_resp.json()["message"]

    # 5. Transition PREPARING -> READY -> SUBMITTED -> AWARDED (Legal sequence)
    r1 = await client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "READY"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "READY"

    r2 = await client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "SUBMITTED"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "SUBMITTED"

    r3 = await client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "AWARDED"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "AWARDED"

    # 6. Terminal state cannot transition to anything
    term_resp = await client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "PREPARING"})
    assert term_resp.status_code == 422


@pytest.mark.asyncio
async def test_bid_application_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify Company A's tracked applications cannot be accessed or modified by Company B."""
    # User A & Company A
    user_a = User(id=uuid.uuid4(), email="user_a@test.com", hashed_password="h", full_name="User A", role="MSME_USER")
    comp_a = Company(id=uuid.uuid4(), owner_id=user_a.id, legal_name="Company A", registration_number="REG-A", business_type="SMALL", sector="IT", incorporation_date=date(2020, 1, 1))

    # User B & Company B
    user_b = User(id=uuid.uuid4(), email="user_b@test.com", hashed_password="h", full_name="User B", role="MSME_USER")
    comp_b = Company(id=uuid.uuid4(), owner_id=user_b.id, legal_name="Company B", registration_number="REG-B", business_type="SMALL", sector="IT", incorporation_date=date(2020, 1, 1))

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="ISO/BID/002",
        title="Cloud Migration Tender",
        issuing_authority="GovCloud",
        sector="IT",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([user_a, comp_a, user_b, comp_b, tender])
    await db_session.commit()

    token_a = create_access_token(subject=str(user_a.id), role="MSME_USER")
    token_b = create_access_token(subject=str(user_b.id), role="MSME_USER")

    # Company A creates a tracked application
    resp_a = await client.post(
        "/api/v1/applications",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"tender_id": str(tender.id), "notes": "Company A Private Notes"},
    )
    assert resp_a.status_code == 201
    app_id = resp_a.json()["id"]

    # Company B tries to view Company A's application -> 404 (Not Found prevents leakage)
    resp_b_get = await client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b_get.status_code == 404

    # Company B tries to update Company A's application -> 404
    resp_b_patch = await client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"status": "REJECTED"},
    )
    assert resp_b_patch.status_code == 404

    # Company B tries to delete Company A's application -> 404
    resp_b_del = await client.delete(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b_del.status_code == 404
