# System Architecture Specification

## 1. High-Level Architecture Overview

The **Tender Intelligence & Compliance Management Platform** follows a modern, decoupled three-tier architecture augmented by an asynchronous document intelligence and agentic workflow pipeline. It bridges deterministic business rules with Retrieval-Augmented Generation (RAG) to deliver explainable, audit-proof tender eligibility assessments for MSMEs.

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client (React + Vite + TypeScript)"]
        UI_MSME["MSME Dashboard & Portal"]
        UI_Admin["Admin Tender Management"]
        UI_QA["Tender Chat & Q&A"]
        UI_Reports["Compliance & Audit Viewer"]
    end

    subgraph GatewayLayer["API & Security Boundary (FastAPI)"]
        AuthMiddleware["JWT Auth & Role Guard (RBAC)"]
        TenantGuard["Tenant Isolation Middleware"]
        ReqValidator["Pydantic Request/Response Validation"]
    end

    subgraph ServiceLayer["Backend Application Services"]
        AuthService["Authentication Service"]
        TenderService["Tender Management Service"]
        DocService["Vault & File Storage Service"]
        RuleEngine["Deterministic Python Rule Engine"]
        AgentService["LangGraph Orchestration Service"]
        RAGService["RAG & Semantic Retrieval Service"]
    end

    subgraph IntelligenceLayer["Document Intelligence & AI Pipeline"]
        PDFParser["PyMuPDF (fitz) Parser"]
        OCRModule["Tesseract OCR Engine"]
        EmbeddingEngine["Embedding Model Client"]
        GeminiClient["Google Gemini API Client"]
    end

    subgraph StorageLayer["Data & Persistence Layer"]
        MongoDB[("MongoDB Database\n(Users, Profiles, Tenders, Reports)")]
        ChromaDB[("ChromaDB Vector Store\n(Tender Document Chunks & Embeddings)")]
        FileStorage[("Protected Local File Storage\n(/uploads/tenders, /uploads/vault)")]
    end

    UI_MSME -->|HTTPS / REST API| AuthMiddleware
    UI_Admin -->|HTTPS / REST API| AuthMiddleware
    UI_QA -->|HTTPS / REST API| AuthMiddleware
    UI_Reports -->|HTTPS / REST API| AuthMiddleware

    AuthMiddleware --> TenantGuard
    TenantGuard --> ReqValidator

    ReqValidator --> AuthService
    ReqValidator --> TenderService
    ReqValidator --> DocService
    ReqValidator --> RuleEngine
    ReqValidator --> AgentService
    ReqValidator --> RAGService

    TenderService --> DocService
    DocService --> FileStorage
    DocService --> PDFParser

    PDFParser -->|Low-density pages| OCRModule
    PDFParser -->|Clean text chunks| EmbeddingEngine
    OCRModule -->|OCR text chunks| EmbeddingEngine

    EmbeddingEngine --> ChromaDB

    RuleEngine --> MongoDB
    AgentService --> RuleEngine
    AgentService --> RAGService
    RAGService --> ChromaDB
    AgentService --> GeminiClient

    AuthService --> MongoDB
    TenderService --> MongoDB
    DocService --> MongoDB
    AgentService --> MongoDB
