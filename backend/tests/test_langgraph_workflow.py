import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
import chromadb
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.company import Company
from app.models.tender import Tender
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.compliance_report import ComplianceReport
from app.models.compliance_finding import ComplianceFinding
from app.services.embedding_service import MockEmbeddingService
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.semantic_retriever import SemanticRetriever
from app.services.vector_store_service import ChromaVectorStoreService
from app.services.workflows.compliance_graph import ComplianceWorkflowOrchestrator


@pytest.mark.asyncio
async def test_langgraph_workflow_eligible_company(db_session: AsyncSession):
    """Test full LangGraph execution for a fully eligible company, verifying database persistence."""
    # 1. Setup Chroma in-memory
    client = chromadb.EphemeralClient()
    mock_embed = MockEmbeddingService()
    vector_store = ChromaVectorStoreService(client=client, embedding_service=mock_embed)
    semantic = SemanticRetriever(vector_store=vector_store)
    retriever = HybridRetriever(session=db_session, semantic_retriever=semantic)

    # 2. Seed User and Company
    user = User(
        id=uuid.uuid4(),
        email=f"eligible_{uuid.uuid4().hex[:6]}@co.com",
        hashed_password="pw",
        full_name="Eligible User",
    )
    db_session.add(user)
    await db_session.flush()

    company = Company(
        id=uuid.uuid4(),
        owner_id=user.id,
        legal_name="Apex Solutions Pvt Ltd",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Information Technology",
        incorporation_date=date(2018, 5, 10),
        annual_turnover=[{"fiscal_year": "2023-2024", "turnover_inr": 65000000.0}],
        work_experience=[
            {
                "client_name": "State Electricity Board",
                "domain": "IT Infrastructure",
                "contract_value": 30000000,
                "duration_years": 4.5,
                "completed": True,
            }
        ],
        certifications=[
            {
                "name": "ISO 9001:2015",
                "valid_until": "2028-12-31",
                "issuing_authority": "TUV",
            }
        ],
    )
    db_session.add(company)
    await db_session.flush()

    # 3. Seed Tender with structured requirements
    structured_reqs = {
        "turnover": {
            "required_turnover_inr": "50000000.00",  # 5.0 Crores
            "currency": "INR",
            "is_mandatory": True,
        },
        "experience": {
            "min_years": 3,
            "relevant_domain": "IT Infrastructure",
            "is_mandatory": True,
        },
        "certifications": [
            {
                "name": "ISO 9001",
                "is_mandatory": True,
            }
        ],
        "mandatory_documents": [
            {
                "document_name": "Audited Balance Sheet",
                "document_type": "FINANCIAL_AUDIT",
                "is_mandatory": True,
            }
        ],
    }

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TND_WF_{uuid.uuid4().hex[:6]}",
        title="Smart Grid IT Modernization",
        issuing_authority="State Power Corp",
        sector="Power",
        submission_deadline=datetime(2027, 6, 30, 18, 0, tzinfo=timezone.utc),
        structured_requirements=structured_reqs,
        created_by=user.id,
    )
    db_session.add(tender)
    await db_session.flush()

    # 4. Seed Company Vault Document matching mandatory document requirement
    doc = Document(
        id=uuid.uuid4(),
        company_id=company.id,
        entity_type="COMPANY",
        document_category="FINANCIAL_AUDIT",
        original_filename="Audited_Balance_Sheet_2024.pdf",
        storage_path=f"companies/{company.id}/audited.pdf",
        mime_type="application/pdf",
        file_size_bytes=4096,
        total_pages=15,
        processing_status="INDEXED",
        sha256_hash="hash_audit",
    )
    db_session.add(doc)
    await db_session.flush()

    # Seed chunk for document
    chunk = DocumentChunkModel(
        id="chunk_wf_1",
        document_id=doc.id,
        company_id=company.id,
        source_filename="Audited_Balance_Sheet_2024.pdf",
        page_number=3,
        chunk_index=0,
        char_start=0,
        char_end=200,
        sha256_hash="hash_audit",
        chunk_text="Audited balance sheet showing net turnover INR 65000000.",
        extraction_method="pymupdf_direct",
    )
    db_session.add(chunk)
    await db_session.commit()

    # 5. Run LangGraph Workflow
    orchestrator = ComplianceWorkflowOrchestrator(
        session=db_session,
        hybrid_retriever=retriever,
    )

    result = await orchestrator.execute(
        tender_id=tender.id,
        company_id=company.id,
        user_id=user.id,
        include_ai_explanation=True,
    )

    # 6. Verify Workflow Output
    assert "report_id" in result
    report_id = result["report_id"]
    assert report_id is not None
    assert result["overall_status"] == "ELIGIBLE"
    assert result["overall_score"] == Decimal("100.00")
    assert len(result["reconciled_findings"]) >= 4

    # 7. Verify Database Persistence of Report and Findings
    rep_stmt = select(ComplianceReport).where(ComplianceReport.id == report_id)
    rep_res = await db_session.execute(rep_stmt)
    persisted_report = rep_res.scalar_one_or_none()

    assert persisted_report is not None
    assert persisted_report.overall_status == "ELIGIBLE"
    assert persisted_report.tender_id == tender.id
    assert persisted_report.company_id == company.id

    find_stmt = select(ComplianceFinding).where(ComplianceFinding.report_id == report_id)
    find_res = await db_session.execute(find_stmt)
    persisted_findings = find_res.scalars().all()

    assert len(persisted_findings) >= 4
    statuses = {f.rule_type: f.status for f in persisted_findings}
    assert statuses.get("TURNOVER") == "PASS"
    assert statuses.get("EXPERIENCE") == "PASS"
    assert statuses.get("CERTIFICATION") == "PASS"
    assert statuses.get("MANDATORY_DOCUMENT") == "PASS"
    assert statuses.get("DEADLINE") == "PASS"


