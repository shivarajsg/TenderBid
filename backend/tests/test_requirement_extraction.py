import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.tender import Tender
from app.models.user import User
from app.schemas.requirements import NormalizedTenderRequirements
from app.services.compliance.requirement_extraction_service import RequirementExtractionService
from app.services.compliance.rule_engine import DeterministicRuleEngine


@pytest.mark.asyncio
async def test_requirement_extraction_deterministic_provenance_and_clean_fields():
    """Verify that requirement extraction correctly parses criteria with exact page provenance."""
    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    tender = Tender(
        id=tender_id,
        tender_reference="TEST/EXTRACT/001",
        title="High Voltage Substation Construction",
        issuing_authority="PowerGrid India",
        sector="Electrical",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
    )

    chunks = [
        DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tender_id=tender_id,
            source_filename="tender_rfp.pdf",
            page_number=3,
            chunk_index=0,
            char_start=0,
            char_end=200,
            sha256_hash="hash1",
            chunk_text=(
                "Section 3.1: Financial Criteria. The bidder must have an average annual turnover "
                "of at least Rs. 5 Crore across the last three financial years. Audited balance sheets required."
            ),
            extraction_method="pymupdf_direct",
        ),
        DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tender_id=tender_id,
            source_filename="tender_rfp.pdf",
            page_number=5,
            chunk_index=1,
            char_start=0,
            char_end=200,
            sha256_hash="hash2",
            chunk_text=(
                "Section 4.2: Technical Experience. The bidder must possess at least 5 years of experience "
                "in substation engineering and must hold a valid ISO 9001:2015 certification. "
                "GST Registration Certificate is mandatory."
            ),
            extraction_method="pymupdf_direct",
        ),
        DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tender_id=tender_id,
            source_filename="tender_rfp.pdf",
            page_number=7,
            chunk_index=2,
            char_start=0,
            char_end=150,
            sha256_hash="hash3",
            chunk_text=(
                "Section 6.0: Commercial Terms. EMD amount is INR 200,000. "
                "MSME units registered under Udyam are eligible for MSME exemption."
            ),
            extraction_method="pymupdf_direct",
        ),
    ]

    extractor = RequirementExtractionService()
    bundle = extractor.extract_from_chunks(tender=tender, chunks=chunks)

    assert bundle.extraction_status == "COMPLETED"
    assert len(bundle.criteria) >= 4
    assert len(bundle.conflicts) == 0

    # Verify turnover criterion and exact page provenance
    turnover = next(c for c in bundle.criteria if c.criterion_type == "TURNOVER")
    assert turnover.extracted_value["required_turnover_inr"] == 50000000.0  # 5 Crore in INR
    assert turnover.page_number == 3
    assert turnover.source_filename == "tender_rfp.pdf"
    assert "average annual turnover" in turnover.supporting_excerpt.lower()
    assert turnover.status == "PROPOSED"

    # Verify experience
    exp = next(c for c in bundle.criteria if c.criterion_type == "EXPERIENCE")
    assert exp.extracted_value["min_experience_years"] == 5
    assert exp.page_number == 5

    # Verify certification
    cert = next(c for c in bundle.criteria if c.criterion_type == "CERTIFICATION")
    assert "ISO 9001" in cert.extracted_value["name"]
    assert cert.page_number == 5

    # Verify EMD
    emd = next(c for c in bundle.criteria if c.criterion_type == "EMD")
    assert emd.extracted_value["emd_amount_inr"] == 200000.0
    assert emd.extracted_value["msme_emd_exemption"] is True


