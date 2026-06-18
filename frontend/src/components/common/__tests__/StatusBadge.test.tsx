import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status === 'online' ? 'success' : 'warning'}`}>{status}</span>;
}

describe('StatusBadge', () => {
  it('renders online status', () => {
    render(<StatusBadge status="online" />);
    expect(screen.getByText('online')).toBeDefined();
  });

  it('renders degraded status', () => {
    render(<StatusBadge status="degraded" />);
    expect(screen.getByText('degraded')).toBeDefined();
  });
});
