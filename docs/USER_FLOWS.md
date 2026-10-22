# User Flows and Interaction Journeys

## 1. Overview of Platform Journeys

The platform supports two distinct user roles:
1. **Platform Administrator**: Curates tender notices, uploads RFP documents, monitors extraction/OCR pipelines, and oversees processing health.
2. **MSME Company User**: Manages company credentials in the Document Vault, searches tenders, triggers compliance evaluations, asks grounded clause questions, and tracks bid preparation.

---

## 2. Administrator Journey: Tender Management & Ingestion

```mermaid
flowchart TD
    A([Admin Logs In]) --> B[Admin Dashboard]
    B --> C[Click 'Create New Tender']
    C --> D[Enter Metadata: Ref ID, Title, Authority, Budget, Deadline]
    D --> E[Define Structured Hard Criteria: Min Turnover, Experience, Certifications]
    E --> F[Upload PDF RFP Documents]
    F --> G{Validate File\nFormat & Size}
    G -->|Invalid / >25MB| H[Display Error: Invalid File] --> F
    G -->|Valid| I[Submit Record]
    I --> J[Background Job: PyMuPDF Text Extraction]
    J --> K{Text Density Check:\nScanned Pages?}
    K -->|Yes: Text < 100 chars| L[Execute Tesseract OCR] --> M[Chunk & Embed Chunks]
    K -->|No: Sufficient Text| M
    M --> N[Insert into ChromaDB Collection]
    N --> O[Update Tender Status: INDEXED]
    O --> P([Tender Available for MSME Analysis])
```

### Detailed Flow Steps:
1. **Authentication**: Admin signs in using administrator credentials.
2. **Tender Initialization**: Admin fills in key tender parameters including title, procuring agency, estimated contract value, EMD amount, and hard closing deadline.
3. **Structured Criteria Definition**: Admin inputs baseline numerical rules (e.g., minimum turnover of \$500k, minimum 3 years of operational experience, ISO 9001 mandatory).
4. **Document Attachment**: Admin uploads the official PDF documentation (RFP, technical specifications, terms & conditions).
5. **Asynchronous Processing**: The system ingests files, classifies pages, applies OCR to rasterized pages, and builds persistent ChromaDB vector collections.
6. **Verification State**: Admin monitors the Ingestion Status badge (`PENDING` -> `EXTRACTING` -> `INDEXED`).

---

## 3. MSME User Journey: Registration & Profile Setup

```mermaid
flowchart TD
    M1([MSME Lands on Site]) --> M2[Sign Up: Email, Password, Company Legal Name, Tax ID]
    M2 --> M3[System Creates User & Company Tenant Record]
    M3 --> M4[Redirect to Company Setup Wizard]
    M4 --> M5[Step 1: Enter Business Sector, Incorporation Date]
    M5 --> M6[Step 2: Enter Audited Annual Turnover for Past 3 FYs]
    M6 --> M7[Step 3: Document Vault Upload\n(Upload Balance Sheets, MSME Reg, ISO Certs)]
    M7 --> M8{Files Validated?}
    M8 -->|Fail| M9[Show Warning: Non-PDF or Corrupt File] --> M7
    M8 -->|Pass| M10[Compute System Readiness Score]
    M10 --> M11([MSME Profile Active - Navigate to Tender Discovery])
```

### Key Setup Elements:
- **Baseline Data Entry**: Incorporation date (used for auto-calculating operational experience), registered business type (Micro, Small, Medium), and audited revenue.
- **Document Vault Ingestion**: Uploading proof documents into their isolated tenant vault. The platform calculates a "Profile Readiness Score" reflecting document coverage.

---

## 4. MSME User Journey: Tender Discovery & Compliance Evaluation

```mermaid
flowchart TD
    S1([MSME Browses Active Tenders]) --> S2[Apply Filters: Sector, Budget Range, Deadline]
    S2 --> S3[Select Tender Details Page]
    S3 --> S4[Review Summary: Budget, EMD Exemption, Deadlines]
    S4 --> S5[Click 'Run Compliance Analysis']
    
    S5 --> S6[LangGraph Agentic Pipeline Initiates]
    S6 --> S7[Deterministic Engine Evaluates Hard Constraints]
    
    S7 --> S8{Hard Mandatory Failure?}
    S8 -->|Yes| S9[Flag Status: INELIGIBLE\nRecord Critical Fail Reasons]
    S8 -->|No| S10[RAG Semantic Retrieval from ChromaDB]
    
    S9 --> S10
    S10 --> S11[Google Gemini Analyzes Qualitative Clauses & Risks]
    S11 --> S12[Reconciliation Guard Verifies Logic Consistency]
    S12 --> S13[Generate Structured Compliance Report]
    S13 --> S14([User Views Compliance Report with Citations])
```

