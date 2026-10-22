import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { companyApi } from '../../api/companyApi';
import { tendersApi } from '../../api/tendersApi';
import { documentsApi } from '../../api/documentsApi';
import { complianceApi } from '../../api/complianceApi';
import { CompanyResponse } from '../../types/company';
import { ComplianceReportResponse } from '../../types/compliance';
import { MetricCard } from '../../components/common/MetricCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { Button } from '../../components/common/Button';
import {
  Building2,
  FileText,
  FileCheck2,
  Search,
  FolderLock,
  ArrowRight,
  AlertCircle,
  PlusCircle,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [tenderCount, setTenderCount] = useState<number>(0);
  const [docCount, setDocCount] = useState<number>(0);
  const [recentReports, setRecentReports] = useState<ComplianceReportResponse[]>([]);
  const [eligibleCount, setEligibleCount] = useState<number>(0);

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
          if (isMounted) setTenderCount(tenders.total);
        } catch {
          // ignore
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
          if (isMounted) {
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
    return <LoadingSpinner message="Aggregating platform intelligence..." />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Welcome back, {user?.full_name}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {company ? (
              <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                <Building2 className="w-4 h-4 text-blue-600" />
                {company.legal_name} ({company.business_type} • {company.sector})
              </span>
            ) : (
              'Agentic Tender Intelligence & Deterministic Verification'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/tenders">
            <Button variant="outline" size="sm" icon={<Search className="w-4 h-4" />}>
              Browse Tenders
            </Button>
          </Link>
          <Link to="/compliance/analyze">
            <Button size="sm" icon={<FileCheck2 className="w-4 h-4" />}>
              Run Compliance
            </Button>
          </Link>
        </div>
      </div>

      {/* Onboarding Notice if company profile is missing */}
      {!company && (
        <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-900">
                Company Profile Setup Required
              </h3>
              <p className="text-xs text-amber-700 mt-1 max-w-2xl">
                To run deterministic compliance evaluation and RAG verification on government tenders,
                please register your company credentials (turnover, incorporation date, sector, work experience).
              </p>
            </div>
          </div>
          <Link to="/company" className="shrink-0">
            <Button size="sm" variant="primary" icon={<PlusCircle className="w-4 h-4" />}>
              Create Company Profile
            </Button>
          </Link>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Active Opportunities"
          value={tenderCount}
          subtitle="Tenders in database"
          icon={<Search className="w-5 h-5" />}
          colorScheme="blue"
        />
        <MetricCard
          title="Vault Documents"
          value={docCount}
          subtitle="Indexed proof files"
          icon={<FolderLock className="w-5 h-5" />}
          colorScheme="purple"
        />
        <MetricCard
          title="Compliance Reports"
          value={recentReports.length}
          subtitle="Evaluations performed"
          icon={<FileText className="w-5 h-5" />}
          colorScheme="slate"
        />
        <MetricCard
          title="Eligible Tenders"
          value={eligibleCount}
          subtitle="Verified by rule engine"
          icon={<FileCheck2 className="w-5 h-5" />}
          colorScheme="emerald"
        />
      </div>

      {/* Recent Compliance Evaluations */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Recent Compliance Intelligence Reports
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Strict deterministic evaluations with hybrid citations and AI explanations
            </p>
          </div>
          {recentReports.length > 0 && (
            <Link
              to="/compliance/reports"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1"
            >
              View all ({recentReports.length})
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {recentReports.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No compliance reports yet"
              description="Select any active tender to test your company qualifications against official criteria."
              actionLabel="Run First Compliance Analysis"
              onAction={() => {
                window.location.href = '/compliance/analyze';
              }}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Report ID / Date</th>
                  <th className="px-6 py-3">Overall Result</th>
                  <th className="px-6 py-3">Rule Score</th>
                  <th className="px-6 py-3">Engine Version</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentReports.map((report) => (
                  <tr key={report.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-slate-900 truncate max-w-xs">
                        {report.id.substring(0, 13)}...
                      </p>
                      <p className="text-xs text-slate-400">
                        {new Date(report.created_at).toLocaleDateString()} at{' '}
                        {new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={report.overall_status} />
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-semibold text-slate-800">
                        {report.overall_score !== null && report.overall_score !== undefined
                          ? `${Number(report.overall_score).toFixed(1)}%`
                          : '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-500">
                      {report.rule_engine_version}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link to={`/compliance/reports/${report.id}`}>
                        <Button variant="outline" size="sm">
                          View Report
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
