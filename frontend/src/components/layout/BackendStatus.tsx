import { useEffect, useState } from 'react';
import { getHealth, getReadiness } from '../../api/health';
import { ApiError, NetworkError } from '../../api/client';

type Status = 'checking' | 'online' | 'degraded' | 'offline';

export function BackendStatus() {
  const [status, setStatus] = useState<Status>('checking');
  const [detail, setDetail] = useState('');

  const check = async () => {
    setStatus('checking');
    try {
      const health = await getHealth();
      if (health.status !== 'ok') { setStatus('degraded'); setDetail('Health not ok'); return; }
      try {
        await getReadiness();
        setStatus('online');
        setDetail('');
      } catch (e) {
        if (e instanceof ApiError && e.status === 503) {
          setStatus('degraded');
          setDetail(`Readiness: ${e.message}`);
        } else {
          setStatus('degraded');
          setDetail('Readiness check failed');
        }
      }
    } catch (e) {
      if (e instanceof NetworkError) {
        setStatus('offline');
        setDetail(e.message);
      } else {
        setStatus('degraded');
        setDetail(String(e));
      }
    }
  };

  useEffect(() => { check(); }, []);

  const labels: Record<Status, string> = {
    checking: 'Checking...',
    online: 'Online',
    degraded: 'Degraded',
    offline: 'Offline',
  };

  return (
    <div className="status-indicator" role="status" aria-live="polite">
      <span className={`status-dot ${status}`} />
      <span>{labels[status]}</span>
      {detail && <span style={{ color: 'var(--muted)' }}>({detail})</span>}
      <button onClick={check} aria-label="Refresh backend status" style={{ padding: '2px 6px', fontSize: '12px', marginLeft: 4 }}>
        Refresh
      </button>
    </div>
  );
}
