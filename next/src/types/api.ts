// API Response Types

// Auth
export interface AuthResponse {
  api_key: string;
}

// User
export interface User {
  userId: string;
  username: string;
  attributes?: {
    email?: string;
    name?: string;
    phone_number?: string;
  };
}

// Collections/Indexes
export interface CollectionMetadata {
  name: string;
  files: string[];
  num_chunks: number;
}

export interface ListCollectionsResponse {
  collections: CollectionMetadata[];
}

export interface UploadResponse {
  message: string;
  indexed_chunks: number;
}

export interface DeleteResponse {
  message: string;
}

// Query
export interface QueryRequest {
  query: string;
  collection?: string;
  collections?: string[];
}

export interface QueryRawResults {
  ids: string[][];
  documents: string[][];
  metadatas: Record<string, unknown>[][];
  distances: number[][];
}

export interface QueryResponse {
  context: string;
  raw_results: QueryRawResults;
}

// Corpus
export interface Corpus {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  is_public: boolean;
  is_approved: boolean;
  owner_id: number;
  owner_username?: string;
  owner_email?: string;
  num_chunks: number;
  num_files: number;
  created_at?: string;
  updated_at?: string;
  user_permission?: string;
  is_owner?: boolean;
}

export interface CorpusCreateRequest {
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  is_public?: boolean;
}

export interface CorpusUpdateRequest {
  display_name?: string;
  description?: string;
  category?: string;
  is_public?: boolean;
}

export interface CorpusVersion {
  version: number;
  description?: string;
  author_id: number;
  author_username?: string;
  num_chunks: number;
  num_files: number;
  created_at: string;
}

export interface CorpusVersionsResponse {
  versions: CorpusVersion[];
}

export interface SubscribeRequest {
  tier: 'free' | 'basic' | 'premium';
}

export interface ListCorpusesResponse {
  corpuses: Corpus[];
}

// Admin
export interface PendingCorpus {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  category?: string;
  owner_username: string;
  version: number;
}

export interface UsageStats {
  unique_users?: number;
  total_actions: number;
  total_queries: number;
  last_access?: string;
}

// Error
export interface ApiError {
  detail: string;
  error_code?: string;
}
