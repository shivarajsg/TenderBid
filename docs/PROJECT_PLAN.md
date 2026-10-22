# Project Plan: Agentic AI-Powered Tender Intelligence & Compliance Management Platform for MSMEs

## 1. Executive Summary & Problem Statement

Micro, Small, and Medium Enterprises (MSMEs) form the backbone of modern industrial economies, contributing significantly to manufacturing output, employment, and exports. Despite preferential procurement policies designed to support them (such as purchase preferences and earnest money deposit exemptions), MSMEs face steep operational barriers when bidding on public and enterprise tenders:

1. **Information Asymmetry & Complexity**: Public tender documents often span dozens or hundreds of pages filled with convoluted legal, technical, and financial clauses. MSMEs lack dedicated legal and tender bidding teams to interpret these dense documents.
2. **High Disqualification Rates Due to Procedural Non-Compliance**: A substantial percentage of MSME bids are rejected at the preliminary qualification stage not due to technical incompetence, but due to minor compliance oversights: missing documents, expired certifications, failure to meet structured turnover thresholds, or non-conformance with specific formatting mandates.
3. **Resource Drain**: Manually parsing a 150-page Request for Proposal (RFP) to extract qualification criteria takes days of valuable engineering time, creating an opportunity cost that limits the number of bids an MSME can submit.
4. **The "Black-Box LLM" Fallacy**: Generic generative AI tools (e.g., off-the-shelf chatbots) frequently hallucinate compliance criteria, confuse optional qualifications with mandatory rejection triggers, or produce subjective assertions without exact page citations. Relying solely on pure generative AI for legal/financial compliance risks tender disqualification or blacklisting.

**The Solution**: An explainable, hybrid intelligence platform designed specifically for MSMEs. The platform combines deterministic Python business rule evaluation (for mathematical financial thresholds, hard certification checks, and submission deadlines) with Retrieval-Augmented Generation (RAG) and LangGraph agentic orchestration for contextual interpretation, deep document search, and evidence-grounded reporting with exact page and filename citations.

---

## 2. Project Goals and Non-Goals

### 2.1 Project Goals
- **Deterministic-First Compliance**: Build an objective rule engine in Python that evaluates numeric turnover, years of active business experience, mandatory certifications, and document availability without delegating arithmetic or definitive pass/fail decisions to an LLM.
- **Explainable & Auditable RAG**: Implement a semantic retrieval pipeline using PyMuPDF, ChromaDB, and Google Gemini that grounds all contextual interpretations in exact source documents, accompanied by page numbers and verbatim excerpts.
- **Strict Evidence Categorization**: Clearly separate compliance statuses into `PASS`, `FAIL`, `NEEDS_REVIEW`, and `MISSING_EVIDENCE`. The platform must acknowledge unknown or unverified factors rather than guessing.
- **Zero Evidence Fabrication**: Systematically prevent LLM hallucinations by requiring strict citation grounding and guardrail prompts.
- **Tenant-Isolated Document Vault**: Provide a secure corporate document vault for MSMEs where company profile data, tax filings, financial audits, and technical certificates are securely managed and strictly isolated from other tenants.
- **Streamlined Tender Ingestion**: Enable platform administrators to upload, parse, index, and manage public tenders with automated PDF text extraction and fallback OCR for scanned pages.
- **Tender-Specific Grounded Q&A**: Provide an interactive natural language question-answering interface where MSMEs can ask specific questions about tender clauses and receive cited answers solely derived from indexed tender documentation.
- **Internal Bid Preparation Tracking**: Provide workflow tools to track bid readiness, required document checklists, and submission deadlines without claiming external submission authority.

### 2.2 Project Non-Goals (Scope Boundaries)
- **No Automated Bidding or Government Portal Submission**: The platform will not auto-submit bids or interact via automated browser sessions with government procurement portals (e.g., GeM, CPPP). It is an intelligence and preparation system, not an automated submission bot.
- **No Unsupervised Live Scraping in Phase 1**: The platform will rely on administrator-uploaded tender notices and tender documentation. Live scraper bots targeting government portals are explicitly designated as future extensions to avoid anti-scraping blocks, CAPTCHA brittleness, and legal policy violations.
- **No Legal Representation or Final Warranty**: The software provides compliance intelligence and decision-support, but does not provide legally binding certification or guarantee tender award.
- **No LLM Overrides of Hard Rules**: The LLM will never have the architectural authority to flip a deterministic `FAIL` to a `PASS` based on subjective rhetoric or sentiment.

