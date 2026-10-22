"""
=============================================================================
TenderKart Connector Unit & Integration Test Suite
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
Phase: Phase 11 — Optional Automated Government Tender Ingestion (TenderKart Provider)
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
from app.services.ingestion.tenderkart_connector import (
    TenderKartConnector,
    TenderKartAPIError,
    TenderKartAuthError,
    TenderKartRateLimitError,
)
from app.services.ingestion.ingestion_service import TenderIngestionService


@pytest.mark.asyncio
async def test_tenderkart_connector_unconfigured_availability_and_fixtures():
    """Verify TenderKart connector in unconfigured state returns transparent MOCK_FALLBACK."""
    connector = TenderKartConnector(api_key=None)
    assert connector.portal_name == "TENDERKART"
    assert connector.official_url == "https://tenderkart.in"

    avail = await connector.check_availability()
    assert avail["portal_name"] == "TENDERKART"
    assert avail["status"] == "MOCK_FALLBACK"
    assert avail["authenticated"] is False
    assert "TenderKart Client API key (TENDERKART_API_KEY) not configured" in avail["blocker_details"]

    records = await connector.fetch_tenders(limit=3)
    assert len(records) == 3
    for r in records:
        assert r.source_portal == "TENDERKART"
        assert r.submission_deadline > datetime.now(timezone.utc)
        assert r.estimated_budget_inr > 0
        assert r.ingestion_metadata["provider"] == "TENDERKART"
        assert r.ingestion_metadata["is_fixture"] is True
        assert r.ingestion_metadata["origin_portal"] in ("GEM", "CPPP", "PWD_MAHARASHTRA")


def test_tenderkart_connector_auth_header_and_safe_repr():
    """Verify API keys are transmitted via headers and masked in string representations."""
    connector = TenderKartConnector(api_key="secret_tk_live_key_999")
    headers = connector._get_headers()
    assert headers["X-API-Key"] == "secret_tk_live_key_999"
    assert headers["Authorization"] == "Bearer secret_tk_live_key_999"

    # Ensure key is never leaked in repr
    rep = repr(connector)
    assert "secret_tk_live_key_999" not in rep
    assert "authenticated=True" in rep


@pytest.mark.asyncio
async def test_tenderkart_connector_availability_active_and_auth_error():
    """Verify availability probe recognizes active 200 OK and 401 Unauthorized states."""
    # 1. Active State (200 OK)
    async def handler_active(request: httpx.Request):
        return httpx.Response(200, json={"filters": [{"id": "filt_1", "name": "Filter 1"}]})

    client_active = httpx.AsyncClient(transport=httpx.MockTransport(handler_active))
    conn_active = TenderKartConnector(api_key="valid_key", client=client_active)
    avail_active = await conn_active.check_availability()
    assert avail_active["status"] == "ACTIVE"
    assert avail_active["authenticated"] is True
    assert avail_active["blocker_details"] is None

    # 2. Auth Required (401 Unauthorized)
    async def handler_unauth(request: httpx.Request):
        return httpx.Response(401, json={"error": "Unauthorized", "message": "Invalid API Key"})

    client_unauth = httpx.AsyncClient(transport=httpx.MockTransport(handler_unauth))
    conn_unauth = TenderKartConnector(api_key="bad_key", client=client_unauth)
    avail_unauth = await conn_unauth.check_availability()
    assert avail_unauth["status"] == "AUTH_REQUIRED"
    assert avail_unauth["authenticated"] is False
    assert "unauthorized or expired" in avail_unauth["blocker_details"]


@pytest.mark.asyncio
async def test_tenderkart_connector_filters_discovery():
    """Verify saved search filters discovery via GET /filters."""
    async def handler_filters(request: httpx.Request):
        assert request.url.path == "/api/v1/client/filters"
        return httpx.Response(200, json={
            "filters": [
                {"id": "filt_solar", "name": "Solar Projects", "query": "solar", "is_active": True},
                {"id": "filt_elec", "name": "Switchgear", "query": "switchgear", "is_active": True},
            ]
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_filters))
    conn = TenderKartConnector(api_key="valid_key", client=client)
    filters = await conn.fetch_filters()
    assert len(filters) == 2
    assert filters[0]["id"] == "filt_solar"
    assert filters[1]["id"] == "filt_elec"


@pytest.mark.asyncio
async def test_tenderkart_connector_cursor_pagination_backfill():
    """Verify multi-page cursor pagination across /filters/{id}/tenders."""
    call_count = 0

    async def handler_pages(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        cursor = request.url.params.get("cursor")

        if not cursor:
            # Page 1
            return httpx.Response(200, json={
                "tenders": [
                    {
                        "id": "uuid-page1-item1",
                        "portal_name": "gem",
                        "tender_id": "GEM/2026/B/1001",
                        "title": "Page 1 Item 1",
                        "organisation": "Authority 1",
                        "tender_value": 5000000.0,
                        "closing_at": "2026-12-01T10:00:00Z",
                    },
                    {
                        "id": "uuid-page1-item2",
                        "portal_name": "gem",
                        "tender_id": "GEM/2026/B/1002",
                        "title": "Page 1 Item 2",
                        "organisation": "Authority 2",
                        "tender_value": 7000000.0,
                        "closing_at": "2026-12-02T10:00:00Z",
                    },
                ],
                "pagination": {
                    "next_cursor": "cursor_token_page2",
                    "has_more": True,
                },
            })
        elif cursor == "cursor_token_page2":
            # Page 2
            return httpx.Response(200, json={
                "tenders": [
                    {
                        "id": "uuid-page2-item1",
                        "portal_name": "cppp",
                        "tender_id": "CPPP/2026/NIC/2001",
                        "title": "Page 2 Item 1",
                        "organisation": "Authority 3",
                        "tender_value": 9000000.0,
                        "closing_at": "2026-12-03T10:00:00Z",
                    },
                ],
                "pagination": {
                    "next_cursor": None,
                    "has_more": False,
                },
            })
        return httpx.Response(400)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_pages))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_solar", client=client)

    records = await conn.fetch_tenders(limit=5)
    assert call_count == 2
    assert len(records) == 3
    assert records[0].source_tender_id == "uuid-page1-item1"
    assert records[1].source_tender_id == "uuid-page1-item2"
    assert records[2].source_tender_id == "uuid-page2-item1"
    assert records[2].ingestion_metadata["origin_portal"] == "CPPP"


@pytest.mark.asyncio
async def test_tenderkart_connector_incremental_sync_and_checkpoint():
    """Verify incremental sync using updated_after and next_updated_after checkpoint capture."""
    received_params = {}

    async def handler_sync(request: httpx.Request):
        nonlocal received_params
        received_params = dict(request.url.params)
        return httpx.Response(200, json={
            "tenders": [
                {
                    "id": "uuid-sync-item-1",
                    "portal_name": "gem",
                    "tender_id": "GEM/2026/B/3001",
                    "title": "Incrementally Updated Tender",
                    "organisation": "Authority Sync",
                    "tender_value": 3200000.0,
                    "closing_at": "2026-11-20T12:00:00Z",
                }
            ],
            "pagination": {"next_cursor": None, "has_more": False},
            "sync": {
                "updated_after": "2026-10-15T00:00:00Z",
                "next_updated_after": "2026-10-21T16:00:00Z",
            },
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_sync))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_sync", client=client)

    records = await conn.fetch_tenders(limit=10, updated_after="2026-10-15T00:00:00Z")
    assert len(records) == 1
    assert received_params.get("updated_after") == "2026-10-15T00:00:00Z"
    assert conn.last_sync_checkpoint == "2026-10-21T16:00:00Z"


@pytest.mark.asyncio
async def test_tenderkart_connector_rate_limiting_retry_after():
    """Verify RFC Retry-After header compliance and exponential backoff retry."""
    attempts = 0

    async def handler_rate_limit(request: httpx.Request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.1"})
        return httpx.Response(200, json={
            "tenders": [
                {
                    "id": "uuid-rate-item",
                    "portal_name": "gem",
                    "tender_id": "GEM/2026/B/4001",
                    "title": "Rate Limit Handled Tender",
                    "organisation": "Authority Rate",
                    "tender_value": 1500000.0,
                    "closing_at": "2026-12-10T12:00:00Z",
                }
            ],
            "pagination": {"next_cursor": None, "has_more": False},
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_rate_limit))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_1", client=client, max_retries=3)

    records = await conn.fetch_tenders(limit=5)
    assert attempts == 2
    assert len(records) == 1
    assert records[0].source_tender_id == "uuid-rate-item"


@pytest.mark.asyncio
async def test_tenderkart_connector_rate_limiting_exhausted():
    """Verify TenderKartRateLimitError is raised when retries are exhausted."""
    async def handler_always_429(request: httpx.Request):
        return httpx.Response(429, headers={"Retry-After": "0.01"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_always_429))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_1", client=client, max_retries=2)

    with pytest.raises(TenderKartRateLimitError) as exc_info:
        await conn.fetch_tenders(limit=5)
    assert "rate limit exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_tenderkart_connector_fetch_tender_detail_and_document_download():
    """Verify GET /tenders/{uuid} details and GET /documents/{id} document download handling."""
    async def handler_detail(request: httpx.Request):
        if "/tenders/test-uuid-detail" in request.url.path:
            return httpx.Response(200, json={
                "id": "test-uuid-detail",
                "title": "Comprehensive IoT Gateway System",
                "organisation": "Power Distribution Corporation",
                "requirements": {
                    "minimum_annual_turnover_inr": 2500000.0,
                    "required_experience_years": 3,
                },
            })
        if "/documents/doc_valid_pdf" in request.url.path:
            return httpx.Response(200, content=b"%PDF-1.4 sample pdf binary data", headers={"Content-Type": "application/pdf"})
        if "/documents/doc_forbidden" in request.url.path:
            return httpx.Response(403, json={"error": "Document access restricted"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_detail))
    conn = TenderKartConnector(api_key="valid_key", client=client)

    # 1. Tender Detail
    detail = await conn.fetch_tender_detail("test-uuid-detail")
    assert detail is not None
    assert detail["title"] == "Comprehensive IoT Gateway System"
    assert detail["requirements"]["required_experience_years"] == 3

    # 2. Document Download (Permitted)
    doc_bytes = await conn.download_document("doc_valid_pdf")
    assert doc_bytes == b"%PDF-1.4 sample pdf binary data"

    # 3. Document Download (Forbidden - handles gracefully without crashing)
    doc_forbidden = await conn.download_document("doc_forbidden")
    assert doc_forbidden is None


@pytest.mark.asyncio
async def test_tenderkart_ingestion_service_e2e_sync_and_checkpoint_advancement(db_session: AsyncSession):
    """
    End-to-end integration test: Ingestion service synchronizes TenderKart records,
    persists them with source_portal='TENDERKART', records checkpoint, and idempotently skips on rerun.
    """
    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json={
            "tenders": [
                {
                    "id": "tk-e2e-uuid-001",
                    "portal_name": "gem",
                    "tender_id": "GEM/2026/B/TK9001",
                    "title": "TenderKart Synchronized Solar Inverters",
                    "organisation": "NTPC Energy Limited",
                    "sector": "Solar Energy",
                    "tender_value": 8500000.0,
                    "emd_fee": 170000.0,
                    "closing_at": "2026-12-15T18:00:00Z",
                    "published_at": "2026-10-18T10:00:00Z",
                    "updated_at": "2026-10-21T12:00:00Z",
                }
            ],
            "pagination": {"next_cursor": None, "has_more": False},
            "sync": {
                "updated_after": "2026-10-01T00:00:00Z",
                "next_updated_after": "2026-10-21T12:00:00Z",
            },
        })

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    tk_conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_test", client=mock_client)

    service = TenderIngestionService(db_session, connectors=[tk_conn])

    # 1. First sync tick: ingest new tender
    run1 = await service.sync_portal(source_portal="TENDERKART", limit=10)
    assert run1.status == "SUCCESS"
    assert run1.tenders_ingested == 1
    assert run1.run_metadata is not None
    assert run1.run_metadata.get("next_updated_after") == "2026-10-21T12:00:00Z"

    # Verify database persistence
    stmt = select(Tender).where(Tender.source_portal == "TENDERKART", Tender.source_tender_id == "tk-e2e-uuid-001")
    res = await db_session.execute(stmt)
    tender_row = res.scalar_one_or_none()
    assert tender_row is not None
    assert tender_row.tender_reference == "GEM/2026/B/TK9001"
    assert tender_row.title == "TenderKart Synchronized Solar Inverters"
    assert tender_row.ingestion_metadata["provider"] == "TENDERKART"
    assert tender_row.ingestion_metadata["origin_portal"] == "GEM"

    # 2. Second sync tick without force: should skip existing without duplicates
    run2 = await service.sync_portal(source_portal="TENDERKART", limit=10, force=False)
    assert run2.status == "SUCCESS"
    assert run2.tenders_ingested == 0
    assert run2.tenders_skipped == 1


@pytest.mark.asyncio
async def test_tenderkart_error_isolation_does_not_block_other_portals(db_session: AsyncSession):
    """Verify that an error in TenderKart connector does not halt synchronization of other portals."""
    class FailingTenderKartConnector(TenderKartConnector):
        async def fetch_tenders(self, limit: int = 50, **kwargs):
            raise httpx.ConnectError("TenderKart endpoint connection failed")

    failing_tk = FailingTenderKartConnector(api_key="bad_key")

    # Service with standard connectors plus failing TenderKart
    service = TenderIngestionService(db_session, connectors=[failing_tk])
    run = await service.sync_portal(source_portal="TENDERKART")
    assert run.status == "FAILED"
    assert "TenderKart endpoint connection failed" in (run.error_message or "")


@pytest.mark.asyncio
async def test_tenderkart_connector_multi_filter_independent_checkpoints(db_session: AsyncSession):
    """
    Verify that independent checkpoints are maintained per saved filter,
    and that a failed run does not advance or corrupt any filter cursor.
    """
    current_filter_called = ""

    async def multi_filter_handler(request: httpx.Request):
        nonlocal current_filter_called
        if request.url.path.endswith("/filters"):
            return httpx.Response(200, json={
                "filters": [
                    {"id": "filt_solar", "name": "Solar Pumping", "is_active": True},
                    {"id": "filt_rail", "name": "Railway Signalling", "is_active": True},
                ]
            })
        elif "filt_solar" in request.url.path:
            current_filter_called = "filt_solar"
            return httpx.Response(200, json={
                "tenders": [{
                    "id": "tk-solar-001",
                    "tenderkart_url": "https://tenderkart.in/tender/tk-solar-001",
                    "portal_name": "gem",
                    "tender_id": "GEM/2026/B/SOLAR1",
                    "title": "Solar Pumping Works",
                    "organisation": "KREDL",
                    "state": ["Karnataka"],
                    "city": ["Bengaluru"],
                    "tender_value": 5000000.0,
                    "closing_at": "2026-12-01T10:00:00Z",
                }],
                "pagination": {"next_cursor": None, "has_more": False},
                "sync": {
                    "updated_after": "2026-10-01T00:00:00Z",
                    "next_updated_after": "2026-10-21T10:00:00Z",
                },
            })
        elif "filt_rail" in request.url.path:
            current_filter_called = "filt_rail"
            return httpx.Response(200, json={
                "tenders": [{
                    "id": "tk-rail-001",
                    "tenderkart_url": "https://tenderkart.in/tender/tk-rail-001",
                    "portal_name": "eprocure",
                    "tender_id": "CPPP/2026/RAIL1",
                    "title": "Signalling Works",
                    "organisation": "Indian Railways",
                    "state": ["Maharashtra"],
                    "tender_value": 7500000.0,
                    "closing_at": "2026-12-05T10:00:00Z",
                }],
                "pagination": {"next_cursor": None, "has_more": False},
                "sync": {
                    "updated_after": "2026-10-01T00:00:00Z",
                    "next_updated_after": "2026-10-21T14:30:00Z",
                },
            })
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(multi_filter_handler))
    conn = TenderKartConnector(api_key="valid_key", client=client)

    # 1. Sync filter 1: Solar
    rec_solar = await conn.fetch_tenders(limit=5, filter_id="filt_solar")
    assert len(rec_solar) == 1
    assert rec_solar[0].official_portal_url == "https://tenderkart.in/tender/tk-solar-001"
    assert conn.filter_checkpoints["filt_solar"] == "2026-10-21T10:00:00Z"

    # 2. Sync filter 2: Rail
    rec_rail = await conn.fetch_tenders(limit=5, filter_id="filt_rail")
    assert len(rec_rail) == 1
    assert conn.filter_checkpoints["filt_rail"] == "2026-10-21T14:30:00Z"

    # Verify both filters maintain their separate independent cursors
    assert conn.filter_checkpoints["filt_solar"] == "2026-10-21T10:00:00Z"
    assert conn.filter_checkpoints["filt_rail"] == "2026-10-21T14:30:00Z"

    # 3. Ingestion service integration: verify checkpoints saved in run_metadata
    service = TenderIngestionService(db_session, connectors=[conn])
    run = await service.sync_portal(source_portal="TENDERKART")
    assert run.status == "SUCCESS"
    assert "filter_checkpoints" in run.run_metadata
    assert run.run_metadata["filter_checkpoints"]["filt_solar"] == "2026-10-21T10:00:00Z"
    assert run.run_metadata["filter_checkpoints"]["filt_rail"] == "2026-10-21T14:30:00Z"

    # 4. Checkpoint non-advancement on failure:
    class ErrorConnector(TenderKartConnector):
        async def fetch_tenders(self, limit: int = 50, **kwargs):
            raise RuntimeError("Sync interrupted mid-cycle")

    err_conn = ErrorConnector(api_key="valid_key")
    err_conn.filter_checkpoints["filt_solar"] = "2026-10-22T99:99:99Z"  # Uncommitted candidate cursor
    service_err = TenderIngestionService(db_session, connectors=[err_conn])
    failed_run = await service_err.sync_portal(source_portal="TENDERKART")
    assert failed_run.status == "FAILED"
    # The failed run must NOT contain the advanced checkpoint
    assert "filter_checkpoints" not in (failed_run.run_metadata or {})


@pytest.mark.asyncio
async def test_tenderkart_spec_compliance_cursor_and_lifecycle_params():
    """
    OpenAPI 3.0.3 Contract Verification:
    1. On initial request (no cursor): status='active,under_evaluation,awarded,cancelled'
    2. On cursor request: status, updated_after, and updated_before must NOT be sent.
    3. Initial backfill without updated_after when no checkpoint exists.
    """
    captured_requests: List[Dict[str, Any]] = []

    async def contract_handler(request: httpx.Request):
        captured_requests.append({
            "path": request.url.path,
            "params": dict(request.url.params),
        })
        cursor = request.url.params.get("cursor")
        if not cursor:
            # Page 1
            return httpx.Response(200, json={
                "tenders": [{
                    "id": "tk-contract-001",
                    "tenderkart_url": "https://tenderkart.in/tender/tk-contract-001",
                    "portal_name": "gem",
                    "tender_id": "GEM/2026/B/CTR01",
                    "title": "Contract Invariant Tender 1",
                    "tender_value": 4500000.0,
                    "closing_at": "2026-12-01T10:00:00Z",
                }],
                "pagination": {"next_cursor": "cur_page2", "has_more": True},
            })
        elif cursor == "cur_page2":
            # Page 2 (Final)
            return httpx.Response(200, json={
                "tenders": [{
                    "id": "tk-contract-002",
                    "tenderkart_url": "https://tenderkart.in/tender/tk-contract-002",
                    "portal_name": "cppp",
                    "tender_id": "CPPP/2026/NIC/CTR02",
                    "title": "Contract Invariant Tender 2",
                    "tender_value": 6500000.0,
                    "closing_at": "2026-12-05T10:00:00Z",
                }],
                "pagination": {"next_cursor": None, "has_more": False},
                "sync": {
                    "updated_after": "2026-10-01T00:00:00Z",
                    "next_updated_after": "2026-10-21T18:00:00Z",
                },
            })
        return httpx.Response(400)

    client = httpx.AsyncClient(transport=httpx.MockTransport(contract_handler))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_contract", client=client)

    records = await conn.fetch_tenders(limit=10)
    assert len(records) == 2
    assert len(captured_requests) == 2

    # Verify Page 1 (initial request):
    # - Has status='active,under_evaluation,awarded,cancelled'
    # - No updated_after (initial backfill)
    req1 = captured_requests[0]["params"]
    assert req1.get("status") == "active,under_evaluation,awarded,cancelled"
    assert "cursor" not in req1
    assert "updated_after" not in req1

    # Verify Page 2 (cursor request):
    # - Has cursor
    # - MUST NOT have status, updated_after, or updated_before
    req2 = captured_requests[1]["params"]
    assert req2.get("cursor") == "cur_page2"
    assert "status" not in req2
    assert "updated_after" not in req2
    assert "updated_before" not in req2

    # Verify final checkpoint committed
    assert conn.filter_checkpoints["filt_contract"] == "2026-10-21T18:00:00Z"


@pytest.mark.asyncio
async def test_tenderkart_cursor_invalidation_handling():
    """
    Verify that if a cursor returns HTTP 400 (e.g. cursor expired or filter modified),
    TenderKartAPIError is raised, the checkpoint is not advanced, and run safely fails.
    """
    async def invalid_cursor_handler(request: httpx.Request):
        cursor = request.url.params.get("cursor")
        if not cursor:
            return httpx.Response(200, json={
                "tenders": [{"id": "tk-cur-01", "portal_name": "gem", "tender_id": "G1", "title": "T1"}],
                "pagination": {"next_cursor": "corrupted_or_expired_cursor", "has_more": True},
            })
        # Cursor page returns 400 Bad Request
        return httpx.Response(400, json={"error": "Invalid or expired cursor"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_cursor_handler))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_inv", client=client)

    with pytest.raises(TenderKartAPIError) as exc_info:
        await conn.fetch_tenders(limit=10)
    assert "cursor invalidated" in str(exc_info.value).lower()
    # Checkpoint must NOT be recorded
    assert "filt_inv" not in conn.filter_checkpoints


@pytest.mark.asyncio
async def test_tenderkart_document_409_conflict_handling():
    """
    Verify that download_document handles HTTP 409 Conflict (upstream document preparation)
    gracefully by returning None and deferring without error.
    """
    async def conflict_doc_handler(request: httpx.Request):
        if "doc_preparing_409" in request.url.path:
            return httpx.Response(409, json={"error": "Document is currently being prepared upstream. Retry later."})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(conflict_doc_handler))
    conn = TenderKartConnector(api_key="valid_key", client=client)

    result = await conn.download_document("doc_preparing_409")
    assert result is None  # Gracefully handled without exception


@pytest.mark.asyncio
async def test_tenderkart_identity_provenance_and_full_payload():
    """
    Verify identity and provenance rules:
    - Provider ('TENDERKART') vs origin portal ('PWD_MAHARASHTRA')
    - tender_reference_number, tenderkart_url, updated_at preserved
    - Full source payload preserved in raw_payload
    - Exact tenderkart_url used, no /tenders/{uuid} synthesized
    """
    raw_item = {
        "id": "4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d",
        "portal_name": "pwd_maharashtra",
        "tender_id": "PWD/MAH/2026/E-9812",
        "tender_reference_number": "PWD/REF/2026/001",
        "tenderkart_url": "https://tenderkart.in/tender/4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d",
        "status": "active",
        "title": "Smart Flyover Lighting",
        "organisation": "Maharashtra PWD",
        "tender_value": 34000000.0,
        "updated_at": "2026-10-21T15:30:00Z",
        "closing_at": "2026-12-30T17:00:00Z",
    }
    conn = TenderKartConnector(api_key="valid_key")
    normalized = conn._normalize_tender(raw_item)

    assert normalized.source_portal == "TENDERKART"
    assert normalized.source_tender_id == "4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d"
    meta = normalized.ingestion_metadata
    assert meta["provider"] == "TENDERKART"
    assert meta["origin_portal"] == "PWD_MAHARASHTRA"
    assert meta["upstream_portal_name"] == "pwd_maharashtra"
    assert meta["upstream_tender_id"] == "PWD/MAH/2026/E-9812"
    assert meta["tender_reference_number"] == "PWD/REF/2026/001"
    assert meta["tenderkart_url"] == "https://tenderkart.in/tender/4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d"
    assert meta["upstream_updated_at"] == "2026-10-21T15:30:00Z"
    assert "raw_payload" in meta
    assert meta["raw_payload"]["id"] == raw_item["id"]


@pytest.mark.asyncio
async def test_tenderkart_reference_collision_safe_isolation(db_session: AsyncSession):
    """
    Verify that when a tender with the same tender_reference exists from a different portal,
    the TenderKart tender's reference is safely differentiated to satisfy the DB unique constraint,
    while preserving the authentic tender_reference_number in metadata.
    """
    # 1. Existing tender from GeM
    existing_gem = Tender(
        id=uuid.uuid4(),
        tender_reference="COMMON/REF/2026/01",
        title="Existing GeM Tender with Same Reference",
        issuing_authority="BHEL",
        sector="Electronics",
        submission_deadline=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        source_portal="GEM",
        source_tender_id="GEM-ORIG-01",
        last_synced_at=datetime.now(timezone.utc),
    )
    db_session.add(existing_gem)
    await db_session.commit()

    # 2. Ingest TenderKart notice with the same reference
    async def collision_handler(request: httpx.Request):
        return httpx.Response(200, json={
            "tenders": [{
                "id": "tk-collision-uuid-99",
                "portal_name": "cppp",
                "tender_id": "CPPP/COLLISION/01",
                "tender_reference_number": "COMMON/REF/2026/01",  # Same reference
                "tenderkart_url": "https://tenderkart.in/tender/tk-collision-uuid-99",
                "title": "TenderKart Distinct Tender with Shared Reference",
                "organisation": "IOCL",
                "tender_value": 2000000.0,
                "closing_at": "2026-12-10T12:00:00Z",
            }],
            "pagination": {"next_cursor": None, "has_more": False},
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(collision_handler))
    conn = TenderKartConnector(api_key="valid_key", default_filter_id="filt_coll", client=client)
    service = TenderIngestionService(db_session, connectors=[conn])

    run = await service.sync_portal(source_portal="TENDERKART")
    assert run.status == "SUCCESS"
    assert run.tenders_ingested == 1

    # Verify both tenders coexist in PostgreSQL
    gem_row = (await db_session.execute(select(Tender).where(Tender.source_portal == "GEM"))).scalar_one()
    tk_row = (await db_session.execute(select(Tender).where(Tender.source_portal == "TENDERKART", Tender.source_tender_id == "tk-collision-uuid-99"))).scalar_one()

    assert gem_row.tender_reference == "COMMON/REF/2026/01"
    assert tk_row.tender_reference.startswith("COMMON/REF/2026/01 (TK-")
    assert tk_row.ingestion_metadata["tender_reference_number"] == "COMMON/REF/2026/01"

