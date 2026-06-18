import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorState } from '../ErrorState';

describe('ErrorState', () => {
  it('renders message', () => {
    render(<ErrorState message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeDefined();
  });

  it('shows code when provided', () => {
    render(<ErrorState message="Error" code="NOT_FOUND" />);
    expect(screen.getByText(/NOT_FOUND/)).toBeDefined();
  });

  it('shows request ID when provided', () => {
    render(<ErrorState message="Error" requestId="abc-123" />);
    expect(screen.getByText(/abc-123/)).toBeDefined();
  });

  it('shows retry button when onRetry provided', () => {
    render(<ErrorState message="Error" onRetry={() => {}} />);
    expect(screen.getByRole('button', { name: 'Retry' })).toBeDefined();
  });
});
