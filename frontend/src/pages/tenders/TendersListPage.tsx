import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { tendersApi } from '../../api/tendersApi';
import { TenderResponse } from '../../types/tender';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { getErrorMessage } from '../../api/client';
import { formatTenderDate, formatTenderDeadline } from '../../utils/dateUtils';
import {
  Search,
  Building,
  Coins,
  ShieldCheck,
  FileCheck2,
  Clock,
  ExternalLink,
  RefreshCw,
  Globe2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  CheckCircle2,
  AlertTriangle,
  FileText,
  AlertCircle,
  Package,
  Calendar,
  Eye,
} from 'lucide-react';

interface GemCrawlMetadata {
  total_portal_records?: number;
  total_pages_available?: number;
  start_page?: number;
  end_page_crawled?: number;
  next_page?: number;
  pages_processed?: number;
  unique_bids_discovered?: number;
  unretrieved_pages?: number[];
  errors_encountered?: string[];
  crawl_completed?: boolean;
  is_partial?: boolean;
  last_retrieved_at?: string;
}

const getAllBidsPortalUrl = (sourcePortal?: string | null, fallbackUrl?: string | null) => {
  const p = (sourcePortal || '').toUpperCase();
  if (p === 'GEM') return 'https://bidplus.gem.gov.in/all-bids';
  if (p === 'CPPP') return 'https://eprocure.gov.in/eprocure/app';
  if (p === 'OPEN_GOV') return 'https://data.gov.in';
  if (p === 'TENDERKART') return 'https://tenderkart.in';
  return 'https://bidplus.gem.gov.in/all-bids';
};

