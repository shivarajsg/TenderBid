import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TenderQAPanel } from '../components/tenders/TenderQAPanel';
import { tendersApi } from '../api/tendersApi';

vi.mock('../api/tendersApi');

describe('TenderQAPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders question input and submits question to retrieve grounded answer with citations', async () => {
    vi.mocked(tendersApi.askTenderQuestion).mockResolvedValue({
      tender_id: 't-1',
      question: 'What is the required warranty period?',
      answer: 'The tender requires a 5-year onsite warranty.',
      status: 'ANSWERED',
      confidence: 'HIGH',
      citations: [
        {
          document_id: 'doc-1',
          source_filename: 'specifications.pdf',
          page_number: 4,
          supporting_excerpt: '5-year onsite replacement warranty is required.',
        },
      ],
    });

    render(<TenderQAPanel tenderId="t-1" tenderTitle="Battery Procurement" />);

    expect(screen.getByText('Contextual Tender Q&A')).toBeInTheDocument();

    const input = screen.getByPlaceholderText(/What is the required turnover/i);
    const askButton = screen.getByRole('button', { name: /^Ask Question$/i });

    fireEvent.change(input, { target: { value: 'What is the required warranty period?' } });
    fireEvent.click(askButton);

    await waitFor(() => {
      expect(screen.getByText('Grounded Evidence Verified')).toBeInTheDocument();
      expect(screen.getByText('The tender requires a 5-year onsite warranty.')).toBeInTheDocument();
      expect(screen.getByText('specifications.pdf')).toBeInTheDocument();
      expect(screen.getByText('Page 4')).toBeInTheDocument();
    });
  });

  it('handles insufficient evidence status gracefully', async () => {
    vi.mocked(tendersApi.askTenderQuestion).mockResolvedValue({
      tender_id: 't-1',
      question: 'What are the rules regarding catering?',
      answer: 'The attached tender notices do not contain verifiable information answering this question.',
      status: 'INSUFFICIENT_EVIDENCE',
      confidence: 'LOW',
      citations: [],
    });

    render(<TenderQAPanel tenderId="t-1" tenderTitle="Battery Procurement" />);

    const input = screen.getByPlaceholderText(/What is the required turnover/i);
    const askButton = screen.getByRole('button', { name: /^Ask Question$/i });

    fireEvent.change(input, { target: { value: 'What are the rules regarding catering?' } });
    fireEvent.click(askButton);

    await waitFor(() => {
      expect(screen.getByText('Insufficient Evidence in Tender')).toBeInTheDocument();
      expect(
        screen.getByText(/The attached tender notices do not contain verifiable information/i)
      ).toBeInTheDocument();
    });
  });
});