@pytest.mark.asyncio
async def test_langgraph_workflow_deterministic_failure_cannot_be_overridden(db_session: AsyncSession):
    """Test that a company failing a mandatory requirement is NOT_ELIGIBLE and AI cannot overturn it."""
    client = chromadb.EphemeralClient()
    mock_embed = MockEmbeddingService()
    vector_store = ChromaVectorStoreService(client=client, embedding_service=mock_embed)
    semantic = SemanticRetriever(vector_store=vector_store)
    retriever = HybridRetriever(session=db_session, semantic_retriever=semantic)

    user = User(
        id=uuid.uuid4(),
        email=f"fail_{uuid.uuid4().hex[:6]}@co.com",
        hashed_password="pw",
        full_name="Failing User",
    )
    db_session.add(user)
    await db_session.flush()

    # Company with low turnover (2 Cr)
    company = Company(
        id=uuid.uuid4(),
        owner_id=user.id,
        legal_name="Small Tech Enterprise",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="IT",
        incorporation_date=date(2022, 1, 1),
        annual_turnover=[{"fiscal_year": "2023-2024", "turnover_inr": 20000000.0}],
    )
    db_session.add(company)
    await db_session.flush()

    # Tender requiring high turnover (10 Cr)
    structured_reqs = {
        "turnover": {
            "required_turnover_inr": "100000000.00",  # 10.0 Crores
            "currency": "INR",
            "is_mandatory": True,
        }
    }

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference=f"TND_FAIL_{uuid.uuid4().hex[:6]}",
        title="Major Infrastructure Contract",
        issuing_authority="National Highway Authority",
        sector="Civil",
        submission_deadline=datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc),
        structured_requirements=structured_reqs,
        created_by=user.id,
    )
    db_session.add(tender)
    await db_session.commit()

    orchestrator = ComplianceWorkflowOrchestrator(
        session=db_session,
        hybrid_retriever=retriever,
    )

    result = await orchestrator.execute(
        tender_id=tender.id,
        company_id=company.id,
        user_id=user.id,
        include_ai_explanation=True,
    )

    assert result["overall_status"] == "NOT_ELIGIBLE"
    assert result["overall_score"] < Decimal("100.00")

    # Verify findings in state
    turnover_finding = next(
        f for f in result["reconciled_findings"] if f.rule_type == "TURNOVER"
    )
    assert turnover_finding.status == "FAIL"
    assert turnover_finding.is_mandatory is True
