import { useEffect, useState } from 'react';
import { getHealth, getReadiness } from '../api/health';
import { getSystemStatus, getIndexStatus, getProfileStatus } from '../api/system';
import { ApiError, NetworkError } from '../api/client';
import type { HealthStatus, ReadinessStatus, SystemStatus as SysStatus, IndexStatus, ProfileStatus } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';

export default function SystemPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [sys, setSys] = useState<SysStatus | null>(null);
  const [index, setIndex] = useState<IndexStatus | null>(null);
  const [profiles, setProfiles] = useState<ProfileStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [h, r, s, i, p] = await Promise.all([
        getHealth().catch(() => null),
        getReadiness().catch(e => e instanceof ApiError ? e : null),
        getSystemStatus().catch(() => null),
        getIndexStatus().catch(() => null),
        getProfileStatus().catch(() => null),
      ]);
      setHealth(h as HealthStatus);
      setReadiness(r && 'status' in r ? r as ReadinessStatus : null);
      setSys(s?.data || null);
      setIndex(i?.data || null);
      setProfiles(p?.data || null);
    } catch (e) {
      setError(e instanceof NetworkError ? 'Cannot connect to server' : String(e));
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="loading">Loading system status...</div>;
  if (error) return <ErrorState title="Connection Error" message={error} onRetry={load} />;

  return (
    <div>
      <div className="page-header flex-between">
        <h2>System Status</h2>
        <button onClick={load} aria-label="Refresh system status">Refresh</button>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Health</div>
          {health ? (
            <div style={{fontSize:14}}>
              <p><span style={{color:'var(--muted)'}}>Status:</span> <span className={`badge ${health.status==='ok'?'badge-success':'badge-warning'}`}>{health.status}</span></p>
              <p><span style={{color:'var(--muted)'}}>Service:</span> {health.service}</p>
              <p><span style={{color:'var(--muted)'}}>Version:</span> {health.version}</p>
            </div>
          ) : <p style={{color:'var(--danger)'}}>Not available</p>}
        </div>

        <div className="card">
          <div className="card-title">Readiness</div>
          {readiness ? (
            <div style={{fontSize:14}}>
              <p><span style={{color:'var(--muted)'}}>Status:</span> <span className={`badge ${readiness.status==='ready'?'badge-success':readiness.status==='degraded'?'badge-warning':'badge-danger'}`}>{readiness.status}</span></p>
              {readiness.checks && Object.entries(readiness.checks).map(([k,v]) => (
                <p key={k}><span style={{color:'var(--muted)'}}>{k}:</span> {String(v)}</p>
              ))}
            </div>
          ) : <ErrorState title="Readiness" message="Readiness check returned an error" />}
        </div>

        <div className="card">
          <div className="card-title">System</div>
          {sys ? (
            <div style={{fontSize:14}}>
              <p><span style={{color:'var(--muted)'}}>DB:</span> {sys.database_connected ? <span className="badge badge-success">Connected</span> : <span className="badge badge-danger">Disconnected</span>}</p>
              <p><span style={{color:'var(--muted)'}}>Schema:</span> {sys.schema_available ? <span className="badge badge-success">Available</span> : <span className="badge badge-warning">Missing</span>}</p>
              <p><span style={{color:'var(--muted)'}}>Environment:</span> {sys.environment}</p>
            </div>
          ) : <p>Not available</p>}
        </div>

        <div className="card">
          <div className="card-title">Index</div>
          {index ? (
            <div style={{fontSize:14}}>
              <p><span style={{color:'var(--muted)'}}>Ready:</span> <span className={`badge ${index.ready?'badge-success':'badge-warning'}`}>{String(index.ready)}</span></p>
              <p><span style={{color:'var(--muted)'}}>Generation:</span> {index.generation}</p>
              <p><span style={{color:'var(--muted)'}}>Items:</span> {index.item_count}</p>
              <p><span style={{color:'var(--muted)'}}>Built:</span> {index.built_at || '—'}</p>
            </div>
          ) : <p>Not available</p>}
        </div>

        <div className="card" style={{gridColumn:'1/-1'}}>
          <div className="card-title">Profiles</div>
          {profiles ? (
            <div style={{fontSize:14}}>
              <p><span style={{color:'var(--muted)'}}>Ready:</span> <span className={`badge ${profiles.ready?'badge-success':'badge-warning'}`}>{String(profiles.ready)}</span></p>
              <p><span style={{color:'var(--muted)'}}>Generation:</span> {profiles.generation}</p>
              <p><span style={{color:'var(--muted)'}}>Count:</span> {profiles.profile_count}</p>
            </div>
          ) : <p>Not available</p>}
        </div>
      </div>
    </div>
  );
}
