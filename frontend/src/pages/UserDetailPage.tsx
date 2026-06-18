import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getUser, getUserProfile } from '../api/users';
import { refreshUserProfile } from '../api/profiles';
import { ApiError } from '../api/client';
import type { ProfileResponse, UserSchema } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';

export default function UserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const [user, setUser] = useState<UserSchema | null>(null);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const handleRefreshProfile = async () => {
    if (!userId) return;
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const r = await refreshUserProfile(userId);
      setRefreshResult(`Refreshed: gen ${r.data.generation}, source=${r.data.source}, events=${r.data.event_count}`);
      // Reload profile
      const p = await getUserProfile(userId);
      setProfile(p.data);
    } catch (e) {
      setRefreshResult(`Refresh failed: ${e instanceof ApiError ? e.message : 'Error'}`);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    getUser(userId)
      .then(r => setUser(r.data))
      .catch(e => {
        if (e instanceof ApiError && e.status === 404) setNotFound(true);
        else setError(e.message);
      })
      .finally(() => setLoading(false));

    getUserProfile(userId)
      .then(r => setProfile(r.data))
      .catch(e => { setProfileError(e instanceof ApiError && e.status === 503 ? 'Profile service not ready' : e.message); });
  }, [userId]);

  if (loading) return <div className="loading">Loading...</div>;
  if (notFound) return <ErrorState title="Not Found" message={`User "${userId}" not found.`} />;
  if (error) return <ErrorState title="Error" message={error} />;

  return (
    <div>
      <div className="page-header">
        <h2>User Detail</h2>
        <Link to="/users">← Back to Users</Link>
      </div>
      {user && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>{user.user_id} {user.is_cold_start && <span className="badge badge-info">Cold Start</span>}</h3>
          <div className="grid-2" style={{ fontSize: 14 }}>
            <div><span style={{color:'var(--muted)'}}>Activity:</span> {user.activity_level || '—'}</div>
            <div><span style={{color:'var(--muted)'}}>Price Pref:</span> {user.price_preference || '—'}</div>
            <div><span style={{color:'var(--muted)'}}>Categories:</span> <div className="tag-list">{user.preferred_categories?.map(c=><span key={c} className="tag">{c}</span>)}</div></div>
            <div><span style={{color:'var(--muted)'}}>Brands:</span> <div className="tag-list">{user.preferred_brands?.map(b=><span key={b} className="tag">{b}</span>)}</div></div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex-between" style={{ marginBottom: 8 }}>
          <h3>Profile</h3>
          <button onClick={handleRefreshProfile} disabled={refreshing} aria-label="Refresh profile">
            {refreshing ? 'Refreshing...' : 'Refresh Profile'}
          </button>
        </div>
        {refreshResult && <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>{refreshResult}</p>}
        {profileError && <ErrorState title="Profile" message={profileError} />}
        {profile && (
          <div className="grid-2" style={{ fontSize: 14 }}>
            <div><span style={{color:'var(--muted)'}}>Status:</span> <span className={`badge ${profile.status==='warm'?'badge-success':'badge-warning'}`}>{profile.status}</span></div>
            <div><span style={{color:'var(--muted)'}}>Generation:</span> {profile.generation}</div>
            <div><span style={{color:'var(--muted)'}}>Built:</span> {profile.built_at || '—'}</div>
            <div><span style={{color:'var(--muted)'}}>Mean Log Price:</span> {profile.mean_log_price?.toFixed(4) || '—'}</div>
            {profile.fallback_reason && <div><span style={{color:'var(--muted)'}}>Fallback:</span> {profile.fallback_reason}</div>}
            <div>
              <span style={{color:'var(--muted)'}}>Top Categories:</span>
              {Object.entries(profile.category_weights || {}).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([k,v])=>(
                <div key={k} style={{marginTop:4}}>
                  <span style={{fontSize:12}}>{k}</span>
                  <div className="score-bar"><div className="score-fill" style={{width:`${(v*100).toFixed(0)}%`}} /></div>
                </div>
              ))}
            </div>
            <div>
              <span style={{color:'var(--muted)'}}>Top Brands:</span>
              {Object.entries(profile.brand_weights || {}).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([k,v])=>(
                <div key={k} style={{marginTop:4}}>
                  <span style={{fontSize:12}}>{k}</span>
                  <div className="score-bar"><div className="score-fill" style={{width:`${(v*100).toFixed(0)}%`}} /></div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