```

---

## 2. Component Descriptions

### 2.1 Frontend Tier (Client Layer)
- **Framework**: React 18+ with TypeScript, bundled using Vite for rapid builds and optimized production assets.
- **Routing**: React Router v6 implementing role-aware protected route guards (`<ProtectedRoute role="MSME" />` and `<ProtectedRoute role="ADMIN" />`).
- **Styling**: Tailwind CSS providing responsive, accessible, utility-first UI components.
- **State & Networking**: Axios with interceptors for automatic JWT Bearer token attachment, 401 token refresh handling, and global error handling.

### 2.2 API & Security Gateway (FastAPI)
- **Framework**: FastAPI (Python 3.11+), leveraging ASGI asynchronous request handling.
- **Validation**: Pydantic v2 schemas enforcing strict input validation, type safety, and standardized JSON error payloads.
- **Authentication**: JWT (JSON Web Tokens) with short-lived access tokens and refresh tokens.
- **Tenant Isolation**: Backend middleware injecting `company_id` from the decoded JWT into the request state, guaranteeing that data operations are scoped exclusively to the authenticated tenant.

### 2.3 Application & Business Logic Services
- **AuthService**: Handles user registration, password hashing (via `bcrypt`), login verification, and token issuance.
- **TenderService**: Manages tender document lifecycles, metadata indexing, and status transitions.
- **DocService (Document Vault)**: Manages MSME company documents (incorporation certificates, turnover audit sheets, ISO credentials) and tender PDF files. Enforces mime-type validation and isolated disk directory partitioning.
- **Deterministic Rule Engine**: Pure Python business logic module devoid of LLM dependencies. Evaluates objective mathematical and logical conditions (e.g., turnover, operational years, deadline validity, mandatory document availability).
- **RAG & Retrieval Service**: Interfaces with ChromaDB to perform metadata-filtered cosine similarity searches, extracting contextual tender excerpts with precise page numbers.
- **LangGraph Orchestration Service**: Manages multi-step stateful workflows reconciling deterministic outputs with semantic evidence and Google Gemini LLM synthesis.

### 2.4 Document Intelligence & AI Components
- **PyMuPDF (`fitz`)**: High-performance C-backed PDF parsing extracting text, layout information, and page metadata.
- **Tesseract OCR**: Invoked conditionally when PyMuPDF detects image-only or low-density pages (<100 characters), ensuring scanned tenders are not silently dropped.
- **Embedding Model**: Google Text Embedding API (e.g., `text-embedding-004`) or compatible high-dimensional embedding model creating semantic vectors with tender metadata.
- **Google Gemini API**: `gemini-1.5-flash` or `gemini-1.5-pro` accessed over secure HTTPS for qualitative clause summarization, risk identification, and natural language explanations.

### 2.5 Persistence & Storage Tier
- **MongoDB**: Primary document store managing:
  - User accounts and authentication credentials.
  - MSME company profiles and financial metrics.
  - Tender metadata and structured requirements.
  - Document metadata records and verification statuses.
  - Historical compliance reports and application tracking states.
- **ChromaDB**: Lightweight vector database storing chunk embeddings, chunk text, and source metadata (`tender_id`, `filename`, `page_number`, `chunk_id`).
- **Protected File Storage**: Sandboxed local filesystem storage during development (partitioned by `/uploads/tenders/{tender_id}/` and `/uploads/vault/{company_id}/`), designed behind an abstract `StorageProvider` interface for seamless migration to Amazon S3 or Google Cloud Storage in production.

---

## 3. End-to-End Request and Data Flows

### 3.1 Tender Ingestion & Indexing Flow (Admin)
```mermaid
sequenceDiagram
    autonumber
    actor Admin as Platform Admin
    participant API as FastAPI Ingestion Router
    participant DocSvc as Doc Processing Service
    participant Disk as Local File Storage
    participant PDF as PyMuPDF / Tesseract
    participant Chunker as Semantic Chunker
    participant Emb as Embedding Engine
    participant VDB as ChromaDB Vector Store
    participant DB as MongoDB

    Admin->>API: POST /api/v1/admin/tenders (Metadata & PDF Upload)
    API->>DocSvc: Validate file (MIME, size) & persist
    DocSvc->>Disk: Write PDF to /uploads/tenders/{tender_id}/
    DocSvc->>DB: Create Tender Record (Status: PROCESSING)
    API-->>Admin: 202 Accepted (Tender Created, Processing Async)

    DocSvc->>PDF: Extract text page-by-page
    alt Scanned Page Detected (Text < 100 chars)
        PDF->>PDF: Run Tesseract OCR on page raster
    end
    PDF-->>DocSvc: Return extracted pages with page numbers
    DocSvc->>Chunker: Split into 500-800 token chunks (preserving page metadata)
    Chunker-->>DocSvc: Chunks with {tender_id, filename, page_no}
    DocSvc->>Emb: Batch generate embeddings
    Emb-->>DocSvc: Vector embeddings list
    DocSvc->>VDB: Insert embeddings + metadata in tender collection
    DocSvc->>DB: Update Tender Record (Status: ACTIVE, TotalPages, ChunksIndexed)
```

---

### 3.2 Compliance Analysis Flow (MSME User)
```mermaid
sequenceDiagram
    autonumber
    actor User as MSME User
    participant API as FastAPI Compliance Router
    participant Orchestrator as LangGraph Orchestrator
    participant RuleEngine as Deterministic Engine
    participant RAG as Retrieval Service (ChromaDB)
    participant LLM as Google Gemini API
    participant DB as MongoDB

    User->>API: POST /api/v1/compliance/analyze (tender_id)
    API->>Orchestrator: Start Compliance Graph (company_id, tender_id)
    
    Orchestrator->>DB: Fetch Company Profile & Document Vault metadata
    Orchestrator->>DB: Fetch Tender Structured Requirements
    
    Note over Orchestrator,RuleEngine: Step 1: Deterministic Hard Checks
    Orchestrator->>RuleEngine: Evaluate (Turnover, Experience, Certs, Docs, Deadlines)
    RuleEngine-->>Orchestrator: Deterministic Results (PASS / FAIL / NEEDS_REVIEW / MISSING_EVIDENCE)
    
    Note over Orchestrator,RAG: Step 2: Semantic Evidence Gathering
    Orchestrator->>RAG: Retrieve relevant clauses for complex criteria
    RAG-->>Orchestrator: Top-k chunks with page numbers and source quotes
    
    Note over Orchestrator,LLM: Step 3: Explanation & Synthesis
    Orchestrator->>LLM: Prompt with Deterministic Results + Retrieved Evidence
    Note over LLM: LLM forbidden from altering deterministic FAIL to PASS
    LLM-->>Orchestrator: Grounded Explanations, Risk Flags, Next Actions
    
    Note over Orchestrator: Step 4: Reconciliation Guard
    Orchestrator->>Orchestrator: Assert no status conflicts between Rule Engine and LLM
    
    Orchestrator->>DB: Save ComplianceReport
    Orchestrator-->>API: Return final Compliance Report
    API-->>User: 200 OK (Structured Report with Citations)
