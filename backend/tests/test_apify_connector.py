"""
=============================================================================
Apify Actor Connector Unit & Integration Test Suite
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
Phase: Phase 11 — Optional Automated Government Tender Ingestion (Apify Provider)
Actor: foxlabs/india-government-tenders
=============================================================================
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
import pytest_asyncio
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.ingestion_run import IngestionRun
from app.services.ingestion.base_connector import RawTenderRecord
from app.services.ingestion.apify_connector import (
    ApifyTenderConnector,
    ApifyAPIError,
    ApifyAuthError,
    CANONICAL_APIFY_TENDERS,
)
from app.services.ingestion.ingestion_service import TenderIngestionService


@pytest.mark.asyncio
async def test_apify_connector_unconfigured_availability_and_fixtures(monkeypatch):
    """Verify Apify connector in unconfigured state returns transparent MOCK_FALLBACK with fixtures."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "APIFY_API_TOKEN", None)
    connector = ApifyTenderConnector(api_token=None)
    assert connector.portal_name == "APIFY"
    assert "foxlabs/india-government-tenders" in connector.official_url

    avail = await connector.check_availability()
    assert avail["portal_name"] == "APIFY"
    assert avail["status"] == "MOCK_FALLBACK"
    assert avail["authenticated"] is False
    assert "APIFY_API_TOKEN" in avail["blocker_details"]

    records = await connector.fetch_tenders(limit=2)
    assert len(records) == 2
    for r in records:
        assert r.source_portal == "APIFY"
        assert r.submission_deadline > datetime.now(timezone.utc)
        assert r.ingestion_metadata["provider"] == "APIFY"
        assert r.ingestion_metadata["is_fixture"] is True
        assert r.ingestion_metadata["data_source_mode"] == "CANONICAL_SCHEMA_FIXTURE"
        assert r.ingestion_metadata["has_full_documents"] is False
        assert "document_names" in r.ingestion_metadata


def test_apify_connector_auth_header_and_safe_repr():
    """Verify API tokens are never leaked in string representations and transmitted via Authorization."""
    secret = "apify_api_secret_test_token_9999"
    connector = ApifyTenderConnector(api_token=secret)
    headers = connector._get_headers()
    assert headers["Authorization"] == f"Bearer {secret}"

    rep = repr(connector)
    assert secret not in rep
    assert "authenticated=True" in rep
    assert "foxlabs" in rep


@pytest.mark.asyncio
async def test_apify_connector_availability_active_and_auth_error():
    """Verify check_availability probe identifies active 200 OK and 401 Unauthorized states."""
    # 1. Active State (200 OK from /users/me)
    async def handler_active(request: httpx.Request):
        if request.url.path.endswith("/users/me"):
            return httpx.Response(200, json={"data": {"id": "usr_1", "username": "tender_tester"}})
        return httpx.Response(404)

    client_active = httpx.AsyncClient(transport=httpx.MockTransport(handler_active))
    conn_active = ApifyTenderConnector(api_token="valid_token", client=client_active)
    avail_active = await conn_active.check_availability()
    assert avail_active["status"] == "ACTIVE"
    assert avail_active["authenticated"] is True
    assert avail_active["blocker_details"] is None

    # 2. Auth Required (401 Unauthorized)
    async def handler_unauth(request: httpx.Request):
        return httpx.Response(401, json={"error": {"type": "token-invalid", "message": "Invalid token"}})

    client_unauth = httpx.AsyncClient(transport=httpx.MockTransport(handler_unauth))
    conn_unauth = ApifyTenderConnector(api_token="invalid_token", client=client_unauth)
    avail_unauth = await conn_unauth.check_availability()
    assert avail_unauth["status"] == "AUTH_REQUIRED"
    assert avail_unauth["authenticated"] is False
    assert "unauthorized or expired" in avail_unauth["blocker_details"].lower()


