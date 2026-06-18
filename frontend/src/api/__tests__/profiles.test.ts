import { describe, it, expect, vi, beforeEach } from 'vitest';
import { refreshUserProfile, refreshAllProfiles } from '../profiles';
import { ApiError } from '../client';

const mockFetch = vi.fn();
global.fetch = mockFetch;
beforeEach(() => { mockFetch.mockReset(); });

function mockRes(status: number, body: unknown, headers?: Record<string, string>) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300, status,
    headers: new Headers(headers || {}),
    json: async () => body,
  });
}

describe('refreshUserProfile', () => {
  it('returns refresh result on success', async () => {
    mockRes(200, { data: { user_id: 'u1', generation: 3, source: 'combined', event_count: 5, ignored_event_count: 0, built_at: '2026-01-01T00:00:00Z', last_event_at: null, profile: null }, meta: { request_id: 'r', api_version: 'v1' } });
    const r = await refreshUserProfile('u1');
    expect(r.data.generation).toBe(3);
    expect(r.data.source).toBe('combined');
  });

  it('throws ApiError on 404', async () => {
    mockRes(404, { error: { code: 'user_not_found', message: 'Not found' }, meta: { request_id: 'r' } });
    await expect(refreshUserProfile('bad')).rejects.toThrow(ApiError);
  });
});

describe('refreshAllProfiles', () => {
  it('returns batch result', async () => {
    mockRes(200, { data: { requested_users: 100, refreshed_users: 42, unchanged_users: 58, failed_users: 0, total_events_used: 500, generation: 3, built_at: '2026-01-01T00:00:00Z' }, meta: { request_id: 'r', api_version: 'v1' } });
    const r = await refreshAllProfiles();
    expect(r.data.refreshed_users).toBe(42);
  });

  it('passes only_with_events param', async () => {
    mockRes(200, { data: { requested_users: 10, refreshed_users: 3, unchanged_users: 7, failed_users: 0, total_events_used: 20, generation: 1, built_at: '2026-01-01T00:00:00Z' }, meta: { request_id: 'r', api_version: 'v1' } });
    await refreshAllProfiles({ only_with_events: true, limit: 10 });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('only_with_events=true');
    expect(url).toContain('limit=10');
  });
});
