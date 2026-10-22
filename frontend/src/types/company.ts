export interface TurnoverRecord {
  fiscal_year: string;
  turnover_inr: number;
  currency?: string;
}

export interface CertificationRecord {
  name: string;
  issuing_authority?: string;
  valid_until?: string;
  document_id?: string;
}

export interface WorkExperienceRecord {
  project_title: string;
  client_name: string;
  contract_value_inr: number;
  completion_date?: string;
}

export interface CompanyCreatePayload {
  legal_name: string;
  registration_number: string;
  business_type?: string;
  sector: string;
  incorporation_date: string;
  annual_turnover?: TurnoverRecord[];
  certifications?: CertificationRecord[];
  work_experience?: WorkExperienceRecord[];
}

export interface CompanyUpdatePayload {
  legal_name?: string;
  registration_number?: string;
  business_type?: string;
  sector?: string;
  incorporation_date?: string;
  annual_turnover?: TurnoverRecord[];
  certifications?: CertificationRecord[];
  work_experience?: WorkExperienceRecord[];
}

export interface CompanyResponse {
  id: string;
  owner_id: string;
  legal_name: string;
  registration_number: string;
  business_type: string;
  sector: string;
  incorporation_date: string;
  years_in_business: number;
  annual_turnover: TurnoverRecord[];
  certifications: CertificationRecord[];
  work_experience: WorkExperienceRecord[];
  created_at: string;
  updated_at: string;
}
