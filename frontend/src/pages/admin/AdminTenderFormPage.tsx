import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { adminApi } from '../../api/adminApi';
import { TenderCreatePayload } from '../../types/tender';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import { Plus, ArrowLeft, ShieldPlus, FileSpreadsheet } from 'lucide-react';

export const AdminTenderFormPage: React.FC = () => {
  const navigate = useNavigate();

  const [tenderReference, setTenderReference] = useState('');
  const [title, setTitle] = useState('');
  const [issuingAuthority, setIssuingAuthority] = useState('');
  const [sector, setSector] = useState('Electrical Engineering');
  const [budget, setBudget] = useState<number | ''>('');
  const [emd, setEmd] = useState<number | ''>('');
  const [msmeExempt, setMsmeExempt] = useState(true);
  const [submissionDeadline, setSubmissionDeadline] = useState('');
  const [publicationDate, setPublicationDate] = useState('');
  const [portalUrl, setPortalUrl] = useState('');

  // Structured requirements JSON string
  const [requirementsJson, setRequirementsJson] = useState(
    JSON.stringify(
      {
        minimum_annual_turnover_inr: 25000000,
        minimum_years_in_business: 3,
        required_certifications: ["ISO 9001:2015"],
        disallow_blacklisted: true,
        mandatory_documents: ["FINANCIAL_AUDIT", "TAX_RECORD"]
      },
      null,
      2
    )
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    let parsedRequirements = null;
    if (requirementsJson.trim()) {
      try {
        parsedRequirements = JSON.parse(requirementsJson);
      } catch {
        setError('Structured requirements must be valid JSON.');
        return;
      }
    }

    if (!tenderReference || !title || !issuingAuthority || !submissionDeadline) {
      setError('Please provide tender reference, title, issuing authority, and submission deadline.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: TenderCreatePayload = {
        tender_reference: tenderReference,
        title,
        issuing_authority: issuingAuthority,
        sector,
        estimated_budget_inr: budget !== '' ? Number(budget) : null,
        emd_amount_inr: emd !== '' ? Number(emd) : null,
        msme_emd_exemption: msmeExempt,
        submission_deadline: new Date(submissionDeadline).toISOString(),
        publication_date: publicationDate ? new Date(publicationDate).toISOString() : null,
        official_portal_url: portalUrl || null,
        structured_requirements: parsedRequirements,
      };

      await adminApi.createTender(payload);
      navigate('/admin/tenders');
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-2">
        <Link
          to="/admin/tenders"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Admin Tenders
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <ShieldPlus className="w-7 h-7 text-purple-600" />
          Publish New Procurement Tender
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Configure metadata and deterministic criteria requirements for MSME compliance matching
        </p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3">
            Tender Identification & Authority
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Tender Reference / ID"
              required
              value={tenderReference}
              onChange={(e) => setTenderReference(e.target.value)}
              placeholder="e.g. NTPC/ELECT/2026/0892"
            />

            <Input
              label="Domain Sector"
              required
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="e.g. Electrical Infrastructure"
            />

            <div className="md:col-span-2">
              <Input
                label="Tender Title"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Supply and Commissioning of 33kV Substation Switchgear"
              />
            </div>

            <div className="md:col-span-2">
              <Input
                label="Issuing Authority / PSU / Ministry"
                required
                value={issuingAuthority}
                onChange={(e) => setIssuingAuthority(e.target.value)}
                placeholder="e.g. National Thermal Power Corporation Limited"
              />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3">
            Financial & Schedule Terms
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Estimated Budget (INR)"
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value !== '' ? Number(e.target.value) : '')}
              placeholder="e.g. 50000000"
            />

            <Input
              label="EMD / Bid Security (INR)"
              type="number"
              value={emd}
              onChange={(e) => setEmd(e.target.value !== '' ? Number(e.target.value) : '')}
              placeholder="e.g. 1000000"
            />

            <div className="flex items-center gap-2 pt-2 md:col-span-2">
              <input
                type="checkbox"
                id="msme_exempt"
                checked={msmeExempt}
                onChange={(e) => setMsmeExempt(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="msme_exempt" className="text-sm font-medium text-slate-700">
                Grant MSME EMD Exemption (under Public Procurement Policy)
              </label>
            </div>

            <Input
              label="Submission Deadline"
              type="datetime-local"
              required
              value={submissionDeadline}
              onChange={(e) => setSubmissionDeadline(e.target.value)}
            />

            <Input
              label="Publication Date"
              type="datetime-local"
              value={publicationDate}
              onChange={(e) => setPublicationDate(e.target.value)}
            />

            <div className="md:col-span-2">
              <Input
                label="Official Portal URL (Optional)"
                type="url"
                value={portalUrl}
                onChange={(e) => setPortalUrl(e.target.value)}
                placeholder="https://eprocure.gov.in/..."
              />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
            <FileSpreadsheet className="w-5 h-5 text-purple-600" />
            Deterministic Eligibility Criteria (JSON)
          </h2>
          <p className="text-xs text-slate-500">
            Define parameter limits parsed by the Python rule engine (turnover, experience, certifications, mandatory documents).
          </p>

          <textarea
            rows={8}
            value={requirementsJson}
            onChange={(e) => setRequirementsJson(e.target.value)}
            className="w-full font-mono text-xs p-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-500 text-slate-900 bg-slate-50"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Link to="/admin/tenders">
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
          <Button type="submit" size="lg" isLoading={isSubmitting} icon={<Plus className="w-5 h-5" />}>
            Publish Tender
          </Button>
        </div>
      </form>
    </div>
  );
};
