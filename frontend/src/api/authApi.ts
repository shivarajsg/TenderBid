import { apiClient } from './client';
import { LoginPayload, RegisterPayload, TokenResponse, UserResponse } from '../types/auth';
import { ResponseEnvelope } from '../types/common';

export const authApi = {
  login: async (payload: LoginPayload): Promise<TokenResponse> => {
    const res = await apiClient.post<ResponseEnvelope<TokenResponse>>('/auth/login', payload);
    return res.data.data;
  },

  register: async (payload: RegisterPayload): Promise<UserResponse> => {
    const res = await apiClient.post<ResponseEnvelope<UserResponse>>('/auth/register', payload);
    return res.data.data;
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    const res = await apiClient.get<ResponseEnvelope<UserResponse>>('/auth/me');
    return res.data.data;
  },
};
