# Phase 1: Architectural Decisions, Assumptions & Trade-offs

## 1. Architectural Decision Records (ADRs)

### ADR-01: Hybrid Deterministic & Agentic Compliance Architecture
- **Context**: Bidding compliance involves both non-negotiable objective thresholds (annual turnover, years of active business, possession of mandatory certificates) and nuanced qualitative specifications (warranty conditions, scope of work, technical standards).
- **Decision**: Adopt a hybrid model where a pure Python deterministic engine evaluates all quantitative constraints, while LangGraph orchestrates RAG and Google Gemini for qualitative analysis, clause extraction, and natural language explanations.
- **Rationale**: Relying entirely on LLMs for numerical comparisons creates unacceptable hallucination risks and inconsistent eligibility judgments. Conversely, pure deterministic rules cannot parse unstructured clauses or identify subtle contractual risks.
- **Consequences**: Strict separation between the deterministic rule module and AI services. Deterministic outputs are immutable and cannot be overridden by AI outputs.

---

### ADR-02: PyMuPDF (`fitz`) with Conditional Tesseract OCR Fallback
- **Context**: Government RFPs frequently mix native digital text with scanned addenda, signed declarations, and rasterized specification sheets.
- **Decision**: Use PyMuPDF as the primary high-speed text extraction engine. Inspect text character density per page; if density falls below 100 characters per page, route that rasterized page through Tesseract OCR.
- **Alternatives Considered**:
  - *Full OCR for all pages*: Too slow (several minutes for a 100-page RFP) and degrades accuracy on clean native digital text.
  - *Native extraction only*: Silently drops scanned addenda, resulting in incomplete tender knowledge and false negatives in compliance checks.
- **Consequences**: PyMuPDF handles 90%+ of pages in sub-second time; Tesseract handles scanned exceptions, preserving page metadata throughout.

---

### ADR-03: Vector Database Selection: ChromaDB
- **Context**: The platform requires persistent semantic vector retrieval indexed with page numbers and source filenames.
- **Decision**: Use ChromaDB in persistent client mode.
- **Alternatives Considered**:
  - *Pinecone / Qdrant Cloud*: Introduces external cloud dependencies, paid tiers, and networking overhead for development and initial deployment.
  - *pgvector*: Requires PostgreSQL, whereas MongoDB is our primary document database for semi-structured tender and profile data.
- **Consequences**: ChromaDB runs locally, stores embeddings on disk, supports metadata filtering (`tender_id`), and provides an easy upgrade path to distributed deployment if required.

---

### ADR-04: Orchestration Framework: LangGraph
- **Context**: The compliance evaluation flow requires multi-step state transitions (validation $\to$ deterministic checks $\to$ semantic retrieval $\to$ LLM explanation $\to$ reconciliation guard $\to$ report synthesis).
- **Decision**: Use LangGraph for workflow orchestration.
- **Alternatives Considered**:
  - *Linear LangChain chains (`LLMChain` / `SequentialChain`)*: Inflexible, poor state inspection, and difficult to introduce conditional branching or deterministic reconciliation guards.
  - *Custom procedural Python scripts*: Lacks standardized state management, graph visualization, and streaming capabilities.
- **Consequences**: LangGraph provides explicit, inspectable typed state (`ComplianceState`), clear node boundaries, and deterministic branch control.

---

### ADR-05: Local-First Sandboxed File Storage with Abstract Storage Interface
- **Context**: Document files (company financials, tender RFPs) must be stored securely during development without requiring immediate AWS/GCP cloud accounts.
- **Decision**: Implement a local file storage provider partitioned by tenant (`/uploads/tenders/{tender_id}` and `/uploads/vault/{company_id}`) behind a generic `StorageProvider` interface (`save_file`, `get_file`, `delete_file`).
- **Consequences**: Zero friction for local development and student deployment; effortless migration to Amazon S3 or Google Cloud Storage in production by simply implementing the interface.

---

