interface Props { message?: string; }

export function EmptyState({ message = 'No results found.' }: Props) {
  return <div className="empty-state" role="status">{message}</div>;
}
