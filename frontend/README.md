# TenderBid Frontend Application

React 18 + TypeScript + Vite + Tailwind CSS frontend for the **Agentic AI-Powered Tender Intelligence and Compliance Management Platform for MSMEs Using RAG**.

---

## Features

- **Auth & Session Management:** JWT Bearer authentication, auto-login upon registration, and role-based route guards (`MSME_USER` vs. `ADMIN`).
- **MSME Dashboard:** Live counts of tenders, vault files, and recent reports.
- **Company Profile:** Manage incorporation date, sector, business classification, audited annual turnover records, certifications, and past completed projects.
- **Document Vault:** Secure PDF uploads with category tagging (`FINANCIAL_AUDIT`, `TAX_RECORD`, `CERTIFICATION`, `WORK_ORDER`, `TENDER_RFP`), file size, page count, and chunk counts.
- **Tender Discovery:** Searchable and sector-filterable tender catalog with budget amounts in INR, MSME EMD exemptions, and RFP PDF downloads.
- **Deterministic Compliance Analysis:** LangGraph workflow execution with step-by-step progress indicators.
- **Report & Citation Inspection:** Overall score and status badges (`ELIGIBLE`, `PARTIALLY_ELIGIBLE`, `NOT_ELIGIBLE`, `NEEDS_REVIEW`), criteria breakdown with deterministic facts vs. Gemini AI narrative explanations, verified document excerpts, page numbers, and print/export functionality.
- **Admin Portal:** Create tenders with JSON criteria, upload multiple PDF notices, trigger vectorization pipelines, and inspect document chunking details.

---

## Local Development (Windows PowerShell)

```powershell
# 1. Install dependencies
npm install

# 2. Start development server
npm run dev
```

App runs on `http://127.0.0.1:5173`.

---

## Available Scripts

- `npm run dev`: Starts the Vite development server with hot module replacement.
- `npm run build`: Compiles TypeScript with `tsc -b` and builds production bundle into `dist/` with `vite build`.
- `npm run preview`: Locally previews the production build.
- `npm test -- --run`: Runs the complete Vitest test suite once (22 tests across 8 suites).
- `npm run test:watch`: Runs Vitest in interactive watch mode for development.

---

## Testing & Quality Assurance

- **Unit & Component Tests**: 22 tests across 8 test suites passing cleanly.
- **Coverage**: Includes StatusBadge rendering, ProtectedRoute and AdminRoute RBAC guards, DocumentVaultPage file interactions, TendersListPage search filters, ComplianceAnalysisPage deterministic notice checks, ComplianceReportDetailPage score breakdown, and end-to-end full-stack navigation journeys.
- **Production Build**: Verified with zero TypeScript compiler diagnostics. Static bundle served via Alpine Nginx with Gzip compression and client-side SPA fallback.

---

## Environment Variables

Configured in `.env.development`:
```ini
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```
