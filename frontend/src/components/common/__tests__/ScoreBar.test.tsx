import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <span>{label}</span>
      <div className="score-bar" role="progressbar" aria-valuenow={pct}>
        <div className="score-fill" style={{ width: `${pct}%` }} />
      </div>
      <span>{pct}%</span>
    </div>
  );
}

describe('ScoreBar', () => {
  it('renders percentage for 0.5', () => {
    render(<ScoreBar value={0.5} label="Test" />);
    expect(screen.getByText('50%')).toBeDefined();
  });

  it('renders 0% for 0', () => {
    render(<ScoreBar value={0} label="Zero" />);
    expect(screen.getByText('0%')).toBeDefined();
  });

  it('renders 100% for 1', () => {
    render(<ScoreBar value={1.0} label="Full" />);
    expect(screen.getByText('100%')).toBeDefined();
  });
});
