import React, { useEffect, useState } from 'react';
import { companyApi } from '../../api/companyApi';
import {
  CompanyResponse,
  TurnoverRecord,
  CertificationRecord,
  WorkExperienceRecord,
} from '../../types/company';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
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
} from 'lucide-react';

export const CompanyProfilePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [legalName, setLegalName] = useState('');
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [businessType, setBusinessType] = useState('SMALL');
  const [sector, setSector] = useState('');
  const [incorporationDate, setIncorporationDate] = useState('');

  // Complex sub-records
  const [turnovers, setTurnovers] = useState<TurnoverRecord[]>([]);
  const [certifications, setCertifications] = useState<CertificationRecord[]>([]);
  const [workExperience, setWorkExperience] = useState<WorkExperienceRecord[]>([]);

  useEffect(() => {
    async function fetchCompany() {
      setLoading(true);
      setError(null);
      try {
        const data = await companyApi.getProfile();
        setCompany(data);
        setLegalName(data.legal_name);
        setRegistrationNumber(data.registration_number);
        setBusinessType(data.business_type);
        setSector(data.sector);
        setIncorporationDate(data.incorporation_date);
        setTurnovers(data.annual_turnover || []);
        setCertifications(data.certifications || []);
        setWorkExperience(data.work_experience || []);
      } catch (err: unknown) {
        // If 404, company not yet created
        setCompany(null);
      } finally {
        setLoading(false);
      }
    }
    fetchCompany();
  }, []);

  const handleAddTurnover = () => {
    setTurnovers([...turnovers, { fiscal_year: '2024-2025', turnover_inr: 0, currency: 'INR' }]);
  };

  const handleRemoveTurnover = (index: number) => {
    setTurnovers(turnovers.filter((_, i) => i !== index));
  };

  const handleUpdateTurnover = (index: number, field: keyof TurnoverRecord, value: string | number) => {
    const updated = [...turnovers];
    updated[index] = { ...updated[index], [field]: value };
    setTurnovers(updated);
  };

  const handleAddCertification = () => {
    setCertifications([...certifications, { name: '', issuing_authority: '' }]);
  };

  const handleRemoveCertification = (index: number) => {
    setCertifications(certifications.filter((_, i) => i !== index));
  };

  const handleUpdateCertification = (index: number, field: keyof CertificationRecord, value: string) => {
    const updated = [...certifications];
    updated[index] = { ...updated[index], [field]: value };
    setCertifications(updated);
  };

  const handleAddExperience = () => {
    setWorkExperience([...workExperience, { project_title: '', client_name: '', contract_value_inr: 0 }]);
  };

  const handleRemoveExperience = (index: number) => {
    setWorkExperience(workExperience.filter((_, i) => i !== index));
  };

  const handleUpdateExperience = (
    index: number,
    field: keyof WorkExperienceRecord,
    value: string | number
  ) => {
    const updated = [...workExperience];
    updated[index] = { ...updated[index], [field]: value };
    setWorkExperience(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const payload = {
      legal_name: legalName,
      registration_number: registrationNumber,
      business_type: businessType,
      sector,
      incorporation_date: incorporationDate,
      annual_turnover: turnovers.map((t) => ({
        ...t,
        turnover_inr: Number(t.turnover_inr),
      })),
      certifications,
      work_experience: workExperience.map((w) => ({
        ...w,
        contract_value_inr: Number(w.contract_value_inr),
      })),
    };

    try {
      if (company) {
        const updated = await companyApi.updateProfile(payload);
        setCompany(updated);
        setSuccessMsg('Company profile updated successfully.');
      } else {
        const created = await companyApi.createProfile(payload);
        setCompany(created);
        setSuccessMsg('Company profile created successfully.');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading company credentials..." />;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">MSME Company Profile</h1>
        <p className="text-sm text-slate-500 mt-1">
          Registered business credentials utilized by the deterministic compliance engine
        </p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Business Details */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Building2 className="w-5 h-5 text-blue-600" />
            General Entity Information
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
              label="Registration / CIN / Udyam Number"
              required
              value={registrationNumber}
              onChange={(e) => setRegistrationNumber(e.target.value)}
              placeholder="e.g. UDYAM-MH-01-0012345"
            />

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
              label="Primary Sector / Domain"
              required
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="e.g. Electrical Engineering / Power Systems"
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

        {/* Audited Annual Turnover */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              Annual Audited Turnover (INR)
            </h2>
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

          <p className="text-xs text-slate-500">
            Rule engine evaluates average turnover against tender minimum financial criteria.
          </p>

          {turnovers.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No fiscal turnover figures added yet.</p>
          ) : (
            <div className="space-y-3">
              {turnovers.map((t, index) => (
                <div key={index} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                  <div className="w-1/3">
                    <Input
                      placeholder="e.g. 2023-2024"
                      value={t.fiscal_year}
                      onChange={(e) => handleUpdateTurnover(index, 'fiscal_year', e.target.value)}
                    />
                  </div>
                  <div className="w-1/2">
                    <Input
                      type="number"
                      placeholder="Turnover in INR (e.g. 50000000)"
                      value={t.turnover_inr || ''}
                      onChange={(e) => handleUpdateTurnover(index, 'turnover_inr', Number(e.target.value))}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveTurnover(index)}
                    className="text-slate-400 hover:text-rose-600 p-2"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Certifications */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <Award className="w-5 h-5 text-purple-600" />
              Corporate & Quality Certifications
            </h2>
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
            <div className="space-y-3">
              {certifications.map((c, index) => (
                <div key={index} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                  <div className="flex-1">
                    <Input
                      placeholder="Certification Name (e.g. ISO 9001:2015)"
                      value={c.name}
                      onChange={(e) => handleUpdateCertification(index, 'name', e.target.value)}
                    />
                  </div>
                  <div className="flex-1">
                    <Input
                      placeholder="Issuing Authority (e.g. Bureau Veritas)"
                      value={c.issuing_authority || ''}
                      onChange={(e) => handleUpdateCertification(index, 'issuing_authority', e.target.value)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveCertification(index)}
                    className="text-slate-400 hover:text-rose-600 p-2"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Work Experience */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-amber-600" />
              Completed Projects & Past Contracts
            </h2>
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
            <p className="text-sm text-slate-400 italic">No work contracts listed yet.</p>
          ) : (
            <div className="space-y-3">
              {workExperience.map((w, index) => (
                <div key={index} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
                  <div className="flex-1">
                    <Input
                      placeholder="Project Title"
                      value={w.project_title}
                      onChange={(e) => handleUpdateExperience(index, 'project_title', e.target.value)}
                    />
                  </div>
                  <div className="flex-1">
                    <Input
                      placeholder="Client Name (e.g. BHEL, NTPC)"
                      value={w.client_name}
                      onChange={(e) => handleUpdateExperience(index, 'client_name', e.target.value)}
                    />
                  </div>
                  <div className="w-40">
                    <Input
                      type="number"
                      placeholder="Value (INR)"
                      value={w.contract_value_inr || ''}
                      onChange={(e) =>
                        handleUpdateExperience(index, 'contract_value_inr', Number(e.target.value))
                      }
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveExperience(index)}
                    className="text-slate-400 hover:text-rose-600 p-2"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button
            type="submit"
            size="lg"
            isLoading={saving}
            icon={<Save className="w-5 h-5" />}
          >
            {company ? 'Update Profile' : 'Save Company Profile'}
          </Button>
        </div>
      </form>
    </div>
  );
};