export const TendersListPage: React.FC = () => {
  const navigate = useNavigate();
  const [tenders, setTenders] = useState<TenderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [downloadingTenderId, setDownloadingTenderId] = useState<string | null>(null);
const [downloadingLocalTenderId, setDownloadingLocalTenderId] = useState<string | null>(null);

  const handleViewOrDownloadLocalPdf = async (tender: TenderResponse) => {
    setDownloadingLocalTenderId(tender.id);
    setError(null);
    try {
      let currentTender = tender;
      let docs = currentTender.documents || [];
      if (docs.length === 0) {
        await tendersApi.fetchTenderDocuments(tender.id);
        currentTender = await tendersApi.getTender(tender.id);
        setTenders((prev) =>
          prev.map((t) => (t.id === tender.id ? currentTender : t))
        );
        docs = currentTender.documents || [];
      }

      if (docs.length > 0) {
        const doc = docs[0];
        await tendersApi.downloadDocument(currentTender.id, doc.id, doc.original_filename);
        const blobUrl = await tendersApi.viewDocumentBlob(currentTender.id, doc.id);
        window.open(blobUrl, '_blank');
      } else {
        setError(`No local PDF document could be retrieved for [${tender.tender_reference}].`);
      }
    } catch (err: unknown) {
      setError(`Failed to retrieve or view local PDF: ${getErrorMessage(err)}`);
    } finally {
      setDownloadingLocalTenderId(null);
    }
  };
  const [unindexedModalTender, setUnindexedModalTender] = useState<TenderResponse | null>(null);
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [selectedPortal, setSelectedPortal] = useState<string>('ALL');
  const [activeOnly, setActiveOnly] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [gemMetrics, setGemMetrics] = useState<GemCrawlMetadata | null>(null);
  const [gemLastRun, setGemLastRun] = useState<{
    tenders_ingested: number;
    tenders_updated: number;
    tenders_skipped: number;
  } | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const fetchTenders = async (
    targetPage = page,
    limitSize = pageSize,
    searchQuery = search,
    sectorFilter = sector,
    portalFilter = selectedPortal,
    onlyActive = activeOnly
  ) => {
    setLoading(true);
    setError(null);
    try {
      const data = await tendersApi.listTenders({
        page: targetPage,
        limit: limitSize,
        search: searchQuery || undefined,
        sector: sectorFilter || undefined,
        source_portal: portalFilter !== 'ALL' ? portalFilter : undefined,
        active_only: onlyActive,
      });
      setTenders(data.items);
      setTotal(data.total);
      if (data.page) {
        setPage(data.page);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchTenders(1, pageSize, search, sector, selectedPortal, activeOnly);
  }, [selectedPortal, activeOnly]);

  const handleToggleActiveOnly = (val: boolean) => {
    setActiveOnly(val);
    setPage(1);
    fetchTenders(1, pageSize, search, sector, selectedPortal, val);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTenders(1, pageSize, search, sector, selectedPortal, activeOnly);
  };

  const handleRefreshTenderList = async () => {
    setRefreshing(true);
    setError(null);
    setSuccessNotice(null);
    try {
      const portalParam = selectedPortal !== 'ALL' ? selectedPortal : undefined;
      const limitParam = selectedPortal === 'GEM' ? 50 : 20;
      const run = await tendersApi.refreshTenders({
        source_portal: portalParam,
        limit: limitParam,
      });

      if (run.source_portal === 'GEM' || (run.run_metadata && run.run_metadata.gem_crawl)) {
        if (run.run_metadata?.gem_crawl) {
          setGemMetrics(run.run_metadata.gem_crawl as GemCrawlMetadata);
          setGemLastRun({
            tenders_ingested: run.tenders_ingested,
            tenders_updated: run.tenders_updated,
            tenders_skipped: run.tenders_skipped,
          });
        }
      }

      if (run.source_portal === 'GEM' && run.run_metadata?.gem_crawl) {
        const crawl = run.run_metadata.gem_crawl as GemCrawlMetadata;
        const totalFmt = crawl.total_portal_records ? Number(crawl.total_portal_records).toLocaleString('en-IN') : 'dynamic';
        const pagesFmt = `Pages ${crawl.start_page}–${crawl.end_page_crawled}`;
        const crawlState = crawl.crawl_completed ? 'Completed' : 'Partial Batch';
        setSuccessNotice(
          `GeM Live Refresh [${crawlState}]: ${run.tenders_found} bids discovered across ${pagesFmt} (of ~${totalFmt} total live GeM bids). ${run.tenders_ingested} new ingested, ${run.tenders_updated} updated, ${run.tenders_skipped} skipped.`
        );
      } else {
        setSuccessNotice(
          `Live tender refresh completed (${run.source_portal}): ${run.tenders_found} discovered, ${run.tenders_ingested} new ingested, ${run.tenders_updated} updated in database.`
        );
      }
      setPage(1);
      await fetchTenders(1, pageSize, search, sector, selectedPortal, activeOnly);
    } catch (err: unknown) {
      setError(`Failed to sync live tender feeds: ${getErrorMessage(err)}`);
      await fetchTenders(page, pageSize, search, sector, selectedPortal, activeOnly);
    } finally {
      setRefreshing(false);
    }
  };

  const handleDownloadTenderPdf = async (tender: TenderResponse) => {
    setDownloadingTenderId(tender.id);
    setError(null);
    setSuccessNotice(null);
    try {
      const res = await tendersApi.fetchTenderDocuments(tender.id);
      const updatedTender = await tendersApi.getTender(tender.id);
      setTenders((prev) =>
        prev.map((t) => (t.id === tender.id ? updatedTender : t))
      );

      if (res.status === 'COMPLETED') {
        const indexedCount = (updatedTender.documents || []).filter(
          (d) => d.processing_status === 'INDEXED'
        ).length;
        setSuccessNotice(
          `Document retrieved & indexed for [${tender.tender_reference}]: ${indexedCount} document(s) verified and ready for compliance evaluation.`
        );
      } else if (res.status === 'HTML_PAGE_ONLY') {
        setError(
          `Notice for [${tender.tender_reference}]: ${res.message || 'Source is an official portal notice page. Direct PDF download is not available.'}`
        );
      } else {
        setError(
          `Document notice for [${tender.tender_reference}]: ${res.message || res.status}`
        );
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setDownloadingTenderId(null);
    }
  };

  const handleEvaluateCompliance = (tender: TenderResponse) => {
    const indexedDocs = (tender.documents || []).filter(
      (d) => d.processing_status === 'INDEXED'
    );
    if (indexedDocs.length === 0) {
      setUnindexedModalTender(tender);
    } else {
      navigate(`/compliance/analyze?tender_id=${tender.id}`);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return;
    setPage(newPage);
    fetchTenders(newPage, pageSize, search, sector, selectedPortal, activeOnly);
    if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
      try {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } catch {
        // Safe fallback for environments like jsdom without smooth scrolling support
      }
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1);
    fetchTenders(1, newSize, search, sector, selectedPortal, activeOnly);
  };

  const formatINR = (val?: number | null) => {
    if (!val) return '₹ Not Disclosed';
    return `₹ ${Number(val).toLocaleString('en-IN')}`;
  };

  const renderPortalBadge = (portal?: string | null) => {
    const p = (portal || 'MANUAL').toUpperCase();
    if (p === 'GEM') {
      return (
        <span
          data-testid="badge-gem"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          GeM Portal
        </span>
      );
    }
    if (p === 'CPPP') {
      return (
        <span
          data-testid="badge-cppp"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-800 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-200"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          CPPP e-Procure
        </span>
      );
    }
    if (p === 'OPEN_GOV') {
      return (
        <span
          data-testid="badge-opengov"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-800 bg-cyan-50 px-2.5 py-1 rounded-md border border-cyan-200"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
          Open Gov PSU
        </span>
      );
    }
    if (p === 'TENDERKART') {
      return (
        <span
          data-testid="badge-tenderkart"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-800 bg-purple-50 px-2.5 py-1 rounded-md border border-purple-200"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
          TenderKart Feed
        </span>
      );
    }
    if (p === 'APIFY') {
      return (
        <span
          data-testid="badge-apify"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          Apify CPPP Feed
        </span>
      );
    }
    return (
      <span
        data-testid="badge-manual"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200"
      >
        Direct Notice
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Sticky Compressed Header & Filter Controls Area */}
      <div className="sticky top-16 z-20 bg-slate-50/95 backdrop-blur-xs -mt-6 md:-mt-8 pt-4 md:pt-6 pb-2.5 space-y-2.5 border-b border-slate-200/80">
        {/* Header with Title and Auto-Ingestion Refresh */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 leading-tight">Tender Opportunities</h1>
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                <Globe2 className="w-3 h-3 text-blue-500" />
                Live Govt Feeds
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated government discovery across GeM, CPPP &amp; Open Procurement feeds with deterministic compliance
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshTenderList}
              disabled={loading || refreshing}
              icon={<RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />}
            >
              {refreshing ? 'Syncing...' : 'Refresh Tender List'}
            </Button>
          </div>
        </div>

        {successNotice && (
          <div className="py-2 px-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successNotice}</span>
            </div>
            <button
              onClick={() => setSuccessNotice(null)}
              className="text-emerald-600 hover:text-emerald-900 ml-2 font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {/* Official Procurement Source Filter Tabs & Active/Closed Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-0.5 text-xs">
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-thin">
            <span className="text-slate-400 font-medium whitespace-nowrap text-xs mr-1">Filter Source:</span>
            {[
              { id: 'ALL', label: 'All Sources' },
              { id: 'GEM', label: 'GeM Portal' },
              { id: 'CPPP', label: 'CPPP e-Procure' },
              { id: 'OPEN_GOV', label: 'Open Gov PSU' },
              { id: 'TENDERKART', label: 'TenderKart Feed' },
              { id: 'APIFY', label: 'Apify Actor Feed' },
              { id: 'MANUAL', label: 'Direct Notices' },
            ].map((tab) => {
              const isActive = selectedPortal === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setSelectedPortal(tab.id)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100/80'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Active / Ongoing vs Closed Toggle */}
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-0.5 shadow-2xs shrink-0">
            <button
              type="button"
              data-testid="toggle-ongoing-bids"
              onClick={() => handleToggleActiveOnly(true)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors flex items-center gap-1 cursor-pointer ${
                activeOnly
                  ? 'bg-emerald-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Show active ongoing tenders closing in the future"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${activeOnly ? 'bg-white animate-pulse' : 'bg-emerald-500'}`} />
              Ongoing Active Bids
            </button>
            <button
              type="button"
              data-testid="toggle-all-bids"
              onClick={() => handleToggleActiveOnly(false)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                !activeOnly
                  ? 'bg-slate-800 text-white shadow-2xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
              title="Include past closed tenders"
            >
              Include Closed
            </button>
          </div>
        </div>

        {/* GeM Live Crawl Transparency Panel */}
        {selectedPortal === 'GEM' && gemMetrics && (
          <div
            data-testid="gem-crawl-transparency-card"
            className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-3 text-xs text-slate-700 shadow-2xs space-y-2 max-h-48 overflow-y-auto"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-200/70 pb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-bold text-emerald-950 text-xs sm:text-sm">Official GeM Live Pagination &amp; Discovery Transparency</span>
                <span
                  data-testid="badge-crawl-status"
                  className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                    gemMetrics.crawl_completed
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : 'bg-amber-100 text-amber-900 border border-amber-300'
                  }`}
                >
                  {gemMetrics.crawl_completed ? 'Catalog Crawl Completed' : 'Bounded Batch (Partial Crawl)'}
                </span>
              </div>
              {gemMetrics.last_retrieved_at && (
                <span className="text-slate-500 text-[10px]">
                  Last GeM Refresh: {new Date(gemMetrics.last_retrieved_at).toLocaleString()}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">GeM Portal Total</div>
                <div className="font-bold text-slate-900 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-total">
                  {gemMetrics.total_portal_records ? gemMetrics.total_portal_records.toLocaleString('en-IN') : 'N/A'}
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">Pages Processed</div>
                <div className="font-bold text-slate-900 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-pages">
                  {gemMetrics.pages_processed || 0} (p.{gemMetrics.start_page}–{gemMetrics.end_page_crawled})
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">Live Bids Found</div>
                <div className="font-bold text-slate-900 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-discovered">
                  {gemMetrics.unique_bids_discovered || 0}
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">New Ingested</div>
                <div className="font-bold text-emerald-700 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-ingested">
                  {gemLastRun ? gemLastRun.tenders_ingested : 0}
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">Updated</div>
                <div className="font-bold text-blue-700 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-updated">
                  {gemLastRun ? gemLastRun.tenders_updated : 0}
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">Duplicates Skipped</div>
                <div className="font-bold text-slate-600 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-skipped">
                  {gemLastRun ? gemLastRun.tenders_skipped : 0}
                </div>
              </div>
              <div className="bg-white/90 p-2 rounded-lg border border-emerald-100">
                <div className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold">Unretrieved Pages</div>
                <div className="font-bold text-slate-700 text-xs sm:text-sm mt-0.5" data-testid="metric-gem-unretrieved">
                  {gemMetrics.unretrieved_pages && gemMetrics.unretrieved_pages.length > 0
                    ? gemMetrics.unretrieved_pages.join(', ')
                    : '0 (None)'}
                </div>
              </div>
            </div>

            {!gemMetrics.crawl_completed && (
              <div className="text-[10px] text-emerald-800 flex items-center justify-between">
                <span>
                  Crawl checkpoint cursor: next batch will resume from <strong>Page {gemMetrics.next_page}</strong>. Click <strong>Refresh Tender List</strong> to continue crawling subsequent pages.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Search & Filter Bar */}
        <form
          onSubmit={handleSearchSubmit}
          className="bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row gap-2 items-center"
        >
          <div className="flex-1 w-full">
            <Input
              placeholder="Search by tender reference, title, or authority..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="w-full sm:w-52">
            <Input
              placeholder="Filter by sector..."
              value={sector}
              onChange={(e) => setSector(e.target.value)}
            />
          </div>
          <Button type="submit" size="sm" icon={<Search className="w-3.5 h-3.5" />} className="w-full sm:w-auto h-9">
            Search
          </Button>
        </form>

        {/* Results Header */}
        <div className="flex items-center justify-between text-xs font-medium text-slate-500 pt-0.5">
          <div>
            Found <span className="font-bold text-slate-800">{total}</span> procurement tenders
          </div>
          <div className="text-[11px] text-slate-400">
            Auto-synchronized with official procurement portals
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Querying active tender notices..." />
      ) : tenders.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200">
          <EmptyState
            title="No tenders found"
            description="Try modifying your search keywords or switching procurement source filters."
            actionLabel="Reset Search & Filters"
            onAction={() => {
              setSearch('');
              setSector('');
              setSelectedPortal('ALL');
              setActiveOnly(true);
              setPage(1);
              fetchTenders(1, pageSize, '', '', 'ALL', true);
            }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {tenders.map((tender) => {
            const deadline = new Date(tender.submission_deadline);
            const isClosingSoon =
              deadline.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000 &&
              deadline.getTime() > Date.now();
            const indexedDocs = (tender.documents || []).filter((d) => d.processing_status === 'INDEXED');
            const isDownloading = downloadingTenderId === tender.id;
            const isHtmlPortal = tender.ingestion_metadata?.document_source_status === 'HTML_PORTAL_PAGE';
            const quantity = tender.ingestion_metadata?.gem_quantity;
            const pubDate = tender.publication_date ? new Date(tender.publication_date) : null;

            return (
              <div
                key={tender.id}
                data-testid={`tender-card-${tender.tender_reference}`}
                className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                        {tender.tender_reference}
                      </span>
                      {renderPortalBadge(tender.source_portal)}
                      {indexedDocs.length > 0 ? (
                        <span
                          data-testid={`badge-indexed-${tender.tender_reference}`}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200"
                        >
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Indexed & Ready ({indexedDocs.length} Doc · {indexedDocs[0].total_pages || 1}p · {indexedDocs[0].indexed_chunks || 1} chunks)
                        </span>
                      ) : isDownloading ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 animate-pulse">
                          <RefreshCw className="w-3 h-3 text-blue-600 animate-spin" />
                          Downloading & Indexing...
                        </span>
                      ) : isHtmlPortal ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          <AlertCircle className="w-3 h-3 text-amber-600" />
                          Portal Notice Only
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          <FileText className="w-3 h-3 text-slate-400" />
                          Not Downloaded
                        </span>
                      )}
                      {Boolean(tender.ingestion_metadata?.is_fixture) && (
                        <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                          Schema Fixture
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                      {tender.sector}
                    </span>
                  </div>

                  <h2 className="text-base font-bold text-slate-900 mt-2 line-clamp-2">
                    {tender.title}
                  </h2>

                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
                    <Building className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{tender.issuing_authority}</span>
                  </p>

                  <div className="mt-5 grid grid-cols-2 gap-3 pt-4 border-t border-slate-100 text-xs">
                    <div>
                      <p className="text-slate-400 flex items-center gap-1">
                        <Coins className="w-3.5 h-3.5" />
                        Estimated Budget
                      </p>
                      <p className="font-semibold text-slate-800 mt-0.5">
                        {formatINR(tender.estimated_budget_inr)}
                      </p>
                    </div>

                    <div>
                      <p className="text-slate-400 flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        EMD Amount
                      </p>
                      <p className="font-semibold text-slate-800 mt-0.5">
                        {tender.msme_emd_exemption ? (
                          <span className="text-emerald-700 font-medium">Exempt for MSMEs</span>
                        ) : (
                          formatINR(tender.emd_amount_inr)
                        )}
                      </p>
                    </div>

                    {Boolean(quantity) && (
                      <div>
                        <p className="text-slate-400 flex items-center gap-1">
                          <Package className="w-3.5 h-3.5" />
                          Quantity
                        </p>
                        <p className="font-semibold text-slate-800 mt-0.5">{String(quantity)}</p>
                      </div>
                    )}

                    {pubDate && (
                      <div>
                        <p className="text-slate-400 flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          Published
                        </p>
                        <p className="font-semibold text-slate-800 mt-0.5">
                          {formatTenderDate(tender.publication_date)}
                        </p>
                      </div>
                    )}

                    <div className="col-span-2 flex items-center justify-between text-slate-600 mt-1 pt-1">
                      <div className="flex items-center gap-1.5">
                        <Clock
                          className={`w-3.5 h-3.5 ${
                            isClosingSoon ? 'text-amber-500 font-bold' : 'text-slate-400'
                          }`}
                        />
                        <span>
                          Deadline: {formatTenderDeadline(tender.submission_deadline)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          data-testid={`btn-local-pdf-${tender.tender_reference}`}
                          disabled={downloadingLocalTenderId === tender.id}
                          onClick={() => handleViewOrDownloadLocalPdf(tender)}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded transition-colors disabled:opacity-50 cursor-pointer"
                          title="Download and view this tender's PDF locally"
                        >
                          <FileText className={`w-3 h-3 text-emerald-600 ${downloadingLocalTenderId === tender.id ? 'animate-spin' : ''}`} />
                          <span>{downloadingLocalTenderId === tender.id ? 'Opening...' : 'View / Download PDF'}</span>
                        </button>

                        <a
                          href={getAllBidsPortalUrl(tender.source_portal, tender.official_portal_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          data-testid={`link-portal-notice-${tender.tender_reference}`}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-800 hover:underline"
                          title="Open official website of all bids (https://bidplus.gem.gov.in/all-bids)"
                        >
                          <span>Portal Notice</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                      {Boolean(tender.ingestion_metadata?.tenderkart_url) && (
                        <a
                          href={String(tender.ingestion_metadata?.tenderkart_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-purple-600 hover:text-purple-800 hover:underline"
                        >
                          <span>TenderKart Notice</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                  <Link to={`/tenders/${tender.id}`}>
                    <Button variant="outline" size="sm">
                      Notice Details
                    </Button>
                  </Link>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={isDownloading}
                      isLoading={isDownloading}
                      onClick={() => handleDownloadTenderPdf(tender)}
                      icon={<Download className="w-3.5 h-3.5" />}
                    >
                      {indexedDocs.length > 0 ? 'Re-download this Tender PDF for Indexing & Evaluating Compliance' : 'Download this Tender PDF for the Indexing for the Evaluating Compliance'}
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleEvaluateCompliance(tender)}
                      icon={<FileCheck2 className="w-4 h-4" />}
                    >
                      Evaluate Compliance
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Guard Modal: When tender has 0 usable documents indexed */}
      {unindexedModalTender && (
        <div
          data-testid="unindexed-document-guard-modal"
          className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4"
        >
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-amber-100 text-amber-700 shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Document Required for Compliance Evaluation
                </h3>
                <p className="text-xs font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded mt-1 inline-block">
                  {unindexedModalTender.tender_reference}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium leading-relaxed">
              Compliance evaluation cannot be completed because no usable tender document has been downloaded and indexed for this bid. Retry document retrieval, open the official source, or upload the tender file manually.
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setUnindexedModalTender(null)}
              >
                Cancel
              </Button>
              {unindexedModalTender.official_portal_url && (
                <a
                  href={unindexedModalTender.official_portal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline" size="sm" icon={<ExternalLink className="w-3.5 h-3.5" />}>
                    Open Official Source
                  </Button>
                </a>
              )}
              <Button
                size="sm"
                isLoading={downloadingTenderId === unindexedModalTender.id}
                disabled={downloadingTenderId === unindexedModalTender.id}
                onClick={async () => {
                  const target = unindexedModalTender;
                  await handleDownloadTenderPdf(target);
                  setUnindexedModalTender(null);
                }}
                icon={<Download className="w-3.5 h-3.5" />}
              >
                Download Tender PDF Now
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Responsive Pagination Controls */}
      {!loading && total > 0 && (
        <div
          data-testid="pagination-controls"
          className="bg-white px-5 py-3.5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
            <span>
              Showing <strong className="font-semibold text-slate-800">{Math.min((page - 1) * pageSize + 1, total)}</strong> to{' '}
              <strong className="font-semibold text-slate-800">{Math.min(page * pageSize, total)}</strong> of{' '}
              <strong className="font-semibold text-slate-800">{total}</strong> tenders
            </span>
            <div className="flex items-center gap-1.5 border-l border-slate-200 pl-3">
              <span className="text-slate-500">Per page:</span>
              <select
                data-testid="select-page-size"
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-md px-2 py-1 focus:outline-hidden focus:ring-1 focus:ring-blue-500 font-medium cursor-pointer"
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              data-testid="btn-first-page"
              onClick={() => handlePageChange(1)}
              disabled={page <= 1}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="First Page"
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>
            <button
              data-testid="btn-prev-page"
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <span data-testid="page-indicator" className="text-xs font-semibold text-slate-700 px-3 py-1 bg-slate-50 rounded-md border border-slate-200">
              Page {page} of {totalPages}
            </span>

            <button
              data-testid="btn-next-page"
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              data-testid="btn-last-page"
              onClick={() => handlePageChange(totalPages)}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Last Page"
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
