import React, { useState } from 'react';
import { tendersApi } from '../../api/tendersApi';
import { TenderQAResponse } from '../../types/tender';
import { Button } from '../common/Button';
import {
  MessageSquare,
  Send,
  Loader2,
  FileText,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
} from 'lucide-react';

interface TenderQAPanelProps {
  tenderId: string;
  tenderTitle: string;
}

export const TenderQAPanel: React.FC<TenderQAPanelProps> = ({ tenderId, tenderTitle }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qaResult, setQaResult] = useState<TenderQAResponse | null>(null);
  const [expandedCitations, setExpandedCitations] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await tendersApi.askTenderQuestion(tenderId, question.trim());
      setQaResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to retrieve answer from tender documents.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
      {/* Header Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left hover:bg-slate-100/70 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-800">Contextual Tender Q&A</h3>
            <p className="text-xs text-slate-500">
              Ask questions grounded strictly in the uploaded tender notices and RFP documents.
            </p>
          </div>
        </div>
        <div className="text-slate-400">
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-6">
          {/* Ask Form */}
          <form onSubmit={handleSubmit} className="mb-6">
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g. What is the required turnover, warranty, or EMD exemption policy?"
                disabled={isLoading}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-slate-800 placeholder-slate-400"
              />
              <Button
                type="submit"
                disabled={isLoading || !question.trim()}
                icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                className="shrink-0"
              >
                {isLoading ? 'Searching...' : 'Ask Question'}
              </Button>
            </div>
          </form>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-3 mb-4">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-600 mt-0.5" />
              <div>
                <p className="font-semibold">Query Failed</p>
                <p className="text-xs text-red-600 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* QA Result */}
          {qaResult && (
            <div className="space-y-4">
              <div
                className={`p-5 rounded-2xl border ${
                  qaResult.status === 'ANSWERED'
                    ? 'bg-blue-50/50 border-blue-200'
                    : 'bg-amber-50/50 border-amber-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {qaResult.status === 'ANSWERED' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Grounded Evidence Verified
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                        <AlertCircle className="w-3.5 h-3.5" /> Insufficient Evidence in Tender
                      </span>
                    )}
                    <span className="text-xs text-slate-400">
                      Confidence: <strong className="text-slate-600">{qaResult.confidence}</strong>
                    </span>
                  </div>
                </div>

                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Question: &ldquo;{qaResult.question}&rdquo;
                </p>
                <div className="text-sm text-slate-800 whitespace-pre-line leading-relaxed font-normal">
                  {qaResult.answer}
                </div>
              </div>

              {/* Supporting Citations */}
              {qaResult.citations && qaResult.citations.length > 0 && (
                <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50/50">
                  <button
                    onClick={() => setExpandedCitations(!expandedCitations)}
                    className="w-full px-4 py-2.5 bg-slate-100/70 text-xs font-semibold text-slate-700 flex items-center justify-between hover:bg-slate-200/60 transition-colors"
                  >
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      Supporting Document Citations ({qaResult.citations.length})
                    </span>
                    {expandedCitations ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  {expandedCitations && (
                    <div className="p-4 space-y-2.5">
                      {qaResult.citations.map((cit, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-700 shadow-2xs"
                        >
                          <div className="flex items-center justify-between font-semibold text-slate-800 mb-1">
                            <span className="flex items-center gap-1.5 text-blue-700">
                              <FileText className="w-3.5 h-3.5" />
                              {cit.source_filename}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[11px]">
                              Page {cit.page_number}
                            </span>
                          </div>
                          <p className="italic text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 font-mono text-[11px] leading-relaxed">
                            &ldquo;{cit.supporting_excerpt}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
