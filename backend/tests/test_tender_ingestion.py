import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tender import Tender
from app.models.ingestion_run import IngestionRun
from app.models.user import User
from app.services.ingestion.cppp_connector import CPPPTenderConnector
from app.services.ingestion.gem_connector import GeMTenderConnector
from app.services.ingestion.open_gov_connector import OpenGovDataConnector
from app.services.ingestion.ingestion_service import TenderIngestionService
from app.services.ingestion_scheduler import TenderIngestionScheduler


@pytest_asyncio.fixture
async def admin_auth_headers(db_session: AsyncSession) -> dict:
    """Fixture providing valid JWT headers for an ADMIN user."""
    admin = User(
        email="admin_ingest@tenderbid.gov.in",
        hashed_password="hashed_password_sample_2026",
        full_name="Portal Administrator",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    token = create_access_token(subject=str(admin.id), role=admin.role)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def msme_auth_headers(db_session: AsyncSession) -> dict:
    """Fixture providing valid JWT headers for a standard MSME user."""
    user = User(
        email="msme_bidder@vendor.in",
        hashed_password="hashed_password_sample_2026",
        full_name="MSME Bidder",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_gem_connector_normalization_and_blocker():
    """Verify GeM connector normalizes records and documents anti-bot/API requirements."""
    connector = GeMTenderConnector()
    assert connector.portal_name == "GEM"

    avail = await connector.check_availability()
    assert avail["portal_name"] == "GEM"
    assert avail["status"] == "MOCK_FALLBACK"
    assert "Cloudflare/WAF" in avail["blocker_details"]

    records = await connector.fetch_tenders(limit=2)
    assert len(records) == 2
    for r in records:
        assert r.source_portal == "GEM"
        assert r.tender_reference.startswith("GEM/")
        assert r.estimated_budget_inr > 0
        assert r.submission_deadline > datetime.now(timezone.utc)
        assert r.official_portal_url.startswith("https://bidplus.gem.gov.in")
        assert r.structured_requirements is not None


@pytest.mark.asyncio
async def test_cppp_connector_normalization_and_captcha_blocker():
    """Verify CPPP connector documents graphical CAPTCHA restriction and provides valid records."""
    connector = CPPPTenderConnector()
    assert connector.portal_name == "CPPP"

    avail = await connector.check_availability()
    assert avail["portal_name"] == "CPPP"
    assert avail["status"] == "MOCK_FALLBACK"
    assert "graphical session CAPTCHA" in avail["blocker_details"]

    records = await connector.fetch_tenders(limit=2)
    assert len(records) == 2
    for r in records:
        assert r.source_portal == "CPPP"
        assert r.tender_reference.startswith("CPPP/")
        assert r.msme_emd_exemption is True
        assert "eprocure.gov.in" in r.official_portal_url


@pytest.mark.asyncio
async def test_open_gov_connector_normalization():
    """Verify Open Government Data connector provides active PSU procurement notices."""
    connector = OpenGovDataConnector()
    assert connector.portal_name == "OPEN_GOV"

    avail = await connector.check_availability()
    assert avail["status"] == "ACTIVE"
    assert avail["authenticated"] is True

    records = await connector.fetch_tenders(limit=2)
    assert len(records) == 2
    for r in records:
        assert r.source_portal == "OPEN_GOV"
        assert r.tender_reference.startswith("OPENGOV/")
        assert r.estimated_budget_inr > 0


@pytest.mark.asyncio
async def test_ingestion_service_deduplication_and_upsert(db_session: AsyncSession):
    """Verify that multiple sync runs idempotently insert then skip/update without duplicate error."""
    service = TenderIngestionService(db_session)

    # First sync: all tenders should be ingested
    run1 = await service.sync_portal(source_portal="ALL", limit=10)
    assert run1.status == "SUCCESS"
    assert run1.tenders_ingested > 0
    initial_ingested = run1.tenders_ingested

    # Verify rows in DB
    result = await db_session.execute(select(Tender))
    tenders = result.scalars().all()
    assert len(tenders) == initial_ingested

    # Second sync without force: should skip existing tenders without duplicate violation
    run2 = await service.sync_portal(source_portal="ALL", limit=10, force=False)
    assert run2.status == "SUCCESS"
    assert run2.tenders_ingested == 0
    assert run2.tenders_skipped == initial_ingested

    # Count in DB should remain unchanged
    result2 = await db_session.execute(select(Tender))
    assert len(result2.scalars().all()) == initial_ingested


@pytest.mark.asyncio
async def test_ingestion_scheduler_tick(db_session: AsyncSession):
    """Verify that TenderIngestionScheduler executes tick in isolated session and increments stats."""
    # Custom session factory returning our test session generator
    from app.db.session import async_sessionmaker
    session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    scheduler = TenderIngestionScheduler(
        session_factory=session_factory,
        interval_seconds=3600,
        enabled=True,
    )
    assert scheduler.execution_count == 0
    assert not scheduler.is_running

    run = await scheduler.tick()
    assert run is not None
    assert run.status == "SUCCESS"
    assert scheduler.execution_count == 1
    assert scheduler.last_sync_time is not None


@pytest.mark.asyncio
async def test_ingestion_api_flow(client: AsyncClient, admin_auth_headers: dict, msme_auth_headers: dict):
    """Verify API endpoints: status inspection, admin manual trigger, catalog visibility, and RBAC."""
    # 1. Inspect status as MSME user
    res_status = await client.get("/api/v1/tenders/ingestion/status", headers=msme_auth_headers)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "portals" in status_data
    assert len(status_data["portals"]) == 5
    portal_names = [p["portal_name"] for p in status_data["portals"]]
    assert "GEM" in portal_names
    assert "CPPP" in portal_names
    assert "OPEN_GOV" in portal_names
    assert "TENDERKART" in portal_names
    assert "APIFY" in portal_names

    # 2. MSME user cannot trigger sync (RBAC guard)
    res_sync_msme = await client.post(
        "/api/v1/tenders/ingestion/sync",
        headers=msme_auth_headers,
        json={"source_portal": "ALL"},
    )
    assert res_sync_msme.status_code == 403

    # 3. Admin user triggers sync
    res_sync_admin = await client.post(
        "/api/v1/tenders/ingestion/sync",
        headers=admin_auth_headers,
        json={"source_portal": "ALL", "batch_size": 20},
    )
    assert res_sync_admin.status_code == 200
    sync_data = res_sync_admin.json()
    assert sync_data["status"] == "SUCCESS"
    assert sync_data["tenders_ingested"] > 0

    # 4. Ingested tenders appear in public /tenders listing
    res_list = await client.get("/api/v1/tenders", headers=msme_auth_headers)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= sync_data["tenders_ingested"]
    first_item = list_data["items"][0]
    assert "source_portal" in first_item
    assert "official_portal_url" in first_item

    # 5. Filter by source portal
    res_filtered = await client.get("/api/v1/tenders?source_portal=GEM", headers=msme_auth_headers)
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.json()
    for item in filtered_data["items"]:
        assert item["source_portal"] == "GEM"
