import io
import uuid
from datetime import date, datetime, timezone
import pytest
import pymupdf
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, UserRole
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.users import UserRepository
from app.models.tender import Tender


def create_dummy_pdf(content: str = "Annual Turnover Report INR 75,000,000.") -> bytes:
    """Create in-memory PDF with MuPDF for realistic upload tests."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), content)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


async def setup_test_msme(
    client: AsyncClient,
    db_session: AsyncSession,
    email: str = "msme@techcorp.in",
    legal_name: str = "TechCorp Solutions Pvt Ltd",
) -> tuple[dict, uuid.UUID]:
    """Helper creating registered user + company and returning headers and company ID."""
    user_repo = UserRepository(db_session)
    password = "TestPassword123!"
    user = await user_repo.create(
        email=email,
        hashed_password=hash_password(password),
        full_name="TechCorp Admin",
        role=UserRole.MSME_USER.value,
    )

    company_repo = CompanyRepository(db_session)
    company = await company_repo.create(
        owner_id=user.id,
        legal_name=legal_name,
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Technology",
        incorporation_date=date(2019, 1, 15),
        business_type="SMALL",
        annual_turnover=[{"fiscal_year": "2023-2024", "turnover_inr": 80000000.0}],
        work_experience=[
            {
                "client_name": "Metro Rail Corp",
                "domain": "Signaling Software",
                "contract_value": 45000000,
                "duration_years": 4.0,
                "completed": True,
            }
        ],
        certifications=[
            {
                "name": "ISO 27001",
                "valid_until": "2028-12-31",
                "issuing_authority": "BSI",
            }
        ],
    )

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, company.id


@pytest.mark.asyncio
async def test_compliance_analyze_and_reports_api(client: AsyncClient, db_session: AsyncSession):
    """Test POST /compliance/analyze, GET /compliance/reports, and finding inspection."""
    headers, company_id = await setup_test_msme(
        client, db_session, email=f"user_{uuid.uuid4().hex[:6]}@co.in"
    )

    # 1. Create a Tender
    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"API_TND_{uuid.uuid4().hex[:6]}",
        title="Metro Rail IT Overhaul",
        issuing_authority="Metro Authority",
        sector="Transportation",
        submission_deadline=datetime(2027, 8, 30, 18, 0, tzinfo=timezone.utc),
        structured_requirements={
            "turnover": {
                "required_turnover_inr": "50000000.00",
                "is_mandatory": True,
            },
            "experience": {
                "min_years": 3,
                "relevant_domain": "Signaling Software",
                "is_mandatory": True,
            },
            "certifications": [
                {
                    "name": "ISO 27001",
                    "is_mandatory": True,
                }
            ],
        },
    )
    db_session.add(tender)
    await db_session.commit()

    # 2. Trigger Compliance Analysis
    analyze_res = await client.post(
        "/api/v1/compliance/analyze",
        headers=headers,
        json={
            "tender_id": str(tender.id),
            "include_ai_explanation": True,
        },
    )
    assert analyze_res.status_code == 201
    rep_data = analyze_res.json()
    assert rep_data["overall_status"] == "ELIGIBLE"
    assert float(rep_data["overall_score"]) == 100.0
    assert len(rep_data["findings"]) >= 3
    report_id = rep_data["id"]

    # 3. List historical compliance reports
    list_res = await client.get("/api/v1/compliance/reports", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == report_id for item in list_data["items"])

    # 4. Filter historical reports by status
    filter_res = await client.get(
        "/api/v1/compliance/reports?status=ELIGIBLE", headers=headers
    )
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] >= 1

    # 5. Fetch single report by ID
    single_res = await client.get(f"/api/v1/compliance/reports/{report_id}", headers=headers)
    assert single_res.status_code == 200
    assert single_res.json()["id"] == report_id

    # 6. Fetch report findings
    findings_res = await client.get(
        f"/api/v1/compliance/reports/{report_id}/findings", headers=headers
    )
    assert findings_res.status_code == 200
    findings_list = findings_res.json()
    assert len(findings_list) >= 3
    finding_id = findings_list[0]["id"]

    # 7. Fetch single finding by ID
    single_finding_res = await client.get(
        f"/api/v1/compliance/reports/{report_id}/findings/{finding_id}", headers=headers
    )
    assert single_finding_res.status_code == 200
    assert single_finding_res.json()["id"] == finding_id


@pytest.mark.asyncio
async def test_compliance_report_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    """Verify company B cannot view company A's compliance reports (HTTP 404)."""
    headers_a, _ = await setup_test_msme(
        client, db_session, email=f"msme_a_{uuid.uuid4().hex[:6]}@co.in", legal_name="Company A"
    )
    headers_b, _ = await setup_test_msme(
        client, db_session, email=f"msme_b_{uuid.uuid4().hex[:6]}@co.in", legal_name="Company B"
    )

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"ISO_TND_{uuid.uuid4().hex[:6]}",
        title="Solar Plant Inverters",
        issuing_authority="SECI",
        sector="Renewable Energy",
        submission_deadline=datetime(2027, 5, 1, 12, 0, tzinfo=timezone.utc),
        structured_requirements={
            "turnover": {"required_turnover_inr": "10000000.00", "is_mandatory": True}
        },
    )
    db_session.add(tender)
    await db_session.commit()

    # Company A generates a report
    res_a = await client.post(
        "/api/v1/compliance/analyze",
        headers=headers_a,
        json={"tender_id": str(tender.id)},
    )
    assert res_a.status_code == 201
    report_a_id = res_a.json()["id"]

    # Company B attempts to read Company A's report
    leak_res = await client.get(
        f"/api/v1/compliance/reports/{report_a_id}",
        headers=headers_b,
    )
    assert leak_res.status_code == 404
    assert "not found or unauthorized" in leak_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_company_vault_upload_api(client: AsyncClient, db_session: AsyncSession):
    """Verify company can upload and index a PDF in the company vault."""
    headers, _ = await setup_test_msme(
        client, db_session, email=f"vault_user_{uuid.uuid4().hex[:6]}@co.in"
    )

    pdf_bytes = create_dummy_pdf("FY24 Audited Financial Statements Turnover INR 80,000,000.")
    files = {"file": ("Audited_FY24.pdf", pdf_bytes, "application/pdf")}
    data = {"document_category": "FINANCIAL_AUDIT"}

    upload_res = await client.post(
        "/api/v1/company/vault/documents/upload",
        headers=headers,
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201
    resp = upload_res.json()
    assert resp["success"] is True
    assert resp["data"]["original_filename"] == "Audited_FY24.pdf"
    assert resp["data"]["document_category"] == "FINANCIAL_AUDIT"
    assert resp["data"]["processing_status"] in ("INDEXED", "PARTIALLY_INDEXED", "COMPLETED")
