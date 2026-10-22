import io
import uuid
import pytest
import pymupdf
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, UserRole
from app.db.repositories.users import UserRepository
from app.services.storage_service import PDF_MAGIC_BYTES


async def create_test_admin(db_session: AsyncSession, client: AsyncClient) -> str:
    """Helper creating an ADMIN user and returning a Bearer JWT."""
    user_repo = UserRepository(db_session)
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@tenderplatform.org"
    password = "AdminSecurePassword2026!"
    await user_repo.create(
        email=admin_email,
        hashed_password=hash_password(password),
        full_name="Tender Administrator",
        role=UserRole.ADMIN.value,
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": password},
    )
    return login_res.json()["data"]["access_token"]


async def create_test_msme(client: AsyncClient) -> str:
    """Helper creating a standard MSME user and returning a Bearer JWT."""
    email = f"msme_{uuid.uuid4().hex[:6]}@precisionparts.com"
    password = "MsmePassword123!"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "MSME Bidder"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return login_res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_admin_create_tender(client: AsyncClient, db_session: AsyncSession):
    """Verify administrator can create a tender with structured requirements."""
    admin_token = await create_test_admin(db_session, client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "tender_reference": f"NTPC/ELECT/{uuid.uuid4().hex[:6]}",
        "title": "Supply and Commissioning of 220kV Transformers",
        "issuing_authority": "National Thermal Power Corporation",
        "sector": "Electrical Infrastructure",
        "estimated_budget_inr": 85000000.0,
        "emd_amount_inr": 1700000.0,
        "msme_emd_exemption": True,
        "submission_deadline": "2026-11-30T17:00:00Z",
        "structured_requirements": {
            "min_turnover_inr": 60000000.0,
            "min_experience_years": 5,
            "mandatory_certifications": ["ISO 9001:2015", "CPRI Type Test Certificate"],
        },
    }

    res = await client.post("/api/v1/admin/tenders", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["tender_reference"] == payload["tender_reference"]
    assert data["sector"] == "Electrical Infrastructure"
    assert data["processing_status"] == "PENDING"
    assert "id" in data


@pytest.mark.asyncio
async def test_msme_user_forbidden_from_admin_tender_creation(client: AsyncClient):
    """Verify standard MSME users receive 403 Forbidden on administrative endpoints."""
    msme_token = await create_test_msme(client)
    headers = {"Authorization": f"Bearer {msme_token}"}

    payload = {
        "tender_reference": "UNAUTH/001",
        "title": "Unauthorized Tender Attempt",
        "issuing_authority": "Test Authority",
        "sector": "Defense",
        "submission_deadline": "2026-12-31T17:00:00Z",
    }

    res = await client.post("/api/v1/admin/tenders", json=payload, headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_and_filter_tenders(client: AsyncClient, db_session: AsyncSession):
    """Verify tender listing with sector, budget, and search queries."""
    admin_token = await create_test_admin(db_session, client)
    msme_token = await create_test_msme(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    msme_headers = {"Authorization": f"Bearer {msme_token}"}

    # Seed two tenders
    ref1 = f"SECTOR_A_{uuid.uuid4().hex[:4]}"
    ref2 = f"SECTOR_B_{uuid.uuid4().hex[:4]}"

    await client.post(
        "/api/v1/admin/tenders",
        json={
            "tender_reference": ref1,
            "title": "Solar Rooftop EPC Contract",
            "issuing_authority": "Solar Energy Corp of India",
            "sector": "Renewable Energy",
            "estimated_budget_inr": 20000000.0,
            "submission_deadline": "2026-12-01T15:00:00Z",
        },
        headers=admin_headers,
    )

    await client.post(
        "/api/v1/admin/tenders",
        json={
            "tender_reference": ref2,
            "title": "Highway Road Surfacing Project",
            "issuing_authority": "National Highways Authority",
            "sector": "Civil Construction",
            "estimated_budget_inr": 90000000.0,
            "submission_deadline": "2026-12-15T15:00:00Z",
        },
        headers=admin_headers,
    )

    # MSME queries renewable energy tenders
    res = await client.get("/api/v1/tenders?sector=Renewable", headers=msme_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(t["tender_reference"] == ref1 for t in body["items"])
    assert not any(t["tender_reference"] == ref2 for t in body["items"])

    # MSME queries by budget threshold
    res_budget = await client.get("/api/v1/tenders?min_budget=50000000", headers=msme_headers)
    assert res_budget.status_code == 200
    items_budget = res_budget.json()["items"]
    assert any(t["tender_reference"] == ref2 for t in items_budget)
    assert not any(t["tender_reference"] == ref1 for t in items_budget)


@pytest.mark.asyncio
async def test_tender_document_upload_and_processing_pipeline(client: AsyncClient, db_session: AsyncSession):
    """End-to-end test of tender creation, PDF upload, extraction, and processing status."""
    admin_token = await create_test_admin(db_session, client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create tender
    ref = f"NIT/PIPELINE/{uuid.uuid4().hex[:6]}"
    create_res = await client.post(
        "/api/v1/admin/tenders",
        json={
            "tender_reference": ref,
            "title": "Pipeline Integration Equipment Tender",
            "issuing_authority": "Gas Authority of India Ltd",
            "sector": "Hydrocarbon Infrastructure",
            "submission_deadline": "2026-12-31T18:00:00Z",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    tender_id = create_res.json()["id"]

    # 2. Upload valid PDF attachment
    doc_pdf = pymupdf.open()
    page = doc_pdf.new_page()
    page.insert_text(
        (50, 50),
        "The Gas Authority of India invites bids for supply of steel pipeline fittings. "
        "Bidder must have annual turnover exceeding 30 Crores INR over last 3 years.",
        fontsize=12,
    )
    pdf_content = doc_pdf.tobytes()
    doc_pdf.close()

    files = [
        ("files", ("GAIL_Notice_NIT.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    upload_res = await client.post(
        f"/api/v1/admin/tenders/{tender_id}/upload-docs",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 201
    uploaded_docs = upload_res.json()
    assert len(uploaded_docs) == 1
    doc_id = uploaded_docs[0]["id"]
    assert uploaded_docs[0]["processing_status"] == "PENDING"
    assert uploaded_docs[0]["original_filename"] == "GAIL_Notice_NIT.pdf"

    # 3. Check initial processing status
    status_res = await client.get(
        f"/api/v1/admin/tenders/{tender_id}/processing-status",
        headers=headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["total_documents"] == 1
    assert status_res.json()["processing_status"] == "PENDING"

    # 4. Trigger processing pipeline
    process_res = await client.post(
        f"/api/v1/admin/tenders/{tender_id}/process",
        headers=headers,
    )
    assert process_res.status_code == 200
    processed_tender = process_res.json()
    assert processed_tender["processing_status"] in ("INDEXED", "PARTIALLY_INDEXED")

    # 5. Download document
    download_res = await client.get(
        f"/api/v1/tenders/{tender_id}/documents/{doc_id}/download",
        headers=headers,
    )
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content == pdf_content


@pytest.mark.asyncio
async def test_upload_invalid_file_rejected(client: AsyncClient, db_session: AsyncSession):
    """Verify non-PDF files are rejected with 400 Bad Request."""
    admin_token = await create_test_admin(db_session, client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create tender
    create_res = await client.post(
        "/api/v1/admin/tenders",
        json={
            "tender_reference": f"NIT/REJECT/{uuid.uuid4().hex[:6]}",
            "title": "Invalid Upload Test Tender",
            "issuing_authority": "Audit Authority",
            "sector": "Administration",
            "submission_deadline": "2026-12-31T18:00:00Z",
        },
        headers=headers,
    )
    tender_id = create_res.json()["id"]

    # Upload text file posing as PDF
    fake_file = [
        ("files", ("malicious.pdf", io.BytesIO(b"This is plain text, not a PDF."), "application/pdf")),
    ]
    res = await client.post(
        f"/api/v1/admin/tenders/{tender_id}/upload-docs",
        files=fake_file,
        headers=headers,
    )
    assert res.status_code == 400
    assert "magic bytes" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_tender_pagination_non_overlapping_pages_and_counts(client: AsyncClient, db_session: AsyncSession):
    """Verify that pagination delivers non-overlapping pages, accurate totals, and page computation."""
    admin_token = await create_test_admin(db_session, client)
    msme_token = await create_test_msme(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    msme_headers = {"Authorization": f"Bearer {msme_token}"}

    # Seed 5 distinct tenders with sequential deadlines
    seeded_refs = []
    for i in range(1, 6):
        ref = f"PAGINATE_{i:02d}_{uuid.uuid4().hex[:4]}"
        seeded_refs.append(ref)
        await client.post(
            "/api/v1/admin/tenders",
            json={
                "tender_reference": ref,
                "title": f"Tender Pagination Verification Item {i}",
                "issuing_authority": "Ministry of Urban Development",
                "sector": "Civic Works",
                "estimated_budget_inr": float(1000000.0 * i),
                "submission_deadline": f"2026-11-{10 + i:02d}T12:00:00Z",
            },
            headers=admin_headers,
        )

    # 1. Fetch Page 1 (limit=2)
    res_p1 = await client.get("/api/v1/tenders?page=1&limit=2", headers=msme_headers)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["total"] == 5
    assert data_p1["page"] == 1
    assert data_p1["pages"] == 3
    assert data_p1["limit"] == 2
    assert data_p1["skip"] == 0
    assert len(data_p1["items"]) == 2
    ids_p1 = [t["id"] for t in data_p1["items"]]

    # 2. Fetch Page 2 (limit=2)
    res_p2 = await client.get("/api/v1/tenders?page=2&limit=2", headers=msme_headers)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["total"] == 5
    assert data_p2["page"] == 2
    assert data_p2["pages"] == 3
    assert data_p2["limit"] == 2
    assert data_p2["skip"] == 2
    assert len(data_p2["items"]) == 2
    ids_p2 = [t["id"] for t in data_p2["items"]]

    # 3. Fetch Page 3 (limit=2, final page with 1 remaining item)
    res_p3 = await client.get("/api/v1/tenders?page=3&limit=2", headers=msme_headers)
    assert res_p3.status_code == 200
    data_p3 = res_p3.json()
    assert data_p3["total"] == 5
    assert data_p3["page"] == 3
    assert data_p3["pages"] == 3
    assert len(data_p3["items"]) == 1
    ids_p3 = [t["id"] for t in data_p3["items"]]

    # Strict invariant: Pages 1, 2, and 3 must not overlap
    assert set(ids_p1).isdisjoint(set(ids_p2)), "Page 1 and Page 2 contain overlapping tender records"
    assert set(ids_p2).isdisjoint(set(ids_p3)), "Page 2 and Page 3 contain overlapping tender records"
    assert set(ids_p1).isdisjoint(set(ids_p3)), "Page 1 and Page 3 contain overlapping tender records"

    # All seeded records must be present in the union of all 3 pages
    all_retrieved_ids = set(ids_p1) | set(ids_p2) | set(ids_p3)
    assert len(all_retrieved_ids) == 5, f"Expected 5 unique records across all pages, got {len(all_retrieved_ids)}"

    # Equivalence check: skip=2&limit=2 must yield identical items to page=2&limit=2
    res_skip = await client.get("/api/v1/tenders?skip=2&limit=2", headers=msme_headers)
    assert res_skip.status_code == 200
    data_skip = res_skip.json()
    assert data_skip["page"] == 2
    assert [t["id"] for t in data_skip["items"]] == ids_p2
