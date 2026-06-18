interface Props {
  title?: string;
  message: string;
  code?: string;
  requestId?: string;
  onRetry?: () => void;
}

export function ErrorState({ title = 'Error', message, code, requestId, onRetry }: Props) {
  return (
    <div className="error-state" role="alert">
      <h3>{title}</h3>
      <p>{message}</p>
      {code && <p style={{ fontSize: '12px', color: 'var(--muted)' }}>Code: {code}</p>}
      {requestId && <p style={{ fontSize: '12px', color: 'var(--muted)' }}>Request ID: {requestId}</p>}
      {onRetry && (
        <button onClick={onRetry} style={{ marginTop: 8 }}>Retry</button>
      )}
    </div>
  );
}
