'use client';

import { fetchAuthSession } from 'aws-amplify/auth';
import type {
  ListCollectionsResponse,
  ListCorpusesResponse,
  UploadResponse,
  DeleteResponse,
  QueryRequest,
  QueryResponse,
  Corpus,
  CorpusCreateRequest,
  CorpusUpdateRequest,
  CorpusVersionsResponse,
  SubscribeRequest,
  PendingCorpus,
  UsageStats,
} from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  errorCode?: string;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
    this.name = 'ApiError';
  }
}

async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.accessToken?.toString() || null;
  } catch {
    return null;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();

  // Check if body is FormData using duck typing (more reliable than instanceof)
  const isFormData = options.body &&
    typeof options.body === 'object' &&
    typeof (options.body as FormData).append === 'function';

  const headers: HeadersInit = {
    'Accept': 'application/json',
    ...options.headers,
  };

  // Only add Content-Type for non-FormData requests
  // For FormData, let the browser set Content-Type with the proper boundary
  if (!isFormData) {
    (headers as Record<string, string>)['Content-Type'] = 'application/json';
  }

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail, error.error_code);
  }

  return response.json();
}

// Index endpoints
export const indexApi = {
  list: () => request<ListCollectionsResponse>('/api/v1/list-indexes/'),

  create: async (collection: string, files: File[]) => {
    const formData = new FormData();
    formData.append('collection', collection);
    files.forEach(file => formData.append('files', file));

    return request<UploadResponse>('/api/v1/create-index/', {
      method: 'POST',
      body: formData,
    });
  },

  update: async (collection: string, files: File[]) => {
    const formData = new FormData();
    formData.append('collection', collection);
    files.forEach(file => formData.append('files', file));

    return request<UploadResponse>('/api/v1/update-index/', {
      method: 'POST',
      body: formData,
    });
  },

  delete: (name: string) =>
    request<DeleteResponse>(`/api/v1/delete-index/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),

  query: (data: QueryRequest) =>
    request<QueryResponse>('/api/v1/query/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Corpus endpoints
export const corpusApi = {
  list: async (): Promise<Corpus[]> => {
    const response = await request<ListCorpusesResponse>('/api/v1/corpus/');
    return response.corpuses;
  },

  create: (data: CorpusCreateRequest) =>
    request<Corpus>('/api/v1/corpus/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: CorpusUpdateRequest) =>
    request<Corpus>(`/api/v1/corpus/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<DeleteResponse>(`/api/v1/corpus/${id}`, {
      method: 'DELETE',
    }),

  subscribe: (id: number, data: SubscribeRequest) =>
    request<{ message: string }>(`/api/v1/corpus/${id}/subscribe`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  unsubscribe: (id: number) =>
    request<{ message: string }>(`/api/v1/corpus/${id}/subscribe`, {
      method: 'DELETE',
    }),

  query: (id: number, query: string, nResults: number = 5) =>
    request<{ context: string }>(`/api/v1/corpus/${id}/query`, {
      method: 'POST',
      body: JSON.stringify({ query, n_results: nResults }),
    }),

  createVersion: (id: number, description?: string) =>
    request<{ version: number }>(`/api/v1/corpus/${id}/versions`, {
      method: 'POST',
      body: JSON.stringify({ description }),
    }),

  listVersions: (id: number) =>
    request<CorpusVersionsResponse>(`/api/v1/corpus/${id}/versions`),
};

// Admin endpoints
export const adminApi = {
  getPendingCorpuses: () =>
    request<PendingCorpus[]>('/api/v1/admin/corpuses/pending'),

  approveCorpus: (id: number) =>
    request<{ message: string }>(`/api/v1/admin/corpuses/${id}/approve`, {
      method: 'POST',
    }),

  rejectCorpus: (id: number) =>
    request<{ message: string }>(`/api/v1/admin/corpuses/${id}/reject`, {
      method: 'POST',
    }),

  getCorpusUsage: (id: number) =>
    request<UsageStats>(`/api/v1/admin/usage/corpus/${id}`),

  getUserUsage: (id: number) =>
    request<UsageStats>(`/api/v1/admin/usage/user/${id}`),
};

export { API_BASE };
