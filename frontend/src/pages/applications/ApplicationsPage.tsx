import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { applicationsApi } from '../../api/applicationsApi';
import { BidApplicationResponse } from '../../types/application';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import {
  FolderKanban,
  FileText,
  Calendar,
  Coins,
  CheckCircle2,
  Clock,
  ArrowRight,
  ExternalLink,
  Trash2,
  AlertCircle,
  FileCheck2,
  TrendingUp,
} from 'lucide-react';

const STAGES = [
  { key: 'ALL', label: 'All Bids' },
  { key: 'IDENTIFIED', label: '1. Identified', color: 'bg-slate-100 text-slate-800' },
  { key: 'PREPARING', label: '2. Preparing Proofs', color: 'bg-blue-100 text-blue-800' },
  { key: 'READY', label: '3. Ready for Submission', color: 'bg-indigo-100 text-indigo-800' },
  { key: 'SUBMITTED', label: '4. Submitted by MSME', color: 'bg-purple-100 text-purple-800' },
  { key: 'AWARDED', label: '5. Contract Awarded', color: 'bg-emerald-100 text-emerald-800' },
  { key: 'REJECTED', label: 'Declined / Rejected', color: 'bg-rose-100 text-rose-800' },
];

const ALLOWED_NEXT_STAGES: Record<string, string[]> = {
  IDENTIFIED: ['PREPARING', 'REJECTED'],
  PREPARING: ['READY', 'REJECTED', 'IDENTIFIED'],
  READY: ['SUBMITTED', 'PREPARING', 'REJECTED'],
  SUBMITTED: ['AWARDED', 'REJECTED'],
  AWARDED: [],
  REJECTED: ['IDENTIFIED', 'PREPARING'],
};

export const ApplicationsPage: React.FC = () => {
  const [applications, setApplications] = useState<BidApplicationResponse[]>([]);
  const [selectedStage, setSelectedStage] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await applicationsApi.listApplications(
        selectedStage === 'ALL' ? undefined : selectedStage
      );
      setApplications(data.items);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [selectedStage]);

  const handleStageTransition = async (appId: string, nextStage: string) => {
    setUpdatingId(appId);
    setError(null);
    try {
      await applicationsApi.updateApplication(appId, { status: nextStage });
      await fetchApplications();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to update stage transition.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDelete = async (appId: string) => {
    if (!window.confirm('Are you sure you want to remove this tender from your preparation pipeline?')) {
      return;
    }
    setError(null);
    try {
      await applicationsApi.deleteApplication(appId);
      setApplications(applications.filter((a) => a.id !== appId));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  const formatINR = (val?: number | null) => {
    if (!val) return 'N/A';
    return `₹ ${Number(val).toLocaleString('en-IN')}`;
  };

  const getStageBadgeColor = (status: string) => {
    const s = STAGES.find((x) => x.key === status);
    return s?.color || 'bg-slate-100 text-slate-800';
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <FolderKanban className="w-7 h-7 text-blue-600" />
            Internal Bid Preparation Pipeline
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Track your company's tender preparation workflow from discovery to submission.
          </p>
        </div>

        <Link to="/tenders">
          <Button size="sm" icon={<TrendingUp className="w-4 h-4" />}>
            Find New Opportunities
          </Button>
        </Link>
      </div>

      {/* Disclaimers & Guarantees */}
      <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-800 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 shrink-0 text-blue-600 mt-0.5" />
        <div>
          <p className="font-bold">Internal Workflow Notice</p>
          <p className="mt-0.5 text-blue-700">
            This pipeline is an internal MSME project tracker. The platform assists in requirement verification and proof collation, but does not submit bids to official government portals (e.g. GeM, CPPP). Bids must be submitted directly to the issuing authority.
          </p>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Stage Filter Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {STAGES.map((s) => {
          const isActive = selectedStage === s.key;
          return (
            <button
              key={s.key}
              onClick={() => setSelectedStage(s.key)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Loading tracked applications..." />
      ) : applications.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8 shadow-xs">
          <FolderKanban className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Tracked Applications</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-6">
            You haven't tracked any tenders in this stage yet. Browse open tenders and click &ldquo;Track in Pipeline&rdquo; to begin.
          </p>
          <Link to="/tenders">
            <Button size="sm">Browse Tender Opportunities</Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {applications.map((app) => {
            const nextStages = ALLOWED_NEXT_STAGES[app.status] || [];
            return (
              <div
                key={app.id}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow"
              >
                <div>
                  {/* Status Badge & Actions */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${getStageBadgeColor(
                        app.status
                      )}`}
                    >
                      {app.status}
                    </span>
                    <button
                      onClick={() => handleDelete(app.id)}
                      className="text-slate-400 hover:text-rose-600 p-1 rounded-md hover:bg-rose-50 transition-colors"
                      title="Untrack Bid"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Reference & Title */}
                  <p className="text-xs font-mono font-bold text-blue-700 mb-1">
                    {app.tender_reference || 'REF-N/A'}
                  </p>
                  <h3 className="text-sm font-bold text-slate-900 line-clamp-2 mb-3">
                    {app.tender_title || 'Untitled Tender Opportunity'}
                  </h3>

                  {/* Metadata items */}
                  <div className="space-y-1.5 text-xs text-slate-500 mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Coins className="w-3.5 h-3.5 text-slate-400" /> Value:
                      </span>
                      <strong className="text-slate-800">{formatINR(app.estimated_budget_inr)}</strong>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" /> Deadline:
                      </span>
                      <strong className="text-slate-800">
                        {app.submission_deadline
                          ? new Date(app.submission_deadline).toLocaleDateString()
                          : 'Not set'}
                      </strong>
                    </div>

                    {app.latest_compliance_status && (
                      <div className="flex items-center justify-between pt-1 border-t border-slate-200">
                        <span className="flex items-center gap-1.5">
                          <FileCheck2 className="w-3.5 h-3.5 text-indigo-500" /> Evaluation:
                        </span>
                        <Link
                          to={`/compliance/reports/${app.latest_report_id}`}
                          className="font-bold text-blue-600 hover:underline flex items-center gap-1"
                        >
                          {app.latest_compliance_status} ({app.latest_compliance_score}%)
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                    )}
                  </div>

                  {app.notes && (
                    <p className="text-xs text-slate-600 italic bg-amber-50/60 border border-amber-100 p-2.5 rounded-lg mb-4">
                      &ldquo;{app.notes}&rdquo;
                    </p>
                  )}
                </div>

                {/* Stage Progression Buttons */}
                <div className="pt-3 border-t border-slate-100 space-y-2">
                  {nextStages.length > 0 ? (
                    <div>
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                        Move to Next Stage:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {nextStages.map((st) => (
                          <button
                            key={st}
                            disabled={updatingId === app.id}
                            onClick={() => handleStageTransition(app.id, st)}
                            className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors border border-slate-200"
                          >
                            &rarr; {st}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Stage Complete
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-2 text-xs">
                    <Link
                      to={`/tenders/${app.tender_id}`}
                      className="text-blue-600 hover:underline font-medium inline-flex items-center gap-1"
                    >
                      View Notice Details &rarr;
                    </Link>
                    <Link
                      to={`/compliance/analyze?tender_id=${app.tender_id}`}
                      className="text-slate-500 hover:text-slate-800 font-medium"
                    >
                      Evaluate
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
