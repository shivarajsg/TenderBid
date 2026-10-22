# Phase 2 Verification & Runtime Inspection Report

**Project Title**: Agentic AI-Powered Tender Intelligence and Compliance Management Platform for MSMEs Using RAG  
**Evaluation Role**: Senior Backend & QA Engineer  
**Inspection Date**: 2026-10-21  
**Operating Environment**: Windows 11 x64 (PowerShell 5.1 / Python 3.13.15)  
**Database Status**: Live Containerized PostgreSQL 16 (`tender_bid_postgres`) on `127.0.0.1:5433`  

---

## 1. Executive Summary & Verification Outcome

All Phase 2 acceptance criteria and PostgreSQL integration verification gates have been achieved.

1. **Docker & PostgreSQL Container**: Container `tender_bid_postgres` is running and healthy on `127.0.0.1:5433` (`5433 -> 5432`).
2. **Online Alembic Migration**: Successfully applied revision `e2d86d729816` directly against live PostgreSQL.
3. **Database Schema Verification**: All tables (`users`, `companies`, `documents`, `alembic_version`), primary keys, foreign keys (`ON DELETE CASCADE`), and unique indices are confirmed via PostgreSQL catalog queries.
4. **Dedicated Test Database**: Created and utilized an isolated test database (`tender_platform_test`), preserving the development database (`tender_platform`).
5. **Automated Test Results**: **23 out of 23 tests passed** (18 unit tests + 5 live PostgreSQL integration tests; 0 failures, 0 errors, 0 skipped).
6. **Live API Execution**: FastAPI running on `http://127.0.0.1:8000` with `/api/v1/health/ready` dynamically returning `HTTP 200 OK` (`{"database": "connected"}`). End-to-end user registration, authentication, company profile management, and document vault metadata registration were tested against the live PostgreSQL database.

---

## 2. Infrastructure & Database Target Inspection

### 2.1 Configuration Review
- **Project Root**: `C:\Users\KumarShiva\Downloads\Tender_Bid`
- **Backend Directory**: `C:\Users\KumarShiva\Downloads\Tender_Bid\backend`
- **Container Service**: `tender_bid_postgres` (`postgres:16-alpine`, port mapping `127.0.0.1:5433:5432`)
- **Resolved Database URI**: `postgresql+asyncpg://tender_app:[REDACTED]@127.0.0.1:5433/tender_platform`
- **Isolated Test Database URI**: `postgresql+asyncpg://tender_app:[REDACTED]@127.0.0.1:5433/tender_platform_test`

### 2.2 Host Port Verification
```powershell
Get-NetTCPConnection -LocalPort 5433
```
**Observed Result**:
```text
LocalAddress  LocalPort  RemoteAddress  RemotePort  State   AppliedSetting
------------  ---------  -------------  ----------  -----   --------------
127.0.0.1     5433       0.0.0.0        0           Listen  
```

---

## 3. Online Alembic Migration Execution

The live migration was executed from `.\backend` using the Python 3.13 virtual environment:

```powershell
Set-Location ".\backend"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

**Observed Output**:
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> e2d86d729816, initial_schema_users_companies_documents
```

---

## 4. PostgreSQL Schema, Constraints & Index Verification

A read-only catalog query against the live PostgreSQL engine verified the applied schema:

### A. Current Alembic Revision
- `e2d86d729816` recorded in `alembic_version`.

### B. Relational Tables Created
- `alembic_version`
- `users`
- `companies`
- `documents`

### C. Verified Table Structure & Columns
- **`users` Table**:
  - `id`: `uuid` (Primary Key, NOT NULL)
  - `email`: `character varying(255)` (Unique, NOT NULL)
  - `hashed_password`: `character varying(255)` (Argon2 hash, NOT NULL)
  - `full_name`: `character varying(255)` (NOT NULL)
  - `role`: `character varying(50)` (Default: `'MSME_USER'`, NOT NULL)
  - `is_active`: `boolean` (Default: `true`, NOT NULL)
  - `created_at`: `timestamp with time zone` (NOT NULL)
  - `updated_at`: `timestamp with time zone` (NOT NULL)
