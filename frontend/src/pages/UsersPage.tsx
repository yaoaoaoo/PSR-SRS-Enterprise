import { useEffect, useState } from 'react';
import { listUsers } from '../api/users';
import { ApiError, NetworkError } from '../api/client';
import type { UserSchema } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Link } from 'react-router-dom';

export default function UsersPage() {
  const [users, setUsers] = useState<UserSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listUsers();
      setUsers(resp.data || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof NetworkError ? 'Cannot connect' : String(e));
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="page-header"><h2>Users</h2><p>{users.length} users</p></div>
      {error && <ErrorState title="Error" message={error} onRetry={load} />}
      {loading && <div className="loading" aria-busy="true">Loading...</div>}
      {!loading && users.length === 0 && <EmptyState />}
      {!loading && users.length > 0 && (
        <table aria-label="Users list">
          <thead><tr><th>User ID</th><th>Activity</th><th>Price Pref</th><th>Preferences</th><th>Cold Start</th></tr></thead>
          <tbody>
            {users.map(u => (
              <tr key={u.user_id}>
                <td><Link to={`/users/${u.user_id}`}>{u.user_id}</Link></td>
                <td>{u.activity_level || '—'}</td>
                <td>{u.price_preference || '—'}</td>
                <td>
                  <div className="tag-list">
                    {u.preferred_categories?.slice(0, 2).map(c => <span key={c} className="tag">{c}</span>)}
                    {u.preferred_brands?.slice(0, 2).map(b => <span key={b} className="tag">{b}</span>)}
                  </div>
                </td>
                <td>{u.is_cold_start ? <span className="badge badge-info">Yes</span> : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
