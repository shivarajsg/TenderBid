import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { complianceApi } from '../../api/complianceApi';
import {
  ComplianceReportResponse,
  ComplianceFindingResponse,
  FindingStatus,
} from '../../types/compliance';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import {
  FileCheck2,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FileText,
  BookmarkCheck,
  Printer,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertOctagon,
  ListOrdered,
  FileSpreadsheet,
  Building2,
  ExternalLink,
  Info,
} from 'lucide-react';

export const ComplianceReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const [report, setReport] = useState<ComplianceReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFindings, setExpandedFindings] = useState<Record<string, boolean>>({});

  // Filter & Search States
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'PRIORITY' | 'ID' | 'STATUS'>('PRIORITY');

  useEffect(() => {
    async function fetchReport() {
      if (!reportId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await complianceApi.getReport(reportId);
        setReport(data);
        const initialExpanded: Record<string, boolean> = {};
        data.findings.forEach((f) => {
          initialExpanded[f.id] = true;
        });
        setExpandedFindings(initialExpanded);
      } catch (err: unknown) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    fetchReport();
  }, [reportId]);

  const toggleFinding = (id: string) => {
    setExpandedFindings((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handlePrint = () => {
    window.print();
  };

  // Filter and sort findings
  const filteredFindings = useMemo(() => {
    if (!report) return [];

    return report.findings
      .filter((f) => {
        // Status filter
        if (statusFilter !== 'ALL' && f.status !== statusFilter) {
          return false;
        }

        // Category filter
        const cat = (f.category || f.rule_type || '').toUpperCase();
        if (categoryFilter !== 'ALL' && cat !== categoryFilter.toUpperCase()) {
          return false;
        }

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchTitle = (f.title || f.requirement_description || '').toLowerCase().includes(q);
          const matchClause = (f.original_clause || '').toLowerCase().includes(q);
          const matchReason = (f.reason || '').toLowerCase().includes(q);
          const matchExp = (f.ai_explanation || '').toLowerCase().includes(q);
          const matchId = (f.requirement_id || '').toLowerCase().includes(q);
          return matchTitle || matchClause || matchReason || matchExp || matchId;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'PRIORITY') {
          // Mandatory failures first, then missing evidence, then review, then pass
          const rank = (f: ComplianceFindingResponse) => {
            if (f.status === 'FAIL' && f.is_mandatory) return 1;
            if (f.status === 'FAIL') return 2;
            if (f.status === 'MISSING_EVIDENCE' && f.is_mandatory) return 3;
            if (f.status === 'MISSING_EVIDENCE') return 4;
            if (f.status === 'NEEDS_REVIEW') return 5;
            if (f.status === 'PASS') return 6;
            return 7;
          };
          return rank(a) - rank(b);
        } else if (sortBy === 'ID') {
          return a.requirement_id.localeCompare(b.requirement_id);
        } else {
          return a.status.localeCompare(b.status);
        }
      });
  }, [report, statusFilter, categoryFilter, searchQuery, sortBy]);

  if (loading) {
    return <LoadingSpinner message="Loading compliance report & verifiable citations..." />;
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <Link
          to="/compliance/reports"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Reports List
        </Link>
        <ErrorAlert message={error || 'Report not found or unauthorized.'} />
      </div>
    );
  }

  const passCount = report.status_counts?.pass ?? report.findings.filter((f) => f.status === 'PASS').length;
  const failCount = report.status_counts?.fail ?? report.findings.filter((f) => f.status === 'FAIL').length;
  const missingCount = report.status_counts?.missing_evidence ?? report.findings.filter((f) => f.status === 'MISSING_EVIDENCE').length;
  const reviewCount = report.status_counts?.needs_review ?? report.findings.filter((f) => f.status === 'NEEDS_REVIEW').length;
  const notAppCount = report.status_counts?.not_applicable ?? report.findings.filter((f) => f.status === 'NOT_APPLICABLE').length;

  const missingDocs = report.missing_documents || [];
  const priorityActions = report.priority_actions || [];
  const comparisons = report.technical_financial_comparisons || [];
  const limitations = report.limitations || [];
  const docCoverage = report.document_coverage;

  const getOutcomeDescriptor = (st: string) => {
    switch (st?.toUpperCase()) {
      case 'ELIGIBLE':
        return 'MEETS CHECKED REQUIREMENTS';
      case 'NOT_ELIGIBLE':
        return 'DOES NOT MEET MANDATORY REQUIREMENTS';
      case 'PARTIALLY_ELIGIBLE':
        return 'INCOMPLETE — EVIDENCE REQUIRED';
      case 'NEEDS_REVIEW':
        return 'REVIEW REQUIRED';
      case 'ANALYSIS_BLOCKED_NO_DOCUMENTS':
      case 'ANALYSIS_BLOCKED':
        return 'ANALYSIS BLOCKED — SOURCE DOCUMENTS UNAVAILABLE';
      default:
        return '';
    }
  };

  return (
    <div className="space-y-8 w-full print:p-0">
      {/* Top Navigation & Print */}
      <div className="flex items-center justify-between print:hidden">
        <Link
          to="/compliance/reports"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Compliance History
        </Link>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            icon={<Printer className="w-4 h-4" />}
            onClick={handlePrint}
          >
            Print / Export Official Audit PDF
          </Button>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Scope Limitations Alert (Section 3) */}
      {limitations.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-900 space-y-2">
          <div className="flex items-start gap-2.5">
            <AlertOctagon className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-amber-950">
                Audit Scope Limitation Notice
              </p>
              <ul className="list-disc list-inside text-xs mt-1 space-y-1 text-amber-900">
                {limitations.map((lim, lIdx) => (
                  <li key={lIdx}>{lim}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Hero Result Banner */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Authoritative Evaluation
              </span>
              <span className="text-xs font-mono text-slate-400">
                ID: {report.id}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <StatusBadge status={report.overall_status} size="lg" />
              {report.overall_score !== null && report.overall_score !== undefined && (
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-slate-900">
                    {Number(report.overall_score).toFixed(0)}%
                  </span>
                  <span className="text-xs text-slate-500 font-medium">overall eligibility score</span>
                </div>
              )}
            </div>

            <p className="text-xs text-slate-500 flex items-center gap-2 pt-1">
              <Clock className="w-3.5 h-3.5" />
              Evaluated on {new Date(report.created_at).toLocaleString()}
              {docCoverage && (
                <span>
                  • Coverage: {docCoverage.indexed_documents}/{docCoverage.total_documents} files indexed ({docCoverage.coverage_status})
                </span>
              )}
            </p>
          </div>

          {/* Quick Metrics Breakdown */}
          <div className="grid grid-cols-5 gap-2.5 bg-slate-50 p-4 rounded-2xl border border-slate-200/80 text-center">
            <div>
              <p className="text-[11px] text-slate-400 font-medium">Total</p>
              <p className="text-lg font-bold text-slate-900">{report.findings.length}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-400 font-medium">Passed</p>
              <p className="text-lg font-bold text-emerald-600">{passCount}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-400 font-medium">Failed</p>
              <p className="text-lg font-bold text-rose-600">{failCount}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-400 font-medium">Missing</p>
              <p className="text-lg font-bold text-amber-600">{missingCount}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-400 font-medium">Review</p>
              <p className="text-lg font-bold text-indigo-600">{reviewCount}</p>
            </div>
          </div>
        </div>

        {/* Executive Summary (Section 8.B) */}
        {(report.executive_summary || report.summary) && (
          <div className="mt-6 pt-6 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Executive AI Synthesis & Evaluation Rationale
            </h3>
            <div className="text-sm text-slate-700 leading-relaxed bg-slate-50/70 p-4 rounded-xl border border-slate-200 whitespace-pre-line">
              {report.executive_summary || report.summary}
            </div>
          </div>
        )}

        {/* Audit Hashes */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400">
          <span>Engine: {report.rule_engine_version || 'v1.0.0'}</span>
          <span>•</span>
          <span title={report.tender_version_hash || ''}>
            Tender Hash: {report.tender_version_hash ? `${report.tender_version_hash.substring(0, 12)}...` : 'N/A'}
          </span>
          <span>•</span>
          <span title={report.company_version_hash || ''}>
            Company Hash: {report.company_version_hash ? `${report.company_version_hash.substring(0, 12)}...` : 'N/A'}
          </span>
          <span>•</span>
          <span>AI Status: {report.ai_analysis_status || 'COMPLETED'}</span>
        </div>
      </div>

      {/* Missing-Document Checklist (Section 8.D) */}
      {missingDocs.length > 0 && (
        <div className="bg-white rounded-3xl border border-amber-200 p-6 sm:p-7 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-amber-950 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              Missing Document Checklist ({missingDocs.length} Actionable Proofs Needed)
            </h2>
            <span className="text-xs text-amber-700 font-medium">
              Upload to Company Document Vault before bidding
            </span>
          </div>
          <p className="text-xs text-slate-600">
            The following required documents were not identified in your vault or contain validity gaps:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {missingDocs.map((item, idx) => (
              <div
                key={idx}
                className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200 text-xs space-y-2 flex flex-col justify-between"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-amber-950 text-sm">{item.document_name}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        item.priority === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-900'
                      }`}
                    >
                      {item.priority}
                    </span>
                  </div>
                  <p className="text-slate-700 leading-normal">
                    <strong>Why Required:</strong> {item.why_required}
                  </p>
                  <p className="text-slate-500 font-mono text-[11px]">
                    Clause: {item.tender_clause}
                  </p>
                </div>

                <div className="pt-2 border-t border-amber-200/80 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-amber-900 font-medium">
                    {item.action_to_resolve}
                  </span>
                  <Link to="/vault" className="shrink-0">
                    <Button size="sm" variant="outline">
                      Vault &rarr;
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Priority Action Plan (Section 8.E) */}
      {priorityActions.length > 0 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ListOrdered className="w-5 h-5 text-blue-600" />
              Prioritized Bid Preparation Action Plan
            </h2>
            <span className="text-xs text-slate-400">Step-by-step roadmap before submission</span>
          </div>

          <div className="space-y-3">
            {priorityActions.map((action, aIdx) => (
              <div
                key={aIdx}
                className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-start gap-4"
              >
                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center font-bold text-sm shrink-0">
                  {action.step}
                </div>
                <div className="space-y-1 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-slate-900">{action.title}</h3>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        action.priority === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-800'
                          : action.priority === 'HIGH'
                          ? 'bg-amber-100 text-amber-900'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {action.priority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700">{action.action}</p>
                  <p className="text-[11px] text-slate-500 italic">Impact: {action.impact}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Technical and Financial Comparison Table (Section 8.F) */}
      {comparisons.length > 0 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            Technical & Financial Numerical Comparison
          </h2>
          <p className="text-xs text-slate-500">
            Factual alignment between stated RFP requirements and your verified corporate records:
          </p>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold">
                <tr>
                  <th className="p-3">Evaluation Parameter</th>
                  <th className="p-3">Required Condition</th>
                  <th className="p-3">Verified Company Fact</th>
                  <th className="p-3">Variance / Shortfall</th>
                  <th className="p-3">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comparisons.map((c, cIdx) => (
                  <tr key={cIdx} className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-900">
                      {c.parameter}
                      <span className="block text-[10px] text-slate-400 font-normal">{c.source}</span>
                    </td>
                    <td className="p-3 font-mono text-slate-700">{c.required_value}</td>
                    <td className="p-3 font-mono text-slate-900 font-medium">{c.observed_value}</td>
                    <td className="p-3 font-mono">
                      <span
                        className={
                          c.difference.startsWith('-')
                            ? 'text-rose-600 font-bold'
                            : c.difference.startsWith('+')
                            ? 'text-emerald-600 font-bold'
                            : 'text-slate-600'
                        }
                      >
                        {c.difference}
                      </span>
                    </td>
                    <td className="p-3">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detailed Compliance Analysis — Requirement by Requirement (Section 6 & 8.C) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-600" />
              Detailed Compliance Analysis — Requirement by Requirement ({filteredFindings.length} of {report.findings.length})
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Comprehensive 17-field evidence evaluation for every individual tender condition
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="rounded-lg border border-slate-300 px-2 py-1 text-xs bg-white text-slate-800"
            >
              <option value="PRIORITY">Priority & Risk</option>
              <option value="ID">Requirement ID</option>
              <option value="STATUS">Compliance Status</option>
            </select>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search requirements, clauses, citations, or keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs bg-white text-slate-800 focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="PASS">Pass Only</option>
              <option value="FAIL">Fail Only</option>
              <option value="MISSING_EVIDENCE">Missing Proof</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="NOT_APPLICABLE">Not Applicable</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs bg-white text-slate-800 focus:outline-none"
            >
              <option value="ALL">All Categories</option>
              <option value="FINANCIAL">Financial (Turnover)</option>
              <option value="ELIGIBILITY">Eligibility (Experience)</option>
              <option value="CERTIFICATES">Certifications (ISO)</option>
              <option value="MANDATORY_DOCUMENTS">Mandatory Documents</option>
              <option value="DEADLINE">Deadlines</option>
              <option value="COMMERCIAL">Commercial (EMD)</option>
              <option value="TECHNICAL">Technical Specs</option>
              <option value="LEGAL">Legal & Statutory</option>
              <option value="SUBMISSION">Submission Forms</option>
            </select>
          </div>
        </div>

        {/* Requirement Cards */}
        {filteredFindings.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 text-sm">
            No requirements match the selected filter criteria.
          </div>
        ) : (
          <div className="space-y-4">
            {filteredFindings.map((finding) => {
              const isExpanded = expandedFindings[finding.id] ?? true;

              return (
                <div
                  key={finding.id}
                  className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden transition-all"
                >
                  {/* Header row */}
                  <div
                    onClick={() => toggleFinding(finding.id)}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer hover:bg-slate-50/70 transition-colors"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                          {finding.requirement_id}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">
                          {finding.category || finding.rule_type}
                        </span>
                        {finding.is_mandatory ? (
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-100 text-rose-800">
                            Mandatory
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                            Optional / Non-Critical
                          </span>
                        )}
                        {finding.needs_human_review && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                            Review Required
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">
                        {finding.title || finding.requirement_description}
                      </h3>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <StatusBadge status={finding.status} isMandatory={finding.is_mandatory} />
                      <button className="text-slate-400 p-1">
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5" />
                        ) : (
                          <ChevronDown className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* 17 Fields Expanded Detail Section (Section 6) */}
                  {isExpanded && (
                    <div className="px-5 pb-6 pt-3 border-t border-slate-100 space-y-4">
                      {/* Original Clause & Plain English Interpretation */}
                      <div className="space-y-2">
                        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                          <p className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                            Original Tender Clause ({finding.tender_source || 'Tender Notice'})
                          </p>
                          <blockquote className="italic text-slate-800 border-l-2 border-slate-400 pl-3 leading-relaxed">
                            "{finding.original_clause || finding.requirement_description}"
                          </blockquote>
                        </div>

                        <div className="p-3.5 rounded-xl bg-blue-50/60 border border-blue-200 text-xs">
                          <p className="font-semibold text-blue-900 uppercase tracking-wider text-[10px] mb-1 flex items-center gap-1.5">
                            <Info className="w-3.5 h-3.5 text-blue-600" />
                            Plain-English Interpretation for Bidder
                          </p>
                          <p className="text-blue-950 leading-relaxed font-medium">
                            {finding.plain_english_interpretation || finding.reason}
                          </p>
                        </div>
                      </div>

                      {/* Side-by-Side: Company Evidence & Comparison Evaluation */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
                        {/* Company Facts */}
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                          <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                            Applicable Company Record & Evidence
                          </p>
                          <p className="text-slate-900 font-medium">
                            {finding.applicable_company_info || 'Company Profile Record'}
                          </p>
                          <p className="text-[11px] text-slate-500 font-mono">
                            Document: {finding.company_evidence || 'None in vault'}
                          </p>
                        </div>

                        {/* Comparison Outcome */}
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                          <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                            Deterministic Comparison & Evaluation
                          </p>
                          <p className="text-slate-800 leading-relaxed">
                            {finding.comparison_evaluation || finding.reason}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            <strong>Specific Condition:</strong> {finding.specific_condition || 'Standard RFP Criterion'}
                          </p>
                        </div>
                      </div>

                      {/* Deterministic Outcome vs AI Explanation */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
                        {/* Left: Rule Outcome */}
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                          <p className="font-bold text-slate-800 uppercase tracking-wider text-[10px]">
                            Authoritative Rule Engine Rationale
                          </p>
                          <p className="text-slate-700 leading-relaxed">{finding.reason}</p>
                          <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-600 space-y-1">
                            <p>
                              <strong>Evidence Gap:</strong>{' '}
                              <span className={finding.status === 'PASS' ? 'text-emerald-700 font-medium' : 'text-amber-800 font-medium'}>
                                {finding.evidence_gap || 'None'}
                              </span>
                            </p>
                            <p>
                              <strong>Risk & Consequence:</strong>{' '}
                              <span className="text-rose-700">{finding.risk_and_consequence || 'Disqualification if unaddressed.'}</span>
                            </p>
                          </div>
                        </div>

                        {/* Right: Explanation & Steps to be Taken */}
                        <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-200 space-y-2">
                          <p className="font-bold text-indigo-900 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                            Explanation & Steps to be Taken
                          </p>
                          <p className="text-indigo-950 leading-relaxed">
                            {finding.ai_explanation || finding.reason}
                          </p>
                          <div className="pt-2 border-t border-indigo-200 text-[11px] text-indigo-900">
                            <strong>Recommended Next Action:</strong>{' '}
                            <span className="font-medium">{finding.recommended_action || 'Maintain verified documentation.'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Verified Evidence Citations (Section 9) */}
                      {finding.evidence_citations && finding.evidence_citations.length > 0 && (
                        <div className="space-y-2 pt-2">
                          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                            <BookmarkCheck className="w-4 h-4 text-emerald-600" />
                            Verified Document Evidence & Physical Page Citations ({finding.evidence_citations.length})
                          </p>

                          <div className="space-y-2">
                            {finding.evidence_citations.map((cite, cIdx) => (
                              <div
                                key={cIdx}
                                className="p-3.5 rounded-xl bg-emerald-50/40 border border-emerald-200/80 text-xs space-y-1.5"
                              >
                                <div className="flex items-center justify-between font-medium text-emerald-900">
                                  <span className="inline-flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5 text-emerald-700" />
                                    <span className="font-semibold">{cite.source_filename}</span>
                                    <span className="text-[11px] px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 font-mono">
                                      Page {cite.page_number}
                                    </span>
                                  </span>
                                  <span className="text-[10px] uppercase font-mono text-emerald-700">
                                    {cite.source_type} • Method: {cite.retrieval_method}
                                    {cite.relevance_score !== null && cite.relevance_score !== undefined
                                      ? ` • ${(cite.relevance_score * 100).toFixed(0)}% RRF match`
                                      : ''}
                                  </span>
                                </div>
                                <blockquote className="italic text-slate-700 pl-3 border-l-2 border-emerald-400 text-[11px] leading-relaxed">
                                  "{cite.excerpt}"
                                </blockquote>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
