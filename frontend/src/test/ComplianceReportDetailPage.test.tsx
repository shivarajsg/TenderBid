import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ComplianceReportDetailPage } from '../pages/compliance/ComplianceReportDetailPage';
import { complianceApi } from '../api/complianceApi';
import { ComplianceReportResponse } from '../types/compliance';

vi.mock('../api/complianceApi');

describe('ComplianceReportDetailPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockReport: ComplianceReportResponse = {
    id: 'report-12345-uuid',
    tender_id: 'tender-12345-uuid',
    company_id: 'company-12345-uuid',
    overall_status: 'PARTIALLY_ELIGIBLE',
    overall_score: 75.0,
    summary: 'Company satisfies turnover but is missing mandatory audited balance sheet.',
    rule_engine_version: '1.0.0',
    tender_version_hash: 'hash_tender_abc123',
    company_version_hash: 'hash_comp_xyz789',
    findings: [
      {
        id: 'finding-1',
        requirement_id: 'CRIT_TURNOVER_01',
        rule_type: 'TURNOVER',
        requirement_description: 'Minimum annual turnover of INR 50,000,000',
        required_value: { required_turnover_inr: 50000000.0 },
        observed_value: { average_turnover_inr: 75000000.0 },
        status: 'PASS',
        is_mandatory: true,
        reason: 'Average annual turnover satisfies threshold.',
        ai_explanation: 'The firm has demonstrated robust audited turnover exceeding the tender specification.',
        evidence_citations: [
          {
            evidence_id: 'cit-1',
            source_type: 'COMPANY_DOCUMENT',
            document_id: 'doc-1',
            source_filename: 'audited_turnover_fy2025.pdf',
            page_number: 3,
            excerpt: 'Total revenue from operations: INR 75,000,000.',
            retrieval_method: 'hybrid',
            relevance_score: 0.94,
          },
        ],
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 'finding-2',
        requirement_id: 'CRIT_AUDIT_DOC',
        rule_type: 'MANDATORY_DOCUMENT',
        requirement_description: 'Audited Balance Sheet for FY 2024-2025',
        required_value: { document_category: 'FINANCIAL_AUDIT' },
        observed_value: { found: false },
        status: 'MISSING_EVIDENCE',
        is_mandatory: true,
        reason: 'No verified financial audit report found in company vault.',
        ai_explanation: 'Mandatory documentation is absent. Upload this document to the vault to fulfill eligibility.',
        evidence_citations: [],
        created_at: '2026-01-01T00:00:00Z',
      },
    ],
    created_at: '2026-01-01T12:00:00Z',
    updated_at: '2026-01-01T12:00:00Z',
  };

  it('renders report with overall status badge, score, and executive summary', async () => {
    vi.mocked(complianceApi.getReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/compliance/reports/report-12345-uuid']}>
        <Routes>
          <Route path="/compliance/reports/:reportId" element={<ComplianceReportDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('PARTIALLY ELIGIBLE')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getByText(/Company satisfies turnover but is missing mandatory/i)).toBeInTheDocument();
    });
  });

  it('displays deterministic findings alongside AI explanations and verified citations', async () => {
    vi.mocked(complianceApi.getReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/compliance/reports/report-12345-uuid']}>
        <Routes>
          <Route path="/compliance/reports/:reportId" element={<ComplianceReportDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // Finding 1
      expect(screen.getByText('Minimum annual turnover of INR 50,000,000')).toBeInTheDocument();
      expect(screen.getByText('The firm has demonstrated robust audited turnover exceeding the tender specification.')).toBeInTheDocument();
      // Citation
      expect(screen.getByText('audited_turnover_fy2025.pdf')).toBeInTheDocument();
      expect(screen.getByText('Page 3')).toBeInTheDocument();
      expect(screen.getByText(/"Total revenue from operations: INR 75,000,000."/)).toBeInTheDocument();

      // Finding 2 (Missing evidence must not be presented as PASS)
      expect(screen.getByText('Audited Balance Sheet for FY 2024-2025')).toBeInTheDocument();
      expect(screen.getByText('MISSING PROOF (Mandatory)')).toBeInTheDocument();
    });
  });
});
