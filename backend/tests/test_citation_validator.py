import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.company import Company
from app.models.tender import Tender
from app.models.document import Document
from app.schemas.evidence import EvidenceCitation
from app.services.retrieval.citation_validator import CitationValidator


@pytest.mark.asyncio
async def test_citation_validator_valid_and_filename_correction(db_session: AsyncSession):
    """Test that valid citations pass and filename mismatches are automatically corrected."""
    user = User(
        id=uuid.uuid4(),
        email=f"valid_{uuid.uuid4().hex[:6]}@co.com",
        hashed_password="pw",
        full_name="Valid User",
    )
    db_session.add(user)
    await db_session.flush()

    company = Company(
        id=uuid.uuid4(),
        owner_id=user.id,
        legal_name="Valid MSME Pvt Ltd",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Tech",
        incorporation_date=date(2020, 1, 1),
    )
    db_session.add(company)
    await db_session.flush()

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TND_{uuid.uuid4().hex[:6]}",
        title="Valid Tender",
        issuing_authority="Railways",
        sector="Transportation",
        submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
        created_by=user.id,
    )
    db_session.add(tender)
    await db_session.flush()

    doc_company = Document(
        id=uuid.uuid4(),
        company_id=company.id,
        entity_type="COMPANY",
        original_filename="Audited_Financials_FY24.pdf",
        storage_path=f"companies/{company.id}/audited.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        total_pages=10,
        processing_status="INDEXED",
        sha256_hash="hash_c",
    )
    doc_tender = Document(
        id=uuid.uuid4(),
        tender_id=tender.id,
        entity_type="TENDER",
        original_filename="NIT_Tender_Notice.pdf",
        storage_path=f"tenders/{tender.id}/nit.pdf",
        mime_type="application/pdf",
        file_size_bytes=4096,
        total_pages=5,
        processing_status="INDEXED",
        sha256_hash="hash_t",
    )
    db_session.add_all([doc_company, doc_tender])
    await db_session.flush()

    validator = CitationValidator(db_session)

    citations = [
        EvidenceCitation(
            evidence_id="ev_1",
            source_type="COMPANY_DOCUMENT",
            document_id=doc_company.id,
            source_filename="wrong_filename.pdf",  # Mismatched name
            page_number=3,
            excerpt="Turnover verified at 5.4 Crores",
        ),
        EvidenceCitation(
            evidence_id="ev_2",
            source_type="TENDER_DOCUMENT",
            document_id=doc_tender.id,
            source_filename="NIT_Tender_Notice.pdf",
            page_number=1,
            excerpt="Mandatory minimum turnover is 3.0 Crores",
        ),
    ]

    valid, warnings = await validator.validate_citations(
        citations=citations,
        authorized_tender_id=tender.id,
        authorized_company_id=company.id,
    )

    assert len(valid) == 2
    assert len(warnings) == 0
    # Confirm filename was corrected to authoritative record
    assert valid[0].source_filename == "Audited_Financials_FY24.pdf"
    assert valid[1].source_filename == "NIT_Tender_Notice.pdf"


@pytest.mark.asyncio
async def test_citation_validator_rejects_unauthorized_and_invalid_pages(db_session: AsyncSession):
    """Test that unauthorized foreign company docs, missing docs, and out-of-bounds pages are rejected."""
    user_a = User(id=uuid.uuid4(), email=f"user_a_{uuid.uuid4().hex[:6]}@co.com", hashed_password="pw", full_name="A")
    user_b = User(id=uuid.uuid4(), email=f"user_b_{uuid.uuid4().hex[:6]}@co.com", hashed_password="pw", full_name="B")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    company_a = Company(
        id=uuid.uuid4(),
        owner_id=user_a.id,
        legal_name="Company A",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Tech",
        incorporation_date=date(2020, 1, 1),
    )
    company_b = Company(
        id=uuid.uuid4(),
        owner_id=user_b.id,
        legal_name="Company B (Foreign)",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Tech",
        incorporation_date=date(2020, 1, 1),
    )
    db_session.add_all([company_a, company_b])
    await db_session.flush()

    tender_a = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TND_{uuid.uuid4().hex[:6]}",
        title="Tender A",
        issuing_authority="CPWD",
        sector="Civil",
        submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
        created_by=user_a.id,
    )
    db_session.add(tender_a)
    await db_session.flush()

    # Document belonging to Company B
    doc_b = Document(
        id=uuid.uuid4(),
        company_id=company_b.id,
        entity_type="COMPANY",
        original_filename="Confidential_B.pdf",
        storage_path=f"companies/{company_b.id}/doc.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        total_pages=4,
        processing_status="INDEXED",
        sha256_hash="hash_b",
    )
    # Document belonging to Company A with 3 pages
    doc_a = Document(
        id=uuid.uuid4(),
        company_id=company_a.id,
        entity_type="COMPANY",
        original_filename="Profile_A.pdf",
        storage_path=f"companies/{company_a.id}/doc.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        total_pages=3,
        processing_status="INDEXED",
        sha256_hash="hash_a",
    )
    db_session.add_all([doc_b, doc_a])
    await db_session.flush()

    validator = CitationValidator(db_session)

    citations = [
        # 1. Non-existent document
        EvidenceCitation(
            evidence_id="ev_none",
            source_type="TENDER_DOCUMENT",
            document_id=uuid.uuid4(),
            source_filename="Ghost.pdf",
            page_number=1,
            excerpt="Ghost citation",
        ),
        # 2. Document belonging to unauthorized Company B
        EvidenceCitation(
            evidence_id="ev_b",
            source_type="COMPANY_DOCUMENT",
            document_id=doc_b.id,
            source_filename="Confidential_B.pdf",
            page_number=2,
            excerpt="Data from other company",
        ),
        # 3. Document belonging to Company A but page number out of bounds (> 3)
        EvidenceCitation(
            evidence_id="ev_oob",
            source_type="COMPANY_DOCUMENT",
            document_id=doc_a.id,
            source_filename="Profile_A.pdf",
            page_number=99,
            excerpt="Fabricated high page number",
        ),
        # 4. Valid citation
        EvidenceCitation(
            evidence_id="ev_valid",
            source_type="COMPANY_DOCUMENT",
            document_id=doc_a.id,
            source_filename="Profile_A.pdf",
            page_number=2,
            excerpt="Authentic snippet",
        ),
    ]

    valid, warnings = await validator.validate_citations(
        citations=citations,
        authorized_tender_id=tender_a.id,
        authorized_company_id=company_a.id,
    )

    assert len(valid) == 1
    assert valid[0].document_id == doc_a.id
    assert valid[0].page_number == 2
    assert len(warnings) == 3
    assert any("does not exist" in w for w in warnings)
    assert any("unauthorized scope" in w for w in warnings)
    assert any("Page number 99 is out of bounds" in w for w in warnings)
