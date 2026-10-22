import { apiClient } from './client';
import {
  TenderCreatePayload,
  TenderDocumentResponse,
  TenderProcessingStatusResponse,
  TenderResponse,
  TenderUpdatePayload,
} from '../types/tender';

export const adminApi = {
  createTender: async (payload: TenderCreatePayload): Promise<TenderResponse> => {
    const res = await apiClient.post<TenderResponse>('/admin/tenders', payload);
    return res.data;
  },

  updateTender: async (tenderId: string, payload: TenderUpdatePayload): Promise<TenderResponse> => {
    const res = await apiClient.put<TenderResponse>(`/admin/tenders/${tenderId}`, payload);
    return res.data;
  },

  deleteTender: async (tenderId: string): Promise<void> => {
    await apiClient.delete(`/admin/tenders/${tenderId}`);
  },

  uploadTenderDocs: async (tenderId: string, files: File[]): Promise<TenderDocumentResponse[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await apiClient.post<TenderDocumentResponse[]>(
      `/admin/tenders/${tenderId}/upload-docs`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return res.data;
  },

  processTender: async (tenderId: string): Promise<TenderResponse> => {
    const res = await apiClient.post<TenderResponse>(`/admin/tenders/${tenderId}/process`);
    return res.data;
  },

  getProcessingStatus: async (tenderId: string): Promise<TenderProcessingStatusResponse> => {
    const res = await apiClient.get<TenderProcessingStatusResponse>(
      `/admin/tenders/${tenderId}/processing-status`
    );
    return res.data;
  },
};
