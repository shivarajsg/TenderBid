import uuid
from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import chromadb

from app.models.user import User
from app.models.company import Company
from app.models.tender import Tender
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.schemas.evidence import EvidenceCitation
from app.services.chunking_service import DocumentChunk
from app.services.embedding_service import MockEmbeddingService
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.semantic_retriever import SemanticRetriever
from app.services.vector_store_service import ChromaVectorStoreService


@pytest.mark.asyncio
async def test_lexical_retrieval_and_company_isolation(db_session: AsyncSession):
    """Verify lexical retriever queries PostgreSQL chunks and strictly isolates company data."""
    retriever = LexicalRetriever(db_session)

    # 1. Create Users
    user_a = User(id=uuid.uuid4(), email=f"user_a_{uuid.uuid4().hex[:6]}@co.com", hashed_password="pw", full_name="User A")
    user_b = User(id=uuid.uuid4(), email=f"user_b_{uuid.uuid4().hex[:6]}@co.com", hashed_password="pw", full_name="User B")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    # 2. Create Companies
    company_a = Company(
        id=uuid.uuid4(),
        owner_id=user_a.id,
        legal_name="Precision Tools Pvt Ltd",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Manufacturing",
        incorporation_date=date(2020, 1, 1),
    )
    company_b = Company(
        id=uuid.uuid4(),
        owner_id=user_b.id,
        legal_name="Apex Engineering Corp",
        registration_number=f"REG_{uuid.uuid4().hex[:6]}",
        sector="Engineering",
        incorporation_date=date(2020, 1, 1),
    )
    db_session.add_all([company_a, company_b])
    await db_session.flush()

    # 3. Create Documents
    doc_a = Document(
        id=uuid.uuid4(),
        company_id=company_a.id,
        entity_type="COMPANY",
        original_filename="Audit_FY24.pdf",
        storage_path=f"companies/{company_a.id}/doc_a.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_a",
        processing_status="INDEXED",
    )
    doc_b = Document(
        id=uuid.uuid4(),
        company_id=company_b.id,
        entity_type="COMPANY",
        original_filename="Secret_Financials.pdf",
        storage_path=f"companies/{company_b.id}/doc_b.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash_b",
        processing_status="INDEXED",
    )
    db_session.add_all([doc_a, doc_b])
    await db_session.flush()

    # 4. Seed Chunks
    chunk_a = DocumentChunkModel(
        id="chunk_co_a",
        document_id=doc_a.id,
        tender_id=None,
        company_id=company_a.id,
        source_filename="Audit_FY24.pdf",
        page_number=2,
        chunk_index=0,
        char_start=0,
        char_end=150,
        sha256_hash="hash_a",
        chunk_text="Annual turnover of Precision Tools Pvt Ltd reached INR 65 Crores.",
        extraction_method="pymupdf_direct",
    )
    chunk_b = DocumentChunkModel(
        id="chunk_co_b",
        document_id=doc_b.id,
        tender_id=None,
        company_id=company_b.id,
        source_filename="Secret_Financials.pdf",
        page_number=1,
        chunk_index=0,
        char_start=0,
        char_end=150,
        sha256_hash="hash_b",
        chunk_text="Turnover for Apex Engineering Corp was INR 120 Crores confidential.",
        extraction_method="pymupdf_direct",
    )
    db_session.add_all([chunk_a, chunk_b])
    await db_session.commit()

    # Company A searches turnover
    results_a = await retriever.search(query="turnover", company_id=company_a.id)
    assert len(results_a) == 1
    assert results_a[0].document_id == doc_a.id
    assert "Precision Tools" in results_a[0].excerpt
    # Must NOT contain Company B's confidential financials
    assert not any(r.document_id == doc_b.id for r in results_a)

    # Calling search without tender_id or company_id must be blocked
    with pytest.raises(ValueError):
        await retriever.search(query="turnover")


@pytest.mark.asyncio
async def test_hybrid_rrf_merging_and_deduplication(db_session: AsyncSession, tmp_path):
    """Verify hybrid retriever merges lexical and semantic candidates using Reciprocal Rank Fusion."""
    from datetime import datetime, timezone
    
    # Create parent tender & document
    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    tender = Tender(
        id=tender_id,
        tender_reference=f"HYBRID_NIT_{uuid.uuid4().hex[:6]}",
        title="Hybrid Tender",
        issuing_authority="BHEL",
        sector="Power",
        submission_deadline=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
    )
    db_session.add(tender)
    await db_session.flush()

    doc = Document(
        id=doc_id,
        tender_id=tender_id,
        entity_type="TENDER",
        original_filename="Tender_NIT.pdf",
        storage_path=f"tenders/{tender_id}/nit.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash="sha_nit",
        processing_status="INDEXED",
    )
    db_session.add(doc)
    await db_session.flush()

    chunk_id = f"{doc_id}_0"
    chunk_model = DocumentChunkModel(
        id=chunk_id,
        document_id=doc_id,
        tender_id=tender_id,
        company_id=None,
        source_filename="Tender_NIT.pdf",
        page_number=1,
        chunk_index=0,
        char_start=0,
        char_end=200,
        sha256_hash="sha_nit",
        chunk_text="Minimum average annual turnover required is INR 50 Crores over last 3 audited years.",
        extraction_method="pymupdf_direct",
    )
    db_session.add(chunk_model)
    await db_session.commit()

    # 2. Semantic setup in ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(tmp_path / "chroma_hybrid"))
    emb_svc = MockEmbeddingService(dimension=64)
    vstore = ChromaVectorStoreService(
        persist_directory=str(tmp_path / "chroma_hybrid"),
        collection_name=f"test_coll_{uuid.uuid4().hex[:8]}",
        embedding_service=emb_svc,
        client=chroma_client,
    )
    vstore.index_chunks([
        DocumentChunk(
            chunk_id=chunk_id,
            text="Minimum average annual turnover required is INR 50 Crores over last 3 audited years.",
            metadata={
                "tender_id": str(tender_id),
                "document_id": str(doc_id),
                "source_filename": "Tender_NIT.pdf",
                "page_number": 1,
            },
        )
    ])

    lexical_retriever = LexicalRetriever(db_session)
    semantic_retriever = SemanticRetriever(vstore)

    hybrid = HybridRetriever(
        session=db_session,
        lexical_retriever=lexical_retriever,
        semantic_retriever=semantic_retriever,
    )

    results = await hybrid.search(query="turnover requirement 50 Crores", tender_id=tender_id, limit=5)

    assert len(results) == 1
    assert results[0].chunk_id == chunk_id
    assert results[0].retrieval_method == "hybrid"
    assert results[0].page_number == 1
    assert results[0].source_filename == "Tender_NIT.pdf"
    assert results[0].relevance_score is not None
    assert results[0].relevance_score > 0
