export interface BidApplicationResponse {
  id: string;
  company_id: string;
  tender_id: string;
  status: 'IDENTIFIED' | 'PREPARING' | 'READY' | 'SUBMITTED' | 'AWARDED' | 'REJECTED';
  notes?: string | null;
  target_submission_date?: string | null;
  created_at: string;
  updated_at: string;

  tender_title?: string | null;
  tender_reference?: string | null;
  submission_deadline?: string | null;
  estimated_budget_inr?: number | null;
  sector?: string | null;
  latest_report_id?: string | null;
  latest_compliance_status?: string | null;
  latest_compliance_score?: number | null;
}

export interface BidApplicationListResponse {
  items: BidApplicationResponse[];
  total: number;
}

export interface CreateBidApplicationPayload {
  tender_id: string;
  notes?: string;
  target_submission_date?: string;
}

export interface UpdateBidApplicationPayload {
  status?: string;
  notes?: string;
  target_submission_date?: string;
}
