import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ActivityPage from '../ActivityPage';

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockStats(total: number, counts: Record<string, number>, rates: Record<string, number>) {
  mockFetch.mockResolvedValueOnce({
    ok: true, status: 200, headers: new Headers(),
    json: async () => ({ data: { total_events: total, event_counts: counts, rates }, meta: { request_id: 'r', api_version: 'v1' } }),
  });
}

function mockRecent(events: unknown[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true, status: 200, headers: new Headers(),
    json: async () => ({ data: events, pagination: { offset: 0, limit: 20, total: events.length, returned: events.length }, meta: { request_id: 'r', api_version: 'v1' } }),
  });
}

function mockError() {
  mockFetch.mockRejectedValueOnce(new Error('Network'));
  mockFetch.mockRejectedValueOnce(new Error('Network'));
}

beforeEach(() => { mockFetch.mockReset(); });

describe('ActivityPage', () => {
  it('renders event counts', async () => {
    mockStats(10, { impression: 5, click: 3, favorite: 1, add_to_cart: 1, purchase: 0 }, { click_through_rate: 0.6, favorite_rate: 0.33, add_to_cart_rate: 0.33, purchase_rate: 0 });
    mockRecent([]);
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(await screen.findByText('10')).toBeDefined();
  });

  it('shows loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // never resolve
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(screen.getByText(/Loading activity/)).toBeDefined();
  });

  it('shows error state', async () => {
    mockError();
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(await screen.findByText(/Error/)).toBeDefined();
  });

  it('shows 0.00% when denominator zero', async () => {
    mockStats(5, { impression: 5, click: 0, favorite: 0, add_to_cart: 0, purchase: 0 }, { click_through_rate: 0, favorite_rate: 0, add_to_cart_rate: 0, purchase_rate: 0 });
    mockRecent([]);
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    const pcts = await screen.findAllByText('0.00%');
    expect(pcts.length).toBeGreaterThanOrEqual(1);
  });

  it('shows empty recent', async () => {
    mockStats(0, {}, {});
    mockRecent([]);
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(await screen.findByText(/No events recorded/)).toBeDefined();
  });

  it('renders recent events with click badge', async () => {
    mockStats(2, { impression: 1, click: 1 }, { click_through_rate: 1.0 });
    mockRecent([{ event_id: 'ev1', event_type: 'click', user_id: 'u1', item_id: 'i1', query_text: 'test', position: 1, timestamp: '2026-01-01T00:00:00Z', client_event_id: null, request_id: 'r1', session_id: '', query_id: null, click_duration_ms: null, add_to_cart_quantity: null, purchase_amount: null }]);
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(await screen.findByText('click')).toBeDefined();
  });

  it('has refresh button', async () => {
    mockStats(0, {}, {});
    mockRecent([]);
    render(<MemoryRouter><ActivityPage /></MemoryRouter>);
    expect(await screen.findByLabelText('Refresh activity')).toBeDefined();
  });
});
