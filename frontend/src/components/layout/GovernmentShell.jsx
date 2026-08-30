/**
 * GovernmentShell — Layout wrapper for government/command center routes.
 *
 * Structure: GlobalHeader (with GovernmentNav) → content
 * No footer — operational interface.
 * Uses Outlet pattern for react-router nested routes.
 *
 * In demo mode, shows a clear "DEMO ENVIRONMENT" indicator so the
 * audience understands the data is simulated. This is a security
 * boundary — demo mode never makes real backend API calls.
 */

import { Outlet, useLocation } from 'react-router-dom';
import GlobalHeader from './GlobalHeader.jsx';
import GovernmentNav from './GovernmentNav.jsx';
import PageTransition from '../common/PageTransition.jsx';
import { useDemoData } from '../../demo';

export default function GovernmentShell() {
  const location = useLocation();
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const demoStep = isDemo ? (demoData.demoStep || 1) : null;

  return (
    <div className="app app--government">
      <a href="#main-content" className="skip-link">Skip to content</a>

      {/* Demo environment banner */}
      {isDemo && (
        <div
          className="demo-env-banner"
          role="status"
          aria-label="Demo mode active"
          data-testid="demo-env-banner"
          style={{
            background: 'linear-gradient(90deg, #0f172a 0%, #1e293b 100%)',
            color: '#94a3b8',
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            textAlign: 'center',
            padding: '4px var(--sp-4)',
            borderBottom: '1px solid #334155',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--sp-2)',
          }}
        >
          <span style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#facc15',
            animation: 'lp-status-pulse 2s ease-in-out infinite',
          }} aria-hidden="true" />
          <span>DEMO ENVIRONMENT</span>
          <span style={{ color: '#64748b', fontWeight: 400 }}>—</span>
          <span style={{ color: '#64748b', fontWeight: 400 }}>
            Step {demoStep} of {demoData.demoStep != null ? 7 : '—'} · Simulated data · No backend calls
          </span>
        </div>
      )}

      <GlobalHeader mode="government">
        <GovernmentNav />
      </GlobalHeader>
      <main id="main-content" className="app-content" role="main" tabIndex={-1}>
        <PageTransition key={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  );
}