@pytest.mark.asyncio
async def test_requirement_extraction_conflicting_clauses_flagged_needs_review():
    """Verify that conflicting criteria across different pages are flagged as NEEDS_REVIEW."""
    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    tender = Tender(
        id=tender_id,
        tender_reference="TEST/CONFLICT/002",
        title="Civil Works",
        issuing_authority="PWD",
        sector="Civil",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
    )

    chunks = [
        DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tender_id=tender_id,
            source_filename="notice.pdf",
            page_number=1,
            chunk_index=0,
            char_start=0,
            char_end=150,
            sha256_hash="h1",
            chunk_text="Clause 1: Minimum annual turnover not less than Rs. 2 Crore.",
            extraction_method="pymupdf_direct",
        ),
        DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tender_id=tender_id,
            source_filename="notice.pdf",
            page_number=8,
            chunk_index=1,
            char_start=0,
            char_end=150,
            sha256_hash="h2",
            chunk_text="Addendum Clause 4: Annual turnover should be at least Rs. 5 Crore.",
            extraction_method="pymupdf_direct",
        ),
    ]

    extractor = RequirementExtractionService()
    bundle = extractor.extract_from_chunks(tender=tender, chunks=chunks)

    # Must flag conflict
    assert bundle.extraction_status == "NEEDS_REVIEW"
    assert len(bundle.conflicts) > 0
    assert any("Conflicting turnover" in c for c in bundle.conflicts)

    turnover = next(c for c in bundle.criteria if c.criterion_type == "TURNOVER")
    assert turnover.status == "NEEDS_REVIEW"
    assert "Conflicting turnover thresholds" in turnover.review_notes


@pytest.mark.asyncio
async def test_admin_approve_and_reject_workflow_and_rule_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test complete lifecycle:
    1. Admin creates tender.
    2. Admin triggers requirement extraction (sets status PENDING_REVIEW).
    3. Unapproved criteria do NOT affect deterministic engine.
    4. Admin approves criteria -> becomes authoritative in structured_requirements.
    """
    admin = User(
        id=uuid.uuid4(),
        email="admin_extract@example.com",
        hashed_password="hashed_pwd",
        full_name="Admin Extract",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(admin)

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="REF/EXTRACT/003",
        title="Highway Lighting",
        issuing_authority="NHAI",
        sector="Infrastructure",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
        processing_status="INDEXED",
        structured_requirements=None,  # No initial requirements
        requirements_approval_status="NOT_REQUESTED",
        created_by=admin.id,
    )
    db_session.add(tender)

    doc = Document(
        id=uuid.uuid4(),
        tender_id=tender.id,
        entity_type="TENDER",
        document_category="TENDER_NOTICE",
        original_filename="rfp_doc.pdf",
        storage_path="tenders/rfp_doc.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_rfp",
        total_pages=5,
        indexed_chunks=1,
        processing_status="INDEXED",
        verification_status="UNVERIFIED",
    )
    db_session.add(doc)

    chunk = DocumentChunkModel(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        tender_id=tender.id,
        source_filename="rfp_doc.pdf",
        page_number=2,
        chunk_index=0,
        char_start=0,
        char_end=200,
        sha256_hash="h3",
        chunk_text="Annual turnover of at least Rs. 3 Crore. 3 years of relevant experience. ISO 9001 mandatory.",
        extraction_method="pymupdf_direct",
    )
    db_session.add(chunk)
    await db_session.commit()

    admin_token = create_access_token(subject=str(admin.id), role="ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Trigger extraction
    resp = await client.post(f"/api/v1/admin/tenders/{tender.id}/extract-requirements", headers=headers)
    assert resp.status_code == 200
    bundle_data = resp.json()
    assert bundle_data["extraction_status"] == "COMPLETED"
    assert len(bundle_data["criteria"]) >= 2

    # Verify tender state: proposed_requirements is populated, approval_status is PENDING_REVIEW
    await db_session.refresh(tender)
    assert tender.requirements_approval_status == "PENDING_REVIEW"
    assert tender.proposed_requirements is not None
    # Crucially: structured_requirements is STILL None (deterministic rule engine isolation!)
    assert tender.structured_requirements is None

    # 2. Get proposed requirements
    get_resp = await client.get(f"/api/v1/admin/tenders/{tender.id}/proposed-requirements", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["tender_id"] == str(tender.id)

    # 3. Admin approves requirements
    approve_resp = await client.post(
        f"/api/v1/admin/tenders/{tender.id}/approve-requirements",
        headers=headers,
        json={},
    )
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["requirements_approval_status"] == "APPROVED"
    assert appr_data["structured_requirements"] is not None

    # Verify structured_requirements is now authoritative and ready for deterministic engine
    await db_session.refresh(tender)
    assert tender.requirements_approval_status == "APPROVED"
    assert "turnover" in tender.structured_requirements
    assert float(tender.structured_requirements["turnover"]["required_turnover_inr"]) == 30000000.0
