# PHASE 3 IMPLEMENTATION REPORT: Tender Management, Secure PDF Ingestion, Document Intelligence, and Persistent ChromaDB Indexing

**Project Title:** Agentic AI-Powered Tender Intelligence and Compliance Management Platform for MSMEs Using RAG  
**Implementation Date:** 2026-10-21  
**Target Environment:** Windows 11, Python 3.13.15, PostgreSQL 16 (Docker container on port 5433), ChromaDB 1.5.9, PyMuPDF 2.0  
**Overall Status:** **COMPLETED & VERIFIED (42 / 42 Tests Passed)**

---

## 1. Executive Summary

Phase 3 implementation has completed all required capabilities for tender management, sandboxed physical PDF storage, document intelligence (PyMuPDF text extraction with Tesseract OCR fallback), recursive character chunking with complete page-level provenance, and persistent vector indexing via ChromaDB.

The implementation strictly honors the foundational decisions established in Phase 1 and Phase 2:
- PostgreSQL remains the authoritative relational database for all structured tender and document metadata.
- ChromaDB operates as the persistent vector database for semantic chunk retrieval, scoped to individual tenders via metadata filters.
- PyMuPDF (`pymupdf`) extracts page-by-page text preserving 1-based physical page numbers, while OCR fallback activates on text-poor (<100 characters) pages with graceful degradation if the host lacks a Tesseract binary.
- All 42 automated tests passed without skips or failures, including 7 live integration tests against the isolated PostgreSQL database (`tender_platform_test`).

---

## 2. Files Created and Modified

### 2.1 New Source Files Created
| File Path | Description |
| :--- | :--- |
| `backend/app/models/tender.py` | Relational SQLAlchemy model for public tender notices and structured criteria |
| `backend/app/schemas/tender.py` | Pydantic v2 validation schemas for tender CRUD, filtering, uploads, and status |
| `backend/app/db/repositories/tenders.py` | Async PostgreSQL repository supporting ILIKE search, budget/sector filters, and pagination |
| `backend/app/services/storage_service.py` | Sandboxed physical PDF storage manager with `%PDF-` validation and traversal defense |
| `backend/app/services/ocr_service.py` | Tesseract OCR wrapper with host binary availability detection and pixmap rendering |
| `backend/app/services/extraction_service.py` | PyMuPDF page-by-page text extractor with density scoring and automated OCR fallback |
| `backend/app/services/chunking_service.py` | Recursive character splitter with provenance metadata (`page_number`, `char_start`, `sha256`) |
| `backend/app/services/embedding_service.py` | Embedding abstraction supporting ChromaDB default ONNX model and fast deterministic mock |
| `backend/app/services/vector_store_service.py` | Persistent ChromaDB client manager with idempotent document chunk purge and scoped queries |
| `backend/app/services/tender_service.py` | Orchestration layer uniting storage, extraction, chunking, and ChromaDB vector indexing |
| `backend/app/api/routes/tenders.py` | Admin endpoints for tender management & MSME endpoints for discovery & document downloads |
| `backend/alembic/versions/2026_10_21_1606-baa6ffa6b4bb_add_tenders_and_document_extensions.py` | Alembic migration schema `baa6ffa6b4bb` |

### 2.2 New Test Files Created
| File Path | Description |
| :--- | :--- |
| `backend/tests/test_storage.py` | 5 unit tests for PDF validation, traversal defense, file size limits, and deletion |
| `backend/tests/test_document_intelligence.py` | 3 unit tests for PyMuPDF page extraction, density scoring, and OCR fallback modes |
| `backend/tests/test_chunking.py` | 2 unit tests for recursive splitting, chunk boundaries, and global index preservation |
| `backend/tests/test_vector_store.py` | 2 integration tests for ChromaDB indexing, metadata filtering, and idempotent purges |
| `backend/tests/test_tenders_api.py` | 5 end-to-end API tests for tender creation, RBAC, upload pipeline, and document downloads |