---

## 3. Target Users & Personas

### 3.1 Persona 1: Rajesh Sharma – Managing Director, Precision Engineering MSME
- **Context**: 12-year-old manufacturing firm with 45 employees, \$2.5M annual turnover, ISO 9001:2015 certified.
- **Pain Point**: Spends 15–20 hours reviewing each tender document. Often discovers on page 84 that an arbitrary 5-year average turnover threshold is slightly above their audited numbers, making the prior review a complete waste of time.
- **Needs**: Instant preliminary eligibility check, red-flag detection on hard constraints, a checklist of missing documents, and an evidence-backed summary of technical criteria.

### 3.2 Persona 2: Priya Patel – Bid Operations Lead, Tech Services MSME
- **Context**: Bids on 10–15 government software/hardware tenders every quarter.
- **Pain Point**: Tracking document versioning (e.g., which financial year audit was uploaded where), verifying specific experience criteria (e.g., "must have delivered 3 similar projects worth \$50k+"), and managing deadline schedules across active bids.
- **Needs**: Centralized corporate document vault, automated document gap detection against tender requirements, precise clause Q&A, and bid readiness tracking.

### 3.3 Persona 3: Platform Administrator – Tender Content & Knowledge Curator
- **Context**: Internal operator responsible for maintaining tender inventory quality.
- **Pain Point**: Ensuring uploaded PDF tender documents are correctly parsed, verifying OCR text extraction completeness, and monitoring processing errors.
- **Needs**: Intuitive tender upload pipeline, ingestion error diagnostics, processing health metrics, and vector index management.

---

## 4. Functional Requirements

### Module 1: Authentication, Authorization & Tenant Isolation
- **FR-1.1**: Email and password registration and login with JWT access and refresh tokens.
- **FR-1.2**: Role-Based Access Control (RBAC) supporting `ADMIN` and `MSME_USER` roles.
- **FR-1.3**: Automatic company association for MSME users; cross-company data access strictly prohibited at the query and database levels.
- **FR-1.4**: Passwords hashed using bcrypt; protected route guards on frontend and dependency injection guards on backend.

### Module 2: Tender Management (Admin Scope)
- **FR-2.1**: Admin CRUD operations for tender records (Title, Reference Number, Issuing Authority, Sector, Estimated Budget, EMD Amount, Publication Date, Submission Deadline, Official Portal URL).
- **FR-2.2**: Support multi-file PDF upload per tender (e.g., Main RFP, Technical Specifications, Commercial Terms, Corrigenda).
- **FR-2.3**: Manual or semi-automated trigger for document extraction, OCR, and vector indexing.
- **FR-2.4**: Public listing and faceted search of active tenders for MSME discovery (search by sector, budget, deadline, keyword).

### Module 3: Document Processing & OCR Engine
- **FR-3.1**: Page-by-page text extraction from uploaded PDFs using PyMuPDF (`fitz`).
- **FR-3.2**: Page classification and text density check: detect scanned pages with insufficient text (< 100 characters per page or below confidence threshold).
- **FR-3.3**: Optical Character Recognition (OCR) pipeline fallback via Tesseract OCR for image-only or low-density pages.
- **FR-3.4**: Preservation of page numbers, original source filenames, and section hierarchies in chunk metadata.
- **FR-3.5**: Explicit error reporting for corrupt, password-protected, or unreadable PDFs; no silent processing failures.

### Module 4: MSME Profile & Corporate Document Vault
- **FR-4.1**: Structured company profile management: legal name, registration number (e.g., Udyam / Tax ID), incorporation date, registered sector, 3-year audited turnover figures, active full-time staff count, industry certifications.
- **FR-4.2**: Document Vault supporting file uploads (Audited Balance Sheets, Tax Clearance Certificates, MSME Registration, ISO Certifications, Past Work Orders, Completion Certificates).
- **FR-4.3**: Document status lifecycle tracking: `UPLOADED`, `METADATA_EXTRACTED`, `PENDING_VERIFICATION`, `EXPIRED`, `ACTIVE`.
- **FR-4.4**: Secure document retrieval with mime-type validation and local-first sandboxed file storage.

