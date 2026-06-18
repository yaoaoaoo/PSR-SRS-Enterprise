import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createEvent, getEventStats, getRecentEvents } from '../events';
import { ApiError } from '../client';

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockResponse(status: number, body: unknown, headers?: Record<string, string>) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers || {}),
    json: async () => body,
  });
}

beforeEach(() => { mockFetch.mockReset(); });

describe('createEvent', () => {
  it('sends POST with correct body', async () => {
    mockResponse(201, { data: { event_id: 'ev1', event_type: 'click' }, meta: { request_id: 'r', api_version: 'v1' } }, { 'X-Request-ID': 'r' });
    await createEvent({ event_type: 'click', event_id: 'ev1', request_id: 'r1', item_id: 'i1', position: 1 });
    const call = mockFetch.mock.calls[0];
    expect(call[0]).toContain('/events');
    expect(call[1].method).toBe('POST');
  });

  it('throws ApiError on 422', async () => {
    mockResponse(422, { error: { code: 'invalid_event', message: 'bad' }, meta: { request_id: 'r' } });
    await expect(createEvent({ event_type: 'INVALID', event_id: 'x', request_id: 'r' })).rejects.toThrow(ApiError);
  });

  it('throws on network error', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));
    await expect(createEvent({ event_type: 'click', event_id: 'x', request_id: 'r' })).rejects.toThrow();
  });
});

describe('getEventStats', () => {
  it('fetches stats', async () => {
    mockResponse(200, { data: { total_events: 5, event_counts: {}, rates: {} }, meta: { request_id: 'r', api_version: 'v1' } });
    const resp = await getEventStats();
    expect(resp.data.total_events).toBe(5);
  });

  it('passes filter params', async () => {
    mockResponse(200, { data: { total_events: 0, event_counts: {}, rates: {} }, meta: { request_id: 'r', api_version: 'v1' } });
    await getEventStats({ user_id: 'u1', event_type: 'click' });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('user_id=u1');
  });
});

describe('getRecentEvents', () => {
  it('fetches recent events', async () => {
    mockResponse(200, { data: [], pagination: { offset: 0, limit: 20, total: 0, returned: 0 }, meta: { request_id: 'r', api_version: 'v1' } });
    const resp = await getRecentEvents();
    expect(resp.data).toEqual([]);
  });
});
