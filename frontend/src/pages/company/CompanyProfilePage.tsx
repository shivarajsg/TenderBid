import React, { useEffect, useState, useMemo } from 'react';
import { companyApi } from '../../api/companyApi';
import { documentsApi } from '../../api/documentsApi';
import {
  CompanyResponse,
  TurnoverRecord,
  CertificationRecord,
  WorkExperienceRecord,
  AddressRecord,
  ContactDetailsRecord,
  TechnicalCapabilitiesRecord,
  WorkforceMetricsRecord,
  TenderExemptionsRecord,
  DeclarationsRecord,
  ProductRecord,
  ServiceRecord,
  KeyPersonnelRecord,
  CompanyReadinessResponse,
  CapabilityStatementResponse,
  CompanyUpdatePayload,
  CompanyCreatePayload,
} from '../../types/company';
import { DocumentResponse, DocumentCategory, DOCUMENT_CATEGORIES } from '../../types/document';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { Modal } from '../../components/common/Modal';
import { getErrorMessage } from '../../api/client';
import {
  Building2,
  Calendar,
  Award,
  Briefcase,
  TrendingUp,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  FileText,
  ShieldCheck,
  Users,
  Check,
  Printer,
  FolderLock,
  Upload,
  ChevronRight,
  Sparkles,
  Layers,
  FileCheck2,
} from 'lucide-react';

// Indian Number & Currency Formatter Helper
export function formatINR(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val)) return '₹0.00';
  const abs = Math.abs(val);
  let formatted = '';
  if (abs >= 10000000) {
    formatted = `₹${(val / 10000000).toFixed(2)} Cr`;
  } else if (abs >= 100000) {
    formatted = `₹${(val / 100000).toFixed(2)} Lakh`;
  } else {
    formatted = new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  }
  return formatted;
}

