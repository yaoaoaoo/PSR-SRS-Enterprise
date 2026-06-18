import { useState, useEffect, useRef, useCallback } from 'react';
import { search } from '../api/search';
import { listUsers } from '../api/users';
import { createEvent } from '../api/events';
import { ApiError, NetworkError, TimeoutError } from '../api/client';
import type { SearchHit, SearchMode, UserSchema } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Link } from 'react-router-dom';
import { createEventId, createRequestId, createSessionId } from '../utils/ids';

const MODES: { value: SearchMode; label: string }[] = [
  { value: 'bm25', label: 'BM25' },
  { value: 'semantic', label: 'Semantic' },
  { value: 'rrf', label: 'RRF' },
  { value: 'linear', label: 'Linear' },
];

export default function SearchPage() {
  const [query, setQuery] = useState('electronics');
  const [mode, setMode] = useState<SearchMode>('linear');
  const [topK, setTopK] = useState(10);
  const [personalize, setPersonalize] = useState(false);
  const [userId, setUserId] = useState('');
  const [users, setUsers] = useState<UserSchema[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ title: string; message: string; code?: string; requestId?: string } | null>(null);
  const [result, setResult] = useState<{ hits: SearchHit[]; summary: Record<string, unknown> } | null>(null);
  const [actionStatus, setActionStatus] = useState<Record<string, string>>({});
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef<string>('');
  const sessionIdRef = useRef<string>('');
  const reportedImpressions = useRef<Set<string>>(new Set());

  const loadUsers = useCallback(async () => {
    try {
      const resp = await listUsers();
      setUsers(resp.data || []);
    } catch { /* non-critical */ }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const doSearch = async () => {
    const q = query.trim();
    if (!q) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setError(null);
    setActionStatus({});
    try {
      const resp = await search({
        query: q, mode, top_k: topK,
        user_id: personalize ? userId || null : null,
        personalize,
      }, ctrl.signal);
      const d = resp.data;
      requestIdRef.current = resp.meta?.request_id || createRequestId();
      sessionIdRef.current = createSessionId();
      setResult({ hits: d.hits, summary: { ...d } });
      reportedImpressions.current = new Set();

      // Report impressions for each result
      d.hits.forEach((hit) => {
        const cei = `imp_${requestIdRef.current}_${hit.item_id}`;
        if (!reportedImpressions.current.has(cei)) {
          reportedImpressions.current.add(cei);
          createEvent({
            event_type: 'impression',
            event_id: cei,
            client_event_id: cei,
            request_id: requestIdRef.current,
            session_id: sessionIdRef.current,
            user_id: personalize ? (userId || '') : '',
            query_id: null,
            query_text: q,
            item_id: hit.item_id,
            position: hit.rank,
          }).catch(() => {/* non-critical */});
        }
      });
    } catch (e) {
      if (e instanceof DOMException) return;
      if (e instanceof ApiError) {
        setError({ title: `API Error (${e.status})`, message: e.message, code: e.code, requestId: e.requestId });
      } else if (e instanceof NetworkError) {
        setError({ title: 'Network Error', message: e.message });
      } else if (e instanceof TimeoutError) {
        setError({ title: 'Timeout', message: 'Request timed out. Please try again.' });
      } else {
        setError({ title: 'Error', message: String(e) });
      }
    } finally {
      setLoading(false);
    }
  };

  const reportAction = async (hit: SearchHit, action: string) => {
    const cei = createEventId(action, requestIdRef.current, hit.item_id);
    setActionStatus(prev => ({ ...prev, [hit.item_id]: action }));
    try {
      await createEvent({
        event_type: action,
        event_id: cei,
        client_event_id: cei,
        request_id: requestIdRef.current,
        session_id: sessionIdRef.current,
        user_id: personalize ? (userId || '') : '',
        query_id: null,
        query_text: query.trim(),
        item_id: hit.item_id,
        position: hit.rank,
      });
      setActionStatus(prev => ({ ...prev, [hit.item_id]: `${action}_ok` }));
    } catch {
      setActionStatus(prev => ({ ...prev, [hit.item_id]: `${action}_err` }));
    }
  };

  const reportClick = (hit: SearchHit) => {
    const cei = createEventId('click', requestIdRef.current, hit.item_id);
    createEvent({
      event_type: 'click',
      event_id: cei,
      client_event_id: cei,
      request_id: requestIdRef.current,
      session_id: sessionIdRef.current,
      user_id: personalize ? (userId || '') : '',
      query_id: null,
      query_text: query.trim(),
      item_id: hit.item_id,
      position: hit.rank,
    }).catch(() => {/* non-blocking */});
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') doSearch();
  };

  return (
    <div>
      <div className="page-header">
        <h2>Search</h2>
        <p>BM25, Semantic, Hybrid, and Personalized retrieval</p>
      </div>

      <div className="card">
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <label htmlFor="query-input">Query</label>
            <input id="query-input" value={query} onChange={e => setQuery(e.target.value)}
                   onKeyDown={handleKeyDown} placeholder="Enter search query..." />
          </div>
          <div className="form-group">
            <label htmlFor="mode-select">Mode</label>
            <select id="mode-select" value={mode} onChange={e => setMode(e.target.value as SearchMode)}>
              {MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="topk-input">Top K</label>
            <input id="topk-input" type="number" min={1} max={100} value={topK}
                   onChange={e => setTopK(Number(e.target.value) || 10)} />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={personalize}
                     onChange={e => setPersonalize(e.target.checked)} />
              Personalize
            </label>
          </div>
          <div className="form-group">
            <label htmlFor="user-select">User</label>
            <select id="user-select" value={userId} onChange={e => setUserId(e.target.value)}
                    disabled={!personalize}>
              <option value="">-- Select user --</option>
              {users.slice(0, 50).map(u => (
                <option key={u.user_id} value={u.user_id}>
                  {u.user_id} {u.is_cold_start ? '(cold-start)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="primary" onClick={doSearch} disabled={loading || !query.trim()}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button onClick={() => { setQuery(''); setMode('linear'); setTopK(10); setPersonalize(false); setUserId(''); setError(null); setResult(null); }}>
            Reset
          </button>
        </div>
      </div>

      {error && <ErrorState {...error} onRetry={doSearch} />}

      {loading && <div className="loading" aria-busy="true">Searching...</div>}

      {result && !loading && (
        <>
          <div className="card">
            <div className="card-title">Search Summary</div>
            <div style={{ fontSize: 14, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px' }}>
              <span style={{ color: 'var(--muted)' }}>Query:</span><span>{String(result.summary.query ?? '')}</span>
              <span style={{ color: 'var(--muted)' }}>Mode:</span><span>{String(result.summary.mode ?? '')}</span>
              <span style={{ color: 'var(--muted)' }}>Results:</span><span>{String(result.summary.returned_count ?? 0)} / {String(result.summary.total_candidates ?? 0)} candidates</span>
              <span style={{ color: 'var(--muted)' }}>Time:</span><span>{String(result.summary.took_ms ?? 0)} ms</span>
              {(Boolean(result.summary.personalization_requested)) && (
                <>
                  <span style={{ color: 'var(--muted)' }}>Personalized:</span>
                  <span className={`badge ${result.summary.personalization_applied ? 'badge-success' : 'badge-warning'}`}>
                    {result.summary.personalization_applied ? 'Applied' : 'Not applied'}
                  </span>
                </>
              )}
              {Boolean(result.summary.fallback_reason) && (
                <>
                  <span style={{ color: 'var(--muted)' }}>Fallback:</span>
                  <span style={{ color: 'var(--warning)' }}>{String(result.summary.fallback_reason ?? '')}</span>
                </>
              )}
            </div>
          </div>

          {result.hits.length === 0 ? (
            <EmptyState message="No results found for this query." />
          ) : (
            <table aria-label="Search results">
              <thead>
                <tr>
                  <th>#</th><th>Title</th><th>Category</th><th>Brand</th><th>Price</th><th>Score</th><th>Actions</th>
                  {Boolean(result.summary.personalization_applied) && <th>Original</th>}
                </tr>
              </thead>
              <tbody>
                {result.hits.map(hit => (
                  <tr key={hit.item_id}>
                    <td>{hit.rank}</td>
                    <td>
                      <Link to={`/items/${hit.item_id}`} onClick={() => reportClick(hit)}>{hit.title || hit.item_id}</Link>
                      {hit.is_cold_start && <span className="badge badge-info" style={{ marginLeft: 6 }}>Cold</span>}
                    </td>
                    <td>{hit.category || '—'}</td>
                    <td>{hit.brand || '—'}</td>
                    <td>{hit.price || '—'}</td>
                    <td>{hit.score?.toFixed(4)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={() => reportAction(hit, 'favorite')}
                          disabled={!!actionStatus[hit.item_id]}
                          aria-label={`Favorite ${hit.title || hit.item_id}`}
                          style={{ padding: '2px 6px', fontSize: 12 }}
                        >
                          {actionStatus[hit.item_id] === 'favorite_ok' ? '★' : actionStatus[hit.item_id] === 'favorite_err' ? '★!' : '☆'}
                        </button>
                        <button
                          onClick={() => reportAction(hit, 'add_to_cart')}
                          disabled={!!actionStatus[hit.item_id]}
                          aria-label={`Add ${hit.title || hit.item_id} to cart`}
                          style={{ padding: '2px 6px', fontSize: 12 }}
                        >
                          {actionStatus[hit.item_id] === 'add_to_cart_ok' ? 'Cart✓' : actionStatus[hit.item_id] === 'add_to_cart_err' ? 'Cart!' : 'Cart'}
                        </button>
                        <button
                          onClick={() => reportAction(hit, 'purchase')}
                          disabled={!!actionStatus[hit.item_id]}
                          aria-label={`Purchase ${hit.title || hit.item_id}`}
                          style={{ padding: '2px 6px', fontSize: 12 }}
                        >
                          {actionStatus[hit.item_id] === 'purchase_ok' ? 'Buy✓' : actionStatus[hit.item_id] === 'purchase_err' ? 'Buy!' : 'Buy'}
                        </button>
                      </div>
                    </td>
                    {Boolean(result.summary.personalization_applied) && <td>{hit.original_rank ?? '—'}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
