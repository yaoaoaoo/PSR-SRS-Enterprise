import { apiGet } from './client';
import type { HealthStatus, ReadinessStatus } from './types';

export function getHealth(signal?: AbortSignal) {
  return apiGet<HealthStatus>('/health', signal);
}

export function getReadiness(signal?: AbortSignal) {
  return apiGet<ReadinessStatus>('/health/ready', signal);
}