export const CompanyProfilePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [readiness, setReadiness] = useState<CompanyReadinessResponse | null>(null);
  const [capabilityStatement, setCapabilityStatement] = useState<CapabilityStatementResponse | null>(null);
  const [vaultDocs, setVaultDocs] = useState<DocumentResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Active Tab state
  const [activeTab, setActiveTab] = useState<
    | 'overview'
    | 'identity'
    | 'financials'
    | 'technical'
    | 'certifications'
    | 'experience'
    | 'workforce'
    | 'exemptions'
    | 'vault'
    | 'statement'
  >('overview');

  // Vault Quick-Upload Modal
  const [isVaultModalOpen, setIsVaultModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState<DocumentCategory>('FINANCIAL_AUDIT');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Form State - Identity & General
  const [legalName, setLegalName] = useState('');
  const [tradeName, setTradeName] = useState('');
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [businessType, setBusinessType] = useState('SMALL');
  const [sector, setSector] = useState('');
  const [incorporationDate, setIncorporationDate] = useState('');
  const [constitution, setConstitution] = useState('PRIVATE_LIMITED');
  const [panNumber, setPanNumber] = useState('');
  const [gstin, setGstin] = useState('');
  const [udyamNumber, setUdyamNumber] = useState('');
  const [dpiitNumber, setDpiitNumber] = useState('');

  // Form State - Address
  const [address, setAddress] = useState<AddressRecord>({
    line1: '',
    line2: '',
    city: '',
    state: '',
    pincode: '',
    country: 'India',
  });

  // Form State - Contact & Signatory
  const [contactDetails, setContactDetails] = useState<ContactDetailsRecord>({
    signatory_name: '',
    designation: '',
    email: '',
    phone: '',
    website: '',
  });

  // Form State - Dynamic Records
  const [turnovers, setTurnovers] = useState<TurnoverRecord[]>([]);
  const [certifications, setCertifications] = useState<CertificationRecord[]>([]);
  const [workExperience, setWorkExperience] = useState<WorkExperienceRecord[]>([]);

  // Form State - Technical Capabilities
  const [coreDomainsStr, setCoreDomainsStr] = useState('');
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [services, setServices] = useState<ServiceRecord[]>([]);
  const [oemStatus, setOemStatus] = useState('OEM');
  const [testingFacilities, setTestingFacilities] = useState('');
  const [serviceCoverage, setServiceCoverage] = useState('PAN_INDIA');

  // Form State - Workforce
  const [totalEmployees, setTotalEmployees] = useState<number>(0);
  const [engineersCount, setEngineersCount] = useState<number>(0);
  const [techniciansCount, setTechniciansCount] = useState<number>(0);
  const [projectManagersCount, setProjectManagersCount] = useState<number>(0);
  const [serviceCentersCount, setServiceCentersCount] = useState<number>(0);
  const [emergencySupport, setEmergencySupport] = useState<boolean>(true);
  const [keyPersonnel, setKeyPersonnel] = useState<KeyPersonnelRecord[]>([]);

  // Form State - Tender Exemptions
  const [exemptions, setExemptions] = useState<TenderExemptionsRecord>({
    msme_category: 'SMALL',
    emd_exemption: true,
    tender_fee_exemption: true,
    turnover_relaxation: true,
    experience_relaxation: true,
    is_dpiit_startup: false,
    mii_class: 'CLASS_1',
    mii_percentage: 50,
  });

  // Form State - Declarations
  const [declarations, setDeclarations] = useState<DeclarationsRecord>({
    non_blacklisted: true,
    no_conflict_of_interest: true,
    mii_compliant: true,
  });

  // Load Company Profile, Readiness, and Vault Documents
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch Profile
      try {
        const data = await companyApi.getProfile();
        setCompany(data);
        setLegalName(data.legal_name || '');
        setTradeName(data.trade_name || '');
        setRegistrationNumber(data.registration_number || '');
        setBusinessType(data.business_type || 'SMALL');
        setSector(data.sector || '');
        setIncorporationDate(data.incorporation_date || '');
        setConstitution(data.constitution || 'PRIVATE_LIMITED');
        setPanNumber(data.pan_number || '');
        setGstin(data.gstin || '');
        setUdyamNumber(data.udyam_number || '');
        setDpiitNumber(data.dpiit_recognition_number || '');

        if (data.address) setAddress({ ...data.address });
        if (data.contact_details) setContactDetails({ ...data.contact_details });

        setTurnovers(data.annual_turnover || []);
        setCertifications(data.certifications || []);
        setWorkExperience(data.work_experience || []);

        if (data.technical_capabilities) {
          const tc = data.technical_capabilities;
          setCoreDomainsStr(tc.core_domains ? tc.core_domains.join(', ') : '');
          setProducts(tc.products || []);
          setServices(tc.services || []);
          setOemStatus(tc.oem_status || 'OEM');
          setTestingFacilities(tc.testing_facilities || '');
          setServiceCoverage(tc.service_coverage || 'PAN_INDIA');
        }

        if (data.workforce_metrics) {
          const wf = data.workforce_metrics;
          setTotalEmployees(wf.total_employees || 0);
          setEngineersCount(wf.engineers_count || 0);
          setTechniciansCount(wf.technicians_count || 0);
          setProjectManagersCount(wf.project_managers_count || 0);
          setServiceCentersCount(wf.service_centers_count || 0);
          setEmergencySupport(wf.emergency_support !== false);
          setKeyPersonnel(wf.key_personnel || []);
        }

        if (data.tender_exemptions) {
          setExemptions({ ...data.tender_exemptions });
        }

        if (data.declarations) {
          setDeclarations({ ...data.declarations });
        }
      } catch {
        setCompany(null);
      }

      // 2. Fetch Readiness
      try {
        const readyData = await companyApi.getReadiness();
        setReadiness(readyData);
      } catch {
        setReadiness(null);
      }

      // 3. Fetch Vault Documents for linking
      try {
        const docs = await documentsApi.listDocuments();
        setVaultDocs(docs);
      } catch {
        setVaultDocs([]);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Fetch Capability Statement when statement tab clicked
  const handleOpenStatementTab = async () => {
    setActiveTab('statement');
    try {
      const stmt = await companyApi.getCapabilityStatement();
      setCapabilityStatement(stmt);
    } catch {
      // ignored
    }
  };

  // Average Turnover Calculation
  const avgTurnover = useMemo(() => {
    if (!turnovers || turnovers.length === 0) return 0;
    const total = turnovers.reduce((sum, t) => sum + (Number(t.turnover_inr) || 0), 0);
    return total / turnovers.length;
  }, [turnovers]);

  // Total Completed Contracts Value
  const totalContractsValue = useMemo(() => {
    if (!workExperience || workExperience.length === 0) return 0;
    return workExperience.reduce((sum, w) => sum + (Number(w.contract_value_inr) || 0), 0);
  }, [workExperience]);

  // Turnovers Handler
  const handleAddTurnover = () => {
    const nextYear = `${new Date().getFullYear() - 1}-${new Date().getFullYear()}`;
    setTurnovers([
      ...turnovers,
      { fiscal_year: nextYear, turnover_inr: 0, net_worth_inr: 0, profit_after_tax_inr: 0, currency: 'INR' },
    ]);
  };

  const handleUpdateTurnover = (index: number, field: keyof TurnoverRecord, value: string | number | null) => {
    const updated = [...turnovers];
    let sanitizedVal = value;
    if (field === 'turnover_inr' || field === 'net_worth_inr' || field === 'profit_after_tax_inr') {
      if (typeof value === 'string') {
        const cleanStr = value.replace(/,/g, '').trim();
        sanitizedVal = cleanStr === '' ? 0 : Number(cleanStr);
      }
    }
    updated[index] = { ...updated[index], [field]: sanitizedVal };
    setTurnovers(updated);
  };

  const handleRemoveTurnover = (index: number) => {
    setTurnovers(turnovers.filter((_, i) => i !== index));
  };

  // Certifications Handler
  const handleAddCertification = () => {
    setCertifications([
      ...certifications,
      { name: 'ISO 9001:2015', issuing_authority: '', verification_status: 'VERIFIED_VALID' },
    ]);
  };

  const handleUpdateCertification = (index: number, field: keyof CertificationRecord, value: string | null) => {
    const updated = [...certifications];
    updated[index] = { ...updated[index], [field]: value };
    setCertifications(updated);
  };

  const handleRemoveCertification = (index: number) => {
    setCertifications(certifications.filter((_, i) => i !== index));
  };

  // Work Experience Handler
  const handleAddExperience = () => {
    setWorkExperience([
      ...workExperience,
      {
        project_title: '',
        client_name: '',
        client_type: 'CENTRAL_GOVT',
        contract_value_inr: 0,
        status: 'COMPLETED',
      },
    ]);
  };

  const handleUpdateExperience = (
    index: number,
    field: keyof WorkExperienceRecord,
    value: string | number | null
  ) => {
    const updated = [...workExperience];
    let sanitizedVal = value;
    if (field === 'contract_value_inr' && typeof value === 'string') {
      const cleanStr = value.replace(/,/g, '').trim();
      sanitizedVal = cleanStr === '' ? 0 : Number(cleanStr);
    }
    updated[index] = { ...updated[index], [field]: sanitizedVal };
    setWorkExperience(updated);
  };

  const handleRemoveExperience = (index: number) => {
    setWorkExperience(workExperience.filter((_, i) => i !== index));
  };

  // Products Handler
  const handleAddProduct = () => {
    setProducts([...products, { name: '', hsn_code: '', capacity_per_month: '' }]);
  };

  const handleUpdateProduct = (index: number, field: keyof ProductRecord, val: string) => {
    const updated = [...products];
    updated[index] = { ...updated[index], [field]: val };
    setProducts(updated);
  };

  const handleRemoveProduct = (index: number) => {
    setProducts(products.filter((_, i) => i !== index));
  };

  // Services Handler
  const handleAddService = () => {
    setServices([...services, { name: '', sac_code: '', description: '' }]);
  };

  const handleUpdateService = (index: number, field: keyof ServiceRecord, val: string) => {
    const updated = [...services];
    updated[index] = { ...updated[index], [field]: val };
    setServices(updated);
  };

  const handleRemoveService = (index: number) => {
    setServices(services.filter((_, i) => i !== index));
  };

  // Key Personnel Handler
  const handleAddPersonnel = () => {
    setKeyPersonnel([...keyPersonnel, { name: '', designation: '', experience_years: 5, qualification: '' }]);
  };

  const handleUpdatePersonnel = (index: number, field: keyof KeyPersonnelRecord, val: string | number) => {
    const updated = [...keyPersonnel];
    updated[index] = { ...updated[index], [field]: val };
    setKeyPersonnel(updated);
  };

  const handleRemovePersonnel = (index: number) => {
    setKeyPersonnel(keyPersonnel.filter((_, i) => i !== index));
  };

  // Vault Quick Upload Submit
  const handleVaultUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a file to upload.');
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      await documentsApi.uploadDocument(uploadFile, uploadCategory);
      setIsVaultModalOpen(false);
      setUploadFile(null);
      const docs = await documentsApi.listDocuments();
      setVaultDocs(docs);
      setSuccessMsg('Document successfully uploaded to Company Vault.');
    } catch (err: unknown) {
      setUploadError(getErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  // Submit Save Profile
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const domains = coreDomainsStr
      .split(',')
      .map((d) => d.trim())
      .filter((d) => d.length > 0);

    const payload: CompanyUpdatePayload | CompanyCreatePayload = {
      legal_name: legalName.trim(),
      trade_name: tradeName.trim() || undefined,
      registration_number: registrationNumber.trim().toUpperCase(),
      business_type: businessType,
      sector: sector.trim(),
      incorporation_date: incorporationDate,
      constitution,
      pan_number: panNumber.trim().toUpperCase() || undefined,
      gstin: gstin.trim().toUpperCase() || undefined,
      udyam_number: udyamNumber.trim().toUpperCase() || undefined,
      dpiit_recognition_number: dpiitNumber.trim() || undefined,
      address,
      contact_details: contactDetails,
      technical_capabilities: {
        core_domains: domains,
        products,
        services,
        oem_status: oemStatus,
        testing_facilities: testingFacilities,
        service_coverage: serviceCoverage,
      },
      workforce_metrics: {
        total_employees: Number(totalEmployees) || 0,
        engineers_count: Number(engineersCount) || 0,
        technicians_count: Number(techniciansCount) || 0,
        project_managers_count: Number(projectManagersCount) || 0,
        service_centers_count: Number(serviceCentersCount) || 0,
        emergency_support: emergencySupport,
        key_personnel: keyPersonnel,
      },
      tender_exemptions: {
        ...exemptions,
        msme_category: businessType,
      },
      declarations,
      annual_turnover: turnovers.map((t) => ({
        ...t,
        turnover_inr: Number(t.turnover_inr) || 0,
        net_worth_inr: t.net_worth_inr !== undefined && t.net_worth_inr !== null ? Number(t.net_worth_inr) : undefined,
        profit_after_tax_inr:
          t.profit_after_tax_inr !== undefined && t.profit_after_tax_inr !== null
            ? Number(t.profit_after_tax_inr)
            : undefined,
      })),
      certifications: certifications.map((c) => ({
        ...c,
        name: c.name.trim(),
      })),
      work_experience: workExperience.map((w) => ({
        ...w,
        contract_value_inr: Number(w.contract_value_inr) || 0,
      })),
    };

    try {
      let savedCompany: CompanyResponse;
      if (company) {
        savedCompany = await companyApi.updateProfile(payload);
      } else {
        savedCompany = await companyApi.createProfile(payload as CompanyCreatePayload);
      }
      setCompany(savedCompany);
      setSuccessMsg('Company Capability & Compliance Profile successfully saved.');

      // Refresh readiness
      try {
        const readyData = await companyApi.getReadiness();
        setReadiness(readyData);
      } catch {
        // ignored
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading Company Capability & Compliance Profile..." />;
  }

  return (
    <div className="space-y-6 max-w-6xl pb-16">
      {/* Enterprise Top Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              {legalName || 'MSME Company Capability Profile'}
            </h1>
            {readiness && (
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                  readiness.readiness_stage === 'BID_READY'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : readiness.readiness_stage === 'PARTIALLY_READY'
                    ? 'bg-amber-100 text-amber-800 border border-amber-300'
                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 mr-1" />
                {readiness.overall_score}% {readiness.readiness_stage.replace('_', ' ')}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Registered credentials and verified document evidence utilized by the deterministic compliance engine.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            icon={<Printer className="w-4 h-4" />}
            onClick={handleOpenStatementTab}
          >
            Capability Statement
          </Button>
          <Button
            type="button"
            size="sm"
            isLoading={saving}
            icon={<Save className="w-4 h-4" />}
            onClick={() => handleSubmit()}
          >
            {company ? 'Save Changes' : 'Initialize Profile'}
          </Button>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center justify-between gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-xs font-medium text-emerald-700 hover:text-emerald-900"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white rounded-xl shadow-xs p-1.5 flex items-center gap-1 overflow-x-auto text-sm">
        {[
          { id: 'overview', label: 'Overview & Readiness', icon: Layers },
          { id: 'identity', label: 'Identity & Registrations', icon: Building2 },
          { id: 'financials', label: 'Financials & Turnover', icon: TrendingUp },
          { id: 'technical', label: 'Technical Capabilities', icon: Briefcase },
          { id: 'certifications', label: 'Certifications', icon: Award },
          { id: 'experience', label: 'Past Experience', icon: Calendar },
          { id: 'workforce', label: 'Workforce & Capacity', icon: Users },
          { id: 'exemptions', label: 'Tender Exemptions', icon: ShieldCheck },
          { id: 'vault', label: 'Document Vault', icon: FolderLock },
          { id: 'statement', label: 'Capability Statement', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                if (tab.id === 'statement') {
                  handleOpenStatementTab();
                } else {
                  setActiveTab(tab.id as typeof activeTab);
                }
              }}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & READINESS DASHBOARD */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Years in Operation
              </span>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {company ? `${company.years_in_business} Years` : 'Unverified'}
              </div>
              <p className="text-xs text-slate-400 mt-1">From incorporation date</p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                3-Year Avg Turnover
              </span>
              <div className="text-2xl font-bold text-emerald-600 mt-1">
                {formatINR(avgTurnover)}
              </div>
              <p className="text-xs text-slate-400 mt-1">Based on {turnovers.length} fiscal records</p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Active Certifications
              </span>
              <div className="text-2xl font-bold text-purple-600 mt-1">
                {certifications.length} Registered
              </div>
              <p className="text-xs text-slate-400 mt-1">Quality & ISO credentials</p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Completed Contracts
              </span>
              <div className="text-2xl font-bold text-amber-600 mt-1">
                {workExperience.length} ({formatINR(totalContractsValue)})
              </div>
              <p className="text-xs text-slate-400 mt-1">Track record in public / private bids</p>
            </div>
          </div>

          {/* Readiness Gauge & Breakdown */}
          {readiness && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Overall Score */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-blue-600" />
                    Overall Bid Readiness Score
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Evaluated against standard public procurement eligibility rules.
                  </p>
                </div>

                <div className="my-6 flex flex-col items-center justify-center">
                  <div className="relative w-36 h-36 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-slate-100"
                        strokeWidth="3.5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className={
                          readiness.overall_score >= 80
                            ? 'text-emerald-500'
                            : readiness.overall_score >= 50
                            ? 'text-amber-500'
                            : 'text-rose-500'
                        }
                        strokeDasharray={`${readiness.overall_score}, 100`}
                        strokeWidth="3.5"
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute text-center">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {readiness.overall_score}%
                      </span>
                      <span className="block text-2xs text-slate-500 font-semibold uppercase">
                        {readiness.readiness_stage.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-xs text-slate-500 border-t border-slate-100 pt-3 flex items-center justify-between">
                  <span>Last Evaluated:</span>
                  <span className="font-medium text-slate-700">
                    {new Date(readiness.calculated_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>

              {/* Category Breakdown Bars */}
              <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <h3 className="text-base font-semibold text-slate-900">Category Readiness Breakdown</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Identity & Legal Registrations', score: readiness.breakdown.identity_and_registration },
                    { label: 'Financial Capability & Turnover', score: readiness.breakdown.financial_capability },
                    { label: 'Technical Capabilities & Offerings', score: readiness.breakdown.technical_capabilities },
                    { label: 'Certifications & Quality Standards', score: readiness.breakdown.certifications_and_standards },
                    { label: 'Past Experience & Work Orders', score: readiness.breakdown.past_experience },
                    { label: 'Workforce & Operational Capacity', score: readiness.breakdown.workforce_and_operations },
                    { label: 'Statutory Declarations & MSME Exemptions', score: readiness.breakdown.statutory_and_exemptions },
                  ].map((cat, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-slate-700">{cat.label}</span>
                        <span className="text-slate-900 font-bold">{cat.score}%</span>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            cat.score >= 80 ? 'bg-emerald-500' : cat.score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                          }`}
                          style={{ width: `${cat.score}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Actionable Gaps & Satisfied Checklist */}
          {readiness && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Missing Gaps */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Recommended Improvements ({readiness.missing_items.length})
                </h3>
                {readiness.missing_items.length === 0 ? (
                  <p className="text-sm text-emerald-600 font-medium">
                    All core requirements and document evidences are satisfied!
                  </p>
                ) : (
                  <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                    {readiness.missing_items.map((gap, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 space-y-1 text-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-800">{gap.item}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-2xs font-bold uppercase ${
                              gap.severity === 'HIGH'
                                ? 'bg-rose-100 text-rose-700'
                                : gap.severity === 'MEDIUM'
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-blue-100 text-blue-700'
                            }`}
                          >
                            {gap.severity}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600">{gap.recommendation}</p>
                        <div className="pt-1 flex justify-end">
                          <button
                            type="button"
                            onClick={() => {
                              if (gap.section_tab === 'identity') setActiveTab('identity');
                              else if (gap.section_tab === 'financials') setActiveTab('financials');
                              else if (gap.section_tab === 'technical') setActiveTab('technical');
                              else if (gap.section_tab === 'certifications') setActiveTab('certifications');
                              else if (gap.section_tab === 'experience') setActiveTab('experience');
                              else if (gap.section_tab === 'workforce') setActiveTab('workforce');
                              else if (gap.section_tab === 'exemptions') setActiveTab('exemptions');
                            }}
                            className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                          >
                            <span>Resolve in {gap.category}</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Satisfied Criteria */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Satisfied Credentials ({readiness.satisfied_items.length})
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {readiness.satisfied_items.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2.5 p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-100 text-xs text-emerald-900"
                    >
                      <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: IDENTITY & REGISTRATIONS */}
      {activeTab === 'identity' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Building2 className="w-5 h-5 text-blue-600" />
              Corporate Identity & Legal Entity
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Legal Entity Name"
                required
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                placeholder="e.g. Apex Electrical Systems Pvt Ltd"
              />

              <Input
                label="Trade / Brand Name (Optional)"
                value={tradeName}
                onChange={(e) => setTradeName(e.target.value)}
                placeholder="e.g. Apex Power"
              />

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Constitution of Business <span className="text-rose-500">*</span>
                </label>
                <select
                  value={constitution}
                  onChange={(e) => setConstitution(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                >
                  <option value="PRIVATE_LIMITED">Private Limited Company</option>
                  <option value="PROPRIETORSHIP">Sole Proprietorship</option>
                  <option value="PARTNERSHIP">Partnership Firm</option>
                  <option value="LLP">Limited Liability Partnership (LLP)</option>
                  <option value="PUBLIC_LIMITED">Public Limited Company</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  MSME Classification <span className="text-rose-500">*</span>
                </label>
                <select
                  value={businessType}
                  onChange={(e) => setBusinessType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                >
                  <option value="MICRO">Micro Enterprise (&lt; ₹5 Cr turnover)</option>
                  <option value="SMALL">Small Enterprise (&lt; ₹50 Cr turnover)</option>
                  <option value="MEDIUM">Medium Enterprise (&lt; ₹250 Cr turnover)</option>
                </select>
              </div>

              <Input
                label="Primary Business Sector / Domain"
                required
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="e.g. Electrical Engineering / Power Infrastructure"
              />

              <Input
                label="Date of Incorporation"
                type="date"
                required
                value={incorporationDate}
                onChange={(e) => setIncorporationDate(e.target.value)}
                helperText={
                  company ? `Verified years in business: ${company.years_in_business} years` : undefined
                }
              />
            </div>
          </div>

          {/* Statutory Registration Numbers */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              Statutory Numbers & Tax Identifiers
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Registration / CIN / LLPIN Number"
                required
                value={registrationNumber}
                onChange={(e) => setRegistrationNumber(e.target.value.toUpperCase())}
                placeholder="e.g. U74999DL2018PTC123456"
              />

              <Input
                label="Udyam Registration Number"
                value={udyamNumber}
                onChange={(e) => setUdyamNumber(e.target.value.toUpperCase())}
                placeholder="e.g. UDYAM-DL-01-0012345"
                helperText="Required for MSME EMD & turnover relaxation"
              />

              <Input
                label="Permanent Account Number (PAN)"
                value={panNumber}
                onChange={(e) => setPanNumber(e.target.value.toUpperCase())}
                maxLength={10}
                placeholder="e.g. ABCDE1234F"
              />

              <Input
                label="Goods & Services Tax Identification (GSTIN)"
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                maxLength={15}
                placeholder="e.g. 07ABCDE1234F1Z5"
              />

              <Input
                label="DPIIT Startup Recognition Number (Optional)"
                value={dpiitNumber}
                onChange={(e) => setDpiitNumber(e.target.value)}
                placeholder="e.g. DIPP12345"
              />
            </div>
          </div>

          {/* Registered Address */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3">
              Registered Corporate Address
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Address Line 1"
                value={address.line1 || ''}
                onChange={(e) => setAddress({ ...address, line1: e.target.value })}
                placeholder="Plot / Street / Building Name"
              />

              <Input
                label="Address Line 2"
                value={address.line2 || ''}
                onChange={(e) => setAddress({ ...address, line2: e.target.value })}
                placeholder="Area / Landmark"
              />

              <Input
                label="City / District"
                value={address.city || ''}
                onChange={(e) => setAddress({ ...address, city: e.target.value })}
                placeholder="e.g. New Delhi"
              />

              <Input
                label="State / Union Territory"
                value={address.state || ''}
                onChange={(e) => setAddress({ ...address, state: e.target.value })}
                placeholder="e.g. Delhi"
              />

              <Input
                label="Postal PIN Code"
                value={address.pincode || ''}
                onChange={(e) => setAddress({ ...address, pincode: e.target.value })}
                placeholder="e.g. 110001"
              />

              <Input
                label="Country"
                value={address.country || 'India'}
                onChange={(e) => setAddress({ ...address, country: e.target.value })}
              />
            </div>
          </div>

          {/* Authorized Signatory Details */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3">
              Authorized Signatory & Official Contact
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Authorized Signatory Name"
                value={contactDetails.signatory_name || ''}
                onChange={(e) =>
                  setContactDetails({ ...contactDetails, signatory_name: e.target.value })
                }
                placeholder="e.g. Vikramaditya Sen"
              />

              <Input
                label="Signatory Designation"
                value={contactDetails.designation || ''}
                onChange={(e) =>
                  setContactDetails({ ...contactDetails, designation: e.target.value })
                }
                placeholder="e.g. Managing Director / Partner"
              />

              <Input
                label="Official Tender Email"
                type="email"
                value={contactDetails.email || ''}
                onChange={(e) => setContactDetails({ ...contactDetails, email: e.target.value })}
                placeholder="tenders@apexpower.in"
              />

              <Input
                label="Official Phone / Mobile"
                value={contactDetails.phone || ''}
                onChange={(e) => setContactDetails({ ...contactDetails, phone: e.target.value })}
                placeholder="+91 9876543210"
              />
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: FINANCIAL CAPABILITY */}
      {activeTab === 'financials' && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl p-6 text-white shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-100">
                Audited Financial Strength
              </span>
              <div className="text-3xl font-bold mt-1">{formatINR(avgTurnover)}</div>
              <p className="text-xs text-emerald-100 mt-1">
                Average annual turnover computed across {turnovers.length} recorded fiscal year(s).
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm px-4 py-3 rounded-xl border border-white/20 text-xs">
              <span className="font-semibold block">Compliance Engine Check:</span>
              <span>Requires &ge; 3 consecutive audited years with positive net worth.</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  Multi-Year Audited Financial Records
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Record exact figures in INR. Link CA certificates from your vault to satisfy proof clauses.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddTurnover}
              >
                Add Fiscal Year
              </Button>
            </div>

            {turnovers.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <TrendingUp className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No turnover records added yet.</p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={handleAddTurnover}
                >
                  Add First Fiscal Year
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {turnovers.map((t, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <div>
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          Fiscal Year
                        </label>
                        <input
                          type="text"
                          value={t.fiscal_year}
                          onChange={(e) => handleUpdateTurnover(index, 'fiscal_year', e.target.value)}
                          placeholder="e.g. 2023-2024"
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-2xs font-semibold text-slate-600 uppercase">
                            Audited Turnover (INR)
                          </label>
                          <span className="text-2xs font-bold text-emerald-600">
                            {formatINR(t.turnover_inr)}
                          </span>
                        </div>
                        <input
                          type="number"
                          value={t.turnover_inr || ''}
                          onChange={(e) => handleUpdateTurnover(index, 'turnover_inr', e.target.value)}
                          placeholder="e.g. 25000000"
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-2xs font-semibold text-slate-600 uppercase">
                            Net Worth (INR)
                          </label>
                          <span className="text-2xs font-bold text-blue-600">
                            {formatINR(t.net_worth_inr)}
                          </span>
                        </div>
                        <input
                          type="number"
                          value={t.net_worth_inr ?? ''}
                          onChange={(e) => handleUpdateTurnover(index, 'net_worth_inr', e.target.value)}
                          placeholder="e.g. 15000000"
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-2xs font-semibold text-slate-600 uppercase">
                            PAT / Net Profit (INR)
                          </label>
                          <span className="text-2xs font-bold text-purple-600">
                            {formatINR(t.profit_after_tax_inr)}
                          </span>
                        </div>
                        <input
                          type="number"
                          value={t.profit_after_tax_inr ?? ''}
                          onChange={(e) =>
                            handleUpdateTurnover(index, 'profit_after_tax_inr', e.target.value)
                          }
                          placeholder="e.g. 3500000"
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-200/80">
                      <div className="flex items-center gap-2 flex-1">
                        <FolderLock className="w-4 h-4 text-slate-400 shrink-0" />
                        <select
                          value={t.document_id || ''}
                          onChange={(e) =>
                            handleUpdateTurnover(index, 'document_id', e.target.value || null)
                          }
                          className="w-full sm:max-w-md text-xs bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none"
                        >
                          <option value="">-- Link CA Certificate / Balance Sheet from Vault --</option>
                          {vaultDocs.map((doc) => (
                            <option key={doc.id} value={doc.id}>
                              {doc.original_filename} ({doc.document_category})
                            </option>
                          ))}
                        </select>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setUploadCategory('FINANCIAL_AUDIT');
                            setIsVaultModalOpen(true);
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          + Upload New Doc
                        </Button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveTurnover(index)}
                        className="text-slate-400 hover:text-rose-600 text-xs flex items-center gap-1 self-end sm:self-center"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Remove Year</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: TECHNICAL EXPERTISE & CAPABILITIES */}
      {activeTab === 'technical' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Briefcase className="w-5 h-5 text-blue-600" />
              Technical Domain & Operational Classification
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  OEM / Supplier Classification
                </label>
                <select
                  value={oemStatus}
                  onChange={(e) => setOemStatus(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                >
                  <option value="OEM">Original Equipment Manufacturer (OEM)</option>
                  <option value="AUTHORIZED_DEALER">Authorized Dealer / Channel Partner</option>
                  <option value="SYSTEM_INTEGRATOR">System Integrator / Solution Provider</option>
                  <option value="EPC_CONTRACTOR">Turnkey EPC Contractor</option>
                  <option value="SERVICE_PROVIDER">Specialized Technical Service Provider</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Geographical Service Coverage
                </label>
                <select
                  value={serviceCoverage}
                  onChange={(e) => setServiceCoverage(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                >
                  <option value="PAN_INDIA">Pan-India (All States & UTs)</option>
                  <option value="REGIONAL">Regional (North / South / East / West)</option>
                  <option value="STATE">State-Specific Operations</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <Input
                  label="Core Competencies & Keywords (comma-separated)"
                  value={coreDomainsStr}
                  onChange={(e) => setCoreDomainsStr(e.target.value)}
                  placeholder="e.g. HT/LT Switchgear, SCADA Integration, Solar Photovoltaic EPC, Power Transformers"
                  helperText="These keywords are matched against tender technical specifications during compliance analysis."
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  In-House Testing, QA & QC Facilities
                </label>
                <textarea
                  rows={3}
                  value={testingFacilities}
                  onChange={(e) => setTestingFacilities(e.target.value)}
                  placeholder="Describe your testing equipment, NABL-accredited test bench, calibration standards, or quality assurance laboratory."
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Products Catalog */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-semibold text-slate-800">
                  Major Products Manufactured / Supplied
                </h3>
                <p className="text-xs text-slate-500">
                  Used for automated GeM category and BOQ item clause evaluation.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddProduct}
              >
                Add Product
              </Button>
            </div>

            {products.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No products listed.</p>
            ) : (
              <div className="space-y-3">
                {products.map((p, idx) => (
                  <div key={idx} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Product Name (e.g. 11kV Vacuum Circuit Breaker)"
                        value={p.name}
                        onChange={(e) => handleUpdateProduct(idx, 'name', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-36">
                      <input
                        type="text"
                        placeholder="HSN Code"
                        value={p.hsn_code || ''}
                        onChange={(e) => handleUpdateProduct(idx, 'hsn_code', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-44">
                      <input
                        type="text"
                        placeholder="Monthly Capacity"
                        value={p.capacity_per_month || ''}
                        onChange={(e) => handleUpdateProduct(idx, 'capacity_per_month', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveProduct(idx)}
                      className="text-slate-400 hover:text-rose-600 p-2"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Services Catalog */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-semibold text-slate-800">
                  Major Services Offered
                </h3>
                <p className="text-xs text-slate-500">
                  Technical, maintenance, engineering, or testing services provided.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddService}
              >
                Add Service
              </Button>
            </div>

            {services.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No services listed.</p>
            ) : (
              <div className="space-y-3">
                {services.map((s, idx) => (
                  <div key={idx} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Service Name (e.g. Substation Maintenance & Testing)"
                        value={s.name}
                        onChange={(e) => handleUpdateService(idx, 'name', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-36">
                      <input
                        type="text"
                        placeholder="SAC Code"
                        value={s.sac_code || ''}
                        onChange={(e) => handleUpdateService(idx, 'sac_code', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveService(idx)}
                      className="text-slate-400 hover:text-rose-600 p-2"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: CERTIFICATIONS & LEGAL COMPLIANCE */}
      {activeTab === 'certifications' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <Award className="w-5 h-5 text-purple-600" />
                  Corporate, Quality & Industry Certifications
                </h2>
                <p className="text-xs text-slate-500">
                  ISO, BIS, CE, and statutory certifications matched against tender eligibility criteria.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddCertification}
              >
                Add Certification
              </Button>
            </div>

            {certifications.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No certifications listed.</p>
            ) : (
              <div className="space-y-4">
                {certifications.map((c, index) => {
                  const isExpired = c.valid_until && new Date(c.valid_until) < new Date();
                  return (
                    <div
                      key={index}
                      className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className="md:col-span-2">
                          <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                            Certification Name
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. ISO 9001:2015, ISO 14001, BIS / ISI Mark"
                            value={c.name}
                            onChange={(e) =>
                              handleUpdateCertification(index, 'name', e.target.value)
                            }
                            className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                          />
                        </div>

                        <div>
                          <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                            Certificate Number
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. CERT-2024-9988"
                            value={c.certificate_number || ''}
                            onChange={(e) =>
                              handleUpdateCertification(index, 'certificate_number', e.target.value)
                            }
                            className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                          />
                        </div>

                        <div>
                          <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                            Issuing Authority
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. TUV, BSI, Bureau Veritas"
                            value={c.issuing_authority || ''}
                            onChange={(e) =>
                              handleUpdateCertification(index, 'issuing_authority', e.target.value)
                            }
                            className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                          />
                        </div>

                        <div>
                          <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                            Valid Until / Expiry Date
                          </label>
                          <input
                            type="date"
                            value={c.valid_until || ''}
                            onChange={(e) =>
                              handleUpdateCertification(index, 'valid_until', e.target.value)
                            }
                            className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                          />
                        </div>

                        <div className="md:col-span-3 flex items-center gap-2 pt-1">
                          <span
                            className={`px-2 py-0.5 rounded text-2xs font-bold uppercase ${
                              isExpired
                                ? 'bg-rose-100 text-rose-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {isExpired ? 'EXPIRED' : 'ACTIVE'}
                          </span>
                          <FolderLock className="w-4 h-4 text-slate-400 shrink-0 ml-2" />
                          <select
                            value={c.document_id || ''}
                            onChange={(e) =>
                              handleUpdateCertification(index, 'document_id', e.target.value || null)
                            }
                            className="text-xs bg-white border border-slate-300 rounded-md px-2.5 py-1 text-slate-700 flex-1 max-w-sm"
                          >
                            <option value="">-- Link Certificate PDF from Vault --</option>
                            {vaultDocs.map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.original_filename}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => handleRemoveCertification(index)}
                          className="text-slate-400 hover:text-rose-600 text-xs flex items-center gap-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Remove</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Statutory Declarations */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              Statutory Declarations & Affidavits
            </h2>

            <div className="space-y-3">
              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors">
                <input
                  type="checkbox"
                  checked={declarations.non_blacklisted ?? true}
                  onChange={(e) =>
                    setDeclarations({ ...declarations, non_blacklisted: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    Non-Blacklisting & Non-Debarment Self-Declaration
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    We hereby certify that our company has never been blacklisted, debarred, or sanctioned by any Central Government Ministry, State Government, PSU, or Public Procurement Authority.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors">
                <input
                  type="checkbox"
                  checked={declarations.no_conflict_of_interest ?? true}
                  onChange={(e) =>
                    setDeclarations({ ...declarations, no_conflict_of_interest: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    No Conflict of Interest Affirmation
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    We confirm there exists no conflict of interest between our firm and any procurement officials of tendering authorities.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors">
                <input
                  type="checkbox"
                  checked={declarations.mii_compliant ?? true}
                  onChange={(e) =>
                    setDeclarations({ ...declarations, mii_compliant: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    Make in India Local Content Compliance
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    We affirm compliance with Public Procurement (Preference to Make in India) Order 2017 for goods and services offered.
                  </p>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: PAST PROJECTS & EXPERIENCE */}
      {activeTab === 'experience' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-amber-600" />
                  Past Projects & Completed Contracts Track Record
                </h2>
                <p className="text-xs text-slate-500">
                  Total Value: <span className="font-bold text-slate-900">{formatINR(totalContractsValue)}</span> across {workExperience.length} contract(s).
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddExperience}
              >
                Add Work Experience
              </Button>
            </div>

            {workExperience.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No past contracts listed yet.</p>
            ) : (
              <div className="space-y-4">
                {workExperience.map((w, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <div className="md:col-span-2">
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          Project / Contract Title
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. Supply & Installation of 33kV Substation Panels"
                          value={w.project_title}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'project_title', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          Client Organization
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. BHEL, NTPC, Indian Railways"
                          value={w.client_name}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'client_name', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          Client Type
                        </label>
                        <select
                          value={w.client_type || 'CENTRAL_GOVT'}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'client_type', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        >
                          <option value="CENTRAL_GOVT">Central Government</option>
                          <option value="STATE_GOVT">State Government</option>
                          <option value="PSU">Public Sector Undertaking (PSU)</option>
                          <option value="DEFENSE_RAILWAYS">Defense / Railways</option>
                          <option value="PRIVATE">Private Enterprise</option>
                        </select>
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-2xs font-semibold text-slate-600 uppercase">
                            Contract Value (INR)
                          </label>
                          <span className="text-2xs font-bold text-amber-600">
                            {formatINR(w.contract_value_inr)}
                          </span>
                        </div>
                        <input
                          type="number"
                          placeholder="e.g. 8500000"
                          value={w.contract_value_inr || ''}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'contract_value_inr', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          PO / Work Order Number
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. PO/2023/BHEL/889"
                          value={w.work_order_number || ''}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'work_order_number', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-2xs font-semibold text-slate-600 uppercase mb-1">
                          Completion Date
                        </label>
                        <input
                          type="date"
                          value={w.completion_date || ''}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'completion_date', e.target.value)
                          }
                          className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none"
                        />
                      </div>

                      <div className="flex items-center gap-2 pt-5">
                        <FolderLock className="w-4 h-4 text-slate-400 shrink-0" />
                        <select
                          value={w.document_id || ''}
                          onChange={(e) =>
                            handleUpdateExperience(index, 'document_id', e.target.value || null)
                          }
                          className="text-xs bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-700 w-full"
                        >
                          <option value="">-- Link Completion Certificate --</option>
                          {vaultDocs.map((doc) => (
                            <option key={doc.id} value={doc.id}>
                              {doc.original_filename}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={() => handleRemoveExperience(index)}
                        className="text-slate-400 hover:text-rose-600 text-xs flex items-center gap-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Remove Contract</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 7: WORKFORCE & CAPACITY */}
      {activeTab === 'workforce' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Users className="w-5 h-5 text-blue-600" />
              Workforce Metrics & Operational Capacity
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <Input
                label="Total Permanent Staff"
                type="number"
                value={totalEmployees || ''}
                onChange={(e) => setTotalEmployees(Number(e.target.value))}
                placeholder="e.g. 45"
              />

              <Input
                label="Qualified Engineers"
                type="number"
                value={engineersCount || ''}
                onChange={(e) => setEngineersCount(Number(e.target.value))}
                placeholder="e.g. 18"
              />

              <Input
                label="Certified Technicians"
                type="number"
                value={techniciansCount || ''}
                onChange={(e) => setTechniciansCount(Number(e.target.value))}
                placeholder="e.g. 12"
              />

              <Input
                label="Project Managers"
                type="number"
                value={projectManagersCount || ''}
                onChange={(e) => setProjectManagersCount(Number(e.target.value))}
                placeholder="e.g. 4"
              />

              <Input
                label="Service Centers Count"
                type="number"
                value={serviceCentersCount || ''}
                onChange={(e) => setServiceCentersCount(Number(e.target.value))}
                placeholder="e.g. 3"
              />

              <div className="flex flex-col justify-center">
                <span className="block text-sm font-medium text-slate-700 mb-2">
                  Emergency Support Availability
                </span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={emergencySupport}
                    onChange={(e) => setEmergencySupport(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">24x7 Emergency / Field Support</span>
                </label>
              </div>
            </div>
          </div>

          {/* Key Personnel */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-semibold text-slate-800">
                  Key Technical & Leadership Personnel
                </h3>
                <p className="text-xs text-slate-500">
                  Project managers and lead engineers submitted for technical team evaluation clauses.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={handleAddPersonnel}
              >
                Add Personnel
              </Button>
            </div>

            {keyPersonnel.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No key personnel listed.</p>
            ) : (
              <div className="space-y-3">
                {keyPersonnel.map((p, idx) => (
                  <div key={idx} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Full Name"
                        value={p.name}
                        onChange={(e) => handleUpdatePersonnel(idx, 'name', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-44">
                      <input
                        type="text"
                        placeholder="Designation"
                        value={p.designation}
                        onChange={(e) => handleUpdatePersonnel(idx, 'designation', e.target.value)}
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-24">
                      <input
                        type="number"
                        placeholder="Yrs Exp"
                        value={p.experience_years || ''}
                        onChange={(e) =>
                          handleUpdatePersonnel(idx, 'experience_years', Number(e.target.value))
                        }
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <div className="w-44">
                      <input
                        type="text"
                        placeholder="Qualification (e.g. B.Tech EE)"
                        value={p.qualification || ''}
                        onChange={(e) =>
                          handleUpdatePersonnel(idx, 'qualification', e.target.value)
                        }
                        className="w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-1.5"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemovePersonnel(idx)}
                      className="text-slate-400 hover:text-rose-600 p-2"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 8: TENDER ELIGIBILITY & EXEMPTIONS */}
      {activeTab === 'exemptions' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <ShieldCheck className="w-5 h-5 text-blue-600" />
              MSME Policy Benefits & Exemption Preferences
            </h2>

            <div className="space-y-4">
              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exemptions.emd_exemption ?? true}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, emd_exemption: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    EMD (Earnest Money Deposit) Exemption Claim
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Claim exemption from EMD submission under Rule 170 of General Financial Rules (GFR) 2017 and Micro and Small Enterprises (MSEs) Public Procurement Policy.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exemptions.tender_fee_exemption ?? true}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, tender_fee_exemption: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    Tender Fee / Cost of Bidding Document Exemption
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    MSEs registered with Udyam are entitled to receive tender sets free of cost.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exemptions.turnover_relaxation ?? true}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, turnover_relaxation: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    Turnover Criteria Relaxation (MSEs & Startups)
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Relaxation in prior turnover requirements subject to meeting quality and technical specifications.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exemptions.experience_relaxation ?? true}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, experience_relaxation: e.target.checked })
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-900 block">
                    Prior Experience Criteria Relaxation
                  </span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Relaxation in past experience years for recognized Startups and eligible Micro & Small Enterprises.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Make in India Preference */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3">
              Make in India (MII) Purchase Preference
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Local Content Classification
                </label>
                <select
                  value={exemptions.mii_class || 'CLASS_1'}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, mii_class: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none"
                >
                  <option value="CLASS_1">Class-I Local Supplier (&ge; 50% Local Content)</option>
                  <option value="CLASS_2">Class-II Local Supplier (20% to 50% Local Content)</option>
                  <option value="NON_LOCAL">Non-Local Supplier (&lt; 20% Local Content)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Indigenized Local Content (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={exemptions.mii_percentage ?? 50}
                  onChange={(e) =>
                    setExemptions({ ...exemptions, mii_percentage: Number(e.target.value) })
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 9: DOCUMENT VAULT INTEGRATION */}
      {activeTab === 'vault' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                  <FolderLock className="w-5 h-5 text-blue-600" />
                  Company Document Vault Integration
                </h2>
                <p className="text-xs text-slate-500">
                  {vaultDocs.length} credential document(s) uploaded and available for compliance evidence.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                icon={<Upload className="w-4 h-4" />}
                onClick={() => {
                  setUploadCategory('FINANCIAL_AUDIT');
                  setIsVaultModalOpen(true);
                }}
              >
                Upload to Vault
              </Button>
            </div>

            {vaultDocs.length === 0 ? (
              <div className="text-center py-10 text-slate-400">
                <FolderLock className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Your Document Vault is empty.</p>
                <p className="text-xs mt-1">
                  Upload audited balance sheets, ISO certificates, or past work orders.
                </p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={() => setIsVaultModalOpen(true)}
                >
                  Upload First Document
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {vaultDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-600 shrink-0" />
                        <span className="text-sm font-semibold text-slate-800 truncate max-w-xs block">
                          {doc.original_filename}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-2xs text-slate-500">
                        <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 font-medium">
                          {doc.document_category}
                        </span>
                        <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                        <span>
                          {new Date(doc.created_at).toLocaleDateString([], {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                      </div>
                      <div className="pt-1 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="text-2xs font-semibold text-emerald-700 uppercase">
                          {doc.verification_status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 10: CAPABILITY STATEMENT (PREVIEW / PRINT) */}
      {activeTab === 'statement' && (
        <div className="space-y-6">
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              icon={<Printer className="w-4 h-4" />}
              onClick={() => window.print()}
            >
              Print Capability Statement
            </Button>
          </div>

          <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xs space-y-6 print:border-none print:shadow-none">
            {/* Header */}
            <div className="border-b-2 border-slate-900 pb-4 flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-black text-slate-900 uppercase tracking-tight">
                  {legalName || 'MSME Enterprise Profile'}
                </h1>
                {tradeName && <p className="text-sm text-slate-600 font-medium">{tradeName}</p>}
                <p className="text-xs text-slate-500 mt-1">
                  MSME {businessType ? businessType.charAt(0).toUpperCase() + businessType.slice(1).toLowerCase() : 'Small'} Enterprise • Sector: {sector}
                </p>
              </div>
              <div className="text-right text-xs text-slate-500 space-y-0.5">
                <p>
                  <span className="font-semibold text-slate-700">CIN/Reg:</span> {registrationNumber}
                </p>
                {udyamNumber && (
                  <p>
                    <span className="font-semibold text-slate-700">Udyam:</span> {udyamNumber}
                  </p>
                )}
                {gstin && (
                  <p>
                    <span className="font-semibold text-slate-700">GSTIN:</span> {gstin}
                  </p>
                )}
                {panNumber && (
                  <p>
                    <span className="font-semibold text-slate-700">PAN:</span> {panNumber}
                  </p>
                )}
              </div>
            </div>

            {/* Executive Summary */}
            {capabilityStatement && (
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1">
                  Executive Summary
                </span>
                <p className="text-sm text-slate-800 leading-relaxed">
                  {capabilityStatement.summary_text}
                </p>
              </div>
            )}

            {/* Financial Overview Table */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
                1. Audited Financial Capability & Turnover
              </h3>
              <table className="w-full text-xs text-left border-collapse border border-slate-200">
                <thead>
                  <tr className="bg-slate-100 text-slate-700">
                    <th className="p-2 border border-slate-200">Fiscal Year</th>
                    <th className="p-2 border border-slate-200">Audited Turnover</th>
                    <th className="p-2 border border-slate-200">Net Worth</th>
                    <th className="p-2 border border-slate-200">PAT / Net Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {turnovers.map((t, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="p-2 border border-slate-200 font-medium">{t.fiscal_year}</td>
                      <td className="p-2 border border-slate-200">{formatINR(t.turnover_inr)}</td>
                      <td className="p-2 border border-slate-200">{formatINR(t.net_worth_inr)}</td>
                      <td className="p-2 border border-slate-200">{formatINR(t.profit_after_tax_inr)}</td>
                    </tr>
                  ))}
                  <tr className="bg-slate-50 font-bold">
                    <td className="p-2 border border-slate-200">3-Year Average</td>
                    <td className="p-2 border border-slate-200 text-emerald-700">
                      {formatINR(avgTurnover)}
                    </td>
                    <td className="p-2 border border-slate-200" colSpan={2}></td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Technical Capabilities Matrix */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
                2. Technical Capabilities & Offerings
              </h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="font-semibold text-slate-700">Classification:</span> {oemStatus}
                </div>
                <div>
                  <span className="font-semibold text-slate-700">Coverage:</span> {serviceCoverage}
                </div>
                <div className="col-span-2">
                  <span className="font-semibold text-slate-700">Core Domains:</span>{' '}
                  {coreDomainsStr || 'General Engineering & Supply'}
                </div>
                {testingFacilities && (
                  <div className="col-span-2">
                    <span className="font-semibold text-slate-700">QA & QC Testing:</span>{' '}
                    {testingFacilities}
                  </div>
                )}
              </div>
            </div>

            {/* Quality Certifications */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
                3. Quality & Industry Certifications
              </h3>
              {certifications.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No certifications registered.</p>
              ) : (
                <ul className="list-disc pl-5 text-xs text-slate-700 space-y-1">
                  {certifications.map((c, i) => (
                    <li key={i}>
                      <span className="font-bold">{c.name}</span> — Issuing Body:{' '}
                      {c.issuing_authority || 'Accredited Registrar'} (Valid Until:{' '}
                      {c.valid_until || 'Current'})
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Major Past Experience */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
                4. Major Past Performance & Completed Contracts
              </h3>
              {workExperience.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No past contracts recorded.</p>
              ) : (
                <ul className="list-disc pl-5 text-xs text-slate-700 space-y-1">
                  {workExperience.map((w, i) => (
                    <li key={i}>
                      <span className="font-bold">{w.project_title}</span> for{' '}
                      <span className="font-semibold">{w.client_name}</span> ({formatINR(w.contract_value_inr)})
                      {w.completion_date && ` • Completed: ${w.completion_date}`}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Signatory Statement */}
            <div className="pt-6 border-t border-slate-200 flex justify-between items-end text-xs text-slate-600">
              <div>
                <p className="font-semibold text-slate-800">
                  {contactDetails.signatory_name || 'Authorized Signatory'}
                </p>
                <p>{contactDetails.designation || 'Director / Proprietor'}</p>
                <p>{legalName}</p>
              </div>
              <div className="text-right">
                <p>Generated: {new Date().toLocaleDateString()}</p>
                <p className="text-2xs text-slate-400">ProcureX Deterministic Intelligence</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* QUICK VAULT UPLOAD MODAL */}
      <Modal
        isOpen={isVaultModalOpen}
        onClose={() => setIsVaultModalOpen(false)}
        title="Upload Document to Company Vault"
      >
        <form onSubmit={handleVaultUpload} className="space-y-4">
          {uploadError && <ErrorAlert message={uploadError} onDismiss={() => setUploadError(null)} />}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Document Category <span className="text-rose-500">*</span>
            </label>
            <select
              value={uploadCategory}
              onChange={(e) => setUploadCategory(e.target.value as DocumentCategory)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white"
            >
              {DOCUMENT_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Select PDF File <span className="text-rose-500">*</span>
            </label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsVaultModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              isLoading={isUploading}
              icon={<Upload className="w-4 h-4" />}
            >
              Upload Document
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
