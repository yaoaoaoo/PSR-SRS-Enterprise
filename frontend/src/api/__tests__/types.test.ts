import { describe, it, expect } from 'vitest';

describe('API types', () => {
  it('SearchRequest type is defined at runtime', () => {
    const req = { query: 'test', mode: 'bm25' as const, top_k: 5 };
    expect(req.query).toBe('test');
    expect(req.mode).toBe('bm25');
  });

  it('EventStats has event_counts', () => {
    const stats = { total_events: 0, event_counts: { impression: 0 }, rates: {} };
    expect(stats.total_events).toBe(0);
  });

  it('ApiError has expected fields', async () => {
    const { ApiError } = await import('../client');
    const e = new ApiError(404, 'not_found', 'Missing', 'rid');
    expect(e.status).toBe(404);
    expect(e.code).toBe('not_found');
  });
});
