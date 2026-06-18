import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SystemPage from '../SystemPage';

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockOK(body: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true, status: 200, headers: new Headers(),
    json: async () => body,
  });
}
function setupMocks() {
  mockOK({ status: 'ok', service: 'PSR', version: '0.1', environment: 'test', timestamp: '' });
  // readiness
  mockFetch.mockResolvedValueOnce({ ok: false, status: 503, headers: new Headers(), json: async () => ({ status: 'not_ready', checks: {} }) });
  mockOK({ data: { service: 'PSR', version: '0.1', environment: 'test', database_connected: true, schema_available: true, index_ready: true, index_generation: 1, profile_ready: true, profile_generation: 1, uptime_seconds: null }, meta: { request_id: 'r', api_version: 'v1' } });
  mockOK({ data: { ready: true, generation: 1, built_at: null, item_count: 500, error_message: null }, meta: { request_id: 'r', api_version: 'v1' } });
  mockOK({ data: { ready: true, generation: 3, built_at: null, profile_count: 100, error_message: null }, meta: { request_id: 'r', api_version: 'v1' } });
}

beforeEach(() => { mockFetch.mockReset(); });

describe('SystemPage', () => {
  it('shows profile generation', async () => {
    setupMocks();
    render(<MemoryRouter><SystemPage /></MemoryRouter>);
    expect(await screen.findByText('3')).toBeDefined();
  });

  it('shows profile count', async () => {
    setupMocks();
    render(<MemoryRouter><SystemPage /></MemoryRouter>);
    expect(await screen.findByText('100')).toBeDefined();
  });

  it('shows index item count', async () => {
    setupMocks();
    render(<MemoryRouter><SystemPage /></MemoryRouter>);
    expect(await screen.findByText('500')).toBeDefined();
  });

  it('renders Refresh button', async () => {
    setupMocks();
    render(<MemoryRouter><SystemPage /></MemoryRouter>);
    expect(await screen.findByLabelText('Refresh system status')).toBeDefined();
  });
});
