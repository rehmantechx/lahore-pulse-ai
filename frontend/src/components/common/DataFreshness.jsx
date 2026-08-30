/**
 * DataFreshness — Shows when data was last updated.
 *
 * Uses actual backend timestamps and the 4-state freshness model
 * (FRESH/DEGRADED/STALE/UNAVAILABLE) from the backend FreshnessService.
 * Never claims "Live" unless the system genuinely supports that claim.
 *
 * Accepts two prop modes:
 *   1. Legacy: timestamp + freshnessHours (backward compatible)
 *   2. Freshness-aware: freshness object from /forecast/status
 *      { state, freshness_hours, latest_observation_at, parameters_available, warnings }
 */

import { formatTimeAgo, formatDateTime } from '../../utils/format';

const FRESHNESS_STATE_CONFIG = {
  fresh: {
    label: 'Fresh',
    dotClass: 'status-dot--online',
    badgeBg: '#f0fdf4',
    badgeColor: '#16a34a',
    badgeBorder: '#bbf7d0',
  },
  degraded: {
    label: 'Degraded',
    dotClass: 'status-dot--online',
    badgeBg: '#fefce8',
    badgeColor: '#a16207',
    badgeBorder: '#fde68a',
  },
  stale: {
    label: 'Stale',
    dotClass: 'status-dot--offline',
    badgeBg: '#fefce8',
    badgeColor: '#854d0e',
    badgeBorder: '#fde68a',
  },
  unavailable: {
    label: 'Unavailable',
    dotClass: 'status-dot--offline',
    badgeBg: '#fef2f2',
    badgeColor: '#dc2626',
    badgeBorder: '#fecaca',
  },
};

function getFreshnessState(state, freshnessHours) {
  if (state && FRESHNESS_STATE_CONFIG[state]) return state;
  // Fallback for legacy mode (no state from backend)
  if (freshnessHours !== null && freshnessHours !== undefined) {
    if (freshnessHours <= 2) return 'fresh';
    if (freshnessHours <= 6) return 'degraded';
    if (freshnessHours <= 12) return 'stale';
    return 'unavailable';
  }
  return null;
}

/**
 * @param {object} props
 * @param {string|null} props.timestamp - ISO timestamp of most recent data
 * @param {number|null} props.freshnessHours - Hours since last observation
 * @param {object|null} props.freshness - Full freshness object from backend
 *   { state, freshness_hours, latest_observation_at, parameters_available, warnings }
 */
export default function DataFreshness({ timestamp, freshnessHours, freshness }) {
  // Extract values from freshness object if provided
  const state = freshness?.state || getFreshnessState(null, freshnessHours);
  const resolvedTimestamp = freshness?.latest_observation_at || timestamp;
  const resolvedHours = freshness?.freshness_hours ?? freshnessHours;
  const warnings = freshness?.warnings || [];

  if (!resolvedTimestamp && !state) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted" role="status" aria-label="Data freshness unknown">
        <span className="status-dot status-dot--offline" aria-hidden="true" />
        <span>Data freshness unknown</span>
      </div>
    );
  }

  const effectiveState = state || getFreshnessState(null, resolvedHours);
  const config = FRESHNESS_STATE_CONFIG[effectiveState] || FRESHNESS_STATE_CONFIG.unavailable;
  const dotClass = config.dotClass;
  const hoursText = resolvedHours !== null && resolvedHours !== undefined
    ? (Number.isFinite(resolvedHours) ? `${resolvedHours.toFixed(1)}h ago` : 'No data')
    : null;

  return (
    <div role="status" aria-label={`Data freshness: ${config.label}${resolvedTimestamp ? `, updated ${formatTimeAgo(resolvedTimestamp)}` : ''}`}>
      <div className="flex items-center gap-2 text-xs">
        <span className={`status-dot ${dotClass}`} aria-hidden="true" />
        {resolvedTimestamp ? (
          <>
            <span className="text-muted">
              Data updated {formatTimeAgo(resolvedTimestamp)}
            </span>
            <span className="text-muted" title={formatDateTime(resolvedTimestamp)}>
              ({formatDateTime(resolvedTimestamp)} PKT)
            </span>
          </>
        ) : (
          <span className="text-muted">No observation data available</span>
        )}
        <span
          className="badge"
          style={{
            background: config.badgeBg,
            color: config.badgeColor,
            border: `1px solid ${config.badgeBorder}`,
          }}
        >
          {config.label}
        </span>
        {hoursText && effectiveState !== 'fresh' && (
          <span className="text-muted" style={{ fontSize: '0.7rem' }}>
            ({hoursText})
          </span>
        )}
      </div>
      {warnings.length > 0 && (
        <div style={{ marginTop: 4, fontSize: '0.7rem', color: config.badgeColor }}>
          {warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}
      {(effectiveState === 'stale' || effectiveState === 'unavailable') && resolvedHours != null && (
        <div
          role="alert"
          style={{
            marginTop: 8,
            padding: '8px 12px',
            borderRadius: 'var(--lp-radius-md)',
            background: effectiveState === 'unavailable' ? 'var(--lp-red-50)' : 'var(--lp-amber-50)',
            border: `1px solid ${effectiveState === 'unavailable' ? 'var(--lp-red-200)' : 'var(--lp-amber-200)'}`,
            fontSize: 'var(--text-sm)',
            color: effectiveState === 'unavailable' ? 'var(--lp-red-700)' : 'var(--lp-amber-700)',
          }}
        >
          <strong>Data is {resolvedHours.toFixed(1)} hours old</strong> — air quality conditions may have changed since this reading.
          Please check back later or use the map for the most recent station data.
        </div>
      )}
    </div>
  );
}
