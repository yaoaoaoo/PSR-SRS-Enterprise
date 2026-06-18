import { useEffect, useState, useCallback } from 'react';
import { getEventStats, getRecentEvents } from '../api/events';
import { ApiError, NetworkError } from '../api/client';
import type { EventRecord, EventStats } from '../api/events';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

function formatRate(r: number | undefined): string {
  if (r === undefined || r === null) return '0%';
  return `${(r * 100).toFixed(2)}%`;
}

const EVENT_COLORS: Record<string, string> = {
  impression: 'badge-info',
  click: 'badge-success',
  favorite: 'badge-warning',
  add_to_cart: 'badge badge-warning',
  purchase: 'badge-success',
};

export default function ActivityPage() {
  const [stats, setStats] = useState<EventStats | null>(null);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [s, r] = await Promise.all([
        getEventStats(),
        getRecentEvents({ limit: '20' }),
      ]);
      setStats(s.data);
      setEvents(r.data || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof NetworkError ? 'Cannot connect to server' : String(e));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="page-header flex-between">
        <h2>Activity</h2>
        <button onClick={load} aria-label="Refresh activity">Refresh</button>
      </div>

      {loading && <div className="loading" aria-busy="true">Loading activity...</div>}
      {error && <ErrorState title="Error" message={error} onRetry={load} />}

      {!loading && stats && (
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card">
            <div className="card-title">Event Counts</div>
            <div style={{ fontSize: 14 }}>
              <p><span style={{ color: 'var(--muted)' }}>Total:</span> {stats.total_events}</p>
              {Object.entries(stats.event_counts).map(([k, v]) => (
                <p key={k}><span style={{ color: 'var(--muted)' }}>{k}:</span> {v}</p>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Conversion Rates</div>
            <div style={{ fontSize: 14 }}>
              <p><span style={{ color: 'var(--muted)' }}>CTR:</span> {formatRate(stats.rates?.click_through_rate)}</p>
              <p><span style={{ color: 'var(--muted)' }}>Favorite:</span> {formatRate(stats.rates?.favorite_rate)}</p>
              <p><span style={{ color: 'var(--muted)' }}>Add to Cart:</span> {formatRate(stats.rates?.add_to_cart_rate)}</p>
              <p><span style={{ color: 'var(--muted)' }}>Purchase:</span> {formatRate(stats.rates?.purchase_rate)}</p>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title">Recent Events</div>
        {!loading && events.length === 0 && !error && <EmptyState message="No events recorded yet." />}
        {events.length > 0 && (
          <table aria-label="Recent events">
            <thead>
              <tr><th>Time</th><th>Type</th><th>User</th><th>Item</th><th>Query</th><th>Position</th></tr>
            </thead>
            <tbody>
              {events.map(e => (
                <tr key={e.event_id}>
                  <td style={{ fontSize: 12 }}>{e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—'}</td>
                  <td><span className={`badge ${EVENT_COLORS[e.event_type] || 'badge-info'}`}>{e.event_type}</span></td>
                  <td style={{ fontSize: 12 }}>{e.user_id || '—'}</td>
                  <td style={{ fontSize: 12 }}>{e.item_id || '—'}</td>
                  <td style={{ fontSize: 12, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.query_text || e.query_id || '—'}</td>
                  <td>{e.position ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
