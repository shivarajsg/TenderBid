import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.document import Document
from app.models.ingestion_run import IngestionRun
from app.services.ingestion.base_connector import RawTenderRecord
from app.services.ingestion.gem_connector import GeMTenderConnector, CANONICAL_GEM_TENDERS
from app.services.ingestion.ingestion_service import TenderIngestionService


def _create_mock_gem_solr_page(page_num: int, start_idx: int, num_found: int = 47245, doc_count: int = 10):
    docs = []
    for i in range(doc_count):
        bid_id = start_idx + i
        docs.append({
            "id": f"gem_solr_{bid_id}",
            "b_id": [bid_id],
            "b_bid_number": [f"GEM/2026/B/{bid_id}"],
            "b_category_name": [f"Category Sample {bid_id}"],
            "b_total_quantity": [50 + i],
            "b_bid_type": [1],
            "b_eval_type": [0],
            "ba_official_details_minName": ["Ministry of Electronics"],
            "ba_official_details_deptName": ["IT Department"],
            "final_start_date_sort": ["2026-03-01T10:00:00Z"],
            "final_end_date_sort": ["2026-04-15T18:00:00Z"],
        })
    return {
        "response": {
            "response": {
                "numFound": num_found,
                "start": (page_num - 1) * 10,
                "docs": docs,
            }
        }
    }


@pytest.mark.asyncio
async def test_gem_pagination_beyond_first_page_and_previous_limit():
    """Verify live listing pagination continues across multiple pages beyond 10-item limit."""
    connector = GeMTenderConnector()

    page_1_data = _create_mock_gem_solr_page(1, 1000, num_found=47245, doc_count=10)
    page_2_data = _create_mock_gem_solr_page(2, 2000, num_found=47245, doc_count=10)
    page_3_data = _create_mock_gem_solr_page(3, 3000, num_found=47245, doc_count=10)

    # Mock HTTP responses
    mock_get = MagicMock(status_code=200, text="var config = {'csrf_bd_gem_nk': 'aabbcc112233'};")

    async def mock_post(url, data=None, headers=None):
        payload = json.loads(data["payload"])
        page = payload["page"]
        if page == 1:
            return MagicMock(status_code=200, json=lambda: page_1_data)
        elif page == 2:
            return MagicMock(status_code=200, json=lambda: page_2_data)
        elif page == 3:
            return MagicMock(status_code=200, json=lambda: page_3_data)
        return MagicMock(status_code=200, json=lambda: {"response": {"response": {"docs": [], "numFound": 47245}}})

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)), \
         patch("httpx.AsyncClient.post", AsyncMock(side_effect=mock_post)):

        records = await connector.fetch_tenders(limit=25, start_page=1)
        assert len(records) == 25
        assert connector.last_crawl_metadata is not None
        assert connector.last_crawl_metadata["pages_processed"] == 3
        assert connector.last_crawl_metadata["end_page_crawled"] == 3
        assert connector.last_crawl_metadata["next_page"] == 4
        assert connector.last_crawl_metadata["is_partial"] is True


@pytest.mark.asyncio
async def test_gem_dynamic_source_reported_total():
    """Verify source-reported total count (numFound) is captured dynamically, not hardcoded."""
    connector = GeMTenderConnector()
    solr_data = _create_mock_gem_solr_page(1, 5000, num_found=48912, doc_count=10)

    mock_get = MagicMock(status_code=200, text="var c = {'csrf_bd_gem_nk': '0123456789abcdef0123456789abcdef'};")
    mock_post = MagicMock(status_code=200, json=lambda: solr_data)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)), \
         patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_post)):

        records = await connector.fetch_tenders(limit=5)
        assert len(records) == 5
        assert connector.last_crawl_metadata["total_portal_records"] == 48912
        for r in records:
            assert r.ingestion_metadata["total_portal_records"] == 48912


@pytest.mark.asyncio
async def test_gem_multi_page_parsing_and_deduplication():
    """Verify bids appearing on multiple pages are deduplicated by stable GeM bid ID."""
    connector = GeMTenderConnector()

    page_1 = _create_mock_gem_solr_page(1, 6000, doc_count=5)
    # Page 2 has 2 duplicate IDs from page 1 and 3 new ones
    page_2 = _create_mock_gem_solr_page(2, 6003, doc_count=5)

    mock_get = MagicMock(status_code=200, text="{'csrf_bd_gem_nk': 'abcdef0123456789abcdef0123456789'}")

    async def mock_post(url, data=None, headers=None):
        payload = json.loads(data["payload"])
        if payload["page"] == 1:
            return MagicMock(status_code=200, json=lambda: page_1)
        return MagicMock(status_code=200, json=lambda: page_2)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)), \
         patch("httpx.AsyncClient.post", AsyncMock(side_effect=mock_post)):

        records = await connector.fetch_tenders(limit=15, start_page=1, max_pages=2)
        # 5 on page 1 + 3 new on page 2 (since 2 were duplicates) = 8 unique
        assert len(records) == 8
        unique_ids = {r.source_tender_id for r in records}
        assert len(unique_ids) == 8


