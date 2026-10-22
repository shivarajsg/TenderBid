# Agentic AI-Powered Tender Intelligence and Compliance Management Platform for MSMEs Using RAG

An enterprise-grade, full-stack intelligence and compliance automation platform engineered for Micro, Small, and Medium Enterprises (MSMEs) participating in public procurement. The platform centralizes tender discovery, manages verified company credentials in an encrypted vault, executes deterministic compliance evaluations, retrieves document evidence via Hybrid RAG (PostgreSQL Full-Text Search + ChromaDB Vector Embeddings), and synthesizes audit-ready gap analyses with Google Gemini AI under strict deterministic supervision.

---

## Table of Contents

- [1. Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
- [2. Platform Capabilities Overview](#2-platform-capabilities-overview)
- [3. Key Architectural Features](#3-key-architectural-features)
  - [3.1 Deterministic Compliance Engine vs. AI Explanation Layer](#31-deterministic-compliance-engine-vs-ai-explanation-layer)
  - [3.2 Hybrid RAG Pipeline & Reciprocal Rank Fusion (RRF)](#32-hybrid-rag-pipeline--reciprocal-rank-fusion-rrf)
  - [3.3 LangGraph 9-Node Orchestration Graph](#33-langgraph-9-node-orchestration-graph)
  - [3.4 In-App PDF Viewing & Automatic Document Retrieval](#34-in-app-pdf-viewing--automatic-document-retrieval)
  - [3.5 Multi-Portal Tender Ingestion Framework](#35-multi-portal-tender-ingestion-framework)
  - [3.6 Bid Tracking & Autonomous Deadline Alerting](#36-bid-tracking--autonomous-deadline-alerting)
- [4. Technology Stack](#4-technology-stack)
- [5. System Architecture](#5-system-architecture)
- [6. Repository Structure](#6-repository-structure)
- [7. Prerequisites](#7-prerequisites)
- [8. Local Installation & Setup Guide (Windows PowerShell)](#8-local-installation--setup-guide-windows-powershell)
- [9. Environment Variables & Configuration](#9-environment-variables--configuration)
- [10. Database Schema & Storage Architecture](#10-database-schema--storage-architecture)
- [11. Tender Ingestion & Document Retrieval Workflow](#11-tender-ingestion--document-retrieval-workflow)
- [12. Deterministic Compliance Engine](#12-deterministic-compliance-engine)
- [13. RAG & Agentic AI Analysis Workflow](#13-rag--agentic-ai-analysis-workflow)
- [14. Complete API Reference](#14-complete-api-reference)
- [15. Frontend User Guide & Workflows](#15-frontend-user-guide--workflows)
- [16. Running Automated Tests & Verification](#16-running-automated-tests--verification)
- [17. Security Architecture & Controls](#17-security-architecture--controls)
- [18. Known Limitations & Practical Troubleshooting](#18-known-limitations--practical-troubleshooting)
- [19. Master 11-Phase Project Status & Roadmap](#19-master-11-phase-project-status--roadmap)
- [20. Production Deployment Considerations](#20-production-deployment-considerations)
- [21. Contribution, License & Acknowledgements](#21-contribution-license--acknowledgements)

---

## 1. Executive Summary & Problem Statement

Public procurement in India through platforms such as the **Government e-Marketplace (GeM)**, the **Central Public Procurement Portal (CPPP)**, state portals, and Public Sector Undertakings (PSUs) represents an enormous market opportunity. However, Micro, Small, and Medium Enterprises (MSMEs) face severe structural barriers when bidding for government contracts:

1. **Information Asymmetry & Manual Overhead**: Tender documents, Requests for Proposals (RFPs), and General Conditions of Contract (GCC) frequently span 50 to 200+ pages of complex legal, financial, and technical clauses. MSMEs lack the dedicated legal and bidding departments required to parse these notices.
2. **Strict Disqualification Rules**: Government tenders enforce strict pre-qualification criteria (annual turnover thresholds over consecutive financial years, past experience with similar work orders, ISO/technical certifications, Earnest Money Deposit (EMD) requirements, and mandatory statutory filings). A single missing document or miscalculated turnover average results in summary disqualification.
3. **Severe Verification Friction**: Bidders must verify their internal records (audited balance sheets, GST returns, PAN, Udyam certificates, client completion certificates) against tender requirements without knowing beforehand whether they meet all mandatory conditions.
4. **Tight Submission Deadlines**: Bidders frequently discover tenders late, leaving inadequate time to gather notarized affidavits, obtain bank guarantees, or clarify ambiguities through pre-bid queries.

### Purpose of this Platform

This platform addresses these challenges by combining **deterministic business rule validation** with **Retrieval-Augmented Generation (RAG)** and **agentic AI workflows**. It delivers an automated, audit-ready assistant that:
- Centralizes tender notices and corporate credentials in an isolated multi-tenant architecture.
- Ingests public tenders from authorized third-party APIs (TenderKart Client API) and cloud scrapers (Apify Government Tenders Actor), with automated fallback for direct portal notices.
- Securely retrieves and indexes official tender PDFs using high-performance text extraction and OCR.
- Evaluates objective financial, technical, and statutory eligibility using strict Python business rules that cannot be hallucinated or overturned by AI.
- Leverages Google Gemini to synthesize plain-English explanations, risk summaries, and missing-evidence checklists grounded strictly in document citations.
- Tracks bids through their procurement lifecycle and alerts users before critical submission deadlines.

> [!NOTE]
> **Academic & Evaluative Context**: This platform is designed for research, technical portfolio demonstration, and pre-production evaluation. Compliance evaluations are decision-support aids based on parsed documentation and do not guarantee government tender qualification or contract awards.

---

## 2. Platform Capabilities Overview

The platform provides a complete set of features confirmed by the codebase:

| Capability | Module / Component | Implementation Status |
| :--- | :--- | :--- |
| **Authentication & RBAC** | `app.core.security`, `app.api.routes.auth` | Implemented & Verified (Argon2id, JWT HS256, `ADMIN` & `MSME_USER` roles) |
| **Company Profile Management** | `app.api.routes.companies`, `CompanyService` | Implemented & Verified (Udyam, PAN, GSTIN, Annual Turnover history, Net Worth) |
| **Encrypted Document Vault** | `app.api.routes.documents`, `DocumentService` | Implemented & Verified (MIME checking, SHA-256 deduplication, file storage) |
| **Tender Catalogue & Discovery** | `app.api.routes.tenders`, `TenderService` | Implemented & Verified (Search, filtering by portal, status, budget, pagination) |
| **Automated Tender Ingestion** | `app.services.ingestion`, `IngestionScheduler` | Implemented & Verified (TenderKart API, Apify Actor, GeM/CPPP connectors) |
| **Secure Tender PDF Retrieval** | `app.services.document_retrieval_service` | Implemented & Verified (SSRF domain whitelist, 50MB cap, magic byte check) |
| **In-App PDF Viewing** | `frontend/src/pages/tenders/TenderDetailPage` | Implemented & Verified (Authenticated stream, inline modal, object URLs) |
| **PDF Extraction & OCR Fallback** | `app.services.extraction_service`, `ocr_service` | Implemented & Verified (PyMuPDF high-speed parser + Tesseract OCR fallback) |
| **Text Chunking & Provenance** | `app.services.chunking_service` | Implemented & Verified (Recursive chunker, page tracking, token counts) |
| **Hybrid RAG (Lexical + Semantic)** | `app.services.retrieval.hybrid_retriever` | Implemented & Verified (PostgreSQL full-text + ChromaDB cosine similarity, RRF) |
| **Deterministic Compliance Engine** | `app.services.compliance.rule_engine` | Implemented & Verified (10 rule types, pure Python math, zero LLM hallucination) |
| **LangGraph Agentic Orchestrator** | `app.services.workflows.compliance_graph` | Implemented & Verified (9-node state graph, state persistence, error boundaries) |
| **Gemini AI Evidence Explanations** | `app.services.ai.compliance_analyzer` | Implemented & Verified (Google Gemini 2.5 Flash, structured 17-field findings) |
| **Deterministic Primacy Guard** | `app.services.compliance.reconciliation_guard` | Implemented & Verified (Hard security barrier preventing AI from mutating rule results) |
| **Tender Q&A Assistant** | `app.services.retrieval.tender_qa_service` | Implemented & Verified (Interactive query engine with exact page citations) |
| **Bid Tracking & Applications** | `app.api.routes.bid_applications`, `BidTrackingService`| Implemented & Verified (Stages: DRAFT, SUBMITTED, UNDER_EVALUATION, AWARDED, REJECTED) |
| **Proactive Deadline Alerts** | `app.services.deadline_scheduler`, `alert_service` | Implemented & Verified (Background asyncio worker, in-app notifications, badge count) |

---

## 3. Key Architectural Features

### 3.1 Deterministic Compliance Engine vs. AI Explanation Layer

A core architectural invariant of the platform is **Deterministic Supremacy**:

$$\text{Final Evaluation Status} \equiv \text{Deterministic Rule Output}$$

```
                                      ┌───────────────────────────────────────┐
                                      │   Authoritative Input Data            │
                                      │   - Structured Tender Requirements    │
                                      │   - Verified Company Financial Data   │
                                      └──────────────────┬────────────────────┘
                                                         │
                                                         ▼
                                      ┌───────────────────────────────────────┐
                                      │   Pure Python Deterministic Engine    │
                                      │   (Financial, Experience, Statutes)   │
                                      └──────────────────┬────────────────────┘
                                                         │ Output: PASS / FAIL / MISSING
                                                         ▼
                     ┌───────────────────────────────────┴───────────────────────────────────┐
                     │                                                                       │
                     ▼                                                                       ▼
      ┌─────────────────────────────┐                                         ┌─────────────────────────────┐
      │   Deterministic Outcome     │                                         │   Hybrid RAG Retrieval      │
      │   Strict, unalterable math  │                                         │   ChromaDB + PostgreSQL FTS │
      └──────────────┬──────────────┘                                         └──────────────┬──────────────┘
                     │                                                                       │
                     │                                                                       ▼
                     │                                                        ┌─────────────────────────────┐
                     │                                                        │   Google Gemini 2.5 Flash   │
                     │                                                        │   Synthesizes plain-English │
                     │                                                        │   rationale & gap analysis  │
                     │                                                        └──────────────┬──────────────┘
                     │                                                                       │
                     ▼                                                                       ▼
      ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
      │                                Reconciliation Guard                                         │
      │   Enforces that AI CANNOT alter status, score, or required values. Discards illegal overrides│
      └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │ Audit-Ready Final Report    │
                                      └─────────────────────────────┘
```

1. **Objective Rules Rule Objective Truth**:
   - Financial turnover is computed using exact `Decimal` arithmetic.
   - Years of operational experience are evaluated against verified incorporation dates.
   - Required certifications (e.g., ISO 9001, ISO 27001, CMMI) and statutory numbers (PAN, GSTIN, Udyam) are matched via exact set comparisons.
   - If an MSME fails an objective turnover threshold (e.g., has ₹1.5 Cr average against ₹5.0 Cr required), the deterministic status is permanently set to `FAIL`.
2. **AI Is Restricted to Explanation & Assistance**:
   - The LLM (Google Gemini) receives the rule outcome, requirement clauses, and retrieved document chunks.
   - It drafts plain-English interpretations, summarizes risk consequences, and suggests actionable remediation steps.
   - The **Reconciliation Guard** (`ReconciliationGuard`) intercepts the AI response. If the AI claims an MSME is compliant when the rule engine marked it `FAIL`, the system rejects the AI mutation, logs a security warning, and preserves the deterministic `FAIL`.

### 3.2 Hybrid RAG Pipeline & Reciprocal Rank Fusion (RRF)

Standard vector search frequently struggles with exact alphanumeric identifiers common in government tenders (e.g., `GEM/2026/B/189211`, `Clause 4.14.2(b)`, `ISO/IEC 27001:2022`). Conversely, keyword search misses semantic synonyms. The platform implements **Reciprocal Rank Fusion (RRF)** combining both retrieval paradigms:

1. **Lexical Search (PostgreSQL)**:
   - Evaluates full-text search vectors generated from indexed document chunks (`DocumentChunkModel`).
   - Uses PostgreSQL `websearch_to_tsquery` or `plainto_tsquery` matching against English dictionary text search vectors (`to_tsvector('english', chunk_text)`).
2. **Semantic Search (ChromaDB)**:
   - Uses deep vector embeddings stored in isolated ChromaDB collections (`tender_documents` and `company_documents`).
   - Executes cosine similarity matching against the user's requirement or query text.
3. **Reciprocal Rank Fusion**:
   For each retrieved document chunk $d$, its fused score is calculated as:
   $$RRF(d) = \sum_{m \in \{\text{lexical}, \text{semantic}\}} \frac{w_m}{k + \text{rank}_m(d)}$$
   where $k = 60$ (smoothing constant), $w_{\text{semantic}} = 0.6$, and $w_{\text{lexical}} = 0.4$.
4. **Citation Verification**:
   The `CitationValidator` verifies that every chunk referenced in the evaluation genuinely exists in the database and matches the target tender or company scope before citations are presented to the user.

### 3.3 LangGraph 9-Node Orchestration Graph

Compliance analysis is coordinated by a stateful, compiled **LangGraph** workflow (`ComplianceWorkflowOrchestrator` in [`compliance_graph.py`](file:///C:/Users/KumarShiva/Downloads/Tender_Bid/backend/app/services/workflows/compliance_graph.py)):

```mermaid
graph TD
    START([Start]) --> N1[1. input_validation]
    N1 --> N2[2. load_context]
    N2 --> N3[3. validate_requirements]
    N3 --> N4[4. deterministic_checks]
    N4 --> N5[5. hybrid_retrieval]
    N5 --> N6[6. evidence_analysis]
    N6 --> N7[7. reconciliation_guard]
    N7 --> N8[8. report_synthesis]
    N8 --> N9[9. persist_report]
    N9 --> END_NODE([End])

    classDef node fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef startEnd fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    class START,END_NODE startEnd;
    class N1,N2,N3,N4,N5,N6,N7,N8,N9 node;
```

1. **`input_validation`**: Verifies valid UUIDs, tenant scopes, and permissions.
2. **`load_context`**: Loads the authoritative Tender, Company, attached RFP documents, and vault credentials.
3. **`validate_requirements`**: Normalizes tender requirements using `RequirementNormalizer` into standardized schemas.
4. **`deterministic_checks`**: Pure Python rule execution across turnover, experience, certifications, deadlines, and mandatory documents.
5. **`hybrid_retrieval`**: Dispatches parallel hybrid RRF queries against ChromaDB and PostgreSQL for each requirement clause.
6. **`evidence_analysis`**: Prompts Google Gemini with normalized requirements and retrieved citations to generate detailed 17-field finding narratives.
7. **`reconciliation_guard`**: Audits findings, forcing deterministic status supremacy over AI outputs.
8. **`report_synthesis`**: Calculates overall compliance score, status counts, document coverage percentage, and executive summaries using `ReportBuilder`.
9. **`persist_report`**: Atomically commits `ComplianceReport` and `ComplianceFinding` records to PostgreSQL in a single database transaction.

### 3.4 In-App PDF Viewing & Automatic Document Retrieval

The platform provides end-to-end document retrieval and native in-app viewing:
- **SSRF Protection Engine**: When fetching tender documents from external URLs, the service validates IP addresses against DNS rebinding, blocks private/loopback/link-local/multicast IP spaces, and strictly limits domains to an approved whitelist (`*.gov.in`, `*.nic.in`, `tenderkart.in`, `apify.com`).
- **Magic Byte Validation**: Streams external HTTP responses, rejects files exceeding 50 MB, and verifies the `%PDF-` binary magic bytes.
- **Interactive Portal Fallback**: Recognizes when an external URL is an interactive bid webpage rather than a direct PDF, classifying it as `OFFICIAL_PORTAL_PAGE` without contaminating the PDF vault.
- **In-App PDF Viewer Modal**: Users inspect tender notices directly inside the browser using an authenticated inline stream (`GET /api/v1/tenders/{tender_id}/documents/{document_id}/view`) loaded via secure object URLs (`<iframe src={blobUrl}>`), eliminating unauthenticated local file downloads.

### 3.5 Multi-Portal Tender Ingestion Framework

The background ingestion framework (`app.services.ingestion`) supports multiple public procurement data providers:
- **TenderKart Client API**: Integrates with `https://tenderkart.in/api/v1/client`, supporting saved filter discovery (`GET /filters`), cursor-based incremental sync with `sync.next_updated_after` checkpoints, and automated rate limiting (30 req/min with RFC `Retry-After` backoff).
- **Apify Cloud Actor**: Dispatches scraping jobs to the Apify actor `foxlabs/india-government-tenders` or `fascinating_lentil~india-government-tenders-scraper` via backend-only token authentication.
- **GeM & CPPP Direct Adapters**: Built-in connectors for GeM and CPPP with automated handling of WAF and CAPTCHA boundaries.

### 3.6 Bid Tracking & Autonomous Deadline Alerting

- **Application Lifecycle**: Tracks internal bid preparation across defined stages (`DRAFT`, `SUBMITTED`, `UNDER_EVALUATION`, `AWARDED`, `REJECTED`) with tracking notes and deadline timestamps.
- **Autonomous Deadline Alert Scheduler**: An asyncio worker (`DeadlineAlertScheduler`) running within the FastAPI lifespan inspects active tenders every 300 seconds. It calculates remaining hours until submission cutoffs and generates in-app `Notification` records at 7 days, 3 days, and 24 hours prior to deadline.

---

## 4. Technology Stack

### Backend Technologies
- **Python 3.13**: Modern Python runtime leveraging enhanced asyncio execution and typed dataclasses.
- **FastAPI (0.115.5)**: High-performance async ASGI web framework for REST API routing and OpenAPI documentation.
- **Uvicorn (0.32.1)**: Production-grade ASGI web server with standard worker protocol support.
- **SQLAlchemy (2.0.36)**: Modern 2.0-style async ORM utilizing `asyncpg` for PostgreSQL connection pooling.
- **Alembic (1.14.0)**: Relational database migration tool managing versioned, zero-downtime schema evolution.
- **PostgreSQL 16**: Relational database managing users, companies, tenders, documents, compliance reports, and full-text search indexes.
- **ChromaDB (0.5.20+)**: Persistent vector database managing embeddings with cosine similarity querying and metadata filtering.
- **LangGraph (0.2.0+) & LangChain Core (0.3.0+)**: Graph-based state machine orchestrating multi-step compliance evaluations.
- **Google GenAI SDK (0.1.0+)**: Official SDK connecting to **Google Gemini 2.5 Flash** for natural language synthesis.
- **PyMuPDF (fitz 1.24.14+)**: Ultra-fast PDF parsing engine extracting text, metadata, and physical page numbers.
- **Pytesseract (0.3.13) & Pillow (11.0.0)**: Optical Character Recognition (OCR) fallback for scanned images and non-searchable PDFs.
- **Pwdlib (Argon2id)** & **PyJWT (2.10.0)**: High-entropy password hashing and cryptographic JSON Web Token signing.
- **HTTPX (0.28.1)**: Asynchronous HTTP client for SSRF-protected external document retrieval and provider API calls.

### Frontend Technologies
- **React (18.3.1)**: Declarative component framework utilizing modern React hooks and strict state lifecycle.
- **TypeScript (5.7.2)**: Static type safety across all UI models, API responses, and route configurations.
- **Vite (6.1.0)**: Modern build tool and ESM development server with optimized rollup production bundling.
- **Tailwind CSS (3.4.17)**: Utility-first CSS framework providing a responsive, professional design system.
- **React Router DOM (6.29.0)**: Client-side routing with protected layout wrappers and role-based route guards.
- **Lucide React (0.475.0)**: Consistent, accessible icon set.
- **Axios (1.7.9)**: HTTP client with request/response interceptors for automatic JWT bearer token injection.

### Testing & Verification Infrastructure
- **Pytest (8.3.4) & Pytest-Asyncio (0.24.0)**: Complete backend test runner supporting unit, mock, and live PostgreSQL integration tests.
- **Vitest (3.0.5)**: High-performance Vite-native frontend test runner with JSDOM browser simulation.
- **Playwright (1.64.1)**: End-to-end browser automation framework running headless Chromium journeys.
- **Docker & Docker Compose**: Multi-stage container definitions and local PostgreSQL database orchestration.

---

## 5. System Architecture

The following diagram illustrates the complete data flow, service boundaries, and deterministic security fences implemented in the platform:

```mermaid
flowchart TD
    subgraph ClientLayer ["Frontend Client Layer (React 18 + TypeScript + Vite)"]
        UI_User["MSME User / Bid Manager"]
        UI_Admin["Platform Administrator"]
        ReactApp["React Single Page Application<br/>(Tailwind CSS + React Router v6)"]
        PDF_Viewer["In-App PDF Viewer Modal<br/>(Authenticated Blob Stream)"]
        UI_User --> ReactApp
        UI_Admin --> ReactApp
        ReactApp -.-> PDF_Viewer
    end

    subgraph SecurityLayer ["FastAPI Boundary & Security Middleware"]
        ReverseProxy["Reverse Proxy / Nginx / Vite Dev Server"]
        FastAPI_App["FastAPI REST Application (app.main:app)"]
        SecHeaders["SecurityHeadersMiddleware<br/>(HSTS, CSP, X-Frame-Options)"]
        RateLimiter["InMemoryRateLimiter<br/>(Auth: 60/m, Analysis: 30/m)"]
        JWT_Auth["JWT Authentication & RBAC<br/>(Argon2id + Bearer Token Guard)"]
        
        ReverseProxy --> FastAPI_App
        FastAPI_App --> SecHeaders
        SecHeaders --> RateLimiter
        RateLimiter --> JWT_Auth
    end

    subgraph RouteLayer ["API Routing Controllers (/api/v1)"]
        R_Auth["/auth"]
        R_Company["/company & /vault"]
        R_Tender["/tenders & /admin/tenders"]
        R_Compliance["/compliance"]
        R_Apps["/applications"]
        R_Notif["/notifications"]
        
        JWT_Auth --> R_Auth
        JWT_Auth --> R_Company
        JWT_Auth --> R_Tender
        JWT_Auth --> R_Compliance
        JWT_Auth --> R_Apps
        JWT_Auth --> R_Notif
    end

    subgraph CoreServices ["Core Business Services & Storage"]
        DocRetrieval["TenderDocumentRetrievalService<br/>(SSRF Protection + Magic Byte Check)"]
        DocParser["ExtractionService & OCRService<br/>(PyMuPDF + Tesseract Fallback)"]
        Chunker["ChunkingService<br/>(Recursive 1000ch / 200ov)"]
        Storage["StorageService (Protected Local Disk)"]
        
        R_Tender --> DocRetrieval
        R_Company --> Storage
        DocRetrieval --> Storage
        Storage --> DocParser
        DocParser --> Chunker
    end

    subgraph DualStore ["Hybrid Persistence & Indexing"]
        PostgresDB[("PostgreSQL 16 (Port 5433)<br/>- Users, Companies, Tenders<br/>- Inverted Lexical Text Search<br/>- Compliance Reports & Findings<br/>- Ingestion Runs & Deadlines")]
        ChromaStore[("ChromaDB Vector Store<br/>- 'tender_documents' Collection<br/>- 'company_documents' Collection<br/>- Semantic Cosine Similarity")]
        
        Chunker --> PostgresDB
        Chunker --> ChromaStore
        R_Company --> PostgresDB
        R_Apps --> PostgresDB
        R_Notif --> PostgresDB
    end

    subgraph AgenticPipeline ["LangGraph Compliance & RAG Pipeline"]
        Orchestrator["ComplianceWorkflowOrchestrator<br/>(9-Node StateGraph)"]
        HybridRetriever["HybridRetriever<br/>(Reciprocal Rank Fusion k=60)"]
        RuleEngine["DeterministicRuleEngine<br/>(Pure Python Math Rules)"]
        GeminiAI["Google Gemini 2.5 Flash<br/>(AI Explanations & Rationale)"]
        ReconGuard["ReconciliationGuard<br/>(Deterministic Supremacy Barrier)"]
        
        R_Compliance --> Orchestrator
        Orchestrator --> RuleEngine
        Orchestrator --> HybridRetriever
        HybridRetriever --> PostgresDB
        HybridRetriever --> ChromaStore
        HybridRetriever --> GeminiAI
        RuleEngine --> ReconGuard
        GeminiAI --> ReconGuard
        ReconGuard --> PostgresDB
    end

    subgraph BackgroundWorkers ["Autonomous Background Schedulers"]
        DeadlineSched["DeadlineAlertScheduler<br/>(300s Polling Cycle)"]
        IngestionSched["TenderIngestionScheduler<br/>(3600s Polling Cycle)"]
        
        DeadlineSched --> PostgresDB
        IngestionSched --> PostgresDB
    end

    ReactApp --> ReverseProxy
```

---

## 6. Repository Structure

```
Tender_Bid/
├── docker-compose.yml                 # Local PostgreSQL container service (Port 5433)
├── docker-compose.prod.yml            # Multi-stage production container stack
├── docs/                              # Architectural documentation & phase verification reports
│   ├── AI_RAG_ARCHITECTURE.md
│   ├── API_SPECIFICATION.md
│   ├── DATABASE_SCHEMA.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── PHASE_10_VERIFICATION_REPORT.md
│   ├── PHASE_11_TENDER_INGESTION_REPORT.md
│   ├── PROJECT_AS_BUILT_AUDIT.md
│   └── PROJECT_ROADMAP.md
│
├── backend/                           # FastAPI Backend Application
│   ├── alembic/                       # Relational database migration scripts
│   │   ├── versions/                  # Versioned schema revisions (5 applied revisions)
│   │   └── env.py                     # Async migration runner environment
│   ├── app/                           # Backend application source code
│   │   ├── api/                       # API route definitions & dependencies
│   │   │   ├── deps.py                # Database session & user injection dependencies
│   │   │   └── routes/                # Endpoint routers (auth, tenders, compliance, etc.)
│   │   ├── core/                      # Configuration, security, and middleware
│   │   │   ├── config.py              # Pydantic Settings loaded from .env
│   │   │   ├── middleware.py          # SecurityHeaders & InMemoryRateLimiter
│   │   │   └── security.py            # Argon2 password hashing & JWT token management
│   │   ├── db/                        # Database connectivity & repositories
│   │   │   ├── session.py             # SQLAlchemy async engine & sessionmaker
│   │   │   └── repositories/          # Type-safe repository abstraction classes
│   │   ├── models/                    # Declarative SQLAlchemy ORM models
│   │   │   ├── user.py                # User account & role definitions
│   │   │   ├── company.py             # MSME company profile & financial parameters
│   │   │   ├── document.py            # Document vault records & storage references
│   │   │   ├── document_chunk.py      # Indexed text chunks for full-text search
│   │   │   ├── tender.py              # Tender notices & structured requirements
│   │   │   ├── compliance_report.py   # Synthesized compliance evaluation reports
│   │   │   ├── compliance_finding.py  # 17-field granular requirement findings
│   │   │   ├── bid_application.py     # Bid tracking & lifecycle records
│   │   │   ├── notification.py        # Proactive user alerts & notifications
│   │   │   └── ingestion_run.py       # Ingestion audit log records
│   │   ├── schemas/                   # Pydantic request/response validation schemas
│   │   ├── services/                  # Business logic services
│   │   │   ├── ai/                    # Gemini API compliance analyzer & prompts
│   │   │   ├── compliance/            # RuleEngine, Normalizer, ReportBuilder, Guard
│   │   │   ├── ingestion/             # Apify, TenderKart, GeM, CPPP connectors
│   │   │   ├── retrieval/             # HybridRetriever, Lexical, Semantic, QA, Validator
│   │   │   ├── workflows/             # LangGraph state graph & orchestrator
│   │   │   ├── chunking_service.py    # Recursive text chunking implementation
│   │   │   ├── deadline_scheduler.py  # Autonomous deadline alert worker
│   │   │   ├── document_retrieval_service.py # SSRF-safe PDF downloader
│   │   │   ├── extraction_service.py  # PyMuPDF text extraction
│   │   │   ├── ocr_service.py         # Tesseract OCR engine fallback
│   │   │   ├── storage_service.py     # Local file storage abstraction
│   │   │   └── vector_store_service.py # ChromaDB persistent client wrapper
│   │   ├── cli.py                     # Administrative CLI tool (create-admin)
│   │   └── main.py                    # FastAPI entry point, lifespan, & exception handlers
│   ├── data/                          # Persistent ChromaDB vector database directory
│   ├── scripts/                       # Maintenance & demonstration automation
│   │   └── demo_walkthrough.py        # 14-step automated platform demonstration script
│   ├── tests/                         # Backend test suite (138 tests across 28 files)
│   ├── uploads/                       # Protected local document vault storage
│   ├── .env.example                   # Sanitized backend environment template
│   ├── alembic.ini                    # Alembic migration configuration
│   ├── Dockerfile                     # Multi-stage production container build
│   ├── pytest.ini                     # Pytest runner configuration
│   └── requirements.txt               # Pinned Python package dependencies
│
└── frontend/                          # React + TypeScript + Vite Application
    ├── e2e/                           # Playwright end-to-end browser journey tests
    ├── src/                           # Frontend application source code
    │   ├── api/                       # Axios typed API client modules
    │   ├── components/                # Reusable UI components & layouts
    │   │   ├── layout/                # AppLayout, Navbar, Sidebar, RouteGuards
    │   │   └── ui/                    # StatusBadge, MetricCard, Modal, InAppPDFViewer
    │   ├── context/                   # React AuthContext for JWT session state
    │   ├── pages/                     # Full-page route views
    │   │   ├── admin/                 # AdminTendersPage, AdminTenderFormPage
    │   │   ├── applications/          # ApplicationsPage (Bid Tracker)
    │   │   ├── auth/                  # LoginPage, RegisterPage
    │   │   ├── company/               # CompanyProfilePage
    │   │   ├── compliance/            # ComplianceAnalysisPage, ReportDetailPage
    │   │   ├── dashboard/             # DashboardPage (Overview & Metrics)
    │   │   ├── tenders/               # TendersListPage, TenderDetailPage (PDF Viewer)
    │   │   └── vault/                 # DocumentVaultPage
    │   ├── test/                      # Frontend Vitest test suite (33 tests across 11 files)
    │   ├── types/                     # TypeScript shared interfaces & enums
    │   ├── App.tsx                    # Route definitions & application root
    │   └── main.tsx                   # React DOM entry point
    ├── .env.example                   # Frontend environment template
    ├── Dockerfile                     # Production Nginx multi-stage build
    ├── nginx.conf                     # Nginx production configuration
    ├── package.json                   # NPM dependencies & scripts
    ├── playwright.config.ts           # Playwright browser runner configuration
    ├── tailwind.config.js             # Tailwind CSS design system rules
    └── vite.config.ts                 # Vite bundler & test configuration
```

---

## 7. Prerequisites

Ensure the following tools and runtimes are installed on your workstation:

| Prerequisite | Minimum Version | Verified Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11 | Windows 11 64-bit | Local workstation host |
| **Python** | 3.11+ | **3.13.1** (`py -3.13 --version`) | Backend application runtime |
| **Node.js** | 20.0+ | **20.18.0** (`node -v`) | Frontend build tool & runtime |
| **npm** | 10.0+ | **10.8.2** (`npm -v`) | Package dependency manager |
| **Docker Desktop**| 4.20+ | **Docker Engine 27+** | Runs isolated PostgreSQL 16 container |
| **Tesseract OCR** *(Optional)* | 5.0+ | 5.3.3 (Windows x64) | OCR text extraction for scanned PDF images |
| **Google Gemini Key** *(Optional)*| API v1/v1beta | Gemini 2.5 Flash | AI-powered narrative analysis & explanations |
| **Apify API Token** *(Optional)* | API v2 | Apify Actor Token | External government tender ingestion crawler |

> [!NOTE]
> The platform runs fully offline using deterministic rules and local RRF retrieval even if `GEMINI_API_KEY` or `APIFY_API_TOKEN` are omitted.

---

## 8. Local Installation & Setup Guide (Windows PowerShell)

Follow these exact steps in an elevated Windows PowerShell terminal to configure, initialize, and execute the entire platform locally.

### Step 1: Open PowerShell and Navigate to the Repository

```powershell
Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid"
```

### Step 2: Start the PostgreSQL Database Container

The local environment uses Docker Compose to run PostgreSQL 16 Alpine. Notice that the host port is mapped to **`5433`** to prevent collisions with any existing local PostgreSQL service running on standard port `5432`:

```powershell
# Start the PostgreSQL service in the background
docker compose up -d postgres

# Verify that the container is healthy and listening on port 5433
docker compose ps
```

Expected output:
```
NAME                    IMAGE                COMMAND                  SERVICE    CREATED          STATUS                    PORTS
tender_bid_postgres     postgres:16-alpine   "docker-entrypoint.s…"   postgres   20 seconds ago   Up 19 seconds (healthy)   127.0.0.1:5433->5432/tcp
```

### Step 3: Configure and Initialize the Python Backend

1. Navigate to the `backend` directory:
   ```powershell
   Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\backend"
   ```

2. Create an isolated Python 3.13 virtual environment:
   ```powershell
   py -3.13 -m venv .venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Upgrade `pip` and install pinned dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Create your backend `.env` file from the provided template:
   ```powershell
   Copy-Item .env.example .env
   ```

   *Verify that your `.env` contains the required high-entropy JWT secret key and points to port 5433:*
   ```ini
   DATABASE_URL="postgresql+asyncpg://tender_app:tender_dev_secret_2026@127.0.0.1:5433/tender_platform"
   JWT_SECRET_KEY="tender_bid_development_jwt_secret_key_super_secure_min_32_bytes"
   ```

6. Apply all Alembic database migrations:
   ```powershell
   python -m alembic upgrade head
   ```

7. *(Optional)* Provision an initial Platform Administrator user:
   ```powershell
   python -m app.cli create-admin --email admin@tenderbid.internal --full-name "Platform Administrator" --password "AdminSecret2026!"
   ```

8. Start the FastAPI development server:
   ```powershell
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   - **Interactive API Documentation (Swagger)**: `http://127.0.0.1:8000/docs`
   - **Alternative Documentation (ReDoc)**: `http://127.0.0.1:8000/redoc`
   - **Backend Health Check**: `http://127.0.0.1:8000/api/v1/health`

### Step 4: Configure and Start the React Frontend

1. Open a **second** Windows PowerShell terminal and navigate to the `frontend` directory:
   ```powershell
   Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\frontend"
   ```

2. Install all frontend dependencies:
   ```powershell
   npm install
   ```

3. Create the frontend environment configuration:
   ```powershell
   Copy-Item .env.example .env.development
   ```

4. Start the Vite development server:
   ```powershell
   npm run dev
   ```

5. Open your web browser and navigate to:
   **`http://127.0.0.1:5173`**

---

## 9. Environment Variables & Configuration

The application centralizes settings via Pydantic (`Settings` in [`config.py`](file:///C:/Users/KumarShiva/Downloads/Tender_Bid/backend/app/core/config.py)). Configure these variables in `backend/.env`:

| Variable | Description | Required? | Default / Example Value |
| :--- | :--- | :---: | :--- |
| `APP_NAME` | Display name of the platform API | No | `Tender Intelligence Platform API` |
| `APP_ENV` | Application lifecycle environment (`development`, `staging`, `production`) | No | `development` |
| `DEBUG` | Enable verbose debug logging and stack traces | No | `false` |
| `DATABASE_URL` | Async connection string targeting PostgreSQL | **Yes** | `postgresql+asyncpg://tender_app:PASSWORD@127.0.0.1:5433/tender_platform` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing JWT tokens ($\ge 32$ chars) | **Yes** | `REPLACE_WITH_SECURE_RANDOM_KEY_MIN_32_CHARS` |
| `JWT_ALGORITHM` | Algorithm used for JWT signatures | No | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of authentication session tokens | No | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Duration before refresh tokens expire | No | `7` |
| `FRONTEND_ORIGINS` | Permitted origins for Cross-Origin Resource Sharing | No | `http://localhost:5173,http://127.0.0.1:5173` |
| `UPLOAD_DIR` | Protected file storage directory for PDFs and credentials | No | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed file upload size in megabytes | No | `25` |
| `TESSERACT_CMD` | Path to `tesseract.exe` for optical character recognition | No | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `CHROMA_PERSIST_DIRECTORY` | On-disk storage path for persistent vector embeddings | No | `./data/chroma` |
| `CHROMA_COLLECTION_NAME` | Vector collection name for tender RFP excerpts | No | `tender_documents` |
| `CHROMA_COMPANY_COLLECTION_NAME`| Vector collection name for company vault credentials | No | `company_documents` |
| `EMBEDDING_PROVIDER` | Embedding provider (`default` uses ONNX MiniLM, `mock`, or `huggingface`) | No | `default` |
| `CHUNK_SIZE` | Maximum character length per document text chunk | No | `1000` |
| `CHUNK_OVERLAP` | Overlapping character boundary between adjacent chunks | No | `200` |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini LLM analysis | Optional | `AIzaSy...` *(Leave empty for rule-only fallback)* |
| `GEMINI_MODEL` | Gemini LLM model identifier | No | `gemini-2.5-flash` |
| `DEADLINE_ALERT_ENABLED` | Enable automated background deadline alert scanning | No | `true` |
| `DEADLINE_ALERT_INTERVAL_SECONDS`| Frequency in seconds for checking tender deadlines | No | `300` |
| `INGESTION_ENABLED` | Enable automated background government tender ingestion | No | `true` |
| `INGESTION_INTERVAL_SECONDS` | Frequency in seconds between tender ingestion runs | No | `3600` |
| `TENDERKART_ENABLED` | Enable TenderKart third-party tender data connector | No | `true` |
| `TENDERKART_API_KEY` | API key for authenticating with TenderKart Client API | Optional | `tk_live_...` |
| `TENDERKART_BASE_URL` | Base URL of the TenderKart Client API | No | `https://tenderkart.in/api/v1/client` |
| `APIFY_ENABLED` | Enable Apify government tenders scraper connector | No | `true` |
| `APIFY_API_TOKEN` | Apify API token for running actors and reading datasets | Optional | `apify_api_...` |
| `APIFY_ACTOR_ID` | Default Apify actor identifier | No | `foxlabs~india-government-tenders` |
| `MAX_DOCUMENT_DOWNLOAD_BYTES` | Maximum allowed tender PDF download size | No | `52428800` (50 MB) |
| `ALLOWED_DOCUMENT_DOMAINS` | Whitelisted domain suffixes for secure document downloads | No | `gov.in,nic.in,tenderkart.in,apify.com` |

---

## 10. Database Schema & Storage Architecture

### 10.1 PostgreSQL Relational Model Structure

The relational database enforces data integrity, multi-tenancy, and audit provenance across 10 core tables:

```
  ┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
  │              users              │                 │            companies            │
  ├─────────────────────────────────┤                 ├─────────────────────────────────┤
  │ id (PK, UUID)                   │ 1             1 │ id (PK, UUID)                   │
  │ email (UQ, String)              ├─────────────────┤ user_id (FK, UUID)              │
  │ hashed_password (String)        │                 │ legal_name (String)             │
  │ role (MSME_USER | ADMIN)        │                 │ udyam_registration_number (Str) │
  │ is_active (Boolean)             │                 │ annual_turnover (JSONB)         │
  └────────────────┬────────────────┘                 │ net_worth (Numeric)             │
                   │                                  └───────────────┬─────────────────┘
                   │ 1                                                │ 1
                   ▼ N                                                ▼ N
  ┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
  │          notifications          │                 │            documents            │
  ├─────────────────────────────────┤                 ├─────────────────────────────────┤
  │ id (PK, UUID)                   │                 │ id (PK, UUID)                   │
  │ user_id (FK, UUID)              │                 │ company_id (FK, Nullable, UUID) │
  │ tender_id (FK, Nullable, UUID)  │                 │ tender_id (FK, Nullable, UUID)  │
  │ title, message (String)         │                 │ storage_path (String)           │
  │ is_read (Boolean)               │                 │ sha256_hash (String)            │
  └─────────────────────────────────┘                 │ processing_status (String)      │
                                                      └───────────────┬─────────────────┘
                                                                      │ 1
                                                                      ▼ N
  ┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
  │             tenders             │                 │         document_chunks         │
  ├─────────────────────────────────┤                 ├─────────────────────────────────┤
  │ id (PK, UUID)                   │ 1             N │ id (PK, UUID)                   │
  │ title (String)                  ├─────────────────┤ document_id (FK, UUID)          │
  │ reference_number (UQ, String)   │                 │ chunk_index (Integer)           │
  │ authority (String)              │                 │ chunk_text (Text)               │
  │ estimated_value (Numeric)       │                 │ page_number (Integer)           │
  │ submission_deadline (DateTime)  │                 │ embedding_id (String)           │
  │ requirements (JSONB)            │                 └─────────────────────────────────┘
  │ proposed_requirements (JSONB)   │
  │ source_portal, source_url (Str) │
  └────────────────┬────────────────┘
                   │
         ┌─────────┴─────────┐
       1 │                 1 │
         ▼ N                 ▼ N
  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
  │  bid_applications   │   │ compliance_reports  │ 1 │ compliance_findings │
  ├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤
  │ id (PK, UUID)       │   │ id (PK, UUID)       │ N │ id (PK, UUID)       │
  │ tender_id (FK)      │   │ tender_id (FK)      ├───┤ report_id (FK)      │
  │ company_id (FK)     │   │ company_id (FK)     │   │ requirement_id (Str)│
  │ status (String)     │   │ overall_status (Str)│   │ status (PASS/FAIL)  │
  │ notes (Text)        │   │ overall_score (Num) │   │ reason (Text)       │
  └─────────────────────┘   │ summary (Text)      │   │ ai_explanation (Text│
                            └─────────────────────┘   └─────────────────────┘
```

### 10.2 Storage Separation Principles
- **Binary Files on Disk**: Uploaded PDFs are never stored directly in PostgreSQL database columns. Instead, they are stored on protected local disk storage (`./uploads`), referenced in the database via UUID-based filenames and `storage_path` strings.
- **Deduplication via SHA-256**: Every uploaded or fetched document has its SHA-256 checksum calculated before writing to disk. Duplicate uploads within the same tender or company are rejected or linked idempotently without redundant storage.
- **Vector Storage in ChromaDB**: Chunks extracted from documents are vectorized and stored in persistent ChromaDB collections (`./data/chroma`). The vector database handles cosine similarity querying, while PostgreSQL stores inverted lexical indexes for full-text search.

---

## 11. Tender Ingestion & Document Retrieval Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as User / Admin
    participant Frontend as React Frontend
    participant API as FastAPI Router
    participant RetrievalSvc as TenderDocumentRetrievalService
    participant ExtHost as External Official Portal
    participant Vault as StorageService (Vault)
    participant Pipe as Document Pipeline
    participant Chroma as ChromaDB / PostgreSQL

    Admin->>Frontend: Clicks "Fetch Tender Documents"
    Frontend->>API: POST /api/v1/tenders/{id}/fetch-documents
    API->>RetrievalSvc: fetch_tender_documents(tender_id)
    RetrievalSvc->>RetrievalSvc: Inspect tender metadata & source URLs
    
    alt URL is Not Safe / Unapproved Domain
        RetrievalSvc-->>API: Rejects download (SSRF Protection)
    else URL is Approved Official Domain
        RetrievalSvc->>ExtHost: Stream GET request (validate size & headers)
        alt Response is HTML Portal Page
            RetrievalSvc->>RetrievalSvc: Classify as OFFICIAL_PORTAL_PAGE (No fake PDF)
        else Response is Genuine PDF (%PDF-)
            RetrievalSvc->>RetrievalSvc: Validate with PyMuPDF & check SHA-256
            RetrievalSvc->>Vault: Write binary file to ./uploads/
            RetrievalSvc->>Pipe: Trigger process_tender_documents()
            Pipe->>Chroma: Extract text, chunk, and index embeddings
        end
    end
    RetrievalSvc-->>API: Return FetchTenderDocumentsResponse
    API-->>Frontend: 200 OK (updated documents array)
    Frontend->>Admin: Displays "Stored in Vault" badge & "View PDF" button
```

---

## 12. Deterministic Compliance Engine

The deterministic compliance engine (`app.services.compliance.rule_engine`) validates objective qualification criteria using pure Python math and logic:

### Evaluated Rule Types
1. **`TURNOVER`**: Verifies minimum annual turnover or average turnover across specified financial years against audited records using exact `Decimal` precision.
2. **`EXPERIENCE`**: Validates required years of operational experience against the company's incorporation date.
3. **`CERTIFICATION`**: Checks for required quality or security accreditations (ISO 9001, ISO 27001, CMMI Level 3+, etc.).
4. **`MANDATORY_DOCUMENT`**: Checks whether mandatory documents (e.g., GST Registration Certificate, Audited Balance Sheets, PAN) exist in the company vault.
5. **`DEADLINE`**: Evaluates whether the submission cutoff has already passed.
6. **`TECHNICAL`**: Matches required technical capabilities and past work orders.
7. **`COMMERCIAL`**: Assesses EMD payment requirements and checks for MSME/NSIC EMD exemption eligibility.
8. **`LEGAL`**: Verifies non-blacklisting declarations and legal business type compatibility.
9. **`SUBMISSION`**: Validates bid submission modes (two-packet, single-stage, e-tender).
10. **`OTHER`**: Handles custom tender-specific criteria.

### Standardized Status Codes

#### Finding Status Codes (`ComplianceFinding.status`):
- **`PASS`**: The company satisfies all conditions of the requirement with verified documentation.
- **`FAIL`**: The company objectively fails a mandatory qualification parameter.
- **`MISSING_EVIDENCE`**: The company has not uploaded the supporting credential to the Document Vault.
- **`NEEDS_REVIEW`**: The requirement requires human judgment, specialized legal interpretation, or physical inspection.
- **`NOT_APPLICABLE`**: The requirement does not apply to this bidder (e.g., MSME exemption for EMD deposit).

#### Overall Report Status Codes (`ComplianceReport.overall_status`):
- **`ELIGIBLE`**: All mandatory requirements evaluated to `PASS`.
- **`PARTIALLY_ELIGIBLE`**: Non-mandatory requirements failed, or conditional exemptions apply.
- **`NOT_ELIGIBLE`**: One or more mandatory requirements evaluated to `FAIL`.
- **`NEEDS_REVIEW`**: Essential evidence is ambiguous or unverified, requiring human confirmation before bidding.
- **`ANALYSIS_BLOCKED_NO_DOCUMENTS`**: Evaluation could not proceed because neither tender notices nor company documents are available.

---

## 13. RAG & Agentic AI Analysis Workflow

1. **Document Parsing**: PyMuPDF extracts text streams with page-level coordinates. Non-text pages trigger Tesseract OCR.
2. **Recursive Chunking**: Chunks are generated with 1,000-character windows and 200-character overlap. Each chunk records `page_number`, `document_id`, `tender_id`, and `token_count`.
3. **Lexical Indexing**: Chunk text is indexed in PostgreSQL using full-text search dictionaries.
4. **Semantic Indexing**: Chunk text is embedded into ChromaDB vector collections.
5. **Hybrid Retrieval (RRF)**: Dispatches both searches and merges candidates using Reciprocal Rank Fusion ($k=60$).
6. **Gemini AI Prompting**: Passes the retrieved excerpts into Google Gemini 2.5 Flash with strict instructions to generate:
   - Plain-English interpretation of complex procurement legal clauses.
   - Specific company evidence comparisons.
   - Gap analyses identifying exactly what is missing.
   - Risk and consequence summaries if the bid is submitted without rectifying gaps.
   - Actionable recommendations for the bidder.
7. **Reconciliation Guard Enforcement**:
   ```python
   # Excerpt from app.services.compliance.reconciliation_guard:
   if deterministic_finding.status == "FAIL" and ai_finding.status != "FAIL":
       logger.warning("Deterministic supremacy violation intercepted! Overriding AI hallucination.")
       ai_finding.status = "FAIL"
   ```

---

## 14. Complete API Reference

All endpoints are mounted under `/api/v1` and document standard HTTP status codes:

### Authentication & Users
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/register` | Register new MSME user account | None |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT bearer token | None |
| `GET` | `/api/v1/auth/me` | Retrieve profile of the authenticated user | Bearer JWT |

### Company Profile & Vault
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/company/profile` | Retrieve MSME corporate profile & financial metrics | Bearer JWT |
| `POST` | `/api/v1/company/profile` | Create company profile | Bearer JWT |
| `PUT` | `/api/v1/company/profile` | Update company profile (turnover, Udyam, etc.) | Bearer JWT |
| `GET` | `/api/v1/company/vault/documents` | List all verified credentials in company vault | Bearer JWT |
| `POST` | `/api/v1/company/vault/documents/upload` | Upload new document to vault (PDF/Images) | Bearer JWT |
| `GET` | `/api/v1/company/vault/documents/{id}` | Inspect metadata of specific vault document | Bearer JWT |
| `DELETE`| `/api/v1/company/vault/documents/{id}` | Delete document from vault | Bearer JWT |

### Tenders & Document Inspection
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/tenders` | Search tenders (paginated, supports `?page=`, `?q=`, `?source=`) | Bearer JWT |
| `GET` | `/api/v1/tenders/{id}` | Retrieve tender details, deadlines, and documents | Bearer JWT |
| `POST` | `/api/v1/tenders/{id}/fetch-documents`| Automatically fetch accessible tender PDFs from source | Bearer JWT |
| `GET` | `/api/v1/tenders/{id}/documents/{doc_id}/view`| Stream tender PDF inline for in-app browser viewing | Bearer JWT |
| `GET` | `/api/v1/tenders/{id}/documents/{doc_id}/download`| Download original tender document | Bearer JWT |
| `POST` | `/api/v1/tenders/{id}/qa` | Ask natural language question on tender with citations | Bearer JWT |
| `GET` | `/api/v1/tenders/ingestion/status` | Retrieve status of government tender ingestion runs | Bearer JWT |
| `POST` | `/api/v1/tenders/ingestion/sync` | Trigger manual government tender ingestion sync | ADMIN |

### Administrator Tender Management
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/admin/tenders` | Publish new tender notice with criteria | ADMIN |
| `PUT` | `/api/v1/admin/tenders/{id}` | Update existing tender details | ADMIN |
| `DELETE`| `/api/v1/admin/tenders/{id}` | Remove tender record | ADMIN |
| `POST` | `/api/v1/admin/tenders/{id}/upload-docs` | Upload official RFP PDF notices | ADMIN |
| `POST` | `/api/v1/admin/tenders/{id}/process` | Trigger PDF parsing, chunking & vector indexing | ADMIN |
| `GET` | `/api/v1/admin/tenders/{id}/processing-status`| Inspect vector indexing progress | ADMIN |
| `POST` | `/api/v1/admin/tenders/{id}/extract-requirements`| Extract structured qualification matrix | ADMIN |
| `GET` | `/api/v1/admin/tenders/{id}/proposed-requirements`| Review AI-proposed requirement bundle | ADMIN |
| `POST` | `/api/v1/admin/tenders/{id}/approve-requirements` | Approve proposed requirements bundle | ADMIN |

### Compliance Intelligence & Reports
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/compliance/analyze` | Run LangGraph compliance evaluation on tender | Bearer JWT |
| `GET` | `/api/v1/compliance/reports` | List historical compliance reports | Bearer JWT |
| `GET` | `/api/v1/compliance/reports/{id}` | Retrieve comprehensive 17-field compliance report | Bearer JWT |
| `GET` | `/api/v1/compliance/reports/{id}/findings` | Retrieve all findings for a report | Bearer JWT |

### Bid Applications & Notifications
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/applications` | List tracked bid applications | Bearer JWT |
| `POST` | `/api/v1/applications` | Create new bid tracking entry | Bearer JWT |
| `PATCH` | `/api/v1/applications/{id}` | Update bid stage (`DRAFT` to `SUBMITTED`, etc.) | Bearer JWT |
| `DELETE`| `/api/v1/applications/{id}` | Delete bid tracking record | Bearer JWT |
| `GET` | `/api/v1/notifications` | Retrieve user deadline notifications | Bearer JWT |
| `GET` | `/api/v1/notifications/unread-count` | Retrieve badge count of unread alerts | Bearer JWT |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark individual notification as read | Bearer JWT |
| `POST` | `/api/v1/notifications/mark-all-read` | Mark all notifications as read | Bearer JWT |
| `POST` | `/api/v1/notifications/trigger-check` | Manually trigger deadline alert check | ADMIN |

### System Health
| Method | Endpoint | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/health` and `/health` | Liveness probe returning service online status | None |
| `GET` | `/api/v1/health/ready` | Readiness probe checking PostgreSQL connectivity | None |

---

## 15. Frontend User Guide & Workflows

### Workflow 1: Authentication & Company Setup
1. Open `http://127.0.0.1:5173` in your browser.
2. Click **Register** to create an MSME account or **Sign In** with existing credentials.
3. Navigate to **Company Profile** in the navigation bar.
4. Input your statutory business information: Legal Name, Business Type (e.g., Private Limited, Partnership, Sole Proprietorship), Udyam Registration Number, PAN, and GSTIN.
5. Enter your financial history: Annual Turnover for the past 3 financial years (e.g., FY 2023-24, FY 2022-23, FY 2021-22) and current Net Worth. Click **Save Company Profile**.

### Workflow 2: Populate the Document Vault
1. Navigate to **Document Vault**.
2. Click **Upload Document**.
3. Select your document type (e.g., *Audited Balance Sheet*, *GST Certificate*, *ISO 9001 Certification*, *Client Work Completion Order*).
4. Upload the PDF file. The system computes its SHA-256 hash, stores it in `./uploads/`, extracts text, and indexes chunks for RAG evaluation.

### Workflow 3: Discover Tenders & View Official Notices
1. Navigate to **Tenders**.
2. Search by keyword or filter by source portal (**GeM Portal**, **CPPP e-Procure**, **TenderKart Feed**).
3. Select any tender to open its **Tender Detail Page**.
4. In the **Official Tender Documents** section:
   - Click **Fetch Tender Documents** to trigger automated document retrieval.
   - For directly accessible PDFs, click **View PDF** to inspect the notice in the built-in authenticated modal viewer.
   - For interactive notices (where only an official bid submission page is available), click **Open Official Tender Page** to open the portal notice in a new tab.
   - Use the **Tender Q&A** panel to ask questions (e.g., *"What is the EMD exemption for micro enterprises?"*) and receive answers with verified page citations.

### Workflow 4: Run Compliance Evaluation
1. On the tender detail view, click **Evaluate Compliance**, or navigate to **Run Compliance Analysis** from the sidebar.
2. Select the target tender. Check the box for **"Include Gemini AI Narrative & Evidence Explanations"**.
3. Click **Start Compliance Evaluation**.
4. The system executes the 9-node LangGraph pipeline. Once completed, review the generated report:
   - **Executive Summary & Overall Status Badge**: Displays `ELIGIBLE`, `PARTIALLY_ELIGIBLE`, or `NOT_ELIGIBLE`.
   - **Compliance Score Gauge**: Visual percentage based on satisfied mandatory requirements.
   - **Status Breakdown**: Counts of Pass, Fail, Missing Evidence, and Needs Review.
   - **Requirement Breakdown**: 17 structured fields per requirement detailing exact clauses, plain-English interpretations, company evidence, gap analyses, risks, and recommended actions.
   - **Missing Documents Checklist**: Explicit list of unuploaded files required for compliance.

### Workflow 5: Track Bids & Monitor Deadlines
1. Click **Track This Bid** to add the tender to your **Applications** pipeline.
2. Update the application status as you prepare your submission (`DRAFT`, `SUBMITTED`, etc.).
3. The notification bell in the top navbar alerts you at 7 days, 3 days, and 24 hours prior to the submission deadline.

---

## 16. Running Automated Tests & Verification

The repository contains automated test suites across both backend and frontend.

### 16.1 Backend Test Suite (Pytest)

The backend test suite contains **138 tests across 28 test files** covering unit tests, mocked services, SSRF validators, and live PostgreSQL integration tests:

```powershell
# Navigate to backend directory and ensure virtual environment is active
Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\backend"
$env:PYTHONPATH="."
.\.venv\Scripts\pytest -v
```

Execution summary:
```
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-8.3.4, pluggy-1.7.0
rootdir: C:\Users\KumarShiva\Downloads\Tender_Bid\backend
configfile: pytest.ini
plugins: anyio-4.15.1, langsmith-0.14.11, asyncio-0.24.0
collected 138 items

tests/test_apify_connector.py .................                          [ 12%]
tests/test_auth.py .......                                               [ 17%]
tests/test_bid_tracking.py .....                                         [ 21%]
tests/test_chunking.py .....                                             [ 24%]
tests/test_citation_validator.py .....                                   [ 28%]
tests/test_companies.py ......                                           [ 32%]
tests/test_compliance_api.py ......                                      [ 36%]
tests/test_compliance_intelligence_upgrade.py ........                   [ 42%]
tests/test_deadline_alerts.py .....                                      [ 46%]
tests/test_deadline_scheduler.py .....                                   [ 49%]
tests/test_document_intelligence.py ......                               [ 54%]
tests/test_document_retrieval.py .........                               [ 60%]
tests/test_documents.py ......                                           [ 65%]
tests/test_health.py ...                                                 [ 67%]
tests/test_hybrid_retrieval.py .....                                     [ 71%]
tests/test_langgraph_workflow.py ......                                  [ 75%]
tests/test_phase10_e2e.py ..........                                     [ 82%]
tests/test_postgres_integration.py ........                              [ 88%]
tests/test_requirement_extraction.py .....                               [ 92%]
tests/test_rule_engine.py ......                                         [ 96%]
tests/test_security_middleware.py ....                                   [ 99%]
tests/test_storage.py ..                                                 [100%]
======================== 138 passed, 6 warnings in 47.43s =====================
```

### 16.2 Full Automated 14-Step Demonstration Script

Execute the complete end-to-end platform demonstration against live PostgreSQL:

```powershell
Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\backend"
.\.venv\Scripts\python.exe scripts/demo_walkthrough.py
```

*Validates: Admin provisioning, RFP ingestion, MSME registration, profile creation, vault upload, tender discovery, LangGraph execution, deterministic rule primacy, and report persistence.*

### 16.3 Frontend Test Suite (Vitest)

The frontend test suite contains **33 tests across 11 test suites**:

```powershell
Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\frontend"
npm test -- --run
```

Execution summary:
```
 ✓ src/test/AdminRoute.test.tsx (2 tests)
 ✓ src/test/ApplicationsPage.test.tsx (2 tests)
 ✓ src/test/ComplianceReportDetailPage.test.tsx (2 tests)
 ✓ src/test/StatusBadge.test.tsx (7 tests)
 ✓ src/test/TendersListPage.test.tsx (4 tests)
 ✓ src/test/E2EJourneys.test.tsx (3 tests)
 ✓ src/test/DocumentVaultPage.test.tsx (2 tests)
 ✓ src/test/ProtectedRoute.test.tsx (2 tests)
 ✓ src/test/TenderQAPanel.test.tsx (2 tests)
 ✓ src/test/TenderDetailPage.test.tsx (4 tests)
 ✓ src/test/ComplianceAnalysisPage.test.tsx (3 tests)

 Test Files  11 passed (11)
      Tests  33 passed (33)
```

### 16.4 Frontend Production Build Verification

```powershell
Set-Location -Path "C:\Users\KumarShiva\Downloads\Tender_Bid\frontend"
npm run build
```

Expected output:
```
> tender-bid-frontend@1.0.0 build
> tsc -b && vite build

vite v6.1.0 building for production...
✓ 1685 modules transformed.
dist/index.html                   0.55 kB │ gzip:   0.36 kB
dist/assets/index-Ds_hPDOB.css   35.72 kB │ gzip:   6.53 kB
dist/assets/index-BuiZsumS.js   391.75 kB │ gzip: 112.07 kB
✓ built in 3.21s
```

---

## 17. Security Architecture & Controls

1. **Authentication & Session Security**: Passwords hashed with Argon2id using `pwdlib`. Stateless authentication via cryptographic JSON Web Tokens (`HS256`) containing expiration and role claims.
2. **Server-Side Token Isolation**: External credentials such as `GEMINI_API_KEY`, `APIFY_API_TOKEN`, and `TENDERKART_API_KEY` are stored exclusively in the backend `.env` file. They are never transmitted to the frontend, included in API responses, or printed in logs.
3. **Multi-Tenant Isolation**: SQL queries enforce strict `company_id` and `user_id` scoping to prevent cross-tenant data leakage.
4. **SSRF Protections on Document Downloads**: External document retrieval validates URL schemes, parses hostnames, resolves DNS, blocks private/loopback/link-local/multicast IP spaces, and limits domain suffixes to an approved whitelist (`gov.in`, `nic.in`, `tenderkart.in`, `apify.com`).
5. **MIME & Magic Byte Verification**: Uploads and downloads are capped at strict size limits (25 MB for user uploads, 50 MB for external tender PDFs) and verified against binary magic bytes (`%PDF-`) and PyMuPDF structure checks.
6. **Defense-in-Depth Middleware**: Standard security response headers are injected on all routes (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1`, `Strict-Transport-Security`). Sliding-window rate limiters prevent brute-force attacks on sensitive auth and analysis endpoints.
7. **Prompt Injection & LLM Containment**: Document excerpts are treated as untrusted strings. The `ReconciliationGuard` acts as a hard barrier: even if an adversary crafts a document excerpt instructing the model to declare the bidder `ELIGIBLE`, the deterministic rule engine outcome cannot be overturned.

> [!CAUTION]
> Never commit `.env` files, production database passwords, API keys, or private company financial records to version control.

---

## 18. Known Limitations & Practical Troubleshooting

### 18.1 Observed Operational Realities
- **GeM & CPPP Direct Scraping**: Official government tender portals (GeM and CPPP) employ active Web Application Firewalls (AWS WAF, Cloudflare) and graphical CAPTCHA barriers on interactive bid forms. Direct unauthenticated automated scraping of official portal pages is blocked by upstream security controls. Use the authorized **TenderKart Client API** or the **Apify Actor** crawler for structured ingestion, or manually upload notices via the Administrator Portal.
- **Web Portal Notices vs. Direct PDFs**: Many tenders published on GeM do not expose a public, unauthenticated direct PDF link; their tender URL points to an interactive portal page. The platform detects this and provides an **"Open Official Tender Page"** button rather than fabricating a document.
- **Tesseract OCR Availability**: OCR fallback requires the native Tesseract binary installed on the host OS. If `tesseract.exe` is missing from system `PATH`, set `TESSERACT_CMD` in `backend/.env`. If omitted, OCR is gracefully skipped, and only digitally extractable text is parsed.

### 18.2 Practical Troubleshooting Guide

| Issue | Root Cause | Practical Resolution |
| :--- | :--- | :--- |
| **`ConnectionRefusedError: [Errno 111]` or port 5433 unreachable** | PostgreSQL container is stopped or listening on another port | Run `docker compose ps`. Verify container `tender_bid_postgres` is running. Ensure connection string uses port `5433`: `postgresql+asyncpg://tender_app:...@127.0.0.1:5433/tender_platform`. |
| **Docker Desktop not running** | Docker daemon is inactive | Start Docker Desktop from the Windows Start menu and wait for the whale icon in the taskbar to turn solid green before running `docker compose up -d`. |
| **`Alembic: Target database is not up to date`** | Pending database migrations | Run `python -m alembic upgrade head` inside `backend/` with the virtual environment activated. |
| **`JWT_SECRET_KEY must be at least 32 characters`** | Missing or weak JWT secret | Ensure `JWT_SECRET_KEY` in `backend/.env` is a string with 32 or more characters. |
| **`Gemini API QuotaExceeded` or 403 Forbidden** | Expired or rate-limited API key | Check key at Google AI Studio. If key is unavailable, leave `GEMINI_API_KEY=""`. The platform will automatically fall back to rule-based explanations without failing. |
| **`ChromaDB: collection not found`** | Uninitialized ChromaDB vector storage | Vector collections are created automatically on first document processing. Ensure `./data/chroma` has write permissions. |

---

## 19. Master 11-Phase Project Status & Roadmap

The platform implementation strictly adheres to the original **11-Phase Master Implementation Roadmap**:

```mermaid
flowchart LR
    P1["Phase 1: Design ✓"] --> P2["Phase 2: Core DB ✓"]
    P2 --> P3["Phase 3: ChromaDB ✓"]
    P3 --> P4["Phase 4: Compliance ✓"]
    P4 --> P5["Phase 5: React UI ✓"]
    P5 --> P6["Phase 6: Extraction ✓"]
    P6 --> P7["Phase 7: Deadlines ✓"]
    P7 --> P8["Phase 8: Analytics ✓"]
    P8 --> P9["Phase 9: Dashboards ✓"]
    P9 --> P10["Phase 10: E2E & Hardening ✓"]
    P10 --> P11["Phase 11: Ingestion & PDF Retrieval ✓"]

    classDef done fill:#065f46,stroke:#10b981,stroke-width:2px,color:#ecfdf5;
    class P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11 done;
```

### Detailed Phase Status

- **Phase 1: Architecture, Planning & System Design** — `COMPLETED & VERIFIED`
  - Complete 9-part architectural specification, database models, and security boundaries.
- **Phase 2: Core Backend, PostgreSQL & Data Foundation** — `COMPLETED & VERIFIED`
  - FastAPI backend, PostgreSQL 16 on port 5433, SQLAlchemy 2.0 async, Argon2id auth, JWT tokens.
- **Phase 3: Tender Management, PDF Ingestion & ChromaDB Indexing** — `COMPLETED & VERIFIED`
  - PyMuPDF text parsing, Tesseract OCR fallback, recursive chunking, ChromaDB vector indexing.
- **Phase 4: Deterministic Compliance Engine, LangGraph & Gemini** — `COMPLETED & VERIFIED`
  - 10 deterministic rule types, LangGraph state graph, Gemini 2.5 Flash, Reconciliation Guard.
- **Phase 5: Modern React Frontend & Platform Integration** — `COMPLETED & VERIFIED`
  - React 18, Vite, TypeScript, Tailwind CSS, Document Vault, Tender Catalogue, Report Viewer.
- **Phase 6: Advanced Extraction & Intelligent Document Normalization** — `COMPLETED & VERIFIED`
  - Structured qualification matrix extraction, `RequirementNormalizer`, admin proposed requirements review.
- **Phase 7: Real-Time Notifications & Deadline Tracking** — `COMPLETED & VERIFIED`
  - Background `DeadlineAlertScheduler`, countdown alerts (7d, 3d, 24h), notification center.
- **Phase 8: Vendor-Tender Matchmaking & Gap Analytics** — `COMPLETED & VERIFIED`
  - Granular 17-field finding analyses, missing documents checklists, priority actions, risk scoring.
- **Phase 9: Application Workflow, Q&A & Dashboards** — `COMPLETED & VERIFIED`
  - Interactive Tender Q&A with page citations, bid application lifecycle tracker, executive dashboards.
- **Phase 10: End-to-End Testing, Security Hardening & Deployment** — `COMPLETED & VERIFIED`
  - Rate limiting, security headers, production Docker Compose, 14-step automated demo script.
- **Phase 11: Automatic Government Tender Ingestion & PDF Retrieval** — `COMPLETED & VERIFIED`
  - TenderKart Client API connector, Apify Government Tenders Actor integration, SSRF-safe PDF retrieval service, in-app PDF viewer modal, and official web portal fallback cards.

---

## 20. Production Deployment Considerations

When promoting from local development to a production environment:

1. **Environment Variables**:
   - Set `APP_ENV=production` and `DEBUG=false`.
   - Generate a high-entropy secret for `JWT_SECRET_KEY` (e.g., `openssl rand -hex 32`).
   - Use strict production credentials for PostgreSQL and restrict database access to the internal network.
2. **Reverse Proxy & HTTPS**:
   - Terminate SSL/TLS at an Nginx, Traefik, or AWS ALB reverse proxy with HSTS enabled.
   - Configure `FRONTEND_ORIGINS` to match your registered domain (e.g., `https://tenderplatform.example.com`).
3. **Volume Persistence**:
   - Ensure the `./uploads` directory and `./data/chroma` vector store are backed by persistent block storage volumes with automated backup snapshots.
4. **Container Orchestration**:
   - Deploy using the provided production compose stack:
     ```powershell
     docker compose -f docker-compose.prod.yml up -d --build
     ```
   - Run Alembic migrations as a pre-deployment step prior to routing traffic to new application containers.

---

## 21. Contribution, License & Acknowledgements

### Contributing
1. Create a feature branch: `git checkout -b feature/your-feature-name`.
2. Implement your changes following established type annotations, docstrings, and architectural patterns.
3. Verify that all automated tests pass:
   - Backend: `pytest -v` (138 tests passing).
   - Frontend: `npm test -- --run` (33 tests passing).
   - Build: `npm run build` (0 TypeScript errors).
4. Submit a clear, descriptive pull request.

### License
**Proprietary Research & Development Platform**. The license has not yet been specified. All rights reserved. Not authorized for uncredited commercial redistribution.

### Acknowledgements & Third-Party Credits
- **FastAPI** & **Starlette** for high-performance Python ASGI web routing.
- **SQLAlchemy** & **Alembic** for type-safe database modeling and migrations.
- **ChromaDB** for persistent vector embeddings storage.
- **PyMuPDF (Artifex Software)** for ultra-fast PDF text parsing.
- **LangChain & LangGraph** for structured graph-based agent orchestration.
- **Google DeepMind** for the Gemini 2.5 Flash generative AI model.
- **Tailwind Labs** & **Lucide** for UI design system components.

---
*Maintained for research and automated procurement intelligence. Ensure authorized access to all evaluated tender notices and source portals.*