### Evaluation Presentation:
- **Clear Status Badge**: `ELIGIBLE` (Green), `POTENTIALLY_ELIGIBLE_WITH_CONDITIONS` (Amber), `INELIGIBLE` (Red).
- **Rule-by-Rule Breakdown**: Displays company credential vs. required threshold, evaluator engine (Deterministic vs. RAG), and pass/fail badge.
- **Auditable Citations**: Each finding features an expandable citation card showing the source PDF filename, page number, and exact quoted clause.
- **Missing Document Alerts**: Specific callouts for required documents not present in the MSME's vault.

---

## 5. MSME User Journey: Contextual Tender Q&A

```mermaid
flowchart TD
    Q1([User Opens 'Ask Tender AI' Drawer]) --> Q2[Enter Question: e.g., 'What are the liquidated damages terms?']
    Q2 --> Q3[FastAPI Receives Query + tender_id]
    Q3 --> Q4[Generate Question Embedding]
    Q4 --> Q5[Query ChromaDB with tender_id Metadata Filter]
    Q5 --> Q6{Sufficient Semantic Match?}
    Q6 -->|No: Low Similarity| Q7[Return Fallback: 'Tender docs do not state this requirement.']
    Q6 -->|Yes: Top Chunks Retrieved| Q8[Prompt Gemini with Grounded Context & System Guardrails]
    Q8 --> Q9[Synthesize Plain Language Answer with Inline Citations]
    Q9 --> Q10([Display Answer with Source Filename & Page Chips])
```

### Guardrail Behaviors:
- If an MSME asks a question unrelated to the tender (e.g., general programming or cooking), the model politely declines and steers back to the tender.
- If a clause is absent from the uploaded documents, the model does not guess or interpolate; it explicitly reports that the specification is silent on that matter.

---

## 6. MSME User Journey: Internal Application Preparation & Tracking

```mermaid
flowchart TD
    T1([User Clicks 'Track Bid Preparation']) --> T2[Initialize Application Record]
    T2 --> T3[System Populates Document Checklist from Compliance Report]
    T3 --> T4[User Assigns Internal Owner & Target Readiness Date]
    T4 --> T5[User Checks Off Assembled Documents & Enters Notes]
    T5 --> T6{All Mandatory Docs Checked?}
    T6 -->|No| T7[Status: PREPARING_DOCUMENTS]
    T6 -->|Yes| T8[Status: READY_FOR_PORTAL_SUBMISSION]
    T8 --> T9[User Manually Submits on External Government Portal]
    T9 --> T10[User Marks Tracker: 'SUBMITTED_EXTERNALLY' & Records Ref ID]
```

---

## 7. Empty States, Edge Cases & Error Scenarios

### 7.1 Empty States
1. **No Tenders Found**:
   - **Trigger**: Search query or sector filter yields 0 matches.
   - **UI Presentation**: Friendly illustration with prompt: "No active tenders match your filters. Try clearing filters or check back soon."
2. **Empty Document Vault**:
   - **Trigger**: New MSME user has not uploaded any credentials.
   - **UI Presentation**: Prompt highlighting benefits: "Upload your Balance Sheets and Certifications to enable one-click eligibility evaluations."
3. **No Compliance Analysis Run Yet**:
   - **Trigger**: MSME views tender details for the first time.
   - **UI Presentation**: Action card: "Run your free AI compliance evaluation to verify eligibility and discover missing documents."

### 7.2 Error Scenarios & Recoveries
1. **Expired Tender Notice**:
   - **Condition**: User clicks "Run Analysis" on a tender whose `submission_deadline` is in the past.
   - **Behavior**: System performs analysis but displays a permanent alert banner: "This tender expired on [Date]. Analysis is generated for historical reference only."
2. **Corrupted or Password-Protected PDF**:
   - **Condition**: Admin uploads a password-locked or damaged PDF.
   - **Behavior**: Ingestion fails immediately with a descriptive error: "Unable to parse [filename]: File is password protected. Please unlock and re-upload."
3. **Gemini API Transient Failure**:
   - **Condition**: Gemini API experiences 503 or quota throttling.
   - **Behavior**: UI gracefully displays the complete deterministic report with the notice: "AI summary unavailable due to upstream connectivity. Deterministic compliance results and raw clause citations are displayed below."