- **`companies` Table**:
  - `id`: `uuid` (Primary Key, NOT NULL)
  - `owner_id`: `uuid` (Foreign Key $\to$ `users.id` `ON DELETE CASCADE`, Unique, NOT NULL)
  - `legal_name`: `character varying(255)` (NOT NULL)
  - `registration_number`: `character varying(100)` (Unique, NOT NULL)
  - `business_type`: `character varying(50)` (NOT NULL)
  - `sector`: `character varying(100)` (NOT NULL)
  - `incorporation_date`: `date` (NOT NULL)
  - `annual_turnover`: `json` (NOT NULL)
  - `certifications`: `json` (NOT NULL)
  - `work_experience`: `json` (NOT NULL)
  - `created_at`: `timestamp with time zone` (NOT NULL)
  - `updated_at`: `timestamp with time zone` (NOT NULL)
- **`documents` Table**:
  - `id`: `uuid` (Primary Key, NOT NULL)
  - `company_id`: `uuid` (Foreign Key $\to$ `companies.id` `ON DELETE CASCADE`, NOT NULL)
  - `uploaded_by`: `uuid` (Foreign Key $\to$ `users.id` `ON DELETE SET NULL`, Nullable)
  - `document_category`: `character varying(50)` (NOT NULL)
  - `original_filename`: `character varying(255)` (NOT NULL)
  - `storage_path`: `character varying(512)` (Protected internal path, NOT NULL)
  - `mime_type`: `character varying(100)` (NOT NULL)
  - `file_size_bytes`: `bigint` (NOT NULL)
  - `sha256_hash`: `character varying(64)` (NOT NULL)
  - `valid_from`: `date` (Nullable)
  - `valid_until`: `date` (Nullable)
  - `verification_status`: `character varying(50)` (NOT NULL)

### D. Verified Foreign Keys & Indices
- **Primary Keys**: `users_pkey`, `companies_pkey`, `documents_pkey`, `alembic_version_pkc`.
- **Foreign Keys**:
  - `companies_owner_id_fkey`: `companies.owner_id` $\to$ `users.id` (`ON DELETE CASCADE`)
  - `documents_company_id_fkey`: `documents.company_id` $\to$ `companies.id` (`ON DELETE CASCADE`)
  - `documents_uploaded_by_fkey`: `documents.uploaded_by` $\to$ `users.id` (`ON DELETE SET NULL`)
- **Indexes**:
  - `ix_users_email` (Unique)
  - `ix_companies_owner_id` (Unique)
  - `ix_companies_registration_number` (Unique)
  - `ix_companies_sector`
  - `ix_documents_company_id`
  - `ix_documents_uploaded_by`
  - `ix_documents_sha256_hash`

---

## 5. Automated Test Suite Execution (Unit & Live PostgreSQL Integration)

### Test Command
```powershell
Set-Location ".\backend"
.\.venv\Scripts\python.exe -m pytest -v
```

### Observed Results
```text
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-8.3.4, pluggy-1.7.0 -- C:\Users\KumarShiva\Downloads\Tender_Bid\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\KumarShiva\Downloads\Tender_Bid\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, asyncio-0.24.0
asyncio: mode=Mode.AUTO, default_loop_scope=function
collecting ... collected 23 items

tests/test_auth.py::test_admin_provisioning_logic PASSED                 [  4%]
tests/test_auth.py::test_register_success PASSED                         [  8%]
tests/test_auth.py::test_register_duplicate_email_rejected PASSED        [ 13%]
tests/test_auth.py::test_register_validation_failure PASSED              [ 17%]
tests/test_auth.py::test_login_success PASSED                            [ 21%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 26%]
tests/test_auth.py::test_get_current_user_profile PASSED                 [ 30%]
tests/test_auth.py::test_public_registration_cannot_escalate_privileges PASSED [ 34%]
tests/test_auth.py::test_unauthenticated_request_rejected PASSED         [ 39%]
tests/test_companies.py::test_create_and_get_company_profile PASSED      [ 43%]
tests/test_companies.py::test_update_company_profile PASSED              [ 47%]
tests/test_companies.py::test_cross_company_isolation PASSED             [ 52%]
tests/test_documents.py::test_register_and_list_documents PASSED         [ 56%]
tests/test_documents.py::test_invalid_mime_type_rejected PASSED          [ 60%]
tests/test_documents.py::test_cross_company_document_isolation PASSED    [ 65%]
tests/test_health.py::test_root_endpoint PASSED                          [ 69%]
tests/test_health.py::test_health_liveness PASSED                        [ 73%]
tests/test_health.py::test_health_readiness PASSED                       [ 78%]
tests/test_postgres_integration.py::test_postgres_connectivity PASSED    [ 82%]
tests/test_postgres_integration.py::test_postgres_crud_and_relationships PASSED [ 86%]
tests/test_postgres_integration.py::test_postgres_unique_constraint_enforcement PASSED [ 91%]
tests/test_postgres_integration.py::test_postgres_foreign_key_enforcement PASSED [ 95%]
tests/test_postgres_integration.py::test_postgres_transaction_rollback PASSED [100%]

============================= 23 passed in 10.65s =============================
```

