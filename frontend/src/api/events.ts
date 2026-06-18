import { apiGet, apiPost } from './client';
import type { DataResponse, ListResponse } from './types';

export interface CreateEventRequest {
  event_type: string;
  event_id: string;
  client_event_id?: string;
  request_id?: string;
  session_id?: string;
  user_id?: string;
  query_id?: string | null;
  query_text?: string | null;
  item_id?: string;
  position?: number | null;
  occurred_at?: string | null;
  click_duration_ms?: number | null;
  add_to_cart_quantity?: number | null;
  purchase_amount?: number | null;
}

export interface EventRecord {
  event_id: string;
  event_type: string;
  client_event_id: string | null;
  request_id: string;
  session_id: string;
  user_id: string;
  query_id: string | null;
  query_text: string | null;
  item_id: string;
  position: number | null;
  timestamp: string;
  click_duration_ms: number | null;
  add_to_cart_quantity: number | null;
  purchase_amount: number | null;
}

export interface EventStats {
  total_events: number;
  event_counts: Record<string, number>;
  rates: Record<string, number>;
}

export function createEvent(body: CreateEventRequest, signal?: AbortSignal) {
  return apiPost<CreateEventRequest, DataResponse<EventRecord>>('/events', body, signal);
}

export function getEventStats(params?: Record<string, string>, signal?: AbortSignal) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return apiGet<DataResponse<EventStats>>(`/events/stats${qs}`, signal);
}

export function getRecentEvents(params?: Record<string, string>, signal?: AbortSignal) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return apiGet<ListResponse<EventRecord>>(`/events/recent${qs}`, signal);
}
