import { describe, it, expect } from 'vitest';
import { createClientId, createRequestId, createSessionId, createEventId } from '../ids';

describe('createClientId', () => {
  it('includes prefix', () => {
    const id = createClientId('test');
    expect(id.startsWith('test_')).toBe(true);
  });

  it('produces non-empty result', () => {
    const id = createClientId('x');
    expect(id.length).toBeGreaterThan(3);
  });

  it('produces different results on consecutive calls', () => {
    const a = createClientId('a');
    const b = createClientId('a');
    expect(a).not.toBe(b);
  });
});

describe('createRequestId', () => {
  it('has req prefix', () => {
    expect(createRequestId().startsWith('req_')).toBe(true);
  });

  it('produces unique IDs', () => {
    const ids = new Set(Array.from({ length: 100 }, () => createRequestId()));
    expect(ids.size).toBe(100);
  });
});

describe('createSessionId', () => {
  it('has sess prefix', () => {
    expect(createSessionId().startsWith('sess_')).toBe(true);
  });
});

describe('createEventId', () => {
  it('includes action, requestId, itemId', () => {
    const id = createEventId('click', 'req_abc', 'item_1');
    expect(id.startsWith('click_req_abc_item_1_')).toBe(true);
  });

  it('produces different IDs for same params', () => {
    const a = createEventId('click', 'r1', 'i1');
    const b = createEventId('click', 'r1', 'i1');
    expect(a).not.toBe(b);
  });
});
