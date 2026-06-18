import { apiPost } from './client';
import type { DataResponse, SearchRequest, SearchResult } from './types';

export function search(body: SearchRequest, signal?: AbortSignal) {
  return apiPost<SearchRequest, DataResponse<SearchResult>>('/search', body, signal);
}
