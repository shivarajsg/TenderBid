export type FindingStatus =
  | 'PASS'
  | 'FAIL'
  | 'MISSING_EVIDENCE'
  | 'NEEDS_REVIEW'
  | 'NOT_APPLICABLE';

export type OverallComplianceStatus =
  | 'ELIGIBLE'
  | 'NOT_ELIGIBLE'
  | 'PARTIALLY_ELIGIBLE'
  | 'NEEDS_REVIEW'
  | 'ANALYSIS_BLOCKED_NO_DOCUMENTS';

export interface EvidenceCitation {
  evidence_id: string;
  source_type: 'TENDER_DOCUMENT' | 'COMPANY_DOCUMENT' | string;
  document_id: string;
  source_filename: string;
  page_number: number;
  excerpt: string;
  char_start?: number | null;
  char_end?: number | null;
  chunk_id?: string | null;
  retrieval_method: string;
  relevance_score?: number | null;
  sha256_hash?: string | null;
}

export interface ComplianceFindingResponse {
  id: string;
  requirement_id: string;
  rule_type: string;
  requirement_description: string;
  required_value?: Record<string, unknown> | null;
  observed_value?: Record<string, unknown> | null;
  status: FindingStatus;
  is_mandatory: boolean;
  reason: string;
  ai_explanation?: string | null;
  evidence_citations?: EvidenceCitation[] | null;
  created_at: string;

  // Section 6: Detailed 17 requirement-by-requirement fields
  category?: string | null;
  title?: string | null;
  original_clause?: string | null;
  tender_source?: string | null;
  plain_english_interpretation?: string | null;
  specific_condition?: string | null;
  applicable_company_info?: string | null;
  company_evidence?: string | null;
  comparison_evaluation?: string | null;
  evidence_gap?: string | null;
  risk_and_consequence?: string | null;
  recommended_action?: string | null;
  needs_human_review?: boolean;
}

export interface DocumentCoverageInfo {
  total_documents: number;
  indexed_documents: number;
  coverage_status: 'FULL' | 'PARTIAL' | 'UNAVAILABLE' | string;
  summary: string;
}

export interface MissingDocumentItem {
  requirement_id: string;
  document_name: string;
  category: string;
  why_required: string;
  tender_clause: string;
  tender_source?: string | null;
  available_doc_checked?: string | null;
  action_to_resolve: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  is_mandatory: boolean;
}

export interface PriorityActionItem {
  step: number;
  title: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'FINAL_SUBMISSION' | string;
  action: string;
  impact: string;
}

export interface TechnicalFinancialComparisonItem {
  parameter: string;
  required_value: string;
  observed_value: string;
  difference: string;
  status: string;
  source: string;
}

export interface ComplianceRiskItem {
  requirement_id: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  description: string;
  mitigation: string;
}

export interface SourceReferenceItem {
  source_type: string;
  document_id: string;
  filename: string;
  page_number: number;
  retrieval_method: string;
  relevance_score?: number | null;
}

export interface StatusCountsMap {
  pass: number;
  fail: number;
  missing_evidence: number;
  needs_review: number;
  not_applicable: number;
}

export interface ComplianceReportResponse {
  id: string;
  tender_id: string;
  company_id: string;
  overall_status: OverallComplianceStatus;
  overall_score?: number | null;
  summary?: string | null;
  rule_engine_version: string;
  tender_version_hash: string;
  company_version_hash: string;
  processing_metadata?: Record<string, unknown> | null;
  findings: ComplianceFindingResponse[];

  // Section 10: Structured Top-Level Fields
  analysis_completeness?: string;
  document_coverage?: DocumentCoverageInfo | null;
  requirements_identified?: number;
  requirements_evaluated?: number;
  status_counts?: StatusCountsMap | null;
  executive_summary?: string | null;
  critical_findings?: Array<{
    requirement_id: string;
    title: string;
    status: string;
    reason: string;
    action: string;
  }> | null;
  missing_documents?: MissingDocumentItem[] | null;
  priority_actions?: PriorityActionItem[] | null;
  risks?: ComplianceRiskItem[] | null;
  source_references?: SourceReferenceItem[] | null;
  technical_financial_comparisons?: TechnicalFinancialComparisonItem[] | null;
  deterministic_analysis_status?: string;
  ai_analysis_status?: string;
  limitations?: string[] | null;

  created_at: string;
  updated_at: string;
}

export interface ComplianceReportListResponse {
  items: ComplianceReportResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface ComplianceAnalyzeRequest {
  tender_id: string;
  include_ai_explanation: boolean;
}
