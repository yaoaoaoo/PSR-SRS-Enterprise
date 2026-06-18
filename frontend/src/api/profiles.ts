import { apiPost } from './client';
import type { DataResponse } from './types';

export interface RefreshResult {
  user_id: string;
  generation: number;
  source: string;
  event_count: number;
  ignored_event_count: number;
  built_at: string;
  last_event_at: string | null;
  profile: { category_weights: Record<string, number>; brand_weights: Record<string, number>; mean_log_price: number | null } | null;
}

export interface BatchRefreshResult {
  requested_users: number;
  refreshed_users: number;
  unchanged_users: number;
  failed_users: number;
  total_events_used: number;
  generation: number;
  built_at: string;
}

export function refreshUserProfile(userId: string, signal?: AbortSignal) {
  return apiPost<object, DataResponse<RefreshResult>>(`/profiles/${userId}/refresh`, {}, signal);
}

export function refreshAllProfiles(options?: { only_with_events?: boolean; limit?: number }, signal?: AbortSignal) {
  const params = new URLSearchParams();
  if (options?.only_with_events) params.set('only_with_events', 'true');
  if (options?.limit) params.set('limit', String(options.limit));
  const qs = params.toString() ? '?' + params.toString() : '';
  return apiPost<object, DataResponse<BatchRefreshResult>>(`/profiles/refresh${qs}`, {}, signal);
}
