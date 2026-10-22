import { apiClient } from './client';
import {
  ComplianceAnalyzeRequest,
  ComplianceFindingResponse,
  ComplianceReportListResponse,
  ComplianceReportResponse,
} from '../types/compliance';

export const complianceApi = {
  analyzeTender: async (payload: ComplianceAnalyzeRequest): Promise<ComplianceReportResponse> => {
    const res = await apiClient.post<ComplianceReportResponse>('/compliance/analyze', payload);
    return res.data;
  },

  listReports: async (params?: {
    tender_id?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<ComplianceReportListResponse> => {
    const res = await apiClient.get<ComplianceReportListResponse>('/compliance/reports', {
      params,
    });
    return res.data;
  },

  getReport: async (reportId: string): Promise<ComplianceReportResponse> => {
    const res = await apiClient.get<ComplianceReportResponse>(`/compliance/reports/${reportId}`);
    return res.data;
  },

  listFindings: async (reportId: string): Promise<ComplianceFindingResponse[]> => {
    const res = await apiClient.get<ComplianceFindingResponse[]>(`/compliance/reports/${reportId}/findings`);
    return res.data;
  },

  getFinding: async (reportId: string, findingId: string): Promise<ComplianceFindingResponse> => {
    const res = await apiClient.get<ComplianceFindingResponse>(
      `/compliance/reports/${reportId}/findings/${findingId}`
    );
    return res.data;
  },
};
