import { apiClient } from './client';
import { CompanyCreatePayload, CompanyResponse, CompanyUpdatePayload } from '../types/company';
import { ResponseEnvelope } from '../types/common';

export const companyApi = {
  getProfile: async (): Promise<CompanyResponse> => {
    const res = await apiClient.get<ResponseEnvelope<CompanyResponse>>('/company/profile');
    return res.data.data;
  },

  createProfile: async (payload: CompanyCreatePayload): Promise<CompanyResponse> => {
    const res = await apiClient.post<ResponseEnvelope<CompanyResponse>>('/company/profile', payload);
    return res.data.data;
  },

  updateProfile: async (payload: CompanyUpdatePayload): Promise<CompanyResponse> => {
    const res = await apiClient.put<ResponseEnvelope<CompanyResponse>>('/company/profile', payload);
    return res.data.data;
  },
};
