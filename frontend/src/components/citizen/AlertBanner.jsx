/**
 * AlertBanner — Top-of-page visual alert for dangerous air quality.
 *
 * Appears at the very top of the homepage when PM2.5 exceeds thresholds.
 * Color-coded by severity. Dismissible (returns on page reload).
 * Shows: What, severity, guidance, and link to detailed info.
 *
 * CONSTRAINTS:
 *   - Visual-only alert (no push notifications)
 *   - Uses existing PM25_LEVELS for thresholds
 *   - Dismiss state stored in sessionStorage (resets on reload)
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { PM25_LEVELS } from '../../constants';

const ALERT_THRESHOLD = 45; // PM2.5 >= Moderate triggers alert

function getAlertLevel(pm25) {
  if (pm25 == null || isNaN(pm25) || pm25 < ALERT_THRESHOLD) return null;
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level;
  }
  return PM25_LEVELS[PM25_LEVELS.length - 1];
}

export default function AlertBanner({ pm25 }) {
  const [dismissed, setDismissed] = useState(false);
  const level = getAlertLevel(pm25);

  // Reset dismissed state when pm25 changes significantly (new event)
  useEffect(() => {
    setDismissed(false);
  }, [pm25 != null ? Math.floor(pm25 / 10) : null]);

  if (!level || dismissed) return null;

  const isSevere = pm25 >= 90; // Unhealthy or worse

  return (
    <div
      className={`alert-banner ${isSevere ? 'alert-banner--severe' : 'alert-banner--warning'}`}
      role="alert"
      aria-live="assertive"
      style={{
        '--alert-color': level.color,
        '--alert-bg': level.bg,
      }}
    >
      <div className="alert-banner__inner">
        <div className="alert-banner__icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>

        <div className="alert-banner__content">
          <div className="alert-banner__title">
            <span className="alert-banner__severity">{level.label}</span>
            <span className="alert-banner__reading">
              — Air Quality Level {Math.round(pm25)}
            </span>
          </div>
          <p className="alert-banner__guidance">{level.guidance}</p>
        </div>

        <div className="alert-banner__actions">
          <Link to="/air-quality" className="alert-banner__cta">
            Details
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </Link>
          <button
            className="alert-banner__dismiss"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss alert"
            type="button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