```

---

## 4. Agentic AI Workflow Architecture (LangGraph)

The LangGraph orchestration engine enforces a predictable, resilient workflow where the Large Language Model acts as an interpreter and synthesizer rather than an unconstrained decision-maker.

```mermaid
flowchart TD
    Start([Start Compliance Analysis]) --> InputValidation["Node 1: Validate Inputs\n(Check company profile & tender status)"]
    
    InputValidation --> CheckInputsValid{Inputs Complete?}
    CheckInputsValid -->|No| GenerateInputError["Set State: INCOMPLETE_PROFILE\nFlag Missing Profile Fields"] --> FinalizeReport
    CheckInputsValid -->|Yes| DeterministicEvaluation["Node 2: Deterministic Rule Engine\n(Turnover, Experience, Certifications, Deadlines)"]
    
    DeterministicEvaluation --> BranchOnHardRules{Any Hard\nMandatory Fail?}
    
    BranchOnHardRules -->|Yes - Non-negotiable| FlagHardFail["Record Hard Failures\n(Status = FAIL)\nSkip unnecessary LLM inference"] --> RetrievalStep
    BranchOnHardRules -->|No / Partial| RetrievalStep["Node 3: Semantic Retrieval\n(ChromaDB query per evaluation clause)"]
    
    RetrievalStep --> VerifyEvidence{Evidence\nFound?}
    VerifyEvidence -->|Low similarity / Missing| MarkUncertain["Record Status: MISSING_EVIDENCE\n(Do not extrapolate)"] --> LLMAnalysis
    VerifyEvidence -->|Evidence Present| LLMAnalysis["Node 4: Gemini AI Analysis\n(Synthesize explanations grounded in citations)"]
    
    LLMAnalysis --> ReconciliationGuard["Node 5: Reconciliation Guard\n(Assert LLM narrative matches deterministic status)"]
    
    ReconciliationGuard --> FinalizeReport["Node 6: Report Synthesis\n(Compute overall status, format citations, build checklist)"]
    
    FinalizeReport --> End([Return Final Structured Report])
```

### 4.1 Node Roles and Invariant Rules
1. **`InputValidation`**: Ensures the MSME company has populated minimum profile fields (turnover history, incorporation year). If essential data is absent, the workflow short-circuits gracefully.
2. **`DeterministicEvaluation`**: Evaluates all hard mathematical constraints. If a tender mandates a \$1,000,000 turnover and the MSME has \$450,000, this node records `FAIL`.
3. **`RetrievalStep`**: Executes targeted queries against the tender's ChromaDB index using criteria keywords. Returns verbatim text, source filenames, and page numbers.
4. **`LLMAnalysis`**: Passes the deterministic results and retrieved text to Google Gemini with strict system instructions: Gemini is instructed to explain *why* criteria passed or failed, highlight ambiguous technical clauses, and suggest remedial actions.
5. **`ReconciliationGuard`**: A pure Python deterministic safety valve that inspects Gemini's structured output. If Gemini erroneously marks a requirement as satisfied despite a deterministic `FAIL`, the guard overrides the narrative and flags a warning.
6. **`ReportSynthesis`**: Aggregates all criteria into a unified schema, computes the final overall recommendation (`ELIGIBLE`, `INELIGIBLE`, or `POTENTIALLY_ELIGIBLE_WITH_CONDITIONS`), and persists the report to MongoDB.

---

## 5. Error Handling & Service Boundaries

| Service Boundary | Failure Mode | Mitigation & System Behavior |
| :--- | :--- | :--- |
| **Document Processing** | Corrupted or password-locked PDF | Parsing stops immediately; sets tender status to `FAILED_PROCESSING`; logs exact error in MongoDB; notifies Admin UI. |
| **Document Processing** | Scanned PDF with unreadable text | Triggers Tesseract OCR; if OCR confidence < 30%, flags page as `DEGRADED_TEXT_QUALITY` but continues remaining pages. |
| **ChromaDB Vector Store** | Vector index unavailable or corrupt | Fallback to deterministic evaluation only; flags compliance report as `RAG_UNAVAILABLE`; LLM semantic check marked `NEEDS_REVIEW`. |
| **Google Gemini API** | Rate limit (429) or Service Down (503) | Exponential backoff retry (up to 3 attempts); if still unavailable, report returns deterministic results with raw retrieved excerpts without AI summary. |
| **Deterministic Rule Engine** | Missing company profile field | Marks specific criterion as `MISSING_EVIDENCE` instead of crashing; overall status reflects missing prerequisites. |
| **Tenant Isolation Guard** | Attempted cross-tenant ID access | Request immediately rejected with HTTP 403 Forbidden; audit event logged to application security logs. |
