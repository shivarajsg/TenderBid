# Tender Intelligence & Compliance Platform - Backend Foundation

Backend service for the **Agentic AI-Powered Tender Intelligence and Compliance Management Platform for MSMEs Using RAG**.

Built with **Python 3.13**, **FastAPI**, **SQLAlchemy 2.x (Async)**, **PostgreSQL** with `asyncpg`, **Alembic**, **PyJWT**, and **Argon2** password hashing.

---

## 1. Prerequisites (Windows Development)

- **Python 3.13** installed (verified with `py -3.13 --version`)
- **Docker Desktop** (for running the local PostgreSQL container)
- **PowerShell**

---

## 2. Windows Setup & Execution Guide

Run all commands from the repository root or `backend` folder as indicated.

### Step 2.1: Create Isolated Virtual Environment

From the `backend` directory:
```powershell
Set-Location backend
py -3.13 -m venv .venv
```

### Step 2.2: Install Pinned Dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 2.3: Start Local PostgreSQL via Docker Compose

From the project root:
```powershell
docker compose up -d postgres
docker compose ps
```
The database maps to `127.0.0.1:5433` (container port 5432) to prevent conflicts with local PostgreSQL instances.

### Step 2.4: Apply Database Migrations (Alembic)

From the `backend` directory:
```powershell
# Apply all versioned migrations against the target database
.\.venv\Scripts\python.exe -m alembic upgrade head

# Or generate offline SQL without a live database
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

### Step 2.5: Provision Administrator Account (CLI)

Public registration creates MSME accounts exclusively. To provision an administrator:
```powershell
.\.venv\Scripts\python.exe -m app.cli create-admin --email admin@tenderbid.internal --full-name "System Administrator"
```
You will be prompted securely for a password (minimum 8 characters).

### Step 2.6: Run Automated Tests

From the `backend` directory:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Step 2.7: Launch the Development Server

From the `backend` directory:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Liveness Probe: `http://127.0.0.1:8000/api/v1/health`
- Database Readiness: `http://127.0.0.1:8000/api/v1/health/ready`

---

## 3. Implemented Endpoints

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Public | Service metadata & status |
| `GET` | `/api/v1/health` | Public | Process liveness probe |
| `GET` | `/api/v1/health/ready` | Public | PostgreSQL readiness probe |
| `POST` | `/api/v1/auth/register` | Public | Register new MSME user (Argon2 hash) |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & issue signed JWT |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve authenticated user profile |
| `GET` | `/api/v1/company/profile` | Authenticated MSME | Retrieve company profile & financial metrics |
| `POST` | `/api/v1/company/profile` | Authenticated MSME | Initialize company profile |
| `PUT` | `/api/v1/company/profile` | Authenticated MSME | Update company profile fields |
| `POST` | `/api/v1/company/vault/documents` | Authenticated MSME | Register document metadata in vault |
| `GET` | `/api/v1/company/vault/documents` | Authenticated MSME | List company documents (optional category filter) |
| `GET` | `/api/v1/company/vault/documents/{id}` | Authenticated MSME | Retrieve single document metadata |
| `GET` | `/api/v1/tenders` | Authenticated | List tenders with sector, budget, and search filters |
| `GET` | `/api/v1/tenders/{id}` | Authenticated | Get tender details and attached notices |
| `GET` | `/api/v1/tenders/{id}/documents/{doc_id}/download` | Authenticated | Securely stream tender PDF attachment |
| `POST` | `/api/v1/admin/tenders` | Admin Only | Create tender with structured criteria |
| `PUT` | `/api/v1/admin/tenders/{id}` | Admin Only | Update tender metadata & thresholds |
| `DELETE` | `/api/v1/admin/tenders/{id}` | Admin Only | Delete tender, cascade docs & purge ChromaDB vectors |
| `POST` | `/api/v1/admin/tenders/{id}/upload-docs` | Admin Only | Upload PDF notices with magic bytes validation |
| `POST` | `/api/v1/admin/tenders/{id}/process` | Admin Only | Trigger PyMuPDF extraction, OCR fallback & Chroma indexing |
| `GET` | `/api/v1/admin/tenders/{id}/processing-status` | Admin Only | Inspect document intelligence & indexing state |

---

## 4. Phase 3 Document Intelligence & Vector Storage Architecture

