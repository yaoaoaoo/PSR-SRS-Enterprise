import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getItem } from '../api/items';
import { ApiError } from '../api/client';
import type { ItemSchema } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';

export default function ItemDetailPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const [item, setItem] = useState<ItemSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!itemId) return;
    setLoading(true);
    getItem(itemId)
      .then(r => setItem(r.data))
      .catch(e => {
        if (e instanceof ApiError && e.status === 404) setNotFound(true);
        else setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [itemId]);

  if (loading) return <div className="loading" aria-busy="true">Loading item...</div>;
  if (notFound) return <ErrorState title="Not Found" message={`Item "${itemId}" not found.`} />;
  if (error) return <ErrorState title="Error" message={error} />;

  return (
    <div>
      <div className="page-header">
        <h2>Item Detail</h2>
        <Link to="/items">← Back to Items</Link>
      </div>
      {item && (
        <div className="card">
          <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '8px 16px', fontSize: 14 }}>
            <span style={{ color: 'var(--muted)' }}>ID:</span><span>{item.item_id}</span>
            <span style={{ color: 'var(--muted)' }}>Title:</span><span>{item.title}</span>
            <span style={{ color: 'var(--muted)' }}>Description:</span><span>{item.description || '—'}</span>
            <span style={{ color: 'var(--muted)' }}>Category:</span><span>{item.category}</span>
            <span style={{ color: 'var(--muted)' }}>Subcategory:</span><span>{item.subcategory}</span>
            <span style={{ color: 'var(--muted)' }}>Brand:</span><span>{item.brand}</span>
            <span style={{ color: 'var(--muted)' }}>Price:</span><span>{item.price}</span>
            <span style={{ color: 'var(--muted)' }}>Quality:</span><span>{item.quality_score?.toFixed(4)}</span>
            <span style={{ color: 'var(--muted)' }}>Popularity:</span><span>{item.popularity_score?.toFixed(4)}</span>
            <span style={{ color: 'var(--muted)' }}>Cold Start:</span>
            <span>{item.is_cold_start ? <span className="badge badge-info">Yes</span> : 'No'}</span>
            <span style={{ color: 'var(--muted)' }}>Created:</span><span>{item.created_at || '—'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