### Module 5: Deterministic Compliance Engine
- **FR-5.1**: Dedicated Python module evaluating structured tender criteria against company parameters without LLM intervention.
- **FR-5.2**: Evaluation rules covering:
  - Minimum Annual Turnover check (individual year and 3-year average).
  - Minimum Operational Experience check (years since incorporation vs. required).
  - Mandatory Certification check (ISO, CMMI, local industry licenses).
  - Mandatory Document Presence check (existence of valid, non-expired documents in Vault).
  - Submission Deadline validity check (tender open vs. expired).
- **FR-5.3**: Deterministic output statuses: `PASS`, `FAIL`, `NEEDS_REVIEW`, `MISSING_EVIDENCE`.
- **FR-5.4**: Immutable rule execution: LLM cannot overturn a `FAIL` verdict produced by this module.

### Module 6: RAG-Based Evidence Retrieval & Vector Search
- **FR-6.1**: Recursive character chunking respecting sentence and paragraph boundaries (500–800 token chunk size, 100–150 token overlap).
- **FR-6.2**: Persistent vector storage in ChromaDB segregated by tender collections or strict metadata filtering (`tender_id`).
- **FR-6.3**: Semantic retrieval with metadata filtering ensuring zero leakage across tenders.
- **FR-6.4**: Evidence packaging returning top-k chunks containing `chunk_text`, `source_filename`, `page_number`, and `similarity_score`.

### Module 7: Agentic Orchestration via LangGraph
- **FR-7.1**: Stateful multi-node workflow orchestrating:
  1. `InputValidationNode`: Validates company profile completeness and tender availability.
  2. `DeterministicCheckNode`: Executes Python business rules.
  3. `EvidenceRetrievalNode`: Executes semantic search for complex/qualitative criteria.
  4. `AIAnalysisNode`: Prompts Google Gemini with deterministic outputs and retrieved chunks to produce explanatory summaries.
  5. `ReconciliationGuardNode`: Verifies that AI narrative strictly respects deterministic flags.
  6. `ReportSynthesisNode`: Formats the final structured compliance report.
- **FR-7.2**: Resilient state transitions and automated fallbacks if the LLM API fails or returns invalid formats.

### Module 8: Evidence-Based Compliance Reporting
- **FR-8.1**: Comprehensive structured report generation containing:
  - Overall status: `ELIGIBLE`, `INELIGIBLE`, or `POTENTIALLY_ELIGIBLE_WITH_CONDITIONS`.
  - Itemized criteria breakdown with status, evaluated value, required value, and citation references.
  - Actionable missing documents checklist.
  - Red flags and risk warnings (e.g., liquidated damages clauses, strict penalty terms).
  - Recommended next steps for the bidding team.
- **FR-8.2**: Exportable report view and persistent historical report archives in MongoDB.

### Module 9: Contextual Tender Q&A
- **FR-9.1**: Tender-specific interactive chat grounded in the selected tender's vector embeddings.
- **FR-9.2**: Every answer must provide inline citation chips (e.g., `[RFP_Part_1.pdf, Page 24]`).
- **FR-9.3**: Strict fallback instruction: when the document corpus lacks sufficient information, the model must explicitly state "The tender documentation does not specify this requirement" rather than extrapolating.

### Module 10: Bid Preparation & Readiness Tracking
- **FR-10.1**: Internal application tracker enabling MSMEs to track bid lifecycle stages: `DISCOVERED`, `EVALUATING`, `PREPARING_DOCS`, `INTERNAL_REVIEW`, `SUBMISSION_READY`, `SUBMITTED_EXTERNALLY`.
- **FR-10.2**: Task and document checklist management tied to the specific tender's compliance report.
- **FR-10.3**: Prominent UI disclaimer clarifying that tracking is purely internal and does not represent an official submission to external portals.

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Security & Compliance
- **NFR-1 (Authentication)**: JWT tokens signed using HMAC-SHA256 with expiring access tokens (60 minutes) and refresh tokens (7 days).
- **NFR-2 (Tenant Isolation)**: All database queries involving company records, document files, and compliance reports must filter on `company_id` extracted directly from the verified JWT payload.
- **NFR-3 (Input & File Sanitization)**: File uploads must be checked for magic numbers (MIME validation), restricted to `.pdf` format, and capped at 25MB per file.
- **NFR-4 (Credential Protection)**: No API keys (e.g., Gemini API keys, JWT secret keys, MongoDB credentials) in frontend builds or client-side storage.

