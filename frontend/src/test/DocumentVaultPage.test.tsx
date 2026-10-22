import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DocumentVaultPage } from '../pages/vault/DocumentVaultPage';
import { documentsApi } from '../api/documentsApi';

vi.mock('../api/documentsApi');

describe('DocumentVaultPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders document items from company vault', async () => {
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([
      {
        id: 'doc-1',
        company_id: 'comp-1',
        document_category: 'FINANCIAL_AUDIT',
        original_filename: 'audited_balance_sheet_2025.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 1048576, // 1 MB
        sha256_hash: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        verification_status: 'VERIFIED_VALID',
        total_pages: 12,
        indexed_chunks: 24,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);

    render(
      <MemoryRouter>
        <DocumentVaultPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Company Document Vault')).toBeInTheDocument();
      expect(screen.getByText('audited_balance_sheet_2025.pdf')).toBeInTheDocument();
      expect(screen.getByText('FINANCIAL_AUDIT')).toBeInTheDocument();
      expect(screen.getByText('1.0 MB')).toBeInTheDocument();
      expect(screen.getByText('24 chunks')).toBeInTheDocument();
    });
  });

  it('renders empty vault state when no documents exist', async () => {
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <DocumentVaultPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Vault is empty')).toBeInTheDocument();
      expect(screen.getByText('Upload First Proof Document')).toBeInTheDocument();
    });
  });
});
