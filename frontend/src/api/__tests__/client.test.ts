import { describe, it, expect } from 'vitest';
import { ApiError } from '../client';

describe('ApiError', () => {
  it('creates error with all fields', () => {
    const e = new ApiError(404, 'not_found', 'Resource not found', 'rid-001', { extra: true });
    expect(e.status).toBe(404);
    expect(e.code).toBe('not_found');
    expect(e.message).toBe('Resource not found');
    expect(e.requestId).toBe('rid-001');
    expect(e.details).toEqual({ extra: true });
    expect(e.name).toBe('ApiError');
  });

  it('is instance of Error', () => {
    const e = new ApiError(500, 'internal', 'msg', 'r');
    expect(e instanceof Error).toBe(true);
  });
});
