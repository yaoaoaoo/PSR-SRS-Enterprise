import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return <div className="loading" aria-busy="true" role="status">{message}</div>;
}

describe('LoadingState', () => {
  it('renders default message', () => {
    render(<LoadingState />);
    expect(screen.getByText('Loading...')).toBeDefined();
  });

  it('renders custom message', () => {
    render(<LoadingState message="Fetching data..." />);
    expect(screen.getByText('Fetching data...')).toBeDefined();
  });

  it('has aria-busy', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status').getAttribute('aria-busy')).toBe('true');
  });
});
