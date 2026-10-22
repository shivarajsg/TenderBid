import { apiClient } from './client';
import { DocumentCategory, DocumentResponse } from '../types/document';
import { ResponseEnvelope } from '../types/common';

export const documentsApi = {
  listDocuments: async (category?: string): Promise<DocumentResponse[]> => {
    const res = await apiClient.get<ResponseEnvelope<DocumentResponse[]>>('/company/vault/documents', {
      params: category ? { category } : undefined,
    });
    return res.data.data;
  },

  getDocument: async (documentId: string): Promise<DocumentResponse> => {
    const res = await apiClient.get<ResponseEnvelope<DocumentResponse>>(`/company/vault/documents/${documentId}`);
    return res.data.data;
  },

  uploadDocument: async (file: File, documentCategory: DocumentCategory): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_category', documentCategory);

    const res = await apiClient.post<ResponseEnvelope<DocumentResponse>>(
      '/company/vault/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return res.data.data;
  },

  deleteDocument: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/company/vault/documents/${documentId}`);
  },
};
