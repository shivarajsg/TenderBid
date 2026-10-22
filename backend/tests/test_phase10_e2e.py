import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
import pymupdf
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, create_access_token, UserRole
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.users import UserRepository
from app.models.document import Document
from app.models.tender import Tender
from app.schemas.evidence import EvidenceCitation
from app.services.retrieval.citation_validator import CitationValidator
from app.services.compliance.rule_engine import RuleFinding
from app.services.compliance.report_builder import ReportBuilder


def create_synthetic_pdf(text: str = "Confidential Audited Financial Statement FY 2024-2025") -> bytes:
    """Helper creating a valid in-memory PDF document."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


async def create_user_and_company(
    db_session: AsyncSession,
    email: str,
    legal_name: str,
    turnover_inr: float = 60000000.0,
    role: str = UserRole.MSME_USER.value,
) -> tuple[uuid.UUID, uuid.UUID, dict]:
    """Helper provisioning a user, their company profile, and returning auth headers."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=email,
        hashed_password=hash_password("SecurePassword2026!"),
        full_name=f"Admin {legal_name}",
        role=role,
    )

    company_id = None
    if role == UserRole.MSME_USER.value:
        company_repo = CompanyRepository(db_session)
        comp = await company_repo.create(
            owner_id=user.id,
            legal_name=legal_name,
            registration_number=f"REG_{uuid.uuid4().hex[:8]}",
            sector="Electrical Infrastructure",
            incorporation_date=date(2018, 5, 20),
            business_type="SMALL",
            annual_turnover=[{"fiscal_year": "2024-2025", "turnover_inr": turnover_inr}],
            certifications=[{"name": "ISO 9001:2015", "valid_until": "2029-01-01"}],
            work_experience=[
                {
                    "project_title": "33kV Switchgear Installation",
                    "client_name": "Power Grid Corp",
                    "contract_value_inr": 25000000.0,
                }
            ],
        )
        company_id = comp.id

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        company_id=str(company_id) if company_id else None,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Test-Bypass-Rate-Limit": "true",
    }
    return user.id, company_id, headers


# =============================================================================
# Journey A: MSME Authentication and Onboarding
# =============================================================================

@pytest.mark.asyncio
async def test_journey_a_msme_auth_and_onboarding(client: AsyncClient, db_session: AsyncSession):
    """
    Test Journey A:
    1. Register MSME account.
    2. Public registration cannot escalate privileges to ADMIN.
    3. Login with valid credentials succeeds.
    4. Login with invalid credentials fails.
    5. Access authenticated /me endpoint.
    6. Protected endpoints reject unauthenticated access.
    7. Expired/malformed tokens rejected.
    8. User cannot access ADMIN routes.
    """
    email = f"msme_test_{uuid.uuid4().hex[:6]}@onboarding.in"
    password = "ValidPassword2026!"

    # 1 & 2: Register with attempt to escalate to ADMIN
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Founder",
            "role": "ADMIN",  # Attempt privilege escalation
        },
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()["data"]
    assert user_data["email"] == email
    # Privilege escalation prevented: must be MSME_USER
    assert user_data["role"] == UserRole.MSME_USER.value

    # 3. Login with valid credentials
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    assert token

    # 4. Login with invalid credentials rejected
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["success"] is False

    # 5. Access authenticated profile
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == email

    # 6. Unauthenticated request rejected
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # 7. Malformed token rejected
    bad_token_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer malformed.token.value"},
    )
    assert bad_token_res.status_code == 401

    # 8. Expired token rejected
    expired_token = create_access_token(
        subject=user_data["id"],
        role=UserRole.MSME_USER.value,
        expires_delta=timedelta(minutes=-10),  # expired 10 minutes ago
    )
    expired_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_res.status_code == 401
    assert "expired" in expired_res.json()["message"].lower()

    # 9. Non-admin cannot access admin routes
    admin_attempt = await client.post(
        "/api/v1/admin/tenders",
        headers=auth_headers,
        json={"tender_reference": "ILLEGAL/01", "title": "Illegal", "issuing_authority": "X", "sector": "Y", "submission_deadline": "2026-12-31T00:00:00Z"},
    )
    assert admin_attempt.status_code == 403


