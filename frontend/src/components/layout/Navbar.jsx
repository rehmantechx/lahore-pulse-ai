/**
 * Navbar — Application header with product identity, navigation,
 * connection status, and data freshness.
 *
 * Compact, professional — not a marketing header.
 */

import { NavLink } from 'react-router-dom';
import { useHealth } from '../../hooks/useHealth';
import { formatTimeAgo } from '../../utils/format';

export default function Navbar({ lastFetchTime }) {
  const { online, loading } = useHealth();

  return (
    <header className="app-header" role="banner">
      <div className="app-header__brand">
        <span className="app-header__brand-icon" aria-hidden="true">LP</span>
        <span>Lahore Pulse</span>
      </div>

      <nav className="app-header__nav" role="navigation" aria-label="Main navigation">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `app-header__link ${isActive ? 'app-header__link--active' : ''}`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/citizen"
          className={({ isActive }) =>
            `app-header__link ${isActive ? 'app-header__link--active' : ''}`
          }
        >
          Citizen
        </NavLink>
        <NavLink
          to="/government"
          className={({ isActive }) =>
            `app-header__link ${isActive ? 'app-header__link--active' : ''}`
          }
        >
          {({ isActive }) => (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <span aria-hidden="true" style={{ fontSize: '0.7em', color: isActive ? '#16a34a' : undefined }}>■</span>
              Command Center
            </span>
          )}
        </NavLink>
        <NavLink
          to="/replay"
          className={({ isActive }) =>
            `app-header__link ${isActive ? 'app-header__link--active' : ''}`
          }
        >
          Replay
        </NavLink>
      </nav>

      <div className="app-header__status" aria-label="System status">
        <span
          className={`status-dot ${loading ? 'status-dot--loading' : online ? 'status-dot--online' : 'status-dot--offline'}`}
          aria-hidden="true"
        />

        {lastFetchTime && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>
            Updated {formatTimeAgo(lastFetchTime.toISOString())}
          </span>
        )}
      </div>
    </header>
  );
}
