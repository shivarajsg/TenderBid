import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApplicationsPage } from '../pages/applications/ApplicationsPage';
import { applicationsApi } from '../api/applicationsApi';

vi.mock('../api/applicationsApi');

describe('ApplicationsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders tracked applications with stage and compliance metadata', async () => {
    vi.mocked(applicationsApi.listApplications).mockResolvedValue({
      items: [
        {
          id: 'app-1',
          company_id: 'comp-1',
          tender_id: 't-1',
          status: 'PREPARING',
          notes: 'Gathering audited balance sheets.',
          tender_title: 'Grid Power Expansion',
          tender_reference: 'GRID/2026/01',
          estimated_budget_inr: 25000000,
          submission_deadline: '2026-11-15T00:00:00Z',
          latest_compliance_status: 'PARTIALLY_ELIGIBLE',
          latest_compliance_score: 75.0,
          latest_report_id: 'rep-1',
          created_at: '2026-10-01T00:00:00Z',
          updated_at: '2026-10-01T00:00:00Z',
        },
      ],
      total: 1,
    });

    render(
      <MemoryRouter>
        <ApplicationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Internal Bid Preparation Pipeline')).toBeInTheDocument();
      expect(screen.getByText('GRID/2026/01')).toBeInTheDocument();
      expect(screen.getByText('Grid Power Expansion')).toBeInTheDocument();
      expect(screen.getByText('PREPARING')).toBeInTheDocument();
      expect(screen.getByText(/PARTIALLY_ELIGIBLE/)).toBeInTheDocument();
      expect(screen.getByText('→ READY')).toBeInTheDocument();
    });
  });

  it('displays empty state when no applications are tracked', async () => {
    vi.mocked(applicationsApi.listApplications).mockResolvedValue({
      items: [],
      total: 0,
    });

    render(
      <MemoryRouter>
        <ApplicationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No Tracked Applications')).toBeInTheDocument();
      expect(screen.getByText('Browse Tender Opportunities')).toBeInTheDocument();
    });
  });
});
