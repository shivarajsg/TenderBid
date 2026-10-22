import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.tender import Tender
from app.models.user import User


@pytest.mark.asyncio
async def test_tender_qa_grounded_answer_with_valid_citations(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that Tender Q&A retrieves relevant chunks and returns cited answers."""
    user = User(
        id=uuid.uuid4(),
        email="msme_qa@example.com",
        hashed_password="hash",
        full_name="MSME QA User",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="TENDER/QA/001",
        title="Supply of Industrial Battery Systems",
        issuing_authority="BHEL",
        sector="Power",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
        processing_status="INDEXED",
    )
    db_session.add(tender)

    doc = Document(
        id=uuid.uuid4(),
        tender_id=tender.id,
        entity_type="TENDER",
        document_category="TENDER_NOTICE",
        original_filename="Battery_Specification.pdf",
        storage_path="tenders/Battery_Specification.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="hash123",
        total_pages=10,
        indexed_chunks=1,
        processing_status="INDEXED",
        verification_status="UNVERIFIED",
    )
    db_session.add(doc)

    chunk = DocumentChunkModel(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        tender_id=tender.id,
        source_filename="Battery_Specification.pdf",
        page_number=4,
        chunk_index=0,
        char_start=0,
        char_end=200,
        sha256_hash="hash123",
        chunk_text=(
            "Warranty and Replacement Policy: All supplied battery banks must come with a "
            "comprehensive 5-year onsite replacement warranty starting from the date of commissioning."
        ),
        extraction_method="pymupdf_direct",
    )
    db_session.add(chunk)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), role="MSME_USER")
    headers = {"Authorization": f"Bearer {token}"}

    # Ask question related to warranty
    qa_payload = {"question": "What is the warranty period required for the battery banks?"}
    response = await client.post(f"/api/v1/tenders/{tender.id}/qa", headers=headers, json=qa_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ANSWERED"
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["source_filename"] == "Battery_Specification.pdf"
    assert data["citations"][0]["page_number"] == 4
    assert "5-year onsite replacement warranty" in data["citations"][0]["supporting_excerpt"]


@pytest.mark.asyncio
async def test_tender_qa_insufficient_evidence_response(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that asking a question unrelated to the tender returns INSUFFICIENT_EVIDENCE."""
    user = User(
        id=uuid.uuid4(),
        email="msme_qa2@example.com",
        hashed_password="hash",
        full_name="MSME QA User 2",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="TENDER/QA/002",
        title="Supply of Railway Rails",
        issuing_authority="Indian Railways",
        sector="Transportation",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
        processing_status="INDEXED",
    )
    db_session.add(tender)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), role="MSME_USER")
    headers = {"Authorization": f"Bearer {token}"}

    # Ask about completely irrelevant topic where no chunk exists
    qa_payload = {"question": "What are the rules regarding catering and flight meals?"}
    response = await client.post(f"/api/v1/tenders/{tender.id}/qa", headers=headers, json=qa_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert "do not contain verifiable information" in data["answer"]
    assert len(data["citations"]) == 0


@pytest.mark.asyncio
async def test_tender_qa_unauthorized_and_invalid_tender(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that unauthenticated requests and queries on non-existent tenders fail appropriately."""
    user = User(
        id=uuid.uuid4(),
        email="msme_qa3@example.com",
        hashed_password="hash",
        full_name="MSME QA User 3",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    fake_id = uuid.uuid4()

    # 1. Unauthenticated request -> 401
    resp = await client.post(f"/api/v1/tenders/{fake_id}/qa", json={"question": "What is the budget?"})
    assert resp.status_code == 401

    # 2. Authenticated but non-existent tender -> 404
    token = create_access_token(subject=str(user.id), role="MSME_USER")
    resp = await client.post(
        f"/api/v1/tenders/{fake_id}/qa",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "What is the budget?"},
    )
    assert resp.status_code == 404



@pytest.mark.asyncio
async def test_tender_extracted_knowledge_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that GET /tenders/{tender_id}/extracted-knowledge returns extracted documents and chunks."""
    user = User(
        id=uuid.uuid4(),
        email="msme_knowledge@example.com",
        hashed_password="hash",
        full_name="MSME Knowledge User",
        role="MSME_USER",
        is_active=True,
    )
    db_session.add(user)

    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="TENDER/KNOWLEDGE/001",
        title="Supply of High-Voltage Cables",
        issuing_authority="PGCIL",
        sector="Power",
        submission_deadline=datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc),
        processing_status="INDEXED",
    )
    db_session.add(tender)

    doc = Document(
        id=uuid.uuid4(),
        tender_id=tender.id,
        entity_type="TENDER",
        document_category="TENDER_NOTICE",
        original_filename="Cable_Spec.pdf",
        storage_path="tenders/Cable_Spec.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash="cablesha123",
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
        source_filename="Cable_Spec.pdf",
        page_number=1,
        chunk_index=0,
        char_start=0,
        char_end=150,
        sha256_hash="cablesha123",
        chunk_text="Technical Specification: 66kV XLPE Insulated Aluminum Conductor Armored Cable conforming to IS 7098 Part 3.",
        extraction_method="pymupdf_direct",
    )
    db_session.add(chunk)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), role="MSME_USER")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/api/v1/tenders/{tender.id}/extracted-knowledge", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tender_reference"] == "TENDER/KNOWLEDGE/001"
    assert data["total_documents"] == 1
    assert data["total_chunks"] == 1
    assert data["documents"][0]["original_filename"] == "Cable_Spec.pdf"
    assert "66kV XLPE" in data["chunks"][0]["chunk_text"]
