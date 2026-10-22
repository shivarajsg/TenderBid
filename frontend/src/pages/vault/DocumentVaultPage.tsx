import React, { useEffect, useState } from 'react';
import { documentsApi } from '../../api/documentsApi';
import { DocumentResponse, DocumentCategory, DOCUMENT_CATEGORIES } from '../../types/document';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorAlert } from '../../components/common/ErrorAlert';
import { Modal } from '../../components/common/Modal';
import { getErrorMessage } from '../../api/client';
import {
  FolderLock,
  Upload,
  FileCheck2,
  Trash2,
  FileText,
  CheckCircle,
  Database,
  Filter,
} from 'lucide-react';

export const DocumentVaultPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState<DocumentCategory>('FINANCIAL_AUDIT');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchDocuments = async (categoryFilter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentsApi.listDocuments(categoryFilter || undefined);
      setDocuments(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments(selectedCategory);
  }, [selectedCategory]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a PDF document to upload.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      await documentsApi.uploadDocument(uploadFile, uploadCategory);
      setIsUploadOpen(false);
      setUploadFile(null);
      await fetchDocuments(selectedCategory);
    } catch (err: unknown) {
      setUploadError(getErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to remove "${filename}" from your vault?`)) {
      return;
    }
    try {
      await documentsApi.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FolderLock className="w-7 h-7 text-blue-600" />
            Company Document Vault
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Securely uploaded MSME proofs indexed for hybrid retrieval & citation generation
          </p>
        </div>

        <Button
          onClick={() => {
            setUploadFile(null);
            setUploadError(null);
            setIsUploadOpen(true);
          }}
          icon={<Upload className="w-4 h-4" />}
        >
          Upload New Document
        </Button>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
            Filter by Category:
          </span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="">All Categories ({documents.length})</option>
            {DOCUMENT_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-500">
          Showing <span className="font-semibold text-slate-800">{documents.length}</span> documents
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Retrieving secure document inventory..." />
      ) : documents.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200">
          <EmptyState
            title="Vault is empty"
            description="Upload your audited balance sheets, tax returns, GST certificates, or past work orders so the compliance engine can cite them."
            actionLabel="Upload First Proof Document"
            onAction={() => setIsUploadOpen(true)}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
                    <FileText className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                    {doc.document_category}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-slate-900 truncate" title={doc.original_filename}>
                  {doc.original_filename}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Uploaded on {new Date(doc.created_at).toLocaleDateString()}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-500">
                  <div>
                    <span className="text-slate-400">Size:</span> {formatFileSize(doc.file_size_bytes)}
                  </div>
                  <div>
                    <span className="text-slate-400">Pages:</span> {doc.total_pages || '—'}
                  </div>
                  <div className="flex items-center gap-1">
                    <Database className="w-3.5 h-3.5 text-blue-500" />
                    <span>{doc.indexed_chunks || 0} chunks</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>{doc.verification_status}</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400 truncate max-w-[150px]">
                  {doc.sha256_hash ? `${doc.sha256_hash.substring(0, 16)}...` : 'N/A'}
                </span>
                <button
                  onClick={() => handleDelete(doc.id, doc.original_filename)}
                  className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors"
                  title="Delete from Vault"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        isOpen={isUploadOpen}
        onClose={() => !isUploading && setIsUploadOpen(false)}
        title="Upload Document to Vault"
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          {uploadError && <ErrorAlert message={uploadError} onDismiss={() => setUploadError(null)} />}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Document Category <span className="text-rose-500">*</span>
            </label>
            <select
              value={uploadCategory}
              onChange={(e) => setUploadCategory(e.target.value as DocumentCategory)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {DOCUMENT_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Select PDF File <span className="text-rose-500">*</span>
            </label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              required
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) setUploadFile(file);
              }}
              className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="text-xs text-slate-400 mt-1">
              Supports searchable and scanned PDFs. Text is extracted, chunked, and indexed into the vector DB.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              disabled={isUploading}
              onClick={() => setIsUploadOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={isUploading}
              icon={<Upload className="w-4 h-4" />}
            >
              Upload & Vectorize
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
