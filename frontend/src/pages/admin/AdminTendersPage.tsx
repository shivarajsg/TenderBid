import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { tendersApi } from '../../api/tendersApi';
import { adminApi } from '../../api/adminApi';
import {
  TenderResponse,
  TenderProcessingStatusResponse,
  ProposedRequirementsBundle,
  IngestionStatusOverviewResponse,
} from '../../types/tender';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { Modal } from '../../components/common/Modal';
import { getErrorMessage } from '../../api/client';
import {
  ShieldAlert,
  Plus,
  Upload,
  Cpu,
  Trash2,
  FileText,
  Activity,
  CheckCircle,
  ExternalLink,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Globe,
  Radio,
} from 'lucide-react';

export const AdminTendersPage: React.FC = () => {
  const [tenders, setTenders] = useState<TenderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Government Ingestion state
  const [ingestionOverview, setIngestionOverview] = useState<IngestionStatusOverviewResponse | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncSuccessMsg, setSyncSuccessMsg] = useState<string | null>(null);

  // Upload modal state
  const [uploadTenderId, setUploadTenderId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Processing state
  const [processingId, setProcessingId] = useState<string | null>(null);

  // Status modal state
  const [statusDetails, setStatusDetails] = useState<TenderProcessingStatusResponse | null>(null);

  // Requirements Extraction & Review Modal state
  const [isExtractingId, setIsExtractingId] = useState<string | null>(null);
  const [reviewBundle, setReviewBundle] = useState<ProposedRequirementsBundle | null>(null);
  const [isApproving, setIsApproving] = useState(false);

  const handleExtractCriteria = async (tenderId: string) => {
    setIsExtractingId(tenderId);
    setError(null);
    try {
      const bundle = await tendersApi.extractTenderRequirements(tenderId);
      setReviewBundle(bundle);
      await fetchTenders();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to extract criteria from documents.');
    } finally {
      setIsExtractingId(null);
    }
  };

  const handleReviewCriteria = async (tenderId: string) => {
    setError(null);
    try {
      const bundle = await tendersApi.getProposedRequirements(tenderId);
      if (bundle) {
        setReviewBundle(bundle);
      } else {
        setError('No proposed requirements found. Click "Extract Criteria" first.');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  const handleApproveCriteria = async () => {
    if (!reviewBundle) return;
    setIsApproving(true);
    setError(null);
    try {
      await tendersApi.approveProposedRequirements(reviewBundle.tender_id);
      setReviewBundle(null);
      await fetchTenders();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to approve requirements.');
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectCriteria = async () => {
    if (!reviewBundle) return;
    setIsApproving(true);
    setError(null);
    try {
      await tendersApi.rejectProposedRequirements(reviewBundle.tender_id);
      setReviewBundle(null);
      await fetchTenders();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to reject requirements.');
    } finally {
      setIsApproving(false);
    }
  };

  const fetchIngestionStatus = async () => {
    try {
      const data = await tendersApi.getIngestionStatus();
      setIngestionOverview(data);
    } catch {
      // Non-blocking status polling
    }
  };

  const handleTriggerSync = async (portal = 'ALL') => {
    setIsSyncing(true);
    setError(null);
    setSyncSuccessMsg(null);
    try {
      const res = await tendersApi.triggerIngestionSync(portal);
      setSyncSuccessMsg(
        `Government sync complete! ${res.tenders_ingested} newly ingested, ${res.tenders_updated} updated, ${res.tenders_skipped} unchanged.`
      );
      await fetchTenders();
      await fetchIngestionStatus();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsSyncing(false);
    }
  };

  const fetchTenders = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await tendersApi.listTenders({ limit: 100 });
      setTenders(data.items);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenders();
    fetchIngestionStatus();
  }, []);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadTenderId || selectedFiles.length === 0) return;

    setIsUploading(true);
    setError(null);
    try {
      await adminApi.uploadTenderDocs(uploadTenderId, selectedFiles);
      setUploadTenderId(null);
      setSelectedFiles([]);
      await fetchTenders();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  const handleProcess = async (tenderId: string) => {
    setProcessingId(tenderId);
    setError(null);
    try {
      await adminApi.processTender(tenderId);
      await fetchTenders();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setProcessingId(null);
    }
  };

  const handleInspectStatus = async (tenderId: string) => {
    try {
      const status = await adminApi.getProcessingStatus(tenderId);
      setStatusDetails(status);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async (tenderId: string, reference: string) => {
    if (
      !window.confirm(
        `Are you sure you want to permanently delete tender ${reference}? All vector chunks will be purged.`
      )
    ) {
      return;
    }
    try {
      await adminApi.deleteTender(tenderId);
      setTenders((prev) => prev.filter((t) => t.id !== tenderId));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-purple-600" />
            Admin Tender Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Publish tenders, ingest PDF specifications, and monitor automated government portal feeds
          </p>
        </div>

        <Link to="/admin/tenders/new">
          <Button size="sm" icon={<Plus className="w-4 h-4" />}>
            Create New Tender
          </Button>
        </Link>
      </div>

      {/* Government Ingestion Control Center */}
      <div className="bg-slate-900 text-white p-5 rounded-2xl shadow-sm border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-bold text-white">Government Tender Ingestion Connectors</h2>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2 py-0.5 rounded-full">
                <Radio className="w-2.5 h-2.5 animate-pulse text-emerald-400" />
                Scheduler {ingestionOverview?.scheduler_running ? 'Active (Hourly)' : 'Online'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Automated polling across GeM, CPPP & Open Government data repositories with transparent ethical access enforcement
            </p>
          </div>

          <Button
            size="sm"
            onClick={() => handleTriggerSync('ALL')}
            disabled={isSyncing}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />}
          >
            {isSyncing ? 'Syncing Feeds...' : 'Sync All Portals Now'}
          </Button>
        </div>

        {syncSuccessMsg && (
          <div className="mt-3 text-xs bg-emerald-950/80 border border-emerald-700/60 text-emerald-200 px-3 py-2 rounded-xl flex items-center justify-between">
            <span>{syncSuccessMsg}</span>
            <button onClick={() => setSyncSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-2">×</button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 text-xs">
          {(ingestionOverview?.portals || []).map((portal) => (
            <div key={portal.portal_name} className="bg-slate-800/80 rounded-xl p-3.5 border border-slate-700/60">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">{portal.portal_title}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                  portal.status === 'ACTIVE'
                    ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/60'
                    : 'bg-amber-900/60 text-amber-300 border border-amber-700/60'
                }`}>
                  {portal.status === 'ACTIVE' ? 'LIVE FEED' : 'VERIFIED FIXTURE'}
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-1.5">{portal.access_mode}</p>
              <div className="mt-2.5 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-300">
                <span>Ingested: <strong className="text-white">{portal.total_tenders_ingested}</strong> notices</span>
                <a
                  href={portal.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:underline flex items-center gap-1"
                >
                  Portal <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Loading all administrative tender notices..." />
      ) : tenders.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200">
          <EmptyState
            title="No tenders created yet"
            description="Create your first procurement notice to ingest RFP files and extract eligibility requirements."
            actionLabel="Create Tender Notice"
            onAction={() => {
              window.location.href = '/admin/tenders/new';
            }}
          />
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3.5">Reference / Title</th>
                  <th className="px-6 py-3.5">Authority / Sector</th>
                  <th className="px-6 py-3.5">Processing Status</th>
                  <th className="px-6 py-3.5">Attached Docs</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tenders.map((tender) => (
                  <tr key={tender.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-blue-700">
                          {tender.tender_reference}
                        </span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                          (tender.source_portal || 'MANUAL').toUpperCase() === 'GEM'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : (tender.source_portal || 'MANUAL').toUpperCase() === 'CPPP'
                            ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
                            : (tender.source_portal || 'MANUAL').toUpperCase() === 'OPEN_GOV'
                            ? 'bg-cyan-50 text-cyan-800 border-cyan-200'
                            : (tender.source_portal || 'MANUAL').toUpperCase() === 'TENDERKART'
                            ? 'bg-purple-50 text-purple-800 border-purple-200'
                            : (tender.source_portal || 'MANUAL').toUpperCase() === 'APIFY'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-slate-50 text-slate-600 border-slate-200'
                        }`}>
                          {tender.source_portal || 'MANUAL'}
                        </span>
                      </div>
                      <p className="font-semibold text-slate-900 line-clamp-1 max-w-sm mt-0.5">
                        {tender.title}
                      </p>
                    </td>

                    <td className="px-6 py-4 text-xs">
                      <p className="font-medium text-slate-800">{tender.issuing_authority}</p>
                      <p className="text-slate-400">{tender.sector}</p>
                    </td>

                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium ${
                          tender.processing_status === 'COMPLETED'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : tender.processing_status === 'PROCESSING'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {tender.processing_status}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-xs">
                      <button
                        onClick={() => handleInspectStatus(tender.id)}
                        className="text-blue-600 hover:underline font-semibold"
                      >
                        {tender.documents.length} document(s)
                      </button>
                    </td>

                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          icon={<Upload className="w-3.5 h-3.5" />}
                          onClick={() => setUploadTenderId(tender.id)}
                          title="Upload RFP PDFs"
                        >
                          Upload
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          isLoading={processingId === tender.id}
                          icon={<Cpu className="w-3.5 h-3.5 text-purple-600" />}
                          onClick={() => handleProcess(tender.id)}
                          title="Extract text & vectorize chunks"
                        >
                          Vectorize
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          isLoading={isExtractingId === tender.id}
                          icon={<Sparkles className="w-3.5 h-3.5 text-blue-600" />}
                          onClick={() => handleExtractCriteria(tender.id)}
                          title="Auto-extract requirements from documents"
                        >
                          Extract Criteria
                        </Button>

                        {tender.proposed_requirements && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-amber-700 bg-amber-50 border-amber-200 hover:bg-amber-100"
                            onClick={() => handleReviewCriteria(tender.id)}
                            title="Review extracted requirements"
                          >
                            Review Criteria
                          </Button>
                        )}

                        <button
                          onClick={() => handleDelete(tender.id, tender.tender_reference)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                          title="Delete Tender"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Docs Modal */}
      <Modal
        isOpen={!!uploadTenderId}
        onClose={() => !isUploading && setUploadTenderId(null)}
        title="Upload Tender RFP Documents"
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Select PDF Documents
            </label>
            <input
              type="file"
              multiple
              accept=".pdf,application/pdf"
              required
              onChange={(e) => {
                if (e.target.files) {
                  setSelectedFiles(Array.from(e.target.files));
                }
              }}
              className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              disabled={isUploading}
              onClick={() => setUploadTenderId(null)}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isUploading} icon={<Upload className="w-4 h-4" />}>
              Upload PDF(s)
            </Button>
          </div>
        </form>
      </Modal>

      {/* Status Details Modal */}
      <Modal
        isOpen={!!statusDetails}
        onClose={() => setStatusDetails(null)}
        title="Tender Processing & Indexing Breakdown"
        maxWidth="lg"
      >
        {statusDetails && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-600 bg-slate-50 p-3 rounded-xl">
              <span>Overall Status: {statusDetails.processing_status}</span>
              <span>Total Documents: {statusDetails.total_documents}</span>
            </div>

            <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
              {statusDetails.documents.map((d) => (
                <div key={d.id} className="py-3 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-slate-800">
                    <span className="truncate max-w-xs">{d.original_filename}</span>
                    <span className="font-mono text-purple-700">{d.processing_status}</span>
                  </div>
                  <div className="text-slate-500 flex gap-4">
                    <span>Pages: {d.total_pages || 0}</span>
                    <span>Chunks: {d.indexed_chunks}</span>
                    <span>Hash: {d.sha256_hash.substring(0, 12)}...</span>
                  </div>
                  {d.error_message && (
                    <p className="text-rose-600 font-medium">{d.error_message}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>

      {/* Review & Approve Proposed Requirements Modal */}
      <Modal
        isOpen={!!reviewBundle}
        onClose={() => !isApproving && setReviewBundle(null)}
        title="Review & Approve Extracted Criteria"
        maxWidth="lg"
      >
        {reviewBundle && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="flex items-center gap-1.5">
                Status:{' '}
                <strong
                  className={
                    reviewBundle.extraction_status === 'COMPLETED'
                      ? 'text-emerald-700'
                      : 'text-amber-700'
                  }
                >
                  {reviewBundle.extraction_status}
                </strong>
              </span>
              <span>Extracted Criteria: {reviewBundle.criteria.length}</span>
            </div>

            {reviewBundle.conflicts.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 space-y-1">
                <p className="font-bold flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4 text-amber-600" /> Detected Conflicts / Review Needed:
                </p>
                <ul className="list-disc list-inside text-amber-700">
                  {reviewBundle.conflicts.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="max-h-96 overflow-y-auto space-y-3">
              {reviewBundle.criteria.map((c, idx) => (
                <div key={idx} className="p-3 rounded-xl border border-slate-200 bg-white text-xs space-y-1.5">
                  <div className="flex items-center justify-between font-bold text-slate-800">
                    <span className="text-blue-700">{c.title}</span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-[11px] text-slate-600">
                      Page {c.page_number} ({c.source_filename})
                    </span>
                  </div>
                  <p className="italic text-slate-600 bg-slate-50 p-2 rounded text-[11px] font-mono">
                    &ldquo;{c.supporting_excerpt}&rdquo;
                  </p>
                  {c.review_notes && (
                    <p className="text-amber-700 font-medium text-[11px]">Note: {c.review_notes}</p>
                  )}
                </div>
              ))}
            </div>

            <div className="p-3 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-800">
              <p className="font-semibold">Deterministic Isolation Notice:</p>
              <p className="mt-0.5 text-[11px] text-purple-700">
                Approving these criteria writes them to authoritative structured requirements for deterministic rule engine evaluations. Rejected criteria are discarded and will not affect bidder compliance outcomes.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
              <Button
                variant="outline"
                disabled={isApproving}
                onClick={handleRejectCriteria}
                icon={<XCircle className="w-4 h-4 text-rose-600" />}
              >
                Reject Criteria
              </Button>
              <Button
                isLoading={isApproving}
                onClick={handleApproveCriteria}
                icon={<CheckCircle2 className="w-4 h-4 text-white" />}
              >
                Approve &amp; Make Authoritative
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
