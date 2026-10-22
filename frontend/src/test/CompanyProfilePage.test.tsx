import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompanyProfilePage, formatINR } from '../pages/company/CompanyProfilePage';
import { companyApi } from '../api/companyApi';
import { documentsApi } from '../api/documentsApi';

vi.mock('../api/companyApi');
vi.mock('../api/documentsApi');

describe('CompanyProfilePage Component', () => {
  const mockCompany = {
    id: 'comp-101',
    owner_id: 'user-202',
    legal_name: 'Apex Industrial Systems Pvt Ltd',
    trade_name: 'Apex Systems',
    registration_number: 'UDYAM-DL-01-0012345',
    business_type: 'SMALL',
    sector: 'Electrical & Power Engineering',
    incorporation_date: '2018-05-10',
    years_in_business: 8,
    constitution: 'PRIVATE_LIMITED',
    pan_number: 'AAACA1234B',
    gstin: '07AAACA1234B1Z5',
    udyam_number: 'UDYAM-DL-01-0012345',
    dpiit_recognition_number: 'DIPP12345',
    address: {
      line1: '123 Okhla Phase III',
      city: 'New Delhi',
      state: 'Delhi',
      pincode: '110020',
      country: 'India',
    },
    contact_details: {
      signatory_name: 'A. K. Sharma',
      designation: 'Managing Director',
      email: 'md@apexsystems.in',
      phone: '+91 9811122233',
    },
    technical_capabilities: {
      core_domains: ['HT Switchgear', 'SCADA'],
      products: [{ name: 'HT Panel', hsn_code: '8537', capacity_per_month: '50 units' }],
      services: [],
      oem_status: 'OEM',
      testing_facilities: 'In-house routine testing lab',
      service_coverage: 'PAN_INDIA',
    },
    workforce_metrics: {
      total_employees: 40,
      engineers_count: 15,
      technicians_count: 10,
      project_managers_count: 3,
      service_centers_count: 2,
      emergency_support: true,
      key_personnel: [],
    },
    tender_exemptions: {
      msme_category: 'SMALL',
      emd_exemption: true,
      tender_fee_exemption: true,
      turnover_relaxation: true,
      experience_relaxation: true,
      mii_class: 'CLASS_1',
      mii_percentage: 65,
    },
    declarations: {
      non_blacklisted: true,
      no_conflict_of_interest: true,
      mii_compliant: true,
    },
    annual_turnover: [
      { fiscal_year: '2023-2024', turnover_inr: 35000000, net_worth_inr: 20000000, profit_after_tax_inr: 4500000 },
      { fiscal_year: '2022-2023', turnover_inr: 28000000, net_worth_inr: 15000000, profit_after_tax_inr: 3200000 },
      { fiscal_year: '2021-2022', turnover_inr: 22000000, net_worth_inr: 12000000, profit_after_tax_inr: 2500000 },
    ],
    certifications: [
      { name: 'ISO 9001:2015', certificate_number: 'ISO-9901', issuing_authority: 'TUV', valid_until: '2027-12-31' },
    ],
    work_experience: [
      {
        project_title: 'Supply of 33kV Switchgear',
        client_name: 'BHEL',
        client_type: 'PSU',
        contract_value_inr: 11000000,
        completion_date: '2023-01-15',
      },
    ],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  const mockReadiness = {
    overall_score: 85,
    readiness_stage: 'BID_READY' as const,
    breakdown: {
      identity_and_registration: 90,
      financial_capability: 85,
      technical_capabilities: 80,
      certifications_and_standards: 90,
      past_experience: 85,
      workforce_and_operations: 80,
      statutory_and_exemptions: 95,
    },
    satisfied_items: ['Legal entity name recorded', 'Business registration verified', '3+ fiscal years turnover recorded'],
    missing_items: [
      {
        category: 'Financial Capability',
        item: 'CA Certificate Proof',
        severity: 'MEDIUM' as const,
        recommendation: 'Link audited balance sheet from vault.',
        section_tab: 'financials',
      },
    ],
    calculated_at: '2026-01-01T12:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(companyApi.getProfile).mockResolvedValue(mockCompany);
    vi.mocked(companyApi.getReadiness).mockResolvedValue(mockReadiness);
    vi.mocked(documentsApi.listDocuments).mockResolvedValue([]);
  });

  it('renders company overview, readiness score badge and key metrics', async () => {
    render(
      <MemoryRouter>
        <CompanyProfilePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Apex Industrial Systems Pvt Ltd')).toBeInTheDocument();
      expect(screen.getByText('85% BID READY')).toBeInTheDocument();
      expect(screen.getByText('8 Years')).toBeInTheDocument();
      expect(screen.getByText('Overall Bid Readiness Score')).toBeInTheDocument();
      expect(screen.getByText('Category Readiness Breakdown')).toBeInTheDocument();
    });
  });

  it('switches between tabs accurately', async () => {
    render(
      <MemoryRouter>
        <CompanyProfilePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Apex Industrial Systems Pvt Ltd')).toBeInTheDocument();
    });

    // Switch to Identity tab
    const identityTabBtn = screen.getByRole('button', { name: /Identity & Registrations/i });
    fireEvent.click(identityTabBtn);
    expect(screen.getByText('Corporate Identity & Legal Entity')).toBeInTheDocument();
    expect(screen.getByText('Statutory Numbers & Tax Identifiers')).toBeInTheDocument();

    // Switch to Financials tab
    const financialsTabBtn = screen.getByRole('button', { name: /Financials & Turnover/i });
    fireEvent.click(financialsTabBtn);
    expect(screen.getByText('Multi-Year Audited Financial Records')).toBeInTheDocument();

    // Switch to Technical tab
    const technicalTabBtn = screen.getByRole('button', { name: /Technical Capabilities/i });
    fireEvent.click(technicalTabBtn);
    expect(screen.getByText('Technical Domain & Operational Classification')).toBeInTheDocument();
  });

  it('formats INR correctly using formatINR helper', () => {
    expect(formatINR(50000000)).toBe('₹5.00 Cr');
    expect(formatINR(2500000)).toBe('₹25.00 Lakh');
    expect(formatINR(50000)).toBe('₹50,000');
    expect(formatINR(0)).toBe('₹0');
  });
});
