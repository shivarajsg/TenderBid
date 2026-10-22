export interface TurnoverRecord {
  fiscal_year: string;
  turnover_inr: number;
  net_worth_inr?: number | null;
  profit_after_tax_inr?: number | null;
  currency?: string;
  document_id?: string | null;
}

export interface CertificationRecord {
  name: string;
  certificate_number?: string | null;
  issuing_authority?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  verification_status?: string | null;
  document_id?: string | null;
}

export interface WorkExperienceRecord {
  project_title: string;
  client_name: string;
  client_type?: string;
  contract_value_inr: number;
  work_order_number?: string | null;
  start_date?: string | null;
  completion_date?: string | null;
  status?: string;
  document_id?: string | null;
}

export interface AddressRecord {
  line1?: string;
  line2?: string;
  city?: string;
  state?: string;
  pincode?: string;
  country?: string;
}

export interface ContactDetailsRecord {
  signatory_name?: string;
  designation?: string;
  email?: string;
  phone?: string;
  website?: string;
}

export interface ProductRecord {
  name: string;
  hsn_code?: string;
  capacity_per_month?: string;
}

export interface ServiceRecord {
  name: string;
  sac_code?: string;
  description?: string;
}

export interface TechnicalCapabilitiesRecord {
  core_domains?: string[];
  products?: ProductRecord[];
  services?: ServiceRecord[];
  oem_status?: string;
  testing_facilities?: string;
  service_coverage?: string;
}

export interface KeyPersonnelRecord {
  name: string;
  designation: string;
  experience_years?: number;
  qualification?: string;
}

export interface WorkforceMetricsRecord {
  total_employees?: number;
  engineers_count?: number;
  technicians_count?: number;
  project_managers_count?: number;
  service_centers_count?: number;
  emergency_support?: boolean;
  key_personnel?: KeyPersonnelRecord[];
}

export interface TenderExemptionsRecord {
  msme_category?: string;
  emd_exemption?: boolean;
  tender_fee_exemption?: boolean;
  turnover_relaxation?: boolean;
  experience_relaxation?: boolean;
  is_dpiit_startup?: boolean;
  mii_class?: string;
  mii_percentage?: number;
  emd_document_id?: string | null;
}

export interface DeclarationsRecord {
  non_blacklisted?: boolean;
  no_conflict_of_interest?: boolean;
  mii_compliant?: boolean;
  updated_at?: string;
}

export interface CompanyCreatePayload {
  legal_name: string;
  trade_name?: string | null;
  registration_number: string;
  business_type?: string;
  sector: string;
  incorporation_date: string;
  constitution?: string;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
  dpiit_recognition_number?: string | null;
  address?: AddressRecord;
  contact_details?: ContactDetailsRecord;
  technical_capabilities?: TechnicalCapabilitiesRecord;
  workforce_metrics?: WorkforceMetricsRecord;
  tender_exemptions?: TenderExemptionsRecord;
  declarations?: DeclarationsRecord;
  annual_turnover?: TurnoverRecord[];
  certifications?: CertificationRecord[];
  work_experience?: WorkExperienceRecord[];
}

export interface CompanyUpdatePayload {
  legal_name?: string;
  trade_name?: string | null;
  registration_number?: string;
  business_type?: string;
  sector?: string;
  incorporation_date?: string;
  constitution?: string;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
  dpiit_recognition_number?: string | null;
  address?: AddressRecord;
  contact_details?: ContactDetailsRecord;
  technical_capabilities?: TechnicalCapabilitiesRecord;
  workforce_metrics?: WorkforceMetricsRecord;
  tender_exemptions?: TenderExemptionsRecord;
  declarations?: DeclarationsRecord;
  annual_turnover?: TurnoverRecord[];
  certifications?: CertificationRecord[];
  work_experience?: WorkExperienceRecord[];
}

export interface CompanyResponse {
  id: string;
  owner_id: string;
  legal_name: string;
  trade_name?: string | null;
  registration_number: string;
  business_type: string;
  sector: string;
  incorporation_date: string;
  years_in_business: number;
  constitution?: string;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
  dpiit_recognition_number?: string | null;
  address?: AddressRecord;
  contact_details?: ContactDetailsRecord;
  technical_capabilities?: TechnicalCapabilitiesRecord;
  workforce_metrics?: WorkforceMetricsRecord;
  tender_exemptions?: TenderExemptionsRecord;
  declarations?: DeclarationsRecord;
  annual_turnover: TurnoverRecord[];
  certifications: CertificationRecord[];
  work_experience: WorkExperienceRecord[];
  created_at: string;
  updated_at: string;
}

export interface MissingItemGap {
  category: string;
  item: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation: string;
  section_tab: string;
}

export interface ReadinessScoreBreakdown {
  identity_and_registration: number;
  financial_capability: number;
  technical_capabilities: number;
  certifications_and_standards: number;
  past_experience: number;
  workforce_and_operations: number;
  statutory_and_exemptions: number;
}

export interface CompanyReadinessResponse {
  overall_score: number;
  readiness_stage: 'CRITICAL_GAPS' | 'PARTIALLY_READY' | 'BID_READY';
  breakdown: ReadinessScoreBreakdown;
  satisfied_items: string[];
  missing_items: MissingItemGap[];
  calculated_at: string;
}

export interface CapabilityStatementResponse {
  generated_at: string;
  company: CompanyResponse;
  metrics: {
    years_in_business: number;
    recorded_fiscal_years: number;
    average_turnover_inr: number;
    latest_turnover_inr: number;
    latest_net_worth_inr?: number | null;
    certifications_count: number;
    completed_contracts_count: number;
    total_contract_value_inr: number;
    employee_count: number;
    engineers_count: number;
  };
  summary_text: string;
}
