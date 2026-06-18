import { apiGet } from './client';
import type { DataResponse, IndexStatus, ProfileStatus, SystemStatus } from './types';

export function getSystemStatus(signal?: AbortSignal) {
  return apiGet<DataResponse<SystemStatus>>('/system/status', signal);
}

export function getIndexStatus(signal?: AbortSignal) {
  return apiGet<DataResponse<IndexStatus>>('/system/index', signal);
}

export function getProfileStatus(signal?: AbortSignal) {
  return apiGet<DataResponse<ProfileStatus>>('/system/profiles', signal);
}
