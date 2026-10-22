import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TendersListPage } from '../pages/tenders/TendersListPage';
import { tendersApi } from '../api/tendersApi';

vi.mock('../api/tendersApi');

describe('TendersListPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.scrollTo = vi.fn();
  });

  it('renders tender list successfully when data is returned', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'tender-1',
          tender_reference: 'NTPC/ELECT/2026/0892',
          title: 'Supply and Commissioning of Switchgear',
          issuing_authority: 'National Thermal Power Corporation',
          sector: 'Electrical Infrastructure',
          estimated_budget_inr: 50000000,
          emd_amount_inr: 1000000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'COMPLETED',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 50,
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('NTPC/ELECT/2026/0892')).toBeInTheDocument();
      expect(screen.getByText('Supply and Commissioning of Switchgear')).toBeInTheDocument();
      expect(screen.getByText('National Thermal Power Corporation')).toBeInTheDocument();
      expect(screen.getByText('Exempt for MSMEs')).toBeInTheDocument();
    });
  });

  it('renders empty state when no tenders are available', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 50,
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No tenders found')).toBeInTheDocument();
    });
  });

  it('renders official government source badges and portal links for ingested tenders', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'gem-tender-1',
          tender_reference: 'GEM/2026/B/892101',
          title: 'Supply of Industrial IoT Gateways',
          issuing_authority: 'Bharat Heavy Electricals Limited',
          sector: 'Industrial Electronics',
          estimated_budget_inr: 4850000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          source_portal: 'GEM',
          source_tender_id: 'GEM-2026-B-892101',
          official_portal_url: 'https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892101',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'cppp-tender-1',
          tender_reference: 'CPPP/2026/NIC/789451',
          title: 'Substation Modernization',
          issuing_authority: 'NTPC Korba',
          sector: 'Electrical',
          estimated_budget_inr: 14500000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          source_portal: 'CPPP',
          source_tender_id: '2026_NIC_789451_1',
          official_portal_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndTenderDetailsExternal&tenderId=2026_NIC_789451_1',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'tk-tender-1',
          tender_reference: 'GEM/2026/B/902144',
          title: 'Solar Inverters and Battery Energy Storage',
          issuing_authority: 'Power Grid Corporation of India Limited',
          sector: 'Renewable Energy',
          estimated_budget_inr: 18500000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          source_portal: 'TENDERKART',
          source_tender_id: 'c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c',
          official_portal_url: 'https://tenderkart.in/tenders/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 3,
      skip: 0,
      limit: 50,
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('badge-gem')).toBeInTheDocument();
      expect(screen.getByTestId('badge-cppp')).toBeInTheDocument();
      expect(screen.getByTestId('badge-tenderkart')).toBeInTheDocument();
      const portalLinks = screen.getAllByText('Portal Notice');
      expect(portalLinks.length).toBe(3);
    });
  });

  it('renders pagination controls and navigates across pages with non-overlapping parameters', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'page-1-tender-1',
          tender_reference: 'PAGE/1/T1',
          title: 'Tender Page One Sample',
          issuing_authority: 'CPWD',
          sector: 'Civil',
          estimated_budget_inr: 2500000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 73,
      skip: 0,
      limit: 12,
      page: 1,
      pages: 7,
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('pagination-controls')).toBeInTheDocument();
      expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 7');
      expect(screen.getByTestId('btn-prev-page')).toBeDisabled();
      expect(screen.getByTestId('btn-next-page')).not.toBeDisabled();
      expect(screen.getByText('PAGE/1/T1')).toBeInTheDocument();
    });

    // Mock page 2 response
    vi.mocked(tendersApi.listTenders).mockResolvedValueOnce({
      items: [
        {
          id: 'page-2-tender-1',
          tender_reference: 'PAGE/2/T1',
          title: 'Tender Page Two Sample',
          issuing_authority: 'NHAI',
          sector: 'Highways',
          estimated_budget_inr: 8500000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 73,
      skip: 12,
      limit: 12,
      page: 2,
      pages: 7,
    });

    const nextBtn = screen.getByTestId('btn-next-page');
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(tendersApi.listTenders).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          limit: 12,
        })
      );
      expect(screen.getByText('PAGE/2/T1')).toBeInTheDocument();
      expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 2 of 7');
      expect(screen.getByTestId('btn-prev-page')).not.toBeDisabled();
    });
  });
});