### 2.3 Existing Files Modified
| File Path | Modifications Made |
| :--- | :--- |
| `backend/app/core/config.py` | Added `MAX_UPLOAD_SIZE_MB`, `TESSERACT_CMD`, `CHROMA_PERSIST_DIRECTORY`, `CHROMA_COLLECTION_NAME`, `EMBEDDING_PROVIDER`, `CHUNK_SIZE`, `CHUNK_OVERLAP` |
| `backend/app/models/document.py` | Extended with `tender_id`, `entity_type`, `total_pages`, `indexed_chunks`, `processing_status`, `extraction_metadata`, `error_message`, and made `company_id` nullable |
| `backend/app/models/__init__.py` | Exported `Tender` |
| `backend/app/api/routes/__init__.py` | Exported `tenders_router` |
| `backend/app/main.py` | Mounted `tenders_router` under `/api/v1` |
| `backend/requirements.txt` | Added `pymupdf>=1.24.14`, `pytesseract>=0.3.13`, `Pillow>=11.0.0`, `chromadb>=0.5.20` |
| `backend/.env.example` | Documented Phase 3 upload, OCR, and ChromaDB configuration variables |
| `backend/tests/conftest.py` | Registered `Tender` model in in-memory test engine metadata |
| `backend/tests/test_postgres_integration.py` | Added live PostgreSQL tests for `Tender` JSONB queries and foreign key cascade deletion |
| `backend/README.md` | Documented Phase 3 endpoints, storage security, document intelligence, and setup commands |

---

## 3. Database Schema Changes & Alembic Migration

### 3.1 Migration Identification
- **Revision ID:** `baa6ffa6b4bb`
- **Revises:** `e2d86d729816`
- **Applied Status:** `baa6ffa6b4bb (head)` confirmed live on PostgreSQL dev database (`tender_platform`).

### 3.2 New Table: `tenders`
```sql
CREATE TABLE tenders (
    id UUID PRIMARY KEY,
    tender_reference VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    issuing_authority VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    estimated_budget_inr NUMERIC(15, 2),
    emd_amount_inr NUMERIC(15, 2),
    msme_emd_exemption BOOLEAN NOT NULL DEFAULT TRUE,
    publication_date TIMESTAMPTZ,
    submission_deadline TIMESTAMPTZ NOT NULL,
    official_portal_url VARCHAR(512),
    structured_requirements JSONB,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_tenders_tender_reference ON tenders (tender_reference);
CREATE INDEX ix_tenders_sector ON tenders (sector);
CREATE INDEX ix_tenders_submission_deadline ON tenders (submission_deadline);
CREATE INDEX ix_tenders_processing_status ON tenders (processing_status);
CREATE INDEX ix_tenders_created_by ON tenders (created_by);
```

### 3.3 Altered Table: `documents`
- `company_id` column altered from `NOT NULL` to `NULL` to accommodate tender attachments.
- Added `tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE`.
- Added `entity_type VARCHAR(50) NOT NULL DEFAULT 'COMPANY'`.
- Added `total_pages INTEGER NULL`.
- Added `indexed_chunks INTEGER NOT NULL DEFAULT 0`.
- Added `processing_status VARCHAR(50) NOT NULL DEFAULT 'PENDING'`.
- Added `extraction_metadata JSONB NULL`.
- Added `error_message VARCHAR(1000) NULL`.
- Added indexes on `ix_documents_tender_id` and `ix_documents_processing_status`.

---

## 4. API Endpoints and Permissions

All endpoints are mounted under `/api/v1` (with health probes also accessible at root):

