export type DocumentCategory =
  | 'FINANCIAL_AUDIT'
  | 'TAX_RECORD'
  | 'CERTIFICATION'
  | 'WORK_ORDER'
  | 'TENDER_RFP';

export const DOCUMENT_CATEGORIES: { value: DocumentCategory; label: string }[] = [
  { value: 'FINANCIAL_AUDIT', label: 'Financial Audit Report / Balance Sheet' },
  { value: 'TAX_RECORD', label: 'Tax Record / GST Return' },
  { value: 'CERTIFICATION', label: 'Corporate / MSME / ISO Certification' },
  { value: 'WORK_ORDER', label: 'Past Work Order / Performance Certificate' },
  { value: 'TENDER_RFP', label: 'Tender RFP / Document' },
];

export interface DocumentResponse {
  id: string;
  company_id: string;
  uploaded_by?: string | null;
  document_category: DocumentCategory;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  valid_from?: string | null;
  valid_until?: string | null;
  verification_status: string;
  processing_status?: string | null;
  total_pages?: number | null;
  indexed_chunks?: number;
  created_at: string;
  updated_at: string;
}
