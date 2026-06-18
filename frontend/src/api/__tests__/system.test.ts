import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getSystemStatus, getIndexStatus, getProfileStatus } from '../system';

const mockFetch = vi.fn();
global.fetch = mockFetch;
beforeEach(() => { mockFetch.mockReset(); });

function mockRes(body: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true, status: 200, headers: new Headers(),
    json: async () => body,
  });
}

describe('system API', () => {
  it('getSystemStatus returns data', async () => {
    mockRes({ data: { service: 'PSR-SRS', version: '0.1.0', environment: 'test', database_connected: true, schema_available: true, index_ready: true, index_generation: 1, profile_ready: true, profile_generation: 1, uptime_seconds: null }, meta: { request_id: 'r', api_version: 'v1' } });
    const r = await getSystemStatus();
    expect(r.data.profile_ready).toBe(true);
  });

  it('getProfileStatus returns generation', async () => {
    mockRes({ data: { ready: true, generation: 3, built_at: null, profile_count: 100, error_message: null }, meta: { request_id: 'r', api_version: 'v1' } });
    const r = await getProfileStatus();
    expect(r.data.generation).toBe(3);
    expect(r.data.profile_count).toBe(100);
  });

  it('getIndexStatus returns item_count', async () => {
    mockRes({ data: { ready: true, generation: 1, built_at: null, item_count: 500, error_message: null }, meta: { request_id: 'r', api_version: 'v1' } });
    const r = await getIndexStatus();
    expect(r.data.item_count).toBe(500);
  });
});