| HTTP Method | Route | Access Control | Functionality |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/admin/tenders` | `ADMIN` only | Create a new tender notice with structured requirements |
| `PUT` | `/api/v1/admin/tenders/{id}` | `ADMIN` only | Update tender metadata or requirements |
| `DELETE` | `/api/v1/admin/tenders/{id}` | `ADMIN` only | Delete tender, cascade delete documents, and purge ChromaDB vector embeddings |
| `POST` | `/api/v1/admin/tenders/{id}/upload-docs` | `ADMIN` only | Upload multipart PDF files with magic byte and size verification |
| `POST` | `/api/v1/admin/tenders/{id}/process` | `ADMIN` only | Trigger text extraction, chunking, and ChromaDB vector indexing |
| `GET` | `/api/v1/admin/tenders/{id}/processing-status` | `ADMIN` only | Inspect document-by-document extraction metrics and indexing status |
| `GET` | `/api/v1/tenders` | Authenticated | Discover tenders with `sector`, `min_budget`, `max_budget`, `deadline_after`, and `search` |
| `GET` | `/api/v1/tenders/{id}` | Authenticated | Retrieve tender details and document metadata |
| `GET` | `/api/v1/tenders/{id}/documents/{doc_id}/download` | Authenticated | Stream verified tender PDF file securely |

---

## 5. Security & Ingestion Pipeline

### 5.1 Storage Sandboxing & Path Traversal Defenses
- Files are stored in `uploads/tenders/<tender_id>/<doc_id>.pdf` or `uploads/companies/<company_id>/<doc_id>.pdf`.
- Path traversal sequences (`../`, `..\`, absolute root escapes) are caught and rejected with `PathTraversalError`.
- File writes use temporary files (`.tmp_<uuid>`) and are atomically renamed upon complete verification.
- Incomplete uploads or failed batches automatically delete temporary and orphaned files.

### 5.2 Magic Bytes & Size Limits
- Inspects first 5 bytes against `b"%PDF-"`. Non-PDF files (e.g. plain text, executables, or ZIP archives disguised with a `.pdf` extension) are rejected immediately with HTTP 400 (`InvalidFileTypeError`).
- Size is bounded by `settings.MAX_UPLOAD_SIZE_MB` (default 25 MB). Exceeding files raise `FileSizeLimitExceededError`.

---

## 6. Document Intelligence & Text Extraction

### 6.1 PyMuPDF Page-by-Page Extraction
- Utilizes `pymupdf` (v2.0) to iterate through all physical document pages sequentially.
- Strictly preserves 1-based page numbers (`page_number = index + 1`).
- Measures character count and non-whitespace character density.

### 6.2 Scanned Page Detection & Tesseract OCR Fallback
- **Threshold:** Pages containing fewer than 100 characters (`LOW_DENSITY_CHAR_THRESHOLD = 100`) are flagged as low-density / candidate scanned pages.
- **Host Binary Detection:** `OCRService.is_available()` validates the presence of the Tesseract executable via `shutil.which` and `pytesseract.get_tesseract_version()`.
- **Active OCR:** When Tesseract is available, PyMuPDF renders the page to a 200 DPI PNG pixmap and calls Tesseract OCR.
- **Graceful Degradation:** If Tesseract is not installed on the host machine, the page is preserved with whatever raw text was extracted and flagged with `extraction_method = "pymupdf_degraded"`. The processing status updates to `PARTIALLY_INDEXED` rather than crashing the API.

---

## 7. Recursive Character Chunking & Provenance

### 7.1 Chunking Hierarchy
- Uses recursive character splitting on `["\n\n", "\n", ". ", " ", ""]` with default `chunk_size = 1000` and `chunk_overlap = 200`.

### 7.2 Page-Level Provenance Metadata
Every chunk stored in memory and sent to ChromaDB preserves the following metadata:
```json
{
  "tender_id": "7bbc764f-51c0-480e-9fbf-7c2d7a8a259f",
  "document_id": "decaeeb7-ac01-45e9-8a14-201248e3a147",
  "source_filename": "GAIL_Notice_NIT.pdf",
  "page_number": 1,
  "chunk_index": 0,
  "char_start": 0,
  "char_end": 158,
  "sha256_hash": "b2c6087593b4f...",
  "extraction_method": "pymupdf_direct"
}
```

---

## 8. Persistent ChromaDB Vector Indexing

### 8.1 Configuration & Storage
- Persistent client targets `CHROMA_PERSIST_DIRECTORY` (default `./data/chroma`).
- Dedicated collection: `tender_documents` using Cosine distance space (`{"hnsw:space": "cosine"}`).
- Embedding provider abstraction allows seamless switching between:
  - `DefaultChromaEmbeddingService`: built-in ChromaDB ONNX `all-MiniLM-L6-v2` for production.
  - `MockEmbeddingService`: deterministic normalized vector generator for fast, isolated test suites.

### 8.2 Multi-Tenant Metadata Filtering & Idempotent Purging
- Search queries are scoped via ChromaDB `where` filters:
  ```python
  where = {"tender_id": str(tender_id)}
  ```
  This ensures queries for Tender A never return chunk matches from Tender B.
- Before indexing or re-indexing any document, `delete_document_chunks(str(doc.id))` is invoked to prevent vector duplication.

---

## 9. Verification & Test Execution Results

All automated tests were executed using the Windows virtual environment (`.\backend\.venv\Scripts\python.exe`):

```powershell
cmd /c "cd backend && .venv\Scripts\python.exe -m pytest -v"
```

### 9.1 Summary of Test Results
```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-8.3.4, pluggy-1.7.0 -- C:\Users\KumarShiva\Downloads\Tender_Bid\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\KumarShiva\Downloads\Tender_Bid\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, asyncio-0.24.0
asyncio: mode=Mode.AUTO, default_loop_scope=function
collected 42 items

