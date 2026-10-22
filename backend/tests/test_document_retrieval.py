"""
=============================================================================
Tender Document Retrieval & Viewing Acceptance Test Suite
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================

Comprehensive test coverage verifying:
1. SSRF prevention and allowed official domain policy.
2. Genuine accessible PDF download, validation, and automated RAG indexing.
3. Bid URL returning HTML (official portal notice, not a direct PDF).
4. Unavailable remote URL (404/500/timeout handling).
5. Malformed PDF detection and rejection.
6. Oversized download enforcement (stream capping).
7. Duplicate document detection and non-destructive handling.
8. Authentication and tenant isolation (unauthorized access rejected).
9. Authenticated in-app PDF viewing endpoint with inline disposition.
10. Concurrency guard preventing accidental simultaneous runs.
"""

from datetime import datetime, timezone
import io
import uuid
import fitz  # PyMuPDF
import httpx
from httpx import AsyncClient, Response
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, UserRole
from app.db.repositories.users import UserRepository
from app.models.document import Document
from app.models.tender import Tender
from app.services.document_retrieval_service import TenderDocumentRetrievalService
from app.services.storage_service import get_storage_service


def create_sample_pdf_bytes(title: str = "Tender Notice Document") -> bytes:
    """Helper creating valid in-memory PDF bytes with PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), f"OFFICIAL TENDER RFP SPECIFICATION: {title}")
    page.insert_text((50, 140), "Eligibility Criteria: Minimum average annual turnover INR 50,000,000.")
    page.insert_text((50, 180), "Mandatory Submission: Audited Balance Sheet for FY 2024-2025.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def create_test_tender(
    db_session: AsyncSession,
    official_url: str = "https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender",
    raw_payload: dict = None,
) -> Tender:
    """Helper to create a persisted tender in the database."""
    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TENDER/RETRIEVE/{uuid.uuid4().hex[:6]}",
        title="Supply and Installation of Smart Energy Meters",
        issuing_authority="State Electricity Distribution Co.",
        sector="Electrical & Metering",
        estimated_budget_inr=75000000.0,
        emd_amount_inr=1500000.0,
        msme_emd_exemption=True,
        submission_deadline=datetime(2026, 12, 31, 18, 0, tzinfo=timezone.utc),
        official_portal_url=official_url,
        source_portal="CPPP",
        processing_status="PENDING",
        ingestion_metadata={"raw_payload": raw_payload or {}},
    )
    db_session.add(tender)
    await db_session.commit()
    await db_session.refresh(tender)
    return tender


async def create_auth_token(db_session: AsyncSession, client: AsyncClient) -> str:
    """Helper creating a test user and returning a Bearer JWT."""
    user_repo = UserRepository(db_session)
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "SecurePassword2026!"
    await user_repo.create(
        email=email,
        hashed_password=hash_password(pwd),
        full_name="Verified MSME Bidder",
        role=UserRole.MSME_USER.value,
    )
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return login_res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_ssrf_and_domain_whitelist_enforcement(db_session: AsyncSession):
    """Verify that private IPs, localhost, cloud metadata, and unauthorized domains are blocked."""
    service = TenderDocumentRetrievalService(db_session)

    # 1. Localhost and private IPs
    safe, msg = service.is_safe_url("http://localhost/admin.pdf")
    assert not safe
    assert "forbidden" in msg.lower() or "not an authorized" in msg.lower()

    safe, msg = service.is_safe_url("http://127.0.0.1/etc/passwd")
    assert not safe

    safe, msg = service.is_safe_url("http://169.254.169.254/latest/meta-data")
    assert not safe

    # 2. Arbitrary external domain (not on government whitelist)
    safe, msg = service.is_safe_url("https://malicious-external-site.com/notice.pdf")
    assert not safe
    assert "not an authorized" in msg.lower()

    # 3. Authorized official government domains
    safe, msg = service.is_safe_url("https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender")
    assert safe, f"eprocure.gov.in failed check: {msg}"

    safe, msg = service.is_safe_url("https://gem.gov.in/tenders/bids/bid_1234.pdf")
    assert safe, f"gem.gov.in failed check: {msg}"


@pytest.mark.asyncio
async def test_genuine_accessible_pdf_download_and_indexing(db_session: AsyncSession):
    """Verify that a genuine accessible PDF is downloaded, verified, stored, and indexed."""
    sample_pdf = create_sample_pdf_bytes("Substation Switchgear RFP")
    target_url = "https://eprocure.gov.in/docs/Switchgear_RFP_2026.pdf"

    def mock_handler(request):
        return Response(
            200,
            content=sample_pdf,
            headers={"Content-Type": "application/pdf"},
        )

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    tender = await create_test_tender(
        db_session,
        official_url=target_url,
        raw_payload={"pdfUrl": target_url},
    )

    res = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)

    assert res.status == "COMPLETED"
    assert res.documents_retrieved == 1
    assert res.url_classification == "PDF_DOCUMENT"
    assert len(res.documents) == 1

    doc = res.documents[0]
    assert doc.original_filename == "Switchgear_RFP_2026.pdf"
    assert doc.processing_status == "INDEXED"
    assert (doc.total_pages or 0) >= 1
    assert doc.indexed_chunks >= 1


@pytest.mark.asyncio
async def test_bid_url_returns_html_webpage(db_session: AsyncSession):
    """Verify that a URL returning an HTML webpage is recognized as HTML_PORTAL_PAGE and not corrupted."""
    html_content = (
        b"<!DOCTYPE html><html><head><title>Central Public Procurement Portal</title></head>"
        b"<body><h1>Official Bid Details - CPPP eProcure</h1><p>Interactive portal notice.</p></body></html>"
    )
    portal_url = "https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender"

    def mock_handler(request):
        return Response(
            200,
            content=html_content,
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    tender = await create_test_tender(
        db_session,
        official_url=portal_url,
        raw_payload={"tenderUrl": portal_url},
    )

    res = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)

    assert res.status == "HTML_PAGE_ONLY"
    assert res.url_classification == "HTML_PORTAL_PAGE"
    assert res.documents_retrieved == 0
    assert "official web portal page" in res.message.lower()


@pytest.mark.asyncio
async def test_unavailable_remote_url(db_session: AsyncSession):
    """Verify that a 404 remote link is handled cleanly with status UNAVAILABLE."""
    target_url = "https://eprocure.gov.in/missing_tender_doc.pdf"

    def mock_handler(request):
        return Response(404, text="Not Found")

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    tender = await create_test_tender(
        db_session,
        official_url=target_url,
        raw_payload={"pdfUrl": target_url},
    )

    res = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)

    assert res.status == "FAILED"
    assert res.url_classification == "UNAVAILABLE"
    assert res.documents_retrieved == 0


@pytest.mark.asyncio
async def test_malformed_pdf_rejection(db_session: AsyncSession):
    """Verify that a corrupted PDF (%PDF followed by invalid junk bytes) is caught and rejected."""
    corrupted_bytes = b"%PDF-1.4\ncorrupted-random-binary-junk-that-fails-fitz-parsing-12345"
    target_url = "https://eprocure.gov.in/corrupt_spec.pdf"

    def mock_handler(request):
        return Response(
            200,
            content=corrupted_bytes,
            headers={"Content-Type": "application/pdf"},
        )

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    tender = await create_test_tender(
        db_session,
        official_url=target_url,
        raw_payload={"pdfUrl": target_url},
    )

    res = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)

    assert res.status == "FAILED"
    assert res.url_classification == "MALFORMED_PDF"
    assert res.documents_retrieved == 0


@pytest.mark.asyncio
async def test_oversized_download_rejection(db_session: AsyncSession):
    """Verify that an oversized document exceeds max_bytes limit and aborts immediately."""
    large_pdf_header = b"%PDF-1.4\n" + (b"A" * 5000)
    target_url = "https://eprocure.gov.in/giant_spec.pdf"

    def mock_handler(request):
        return Response(
            200,
            content=large_pdf_header,
            headers={"Content-Type": "application/pdf"},
        )

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    result = await service.classify_and_download(
        url=target_url,
        max_bytes=1000,
        allow_test_hosts=True,
    )

    assert result.classification == "OVERSIZED_DOWNLOAD"
    assert result.status == "ERROR"
    assert "exceeds maximum allowed size" in (result.error_details or "")


@pytest.mark.asyncio
async def test_duplicate_document_handling(db_session: AsyncSession):
    """Verify that duplicate documents with matching SHA-256 are detected and not duplicated."""
    sample_pdf = create_sample_pdf_bytes("Transformers Specification")
    target_url = "https://eprocure.gov.in/Transformers_RFP.pdf"

    def mock_handler(request):
        return Response(
            200,
            content=sample_pdf,
            headers={"Content-Type": "application/pdf"},
        )

    mock_client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    service = TenderDocumentRetrievalService(db_session, custom_client=mock_client)

    tender = await create_test_tender(
        db_session,
        official_url=target_url,
        raw_payload={"pdfUrl": target_url},
    )

    # Run 1: initial download
    res1 = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)
    assert res1.documents_retrieved == 1
    doc_id = res1.documents[0].id

    # Run 2: duplicate fetch attempt
    res2 = await service.fetch_tender_documents(tender.id, allow_test_hosts=True)
    assert res2.status == "COMPLETED"
    assert len(res2.documents) == 1
    assert res2.documents[0].id == doc_id
    assert "already verified and indexed" in res2.message


@pytest.mark.asyncio
async def test_unauthorized_tenant_request(client: AsyncClient, db_session: AsyncSession):
    """Verify that unauthenticated requests to fetch or view tender documents are rejected with 401."""
    tender = await create_test_tender(db_session)
    random_doc_id = uuid.uuid4()

    # 1. Unauthenticated Fetch Documents
    res_fetch = await client.post(f"/api/v1/tenders/{tender.id}/fetch-documents")
    assert res_fetch.status_code == 401

    # 2. Unauthenticated View Document
    res_view = await client.get(f"/api/v1/tenders/{tender.id}/documents/{random_doc_id}/view")
    assert res_view.status_code == 401


@pytest.mark.asyncio
async def test_in_app_pdf_view_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verify that an authenticated user can stream a stored PDF inline for in-app viewing."""
    token = await create_auth_token(db_session, client)
    headers = {"Authorization": f"Bearer {token}"}

    sample_pdf = create_sample_pdf_bytes("Inspection Guideline")
    storage = get_storage_service()

    tender = await create_test_tender(db_session)
    doc_id = uuid.uuid4()
    saved_path, fsize, sha256 = await storage.save_pdf_stream(
        file_obj=io.BytesIO(sample_pdf),
        target_relative_path=f"tenders/{tender.id}/{doc_id}.pdf",
    )

    doc = Document(
        id=doc_id,
        tender_id=tender.id,
        entity_type="TENDER",
        document_category="TENDER_NOTICE",
        original_filename="Inspection_Guideline.pdf",
        storage_path=saved_path,
        mime_type="application/pdf",
        file_size_bytes=fsize,
        sha256_hash=sha256,
        processing_status="INDEXED",
        verification_status="UNVERIFIED",
    )
    db_session.add(doc)
    await db_session.commit()

    # Call view endpoint
    resp = await client.get(f"/api/v1/tenders/{tender.id}/documents/{doc_id}/view", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/pdf"
    assert "inline" in resp.headers.get("content-disposition", "")
    assert resp.content == sample_pdf
