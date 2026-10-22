import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TenderDetailPage } from '../pages/tenders/TenderDetailPage';
import { tendersApi } from '../api/tendersApi';
import { TenderResponse } from '../types/tender';

vi.mock('../api/tendersApi');
vi.mock('../api/applicationsApi');

describe('TenderDetailPage Component — Document Retrieval & In-App Viewing', () => {
  const mockTenderWithDoc: TenderResponse = {
    id: 'tender-123',
    tender_reference: 'NTPC/ELECT/2026/01',
    title: 'Procurement of Substation Switchgear',
    issuing_authority: 'National Thermal Power Corporation',
    sector: 'Power & Energy',
    estimated_budget_inr: 50000000,
    emd_amount_inr: 1000000,
    msme_emd_exemption: true,
    submission_deadline: '2026-12-31T00:00:00Z',
    publication_date: '2026-01-01T00:00:00Z',
    official_portal_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender',
    source_portal: 'CPPP',
    processing_status: 'INDEXED',
    documents: [
      {
        id: 'doc-456',
        tender_id: 'tender-123',
        original_filename: 'NTPC_Switchgear_Specification.pdf',
        document_category: 'TENDER_NOTICE',
        file_size_bytes: 1024000,
        mime_type: 'application/pdf',
        sha256_hash: 'abc123sha256',
        total_pages: 14,
        indexed_chunks: 28,
        processing_status: 'INDEXED',
        download_status: 'DOWNLOADED',
        created_at: '2026-01-01T00:00:00Z',
      },
    ],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  const mockTenderEmpty: TenderResponse = {
    ...mockTenderWithDoc,
    id: 'tender-empty',
    documents: [],
    official_portal_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-pdf-blob');
    window.URL.revokeObjectURL = vi.fn();
  });

  it('renders attached tender document with vault status, indexed chunks, and View PDF button', async () => {
    vi.mocked(tendersApi.getTender).mockResolvedValue(mockTenderWithDoc);

    render(
      <MemoryRouter initialEntries={['/tenders/tender-123']}>
        <Routes>
          <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('NTPC_Switchgear_Specification.pdf')).toBeInTheDocument();
      expect(screen.getByText(/Stored in Vault/i)).toBeInTheDocument();
      expect(screen.getByText(/Indexed & Ready \(14 pages, 28 chunks\)/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /View PDF/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Download PDF/i })).toBeInTheDocument();
    });
  });

  it('opens in-app authenticated embedded PDF viewer modal when clicking View PDF', async () => {
    vi.mocked(tendersApi.getTender).mockResolvedValue(mockTenderWithDoc);
    vi.mocked(tendersApi.viewDocumentBlob).mockResolvedValue('blob:http://localhost/mock-pdf-blob');

    render(
      <MemoryRouter initialEntries={['/tenders/tender-123']}>
        <Routes>
          <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /View PDF/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /View PDF/i }));

    await waitFor(() => {
      expect(tendersApi.viewDocumentBlob).toHaveBeenCalledWith('tender-123', 'doc-456');
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/Secure In-App PDF Viewer • Verified Vault Storage/i)).toBeInTheDocument();
      const iframe = screen.getByTitle('NTPC_Switchgear_Specification.pdf');
      expect(iframe).toHaveAttribute('src', 'blob:http://localhost/mock-pdf-blob');
    });

    // Close modal
    fireEvent.click(screen.getByTitle('Close PDF viewer'));
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-pdf-blob');
  });

  it('renders official portal fallback button when tender has 0 attached PDF files', async () => {
    vi.mocked(tendersApi.getTender).mockResolvedValue(mockTenderEmpty);

    render(
      <MemoryRouter initialEntries={['/tenders/tender-empty']}>
        <Routes>
          <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/No direct PDF files are currently stored for this tender record/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Open Official Tender Page/i })).toBeInTheDocument();
    });
  });

  it('triggers Fetch Tender Documents and displays feedback notification', async () => {
    vi.mocked(tendersApi.getTender).mockResolvedValue(mockTenderEmpty);
    vi.mocked(tendersApi.fetchTenderDocuments).mockResolvedValue({
      tender_id: 'tender-empty',
      status: 'HTML_PAGE_ONLY',
      url_classification: 'HTML_PORTAL_PAGE',
      source_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender',
      documents_retrieved: 0,
      documents_indexed: 0,
      documents: [],
      official_portal_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender',
      message: 'The tender source provides an interactive official web portal page rather than a downloadable PDF file.',
    });

    render(
      <MemoryRouter initialEntries={['/tenders/tender-empty']}>
        <Routes>
          <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Fetch Tender Documents/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Fetch Tender Documents/i }));

    await waitFor(() => {
      expect(tendersApi.fetchTenderDocuments).toHaveBeenCalledWith('tender-empty');
      expect(
        screen.getByText(/The tender source provides an interactive official web portal page rather than a downloadable PDF file/i)
      ).toBeInTheDocument();
    });
  });
});