@pytest.mark.asyncio
async def test_gem_connector_returns_genuine_raw_tender_records():
    """Verify connector outputs genuine RawTenderRecord with proper schema attributes."""
    connector = GeMTenderConnector()
    solr_data = _create_mock_gem_solr_page(1, 7100, doc_count=2)

    mock_get = MagicMock(status_code=200, text="{'csrf_bd_gem_nk': '7100abcdef0123456789abcdef012345'}")
    mock_post = MagicMock(status_code=200, json=lambda: solr_data)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)), \
         patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_post)):

        records = await connector.fetch_tenders(limit=2)
        assert len(records) == 2
        rec = records[0]
        assert isinstance(rec, RawTenderRecord)
        assert rec.source_portal == "GEM"
        assert rec.tender_reference == "GEM/2026/B/7100"
        assert rec.source_tender_id == "7100"
        assert rec.official_portal_url == "https://bidplus.gem.gov.in/showbidDocument/7100"
        assert rec.ingestion_metadata["is_fixture"] is False
        assert rec.ingestion_metadata["data_source_mode"] == "LIVE_GEM_PORTAL"
        assert rec.structured_requirements["quantity"] == 50


@pytest.mark.asyncio
async def test_gem_live_failure_not_silently_substituted_by_fixtures():
    """Verify live GeM failures raise honestly and NEVER substitute fixture data in live mode."""
    connector = GeMTenderConnector()

    mock_get = MagicMock(status_code=503, text="Service Unavailable")

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)):
        with pytest.raises(RuntimeError) as exc_info:
            await connector.fetch_tenders(limit=10, mode="live")
        assert "GeM initial page returned HTTP 503" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gem_fixture_mode_works_when_explicitly_requested():
    """Verify canonical fixture records remain available when explicitly requested."""
    connector = GeMTenderConnector()

    # mode="fixture" should return canonical fixtures without network calls
    fixture_records = await connector.fetch_tenders(limit=3, mode="fixture")
    assert len(fixture_records) == 3
    for r in fixture_records:
        assert r.source_portal == "GEM"
        assert r.ingestion_metadata["is_fixture"] is True
        assert r.ingestion_metadata["data_source_mode"] == "CANONICAL_SCHEMA_FIXTURE"


@pytest.mark.asyncio
async def test_gem_only_refresh_does_not_execute_unrelated_connectors(db_session: AsyncSession):
    """Verify GeM-specific refresh runs ONLY GeM and preserves other connectors untouched."""
    service = TenderIngestionService(db_session)

    mock_records = [
        RawTenderRecord(
            tender_reference="GEM/2026/B/99001",
            title="GeM Medical Supplies",
            issuing_authority="AIIMS",
            sector="Healthcare",
            submission_deadline=datetime(2026, 12, 31, tzinfo=timezone.utc),
            source_portal="GEM",
            source_tender_id="99001",
            official_portal_url="https://bidplus.gem.gov.in/showbidDocument/99001",
            ingestion_metadata={"is_fixture": False, "data_source_mode": "LIVE_GEM_PORTAL"},
        )
    ]

    with patch.object(service.connectors["GEM"], "fetch_tenders", AsyncMock(return_value=mock_records)) as mock_gem, \
         patch.object(service.connectors["CPPP"], "fetch_tenders", AsyncMock()) as mock_cppp, \
         patch.object(service.connectors["OPEN_GOV"], "fetch_tenders", AsyncMock()) as mock_opengov:

        run = await service.sync_portal(source_portal="GEM", limit=10)
        assert run.status == "SUCCESS"
        assert run.source_portal == "GEM"
        assert run.tenders_ingested == 1

        mock_gem.assert_called_once()
        mock_cppp.assert_not_called()
        mock_opengov.assert_not_called()


