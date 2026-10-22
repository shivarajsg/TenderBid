import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.compliance_finding import ComplianceFinding
from app.models.compliance_report import ComplianceReport
from app.models.document import Document
from app.models.tender import Tender
from app.models.user import User
from app.schemas.compliance import ComplianceFindingResponse, ComplianceReportResponse
from app.schemas.evidence import EvidenceCitation
from app.schemas.requirements import (
    CertificationRequirement,
    CommercialRequirement,
    DeadlineRequirement,
    ExperienceRequirement,
    LegalRequirement,
    MandatoryDocumentRequirement,
    NormalizedTenderRequirements,
    TechnicalRequirement,
    TurnoverRequirement,
)
from app.services.compliance.report_builder import ReportBuilder
from app.services.compliance.rule_engine import DeterministicRuleEngine, get_rule_engine
from app.services.retrieval.citation_validator import CitationValidator
from app.services.workflows.compliance_graph import ComplianceWorkflowOrchestrator


@pytest.fixture
def rule_engine():
    return get_rule_engine()


@pytest.mark.asyncio
async def test_deterministic_turnover_pass_fail_and_missing(rule_engine: DeterministicRuleEngine):
    """Test turnover evaluation: PASS, FAIL, and MISSING_EVIDENCE."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("50000000.00"),  # 5 Crore
        currency="INR",
        comparison_method="AVERAGE_TURNOVER",
        financial_years_count=3,
        is_mandatory=True,
    )

    # 1. Missing evidence
    f_missing = rule_engine.evaluate_turnover(req, [])
    assert f_missing.status == "MISSING_EVIDENCE"
    assert f_missing.is_mandatory is True
    assert "CRIT_TURNOVER_01" in f_missing.requirement_id
    assert "No audited financial turnover records" in f_missing.reason
    assert "title" in f_missing.required_value
    assert "FINANCIAL" in f_missing.required_value["category"]

    # 2. Confirmed failure (Turnover 3 Cr < 5 Cr)
    low_turnover = [
        {"fiscal_year": "2023-2024", "turnover_inr": 30000000.0},
        {"fiscal_year": "2022-2023", "turnover_inr": 28000000.0},
        {"fiscal_year": "2021-2022", "turnover_inr": 32000000.0},
    ]
    f_fail = rule_engine.evaluate_turnover(req, low_turnover)
    assert f_fail.status == "FAIL"
    assert "falls below mandatory requirement" in f_fail.reason
    assert f_fail.observed_value["average_turnover_inr"] == 30000000.0
    assert "shortfall" in f_fail.observed_value["evidence_gap"].lower()

    # 3. Passing turnover (Turnover 6 Cr >= 5 Cr)
    high_turnover = [
        {"fiscal_year": "2023-2024", "turnover_inr": 65000000.0},
        {"fiscal_year": "2022-2023", "turnover_inr": 60000000.0},
        {"fiscal_year": "2021-2022", "turnover_inr": 55000000.0},
    ]
    f_pass = rule_engine.evaluate_turnover(req, high_turnover)
    assert f_pass.status == "PASS"
    assert f_pass.observed_value["average_turnover_inr"] == 60000000.0


@pytest.mark.asyncio
async def test_deterministic_experience_duration_and_projects_shortfall(rule_engine: DeterministicRuleEngine):
    """Test experience evaluation flags duration and project count shortfalls accurately."""
    req = ExperienceRequirement(
        min_experience_years=5,
        min_completed_projects=3,
        relevant_domain="Power Distribution",
        is_mandatory=True,
    )

    # Shortfall: 1 project spanning 2 years
    short_records = [
        {
            "project_title": "Local Substation Wiring",
            "domain": "Power Distribution",
            "duration_years": 2.0,
            "contract_value_inr": 10000000,
        }
    ]
    f_short = rule_engine.evaluate_experience(req, short_records)
    assert f_short.status == "FAIL"
    assert "fall short" in f_short.reason
    assert f_short.observed_value["matching_projects_count"] == 1
    assert f_short.observed_value["total_experience_years"] == 2.0

    # Adequate: 3 projects spanning 6 years in domain
    adequate_records = [
        {"project_title": "Project Alpha", "domain": "Power Distribution", "duration_years": 2.5},
        {"project_title": "Project Beta", "domain": "Power Distribution", "duration_years": 2.0},
        {"project_title": "Project Gamma", "domain": "Power Distribution", "duration_years": 1.5},
    ]
    f_pass = rule_engine.evaluate_experience(req, adequate_records)
    assert f_pass.status == "PASS"
    assert f_pass.observed_value["matching_projects_count"] == 3
    assert f_pass.observed_value["total_experience_years"] == 6.0


@pytest.mark.asyncio
async def test_deterministic_certification_active_vs_expired_vs_missing(rule_engine: DeterministicRuleEngine):
    """Test certification check distinguishes missing vs expired vs active certificate."""
    req = CertificationRequirement(name="ISO 9001:2015", is_mandatory=True)

    # 1. Missing evidence (no cert registered)
    f_missing = rule_engine.evaluate_certification(req, [], [])
    assert f_missing.status == "MISSING_EVIDENCE"
    assert "No certification credentials registered" in f_missing.reason

    # 2. Expired certificate (Confirmed failure)
    expired_certs = [
        {
            "name": "ISO 9001:2015",
            "valid_until": "2022-01-01",
            "issuing_authority": "TUV",
        }
    ]
    f_expired = rule_engine.evaluate_certification(req, expired_certs, [])
    assert f_expired.status == "FAIL"
    assert "expired on 2022-01-01" in f_expired.reason

    # 3. Valid active certificate (Pass)
    active_certs = [
        {
            "name": "ISO 9001:2015",
            "valid_until": "2029-12-31",
            "issuing_authority": "Bureau Veritas",
        }
    ]
    f_pass = rule_engine.evaluate_certification(req, active_certs, [])
    assert f_pass.status == "PASS"
    assert "Valid and active certificate" in f_pass.reason


@pytest.mark.asyncio
async def test_deterministic_commercial_msme_emd_exemption(rule_engine: DeterministicRuleEngine):
    """Test EMD exemption for MSME Udyam registration vs non-MSME missing EMD."""
    req = CommercialRequirement(
        title="Earnest Money Deposit",
        condition_type="EMD",
        amount_inr=Decimal("250000.00"),
        msme_exemptible=True,
        is_mandatory=True,
    )

    # MSME company profile
    msme_company = {
        "registration_number": "UDYAM-MH-01-0099887",
        "business_type": "SMALL",
        "sector": "Manufacturing",
    }
    f_exempt = rule_engine.evaluate_commercial(req, msme_company, [])
    assert f_exempt.status == "PASS"
    assert "100% EMD exemption" in f_exempt.reason
    assert f_exempt.observed_value["exemption_claimed"] is True

    # Non-MSME without EMD proof in vault
    non_msme = {
        "registration_number": "CIN-U12345MH2020PTC001",
        "business_type": "LARGE",
        "sector": "Manufacturing",
    }
    f_unpaid = rule_engine.evaluate_commercial(req, non_msme, [])
    assert f_unpaid.status == "MISSING_EVIDENCE"
    assert "No payment proof or valid MSME exemption" in f_unpaid.reason


@pytest.mark.asyncio
async def test_deterministic_technical_specification_review(rule_engine: DeterministicRuleEngine):
    """Test technical specification evaluation flagging review when proof is pending."""
    req = TechnicalRequirement(
        title="Vacuum Circuit Breaker Short-Circuit Rating",
        specification="Must withstand minimum 31.5kA for 3 seconds as per IEC 62271-100.",
        is_mandatory=True,
    )

    company_prof = {"sector": "Electrical Infrastructure"}
    # No datasheet uploaded in vault
    f_tech = rule_engine.evaluate_technical(req, company_prof, [])
    assert f_tech.status == "NEEDS_REVIEW"
    assert "requires human technical review" in f_tech.reason


@pytest.mark.asyncio
async def test_report_builder_overall_status_calculations():
    """Verify non-overlapping overall status calculations and priority checklists."""
    # 1. No documents
    stat_no_doc, score_no_doc, summary_no_doc = ReportBuilder.derive_overall_status(
        findings=[], has_usable_tender_documents=False
    )
    assert stat_no_doc == "ANALYSIS_BLOCKED_NO_DOCUMENTS"
    assert "Full compliance analysis is unavailable because no usable tender documents have been indexed" in summary_no_doc

    # 2. Mandatory failure overrides eligible items
    req_fail = TurnoverRequirement(
        required_turnover_inr=Decimal("50000000.00"),
        comparison_method="AVERAGE_TURNOVER",
        is_mandatory=True,
    )
    f_fail = get_rule_engine().evaluate_turnover(req_fail, [{"fiscal_year": "2024", "turnover_inr": 10000000.0}])

    stat_fail, _, _ = ReportBuilder.derive_overall_status([f_fail], has_usable_tender_documents=True)
    assert stat_fail == "NOT_ELIGIBLE"

    # 3. Missing evidence results in PARTIALLY_ELIGIBLE
    f_missing = get_rule_engine().evaluate_turnover(req_fail, [])
    stat_missing, _, _ = ReportBuilder.derive_overall_status([f_missing], has_usable_tender_documents=True)
    assert stat_missing == "PARTIALLY_ELIGIBLE"


@pytest.mark.asyncio
async def test_blocked_analysis_when_no_usable_tender_documents(db_session: AsyncSession):
    """Test orchestrator execution when selected tender has 0 usable indexed documents."""
    user = User(
        id=uuid.uuid4(),
        email=f"tester_{uuid.uuid4().hex[:6]}@co.com",
        hashed_password="pw",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    company = Company(
        id=uuid.uuid4(),
        owner_id=user.id,
        legal_name="Test Co",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Engineering",
        incorporation_date=date(2020, 1, 1),
    )
    db_session.add(company)
    await db_session.flush()

    # Tender without any attached documents or structured requirements
    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TND_NODOC_{uuid.uuid4().hex[:6]}",
        title="Unprocessed Tender Notice",
        issuing_authority="Public Authority",
        sector="Civil",
        submission_deadline=datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc),
        processing_status="PENDING",
    )
    db_session.add(tender)
    await db_session.commit()

    orchestrator = ComplianceWorkflowOrchestrator(db_session)
    state = await orchestrator.execute(
        tender_id=tender.id,
        company_id=company.id,
        user_id=user.id,
        include_ai_explanation=False,
    )

    assert state.get("overall_status") == "ANALYSIS_BLOCKED_NO_DOCUMENTS"
    assert state.get("has_usable_tender_documents") is False
    assert any("Full compliance analysis is unavailable" in lim for lim in state.get("limitations", []))


@pytest.mark.asyncio
async def test_finding_response_model_exposes_all_17_fields():
    """Verify that ComplianceFindingResponse model validator automatically surfaces all Section 6 fields."""
    finding_id = uuid.uuid4()
    resp = ComplianceFindingResponse(
        id=finding_id,
        requirement_id="CRIT_TURNOVER_01",
        rule_type="TURNOVER",
        requirement_description="Minimum turnover of INR 50,000,000.00",
        required_value={
            "title": "Minimum Annual Turnover Threshold",
            "category": "FINANCIAL",
            "original_clause": "Average annual turnover of at least INR 50,000,000.",
            "tender_source": "Tender Document Clause 4.1, Page 2",
            "plain_english_interpretation": "Requires audited revenue >= 5 Cr.",
            "specific_condition": "INR 50,000,000.00 over 3 FYs",
            "needs_human_review": False,
        },
        observed_value={
            "applicable_company_info": "Achieved turnover of INR 65,000,000.",
            "company_evidence": "Audited_FY25.pdf, Page 1",
            "comparison_evaluation": "Turnover exceeds requirement by 15,000,000 INR.",
            "evidence_gap": "None",
            "risk_and_consequence": "No risk.",
            "recommended_action": "Attach CA certificate.",
        },
        status="PASS",
        is_mandatory=True,
        reason="Turnover satisfies minimum requirement.",
        created_at=datetime.now(timezone.utc),
    )

    # Assert that all 17 fields from Section 6 are directly exposed
    assert resp.requirement_id == "CRIT_TURNOVER_01"
    assert resp.category == "FINANCIAL"
    assert resp.title == "Minimum Annual Turnover Threshold"
    assert resp.original_clause == "Average annual turnover of at least INR 50,000,000."
    assert resp.tender_source == "Tender Document Clause 4.1, Page 2"
    assert resp.plain_english_interpretation == "Requires audited revenue >= 5 Cr."
    assert resp.specific_condition == "INR 50,000,000.00 over 3 FYs"
    assert resp.applicable_company_info == "Achieved turnover of INR 65,000,000."
    assert resp.company_evidence == "Audited_FY25.pdf, Page 1"
    assert resp.comparison_evaluation == "Turnover exceeds requirement by 15,000,000 INR."
    assert resp.status == "PASS"
    assert resp.evidence_gap == "None"
    assert resp.risk_and_consequence == "No risk."
    assert resp.recommended_action == "Attach CA certificate."
    assert resp.needs_human_review is False


@pytest.mark.asyncio
async def test_citation_validator_rejects_out_of_bounds_pages(db_session: AsyncSession):
    """Verify CitationValidator rejects citations referencing non-existent physical PDF pages."""
    tender_id = uuid.uuid4()
    company_id = uuid.uuid4()

    # Create Tender first to satisfy foreign key
    tender = Tender(
        id=tender_id,
        tender_reference=f"TND_VAL_{uuid.uuid4().hex[:6]}",
        title="Validation Test Tender",
        issuing_authority="Auth",
        sector="Test",
        submission_deadline=datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(tender)
    await db_session.flush()

    # Document with total_pages = 5
    doc = Document(
        id=uuid.uuid4(),
        tender_id=tender_id,
        original_filename="Tender_Spec.pdf",
        storage_path="tenders/spec.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="abc",
        total_pages=5,
    )
    db_session.add(doc)
    await db_session.commit()

    validator = CitationValidator(db_session)

    # Citation with page_number = 99 (Out of bounds)
    out_of_bounds = EvidenceCitation(
        evidence_id="cit_invalid_page",
        source_type="TENDER_DOCUMENT",
        document_id=doc.id,
        source_filename=doc.original_filename,
        page_number=99,
        excerpt="Fabricated page quotation",
    )

    valid_cits, warnings = await validator.validate_citations(
        [out_of_bounds], authorized_tender_id=tender_id, authorized_company_id=company_id
    )

    assert len(valid_cits) == 0
    assert any("out of bounds" in w for w in warnings)
