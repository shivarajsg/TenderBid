import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { complianceApi } from '../../api/complianceApi';
import { ComplianceReportResponse } from '../../types/compliance';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import { History, Filter, FileText, ArrowRight, Plus } from 'lucide-react';

export const ComplianceReportsListPage: React.FC = () => {
  const [reports, setReports] = useState<ComplianceReportResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async (status?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await complianceApi.listReports({
        status: status || undefined,
        limit: 50,
      });
      setReports(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports(statusFilter);
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <History className="w-7 h-7 text-blue-600" />
            Compliance Reports History
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative audit trail of deterministic eligibility evaluations and RAG evidence
          </p>
        </div>

        <Link to="/compliance/analyze">
          <Button size="sm" icon={<Plus className="w-4 h-4" />}>
            Run New Analysis
          </Button>
        </Link>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
            Filter by Status:
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="">All Statuses ({total})</option>
            <option value="ELIGIBLE">ELIGIBLE</option>
            <option value="PARTIALLY_ELIGIBLE">PARTIALLY ELIGIBLE</option>
            <option value="NOT_ELIGIBLE">NOT ELIGIBLE</option>
            <option value="NEEDS_REVIEW">NEEDS REVIEW</option>
          </select>
        </div>

        <div className="text-xs text-slate-500">
          Showing <span className="font-semibold text-slate-800">{reports.length}</span> reports
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Loading historical compliance records..." />
      ) : reports.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200">
          <EmptyState
            title="No compliance reports found"
            description="You have not evaluated any tenders matching this filter yet."
            actionLabel="Evaluate a Tender Now"
            onAction={() => {
              window.location.href = '/compliance/analyze';
            }}
          />
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3.5">Report / Date</th>
                  <th className="px-6 py-3.5">Eligibility Result</th>
                  <th className="px-6 py-3.5">Score</th>
                  <th className="px-6 py-3.5">Criteria Tested</th>
                  <th className="px-6 py-3.5">Engine Version</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-semibold text-slate-900 font-mono text-xs">
                        {report.id.substring(0, 18)}...
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {new Date(report.created_at).toLocaleDateString()} at{' '}
                        {new Date(report.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </td>

                    <td className="px-6 py-4">
                      <StatusBadge status={report.overall_status} />
                    </td>

                    <td className="px-6 py-4">
                      <span className="font-bold text-slate-900 text-sm">
                        {report.overall_score !== null && report.overall_score !== undefined
                          ? `${Number(report.overall_score).toFixed(1)}%`
                          : '—'}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-xs text-slate-600">
                      {report.findings?.length || 0} criteria
                    </td>

                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
                      {report.rule_engine_version}
                    </td>

                    <td className="px-6 py-4 text-right">
                      <Link to={`/compliance/reports/${report.id}`}>
                        <Button variant="outline" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                          Inspect Report
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
