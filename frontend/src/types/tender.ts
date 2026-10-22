export interface TenderDocumentResponse {
  id: string;
  tender_id?: string | null;
  original_filename: string;
  document_category: string;
  file_size_bytes: number;
  mime_type: string;
  sha256_hash: string;
  total_pages?: number | null;
  indexed_chunks: number;
  processing_status: string;
  download_status?: string | null;
  url_classification?: string | null;
  extraction_metadata?: Record<string, unknown> | null;
  error_message?: string | null;
  created_at: string;
}

export interface FetchTenderDocumentsResponse {
  tender_id: string;
  status: 'COMPLETED' | 'PARTIAL' | 'HTML_PAGE_ONLY' | 'NO_DOCUMENTS_FOUND' | 'RESTRICTED' | 'FAILED' | string;
  url_classification: 'PDF_DOCUMENT' | 'HTML_PORTAL_PAGE' | 'RESTRICTED_ACCESS' | 'UNAVAILABLE' | 'NONE' | string;
  source_url?: string | null;
  documents_retrieved: number;
  documents_indexed: number;
  documents: TenderDocumentResponse[];
  official_portal_url?: string | null;
  message: string;
  error_details?: string | null;
}

export interface TenderBase {
  tender_reference: string;
  title: string;
  issuing_authority: string;
  sector: string;
  estimated_budget_inr?: number | null;
  emd_amount_inr?: number | null;
  msme_emd_exemption: boolean;
  publication_date?: string | null;
  submission_deadline: string;
  official_portal_url?: string | null;
  source_portal?: string | null;
  source_tender_id?: string | null;
  last_synced_at?: string | null;
  ingestion_metadata?: Record<string, unknown> | null;
  structured_requirements?: Record<string, unknown> | null;
}

export interface TenderCreatePayload extends TenderBase {}

export interface TenderUpdatePayload {
  title?: string;
  issuing_authority?: string;
  sector?: string;
  estimated_budget_inr?: number | null;
  emd_amount_inr?: number | null;
  msme_emd_exemption?: boolean;
  publication_date?: string | null;
  submission_deadline?: string;
  official_portal_url?: string | null;
  source_portal?: string | null;
  source_tender_id?: string | null;
  last_synced_at?: string | null;
  ingestion_metadata?: Record<string, unknown> | null;
  structured_requirements?: Record<string, unknown> | null;
}

export interface TenderResponse extends TenderBase {
  id: string;
  processing_status: string;
  proposed_requirements?: Record<string, unknown> | null;
  requirements_approval_status?: string;
  created_by?: string | null;
  documents: TenderDocumentResponse[];
  created_at: string;
  updated_at: string;
}

export interface ProposedCriterionItem {
  criterion_type: string;
  title: string;
  extracted_value: Record<string, unknown>;
  source_filename: string;
  page_number: number;
  document_id?: string | null;
  supporting_excerpt: string;
  status: string;
  confidence: number;
  review_notes?: string | null;
}

export interface ProposedRequirementsBundle {
  tender_id: string;
  extraction_status: string;
  criteria: ProposedCriterionItem[];
  conflicts: string[];
  unsupported_clauses: string[];
  normalized_preview?: Record<string, unknown> | null;
  extracted_at: string;
}

export interface TenderQACitation {
  document_id: string;
  source_filename: string;
  page_number: number;
  supporting_excerpt: string;
}

export interface TenderQAResponse {
  tender_id: string;
  question: string;
  answer: string;
  status: string;
  confidence: string;
  citations: TenderQACitation[];
}

export interface TenderListResponse {
  items: TenderResponse[];
  total: number;
  skip: number;
  limit: number;
  page?: number;
  pages?: number;
}

export interface TenderProcessingStatusResponse {
  tender_id: string;
  processing_status: string;
  total_documents: number;
  documents: TenderDocumentResponse[];
}

export interface IngestionPortalStatus {
  portal_name: string;
  portal_title: string;
  status: string;
  official_url: string;
  access_mode: string;
  blocker_details?: string | null;
  last_synced_at?: string | null;
  total_tenders_ingested: number;
}

export interface IngestionRunResponse {
  id: string;
  source_portal: string;
  status: string;
  tenders_found: number;
  tenders_ingested: number;
  tenders_updated: number;
  tenders_skipped: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
  run_metadata?: Record<string, any> | null;
}

export interface IngestionStatusOverviewResponse {
  scheduler_running: boolean;
  scheduler_interval_seconds: number;
  portals: IngestionPortalStatus[];
  latest_runs: IngestionRunResponse[];
}