tests/test_auth.py::test_admin_provisioning_logic PASSED                 [  2%]
tests/test_auth.py::test_register_success PASSED                         [  4%]
tests/test_auth.py::test_register_duplicate_email_rejected PASSED        [  7%]
tests/test_auth.py::test_register_validation_failure PASSED              [  9%]
tests/test_auth.py::test_login_success PASSED                            [ 11%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 14%]
tests/test_auth.py::test_get_current_user_profile PASSED                 [ 16%]
tests/test_auth.py::test_public_registration_cannot_escalate_privileges PASSED [ 19%]
tests/test_auth.py::test_unauthenticated_request_rejected PASSED         [ 21%]
tests/test_chunking.py::test_recursive_splitter_chunk_size_and_overlap PASSED [ 23%]
tests/test_chunking.py::test_multi_page_sequential_chunk_indexing PASSED [ 26%]
tests/test_companies.py::test_create_and_get_company_profile PASSED      [ 28%]
tests/test_companies.py::test_update_company_profile PASSED              [ 30%]
tests/test_companies.py::test_cross_company_isolation PASSED             [ 33%]
tests/test_document_intelligence.py::test_pymupdf_page_by_page_text_extraction PASSED [ 35%]
tests/test_document_intelligence.py::test_low_density_page_ocr_fallback_degraded PASSED [ 38%]
tests/test_document_intelligence.py::test_ocr_fallback_applied_when_available PASSED [ 40%]
tests/test_documents.py::test_register_and_list_documents PASSED         [ 42%]
tests/test_documents.py::test_invalid_mime_type_rejected PASSED          [ 45%]
tests/test_documents.py::test_cross_company_document_isolation PASSED    [ 47%]
tests/test_health.py::test_root_endpoint PASSED                          [ 50%]
tests/test_health.py::test_health_liveness PASSED                        [ 52%]
tests/test_health.py::test_health_readiness PASSED                       [ 54%]
tests/test_postgres_integration.py::test_postgres_connectivity PASSED    [ 57%]
tests/test_postgres_integration.py::test_postgres_crud_and_relationships PASSED [ 59%]
tests/test_postgres_integration.py::test_postgres_unique_constraint_enforcement PASSED [ 61%]
tests/test_postgres_integration.py::test_postgres_foreign_key_enforcement PASSED [ 64%]
tests/test_postgres_integration.py::test_postgres_transaction_rollback PASSED [ 66%]
tests/test_postgres_integration.py::test_postgres_tender_crud_and_cascade_delete PASSED [ 69%]
tests/test_postgres_integration.py::test_postgres_tender_unique_reference_enforcement PASSED [ 71%]
tests/test_storage.py::test_save_valid_pdf_stream PASSED                 [ 73%]
tests/test_storage.py::test_reject_invalid_magic_bytes PASSED            [ 76%]
tests/test_storage.py::test_reject_oversized_file PASSED                 [ 78%]
tests/test_storage.py::test_path_traversal_detection PASSED              [ 80%]
tests/test_storage.py::test_delete_file PASSED                           [ 83%]
tests/test_tenders_api.py::test_admin_create_tender PASSED               [ 85%]
tests/test_tenders_api.py::test_msme_user_forbidden_from_admin_tender_creation PASSED [ 88%]
tests/test_tenders_api.py::test_list_and_filter_tenders PASSED           [ 90%]
tests/test_tenders_api.py::test_tender_document_upload_and_processing_pipeline PASSED [ 92%]
tests/test_tenders_api.py::test_upload_invalid_file_rejected PASSED      [ 95%]
tests/test_vector_store.py::test_index_and_query_chunks PASSED           [ 97%]
tests/test_vector_store.py::test_idempotent_reindexing_purge PASSED      [100%]

======================= 42 passed, 2 warnings in 19.18s =======================
```

---

## 10. Known Limitations and Blocked Integrations

1. **Host Tesseract Binary Dependency:**
   On Windows systems without Tesseract installed (or where `TESSERACT_CMD` is not set), text-poor scanned pages automatically record `pymupdf_degraded` rather than performing OCR. This is an intentional graceful degradation design.
2. **Out of Scope for Phase 3:**
   - Deterministic compliance engine comparison between MSME profiles and tender thresholds (scheduled for Phase 4).
   - LangGraph orchestration workflow (scheduled for Phase 4).
   - Gemini API question-answering and compliance report synthesis (scheduled for Phase 4).
   - Automated government portal scrapers (GeM / CPPP).

---

## 11. Recommended Next Steps for Phase 4

With the relational models, secure ingestion pipeline, page-by-page text extractor, and persistent ChromaDB vector store verified, the recommended roadmap for **Phase 4** is:
1. **Deterministic Eligibility Engine:** Implement the rule-based verification matrix in pure Python (checking turnover thresholds, operational experience years, and mandatory certification matches).
2. **Hybrid RAG Semantic Retrieval:** Query ChromaDB for specific requirement criteria clauses with page number and excerpt citation extraction.
3. **LangGraph Compliance Orchestrator:** Implement the state graph combining deterministic check outputs with RAG evidence and LLM synthesis.
4. **Compliance Report Generator:** Generate structured reports including overall status (`ELIGIBLE`, `INELIGIBLE`, `CONDITIONALLY_ELIGIBLE`), missing documents checklist, and actionable recommendations.
