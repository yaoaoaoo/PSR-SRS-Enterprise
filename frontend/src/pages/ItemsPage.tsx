import { useEffect, useState } from 'react';
import { listItems } from '../api/items';
import { ApiError, NetworkError } from '../api/client';
import type { ItemSchema } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Pagination } from '../components/common/Pagination';
import { Link } from 'react-router-dom';

export default function ItemsPage() {
  const [items, setItems] = useState<ItemSchema[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const LIMIT = 20;

  const load = async (o: number) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listItems();
      setItems((resp.data || []).slice(o, o + LIMIT));
      setTotal(resp.pagination?.total || resp.data?.length || 0);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof NetworkError ? 'Cannot connect to server' : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(offset); }, [offset]);

  return (
    <div>
      <div className="page-header"><h2>Items</h2><p>{total} items in catalog</p></div>
      {error && <ErrorState title="Error" message={error} onRetry={() => load(offset)} />}
      {loading && <div className="loading" aria-busy="true">Loading items...</div>}
      {!loading && !error && items.length === 0 && <EmptyState />}
      {!loading && items.length > 0 && (
        <>
          <Pagination offset={offset} limit={LIMIT} total={total}
                      onPrev={() => setOffset(Math.max(0, offset - LIMIT))}
                      onNext={() => setOffset(offset + LIMIT)} />
          <table aria-label="Items list">
            <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Brand</th><th>Price</th><th>Cold Start</th></tr></thead>
            <tbody>
              {items.map(item => (
                <tr key={item.item_id}>
                  <td><Link to={`/items/${item.item_id}`}>{item.item_id}</Link></td>
                  <td>{item.title}</td>
                  <td>{item.category}</td>
                  <td>{item.brand}</td>
                  <td>{item.price}</td>
                  <td>{item.is_cold_start ? <span className="badge badge-info">Yes</span> : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
