import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ComplianceAnalysisPage } from '../pages/compliance/ComplianceAnalysisPage';
import { companyApi } from '../api/companyApi';
import { tendersApi } from '../api/tendersApi';

vi.mock('../api/companyApi');
vi.mock('../api/tendersApi');
vi.mock('../api/complianceApi');

describe('ComplianceAnalysisPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays deterministic architecture guarantee notice', async () => {
    vi.mocked(companyApi.getProfile).mockResolvedValue({
      id: 'comp-1',
      owner_id: 'user-1',
      legal_name: 'Apex Electricals Pvt Ltd',
      registration_number: 'UDYAM-01-12345',
      business_type: 'SMALL',
      sector: 'Electrical',
      incorporation_date: '2020-01-01',
      years_in_business: 6,
      annual_turnover: [],
      certifications: [],
      work_experience: [],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'tender-1',
          tender_reference: 'NTPC/2026/01',
          title: 'Power System Supply',
          issuing_authority: 'NTPC',
          sector: 'Energy',
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T00:00:00Z',
          processing_status: 'COMPLETED',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
    });

    render(
      <MemoryRouter>
        <ComplianceAnalysisPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Deterministic Architecture Guarantee:')).toBeInTheDocument();
      expect(screen.getByText('Include Gemini AI Narrative & Evidence Explanations')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start Compliance Evaluation/i })).toBeEnabled();
    });
  });

  it('shows missing company profile warning when company is not configured', async () => {
    vi.mocked(companyApi.getProfile).mockRejectedValue(new Error('Company not found'));
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 100,
    });

    render(
      <MemoryRouter>
        <ComplianceAnalysisPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Company Profile Not Configured')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start Compliance Evaluation/i })).toBeDisabled();
    });
  });

  it('renders prominent warning and direct upload link when selected tender has 0 indexed documents', async () => {
    vi.mocked(companyApi.getProfile).mockResolvedValue({
      id: 'comp-1',
      owner_id: 'user-1',
      legal_name: 'Apex Electricals Pvt Ltd',
      registration_number: 'UDYAM-01-12345',
      business_type: 'SMALL',
      sector: 'Electrical',
      incorporation_date: '2020-01-01',
      years_in_business: 6,
      annual_turnover: [],
      certifications: [],
      work_experience: [],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'tender-empty-docs',
          tender_reference: 'GEM/2026/B/99999',
          title: 'Unprocessed Tender Notice',
          issuing_authority: 'Defence PSU',
          sector: 'Defence',
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T00:00:00Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
    });

    render(
      <MemoryRouter>
        <ComplianceAnalysisPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          /Full compliance analysis is unavailable because no usable tender documents have been indexed/i
        )
      ).toBeInTheDocument();
      expect(
        screen.getByRole('link', { name: /View Tender Notice & Upload \/ Inspect Documents/i })
      ).toHaveAttribute('href', '/tenders/tender-empty-docs');
    });
  });
});
