import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotFoundPage from '../NotFoundPage';

describe('NotFoundPage', () => {
  it('renders 404', () => {
    render(<MemoryRouter><NotFoundPage /></MemoryRouter>);
    expect(screen.getByText('404')).toBeDefined();
    expect(screen.getByText('Page not found.')).toBeDefined();
    expect(screen.getByText('Go to Search')).toBeDefined();
  });
});
