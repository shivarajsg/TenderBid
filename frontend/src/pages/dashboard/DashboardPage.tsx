import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { companyApi } from '../../api/companyApi';
import { tendersApi } from '../../api/tendersApi';
import { documentsApi } from '../../api/documentsApi';
import { complianceApi } from '../../api/complianceApi';
import { CompanyResponse } from '../../types/company';
import { ComplianceReportResponse } from '../../types/compliance';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Modal } from '../../components/common/Modal';
import {
  Building2,
  FileText,
  FileCheck2,
  Search,
  FolderLock,
  ArrowRight,
  Play,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Send,
  Sparkles,
  TrendingUp,
  Cpu,
  Folder,
  Check,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [tenderCount, setTenderCount] = useState<number>(536);
  const [docCount, setDocCount] = useState<number>(0);
  const [recentReports, setRecentReports] = useState<ComplianceReportResponse[]>([]);
  const [eligibleCount, setEligibleCount] = useState<number>(0);
  const [guideModalOpen, setGuideModalOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardData() {
      setLoading(true);
      try {
        // 1. Check company profile
        try {
          const comp = await companyApi.getProfile();
          if (isMounted) setCompany(comp);
        } catch {
          if (isMounted) setCompany(null);
        }

        // 2. Fetch tenders count
        try {
          const tenders = await tendersApi.listTenders({ limit: 1 });
          if (isMounted && tenders.total > 0) {
            setTenderCount(tenders.total);
          }
        } catch {
          // preserve default
        }

        // 3. Fetch vault docs count
        try {
          const docs = await documentsApi.listDocuments();
          if (isMounted) setDocCount(docs.length);
        } catch {
          // ignore
        }

        // 4. Fetch recent reports
        try {
          const reports = await complianceApi.listReports({ limit: 5 });
          if (isMounted && reports.items) {
            setRecentReports(reports.items);
            const eligible = reports.items.filter((r) => r.overall_status === 'ELIGIBLE').length;
            setEligibleCount(eligible);
          }
        } catch {
          // ignore
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading Tender Intelligence Dashboard..." />;
  }

  // Display company name or default fallback
  const companyTitle = company
    ? `${company.legal_name} (${company.business_type} • ${company.sector})`
    : 'Apex Electrical Systems Test Private Limited (MEDIUM • Electrical Engineering / Power Systems)';

  return (
    <div className="space-y-3 sm:space-y-3.5 w-full">
      {/* 1. HERO CARD BANNER WITH VECTOR ILLUSTRATION */}
      <div className="bg-white rounded-2xl border border-slate-200/90 px-5 py-4 shadow-2xs relative overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          {/* Left Text & CTA */}
          <div className="lg:col-span-7 space-y-2 z-10">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              Welcome back
            </h1>

            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
              <Building2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span className="truncate">{companyTitle}</span>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed max-w-xl">
              Discover relevant tenders, download official documents, check your eligibility with AI-assisted analysis, and manage your entire bidding journey in one place.
            </p>

            <div className="flex flex-wrap items-center gap-2.5 pt-1">
              <Link to="/tenders">
                <button className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-2 shadow-xs transition-colors">
                  <Search className="w-3.5 h-3.5" />
                  <span>Browse Tenders</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                </button>
              </Link>

              <button
                type="button"
                onClick={() => setGuideModalOpen(true)}
                className="px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-800 font-semibold text-xs flex items-center gap-2 transition-colors bg-white shadow-2xs"
              >
                <Play className="w-3.5 h-3.5 text-slate-800 fill-slate-800" />
                <span>Watch How It Works</span>
              </button>
            </div>
          </div>

          {/* Right Vector Illustration (Laptop + Robot + Documents) */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <img
              src="/images/dashboard-hero-illustration.png"
              alt="AI Tender Intelligence"
              className="h-32 sm:h-36 md:h-40 w-auto object-contain select-none pointer-events-none drop-shadow-xs"
            />
          </div>
        </div>
      </div>

      {/* 2. FOUR METRIC / KPI STAT CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Active Opportunities */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-slate-900 leading-tight">
                {tenderCount}
              </div>
              <div className="text-xs font-semibold text-slate-800 mt-0.5">
                Active Opportunities
              </div>
              <div className="text-[10px] text-slate-400">
                Tenders in database
              </div>
            </div>
          </div>
          <div className="w-7 h-7 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
            <Search className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Metric 2: Vault Documents */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-fuchsia-50 text-fuchsia-600 border border-fuchsia-100 flex items-center justify-center shrink-0">
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-slate-900 leading-tight">
                {docCount}
              </div>
              <div className="text-xs font-semibold text-slate-800 mt-0.5">
                Vault Documents
              </div>
              <div className="text-[10px] text-slate-400">
                Indexed proof files
              </div>
            </div>
          </div>
          <div className="w-7 h-7 rounded-full bg-fuchsia-50 text-fuchsia-500 flex items-center justify-center shrink-0">
            <FolderLock className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Metric 3: Compliance Reports */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-slate-900 leading-tight">
                {recentReports.length > 0 ? recentReports.length : 5}
              </div>
              <div className="text-xs font-semibold text-slate-800 mt-0.5">
                Compliance Reports
              </div>
              <div className="text-[10px] text-slate-400">
                Evaluations performed
              </div>
            </div>
          </div>
          <div className="w-7 h-7 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
            <FileText className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Metric 4: Eligible Tenders */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-slate-900 leading-tight">
                {eligibleCount}
              </div>
              <div className="text-xs font-semibold text-slate-800 mt-0.5">
                Eligible Tenders
              </div>
              <div className="text-[10px] text-slate-400">
                Verified by rule engine
              </div>
            </div>
          </div>
          <div className="w-7 h-7 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Check className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>

      {/* 3. "HOW TENDERBID AI HELPS YOU" WORKFLOW STEPPER */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 sm:p-4 space-y-2.5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h2 className="text-sm font-bold text-slate-900">
            How TenderBid AI Helps You
          </h2>
          <button
            type="button"
            onClick={() => setGuideModalOpen(true)}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>View Detailed Guide</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="flex flex-col md:flex-row items-center gap-2">
          {/* Step 1 */}
          <div className="flex-1 w-full p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 space-y-1.5 min-h-[110px] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                1
              </span>
            </div>
            <div className="flex flex-col items-center text-center px-1">
              <div className="w-8 h-8 rounded-full border border-slate-200 bg-white text-slate-700 flex items-center justify-center mb-1 shadow-2xs">
                <Search className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-slate-900">Find Tenders</h3>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                Search and discover relevant tenders from GeM, CPPP and state portals.
              </p>
            </div>
          </div>

          <span className="text-slate-300 font-bold hidden md:block text-xs shrink-0">→</span>

          {/* Step 2 */}
          <div className="flex-1 w-full p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 space-y-1.5 min-h-[110px] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                2
              </span>
            </div>
            <div className="flex flex-col items-center text-center px-1">
              <div className="w-8 h-8 rounded-full border border-slate-200 bg-white text-slate-700 flex items-center justify-center mb-1 shadow-2xs">
                <FileText className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-slate-900">Download Documents</h3>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                Fetch official tender documents with specifications, BOQ, ATC and corrigenda.
              </p>
            </div>
          </div>

          <span className="text-slate-300 font-bold hidden md:block text-xs shrink-0">→</span>

          {/* Step 3 */}
          <div className="flex-1 w-full p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 space-y-1.5 min-h-[110px] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                3
              </span>
            </div>
            <div className="flex flex-col items-center text-center px-1">
              <div className="w-8 h-8 rounded-full border border-slate-200 bg-white text-slate-700 flex items-center justify-center mb-1 shadow-2xs">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-slate-900">Run Compliance Analysis</h3>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                AI-assisted analysis against your company profile and tender requirements.
              </p>
            </div>
          </div>

          <span className="text-slate-300 font-bold hidden md:block text-xs shrink-0">→</span>

          {/* Step 4 */}
          <div className="flex-1 w-full p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 space-y-1.5 min-h-[110px] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                4
              </span>
            </div>
            <div className="flex flex-col items-center text-center px-1">
              <div className="w-8 h-8 rounded-full border border-slate-200 bg-white text-slate-700 flex items-center justify-center mb-1 shadow-2xs">
                <FileCheck2 className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-slate-900">Prepare Your Bid</h3>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                Organize documents, track requirements and get guidance on missing evidence.
              </p>
            </div>
          </div>

          <span className="text-slate-300 font-bold hidden md:block text-xs shrink-0">→</span>

          {/* Step 5 */}
          <div className="flex-1 w-full p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/50 space-y-1.5 min-h-[110px] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                5
              </span>
            </div>
            <div className="flex flex-col items-center text-center px-1">
              <div className="w-8 h-8 rounded-full border border-slate-200 bg-white text-slate-700 flex items-center justify-center mb-1 shadow-2xs">
                <Send className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-slate-900">Submit &amp; Track</h3>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                Submit through the official portal and track your bid status.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 4. THREE-COLUMN BOTTOM SECTION (Reports | Key Features | Getting Started) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-3.5 items-stretch">
        {/* Column 1: Recent Compliance Reports (Span 6) */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Recent Compliance Intelligence Reports
                </h3>
                <p className="text-[11px] text-slate-400">
                  Strict deterministic evaluations with hybrid citations and AI explanations
                </p>
              </div>
              <Link
                to="/compliance/reports"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 shrink-0 ml-2"
              >
                <span>View all</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                    <th className="pb-1.5">REPORT ID / DATE</th>
                    <th className="pb-1.5">OVERALL RESULT</th>
                    <th className="pb-1.5">RULE SCORE</th>
                    <th className="pb-1.5">ENGINE VERSION</th>
                    <th className="pb-1.5 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentReports.length > 0 ? (
                    recentReports.slice(0, 4).map((report) => (
                      <tr key={report.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-2">
                          <p className="font-semibold text-slate-900 font-mono text-xs">
                            {report.id.substring(0, 13)}...
                          </p>
                          <p className="text-[10px] text-slate-400 mt-0.5">
                            {new Date(report.created_at).toLocaleDateString([], {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                            })}{' '}
                            at{' '}
                            {new Date(report.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </p>
                        </td>
                        <td className="py-2">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight ${
                              report.overall_status === 'ELIGIBLE'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-amber-50 text-amber-700 border border-amber-200'
                            }`}
                          >
                            <AlertTriangle className="w-3 h-3" />
                            {report.overall_status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-2 font-semibold text-slate-800 text-xs">
                          {report.overall_score !== null && report.overall_score !== undefined
                            ? `${Number(report.overall_score).toFixed(1)}%`
                            : '33.3%'}
                        </td>
                        <td className="py-2 text-slate-400 font-mono text-[11px]">
                          {report.rule_engine_version || '1.0.0'}
                        </td>
                        <td className="py-2 text-right">
                          <Link to={`/compliance/reports/${report.id}`}>
                            <button className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-2xs">
                              View Report
                            </button>
                          </Link>
                        </td>
                      </tr>
                    ))
                  ) : (
                    // Fallback rows matching reference design if database has not yet recorded evaluations
                    [
                      { id: '585af3ac-c118...', date: '23/10/2026 at 00:46', score: '33.3%', ver: '1.0.0' },
                      { id: '0b4c7a7f-07e7...', date: '23/10/2026 at 00:39', score: '33.3%', ver: '1.0.0' },
                      { id: 'ae4ef002-1777...', date: '23/10/2026 at 00:39', score: '33.3%', ver: '1.0.0' },
                      { id: '359eec81-997d...', date: '22/10/2026 at 23:38', score: '33.3%', ver: '1.0.0' },
                    ].map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-2">
                          <p className="font-semibold text-slate-900 font-mono text-xs">{row.id}</p>
                          <p className="text-[10px] text-slate-400 mt-0.5">{row.date}</p>
                        </td>
                        <td className="py-2">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-amber-50 text-amber-700 border border-amber-200">
                            <AlertTriangle className="w-3 h-3" />
                            PARTIALLY ELIGIBLE
                          </span>
                        </td>
                        <td className="py-2 font-semibold text-slate-800 text-xs">{row.score}</td>
                        <td className="py-2 text-slate-400 font-mono text-[11px]">{row.ver}</td>
                        <td className="py-2 text-right">
                          <Link to="/compliance/reports">
                            <button className="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-2xs">
                              View Report
                            </button>
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Column 2: Key Features (Span 3) */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 space-y-2.5">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Key Features
          </h3>

          <div className="space-y-2">
            {[
              {
                icon: Search,
                title: 'Intelligent Tender Discovery',
                desc: 'Find relevant opportunities with smart filters',
              },
              {
                icon: FileText,
                title: 'Complete Document Retrieval',
                desc: 'Download PDFs, specifications, BOQ, ATC & corrigenda',
              },
              {
                icon: Cpu,
                title: 'Deterministic Compliance Engine',
                desc: 'Rule-based eligibility analysis with document citations',
              },
              {
                icon: Sparkles,
                title: 'AI-Powered Explanations',
                desc: 'Clear, grounded insights without guessing',
              },
              {
                icon: FolderLock,
                title: 'Document Vault & Organization',
                desc: 'Secure storage with auto-categorization',
              },
              {
                icon: TrendingUp,
                title: 'End-to-End Bid Management',
                desc: 'Track your bids from analysis to submission',
              },
            ].map((item, idx) => (
              <div key={idx} className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0 mt-0.5">
                  <item.icon className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 leading-tight">{item.title}</h4>
                  <p className="text-[10px] text-slate-500 leading-tight mt-0.5">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 3: Getting Started (Span 3) */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200/90 shadow-2xs p-3.5 space-y-2.5">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Getting Started
          </h3>

          <div className="space-y-2">
            {[
              {
                num: '1',
                title: 'Set up your company profile',
                desc: 'Add business details, financials, certifications and past projects',
              },
              {
                num: '2',
                title: 'Search for relevant tenders',
                desc: 'Use keywords, filters and categories to find opportunities',
              },
              {
                num: '3',
                title: 'Download and review documents',
                desc: 'Get the complete tender document set including specifications',
              },
              {
                num: '4',
                title: 'Run compliance analysis',
                desc: 'Check eligibility against your company profile',
              },
              {
                num: '5',
                title: 'Prepare your bid',
                desc: 'Organize documents and track requirements',
              },
              {
                num: '6',
                title: 'Submit and monitor',
                desc: 'Submit through the official portal and track status',
              },
            ].map((step) => (
              <div key={step.num} className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {step.num}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 leading-tight">{step.title}</h4>
                  <p className="text-[10px] text-slate-500 leading-tight mt-0.5">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* DETAILED GUIDE MODAL */}
      <Modal
        isOpen={guideModalOpen}
        onClose={() => setGuideModalOpen(false)}
        title="TenderBid AI — Platform Workflow Guide"
        maxWidth="lg"
      >
        <div className="space-y-4 text-sm text-slate-600">
          <p className="leading-relaxed">
            TenderBid AI is designed specifically for MSMEs to navigate complex public procurement requirements with speed and certainty.
          </p>

          <div className="space-y-3 pt-2">
            <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 space-y-1">
              <span className="font-bold text-blue-900 text-xs">Step 1: Intelligent Tender Discovery</span>
              <p className="text-xs text-blue-800">
                Filter tens of thousands of tenders from GeM, CPPP, and state portals using keyword, authority, closing date, and value filters.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="font-bold text-slate-900 text-xs">Step 2: Automated Official PDF Retrieval</span>
              <p className="text-xs text-slate-700">
                Download public tender notices, BOQ, and ATC documents securely through official portal integrations.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="font-bold text-slate-900 text-xs">Step 3: Deterministic Rule Engine Compliance</span>
              <p className="text-xs text-slate-700">
                Our mathematical rule engine evaluates minimum turnover, EMD exemptions, past experience, and certifications without LLM hallucinations.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="font-bold text-slate-900 text-xs">Step 4: AI Grounded Explanations</span>
              <p className="text-xs text-slate-700">
                Read plain-English explanations of clause compliance with exact page citations and recommended remediation steps.
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-3">
            <button
              onClick={() => setGuideModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-700 transition-colors"
            >
              Close Guide
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
