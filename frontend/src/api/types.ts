// API type definitions based on real OpenAPI /api/v1/openapi.json

export interface ApiMeta {
  request_id: string;
  api_version: string;
}

export interface DataResponse<T> {
  data: T;
  meta: ApiMeta;
}

export interface PaginationMeta {
  offset: number;
  limit: number;
  total: number;
  returned: number;
}

export interface ListResponse<T> {
  data: T[];
  pagination: PaginationMeta;
  meta: ApiMeta;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details: unknown;
}

export interface ErrorResponse {
  error: ErrorDetail;
  meta: ApiMeta;
}

// Search
export type SearchMode = 'bm25' | 'semantic' | 'rrf' | 'linear';

export interface SearchRequest {
  query: string;
  mode?: SearchMode;
  top_k?: number;
  user_id?: string | null;
  personalize?: boolean;
}

export interface SearchHit {
  item_id: string;
  rank: number;
  score: number;
  source: string;
  original_rank: number | null;
  bm25_score: number | null;
  semantic_score: number | null;
  fusion_score: number | null;
  personalization_score: number | null;
  title: string | null;
  category: string | null;
  subcategory: string | null;
  brand: string | null;
  price: string | null;
  quality_score: number | null;
  popularity_score: number | null;
  is_cold_start: boolean | null;
}

export interface SearchResult {
  query: string;
  mode: string;
  personalization_requested: boolean;
  personalization_applied: boolean;
  user_id: string | null;
  fallback_reason: string | null;
  total_candidates: number;
  returned_count: number;
  index_generation: number;
  took_ms: number;
  hits: SearchHit[];
}

// Items
export interface ItemSchema {
  item_id: string;
  title: string;
  description: string;
  category: string;
  subcategory: string;
  brand: string;
  price: string;
  quality_score: number;
  popularity_score: number;
  is_cold_start: boolean;
  created_at: string | null;
}

// Users
export interface UserSchema {
  user_id: string;
  preferred_categories: string[];
  preferred_brands: string[];
  price_preference: string | null;
  activity_level: string | null;
  is_cold_start: boolean;
  created_at: string | null;
}

export interface ProfileResponse {
  user_id: string;
  status: string;
  generation: number;
  built_at: string | null;
  is_cold_start: boolean;
  category_weights: Record<string, number>;
  brand_weights: Record<string, number>;
  mean_log_price: number | null;
  fallback_reason: string | null;
}

// Evaluation
export interface EvalQueryItem {
  query_id: string;
  query_text?: string;
}

export interface EvaluationQueriesRequest {
  queries: EvalQueryItem[];
  ks: number[];
}

export interface CoverageRequestItem {
  request_id: string;
  query_id?: string;
  candidate_item_ids: string[];
}

export interface CandidateCoverageRequest {
  requests: CoverageRequestItem[];
}

export interface CandidateCoverageResult {
  eligible_requests: number;
  covered_requests: number;
  uncovered_requests: number;
  request_level_coverage: number;
  total_positive_items: number;
  covered_positive_items: number;
  item_level_recall: number;
  took_ms: number;
}

export interface EvaluationResult {
  query_count: number;
  metrics: Record<string, unknown>;
  candidate_coverage: Record<string, unknown> | null;
  took_ms: number;
  ks: number[];
}

// System
export interface SystemStatus {
  service: string;
  version: string;
  environment: string;
  database_connected: boolean;
  schema_available: boolean;
  index_ready: boolean;
  index_generation: number;
  profile_ready: boolean;
  profile_generation: number;
  uptime_seconds: number | null;
}

export interface IndexStatus {
  ready: boolean;
  generation: number;
  built_at: string | null;
  item_count: number;
  error_message: string | null;
}

export interface ProfileStatus {
  ready: boolean;
  generation: number;
  built_at: string | null;
  profile_count: number;
  error_message: string | null;
}

// Health
export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessStatus {
  status: string;
  service: string;
  version: string;
  checks: Record<string, string>;
  details?: Record<string, unknown>;
}
