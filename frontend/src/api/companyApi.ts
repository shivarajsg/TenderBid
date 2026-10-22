import { apiClient } from './client';
import {
  CapabilityStatementResponse,
  CompanyCreatePayload,
  CompanyReadinessResponse,
  CompanyResponse,
  CompanyUpdatePayload,
} from '../types/company';
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

  getReadiness: async (): Promise<CompanyReadinessResponse> => {
    const res = await apiClient.get<ResponseEnvelope<CompanyReadinessResponse>>('/company/readiness');
    return res.data.data;
  },

  getCapabilityStatement: async (): Promise<CapabilityStatementResponse> => {
    const res = await apiClient.get<ResponseEnvelope<CapabilityStatementResponse>>('/company/capability-statement');
    return res.data.data;
  },
};