### 4.1 Secure PDF File Ingestion
- Uploaded files are strictly checked for `%PDF-` magic byte headers (bytes `b"%PDF-"`).
- File sizes are enforced against `MAX_UPLOAD_SIZE_MB` (default 25 MB).
- Paths are resolved within a sandboxed directory (`uploads/tenders/<tender_id>/<doc_id>.pdf`) with strict path-traversal prevention.

### 4.2 Text Extraction & OCR Fallback
- **PyMuPDF (`pymupdf`)** extracts text page by page, preserving 1-based physical page numbering.
- **Scanned page detection**: Pages with character counts < 100 are flagged as low-density.
- **Tesseract OCR Fallback**: If available on host (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`), the page is rendered to high-resolution PNG bytes and OCR is executed. If Tesseract is not installed, the service gracefully degrades to `pymupdf_degraded` without crashing.

### 4.3 Recursive Character Chunking
- Segments text using `["\n\n", "\n", ". ", " ", ""]` with configurable `chunk_size` (1000) and `chunk_overlap` (200).
- Maintains strict provenance: `tender_id`, `document_id`, `source_filename`, `page_number`, `chunk_index`, `char_start`, `char_end`, and `sha256_hash`.

### 4.4 Persistent ChromaDB Vector Indexing
- Stored locally at `CHROMA_PERSIST_DIRECTORY` (default `./data/chroma`).
- Collection `tender_documents` uses Cosine similarity (`{"hnsw:space": "cosine"}`).
- Multi-tenant and tender scoping is enforced via ChromaDB metadata filters (`where={"tender_id": "..."}`).
- Idempotent re-indexing purges previous chunks for `document_id` before upserting fresh vectors.

| `POST` | `/api/v1/company/vault/documents/upload` | Authenticated MSME | Upload, extract, chunk, and index vault PDF |
| `DELETE` | `/api/v1/company/vault/documents/{id}` | Authenticated MSME | Delete document metadata |
| `POST` | `/api/v1/compliance/analyze` | Authenticated MSME | Run LangGraph deterministic + AI compliance analysis |
| `GET` | `/api/v1/compliance/reports` | Authenticated MSME | List historical compliance reports (status filter) |
| `GET` | `/api/v1/compliance/reports/{id}` | Authenticated MSME | Fetch single compliance report with tenant check |
| `GET` | `/api/v1/compliance/reports/{id}/findings` | Authenticated MSME | List detailed criteria findings and citations |
| `GET` | `/api/v1/compliance/reports/{id}/findings/{finding_id}` | Authenticated MSME | Inspect single finding with page-level citations |

---

## 4. Key Security Controls

1. **Argon2 Password Hashing**: Utilizes `pwdlib[argon2]` with secure salt and memory-hard iterations.
2. **Strict Tenant Isolation**: Every company and vault document query enforces `owner_id` or `company_id` resolved directly from the authenticated JWT token. Cross-tenant access attempts return `404 Not Found` without disclosing record existence.
3. **No Privilege Escalation**: Public registration strictly assigns `MSME_USER` role regardless of request payload content. Administrator accounts can only be provisioned via the secure CLI tool.
4. **Protected Vault Paths**: Internal storage references (`uploads/vault/{company_id}/{uuid}.pdf`) are kept internal and never exposed in client API responses.
5. **Reconciliation Guard**: Cryptographic and factual guard layer strictly enforcing that LLMs can never overturn deterministic `FAIL` results, remove unverified citations, or fabricate evidence.

---

## 5. Phase 4 Compliance Engine, Hybrid Retrieval & LangGraph Architecture

### 5.1 Pure Python Deterministic Rule Engine
Objective eligibility conditions are evaluated without generative model intervention:
- **Financial Turnover**: `Decimal` arithmetic evaluating annual minimums or multi-year average thresholds against audited financial records.
- **Relevant Work Experience**: Validates completed contracts in relevant technical domains and contract values; strictly forbids substituting company incorporation age for domain project experience.
- **Active Certifications**: Validates mandatory credentials (e.g. ISO 9001, ISO 27001) and checks against current date for expiration.
- **Mandatory Documents**: Verifies matching documents exist in the MSME company vault.
- **Submission Deadlines**: Validates submission window against UTC timestamps.
- **Categorical Statuses**: `PASS`, `FAIL`, `MISSING_EVIDENCE`, `NEEDS_REVIEW`, `NOT_APPLICABLE`.
- **Decision Policy**: `NOT_ELIGIBLE` if any mandatory requirement fails; `ELIGIBLE` if all mandatory requirements pass; `PARTIALLY_ELIGIBLE` if core requirements pass but supporting documents are missing.

### 5.2 Hybrid Retrieval Layer (RRF)
- **Lexical Retriever**: Queries PostgreSQL `document_chunks` table for keyword and phrase matching within authorized scope.
- **Semantic Retriever**: Queries dense ChromaDB embeddings with cosine distance and multi-tenant metadata filtering.
- **Reciprocal Rank Fusion**: Merges lexical and semantic rankings with constant $k=60$ ($RRF(d) = \sum \frac{1}{k + r_i(d)}$) and deduplicates identical text chunks.
- **Citation Validator**: Validates document existence, authorization scope, and physical 1-based page bounds.

### 5.3 LangGraph Orchestration Workflow
Compiles a 9-node `StateGraph(ComplianceState)`:
1. `input_validation`: Validates input parameters and basic authorization preconditions.
2. `load_context`: Reads authoritative database records, computing SHA-256 version hashes for tender and company.
3. `validate_requirements`: Normalizes raw criteria into typed `NormalizedTenderRequirements`.
4. `deterministic_checks`: Runs `DeterministicRuleEngine` against company credentials.
5. `hybrid_retrieval`: Fetches lexical and semantic citations from both tender and company records.
6. `evidence_analysis`: Generates explainable natural language findings using Gemini (`gemini-2.5-flash`).
7. `reconciliation_guard`: Reconciles AI explanations against deterministic outcomes, ensuring no `FAIL` is overturned.
8. `report_synthesis`: Computes overall status, numeric compliance score, and executive summary.
9. `persist_report`: Commits versioned `ComplianceReport` and child `ComplianceFinding` records in PostgreSQL.

---

## 6. Phase 10 Testing, Security Hardening & Demonstration

### 6.1 Defense-in-Depth Middleware
- **Security Headers (`SecurityHeadersMiddleware`)**: Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`.
- **Sliding-Window Rate Limiter (`InMemoryRateLimiter`)**:
  - Auth routes (`/api/v1/auth/login`, `/api/v1/auth/register`): 60 req/min per IP.
  - Compliance analysis (`/api/v1/compliance/analyze`): 30 req/min per IP.
  - Global API: 600 req/min per IP.
  - Violations return HTTP 429 (`Too Many Requests`) with `Retry-After: 60`.

### 6.2 Test Suite Execution (77 Passing Tests)
Run the complete backend test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
Covers:
- Auth, registration, and Argon2 password verification (9 tests)
- Chunking and token estimation (2 tests)
- Citation validation & page bound bounds (2 tests)
- Company profile & multi-tenant isolation (3 tests)
- Compliance API and vault upload (3 tests)
- PyMuPDF and OCR fallback (3 tests)
- Document metadata and cross-tenant checks (3 tests)
- Health endpoints & readiness probe (3 tests)
- Hybrid retrieval & RRF fusion (2 tests)
- LangGraph orchestration workflow (2 tests)
- **Phase 10 E2E Journeys & 6 Compliance Scenarios (10 tests)**
- PostgreSQL real integration tests (8 tests)
- Deterministic rule engine tests (13 tests)
- **Security headers & rate limiter middleware (2 tests)**
- Document storage & magic bytes validation (5 tests)
- Admin tender CRUD and cascade delete (5 tests)
- Vector store indexing & purging (2 tests)

### 6.3 Automated 14-Step Platform Demonstration
Execute the full-stack synthetic demonstration walkthrough:
```powershell
.\.venv\Scripts\python.exe scripts/demo_walkthrough.py
```
Validates the entire lifecycle:
1. Administrator provisioning and tender creation.
2. Synthetic RFP document upload and vectorization.
3. MSME user registration and JWT authentication.
4. MSME company profile credential configuration.
5. MSME audited balance sheet upload to Document Vault.
6. Tender catalog search and discovery.
7. LangGraph compliance intelligence execution.
8. Deterministic rule evaluation (turnover, experience, certifications, deadlines).
9. Hybrid RAG retrieval (PostgreSQL lexical + ChromaDB semantic).
10. AI narrative explanation synthesis.
11. Reconciliation guard checking deterministic supremacy.
12. Audit-ready compliance report inspection with page citations.
13. Demonstrated mandatory failure scenario: Under-qualified MSME is strictly marked `NOT_ELIGIBLE`.
14. Report persistence across session reloads.
