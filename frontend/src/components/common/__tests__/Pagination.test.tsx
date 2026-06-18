import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Pagination } from '../Pagination';

describe('Pagination', () => {
  it('shows range and total', () => {
    render(<Pagination offset={0} limit={20} total={50} onPrev={vi.fn()} onNext={vi.fn()} />);
    expect(screen.getByText(/1–20 of 50/)).toBeDefined();
  });

  it('disables Previous on first page', () => {
    render(<Pagination offset={0} limit={20} total={50} onPrev={vi.fn()} onNext={vi.fn()} />);
    expect(screen.getByLabelText('Previous page')).toBeDisabled();
  });

  it('disables Next on last page', () => {
    render(<Pagination offset={40} limit={20} total={50} onPrev={vi.fn()} onNext={vi.fn()} />);
    expect(screen.getByLabelText('Next page')).toBeDisabled();
  });
});
