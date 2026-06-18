import { apiGet } from './client';
import type { DataResponse, ItemSchema, ListResponse } from './types';

export function listItems(signal?: AbortSignal) {
  return apiGet<ListResponse<ItemSchema>>('/items', signal);
}

export function getItem(itemId: string, signal?: AbortSignal) {
  return apiGet<DataResponse<ItemSchema>>(`/items/${itemId}`, signal);
}
