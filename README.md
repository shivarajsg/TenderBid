# TenderBid AI — Agentic AI-Powered Tender Intelligence & Compliance Management Platform for MSMEs

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7.2-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4.17-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.20+-FF6F61?logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.0+-2B5797?logo=diagram&logoColor=white)](https://www.langchain.com/langgraph)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-176_Passed-10B981?logo=checkmarx&logoColor=white)](https://github.com/shivarajsg/TenderBid)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/shivarajsg/TenderBid)

An enterprise-grade, full-stack intelligence and compliance automation platform engineered for Micro, Small, and Medium Enterprises (MSMEs) participating in public procurement. 

The platform centralizes tender discovery across **Government e-Marketplace (GeM)**, **Central Public Procurement Portal (CPPP)**, and state/PSU feeds, manages verified company credentials in an encrypted vault, executes deterministic compliance evaluations, retrieves document evidence via **Hybrid RAG** (PostgreSQL Full-Text Search + ChromaDB Vector Embeddings), and synthesizes audit-ready gap analyses with **Google Gemini AI** under strict mathematical supervision.

---

## Table of Contents

- [1. Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
- [2. Platform Capabilities Overview](#2-platform-capabilities-overview)
- [3. Key Architectural Features & Differentiators](#3-key-architectural-features--differentiators)
  - [3.1 Deterministic Compliance Engine vs. AI Explanation Layer](#31-deterministic-compliance-engine-vs-ai-explanation-layer)
  - [3.2 Hybrid RAG Pipeline & Reciprocal Rank Fusion (RRF)](#32-hybrid-rag-pipeline--reciprocal-rank-fusion-rrf)
  - [3.3 LangGraph 9-Node Stateful Orchestration Graph](#33-langgraph-9-node-stateful-orchestration-graph)
  - [3.4 In-App Document Inspection & Grounded Tender Q&A](#34-in-app-document-inspection--grounded-tender-qa)
  - [3.5 MSME Company Capability & Compliance Profile](#35-msme-company-capability--compliance-profile)
  - [3.6 Multi-Portal Ingestion & GeM Crawl Transparency](#36-multi-portal-ingestion--gem-crawl-transparency)
  - [3.7 Autonomous Bid Pipeline & Deadline Alerting](#37-autonomous-bid-pipeline--deadline-alerting)
- [4. Technology Stack](#4-technology-stack)
- [5. System Architecture](#5-system-architecture)
- [6. Repository Structure](#6-repository-structure)
- [7. Prerequisites](#7-prerequisites)
- [8. Local Installation & Setup Guide](#8-local-installation--setup-guide)
- [9. Environment Variables & Configuration](#9-environment-variables--configuration)
- [10. Database Schema & Storage Architecture](#10-database-schema--storage-architecture)
- [11. Deterministic Compliance Engine Invariants](#11-deterministic-compliance-engine-invariants)
- [12. Complete API Reference](#12-complete-api-reference)
- [13. Frontend User Guide & Workflows](#13-frontend-user-guide--workflows)
- [14. Automated Test Suites & Verification](#14-automated-test-suites--verification)
- [15. Security Architecture & Controls](#15-security-architecture--controls)
- [16. Troubleshooting & Operational Guidance](#16-troubleshooting--operational-guidance)
- [17. Master 11-Phase Project Roadmap](#17-master-11-phase-project-roadmap)
- [18. Production Deployment Guide](#18-production-deployment-guide)
- [19. License & Acknowledgements](#19-license--acknowledgements)

---

## 1. Executive Summary & Problem Statement

Public procurement in India through platforms such as the **Government e-Marketplace (GeM)**, **Central Public Procurement Portal (CPPP)**, state portals, and Public Sector Undertakings (PSUs) represents an enormous market opportunity. However, Micro, Small, and Medium Enterprises (MSMEs) face severe structural barriers when bidding for government contracts:

1. **Information Asymmetry & Manual Overhead**: Requests for Proposals (RFPs), General Conditions of Contract (GCC), and Special Conditions of Contract (SCC) frequently span 50 to 300+ pages of dense legal, financial, and technical clauses. MSMEs lack the dedicated bid management teams required to parse these notices.
2. **Strict Disqualification Rules**: Government tenders enforce strict pre-qualification criteria (annual turnover thresholds over consecutive financial years, past experience with similar work orders, ISO/technical certifications, Earnest Money Deposit (EMD) requirements, and mandatory statutory filings). A single missing document or miscalculated turnover average results in summary disqualification.
3. **Severe Verification Friction**: Bidders must verify their internal records (audited balance sheets, GST returns, PAN, Udyam certificates, client completion certificates) against tender requirements without knowing beforehand whether they meet all mandatory conditions.
4. **Tight Submission Deadlines**: Bidders frequently discover tenders late, leaving inadequate time to gather notarized affidavits, obtain bank guarantees, or clarify ambiguities through pre-bid queries.

### Purpose of this Platform

**TenderBid AI** resolves these challenges by combining **deterministic mathematical rule validation** with **Retrieval-Augmented Generation (RAG)** and **stateful agentic AI workflows**:

- **Centralizes procurement discovery** across GeM, CPPP, and open public procurement feeds with automated sync.
- **Maintains an encrypted corporate document vault** for tax certificates, financial balance sheets, and client work orders.
- **Evaluates objective financial, technical, and statutory eligibility** using strict Python business rules that cannot be hallucinated or overturned by AI.
- **Leverages Google Gemini** to synthesize plain-English explanations, risk summaries, and missing-evidence checklists grounded strictly in document citations.
- **Provides an interactive, document-grounded Tender Q&A assistant** that answers bidder queries with exact page numbers and verbatim quotations.
- **Tracks bids through an end-to-end pipeline** and autonomously alerts users before critical submission cutoffs.

> [!NOTE]
> **Academic & Evaluative Context**: This platform is designed for research, technical portfolio demonstration, and pre-production evaluation. Compliance evaluations are decision-support aids based on parsed documentation and do not guarantee government tender qualification or contract awards.

---

## 2. Platform Capabilities Overview

| Capability | Module / Component | Implementation Status |
| :--- | :--- | :--- |
| **Authentication & RBAC** | `app.core.security`, `app.api.routes.auth` | Implemented (Argon2id, JWT HS256, `ADMIN` & `MSME_USER` roles) |
| **Comprehensive MSME Profile** | `app.api.routes.companies`, `CompanyService` | Implemented (10-tab capability statement, 7-category readiness score 0–100%) |
| **Encrypted Document Vault** | `app.api.routes.documents`, `DocumentService` | Implemented (MIME checking, SHA-256 deduplication, file storage) |
| **Tender Catalogue & Filtering** | `app.api.routes.tenders`, `TenderService` | Implemented (Search, sector filters, source tabs, sticky compressed controls) |
| **Automated Tender Ingestion** | `app.services.ingestion`, `IngestionScheduler` | Implemented (GeM live catalog crawler, TenderKart API, Apify Actor) |
| **SSRF-Safe PDF Retrieval** | `app.services.document_retrieval_service` | Implemented (DNS rebinding guard, 50MB cap, magic byte verification) |
| **In-App PDF Viewer Modal** | `frontend/src/pages/tenders/TenderDetailPage` | Implemented (Authenticated blob stream, object URLs, zero file leakage) |
| **Grounded Tender Q&A Assistant** | `app.services.retrieval.tender_qa_service` | Implemented (Semantic search over indexed chunks with exact page citations) |
| **PDF Extraction & OCR Fallback** | `app.services.extraction_service`, `ocr_service` | Implemented (PyMuPDF high-speed parser + Tesseract OCR fallback) |
| **Recursive Text Chunking** | `app.services.chunking_service` | Implemented (1000 char chunks, 200 overlap, physical page tracking) |
| **Hybrid RAG Pipeline** | `app.services.retrieval.hybrid_retriever` | Implemented (PostgreSQL FTS + ChromaDB cosine similarity, RRF $k=60$) |
| **Deterministic Compliance Engine** | `app.services.compliance.rule_engine` | Implemented (10 rule types, pure Python math, zero LLM hallucination) |
| **LangGraph 9-Node Orchestrator** | `app.services.workflows.compliance_graph` | Implemented (Stateful compiled workflow, transaction boundaries, rollback) |
| **Gemini AI Evidence Explanations** | `app.services.ai.compliance_analyzer` | Implemented (Google Gemini 2.5 Flash, structured 17-field findings) |
| **Deterministic Primacy Guard** | `app.services.compliance.reconciliation_guard` | Implemented (Hard security barrier preventing AI from mutating rule decisions) |
| **Bid Pipeline & Lifecycle Tracking**| `app.api.routes.bid_applications`, `BidTrackingService`| Implemented (Stages: `DRAFT`, `SUBMITTED`, `UNDER_EVALUATION`, `AWARDED`, `REJECTED`) |
| **Proactive Deadline Alerts** | `app.services.deadline_scheduler`, `alert_service` | Implemented (Background asyncio worker, in-app bell dropdown, 7d/3d/24h triggers) |

---

## 3. Key Architectural Features & Differentiators

### 3.1 Deterministic Compliance Engine vs. AI Explanation Layer

A foundational architectural invariant of the platform is **Deterministic Supremacy**:

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
   - The LLM receives the rule outcome, requirement clauses, and retrieved document chunks.
   - It drafts plain-English interpretations, summarizes risk consequences, and suggests actionable remediation steps.
   - The **Reconciliation Guard** (`ReconciliationGuard`) intercepts the AI response. If the AI claims an MSME is compliant when the rule engine marked it `FAIL`, the system rejects the AI mutation, logs a security warning, and preserves the deterministic `FAIL`.

---

### 3.2 Hybrid RAG Pipeline & Reciprocal Rank Fusion (RRF)

Standard vector search frequently struggles with exact alphanumeric identifiers common in government tenders (e.g., `GEM/2026/B/8071017`, `Clause 4.14.2(b)`, `ISO/IEC 27001:2022`). Conversely, keyword search misses semantic synonyms. The platform implements **Reciprocal Rank Fusion (RRF)** combining both retrieval paradigms:

1. **Lexical Search (PostgreSQL)**:
   - Evaluates full-text search vectors generated from indexed document chunks (`DocumentChunkModel`).
   - Uses PostgreSQL `websearch_to_tsquery` or `plainto_tsquery` matching against English dictionary text search vectors (`to_tsvector('english', chunk_text)`).
2. **Semantic Search (ChromaDB)**:
   - Uses deep vector embeddings stored in isolated ChromaDB collections (`tender_documents` and `company_documents`).
   - Executes cosine similarity matching against the user's requirement or query text.
3. **Reciprocal Rank Fusion Formula**:
   For each retrieved document chunk $d$, its fused score is calculated as:
   $$RRF(d) = \sum_{m \in \{\text{lexical}, \text{semantic}\}} \frac{w_m}{k + \text{rank}_m(d)}$$
   where $k = 60$ (smoothing constant), $w_{\text{semantic}} = 0.6$, and $w_{\text{lexical}} = 0.4$.
4. **Citation Verification**:
   The `CitationValidator` verifies that every chunk referenced in the evaluation genuinely exists in the database and matches the target tender or company scope before citations are presented to the user.

---

### 3.3 LangGraph 9-Node Stateful Orchestration Graph

Compliance analysis is coordinated by a stateful, compiled **LangGraph** workflow (`ComplianceWorkflowOrchestrator` in [`compliance_graph.py`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/backend/app/services/workflows/compliance_graph.py)):

```mermaid
graph TD
    START([Start]) --> N1["1. input_validation"]
    N1 --> N2["2. load_context"]
    N2 --> N3["3. validate_requirements"]
    N3 --> N4["4. deterministic_checks"]
    N4 --> N5["5. hybrid_retrieval"]
    N5 --> N6["6. evidence_analysis"]
    N6 --> N7["7. reconciliation_guard"]
    N7 --> N8["8. report_synthesis"]
    N8 --> N9["9. persist_report"]
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

---

### 3.4 In-App Document Inspection & Grounded Tender Q&A

- **SSRF Protection Engine**: When fetching tender documents from external URLs, the service validates IP addresses against DNS rebinding, blocks private/loopback/link-local/multicast IP spaces, and strictly limits domains to an approved whitelist (`*.gov.in`, `*.nic.in`, `tenderkart.in`, `apify.com`).
- **Magic Byte Validation**: Streams external HTTP responses, rejects files exceeding 50 MB, and verifies the `%PDF-` binary magic bytes.
- **In-App PDF Viewer Modal**: Users inspect tender notices directly inside the browser using an authenticated inline stream (`GET /api/v1/tenders/{tender_id}/documents/{document_id}/view`) loaded via secure object URLs (`<iframe src={blobUrl}>`), eliminating unauthenticated local file downloads.
- **Grounded Tender Q&A**: An interactive panel on the tender detail view allows users to ask questions (e.g., *"What is the minimum annual turnover required?"*, *"Is Earnest Money Deposit (EMD) exempt for MSMEs?"*). The system retrieves the most relevant indexed chunks from the tender's official files, feeds them to Gemini with strict grounding instructions, and returns an answer complete with exact document name, page number, and verbatim quotation.

---

### 3.5 MSME Company Capability & Compliance Profile

The platform includes a modular, 10-tab enterprise capability management system:

1. **Overview & Objective Readiness Scoring (0–100%)**:
   - Evaluates profile readiness across 7 weighted categories:
     - Identity & Legal Registrations (15%)
     - Financial Capability & Turnover (25%)
     - Technical Capabilities & Offerings (15%)
     - Quality Certifications & Standards (15%)
     - Past Experience & Work Orders (15%)
     - Workforce & Operational Capacity (5%)
     - Statutory Declarations & MSME Exemptions (10%)
   - Surfaces prioritized gap cards with actionable remediation links.
2. **Sanitized Numeric Safeguards**: Enforces strict positive numeric values, rejects scientific notation strings (e.g., `1e+25`), sanitizes comma-delimited currency entries, and caps amounts at realistic enterprise thresholds (₹10,000 Crore).
3. **Formal Capability Statement Generator**: Dynamically generates executive narrative summaries, multi-year turnover tables, 3-year averages, solvency indicators, and statutory compliance declarations ready for inclusion in bid proposals.

---

### 3.6 Multi-Portal Ingestion & GeM Crawl Transparency

The background ingestion framework (`app.services.ingestion`) supports multiple public procurement data providers:

- **GeM Live Catalog Pagination**: Crawls live tender listings from the Government e-Marketplace with bounded batching, checkpoint cursors, and real-time frontend discovery transparency metrics:
  - Total GeM Portal Records
  - Pages Processed & Range ($p.\text{start}–p.\text{end}$)
  - Live Bids Discovered
  - New Ingested vs. Updated vs. Duplicates Skipped
- **TenderKart Client API**: Integrates with `https://tenderkart.in/api/v1/client`, supporting saved filter discovery (`GET /filters`), cursor-based incremental sync with `sync.next_updated_after` checkpoints, and automated rate limiting (30 req/min with RFC `Retry-After` backoff).
- **Apify Cloud Actor**: Dispatches scraping jobs to the Apify actor `foxlabs/india-government-tenders` or `fascinating_lentil~india-government-tenders-scraper` via backend-only token authentication.

---

### 3.7 Autonomous Bid Pipeline & Deadline Alerting

- **Application Lifecycle**: Tracks internal bid preparation across defined stages (`DRAFT`, `SUBMITTED`, `UNDER_EVALUATION`, `AWARDED`, `REJECTED`) with tracking notes and deadline timestamps.
- **Autonomous Deadline Alert Scheduler**: An asyncio worker (`DeadlineAlertScheduler`) running within the FastAPI lifespan inspects active tenders every 300 seconds. It calculates remaining hours until submission cutoffs and generates in-app `Notification` records at 7 days, 3 days, and 24 hours prior to deadline.

---

## 4. Technology Stack

### Backend
- **Python 3.13**: Modern async runtime with typed dataclasses.
- **FastAPI (0.115.5)**: High-performance async ASGI web framework for REST APIs and OpenAPI docs.
- **Uvicorn (0.32.1)**: Production-grade ASGI web server.
- **SQLAlchemy (2.0.36)**: Modern async ORM utilizing `asyncpg` for PostgreSQL connection pooling.
- **Alembic (1.14.0)**: Versioned, zero-downtime database schema migration engine.
- **PostgreSQL 16**: Relational database managing users, companies, tenders, documents, compliance reports, and full-text search indexes.
- **ChromaDB (0.5.20+)**: Persistent vector database managing embeddings with cosine similarity querying.
- **LangGraph (0.2.0+) & LangChain Core (0.3.0+)**: Graph-based state machine orchestrating multi-step compliance evaluations.
- **Google GenAI SDK (0.1.0+)**: Official SDK connecting to **Google Gemini 2.5 Flash** for natural language synthesis.
- **PyMuPDF (fitz 1.24.14+)**: Ultra-fast PDF parsing engine extracting text, metadata, and physical page numbers.
- **Pytesseract (0.3.13) & Pillow (11.0.0)**: Optical Character Recognition (OCR) fallback for scanned PDFs.
- **Pwdlib (Argon2id)** & **PyJWT (2.10.0)**: High-entropy password hashing and cryptographic JSON Web Token signing.
- **HTTPX (0.28.1)**: Async HTTP client for SSRF-protected external document retrieval.

### Frontend
- **React (18.3.1)**: Declarative component framework utilizing modern React hooks.
- **TypeScript (5.7.2)**: Static type safety across all UI models, API responses, and route configurations.
- **Vite (6.1.0+)**: Modern build tool and ESM development server with optimized rollup bundling.
- **Tailwind CSS (3.4.17)**: Utility-first CSS framework providing a responsive, professional design system.
- **React Router DOM (6.29.0)**: Client-side routing with protected layout wrappers and role-based guards.
- **Lucide React (0.475.0)**: Clean, consistent outline icon library.
- **Axios (1.7.9)**: HTTP client with automatic JWT bearer token injection.

### Testing Infrastructure
- **Pytest (8.3.4) & Pytest-Asyncio (0.24.0)**: 138 backend tests across 28 files (unit, mock, and PostgreSQL integration).
- **Vitest (3.2.7)**: 38 frontend tests across 11 test suites with JSDOM simulation.
- **Playwright (1.64.1)**: End-to-end browser automation framework running headless Chromium journeys.
- **Docker & Docker Compose**: Local PostgreSQL database orchestration on dedicated port 5433.

---

## 5. System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["Frontend Client Layer (React 18 + TypeScript + Vite)"]
        UI_User["MSME Bidder / Manager"]
        UI_Admin["Platform Administrator"]
        ReactApp["React SPA<br/>(Tailwind CSS + React Router v6)"]
        PDF_Viewer["In-App PDF Viewer Modal<br/>(Authenticated Blob Stream)"]
        QA_Panel["Tender Q&A Assistant<br/>(Grounded Document Citations)"]
        UI_User --> ReactApp
        UI_Admin --> ReactApp
        ReactApp -.-> PDF_Viewer
        ReactApp -.-> QA_Panel
    end

    subgraph SecurityLayer ["FastAPI Boundary & Security Middleware"]
        ReverseProxy["Reverse Proxy / Vite Dev Server"]
        FastAPI_App["FastAPI REST Application (app.main:app)"]
        SecHeaders["SecurityHeadersMiddleware<br/>(HSTS, CSP, X-Frame-Options)"]
        RateLimiter["InMemoryRateLimiter<br/>(Auth: 60/m, Analysis: 30/m)"]
        JWT_Auth["JWT Authentication & RBAC<br/>(Argon2id + Bearer Guard)"]
        
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
├── docs/                              # System documentation & phase verification reports
│   ├── AI_RAG_ARCHITECTURE.md
│   ├── API_SPECIFICATION.md
│   ├── DATABASE_SCHEMA.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── PHASE_10_VERIFICATION_REPORT.md
│   ├── PHASE_11_TENDER_INGESTION_REPORT.md
│   └── PROJECT_AS_BUILT_AUDIT.md
│
├── backend/                           # FastAPI Backend Application
│   ├── alembic/                       # Database migration scripts
│   │   ├── versions/                  # Applied schema revisions
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
    ├── public/images/                 # Vector illustrations & cached static assets
    ├── src/                           # Frontend application source code
    │   ├── api/                       # Axios typed API client modules
    │   ├── components/                # Reusable UI components & layouts
    │   │   ├── common/                # Navbar, Button, Input, Modal, ErrorAlert
    │   │   ├── layout/                # AppLayout, Sidebar, ProtectedRoute, AdminRoute
    │   │   └── tenders/               # TenderQAPanel, InAppPDFViewer
    │   ├── context/                   # React AuthContext for JWT session state
    │   ├── pages/                     # Full-page route views
    │   │   ├── admin/                 # AdminTendersPage, AdminTenderFormPage
    │   │   ├── applications/          # ApplicationsPage (Bid Tracker)
    │   │   ├── auth/                  # LoginPage, RegisterPage
    │   │   ├── company/               # CompanyProfilePage (10-tab capability statement)
    │   │   ├── compliance/            # ComplianceAnalysisPage, ReportDetailPage
    │   │   ├── dashboard/             # DashboardPage (Fitted single-page overview)
    │   │   ├── tenders/               # TendersListPage (Sticky controls), TenderDetailPage
    │   │   └── vault/                 # DocumentVaultPage
    │   ├── test/                      # Frontend Vitest test suite (38 tests across 11 files)
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

| Prerequisite | Minimum Version | Verified Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11, macOS, or Linux | Windows 11 / Ubuntu 22.04 | Workstation or server host |
| **Python** | 3.11+ | **3.13.1** | Backend application runtime |
| **Node.js** | 20.0+ | **20.18.0** | Frontend build tool & runtime |
| **npm** | 10.0+ | **10.8.2** | Package dependency manager |
| **Docker Engine** | 24.0+ | **Docker Engine 27+** | Local isolated PostgreSQL 16 container |
| **Tesseract OCR** *(Optional)* | 5.0+ | 5.3.3 | Scanned PDF optical character recognition |
| **Google Gemini Key** *(Optional)*| API v1/v1beta | Gemini 2.5 Flash | AI-powered narrative analysis & explanations |
| **Apify API Token** *(Optional)* | API v2 | Apify Actor Token | External government tender ingestion crawler |

> [!NOTE]
> The platform operates fully offline using deterministic rules and local RRF retrieval even if `GEMINI_API_KEY` or `APIFY_API_TOKEN` are omitted.

---

## 8. Local Installation & Setup Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/shivarajsg/TenderBid.git
cd TenderBid
```

### Step 2: Start the PostgreSQL Database Container

The local environment uses Docker Compose to run PostgreSQL 16 Alpine. The host port is mapped to **`5433`** to prevent collisions with any existing local PostgreSQL service running on standard port `5432`:

```bash
# Start PostgreSQL container in background
docker compose up -d postgres

# Verify that the container is healthy and listening on port 5433
docker compose ps
```

### Step 3: Configure and Initialize the Python Backend

```bash
cd backend

# Create and activate a Python 3.13 virtual environment
# Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
# python3 -m venv .venv
# source .venv/bin/activate

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Configure backend environment
cp .env.example .env

# Apply database migrations
python -m alembic upgrade head

# (Optional) Provision an initial Platform Administrator
python -m app.cli create-admin --email admin@tenderbid.internal --full-name "Platform Administrator" --password "AdminSecret2026!"

# Start the FastAPI development server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Documentation (Swagger)**: `http://127.0.0.1:8000/docs`
- **Alternative Documentation (ReDoc)**: `http://127.0.0.1:8000/redoc`
- **Backend Health Check**: `http://127.0.0.1:8000/api/v1/health`

### Step 4: Configure and Start the React Frontend

Open a new terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Configure frontend environment
cp .env.example .env.development

# Start Vite development server
npm run dev
```

Open your browser and navigate to: **`http://127.0.0.1:5173`**

---

## 9. Environment Variables & Configuration

Key configuration parameters managed in `backend/.env`:

| Variable | Description | Required? | Default / Example Value |
| :--- | :--- | :---: | :--- |
| `DATABASE_URL` | Async PostgreSQL connection string | **Yes** | `postgresql+asyncpg://tender_app:tender_dev_secret_2026@127.0.0.1:5433/tender_platform` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing JWT tokens ($\ge 32$ chars) | **Yes** | `tender_bid_development_jwt_secret_key_super_secure_min_32_bytes` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of authentication session tokens | No | `60` |
| `UPLOAD_DIR` | Protected file storage directory for PDFs and credentials | No | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed file upload size in megabytes | No | `25` |
| `TESSERACT_CMD` | Path to `tesseract.exe` for optical character recognition | No | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `CHROMA_PERSIST_DIRECTORY` | On-disk storage path for persistent vector embeddings | No | `./data/chroma` |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini LLM analysis | Optional | `AIzaSy...` *(Leave empty for rule-only fallback)* |
| `GEMINI_MODEL` | Gemini LLM model identifier | No | `gemini-2.5-flash` |
| `DEADLINE_ALERT_ENABLED` | Enable automated background deadline alert scanning | No | `true` |
| `DEADLINE_ALERT_INTERVAL_SECONDS`| Frequency in seconds for checking tender deadlines | No | `300` |
| `INGESTION_ENABLED` | Enable automated background government tender ingestion | No | `true` |
| `INGESTION_INTERVAL_SECONDS` | Frequency in seconds between tender ingestion runs | No | `3600` |
| `TENDERKART_ENABLED` | Enable TenderKart third-party tender data connector | No | `true` |
| `MAX_DOCUMENT_DOWNLOAD_BYTES` | Maximum allowed tender PDF download size | No | `52428800` (50 MB) |
| `ALLOWED_DOCUMENT_DOMAINS` | Whitelisted domain suffixes for secure document downloads | No | `gov.in,nic.in,tenderkart.in,apify.com` |

---

## 10. Database Schema & Storage Architecture

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
                   │                                  │ technical_capabilities (JSONB)  │
                   │                                  │ declarations (JSONB)            │
                   │ 1                                └───────────────┬─────────────────┘
                   ▼ N                                                │ 1
  ┌─────────────────────────────────┐                                 ▼ N
  │          notifications          │                 ┌─────────────────────────────────┐
  ├─────────────────────────────────┤                 │            documents            │
  │ id (PK, UUID)                   │                 ├─────────────────────────────────┤
  │ user_id (FK, UUID)              │                 │ id (PK, UUID)                   │
  │ tender_id (FK, Nullable, UUID)  │                 │ company_id (FK, Nullable, UUID) │
  │ title, message (String)         │                 │ tender_id (FK, Nullable, UUID)  │
  │ notification_type (String)      │                 │ storage_path (String)           │
  │ is_read (Boolean)               │                 │ sha256_hash (String)            │
  └─────────────────────────────────┘                 │ processing_status (String)      │
                                                      └───────────────┬─────────────────┘
                                                                      │ 1
                                                                      ▼ N
                                                      ┌─────────────────────────────────┐
                                                      │         document_chunks         │
                                                      ├─────────────────────────────────┤
                                                      │ id (PK, UUID)                   │
                                                      │ document_id (FK, UUID)          │
                                                      │ chunk_text (Text)               │
                                                      │ page_number (Integer)           │
                                                      │ tsv (TSVector, Full-Text Index) │
                                                      └─────────────────────────────────┘
```

---

## 11. Deterministic Compliance Engine Invariants

The deterministic compliance engine (`app.services.compliance.rule_engine`) guarantees:

1. **Non-Overridable Mathematical Integrity**:
   - Every financial threshold is evaluated via exact decimal comparisons.
   - Years in business are derived strictly from verified registration dates:
     $$\Delta t = \frac{\text{Tender Posting Date} - \text{Incorporation Date}}{365.25}$$
   - Set membership (certifications, statutory numbers) requires exact matching ($C_{\text{required}} \subseteq C_{\text{company}}$).
2. **Deterministic Primacy Enforcement**:
   - The `ReconciliationGuard` compares the raw rule engine output against the AI-generated narrative.
   - If Google Gemini returns an `ELIGIBLE` status for a clause where the rule engine computed `FAIL`, the guard forcibly discards the AI status mutation and preserves the deterministic `FAIL`.

---

## 12. Complete API Reference

### Authentication & Authorization
| Method | Endpoint | Summary | Access |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/register` | Register new MSME user account | Public |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access token | Public |
| `GET` | `/api/v1/auth/me` | Retrieve authenticated user profile and role | Bearer JWT |

### MSME Company Profile & Vault
| Method | Endpoint | Summary | Access |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/company/profile` | Retrieve MSME corporate profile & metrics | Bearer JWT |
| `POST` | `/api/v1/company/profile` | Create company profile | Bearer JWT |
| `PUT` | `/api/v1/company/profile` | Update corporate profile & credentials | Bearer JWT |
| `GET` | `/api/v1/company/readiness-score` | Retrieve 7-category readiness score & gaps | Bearer JWT |
| `GET` | `/api/v1/company/capability-statement`| Generate formal capability statement | Bearer JWT |
| `GET` | `/api/v1/company/vault/documents` | List verified credentials in vault | Bearer JWT |
| `POST` | `/api/v1/company/vault/documents/upload` | Upload new document to vault | Bearer JWT |
| `DELETE`| `/api/v1/company/vault/documents/{id}` | Remove document from vault | Bearer JWT |

### Tenders & Document Intelligence
| Method | Endpoint | Summary | Access |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/tenders` | Search & filter tenders (paginated, by portal) | Bearer JWT |
| `GET` | `/api/v1/tenders/{id}` | Retrieve tender details, requirements, docs | Bearer JWT |
| `POST` | `/api/v1/tenders/{id}/fetch-documents`| Download official tender PDFs | Bearer JWT |
| `GET` | `/api/v1/tenders/{id}/documents/{doc_id}/view`| Stream tender PDF inline for browser viewer | Bearer JWT |
| `POST` | `/api/v1/tenders/{id}/qa` | Grounded Tender Q&A with exact page citations | Bearer JWT |
| `GET` | `/api/v1/tenders/ingestion/status` | Retrieve status of live catalog crawls | Bearer JWT |
| `POST` | `/api/v1/tenders/ingestion/sync` | Trigger manual tender ingestion sync | ADMIN |

### Compliance Intelligence & LangGraph Workflow
| Method | Endpoint | Summary | Access |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/compliance/analyze` | Execute LangGraph compliance evaluation | Bearer JWT |
| `GET` | `/api/v1/compliance/reports` | List historical compliance reports | Bearer JWT |
| `GET` | `/api/v1/compliance/reports/{id}` | Retrieve comprehensive compliance report | Bearer JWT |

### Bid Tracking & Deadline Alerts
| Method | Endpoint | Summary | Access |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/applications` | List tracked bids in pipeline | Bearer JWT |
| `POST` | `/api/v1/applications` | Track new tender in pipeline | Bearer JWT |
| `PATCH` | `/api/v1/applications/{id}` | Update application stage (`DRAFT` to `SUBMITTED`)| Bearer JWT |
| `GET` | `/api/v1/notifications` | Retrieve deadline countdown notifications | Bearer JWT |
| `PATCH` | `/api/v1/notifications/{id}/read`| Mark alert as read | Bearer JWT |

---

## 13. Frontend User Guide & Workflows

### 1. Dashboard Overview
- Fits within a single cohesive screen without vertical scrollbars on standard 1080p desktop and laptop displays.
- Visualizes 4 active KPIs (Active Opportunities, Vault Documents, Compliance Reports, Eligible Tenders).
- 5-step guided workflow stepper with connecting direction arrows.
- Tabular recent compliance reports, key features breakdown, and getting-started guide.

### 2. Tender Discovery & Ingestion
- Filter across official government feeds (**GeM Portal**, **CPPP e-Procure**, **Open Gov PSU**, **TenderKart Feed**, **Direct Notices**).
- Sticky compressed search controls stay pinned at the top during scrolling.
- Real-time GeM live crawl transparency metrics show catalog records, page ranges, and newly ingested counts.

### 3. Tender Detail & Document Inspection
- View official tender metadata, issuing authority, submission deadlines, and categorizations.
- Click **Fetch Tender Documents** to automatically retrieve official bid specifications.
- Click **View PDF** to inspect documents in the secure in-app modal viewer without leaving the browser.
- Open the **Tender Q&A** panel to ask natural language questions and review grounded answers with page numbers and quotations.

### 4. Running Compliance Analysis
- Navigate to **Evaluate Tender**, select any tender notice, and choose whether to include Gemini AI explanations.
- The 9-node LangGraph orchestrator parses clauses, checks verified credentials against requirements, executes hybrid RRF retrieval, prompts Gemini, and enforces deterministic supremacy.
- The resulting report displays overall score, eligibility badge (`ELIGIBLE`, `PARTIALLY_ELIGIBLE`, `NOT_ELIGIBLE`), granular 17-field findings, and a missing documents checklist.

---

## 14. Automated Test Suites & Verification

### Backend Tests (Pytest)
```bash
cd backend
python -m pytest -v
```
**138 tests across 28 files passed** (including unit, mock, SSRF protection, LangGraph workflow, and PostgreSQL integration tests).

### Frontend Tests (Vitest)
```bash
cd frontend
npm test -- --run
```
**38 tests across 11 test suites passed** (covering auth guards, route protections, compliance reports, tender listing, document vault, and Tender Q&A).

### Frontend Production Build
```bash
cd frontend
npm run build
```
Compiled cleanly with Vite and TypeScript compiler with 0 errors.

---

## 15. Security Architecture & Controls

1. **Authentication & Session Security**: Passwords hashed with Argon2id using `pwdlib`. Stateless authentication via cryptographic JSON Web Tokens (`HS256`).
2. **Server-Side Token Isolation**: External credentials such as `GEMINI_API_KEY`, `APIFY_API_TOKEN`, and `TENDERKART_API_KEY` are stored exclusively in the backend `.env` file. They are never exposed to the client.
3. **Multi-Tenant Isolation**: SQL queries enforce strict `company_id` and `user_id` scoping to prevent cross-tenant data leakage.
4. **SSRF Protections on Document Downloads**: External document retrieval validates URL schemes, parses hostnames, resolves DNS, blocks private/loopback/link-local/multicast IP spaces, and limits domain suffixes to an approved whitelist (`gov.in`, `nic.in`, `tenderkart.in`, `apify.com`).
5. **MIME & Magic Byte Verification**: Uploads and downloads are capped at strict size limits (25 MB for user uploads, 50 MB for external tender PDFs) and verified against binary magic bytes (`%PDF-`).
6. **Defense-in-Depth Middleware**: Standard security response headers are injected on all routes (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1`, `Strict-Transport-Security`). Sliding-window rate limiters prevent brute-force attacks.
7. **Prompt Injection & LLM Containment**: Document excerpts are treated as untrusted strings. The `ReconciliationGuard` acts as a hard barrier: even if an adversary crafts a document excerpt instructing the model to declare the bidder `ELIGIBLE`, the deterministic rule engine outcome cannot be overturned.

---

## 16. Troubleshooting & Operational Guidance

| Issue | Root Cause | Practical Resolution |
| :--- | :--- | :--- |
| **`ConnectionRefusedError: [Errno 111]` or port 5433 unreachable** | PostgreSQL container is stopped | Run `docker compose ps`. Verify container `tender_bid_postgres` is running. Ensure connection string uses port `5433`. |
| **Docker Desktop not running** | Docker daemon is inactive | Start Docker Desktop from the Start menu before running `docker compose up -d`. |
| **`Alembic: Target database is not up to date`** | Pending migrations | Run `python -m alembic upgrade head` in `backend/` with the virtual environment activated. |
| **`JWT_SECRET_KEY must be at least 32 characters`** | Missing or weak JWT secret | Ensure `JWT_SECRET_KEY` in `backend/.env` is a string with 32 or more characters. |
| **`Gemini API QuotaExceeded` or 403 Forbidden** | Expired or rate-limited API key | Leave `GEMINI_API_KEY=""`. The platform will automatically fall back to rule-based explanations without failing. |
| **`ChromaDB: collection not found`** | Uninitialized ChromaDB storage | Vector collections are created automatically on first document processing. Ensure `./data/chroma` has write permissions. |

---

## 17. Master 11-Phase Project Roadmap

```mermaid
flowchart LR
    P1["Phase 1: Architecture ✓"] --> P2["Phase 2: PostgreSQL ✓"]
    P2 --> P3["Phase 3: ChromaDB ✓"]
    P3 --> P4["Phase 4: Rule Engine ✓"]
    P4 --> P5["Phase 5: React UI ✓"]
    P5 --> P6["Phase 6: Matrix Extraction ✓"]
    P6 --> P7["Phase 7: Deadlines ✓"]
    P7 --> P8["Phase 8: Gap Analytics ✓"]
    P8 --> P9["Phase 9: Tender Q&A ✓"]
    P9 --> P10["Phase 10: E2E Hardening ✓"]
    P10 --> P11["Phase 11: Live Ingestion ✓"]

    classDef done fill:#065f46,stroke:#10b981,stroke-width:2px,color:#ecfdf5;
    class P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11 done;
```

All 11 phases are **fully implemented and verified**.

---

## 18. Production Deployment Guide

Deploy using the provided multi-stage production container stack:

```bash
# Build and run production containers
docker compose -f docker-compose.prod.yml up -d --build

# Run Alembic migrations in production container
docker compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
```

---

## 19. License & Acknowledgements

### License
**Proprietary Research & Development Platform**. All rights reserved.

### Acknowledgements & Third-Party Credits
- **FastAPI** & **Starlette** for high-performance Python ASGI web routing.
- **SQLAlchemy** & **Alembic** for type-safe database modeling and migrations.
- **ChromaDB** for persistent vector embeddings storage.
- **PyMuPDF (Artifex Software)** for ultra-fast PDF text parsing.
- **LangChain & LangGraph** for structured graph-based agent orchestration.
- **Google DeepMind** for the Gemini 2.5 Flash generative AI model.
- **Tailwind Labs** & **Lucide** for UI design system components.