### 5.2 Performance & Scalability
- **NFR-5 (Response Latency)**: Standard REST API endpoints (metadata queries, profile updates) must respond in under 250ms (p95).
- **NFR-6 (Document Ingestion)**: Ingestion of a standard 50-page PDF (without heavy OCR) must complete in under 20 seconds.
- **NFR-7 (Q&A Latency)**: Tender Q&A responses via RAG and Gemini streaming/response must begin rendering within 3.5 seconds.
- **NFR-8 (Deterministic Rule Speed)**: Deterministic compliance checks must execute in under 50ms.

### 5.3 Reliability & Explainability
- **NFR-9 (Deterministic Supremacy)**: 100% adherence to deterministic rule outputs. Zero instances where an LLM turns a hard mathematical fail into a pass.
- **NFR-10 (Citation Precision)**: Every factual claim in compliance explanations and Q&A answers must map to an identifiable `source_filename` and `page_number`.
- **NFR-11 (Graceful Degradation)**: If Tesseract OCR is unavailable or fails on an unreadable page, the system must log an extraction warning for that specific page while indexing the remaining text.

### 5.4 Maintainability & Extensibility
- **NFR-12 (Modular Clean Architecture)**: Strict separation between API route controllers, business logic services, data access repositories, and AI orchestration nodes.
- **NFR-13 (Pydantic Contract Enforcement)**: All inbound payloads, internal workflow states, and outbound responses must use strict Pydantic schemas.

---

## 6. Core Features and Prioritization (MoSCoW Matrix)

| Category | Features |
| :--- | :--- |
| **Must Have (P0)** | - JWT-based Auth & RBAC (Admin, MSME)<br>- Tenant-isolated MSME Profile & Document Vault<br>- Admin Tender Upload & PyMuPDF text extraction<br>- ChromaDB Vector Indexing with Page Metadata<br>- Deterministic Python Compliance Rule Engine (Turnover, Exp, Certs, Docs)<br>- LangGraph Orchestration Pipeline<br>- Explainable Compliance Report with Document & Page Citations<br>- Tender Q&A with Strict Citation Grounding |
| **Should Have (P1)** | - Tesseract OCR fallback for scanned tender pages<br>- Internal Application Preparation Tracker with Checklists<br>- Faceted Tender Search & Filter (Sector, Budget, Deadline)<br>- Downloadable Compliance Report (PDF / Markdown export)<br>- Detailed Ingestion Health & Error Logs for Admin |
| **Could Have (P2)** | - Advanced Semantic Chunking (clause/section header aware)<br>- Email/In-app Notifications for Upcoming Tender Deadlines<br>- Automated Suggestion of Past Work Orders matching technical keywords<br>- Multi-file comparison across tender addenda and corrigenda |
| **Won't Have (v1)** | - Automated tender scraping from government portals<br>- Automated bot bid submission to e-Procurement portals<br>- Multi-tenant cloud object storage (AWS S3/GCS - abstracted for future migration)<br>- Paid third-party financial verification API integrations |

---

## 7. Scope of the Initial Release (Phase 1 Baseline)

The initial release targets a robust, fully demonstrative, self-contained end-to-end platform suitable for MSME decision support:
1. **Curated Tender Repository**: Seeded or admin-uploaded real-world government/enterprise RFP documents.
2. **Deterministic & RAG Hybrid Engine**: Fully functional LangGraph state machine delivering mathematically verified and citation-grounded compliance reports.
3. **Interactive MSME Portal**: A clean, responsive React interface allowing an enterprise to register, complete their profile, upload sample verification documents, run compliance checks on any active tender, and query tender specifics via natural language Q&A.
4. **Local Development Simplicity**: MongoDB running locally or via Docker, local ChromaDB vector persistence, and local sandboxed file storage, requiring zero external paid subscriptions other than a Google Gemini API key.
