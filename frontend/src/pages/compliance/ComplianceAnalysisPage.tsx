import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { tendersApi } from '../../api/tendersApi';
import { companyApi } from '../../api/companyApi';
import { complianceApi } from '../../api/complianceApi';
import { TenderResponse } from '../../types/tender';
import { CompanyResponse } from '../../types/company';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import { formatTenderDeadline } from '../../utils/dateUtils';
import {
  FileCheck2,
  Sparkles,
  Building2,
  AlertCircle,
  Cpu,
  ArrowRight,
  FileText,
  AlertOctagon,
  Calendar,
  Layers,
  ShieldCheck,
  Download,
} from 'lucide-react';

export const ComplianceAnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [tenders, setTenders] = useState<TenderResponse[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>(
    searchParams.get('tender_id') || ''
  );
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [includeAiExplanation, setIncludeAiExplanation] = useState(true);

  const [loading, setLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [downloadingDoc, setDownloadingDoc] = useState(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleDownloadPdf = async () => {
    if (!selectedTender) return;
    setDownloadingDoc(true);
    setError(null);
    try {
      await tendersApi.fetchTenderDocuments(selectedTender.id);
      const updated = await tendersApi.getTender(selectedTender.id);
      setTenders((prev) => prev.map((t) => (t.id === selectedTender.id ? updated : t)));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setDownloadingDoc(false);
    }
  };

  useEffect(() => {
    async function loadPrerequisites() {
      setLoading(true);
      setError(null);
      try {
        // Fetch company profile
        try {
          const comp = await companyApi.getProfile();
          setCompany(comp);
        } catch {
          setCompany(null);
        }

        // Fetch tenders
        const tenderData = await tendersApi.listTenders({ limit: 100 });
        setTenders(tenderData.items);
        if (!selectedTenderId && tenderData.items.length > 0) {
          setSelectedTenderId(tenderData.items[0].id);
        }
      } catch (err: unknown) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    loadPrerequisites();
  }, [selectedTenderId]);

  const selectedTender = tenders.find((t) => t.id === selectedTenderId);
  const attachedDocs = selectedTender?.documents || [];
  const indexedDocsCount = attachedDocs.filter((d) => d.processing_status === 'INDEXED').length;
  const hasNoUsableDocs = attachedDocs.length === 0 || indexedDocsCount === 0;

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenderId) {
      setError('Please select a tender to evaluate.');
      return;
    }

    if (!company) {
      setError('You must create a company profile before running compliance analysis.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setAnalysisStep('Validating tender documents and physical page bounds...');

    const timer1 = setTimeout(() => {
      setAnalysisStep('Loading and normalizing extracted requirements across categories...');
    }, 1200);

    const timer2 = setTimeout(() => {
      setAnalysisStep('Evaluating deterministic Python business rules and numeric thresholds...');
    }, 2500);

    const timer3 = setTimeout(() => {
      setAnalysisStep('Performing requirement-specific hybrid lexical and semantic retrieval...');
    }, 3800);

    const timer4 = setTimeout(() => {
      setAnalysisStep('Validating evidence citations and tenant boundaries...');
    }, 5000);

    const timer5 = setTimeout(() => {
      setAnalysisStep('Synthesizing natural language explanations via Gemini AI...');
    }, 6200);

    try {
      const report = await complianceApi.analyzeTender({
        tender_id: selectedTenderId,
        include_ai_explanation: includeAiExplanation,
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      clearTimeout(timer5);

      navigate(`/compliance/reports/${report.id}`);
    } catch (err: unknown) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      clearTimeout(timer5);
      setIsAnalyzing(false);
      setError(getErrorMessage(err));
    }
  };

  if (loading) {
    return <LoadingSpinner message="Preparing compliance intelligence workspace..." />;
  }

  return (
    <div className="space-y-6 w-full">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <FileCheck2 className="w-7 h-7 text-blue-600" />
          Run Tender Compliance Analysis
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Objective criteria evaluation backed by LangGraph orchestration, deterministic Python rules, and hybrid RAG evidence
        </p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Prerequisite Check: Company Profile */}
      {!company && (
        <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-900">
                Company Profile Not Configured
              </h3>
              <p className="text-xs text-amber-700 mt-1">
                The compliance engine needs your verified company turnover figures, work experience, certifications, and document vault to evaluate eligibility.
              </p>
            </div>
          </div>
          <Link to="/company" className="shrink-0">
            <Button size="sm">Create Profile</Button>
          </Link>
        </div>
      )}

      {/* Deterministic Architecture Notice */}
      <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 flex items-start gap-3">
        <Cpu className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-blue-950">Deterministic Architecture Guarantee:</span>{' '}
          Python rules compute objective PASS / FAIL / MISSING_EVIDENCE statuses strictly based on verified data.
          Gemini AI provides evidence-grounded interpretations and recommendations, but is strictly prohibited
          from overriding deterministic rule decisions or inventing missing citations.
        </div>
      </div>

      {/* Main Analysis Form */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
        <form onSubmit={handleRunAnalysis} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-800 mb-1">
              Select Procurement Tender <span className="text-rose-500">*</span>
            </label>
            <select
              value={selectedTenderId}
              onChange={(e) => setSelectedTenderId(e.target.value)}
              disabled={isAnalyzing}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
            >
              {tenders.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.tender_reference}] {t.title} — {t.issuing_authority}
                </option>
              ))}
            </select>
          </div>

          {selectedTender && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
              <div className="flex items-center justify-between font-semibold text-slate-800">
                <span>Authority: {selectedTender.issuing_authority}</span>
                <span className="text-blue-600">{selectedTender.sector}</span>
              </div>
              <p className="text-slate-600">
                Deadline:{' '}
                {formatTenderDeadline(selectedTender.submission_deadline)}
              </p>
              <p className="text-slate-500">
                Attached Documents: {indexedDocsCount} files indexed ({attachedDocs.length} total attached)
              </p>
            </div>
          )}

          {/* Section 3: Handling 0 Files Indexed Explicitly */}
          {selectedTender && hasNoUsableDocs && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-300 text-amber-950 space-y-3">
              <div className="flex items-start gap-3">
                <AlertOctagon className="w-6 h-6 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-amber-950">
                    Attached Documents: {indexedDocsCount} files indexed
                  </h3>
                  <p className="text-xs text-amber-900 mt-1 leading-relaxed">
                    <strong>Full compliance analysis is unavailable because no usable tender documents have been indexed.</strong> Compliance evaluation cannot be completed because no usable tender document has been downloaded and indexed for this bid. Retry document retrieval, open the official source, or upload the tender file manually.
                  </p>
                  <p className="text-[11px] text-amber-700 mt-1">
                    Evaluating this tender without indexed documents will only check pre-configured structured RFP parameters and will report documented scope limitations.
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button
                  size="sm"
                  type="button"
                  isLoading={downloadingDoc}
                  disabled={downloadingDoc}
                  onClick={handleDownloadPdf}
                  icon={<Download className="w-4 h-4" />}
                >
                  Download Tender PDF Now
                </Button>
                <Link to={`/tenders/${selectedTender.id}`}>
                  <Button size="sm" variant="outline" icon={<FileText className="w-4 h-4" />}>
                    View Tender Notice & Upload / Inspect Documents
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {/* Partial Document Coverage Warning */}
          {selectedTender && !hasNoUsableDocs && indexedDocsCount < attachedDocs.length && (
            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-blue-950">Scope Limitation:</span> Partial document coverage ({indexedDocsCount} of {attachedDocs.length} files indexed). Some clauses may require manual review from unindexed attachments.
              </div>
            </div>
          )}

          {/* AI Explanation Toggle */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <input
              type="checkbox"
              id="include_ai"
              checked={includeAiExplanation}
              onChange={(e) => setIncludeAiExplanation(e.target.checked)}
              disabled={isAnalyzing}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="include_ai" className="text-xs text-slate-700 cursor-pointer">
              <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                Include Gemini AI Narrative & Evidence Explanations
              </span>
              <span className="block text-slate-500 mt-0.5">
                Generates detailed rationale for each criterion, risk analysis, and links specific document citations (page numbers and quotations).
              </span>
            </label>
          </div>

          {/* Analysis Active Feedback */}
          {isAnalyzing && (
            <div className="p-5 rounded-2xl bg-indigo-50 border border-indigo-200 text-center space-y-3 animate-pulse">
              <div className="inline-flex p-3 rounded-full bg-indigo-100 text-indigo-700">
                <Cpu className="w-6 h-6 animate-spin" />
              </div>
              <p className="text-sm font-bold text-indigo-950">Orchestrating Compliance Graph</p>
              <p className="text-xs font-medium text-indigo-700">{analysisStep}</p>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button
              type="submit"
              size="lg"
              disabled={!company || isAnalyzing}
              isLoading={isAnalyzing}
              icon={<FileCheck2 className="w-5 h-5" />}
            >
              Start Compliance Evaluation
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