### Breakdown of Verified Layers
| Suite | Target Database | Count | Result | Scope Verified |
| :--- | :--- | :--- | :--- | :--- |
| **Unit Tests** | In-Memory SQLite (`aiosqlite`) | 18 | **18 Passed** | Password hashing (Argon2), JWT expiry/signing, route guards, privilege escalation blocks, cross-company isolation. |
| **PostgreSQL Integration Tests** | Isolated PostgreSQL (`tender_platform_test`) | 5 | **5 Passed** | Live PostgreSQL connectivity, real foreign keys (`ON DELETE CASCADE`), engine-level unique constraint (`IntegrityError`), transaction rollback, asyncpg session handling. |

---

## 6. Live FastAPI Server & End-to-End Application Operations

The server was launched via Uvicorn on `http://127.0.0.1:8000`:

```powershell
Set-Location ".\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 6.1 System Probes
```python
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0) as client:
    # 1. Root Metadata
    r_root = client.get("/")
    # Status: 200 OK -> {"app": "Tender Intelligence Platform API", "status": "online", "api_version": "v1", "docs_url": "/docs"}

    # 2. Liveness Check
    r_health = client.get("/api/v1/health")
    # Status: 200 OK -> {"success": true, "data": {"status": "healthy", ...}}

    # 3. Interactive OpenAPI Docs
    r_docs = client.get("/docs")
    # Status: 200 OK

    # 4. PostgreSQL Readiness Probe
    r_ready = client.get("/api/v1/health/ready")
    # Status: 200 OK -> {"success": true, "message": "All backend subsystems are ready", "data": {"database": "connected"}}
```
**Result**: The readiness check confirms live async database connectivity to PostgreSQL returning **`HTTP 200 OK`**.

### 6.2 Live PostgreSQL End-to-End Workflow Verification
Executed against the running server connected to PostgreSQL:
1. `POST /api/v1/auth/register` $\to$ **`HTTP 201 Created`**: User created with Argon2-hashed credentials.
2. `POST /api/v1/auth/login` $\to$ **`HTTP 200 OK`**: Authenticated and issued JWT Bearer token.
3. `POST /api/v1/company/profile` $\to$ **`HTTP 201 Created`**: Initialized MSME company profile with registration ID and turnover metrics in PostgreSQL.
4. `GET /api/v1/company/profile` $\to$ **`HTTP 200 OK`**: Retrieved profile; calculated operational tenure accurately (`years_in_business: 11`).
5. `POST /api/v1/company/vault/documents` $\to$ **`HTTP 201 Created`**: Registered PDF metadata record in the company vault.
6. `GET /api/v1/company/vault/documents` $\to$ **`HTTP 200 OK`**: Retrieved vault document inventory (`Count: 1`).

---

## 7. Files Created and Modified During Verification

1. [`docker-compose.yml`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/docker-compose.yml): Maintained official PostgreSQL container specification.
2. [`backend/alembic/versions/2026_10_20_2342-e2d86d729816_initial_schema.py`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/backend/alembic/versions/2026_10_20_2342-e2d86d729816_initial_schema.py): Applied online migration against PostgreSQL.
3. [`backend/tests/test_postgres_integration.py`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/backend/tests/test_postgres_integration.py): Dedicated live PostgreSQL integration test suite targeting `tender_platform_test`.
4. [`backend/scripts/setup_test_db.py`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/backend/scripts/setup_test_db.py): Automated initialization script ensuring the isolated `tender_platform_test` database exists.
5. [`backend/scripts/inspect_db.py`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/backend/scripts/inspect_db.py): Read-only schema introspection utility.
6. [`docs/PHASE_2_VERIFICATION_REPORT.md`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/docs/PHASE_2_VERIFICATION_REPORT.md): Updated verification report.

---

## 8. Conclusion & Phase 3 Readiness

The backend foundation is verified against live PostgreSQL.
- Database: Operational, migrated, and verified.
- Authentication: Argon2 password hashing and JWT RBAC verified.
- Tenant Isolation: Company profile and document vault boundaries verified at API and database constraint levels.
- Readiness Probe: Active async PostgreSQL ping confirmed.
- Test Coverage: 23/23 tests passing.

The platform is ready to proceed to **Phase 3: Document Intelligence, PDF Extraction & ChromaDB Vector Indexing**.
