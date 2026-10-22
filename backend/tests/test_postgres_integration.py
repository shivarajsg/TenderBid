import os
from datetime import date
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password, UserRole
from app.db.base import Base
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.tenders import TenderRepository
from app.db.repositories.users import UserRepository
from app.models.document import Document
from app.schemas.tender import TenderCreate
import app.models  # noqa: F401

settings = get_settings()

# Always target the isolated test database, never the development database
base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
PG_TEST_URL = os.getenv("TEST_POSTGRES_DATABASE_URL", f"{base_url}/tender_platform_test")


async def is_postgres_available() -> bool:
    """Check if PostgreSQL target is reachable via asyncpg."""
    try:
        test_eng = create_async_engine(PG_TEST_URL, pool_pre_ping=True)
        async with test_eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await test_eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
async def pg_engine():
    """Function-scoped async engine for isolated PostgreSQL integration tests."""
    if not await is_postgres_available():
        pytest.skip(f"PostgreSQL target {PG_TEST_URL.split('@')[-1]} is unreachable.")

    engine = create_async_engine(PG_TEST_URL, pool_pre_ping=True)

    # Initialize schema in isolated test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Teardown schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def pg_session_factory(pg_engine):
    """Session factory bound to the isolated PostgreSQL test engine."""
    return async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_connectivity(pg_engine):
    """Verify live PostgreSQL connectivity against the dedicated test database."""
    async with pg_engine.connect() as conn:
        result = await conn.execute(text("SELECT current_database(), current_user"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == "tender_platform_test"
        assert row[1] == "tender_app"


@pytest.mark.asyncio
async def test_postgres_crud_and_relationships(pg_session_factory):
    """Verify relational CRUD operations across Users, Companies, and Documents in PostgreSQL."""
    async with pg_session_factory() as session:
        user_repo = UserRepository(session)
        company_repo = CompanyRepository(session)
        doc_repo = DocumentRepository(session)

        # 1. Insert User
        user = await user_repo.create(
            email="pg_real_user@tenderbid.test",
            hashed_password=hash_password("RealSecurePassword123!"),
            full_name="PostgreSQL Verified User",
            role=UserRole.MSME_USER.value,
        )
        assert user.id is not None

        # 2. Insert Company referencing User
        company = await company_repo.create(
            owner_id=user.id,
            legal_name="PostgreSQL Real Steel Ltd",
            registration_number="UDYAM-PG-REAL-001",
            business_type="SMALL",
            sector="Heavy Engineering",
            incorporation_date=date(2016, 5, 20),
            annual_turnover=[{"fiscal_year": "2024-2025", "turnover_inr": 50000000.0}],
            certifications=[{"name": "ISO 9001:2015"}],
        )
        assert company.owner_id == user.id

        # 3. Insert Document referencing Company and User
        doc = await doc_repo.create(
            company_id=company.id,
            uploaded_by=user.id,
            document_category="FINANCIAL_AUDIT",
            original_filename="Audited_Balance_Sheet.pdf",
            storage_path=f"vault/{company.id}/sample.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048500,
            sha256_hash="c" * 64,
            valid_from=date(2024, 4, 1),
            valid_until=date(2025, 3, 31),
        )
        assert doc.company_id == company.id
        assert doc.uploaded_by == user.id

        await session.commit()

    # 4. Verify retrieval with eager relationships
    async with pg_session_factory() as session:
        user_repo = UserRepository(session)
        doc_repo = DocumentRepository(session)

        fetched_user = await user_repo.get_by_email("pg_real_user@tenderbid.test")
        assert fetched_user is not None
        assert fetched_user.company is not None
        assert fetched_user.company.legal_name == "PostgreSQL Real Steel Ltd"

        docs = await doc_repo.list_by_company(fetched_user.company.id)
        assert len(docs) == 1
        assert docs[0].original_filename == "Audited_Balance_Sheet.pdf"


@pytest.mark.asyncio
async def test_postgres_unique_constraint_enforcement(pg_session_factory):
    """Verify unique constraint on email is enforced at the PostgreSQL engine level."""
    async with pg_session_factory() as session:
        user_repo = UserRepository(session)
        await user_repo.create(
            email="unique_check@tenderbid.test",
            hashed_password=hash_password("Pass12345!"),
            full_name="User Unique 1",
        )
        await session.commit()

    # Attempting to insert duplicate email must raise IntegrityError
    with pytest.raises(IntegrityError):
        async with pg_session_factory() as session:
            user_repo = UserRepository(session)
            await user_repo.create(
                email="unique_check@tenderbid.test",
                hashed_password=hash_password("Pass12345!"),
                full_name="User Unique 2",
            )
            await session.commit()


@pytest.mark.asyncio
async def test_postgres_foreign_key_enforcement(pg_session_factory):
    """Verify foreign key constraint blocks orphaned company records in PostgreSQL."""
    import uuid
    orphaned_owner_id = uuid.uuid4()

    with pytest.raises(IntegrityError):
        async with pg_session_factory() as session:
            company_repo = CompanyRepository(session)
            await company_repo.create(
                owner_id=orphaned_owner_id,
                legal_name="Orphaned Co",
                registration_number="UDYAM-ORPHAN-001",
                business_type="MICRO",
                sector="IT",
                incorporation_date=date(2022, 1, 1),
            )
            await session.commit()


@pytest.mark.asyncio
async def test_postgres_transaction_rollback(pg_session_factory):
    """Verify transaction rollback discards partial inserts on error."""
    async with pg_session_factory() as session:
        user_repo = UserRepository(session)
        await user_repo.create(
            email="rollback_user@tenderbid.test",
            hashed_password=hash_password("Pass12345!"),
            full_name="Rollback User",
        )
        # Roll back explicitly
        await session.rollback()

    async with pg_session_factory() as session:
        user_repo = UserRepository(session)
        fetched = await user_repo.get_by_email("rollback_user@tenderbid.test")
        assert fetched is None


@pytest.mark.asyncio
async def test_postgres_tender_crud_and_cascade_delete(pg_session_factory):
    """Verify Tender creation with JSONB criteria and cascade deletion of documents in real PostgreSQL."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal

    tender_ref = f"PG_NIT_{uuid.uuid4().hex[:6]}"
    doc_id = uuid.uuid4()

    async with pg_session_factory() as session:
        tender_repo = TenderRepository(session)
        tender = await tender_repo.create(
            tender_in=TenderCreate(
                tender_reference=tender_ref,
                title="PostgreSQL Integration Switchgear Tender",
                issuing_authority="PGCIL",
                sector="Power Transmission",
                estimated_budget_inr=Decimal("120000000.00"),
                emd_amount_inr=Decimal("2400000.00"),
                msme_emd_exemption=True,
                submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
                structured_requirements={
                    "min_turnover_inr": 80000000.0,
                    "mandatory_certifications": ["ISO 9001:2015"],
                },
            )
        )
        tender_id = tender.id

        # Attach a document to this tender
        doc = Document(
            id=doc_id,
            tender_id=tender_id,
            entity_type="TENDER",
            original_filename="specs.pdf",
            storage_path=f"tenders/{tender_id}/{doc_id}.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            processing_status="PENDING",
            verification_status="UNVERIFIED",
        )
        session.add(doc)
        await session.commit()

    # Verify retrieval with JSONB structured requirements
    async with pg_session_factory() as session:
        tender_repo = TenderRepository(session)
        fetched_tender = await tender_repo.get_by_id(tender_id)
        assert fetched_tender is not None
        assert fetched_tender.tender_reference == tender_ref
        assert fetched_tender.structured_requirements["min_turnover_inr"] == 80000000.0
        assert len(fetched_tender.documents) == 1
        assert fetched_tender.documents[0].id == doc_id

        # Delete tender and verify cascade delete of the document in PostgreSQL
        await tender_repo.delete(fetched_tender)

    # Verify document was cascade deleted
    async with pg_session_factory() as session:
        from sqlalchemy import select
        doc_stmt = select(Document).where(Document.id == doc_id)
        doc_res = await session.execute(doc_stmt)
        assert doc_res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_postgres_compliance_reports_and_document_chunks(pg_session_factory):
    """Verify Phase 4 compliance models, JSONB fields, and cascade deletion in PostgreSQL."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.compliance_report import ComplianceReport
    from app.models.compliance_finding import ComplianceFinding
    from app.models.document_chunk import DocumentChunkModel
    from app.models.user import User
    from app.models.company import Company
    from app.models.tender import Tender
    from app.models.document import Document

    report_id = uuid.uuid4()
    finding_id = uuid.uuid4()
    tender_id = uuid.uuid4()
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    async with pg_session_factory() as session:
        # 1. Parent Records
        user = User(
            id=user_id,
            email=f"pg_comp_{uuid.uuid4().hex[:6]}@co.com",
            hashed_password="pw",
            full_name="Comp User",
            role=UserRole.MSME_USER.value,
        )
        session.add(user)
        await session.flush()

        company = Company(
            id=company_id,
            owner_id=user.id,
            legal_name="PG Compliance MSME",
            registration_number=f"REG_PG_{uuid.uuid4().hex[:6]}",
            business_type="SMALL",
            sector="Technology",
            incorporation_date=date(2020, 1, 1),
            annual_turnover=[{"fiscal_year": "2023-2024", "turnover_inr": 50000000.0}],
        )
        session.add(company)

        tender = Tender(
            id=tender_id,
            tender_reference=f"PG_TND_{uuid.uuid4().hex[:6]}",
            title="PG IT Tender",
            issuing_authority="PG Power",
            sector="Power",
            submission_deadline=datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc),
            structured_requirements={"min_turnover_inr": 40000000.0},
        )
        session.add(tender)
        await session.flush()

        doc = Document(
            id=doc_id,
            company_id=company_id,
            entity_type="COMPANY",
            document_category="FINANCIAL_AUDIT",
            original_filename="Audited.pdf",
            storage_path=f"companies/{company_id}/doc.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            processing_status="INDEXED",
            verification_status="UNVERIFIED",
        )
        session.add(doc)
        await session.flush()

        # 2. Document Chunk in PostgreSQL
        chunk = DocumentChunkModel(
            id="pg_chunk_1",
            document_id=doc_id,
            tender_id=None,
            company_id=company_id,
            source_filename="Audited.pdf",
            page_number=1,
            chunk_index=0,
            char_start=0,
            char_end=100,
            sha256_hash="hash_c1",
            chunk_text="Annual turnover verified at 50 Crores in PostgreSQL.",
            extraction_method="pymupdf_direct",
        )
        session.add(chunk)

        # 3. Compliance Report
        report = ComplianceReport(
            id=report_id,
            tender_id=tender_id,
            company_id=company_id,
            generated_by=user_id,
            overall_status="ELIGIBLE",
            overall_score=Decimal("100.00"),
            summary="MSME satisfies all requirements in PostgreSQL test.",
            rule_engine_version="1.0.0",
            tender_version_hash="thash123",
            company_version_hash="chash123",
            processing_metadata={"tested_in": "postgresql", "rrf_k": 60},
        )
        session.add(report)

        # 4. Compliance Finding
        finding = ComplianceFinding(
            id=finding_id,
            report_id=report_id,
            requirement_id="CRIT_TURNOVER_01",
            rule_type="TURNOVER",
            requirement_description="Minimum turnover INR 40,000,000",
            required_value={"min_turnover_inr": 40000000.0},
            observed_value={"observed_turnover_inr": 50000000.0},
            status="PASS",
            is_mandatory=True,
            reason="Observed turnover exceeds required threshold.",
            ai_explanation="Turnover verified.",
            evidence_citations=[
                {
                    "evidence_id": "ev_pg_1",
                    "source_type": "COMPANY_DOCUMENT",
                    "document_id": str(doc_id),
                    "source_filename": "Audited.pdf",
                    "page_number": 1,
                    "excerpt": "Annual turnover verified at 50 Crores.",
                }
            ],
        )
        session.add(finding)
        await session.commit()

    # Verify retrieval and JSONB round-trip in PostgreSQL
    async with pg_session_factory() as session:
        rep_stmt = select(ComplianceReport).where(ComplianceReport.id == report_id)
        rep_res = await session.execute(rep_stmt)
        fetched_rep = rep_res.scalar_one()
        assert fetched_rep.overall_status == "ELIGIBLE"
        assert fetched_rep.overall_score == Decimal("100.00")
        assert fetched_rep.processing_metadata["tested_in"] == "postgresql"

        find_stmt = select(ComplianceFinding).where(ComplianceFinding.id == finding_id)
        find_res = await session.execute(find_stmt)
        fetched_find = find_res.scalar_one()
        assert fetched_find.status == "PASS"
        assert fetched_find.required_value["min_turnover_inr"] == 40000000.0
        assert len(fetched_find.evidence_citations) == 1
        assert fetched_find.evidence_citations[0]["page_number"] == 1

        # Delete ComplianceReport and assert cascade deletion of ComplianceFinding in PostgreSQL
        await session.delete(fetched_rep)
        await session.commit()

    # Verify cascade delete
    async with pg_session_factory() as session:
        orphan_find = await session.execute(
            select(ComplianceFinding).where(ComplianceFinding.id == finding_id)
        )
        assert orphan_find.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_postgres_tender_unique_reference_enforcement(pg_session_factory):
    """Verify unique constraint on tender_reference is enforced by PostgreSQL."""
    import uuid
    from datetime import datetime, timezone

    dup_ref = f"DUP_NIT_{uuid.uuid4().hex[:6]}"

    async with pg_session_factory() as session:
        tender_repo = TenderRepository(session)
        await tender_repo.create(
            tender_in=TenderCreate(
                tender_reference=dup_ref,
                title="Tender 1",
                issuing_authority="Auth 1",
                sector="IT",
                submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
            )
        )

    # Attempting to insert duplicate reference must raise IntegrityError
    with pytest.raises(IntegrityError):
        async with pg_session_factory() as session:
            tender_repo = TenderRepository(session)
            await tender_repo.create(
                tender_in=TenderCreate(
                    tender_reference=dup_ref,
                    title="Tender 2",
                    issuing_authority="Auth 2",
                    sector="Civil",
                    submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
                )
            )


