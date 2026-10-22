import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { tendersApi } from '../../api/tendersApi';
import { applicationsApi } from '../../api/applicationsApi';
import { TenderResponse, TenderExtractedKnowledgeResponse } from '../../types/tender';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { TenderQAPanel } from '../../components/tenders/TenderQAPanel';
import { getErrorMessage } from '../../api/client';
import {
  FileText,
  Download,
  Building,
  Calendar,
  Coins,
  ShieldCheck,
  FileCheck2,
  ExternalLink,
  ArrowLeft,
  CheckCircle2,
  FileSpreadsheet,
  BookmarkPlus,
  Check,
  Eye,
  RefreshCw,
  AlertTriangle,
  Info,
  X,
  Globe,
  Sparkles,
  Database,
  Layers,
} from 'lucide-react';

export const TenderDetailPage: React.FC = () => {
  const { tenderId } = useParams<{ tenderId: string }>();
  const [tender, setTender] = useState<TenderResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trackSuccess, setTrackSuccess] = useState<string | null>(null);
  const [isTracking, setIsTracking] = useState(false);
  const [isFetchingDocs, setIsFetchingDocs] = useState(false);
  const [fetchFeedback, setFetchFeedback] = useState<{
    type: 'success' | 'info' | 'warning' | 'error';
    text: string;
  } | null>(null);
  const [viewingDoc, setViewingDoc] = useState<{ id: string; filename: string } | null>(null);
  const [viewingBlobUrl, setViewingBlobUrl] = useState<string | null>(null);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [extractedKnowledge, setExtractedKnowledge] = useState<TenderExtractedKnowledgeResponse | null>(null);
  const [isLoadingKnowledge, setIsLoadingKnowledge] = useState(false);
  const [showKnowledgeChunks, setShowKnowledgeChunks] = useState(false);

  const fetchKnowledge = async (id: string) => {
    setIsLoadingKnowledge(true);
    try {
      const data = await tendersApi.getExtractedKnowledge(id);
      setExtractedKnowledge(data);
    } catch {
      // Non-blocking
    } finally {
      setIsLoadingKnowledge(false);
    }
  };

  useEffect(() => {
    async function fetchTender() {
      if (!tenderId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await tendersApi.getTender(tenderId);
        setTender(data);
        fetchKnowledge(tenderId);
      } catch (err: unknown) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    fetchTender();
  }, [tenderId]);

  useEffect(() => {
    return () => {
      if (viewingBlobUrl) {
        window.URL.revokeObjectURL(viewingBlobUrl);
      }
    };
  }, [viewingBlobUrl]);

  const handleDownload = async (docId: string, filename: string) => {
    if (!tenderId) return;
    setDownloadingId(docId);
    try {
      await tendersApi.downloadDocument(tenderId, docId, filename);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setDownloadingId(null);
    }
  };

  const handleFetchDocuments = async () => {
    if (!tender) return;
    setIsFetchingDocs(true);
    setFetchFeedback(null);
    try {
      const res = await tendersApi.fetchTenderDocuments(tender.id);
      // Refresh tender record to reflect any newly ingested/indexed attachments
      const updated = await tendersApi.getTender(tender.id);
      setTender(updated);
      fetchKnowledge(tender.id);

      if (res.status === 'COMPLETED' && res.documents_retrieved > 0) {
        setFetchFeedback({
          type: 'success',
          text: res.message || `Successfully retrieved and indexed ${res.documents_retrieved} document(s). Ready for compliance analysis!`,
        });
      } else if (res.status === 'HTML_PAGE_ONLY' || res.url_classification === 'HTML_PORTAL_PAGE') {
        setFetchFeedback({
          type: 'info',
          text: res.message || 'The tender source provides an interactive official web portal page rather than a downloadable PDF file.',
        });
      } else if (res.status === 'RESTRICTED' || res.url_classification === 'RESTRICTED_ACCESS') {
        setFetchFeedback({
          type: 'warning',
          text: res.message || 'Direct access is restricted by portal access controls or authentication. Please use the official tender page link.',
        });
      } else if (res.status === 'NO_DOCUMENTS_FOUND') {
        setFetchFeedback({
          type: 'info',
          text: res.message || 'No document attachments or direct download URLs are published for this notice.',
        });
      } else {
        setFetchFeedback({
          type: 'info',
          text: res.message || 'Document retrieval completed.',
        });
      }
    } catch (err: unknown) {
      setFetchFeedback({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setIsFetchingDocs(false);
    }
  };

  const handleOpenPdfViewer = async (docId: string, filename: string) => {
    if (!tender) return;
    setViewingDoc({ id: docId, filename });
    setIsLoadingPdf(true);
    setPdfError(null);
    try {
      const blobUrl = await tendersApi.viewDocumentBlob(tender.id, docId);
      setViewingBlobUrl(blobUrl);
    } catch (err: unknown) {
      setPdfError(getErrorMessage(err));
    } finally {
      setIsLoadingPdf(false);
    }
  };

  const handleClosePdfViewer = () => {
    if (viewingBlobUrl) {
      window.URL.revokeObjectURL(viewingBlobUrl);
    }
    setViewingBlobUrl(null);
    setViewingDoc(null);
    setPdfError(null);
  };

  const handleTrack = async () => {
    if (!tender) return;
    setIsTracking(true);
    setError(null);
    try {
      await applicationsApi.createApplication({ tender_id: tender.id });
      setTrackSuccess('Tracked in your internal preparation pipeline!');
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to track application (may already be tracked).');
    } finally {
      setIsTracking(false);
    }
  };

  const formatINR = (val?: number | null) => {
    if (!val) return 'Not Disclosed';
    return `₹ ${Number(val).toLocaleString('en-IN')}`;
  };

  if (loading) {
    return <LoadingSpinner message="Loading tender notice details..." />;
  }

  if (!tender) {
    return (
      <div className="space-y-4">
        <Link to="/tenders" className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Tenders
        </Link>
        <ErrorAlert message={error || 'Tender notice not found.'} />
      </div>
    );
  }

  return (
    <div className="space-y-6 w-full">
      {/* Back button & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/tenders"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Tender List
        </Link>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="md"
            icon={trackSuccess ? <Check className="w-4 h-4 text-emerald-600" /> : <BookmarkPlus className="w-4 h-4 text-blue-600" />}
            onClick={handleTrack}
            disabled={isTracking || !!trackSuccess}
          >
            {trackSuccess ? 'Tracked in Pipeline' : isTracking ? 'Tracking...' : 'Track in Pipeline'}
          </Button>

          <Link to={`/compliance/analyze?tender_id=${tender.id}`}>
            <Button size="md" icon={<FileCheck2 className="w-4 h-4" />}>
              Evaluate My Compliance
            </Button>
          </Link>
        </div>
      </div>

      {trackSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {trackSuccess}
          </span>
          <Link to="/applications" className="font-semibold underline hover:text-emerald-900">
            View Bid Pipeline &rarr;
          </Link>
        </div>
      )}

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Main Notice Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-3 py-1 rounded-md border border-blue-200">
            {tender.tender_reference}
          </span>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
            {tender.sector}
          </span>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            Status: {tender.processing_status}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-slate-900">{tender.title}</h1>

        <p className="text-sm text-slate-600 flex items-center gap-2">
          <Building className="w-4 h-4 text-slate-400" />
          <span>Issuing Authority: <strong className="text-slate-800">{tender.issuing_authority}</strong></span>
        </p>

        {tender.official_portal_url && (
          <a
            href={tender.official_portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline font-medium"
          >
            <span>Official Portal Link</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}

        {/* Commercial & Timing Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-slate-100 text-sm">
          <div className="p-3 rounded-xl bg-slate-50">
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <Coins className="w-3.5 h-3.5" /> Estimated Value
            </p>
            <p className="font-bold text-slate-900 mt-0.5">{formatINR(tender.estimated_budget_inr)}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-50">
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> EMD Requirement
            </p>
            <p className="font-bold text-slate-900 mt-0.5">
              {tender.msme_emd_exemption ? (
                <span className="text-emerald-700">MSME Exempt</span>
              ) : (
                formatINR(tender.emd_amount_inr)
              )}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-50">
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Published Date
            </p>
            <p className="font-bold text-slate-900 mt-0.5">
              {tender.publication_date
                ? new Date(tender.publication_date).toLocaleDateString()
                : 'Not specified'}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-50">
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Closing Deadline
            </p>
            <p className="font-bold text-slate-900 mt-0.5">
              {new Date(tender.submission_deadline).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Grounded Tender Q&A (Phase 9) */}
      <TenderQAPanel tenderId={tender.id} tenderTitle={tender.title} />

      {/* Extracted Document Knowledge in Backend (AI Knowledge Base) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-slate-900">
                  Extracted Document Knowledge in Backend
                </h2>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
                  AI Context Verified
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                The authoritative text and vector chunks extracted from downloaded tender PDFs that the AI reads to answer questions.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={isLoadingKnowledge}
              icon={<RefreshCw className={`w-3.5 h-3.5 ${isLoadingKnowledge ? 'animate-spin text-blue-600' : ''}`} />}
              onClick={() => fetchKnowledge(tender.id)}
            >
              {isLoadingKnowledge ? 'Refreshing...' : 'Refresh Extracted Knowledge'}
            </Button>
            {extractedKnowledge && extractedKnowledge.chunks.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                icon={<Layers className="w-3.5 h-3.5 text-indigo-600" />}
                onClick={() => setShowKnowledgeChunks(!showKnowledgeChunks)}
              >
                {showKnowledgeChunks ? 'Hide Extracted Text' : `View Extracted Text (${extractedKnowledge.chunks.length} chunks)`}
              </Button>
            )}
          </div>
        </div>

        {extractedKnowledge && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-slate-400 font-medium">Authoritative Documents</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{extractedKnowledge.total_documents} File(s)</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-slate-400 font-medium">Total Vector Chunks</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">{extractedKnowledge.total_chunks} Chunks Indexed</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-slate-400 font-medium">Extraction Pipeline</span>
              <p className="text-base font-bold text-emerald-700 mt-0.5 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                PyMuPDF Direct + OCR Verified
              </p>
            </div>
          </div>
        )}

        {/* Expandable Extracted Chunks Viewer */}
        {showKnowledgeChunks && extractedKnowledge && extractedKnowledge.chunks.length > 0 && (
          <div className="mt-4 border border-slate-200 rounded-xl overflow-hidden bg-slate-50">
            <div className="px-4 py-2.5 bg-slate-100 border-b border-slate-200 flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Authoritative Document Text Seen by AI ({extractedKnowledge.chunks.length} Chunks)</span>
              <span className="text-[11px] text-slate-500 font-mono">Page Scoped • RRF Ranked</span>
            </div>
            <div className="max-h-96 overflow-y-auto p-4 space-y-3">
              {extractedKnowledge.chunks.map((c, idx) => (
                <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200 text-xs shadow-2xs">
                  <div className="flex items-center justify-between text-slate-500 mb-1.5 pb-1 border-b border-slate-100 font-medium">
                    <span className="text-blue-700 font-semibold flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" />
                      {c.source_filename}
                    </span>
                    <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-mono text-[11px]">
                      Page {c.page_number} • Chunk #{c.chunk_index}
                    </span>
                  </div>
                  <p className="text-slate-800 leading-relaxed font-sans whitespace-pre-wrap text-[12px]">
                    {c.chunk_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Structured Requirements Breakdown */}
      {tender.structured_requirements && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            Deterministic Eligibility Criteria Extracted from RFP
          </h2>
          <p className="text-xs text-slate-500">
            These objective parameters are verified by the Python deterministic rule engine against your company records.
          </p>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 font-mono text-xs overflow-x-auto text-slate-800">
            <pre>{JSON.stringify(tender.structured_requirements, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* Attached Documents */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Official Tender Documents & RFP Specifications ({tender.documents.length})
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Verified tender notices, technical schedules, and RFPs stored securely in vault storage.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            disabled={isFetchingDocs}
            icon={<RefreshCw className={`w-4 h-4 ${isFetchingDocs ? 'animate-spin text-blue-600' : ''}`} />}
            onClick={handleFetchDocuments}
          >
            {isFetchingDocs ? 'Fetching Documents...' : 'Fetch Tender Documents'}
          </Button>
        </div>

        {/* Retrieval Feedback Notice */}
        {fetchFeedback && (
          <div
            className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 ${
              fetchFeedback.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : fetchFeedback.type === 'warning'
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : fetchFeedback.type === 'error'
                ? 'bg-rose-50 border-rose-200 text-rose-900'
                : 'bg-blue-50 border-blue-200 text-blue-900'
            }`}
          >
            <div className="flex items-start gap-2">
              {fetchFeedback.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
              {fetchFeedback.type === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />}
              {fetchFeedback.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />}
              {fetchFeedback.type === 'info' && <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />}
              <span>{fetchFeedback.text}</span>
            </div>
            <button
              onClick={() => setFetchFeedback(null)}
              className="text-slate-400 hover:text-slate-600 p-0.5"
              title="Dismiss notice"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {tender.documents.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-50 border border-slate-200 text-center space-y-3">
            <p className="text-xs text-slate-500">
              No direct PDF files are currently stored for this tender record.
            </p>
            {tender.official_portal_url ? (
              <div className="space-y-2">
                <p className="text-xs text-slate-400">
                  The issuing authority published this tender notice on an official procurement web portal:
                </p>
                <a
                  href={tender.official_portal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block"
                >
                  <Button variant="outline" size="sm" icon={<ExternalLink className="w-4 h-4 text-blue-600" />}>
                    Open Official Tender Page
                  </Button>
                </a>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No official document URL has been published yet.</p>
            )}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {tender.documents.map((doc) => {
              const isIndexed = doc.processing_status === 'INDEXED';
              const isFailed = doc.processing_status === 'FAILED';
              const isExtracting = doc.processing_status === 'EXTRACTING' || doc.processing_status === 'PENDING';

              return (
                <div key={doc.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-600 shrink-0 mt-0.5">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-slate-800 break-all">{doc.original_filename}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="font-medium text-slate-500">
                          {doc.document_category}
                        </span>
                        <span className="text-slate-300">•</span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono text-[11px]">
                          PDF Document
                        </span>
                        <span className="text-slate-300">•</span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium text-[11px] flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3" /> Stored in Vault
                        </span>
                        <span className="text-slate-300">•</span>
                        {isIndexed && (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium text-[11px]">
                            Indexed & Ready ({doc.total_pages || 0} pages, {doc.indexed_chunks} chunks)
                          </span>
                        )}
                        {isExtracting && (
                          <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium text-[11px]">
                            Processing...
                          </span>
                        )}
                        {isFailed && (
                          <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-medium text-[11px]">
                            Processing Failed
                          </span>
                        )}
                      </div>
                      {doc.error_message && (
                        <p className="text-xs text-rose-600 mt-1">{doc.error_message}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Eye className="w-4 h-4" />}
                      onClick={() => handleOpenPdfViewer(doc.id, doc.original_filename)}
                      disabled={isFailed}
                    >
                      View PDF
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={downloadingId === doc.id}
                      icon={<Download className="w-4 h-4" />}
                      onClick={() => handleDownload(doc.id, doc.original_filename)}
                    >
                      Download PDF
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Fallback Official Portal Link (when docs exist as well) */}
        {tender.documents.length > 0 && tender.official_portal_url && (
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-slate-400" />
              Official Portal Source Notice
            </span>
            <a
              href={tender.official_portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline font-medium inline-flex items-center gap-1"
            >
              Open Official Tender Page <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>

      {/* In-App Authenticated Embedded PDF Viewer Modal */}
      {viewingDoc && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/70 backdrop-blur-xs animate-in fade-in duration-150"
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl flex flex-col h-[88vh] overflow-hidden border border-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50/80">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-1.5 rounded-lg bg-blue-100 text-blue-700 shrink-0">
                  <FileText className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 truncate">
                    {viewingDoc.filename}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Secure In-App PDF Viewer • Verified Vault Storage
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  icon={<Download className="w-3.5 h-3.5" />}
                  onClick={() => handleDownload(viewingDoc.id, viewingDoc.filename)}
                >
                  Download
                </Button>
                <button
                  onClick={handleClosePdfViewer}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                  title="Close PDF viewer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="flex-1 bg-slate-100 p-2 sm:p-4 overflow-hidden flex flex-col justify-center">
              {isLoadingPdf && (
                <div className="py-12">
                  <LoadingSpinner message="Streaming verified PDF document from secure vault..." />
                </div>
              )}

              {pdfError && (
                <div className="p-6">
                  <ErrorAlert message={pdfError} />
                </div>
              )}

              {viewingBlobUrl && !isLoadingPdf && (
                <iframe
                  src={viewingBlobUrl}
                  className="w-full h-full rounded-xl border border-slate-300 shadow-inner bg-white"
                  title={viewingDoc.filename}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
