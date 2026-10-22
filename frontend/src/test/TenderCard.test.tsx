import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { TenderCard } from '../components/tenders/TenderCard';
import { getTenderCategoryKey, getTenderImageUrl } from '../utils/tenderImage';
import { TenderResponse } from '../types/tender';

const mockTender: TenderResponse = {
  id: 'tender-card-test-1',
  tender_reference: 'GEM/2026/B/8147726',
  title: 'WHEEL HUB ASSY BEML TATRA',
  issuing_authority: 'Ministry of Defence - Department of Military Affairs',
  sector: 'Automotive',
  estimated_budget_inr: null,
  emd_amount_inr: null,
  msme_emd_exemption: true,
  publication_date: '2026-10-12T10:00:00Z',
  submission_deadline: '2026-10-23T14:30:00Z',
  official_portal_url: 'https://bidplus.gem.gov.in/showbidDocument/GEM-8147726',
  source_portal: 'GEM',
  processing_status: 'PENDING',
  documents: [],
  ingestion_metadata: {
    gem_quantity: 1,
  },
  created_at: '2026-10-12T10:00:00Z',
  updated_at: '2026-10-12T10:00:00Z',
};

describe('TenderCard & Image Utilities', () => {
  it('correctly maps tender title to automotive-machinery category', () => {
    const cat = getTenderCategoryKey('WHEEL HUB ASSY BEML TATRA', 'Defence');
    expect(cat).toBe('automotive-machinery');
    const url = getTenderImageUrl('WHEEL HUB ASSY BEML TATRA', 'Defence');
    expect(url).toContain('/images/tender-categories/automotive-machinery.svg');
  });

  it('renders all tender details matching reference layout', () => {
    const onDownloadPdf = vi.fn();
    const onViewOrDownloadLocalPdf = vi.fn();
    const onEvaluateCompliance = vi.fn();
    const getAllBidsPortalUrl = vi.fn().mockReturnValue('https://bidplus.gem.gov.in/all-bids');

    render(
      <MemoryRouter>
        <TenderCard
          tender={mockTender}
          isDownloading={false}
          isDownloadingLocal={false}
          onDownloadPdf={onDownloadPdf}
          onViewOrDownloadLocalPdf={onViewOrDownloadLocalPdf}
          onEvaluateCompliance={onEvaluateCompliance}
          getAllBidsPortalUrl={getAllBidsPortalUrl}
        />
      </MemoryRouter>
    );

    // Badges
    expect(screen.getByText('GEM/2026/B/8147726')).toBeInTheDocument();
    expect(screen.getByTestId('badge-gem')).toBeInTheDocument();
    expect(screen.getByText('Not Downloaded')).toBeInTheDocument();

    // Title and Authority
    expect(screen.getByText('WHEEL HUB ASSY BEML TATRA')).toBeInTheDocument();
    expect(screen.getByText('Ministry of Defence - Department of Military Affairs')).toBeInTheDocument();

    // Info Grid
    expect(screen.getByText('₹ Not Disclosed')).toBeInTheDocument();
    expect(screen.getByText('Exempt for MSMEs')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('12/10/2026')).toBeInTheDocument();
    expect(screen.getByText(/23\/10\/2026/)).toBeInTheDocument();

    // Image container and rounded styling
    const img = screen.getByAltText('WHEEL HUB ASSY BEML TATRA');
    expect(img).toBeInTheDocument();
    expect(img).toHaveClass('object-cover');
    expect(img).toHaveClass('group-hover:scale-105');

    // Buttons
    expect(screen.getByText('View Notice Details')).toBeInTheDocument();
    expect(screen.getByText('Evaluate Compliance')).toBeInTheDocument();
    const downloadBtn = screen.getByRole('button', { name: /Download this Tender PDF/i });
    expect(downloadBtn).toBeInTheDocument();

    // Trigger actions
    fireEvent.click(downloadBtn);
    expect(onDownloadPdf).toHaveBeenCalledWith(mockTender);

    fireEvent.click(screen.getByText('Evaluate Compliance'));
    expect(onEvaluateCompliance).toHaveBeenCalledWith(mockTender);

    fireEvent.click(screen.getByTestId('btn-local-pdf-GEM/2026/B/8147726'));
    expect(onViewOrDownloadLocalPdf).toHaveBeenCalledWith(mockTender);
  });
});
