import { NavLink, Outlet } from 'react-router-dom';
import { BackendStatus } from './BackendStatus';

const NAV_ITEMS = [
  { to: '/search', label: 'Search' },
  { to: '/items', label: 'Items' },
  { to: '/users', label: 'Users' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/activity', label: 'Activity' },
  { to: '/system', label: 'System' },
];

export default function AppLayout() {
  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>PSR-SRS Enterprise</h1>
        <nav aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'active' : ''}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <BackendStatus />
      </header>
      <main>
        <Outlet />
      </main>
      <footer style={{ textAlign: 'center', padding: '20px 0', color: 'var(--muted)', fontSize: '13px', marginTop: 40, borderTop: '1px solid var(--border)' }}>
        PSR-SRS Enterprise v0.1.0
      </footer>
    </div>
  );
}
