/**
 * GovernmentNav — Navigation for government/command center routes.
 *
 * 6 items: Overview, Incidents, Forecasts, Analytics, System, Replay
 *
 * In demo mode:
 * - Shows "GUIDED DEMO — Step N of 7" indicator
 * - Navigation links are visually dimmed (not broken-looking) during demo
 * - Step indicator uses the same label from the state machine
 */

import { NavLink } from 'react-router-dom';
import { useDemoData } from '../../demo';
import { getStep } from '../../demo/stateMachine';

const NAV_ITEMS = [
  {
    to: '/government',
    label: 'Overview',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
      </svg>
    ),
  },
  {
    to: '/government/incidents',
    label: 'Incidents',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
  },
  {
    to: '/government/forecasts',
    label: 'Forecasts',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    to: '/government/analytics',
    label: 'Analytics',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },

  {
    to: '/government/system',
    label: 'System',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
  {
    to: '/government/replay',
    label: 'Replay',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="5 3 19 12 5 21 5 3" />
      </svg>
    ),
  },
];

export default function GovernmentNav() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const demoStep = isDemo ? (demoData.demoStep || 1) : null;
  const stepConfig = isDemo ? getStep(demoStep) : null;

  return (
    <div className={`gov-nav ${isDemo ? 'gov-nav--demo' : ''}`}>
      {/* Demo step indicator — compact pill */}
      {isDemo && stepConfig && (
        <div
          className="gov-nav__demo-indicator"
          data-testid="demo-step-indicator"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 10px',
            marginRight: 'var(--sp-2)',
            background: 'rgba(20, 184, 166, 0.08)',
            border: '1px solid rgba(20, 184, 166, 0.15)',
            borderRadius: '999px',
            flexShrink: 0,
          }}
        >
          <span style={{
            fontSize: '9px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: '#0f8b7d',
            whiteSpace: 'nowrap',
          }}>
            DEMO — Step {demoStep}/7
          </span>
        </div>
      )}

      {NAV_ITEMS.map((item) => {
        const isDisabled = isDemo && item.to !== '/government';
        return (
          <NavLink
            key={item.to}
            to={isDisabled ? '#' : item.to}
            end={item.to === '/government'}
            className={({ isActive }) =>
              `gov-nav__link ${isActive ? 'gov-nav__link--active' : ''} ${isDisabled ? 'gov-nav__link--disabled' : ''}`
            }
            aria-disabled={isDisabled}
            onClick={isDisabled ? (e) => e.preventDefault() : undefined}
          >
            <span className="gov-nav__icon">{item.icon}</span>
            <span className="gov-nav__label">{item.label}</span>
          </NavLink>
        );
      })}
    </div>
  );
}
