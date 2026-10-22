import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const TOKEN_KEY = 'tender_bid_token';

export const tokenStorage = {
  get: (): string | null => {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string): void => {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      // storage unavailable
    }
  },
  clear: (): void => {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // storage unavailable
    }
  },
};

const rawBaseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
let baseURL = rawBaseURL.trim();
if (baseURL && !baseURL.startsWith('http://') && !baseURL.startsWith('https://') && !baseURL.startsWith('/')) {
  baseURL = `https://${baseURL}`;
}
if (baseURL && baseURL.startsWith('http') && !baseURL.includes('/api/v1')) {
  baseURL = `${baseURL.replace(/\/+$/, '')}/api/v1`;
}

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.get();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      tokenStorage.clear();
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { message?: string; detail?: string | Array<{ msg: string }> };
    if (data?.message) return data.message;
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d) => d.msg).join(', ');
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred. Please try again.';
}
