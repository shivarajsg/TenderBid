export interface ResponseEnvelope<T> {
  success: boolean;
  message?: string;
  data: T;
}

export interface ErrorEnvelope {
  success: false;
  error_code: string;
  message: string;
  details?: Array<{ field?: string; message: string; type?: string }> | null;
}
