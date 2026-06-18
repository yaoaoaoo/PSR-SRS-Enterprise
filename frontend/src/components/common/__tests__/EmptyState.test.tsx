import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmptyState } from '../EmptyState';

describe('EmptyState', () => {
  it('renders default message', () => {
    render(<EmptyState />);
    expect(screen.getByText('No results found.')).toBeDefined();
  });

  it('renders custom message', () => {
    render(<EmptyState message="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeDefined();
  });
});
