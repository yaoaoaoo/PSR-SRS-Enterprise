import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="empty-state" style={{ padding: '80px 16px' }}>
      <h2 style={{ fontSize: 48, color: 'var(--muted)', marginBottom: 8 }}>404</h2>
      <p>Page not found.</p>
      <p style={{ marginTop: 16 }}>
        <Link to="/search">Go to Search</Link>
      </p>
    </div>
  );
}