@pytest.mark.asyncio
async def test_apify_connector_filters_summary_rows_only_imports_tenders():
    """
    Spec Invariant: Process only actual tender records (recordType == 'tender').
    Summary rows, run statistics, or non-tender dataset items must be strictly filtered out.
    """
    run_id = "test_run_123"
    dataset_id = "test_ds_456"

    async def actor_handler(request: httpx.Request):
        if request.url.path.endswith("/runs"):
            # Actor launch
            return httpx.Response(201, json={"data": {"id": run_id, "defaultDatasetId": dataset_id}})
        elif f"/actor-runs/{run_id}" in request.url.path:
            # Poll status
            return httpx.Response(200, json={"data": {"status": "SUCCEEDED", "usageTotalUsd": 0.003}})
        elif f"/datasets/{dataset_id}/items" in request.url.path:
            # Dataset items with mixed record types
            return httpx.Response(200, json=[
                {
                    "recordType": "summary",
                    "totalDiscovered": 150,
                    "portal": "eprocure.gov.in",
                    "note": "This is a summary aggregation row and MUST NOT be imported as a tender",
                },
                {
                    "recordType": "tender",
                    "tenderId": "2026_TEST_AMU_001",
                    "referenceNo": "AMU/ELECTRICAL/2026",
                    "title": "Internal Electrification Works at Main Campus",
                    "organisation": "Aligarh Muslim University",
                    "portal": "eprocure.gov.in",
                    "tenderCategory": "Electrical Works",
                    "tenderValueExact": 1200000.0,
                    "emdExact": 24000.0,
                    "publishedAt": "2026-10-21T10:00:00Z",
                    "bidSubmissionEndAt": "2026-11-05T15:00:00Z",
                    "documentNames": ["AMU_BOQ.xls", "NIT_Specification.pdf"],
                    "tenderUrl": "https://eprocure.gov.in/test/tender/1",
                },
                {
                    "recordType": "metadata_status",
                    "scrapedCount": 1,
                    "proxyType": "datacenter",
                },
                {
                    "recordType": "tender",
                    "tenderId": "2026_TEST_BPCL_002",
                    "referenceNo": "BPCL/LED/2026/99",
                    "title": "Kandla Port Smart Street LED Lighting Installation",
                    "organisation": "BPCL",
                    "portal": "cppp",
                    "tenderCategory": "Goods",
                    "tenderValueExact": 3500000.0,
                    "emdExact": 70000.0,
                    "publishedAt": "2026-10-21T12:00:00Z",
                    "bidSubmissionEndAt": "2026-11-12T17:00:00Z",
                    "documentNames": ["BPCL_Lighting_Spec.pdf"],
                    "tenderUrl": "https://eprocure.gov.in/test/tender/2",
                },
            ])
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(actor_handler))
    conn = ApifyTenderConnector(api_token="valid_token", client=client)

    records = await conn.fetch_tenders(limit=5)
    # Exactly 2 tenders should be returned (summary and metadata rows filtered out)
    assert len(records) == 2
    assert records[0].source_tender_id == "2026_TEST_AMU_001"
    assert records[1].source_tender_id == "2026_TEST_BPCL_002"
    assert records[0].ingestion_metadata["is_fixture"] is False
    assert records[0].ingestion_metadata["data_source_mode"] == "APIFY_ACTOR_LIVE"
    assert records[0].ingestion_metadata["document_names"] == ["AMU_BOQ.xls", "NIT_Specification.pdf"]


@pytest.mark.asyncio
async def test_apify_connector_actor_failure_handling():
    """Verify ApifyAPIError is raised when an actor run terminates with FAILED status."""
    run_id = "fail_run_789"

    async def fail_handler(request: httpx.Request):
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": run_id, "defaultDatasetId": "ds_fail"}})
        elif f"/actor-runs/{run_id}" in request.url.path:
            return httpx.Response(200, json={"data": {"status": "FAILED", "errorMessage": "Actor memory exceeded"}})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail_handler))
    conn = ApifyTenderConnector(api_token="valid_token", client=client)

    with pytest.raises(ApifyAPIError) as exc_info:
        await conn.fetch_tenders(limit=5)
    assert "non-success status 'FAILED'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_apify_ingestion_service_e2e_and_duplicate_prevention(db_session: AsyncSession):
    """
    End-to-end integration test:
    1. Ingestion service synchronizes live Apify tender records into PostgreSQL.
    2. Verifies persisted records with source_portal='APIFY'.
    3. Re-running the sync skips existing tenders without creating duplicate records.
    """
    run_id = "e2e_run_001"
    dataset_id = "e2e_ds_001"

    async def mock_handler(request: httpx.Request):
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": run_id, "defaultDatasetId": dataset_id}})
        elif f"/actor-runs/{run_id}" in request.url.path:
            return httpx.Response(200, json={"data": {"status": "SUCCEEDED", "usageTotalUsd": 0.003}})
        elif f"/datasets/{dataset_id}/items" in request.url.path:
            return httpx.Response(200, json=[
                {
                    "recordType": "tender",
                    "tenderId": "2026_AMU_931133_E2E",
                    "referenceNo": "AMU/E2E/2026/01",
                    "title": "E2E Verified Electrification Works",
                    "organisation": "Aligarh Muslim University",
                    "department": "Electricity Division",
                    "portal": "eprocure.gov.in",
                    "sourceName": "GePNIC — eprocure.gov.in",
                    "tenderCategory": "Electrical",
                    "tenderValueExact": 1850000.0,
                    "emdExact": 37000.0,
                    "publishedAt": "2026-10-21T10:00:00Z",
                    "bidSubmissionEndAt": "2026-11-20T17:00:00Z",
                    "documentNames": ["E2E_Tender_Document.pdf"],
                    "tenderUrl": "https://eprocure.gov.in/app?tenderId=2026_AMU_931133_E2E",
                    "scrapedAt": "2026-10-21T18:42:08.438Z",
                }
            ])
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    apify_conn = ApifyTenderConnector(api_token="valid_token", client=client)
    service = TenderIngestionService(db_session, connectors=[apify_conn])

    # 1. First sync tick: ingests new tender
    run1 = await service.sync_portal(source_portal="APIFY", limit=5)
    assert run1.status == "SUCCESS"
    assert run1.tenders_ingested == 1
    assert run1.tenders_skipped == 0
    assert run1.run_metadata["live_records_count"] == 1
    assert run1.run_metadata["fixture_records_count"] == 0

    # Verify PostgreSQL database entity
    stmt = select(Tender).where(
        Tender.source_portal == "APIFY",
        Tender.source_tender_id == "2026_AMU_931133_E2E",
    )
    res = await db_session.execute(stmt)
    tender_row = res.scalar_one_or_none()
    assert tender_row is not None
    assert tender_row.tender_reference == "AMU/E2E/2026/01"
    assert tender_row.issuing_authority == "Aligarh Muslim University"
    assert tender_row.estimated_budget_inr == Decimal("1850000.00")
    assert tender_row.emd_amount_inr == Decimal("37000.00")
    assert tender_row.ingestion_metadata["provider"] == "APIFY"
    assert tender_row.ingestion_metadata["origin_portal"] == "EPROCURE"
    assert tender_row.ingestion_metadata["is_fixture"] is False
    assert tender_row.ingestion_metadata["document_names"] == ["E2E_Tender_Document.pdf"]

    # 2. Second sync tick: re-running query MUST NOT create duplicates
    run2 = await service.sync_portal(source_portal="APIFY", limit=5, force=False)
    assert run2.status == "SUCCESS"
    assert run2.tenders_ingested == 0
    assert run2.tenders_skipped == 1

    # Verify row count in DB is still exactly 1
    count_stmt = select(Tender).where(
        Tender.source_portal == "APIFY",
        Tender.source_tender_id == "2026_AMU_931133_E2E",
    )
    all_rows = (await db_session.execute(count_stmt)).scalars().all()
    assert len(all_rows) == 1


