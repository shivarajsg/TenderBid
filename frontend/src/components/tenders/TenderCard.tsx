import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { TenderResponse } from '../../types/tender';
import { Button } from '../common/Button';
import { getTenderCategoryKey, getCategoryDisplayName, getTenderImageUrl } from '../../utils/tenderImage';
import {
  FileText,
  Download,
  Building,
  Calendar,
  Coins,
  ShieldCheck,
  Package,
  Clock,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  FileCheck2,
} from 'lucide-react';

interface TenderCardProps {
  tender: TenderResponse;
  isDownloading: boolean;
  isDownloadingLocal: boolean;
  onDownloadPdf: (tender: TenderResponse) => void;
  onViewOrDownloadLocalPdf: (tender: TenderResponse) => void;
  onEvaluateCompliance: (tender: TenderResponse) => void;
  getAllBidsPortalUrl: (sourcePortal?: string | null, fallbackUrl?: string | null) => string;
}

export const TenderCard: React.FC<TenderCardProps> = ({
  tender,
  isDownloading,
  isDownloadingLocal,
  onDownloadPdf,
  onViewOrDownloadLocalPdf,
  onEvaluateCompliance,
  getAllBidsPortalUrl,
}) => {
  const [imgError, setImgError] = useState(false);
  const deadline = new Date(tender.submission_deadline);
  const isClosingSoon =
    deadline.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000 &&
    deadline.getTime() > Date.now();
  const indexedDocs = (tender.documents || []).filter((d) => d.processing_status === 'INDEXED');
  const isHtmlPortal = tender.ingestion_metadata?.document_source_status === 'HTML_PORTAL_PAGE';
  const quantity = tender.ingestion_metadata?.gem_quantity || '1';
  const pubDate = tender.publication_date ? new Date(tender.publication_date) : null;

  const categoryKey = getTenderCategoryKey(tender.title, tender.sector);
  const categoryTitle = getCategoryDisplayName(categoryKey);
  const imageUrl = imgError
    ? '/images/tender-categories/general-procurement.svg'
    : getTenderImageUrl(tender.title, tender.sector);

  const formatINR = (val?: number | null) => {
    if (val === null || val === undefined || val === 0) return '₹ Not Disclosed';
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
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
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
          <span className="w-2 h-2 rounded-full bg-indigo-500" />
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
          <span className="w-2 h-2 rounded-full bg-cyan-500" />
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
          <span className="w-2 h-2 rounded-full bg-purple-500" />
          TenderKart Direct
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
        Manual Entry
      </span>
    );
  };

  return (
    <div
      data-testid={`tender-card-${tender.tender_reference}`}
      className="bg-white rounded-3xl border border-slate-200/90 p-6 sm:p-7 shadow-xs hover:shadow-xl transition-all duration-300 flex flex-col justify-between group"
    >
      <div>
        {/* Top Badges Row */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            {/* Tender Reference Badge */}
            <span className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-slate-800 bg-slate-100/90 px-3 py-1 rounded-lg border border-slate-200">
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <span>{tender.tender_reference}</span>
            </span>

            {/* Source Portal Badge */}
            {renderPortalBadge(tender.source_portal)}

            {/* Document Processing State Badge */}
            {indexedDocs.length > 0 ? (
              <span
                data-testid={`badge-indexed-${tender.tender_reference}`}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Indexed & Ready ({indexedDocs.length} Doc · {indexedDocs[0].total_pages || 1}p · {indexedDocs[0].indexed_chunks || 1} chunks)</span>
              </span>
            ) : isDownloading ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-800 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200 animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                <span>Downloading & Indexing...</span>
              </span>
            ) : isHtmlPortal ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-800 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>Portal Notice Only</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 bg-slate-100/80 px-2.5 py-1 rounded-lg border border-slate-200">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Not Downloaded</span>
              </span>
            )}
          </div>
        </div>

        {/* Category / Sector Pill */}
        <div className="mt-2.5">
          <span className="inline-block text-[11px] font-medium text-slate-600 bg-slate-100/90 border border-slate-200/80 px-3 py-0.5 rounded-full">
            {categoryTitle}
          </span>
        </div>

        {/* Tender Title */}
        <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug mt-3 line-clamp-2 uppercase">
          {tender.title}
        </h2>

        {/* Procuring Ministry / Authority */}
        <p className="text-xs sm:text-sm font-medium text-slate-500 flex items-center gap-2 mt-1.5">
          <Building className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="truncate">{tender.issuing_authority}</span>
        </p>

        {/* Main Body: Info Grid + Large Relevant Tender Image */}
        <div className="mt-6 flex flex-col md:flex-row items-stretch gap-6">
          {/* Left: Information Grid */}
          <div className="flex-1 grid grid-cols-2 gap-y-4 gap-x-6 text-xs sm:text-sm">
            {/* Estimated Budget */}
            <div>
              <p className="text-slate-400 font-medium flex items-center gap-1.5 text-xs">
                <Coins className="w-3.5 h-3.5" />
                <span>Estimated Budget</span>
              </p>
              <p className="font-bold text-slate-900 mt-1 text-sm sm:text-base">
                {formatINR(tender.estimated_budget_inr)}
              </p>
            </div>

            {/* EMD Amount */}
            <div>
              <p className="text-slate-400 font-medium flex items-center gap-1.5 text-xs">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>EMD Amount</span>
              </p>
              <p className="font-bold mt-1 text-sm sm:text-base">
                {tender.msme_emd_exemption ? (
                  <span className="text-emerald-700 font-semibold">Exempt for MSMEs</span>
                ) : (
                  formatINR(tender.emd_amount_inr)
                )}
              </p>
            </div>

            {/* Quantity */}
            <div>
              <p className="text-slate-400 font-medium flex items-center gap-1.5 text-xs">
                <Package className="w-3.5 h-3.5" />
                <span>Quantity</span>
              </p>
              <p className="font-bold text-slate-900 mt-1">
                {String(quantity)}
              </p>
            </div>

            {/* Published Date */}
            <div>
              <p className="text-slate-400 font-medium flex items-center gap-1.5 text-xs">
                <Calendar className="w-3.5 h-3.5" />
                <span>Published</span>
              </p>
              <p className="font-bold text-slate-900 mt-1">
                {pubDate ? pubDate.toLocaleDateString() : 'Not Disclosed'}
              </p>
            </div>

            {/* Submission Deadline (spanning columns) */}
            <div className="col-span-2 pt-2 border-t border-slate-100">
              <p className="text-slate-400 font-medium flex items-center gap-1.5 text-xs">
                <Clock className={`w-3.5 h-3.5 ${isClosingSoon ? 'text-amber-500 font-bold' : 'text-slate-400'}`} />
                <span>Submission Deadline</span>
              </p>
              <p className="font-bold text-slate-900 mt-1 text-sm sm:text-base flex items-center gap-2">
                <span>
                  {deadline.toLocaleDateString()} at{' '}
                  {deadline.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {isClosingSoon && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                    Closing Soon
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Right: Large Relevant Tender Image with Rounded Corners & Subtle Hover Animation */}
          <div className="w-full md:w-[320px] lg:w-[360px] h-[220px] md:h-[240px] relative rounded-2xl md:rounded-3xl overflow-hidden shrink-0 border border-slate-200/80 bg-slate-950 shadow-2xs group">
            <img
              src={imageUrl}
              alt={tender.title}
              onError={() => setImgError(true)}
              loading="lazy"
              className="w-full h-full object-cover transition-transform duration-300 ease-out group-hover:scale-105 motion-reduce:transform-none filter grayscale contrast-[1.05]"
            />
            {/* Subtle Gradient & Badge Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none" />
            <div className="absolute top-3 left-3">
              <span className="text-[10px] font-mono font-semibold text-slate-200 bg-slate-900/80 backdrop-blur-xs px-2.5 py-1 rounded-md border border-slate-700/60 uppercase">
                {categoryKey.replace('-', ' ')}
              </span>
            </div>
          </div>
        </div>

        {/* Source Information Bar */}
        <div className="bg-slate-50 border border-slate-200/70 rounded-xl p-3 sm:px-4 sm:py-3 flex flex-wrap items-center justify-between gap-3 text-xs mt-6">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-slate-200/80 text-slate-700">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Tender Source</span>
              <span className="font-semibold text-slate-800">
                {tender.source_portal === 'GEM' ? 'GeM Portal (Bid Plus)' : tender.source_portal || 'Government Portal'}
              </span>
            </div>
            {/* Side-by-side local PDF view/download button */}
            <button
              type="button"
              data-testid={`btn-local-pdf-${tender.tender_reference}`}
              disabled={isDownloadingLocal}
              onClick={() => onViewOrDownloadLocalPdf(tender)}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50 cursor-pointer ml-1"
              title="Download and view this tender's PDF locally"
            >
              <FileText className={`w-3 h-3 text-emerald-600 ${isDownloadingLocal ? 'animate-spin' : ''}`} />
              <span>{isDownloadingLocal ? 'Opening...' : 'View / Download PDF'}</span>
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-slate-200/80 text-slate-700">
              <ExternalLink className="w-4 h-4" />
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Official Portal Link</span>
              <a
                href={getAllBidsPortalUrl(tender.source_portal, tender.official_portal_url)}
                target="_blank"
                rel="noopener noreferrer"
                data-testid={`link-portal-notice-${tender.tender_reference}`}
                className="font-semibold text-slate-900 hover:text-blue-600 hover:underline inline-flex items-center gap-1"
                title="Open official website of all bids (https://bidplus.gem.gov.in/all-bids)"
              >
                <span>Portal Notice</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Action Buttons */}
      <div className="mt-6 pt-5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
        {/* Left: View Notice Details */}
        <Link to={`/tenders/${tender.id}`}>
          <Button variant="outline" size="sm" icon={<FileText className="w-3.5 h-3.5" />} className="rounded-xl px-4 py-2 font-semibold">
            View Notice Details
          </Button>
        </Link>

        {/* Center: Premium Solid Black Download & Index Tender PDF Button */}
        <div className="flex flex-col items-center">
          <button
            type="button"
            disabled={isDownloading}
            onClick={() => onDownloadPdf(tender)}
            className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-black hover:bg-neutral-800 text-white shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
          >
            {isDownloading ? (
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Download className="w-4 h-4 text-white" />
            )}
            <span>
              {indexedDocs.length > 0
                ? 'Re-download this Tender PDF for Indexing & Evaluating Compliance'
                : 'Download this Tender PDF for the Indexing for the Evaluating Compliance'}
            </span>
          </button>
          <span className="text-[10px] text-slate-400 font-medium text-center mt-1">
            Download & Index Tender PDF
          </span>
        </div>

        {/* Right: Evaluate Compliance */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onEvaluateCompliance(tender)}
          icon={<FileCheck2 className="w-3.5 h-3.5 text-slate-700" />}
          className="rounded-xl px-4 py-2 font-semibold"
        >
          Evaluate Compliance
        </Button>
      </div>
    </div>
  );
};
