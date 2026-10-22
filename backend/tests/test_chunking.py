import uuid
import pytest

from app.services.chunking_service import RecursiveCharacterChunker
from app.services.extraction_service import PageExtractionResult


def test_recursive_splitter_chunk_size_and_overlap():
    """Verify recursive splitter breaks paragraphs without exceeding chunk size."""
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    text = (
        "The bidder must submit audited financial balance sheets for the preceding three fiscal years. "
        "The minimum annual turnover shall not be less than INR twenty five crores. "
        "Earnest money deposit (EMD) is exempt for registered MSME enterprises holding valid Udyam certificate."
    )

    page = PageExtractionResult(
        page_number=3,
        text=text,
        char_count=len(text),
        ocr_applied=False,
        extraction_method="pymupdf_direct",
        density_score=0.85,
    )

    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunks = chunker.chunk_page(
        page=page,
        tender_id=tender_id,
        document_id=doc_id,
        source_filename="tender_rfp.pdf",
    )

    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 100
        # Check metadata fields
        assert c.metadata["tender_id"] == str(tender_id)
        assert c.metadata["document_id"] == str(doc_id)
        assert c.metadata["source_filename"] == "tender_rfp.pdf"
        assert c.metadata["page_number"] == 3
        assert c.metadata["extraction_method"] == "pymupdf_direct"
        assert len(c.metadata["sha256_hash"]) == 64
        assert c.chunk_id.startswith(str(doc_id))


def test_multi_page_sequential_chunk_indexing():
    """Verify chunk indices increment monotonically across distinct document pages."""
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)

    p1 = PageExtractionResult(1, "First page text content describing tender overview.", 50, False, "pymupdf_direct", 0.9)
    p2 = PageExtractionResult(2, "Second page technical specs requirement details.", 48, False, "pymupdf_direct", 0.9)

    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    all_chunks = chunker.chunk_document_pages(
        pages=[p1, p2],
        tender_id=tender_id,
        document_id=doc_id,
        source_filename="notice.pdf",
    )

    assert len(all_chunks) >= 2
    indices = [c.metadata["chunk_index"] for c in all_chunks]
    assert indices == list(range(len(all_chunks)))

    # Page numbers must match original pages
    assert all_chunks[0].metadata["page_number"] == 1
    assert all_chunks[-1].metadata["page_number"] == 2
