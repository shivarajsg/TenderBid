import { apiClient } from './client';
import {
  BidApplicationListResponse,
  BidApplicationResponse,
  CreateBidApplicationPayload,
  UpdateBidApplicationPayload,
} from '../types/application';

export const applicationsApi = {
  listApplications: async (status?: string): Promise<BidApplicationListResponse> => {
    const res = await apiClient.get<BidApplicationListResponse>('/applications', {
      params: status ? { status } : undefined,
    });
    return res.data;
  },

  createApplication: async (payload: CreateBidApplicationPayload): Promise<BidApplicationResponse> => {
    const res = await apiClient.post<BidApplicationResponse>('/applications', payload);
    return res.data;
  },

  getApplication: async (applicationId: string): Promise<BidApplicationResponse> => {
    const res = await apiClient.get<BidApplicationResponse>(`/applications/${applicationId}`);
    return res.data;
  },

  updateApplication: async (
    applicationId: string,
    payload: UpdateBidApplicationPayload
  ): Promise<BidApplicationResponse> => {
    const res = await apiClient.patch<BidApplicationResponse>(`/applications/${applicationId}`, payload);
    return res.data;
  },

  deleteApplication: async (applicationId: string): Promise<void> => {
    await apiClient.delete(`/applications/${applicationId}`);
  },
};