@pytest.mark.asyncio
async def test_apify_reference_collision_safe_isolation(db_session: AsyncSession):
    """
    Verify that when an Apify notice shares a reference number with an existing tender
    from another portal, the Apify tender reference is safely differentiated to satisfy
    PostgreSQL's unique constraint while preserving the original referenceNo in metadata.
    """
    # 1. Existing tender from GeM
    existing_gem = Tender(
        id=uuid.uuid4(),
        tender_reference="DUPLICATE/REF/2026",
        title="Existing GeM Tender with Shared Reference",
        issuing_authority="BHEL",
        sector="Electrical",
        submission_deadline=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        source_portal="GEM",
        source_tender_id="GEM-COLL-99",
        last_synced_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_gem)
    await db_session.commit()

    # 2. Ingest Apify tender with the identical reference number
    run_id = "coll_run_01"
    dataset_id = "coll_ds_01"

    async def coll_handler(request: httpx.Request):
        if request.url.path.endswith("/runs"):
            return httpx.Response(201, json={"data": {"id": run_id, "defaultDatasetId": dataset_id}})
        elif f"/actor-runs/{run_id}" in request.url.path:
            return httpx.Response(200, json={"data": {"status": "SUCCEEDED"}})
        elif f"/datasets/{dataset_id}/items" in request.url.path:
            return httpx.Response(200, json=[{
                "recordType": "tender",
                "tenderId": "2026_APIFY_COLLISION_01",
                "referenceNo": "DUPLICATE/REF/2026",  # Identical reference
                "title": "Apify Tender with Shared Reference",
                "organisation": "CPWD",
                "portal": "eprocure.gov.in",
                "tenderValueExact": 500000.0,
                "bidSubmissionEndAt": "2026-12-05T10:00:00Z",
                "tenderUrl": "https://eprocure.gov.in/coll/1",
            }])
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(coll_handler))
    apify_conn = ApifyTenderConnector(api_token="valid_token", client=client)
    service = TenderIngestionService(db_session, connectors=[apify_conn])

    run = await service.sync_portal(source_portal="APIFY", limit=5)
    assert run.status == "SUCCESS"
    assert run.tenders_ingested == 1

    # Verify both tenders coexist without unique constraint violation
    gem_tender = (await db_session.execute(select(Tender).where(Tender.source_portal == "GEM"))).scalar_one()
    apify_tender = (await db_session.execute(select(Tender).where(Tender.source_portal == "APIFY", Tender.source_tender_id == "2026_APIFY_COLLISION_01"))).scalar_one()

    assert gem_tender.tender_reference == "DUPLICATE/REF/2026"
    assert apify_tender.tender_reference.startswith("DUPLICATE/REF/2026 (APIFY-")
    assert apify_tender.ingestion_metadata["tender_reference_number"] == "DUPLICATE/REF/2026"


@pytest.mark.asyncio
async def test_apify_service_overview_registration(db_session: AsyncSession):
    """Verify that Apify connector is registered in TenderIngestionService overview."""
    service = TenderIngestionService(db_session)
    assert "APIFY" in service.connectors

    overview = await service.get_overview()
    apify_portal = next((p for p in overview.portals if p.portal_name == "APIFY"), None)
    assert apify_portal is not None
    assert apify_portal.portal_title == "Apify India Government Tenders Feed"
    assert "foxlabs/india-government-tenders" in apify_portal.official_url
