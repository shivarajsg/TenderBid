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

  it('triggers live refresh when Refresh Tender List button is clicked', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'tender-live-1',
          tender_reference: 'GEM/2026/B/7996346',
          title: 'All In One PC Workstation',
          issuing_authority: 'Ministry of Defence',
          sector: 'Public Procurement',
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 12,
    });

    vi.mocked(tendersApi.refreshTenders).mockResolvedValue({
      id: 'run-1',
      source_portal: 'ALL',
      status: 'SUCCESS',
      tenders_found: 5,
      tenders_ingested: 3,
      tenders_updated: 2,
      tenders_skipped: 0,
      started_at: '2026-10-22T20:00:00Z',
      completed_at: '2026-10-22T20:00:02Z',
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Refresh Tender List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Refresh Tender List'));

    await waitFor(() => {
      expect(tendersApi.refreshTenders).toHaveBeenCalled();
      expect(screen.getByText(/Live tender refresh completed/i)).toBeInTheDocument();
    });
  });

  it('triggers per-tender PDF download and updates card state', async () => {
    const tenderObj = {
      id: 'tender-download-1',
      tender_reference: 'GEM/2026/B/8098475',
      title: 'Industrial Generator Systems',
      issuing_authority: 'Central Electricity Authority',
      sector: 'Power',
      msme_emd_exemption: true,
      submission_deadline: '2026-12-31T23:59:59Z',
      processing_status: 'PENDING',
      documents: [],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };

    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [tenderObj],
      total: 1,
      skip: 0,
      limit: 12,
    });

    vi.mocked(tendersApi.fetchTenderDocuments).mockResolvedValue({
      tender_id: tenderObj.id,
      status: 'COMPLETED',
      url_classification: 'PDF_DOCUMENT',
      documents_retrieved: 1,
      documents_indexed: 1,
      documents: [
        {
          id: 'doc-1',
          tender_id: tenderObj.id,
          original_filename: 'Industrial_Generator_Systems.pdf',
          document_category: 'TENDER_NOTICE',
          file_size_bytes: 145000,
          mime_type: 'application/pdf',
          sha256_hash: 'abcdef123456',
          total_pages: 13,
          indexed_chunks: 26,
          processing_status: 'INDEXED',
          created_at: '2026-10-22T20:00:00Z',
        },
      ],
      message: 'Successfully downloaded and indexed tender document.',
    });

    vi.mocked(tendersApi.getTender).mockResolvedValue({
      ...tenderObj,
      documents: [
        {
          id: 'doc-1',
          tender_id: tenderObj.id,
          original_filename: 'Industrial_Generator_Systems.pdf',
          document_category: 'TENDER_NOTICE',
          file_size_bytes: 145000,
          mime_type: 'application/pdf',
          sha256_hash: 'abcdef123456',
          total_pages: 13,
          indexed_chunks: 26,
          processing_status: 'INDEXED',
          created_at: '2026-10-22T20:00:00Z',
        },
      ],
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Download Tender PDF')).toBeInTheDocument();
      expect(screen.getByText('Not Downloaded')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Download Tender PDF'));

    await waitFor(() => {
      expect(tendersApi.fetchTenderDocuments).toHaveBeenCalledWith('tender-download-1');
      expect(screen.getByText(/Indexed & Ready/i)).toBeInTheDocument();
    });
  });

  it('guards Evaluate Compliance when tender has no indexed documents and shows mandatory alert modal', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'tender-guard-1',
          tender_reference: 'GEM/2026/B/892104',
          title: 'Enterprise Workstations',
          issuing_authority: 'IIST',
          sector: 'IT',
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 12,
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Evaluate Compliance')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Evaluate Compliance'));

    await waitFor(() => {
      expect(screen.getByTestId('unindexed-document-guard-modal')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Compliance evaluation cannot be completed because no usable tender document has been downloaded and indexed for this bid. Retry document retrieval, open the official source, or upload the tender file manually.'
        )
      ).toBeInTheDocument();
      expect(screen.getByText('Download Tender PDF Now')).toBeInTheDocument();
    });
  });

  it('renders GeM live crawl transparency metrics panel when GeM portal refresh returns pagination metadata', async () => {
    vi.mocked(tendersApi.listTenders).mockResolvedValue({
      items: [
        {
          id: 'gem-bid-1',
          tender_reference: 'GEM/2026/B/8147949',
          title: 'Rapid Diagnostic Kit',
          issuing_authority: 'Ministry of Health',
          sector: 'Healthcare',
          msme_emd_exemption: true,
          submission_deadline: '2026-12-31T23:59:59Z',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          source_portal: 'GEM',
        },
      ],
      total: 1,
      skip: 0,
      limit: 12,
    });

    vi.mocked(tendersApi.refreshTenders).mockResolvedValue({
      id: 'mock-gem-run-id',
      source_portal: 'GEM',
      status: 'SUCCESS',
      tenders_found: 50,
      tenders_ingested: 10,
      tenders_updated: 5,
      tenders_skipped: 35,
      started_at: '2026-01-01T00:00:00Z',
      completed_at: '2026-01-01T00:01:00Z',
      run_metadata: {
        gem_crawl: {
          total_portal_records: 47245,
          total_pages_available: 4725,
          start_page: 1,
          end_page_crawled: 5,
          next_page: 6,
          pages_processed: 5,
          unique_bids_discovered: 50,
          unretrieved_pages: [],
          crawl_completed: false,
          is_partial: true,
          last_retrieved_at: '2026-01-01T00:01:00Z',
        },
      },
    });

    render(
      <MemoryRouter>
        <TendersListPage />
      </MemoryRouter>
    );

    // Switch to GeM Portal tab
    fireEvent.click(screen.getByText('GeM Portal'));

    await waitFor(() => {
      expect(screen.getByText('Refresh Tender List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Refresh Tender List'));

    await waitFor(() => {
      expect(screen.getByTestId('gem-crawl-transparency-card')).toBeInTheDocument();
      expect(screen.getByTestId('metric-gem-total')).toHaveTextContent('47,245');
      expect(screen.getByTestId('metric-gem-pages')).toHaveTextContent('5 (p.1–5)');
      expect(screen.getByTestId('metric-gem-discovered')).toHaveTextContent('50');
      expect(screen.getByTestId('metric-gem-ingested')).toHaveTextContent('10');
      expect(screen.getByTestId('metric-gem-updated')).toHaveTextContent('5');
      expect(screen.getByTestId('metric-gem-skipped')).toHaveTextContent('35');
      expect(screen.getByTestId('metric-gem-unretrieved')).toHaveTextContent('0 (None)');
      expect(screen.getByTestId('badge-crawl-status')).toHaveTextContent('Bounded Batch (Partial Crawl)');
    });
  });
});