@pytest.mark.asyncio
async def test_gem_refresh_preserves_existing_records_and_documents(db_session: AsyncSession):
    """Verify refreshing GeM preserves existing database records, UUIDs, and attached documents."""
    # 1. Create existing GeM tender with attached document
    existing_id = uuid.uuid4()
    existing_tender = Tender(
        id=existing_id,
        tender_reference="GEM/2026/B/8147949",
        title="Existing GeM Diagnostic Kit",
        issuing_authority="Ministry of Health",
        sector="Healthcare",
        submission_deadline=datetime(2026, 11, 1, tzinfo=timezone.utc),
        source_portal="GEM",
        source_tender_id="8147949",
        official_portal_url="https://bidplus.gem.gov.in/showbidDocument/8147949",
        processing_status="INDEXED",
    )
    db_session.add(existing_tender)
    await db_session.flush()

    existing_doc = Document(
        id=uuid.uuid4(),
        tender_id=existing_id,
        entity_type="TENDER",
        document_category="TENDER_NOTICE",
        original_filename="Rapid_Diagnostic_Kit.pdf",
        storage_path="downloads/8147949/Rapid_Diagnostic_Kit.pdf",
        file_size_bytes=125000,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/pdf",
        processing_status="INDEXED",
    )
    db_session.add(existing_doc)
    await db_session.commit()

    # 2. Run sync with updated deadline for that same bid
    service = TenderIngestionService(db_session)
    updated_record = RawTenderRecord(
        tender_reference="GEM/2026/B/8147949",
        title="Existing GeM Diagnostic Kit (Updated Title)",
        issuing_authority="Ministry of Health",
        sector="Healthcare",
        submission_deadline=datetime(2026, 12, 1, tzinfo=timezone.utc),
        source_portal="GEM",
        source_tender_id="8147949",
        official_portal_url="https://bidplus.gem.gov.in/showbidDocument/8147949",
        ingestion_metadata={"is_fixture": False, "data_source_mode": "LIVE_GEM_PORTAL"},
    )

    with patch.object(service.connectors["GEM"], "fetch_tenders", AsyncMock(return_value=[updated_record])):
        run = await service.sync_portal(source_portal="GEM", limit=10)
        assert run.status == "SUCCESS"
        assert run.tenders_updated == 1
        assert run.tenders_ingested == 0

    # 3. Verify tender ID and document remain completely intact
    stmt = select(Tender).where(Tender.tender_reference == "GEM/2026/B/8147949")
    res = await db_session.execute(stmt)
    t = res.scalar_one()
    assert t.id == existing_id

    doc_stmt = select(Document).where(Document.tender_id == existing_id)
    doc_res = await db_session.execute(doc_stmt)
    docs = doc_res.scalars().all()
    assert len(docs) == 1
    assert docs[0].original_filename == "Rapid_Diagnostic_Kit.pdf"


@pytest.mark.asyncio
async def test_gem_incomplete_pagination_produces_honest_partial_status(db_session: AsyncSession):
    """Verify failed subsequent pages result in honest PARTIAL status without hiding errors."""
    connector = GeMTenderConnector()
    page_1 = _create_mock_gem_solr_page(1, 9100, doc_count=10)

    mock_get = MagicMock(status_code=200, text="{'csrf_bd_gem_nk': '0123456789abcdef0123456789abcdef'}")

    async def mock_post(url, data=None, headers=None):
        payload = json.loads(data["payload"])
        if payload["page"] == 1:
            return MagicMock(status_code=200, json=lambda: page_1)
        # Page 2 fails with HTTP 502 Bad Gateway
        return MagicMock(status_code=502, text="Bad Gateway")

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_get)), \
         patch("httpx.AsyncClient.post", AsyncMock(side_effect=mock_post)):

        records = await connector.fetch_tenders(limit=20, start_page=1)
        assert len(records) == 10
        assert connector.last_crawl_metadata["is_partial"] is True
        assert connector.last_crawl_metadata["unretrieved_pages"] == [2]

    # Verify ingestion service records PARTIAL status honestly
    service = TenderIngestionService(db_session)
    with patch.object(service.connectors["GEM"], "fetch_tenders", AsyncMock(return_value=records)), \
         patch.object(service.connectors["GEM"], "last_crawl_metadata", connector.last_crawl_metadata):

        run = await service.sync_portal(source_portal="GEM", limit=20)
        assert run.status == "PARTIAL"
        assert run.tenders_ingested == 10
        assert run.run_metadata["gem_crawl"]["unretrieved_pages"] == [2]


@pytest.mark.asyncio
async def test_gem_controlled_live_source_retrieval(db_session: AsyncSession):
    """
    Controlled live acceptance test against the public GeM listing portal.
    Verifies that real GeM portal responds, dynamic numFound (47,000+) is discovered,
    and multiple pages (page 1 and 2) are retrieved and ingested.
    """
    connector = GeMTenderConnector()
    avail = await connector.check_availability()
    if not avail.get("online"):
        pytest.skip("GeM portal is temporarily unreachable from local network.")

    # Request small controlled live batch (15 tenders = 2 pages)
    records = await connector.fetch_tenders(limit=15, start_page=1, mode="live")
    assert len(records) >= 10
    assert connector.last_crawl_metadata is not None
    # Verify dynamic total count from GeM Solr
    total_portal = connector.last_crawl_metadata["total_portal_records"]
    assert total_portal > 40000, f"Expected >40,000 ongoing GeM tenders, got {total_portal}"
    assert connector.last_crawl_metadata["pages_processed"] >= 2
    for r in records:
        assert r.source_portal == "GEM"
        assert r.tender_reference.startswith("GEM/")
        assert r.ingestion_metadata["is_fixture"] is False
        assert r.ingestion_metadata["data_source_mode"] == "LIVE_GEM_PORTAL"

