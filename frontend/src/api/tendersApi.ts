import { apiClient } from './client';
import {
  FetchTenderDocumentsResponse,
  IngestionRunResponse,
  IngestionStatusOverviewResponse,
  ProposedRequirementsBundle,
  TenderListResponse,
  TenderQAResponse,
  TenderResponse,
} from '../types/tender';

export interface TenderFilterParams {
  page?: number;
  skip?: number;
  limit?: number;
  sector?: string;
  search?: string;
  min_budget?: number;
  max_budget?: number;
  source_portal?: string;
}

export const tendersApi = {
  listTenders: async (params?: TenderFilterParams): Promise<TenderListResponse> => {
    const res = await apiClient.get<TenderListResponse>('/tenders', {
      params,
    });
    return res.data;
  },

  refreshTenders: async (params?: { source_portal?: string; limit?: number; force?: boolean }): Promise<IngestionRunResponse> => {
    const res = await apiClient.post<IngestionRunResponse>('/tenders/refresh', null, {
      params,
    });
    return res.data;
  },

  getTender: async (tenderId: string): Promise<TenderResponse> => {
    const res = await apiClient.get<TenderResponse>(`/tenders/${tenderId}`);
    return res.data;
  },

  downloadDocument: async (tenderId: string, documentId: string, filename: string): Promise<void> => {
    const res = await apiClient.get(`/tenders/${tenderId}/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  viewDocumentBlob: async (tenderId: string, documentId: string): Promise<string> => {
    const res = await apiClient.get(`/tenders/${tenderId}/documents/${documentId}/view`, {
      responseType: 'blob',
    });
    return window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
  },

  fetchTenderDocuments: async (tenderId: string): Promise<FetchTenderDocumentsResponse> => {
    const res = await apiClient.post<FetchTenderDocumentsResponse>(
      `/tenders/${tenderId}/fetch-documents`
    );
    return res.data;
  },

  askTenderQuestion: async (tenderId: string, question: string): Promise<TenderQAResponse> => {
    const res = await apiClient.post<TenderQAResponse>(`/tenders/${tenderId}/qa`, {
      question,
    });
    return res.data;
  },

  extractTenderRequirements: async (tenderId: string): Promise<ProposedRequirementsBundle> => {
    const res = await apiClient.post<ProposedRequirementsBundle>(
      `/admin/tenders/${tenderId}/extract-requirements`
    );
    return res.data;
  },

  getProposedRequirements: async (tenderId: string): Promise<ProposedRequirementsBundle | null> => {
    const res = await apiClient.get<ProposedRequirementsBundle | null>(
      `/admin/tenders/${tenderId}/proposed-requirements`
    );
    return res.data;
  },

  approveProposedRequirements: async (
    tenderId: string,
    criteriaOverride?: Record<string, unknown>
  ): Promise<TenderResponse> => {
    const res = await apiClient.post<TenderResponse>(
      `/admin/tenders/${tenderId}/approve-requirements`,
      { criteria_override: criteriaOverride }
    );
    return res.data;
  },

  rejectProposedRequirements: async (tenderId: string): Promise<TenderResponse> => {
    const res = await apiClient.post<TenderResponse>(
      `/admin/tenders/${tenderId}/reject-requirements`
    );
    return res.data;
  },

  getIngestionStatus: async (): Promise<IngestionStatusOverviewResponse> => {
    const res = await apiClient.get<IngestionStatusOverviewResponse>('/tenders/ingestion/status');
    return res.data;
  },

  triggerIngestionSync: async (
    sourcePortal: string = 'ALL',
    batchSize: number = 50,
    force: boolean = false
  ): Promise<IngestionRunResponse> => {
    const res = await apiClient.post<IngestionRunResponse>('/tenders/ingestion/sync', {
      source_portal: sourcePortal,
      batch_size: batchSize,
      force,
    });
    return res.data;
  },
};
