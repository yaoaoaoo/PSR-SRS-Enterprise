import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getHealth, getReadiness } from '../health';

const mockFetch = vi.fn();
global.fetch = mockFetch;
beforeEach(() => { mockFetch.mockReset(); });

describe('health API', () => {
  it('getHealth returns ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200, headers: new Headers(),
      json: async () => ({ status: 'ok', service: 'PSR-SRS', version: '0.1.0', environment: 'test', timestamp: '2026-01-01T00:00:00Z' }),
    });
    const r = await getHealth();
    expect(r.status).toBe('ok');
  });

  it('getReadiness handles 503', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false, status: 503, headers: new Headers({ 'X-Request-ID': 'rid503' }),
      json: async () => ({ status: 'not_ready', service: 'PSR-SRS', version: '0.1.0', checks: {}, timestamp: '2026-01-01T00:00:00Z' }),
    });
    await expect(getReadiness()).rejects.toThrow();
  });

  it('getHealth sends X-Request-ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200, headers: new Headers({ 'X-Request-ID': 'fe-abc-1' }),
      json: async () => ({ status: 'ok' }),
    });
    await getHealth();
    const reqHeaders = mockFetch.mock.calls[0][1].headers;
    expect(reqHeaders['X-Request-ID']).toBeDefined();
  });
});
