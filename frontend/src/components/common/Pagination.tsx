interface Props {
  offset: number;
  limit: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  canPrev?: boolean;
  canNext?: boolean;
}

export function Pagination({ offset, limit, total, onPrev, onNext }: Props) {
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);

  return (
    <nav className="pagination" aria-label="Pagination">
      <button onClick={onPrev} disabled={offset === 0} aria-label="Previous page">Previous</button>
      <span>{start}–{end} of {total}</span>
      <button onClick={onNext} disabled={offset + limit >= total} aria-label="Next page">Next</button>
    </nav>
  );
}