### ADR-06: Database Technology Pivot to PostgreSQL and SQLAlchemy 2.x
- **Context**: While Phase 1 conceptualized MongoDB for document storage, the business domain requires strict relational integrity between tenants, users, company profiles, documents, tenders, compliance snapshots, and application states. Financial thresholds, company credentials, and audit trails demand atomic transactions, relational foreign key constraints, and schema migrations.
- **Decision**: Adopt PostgreSQL as the primary relational application database, accessed asynchronously via SQLAlchemy 2.x and `asyncpg`, with Alembic managing versioned schema migrations. ChromaDB remains the dedicated vector database for RAG retrieval in subsequent phases.
- **Rationale**:
  - Relational foreign keys between users, companies, and documents enforce tenant isolation and ownership at the engine level.
  - Transactional consistency guarantees atomic updates for multi-step profile and bid preparation workflows.
  - Alembic provides auditable, deterministic migration paths across development and production environments.
- **Consequences**: MongoDB and Motor are discarded from backend dependencies. All data models are defined using SQLAlchemy 2.x declarative mappings and Pydantic v2 schemas.

---

## 2. Core Assumptions

1. **Structured Tender Inputs**: In the initial release, administrators manually enter structured eligibility criteria (minimum turnover, required experience years, mandatory certificates) or review extracted values during tender upload. Fully unsupervised automated extraction of structured criteria is treated as an AI-assisted suggestion, not an infallible ground truth.
2. **PDF Dominance**: Tender documentation and company evidence are assumed to be in PDF format. Non-PDF formats (e.g., DOCX, XLSX, scanned TIFFs) will require conversion to PDF before ingestion.
3. **No Live Portal Scraping in v1**: To avoid anti-scraping blocks, CAPTCHA hurdles, and government portal policy restrictions, tenders are curated and uploaded via the Admin Portal rather than scraped directly.
4. **English Language Baseline**: Initial document extraction, RAG embeddings, and LLM prompts are optimized for English tender notices and company documents.
5. **Human-in-the-Loop Signoff**: The platform assists and accelerates bid preparation but assumes the MSME's bidding manager performs final human verification prior to official portal submission.

---

## 3. Evaluated Alternatives and Trade-offs

| Decision Area | Selected Option | Alternative Considered | Trade-off / Justification |
| :--- | :--- | :--- | :--- |
| **Primary Database** | MongoDB | PostgreSQL (Relational) | MongoDB handles semi-structured, nested tender criteria, arbitrary certificate types, and dynamic report payloads with less schema migration overhead. |
| **Frontend Framework** | React + Vite + TypeScript | Next.js (Full-stack SSR) | A dedicated FastAPI backend with React SPA provides cleaner service decoupling, distinct backend API contracts, and simpler student team division of labor. |
| **LLM Provider** | Google Gemini (1.5 Flash / Pro) | Local Ollama / LLaMA 3 | Gemini provides large context windows, fast inference, and low operational cost without demanding local GPU hardware. |
| **Auth Strategy** | Stateless JWT with RBAC | Stateful Session Cookies | JWT integrates cleanly with decoupled React single-page applications and mobile or CLI integrations. |

---

## 4. Technical Risks & Mitigations

| Risk | Impact | Probability | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Gemini API Rate Limiting (429)** | High | Medium | Implement exponential backoff retries; fall back gracefully to raw retrieved excerpts + deterministic results if API is unavailable. |
| **OCR Quality on Bad Scans** | Medium | High | Detect low-confidence OCR pages and prominently warn the user in the report that specific pages had degraded text. |
| **Cross-Tenant Data Leakage** | Critical | Low | Enforce `company_id` filter injection at the repository query layer; verify via automated integration tests. |
| **LLM Hallucinating Tender Rules** | High | Medium | Enforce strict citation grounding; mandate page references; forbid LLM from overriding deterministic checks via the Reconciliation Guard. |

---

## 5. Open Questions for Confirmation in Subsequent Phases

1. **Corrigenda & Addenda Handling**: When a procuring agency issues an amendment changing a deadline or turnover threshold, how should the existing indexed tender and previous compliance reports be versioned or invalidated? *(Proposed: Admin uploads corrigendum $\to$ system flags existing reports as `OUTDATED_BY_CORRIGENDUM`).*
2. **Document Expiration Alerts**: Should the system automatically email or notify MSME users when an uploaded credential (e.g., ISO certificate) is within 30 days of expiration? *(Targeted for Phase 4 or 5).*
3. **Tender Requirement Extraction Assistance**: Should we build an AI-assisted form auto-filler for the Admin when uploading tenders, where Gemini pre-populates structured turnover and experience thresholds for admin confirmation? *(Recommended for Phase 3/4).*
