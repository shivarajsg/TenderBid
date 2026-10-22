import uuid
import pytest
import chromadb

from app.services.chunking_service import DocumentChunk
from app.services.embedding_service import MockEmbeddingService
from app.services.vector_store_service import ChromaVectorStoreService


@pytest.fixture
def vector_store(tmp_path):
    """Fixture initializing an isolated ChromaVectorStoreService in a temp directory."""
    chroma_client = chromadb.PersistentClient(path=str(tmp_path / "chroma_test"))
    embedding_svc = MockEmbeddingService(dimension=64)
    
    svc = ChromaVectorStoreService(
        persist_directory=str(tmp_path / "chroma_test"),
        collection_name=f"test_coll_{uuid.uuid4().hex[:8]}",
        embedding_service=embedding_svc,
        client=chroma_client,
    )
    return svc


def test_index_and_query_chunks(vector_store):
    """Verify chunks can be indexed and queried with tender-level metadata filtering."""
    tender_a = str(uuid.uuid4())
    tender_b = str(uuid.uuid4())
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())

    chunk_a = DocumentChunk(
        chunk_id=f"{doc_a}_0",
        text="Solar panel installations require ISO 14001 environmental safety certification.",
        metadata={"tender_id": tender_a, "document_id": doc_a, "page_number": 1},
    )
    chunk_b = DocumentChunk(
        chunk_id=f"{doc_b}_0",
        text="High-voltage switchgear substations require CPRI type test certificates.",
        metadata={"tender_id": tender_b, "document_id": doc_b, "page_number": 1},
    )

    count = vector_store.index_chunks([chunk_a, chunk_b])
    assert count == 2
    assert vector_store.count() == 2

    # Query scoped to Tender A
    results_a = vector_store.query(
        query_text="What safety certification is required for solar installations?",
        tender_id=tender_a,
        n_results=5,
    )

    assert len(results_a) == 1
    assert results_a[0]["chunk_id"] == f"{doc_a}_0"
    assert results_a[0]["metadata"]["tender_id"] == tender_a
    # Ensure Tender B chunk was filtered out
    assert not any(r["metadata"]["tender_id"] == tender_b for r in results_a)


def test_idempotent_reindexing_purge(vector_store):
    """Verify that re-indexing a document purges old chunks without creating duplicate vector entries."""
    tender_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    # Initial indexing of 2 chunks
    initial_chunks = [
        DocumentChunk(f"{doc_id}_0", "Version 1 chunk text first part.", {"tender_id": tender_id, "document_id": doc_id}),
        DocumentChunk(f"{doc_id}_1", "Version 1 chunk text second part.", {"tender_id": tender_id, "document_id": doc_id}),
    ]
    vector_store.index_chunks(initial_chunks)
    assert vector_store.count() == 2

    # Purge before reindexing
    purged_count = vector_store.delete_document_chunks(doc_id)
    assert purged_count == 2
    assert vector_store.count() == 0

    # Re-index updated version with 1 chunk
    updated_chunks = [
        DocumentChunk(f"{doc_id}_0", "Version 2 replacement text completely rewritten.", {"tender_id": tender_id, "document_id": doc_id}),
    ]
    vector_store.index_chunks(updated_chunks)
    assert vector_store.count() == 1

    # Verify query returns only the replacement text
    results = vector_store.query("Version 2 replacement", tender_id=tender_id)
    assert len(results) == 1
    assert "Version 2" in results[0]["text"]