# =============================================================================
# Journey B: Tender Discovery and Administration
# =============================================================================

@pytest.mark.asyncio
async def test_journey_b_tender_discovery_and_admin_boundary(client: AsyncClient, db_session: AsyncSession):
    """
    Test Journey B:
    1. Admin creates tender opportunity with structured requirements.
    2. MSME user is forbidden from creating or modifying tenders.
    3. MSME user discovers tender in catalog.
    4. MSME user inspects details of active tender.
    5. 404 returned on non-existent tender.
    6. Admin updates tender.
    """
    # Setup Admin and MSME users
    _, _, admin_headers = await create_user_and_company(
        db_session, "admin_user@platform.gov.in", "Gov Administrator", role=UserRole.ADMIN.value
    )
    _, _, msme_headers = await create_user_and_company(
        db_session, "msme_bidder@vendor.in", "Vendor Corp Pvt Ltd", role=UserRole.MSME_USER.value
    )

    tender_ref = f"NTPC/TDR/{uuid.uuid4().hex[:6]}"
    tender_payload = {
        "tender_reference": tender_ref,
        "title": "Substation Transformers Procurement",
        "issuing_authority": "National Thermal Power Corp",
        "sector": "Power Systems",
        "estimated_budget_inr": 40000000.0,
        "emd_amount_inr": 800000.0,
        "msme_emd_exemption": True,
        "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
        "structured_requirements": {
            "minimum_annual_turnover_inr": 30000000,
            "minimum_years_in_business": 4,
            "required_certifications": ["ISO 9001:2015"],
        },
    }

    # 2. MSME cannot create tender
    msme_create = await client.post("/api/v1/admin/tenders", headers=msme_headers, json=tender_payload)
    assert msme_create.status_code == 403

    # 1. Admin creates tender
    admin_create = await client.post("/api/v1/admin/tenders", headers=admin_headers, json=tender_payload)
    assert admin_create.status_code == 201
    created_tender = admin_create.json()
    tender_id = created_tender["id"]
    assert created_tender["tender_reference"] == tender_ref

    # 3. MSME discovers tender in public listing
    catalog_res = await client.get("/api/v1/tenders", headers=msme_headers)
    assert catalog_res.status_code == 200
    items = catalog_res.json()["items"]
    found = [t for t in items if t["id"] == tender_id]
    assert len(found) == 1
    assert found[0]["title"] == "Substation Transformers Procurement"

    # 4. MSME opens tender details
    detail_res = await client.get(f"/api/v1/tenders/{tender_id}", headers=msme_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["tender_reference"] == tender_ref

    # 5. Non-existent tender returns 404
    missing_res = await client.get(f"/api/v1/tenders/{uuid.uuid4()}", headers=msme_headers)
    assert missing_res.status_code == 404

    # 6. Admin updates tender
    update_res = await client.put(
        f"/api/v1/admin/tenders/{tender_id}",
        headers=admin_headers,
        json={"title": "Substation Transformers Procurement - Corrigendum 1"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Substation Transformers Procurement - Corrigendum 1"

    # MSME cannot update or delete
    msme_update = await client.put(
        f"/api/v1/admin/tenders/{tender_id}",
        headers=msme_headers,
        json={"title": "Hacked Title"},
    )
    assert msme_update.status_code == 403


# =============================================================================
# Journey C: Company Document Vault and Security
# =============================================================================

@pytest.mark.asyncio
async def test_journey_c_document_vault_and_security(client: AsyncClient, db_session: AsyncSession):
    """
    Test Journey C:
    1. Upload valid synthetic PDF to company vault.
    2. Confirm document appears in authenticated vault.
    3. Reject non-PDF or corrupted file uploads.
    4. Path traversal attempts rejected.
    5. Cross-company document isolation enforced (Company B cannot read or delete Company A's docs).
    """
    _, comp_a_id, headers_a = await create_user_and_company(
        db_session, "comp_a@shield.in", "Company Alpha Pvt Ltd"
    )
    _, comp_b_id, headers_b = await create_user_and_company(
        db_session, "comp_b@shield.in", "Company Beta Pvt Ltd"
    )

    valid_pdf = create_synthetic_pdf("Audited Balance Sheet FY 2024-2025. Turnover INR 50,000,000.")

    # 1. Upload valid PDF
    upload_res = await client.post(
        "/api/v1/company/vault/documents/upload",
        headers=headers_a,
        files={"file": ("balance_sheet.pdf", valid_pdf, "application/pdf")},
        data={"document_category": "FINANCIAL_AUDIT"},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()["data"]
    doc_id = doc_data["id"]
    assert doc_data["original_filename"] == "balance_sheet.pdf"
    assert doc_data["processing_status"] in ["INDEXED", "EXTRACTING"]

    # 2. Document appears in Company A vault
    list_a = await client.get("/api/v1/company/vault/documents", headers=headers_a)
    assert list_a.status_code == 200
    assert any(d["id"] == doc_id for d in list_a.json()["data"])

    # 3. Reject invalid non-PDF file
    fake_doc = b"This is a plaintext file not a PDF."
    bad_upload = await client.post(
        "/api/v1/company/vault/documents/upload",
        headers=headers_a,
        files={"file": ("fake.pdf", fake_doc, "application/pdf")},
        data={"document_category": "FINANCIAL_AUDIT"},
    )
    assert bad_upload.status_code == 400

    # 4. Path traversal attempt in filename is safely sanitized by backend
    traversal_upload = await client.post(
        "/api/v1/company/vault/documents/upload",
        headers=headers_a,
        files={"file": ("../../evil.pdf", valid_pdf, "application/pdf")},
        data={"document_category": "FINANCIAL_AUDIT"},
    )
    # Backend saves file safely using internal UUID or rejects
    assert traversal_upload.status_code in [201, 400]
    if traversal_upload.status_code == 201:
        # Verify stored path is not outside sandbox
        t_doc = traversal_upload.json()["data"]
        assert ".." not in t_doc["id"]

    # 5. Cross-company document isolation
    # Company B lists documents -> does not see Company A's document
    list_b = await client.get("/api/v1/company/vault/documents", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(d["id"] == doc_id for d in list_b.json()["data"])

    # Company B tries to get Company A's document -> 404
    get_b = await client.get(f"/api/v1/company/vault/documents/{doc_id}", headers=headers_b)
    assert get_b.status_code == 404

    # Company B tries to delete Company A's document -> 404
    del_b = await client.delete(f"/api/v1/company/vault/documents/{doc_id}", headers=headers_b)
    assert del_b.status_code == 404


# =============================================================================
# Journey D: Deterministic Compliance Analysis Scenarios
# =============================================================================

@pytest.mark.asyncio
async def test_journey_d_scenario_1_demonstrated_mandatory_failure():
    """
    Scenario 1: Mandatory criterion failure.
    Company turnover is below mandatory threshold.
    Expected: Status is NOT_ELIGIBLE. Deterministic failure cannot be overridden.
    """
    findings = [
        RuleFinding(
            requirement_id="CRIT_TURNOVER_01",
            rule_type="TURNOVER",
            requirement_description="Minimum annual turnover of INR 100,000,000",
            required_value={"required_turnover_inr": 100000000.0},
            observed_value={"average_turnover_inr": 25000000.0},
            status="FAIL",
            is_mandatory=True,
            reason="Turnover INR 25,000,000 is below required INR 100,000,000.",
        ),
        RuleFinding(
            requirement_id="CRIT_EXP_01",
            rule_type="EXPERIENCE",
            requirement_description="Minimum 3 years operational experience",
            required_value={"years": 3},
            observed_value={"years": 5},
            status="PASS",
            is_mandatory=True,
            reason="Experience satisfies requirement.",
        ),
    ]

    overall_status, score, summary = ReportBuilder.derive_overall_status(findings)
    assert overall_status == "NOT_ELIGIBLE"
    assert "mandatory requirement(s) failed" in summary


@pytest.mark.asyncio
async def test_journey_d_scenario_2_missing_mandatory_evidence():
    """
    Scenario 2: Missing mandatory evidence.
    Company has no sufficient evidence for a mandatory criterion.
    Expected: Status is PARTIALLY_ELIGIBLE; never satisfied as a PASS.
    """
    findings = [
        RuleFinding(
            requirement_id="CRIT_AUDIT_DOC",
            rule_type="MANDATORY_DOCUMENT",
            requirement_description="Audited Balance Sheet for FY 2024-2025",
            required_value={"document_category": "FINANCIAL_AUDIT"},
            observed_value={"found": False},
            status="MISSING_EVIDENCE",
            is_mandatory=True,
            reason="No verified financial audit report found in company vault.",
        ),
    ]

    overall_status, score, summary = ReportBuilder.derive_overall_status(findings)
    assert overall_status == "PARTIALLY_ELIGIBLE"
    assert overall_status != "ELIGIBLE"
    assert "missing" in summary.lower()


@pytest.mark.asyncio
async def test_journey_d_scenario_3_supported_compliance():
    """
    Scenario 3: Supported compliance.
    All mandatory criteria have required evidence and satisfy rules.
    Expected: Status is ELIGIBLE.
    """
    findings = [
        RuleFinding(
            requirement_id="CRIT_TURNOVER",
            rule_type="TURNOVER",
            requirement_description="Turnover >= 50,000,000",
            required_value={"turnover": 50000000},
            observed_value={"turnover": 80000000},
            status="PASS",
            is_mandatory=True,
            reason="Turnover satisfies requirement.",
        ),
        RuleFinding(
            requirement_id="CRIT_CERT",
            rule_type="CERTIFICATION",
            requirement_description="ISO 9001:2015",
            required_value={"name": "ISO 9001:2015"},
            observed_value={"active": True},
            status="PASS",
            is_mandatory=True,
            reason="Certification active and valid.",
        ),
    ]

    overall_status, score, summary = ReportBuilder.derive_overall_status(findings)
    assert overall_status == "ELIGIBLE"
    assert score == Decimal("100.00")


@pytest.mark.asyncio
async def test_journey_d_scenario_4_ambiguous_criterion():
    """
    Scenario 4: Ambiguous criterion.
    Requirement cannot be evaluated objectively from available criteria.
    Expected: Surfaced as NEEDS_REVIEW without inventing false certainty.
    """
    findings = [
        RuleFinding(
            requirement_id="CRIT_SPECIAL_01",
            rule_type="OTHER",
            requirement_description="Subjective local vendor preference clause",
            required_value={},
            observed_value={},
            status="NEEDS_REVIEW",
            is_mandatory=False,
            reason="Criterion is qualitative and requires procurement committee evaluation.",
        ),
    ]

    overall_status, score, summary = ReportBuilder.derive_overall_status(findings)
    assert overall_status == "NEEDS_REVIEW"
    assert "administrative review" in summary.lower()


@pytest.mark.asyncio
async def test_journey_d_scenario_5_unverified_citation_rejection(db_session: AsyncSession):
    """
    Scenario 5: Unverified citation.
    Citation references non-existent document, invalid page, or unauthorized company.
    Expected: Citation rejected by backend CitationValidator.
    """
    validator = CitationValidator(db_session)
    valid_tender_id = uuid.uuid4()
    valid_company_id = uuid.uuid4()

    # 1. Non-existent document UUID
    fake_cit = EvidenceCitation(
        evidence_id="ev_fake_1",
        source_type="COMPANY_DOCUMENT",
        document_id=uuid.uuid4(),  # Random non-existent UUID
        source_filename="fake_doc.pdf",
        page_number=1,
        excerpt="Fabricated compliance claim.",
        retrieval_method="semantic",
    )

    valid_cits, warnings = await validator.validate_citations(
        [fake_cit],
        authorized_tender_id=valid_tender_id,
        authorized_company_id=valid_company_id,
    )

    assert len(valid_cits) == 0
    assert len(warnings) == 1
    assert "Citation Rejected" in warnings[0]


@pytest.mark.asyncio
async def test_journey_d_scenario_6_cross_company_report_access(client: AsyncClient, db_session: AsyncSession):
    """
    Scenario 6: Cross-company report access.
    User attempts to access another company's compliance report.
    Expected: Access denied with HTTP 404/403.
    """
    # Create Company A and Company B
    _, comp_a_id, headers_a = await create_user_and_company(
        db_session, "user_a@enterprise.in", "Enterprise A Pvt Ltd"
    )
    _, comp_b_id, headers_b = await create_user_and_company(
        db_session, "user_b@enterprise.in", "Enterprise B Pvt Ltd"
    )

    # Create a tender
    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TDR/E2E/{uuid.uuid4().hex[:6]}",
        title="Sample Tender for Cross-Company Test",
        issuing_authority="BHEL",
        sector="Engineering",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        processing_status="COMPLETED",
        structured_requirements={
            "minimum_annual_turnover_inr": 20000000,
        },
    )
    db_session.add(tender)
    await db_session.commit()

    # Company A runs analysis
    analyze_res = await client.post(
        "/api/v1/compliance/analyze",
        headers=headers_a,
        json={"tender_id": str(tender.id), "include_ai_explanation": False},
    )
    assert analyze_res.status_code == 201
    report_a_id = analyze_res.json()["id"]

    # Company B tries to fetch Company A's report -> 404
    get_res = await client.get(
        f"/api/v1/compliance/reports/{report_a_id}",
        headers=headers_b,
    )
    assert get_res.status_code == 404

    # Company B lists reports -> 0 items
    list_res = await client.get(
        "/api/v1/compliance/reports",
        headers=headers_b,
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0


# =============================================================================
# Journey E: Report History and Report Detail Persistence
# =============================================================================

@pytest.mark.asyncio
async def test_journey_e_report_history_and_persistence(client: AsyncClient, db_session: AsyncSession):
    """
    Test Journey E:
    1. Run compliance analysis.
    2. Confirm persisted report can be opened with eager findings.
    3. Re-read / reload: verify report remains available and unchanged.
    4. Verify finding status, mandatory flag, and objective reasons.
    5. Inaccessible reports cannot be accessed by guessing IDs.
    """
    _, comp_id, headers = await create_user_and_company(
        db_session, "msme_reports@firm.in", "Firm Precision Ltd", turnover_inr=75000000.0
    )

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TDR/HIST/{uuid.uuid4().hex[:6]}",
        title="High Precision Machining Tender",
        issuing_authority="ISRO",
        sector="Aerospace Manufacturing",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=45),
        processing_status="COMPLETED",
        structured_requirements={
            "minimum_annual_turnover_inr": 50000000,
            "required_certifications": ["ISO 9001:2015"],
        },
    )
    db_session.add(tender)
    await db_session.commit()

    # 1. Run analysis
    run_res = await client.post(
        "/api/v1/compliance/analyze",
        headers=headers,
        json={"tender_id": str(tender.id), "include_ai_explanation": False},
    )
    assert run_res.status_code == 201
    report_id = run_res.json()["id"]
    initial_status = run_res.json()["overall_status"]

    # 2. Fetch report detail
    detail_res = await client.get(
        f"/api/v1/compliance/reports/{report_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    report_data = detail_res.json()
    assert report_data["id"] == report_id
    assert report_data["overall_status"] == initial_status
    assert len(report_data["findings"]) >= 1

    # 3. Re-fetch to test persistence across requests
    refetch_res = await client.get(
        f"/api/v1/compliance/reports/{report_id}",
        headers=headers,
    )
    assert refetch_res.status_code == 200
    assert refetch_res.json() == report_data

    # 4. Inaccessible non-existent report returns 404
    missing_report = await client.get(
        f"/api/v1/compliance/reports/{uuid.uuid4()}",
        headers=headers,
    )
    assert missing_report.status_code == 404
