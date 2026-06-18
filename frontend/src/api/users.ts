import { apiGet } from './client';
import type { DataResponse, ListResponse, ProfileResponse, UserSchema } from './types';

export function listUsers(signal?: AbortSignal) {
  return apiGet<ListResponse<UserSchema>>('/users', signal);
}

export function getUser(userId: string, signal?: AbortSignal) {
  return apiGet<DataResponse<UserSchema>>(`/users/${userId}`, signal);
}

export function getUserProfile(userId: string, signal?: AbortSignal) {
  return apiGet<DataResponse<ProfileResponse>>(`/users/${userId}/profile`, signal);
}
