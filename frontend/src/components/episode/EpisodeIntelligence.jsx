/**
 * EpisodeIntelligence -- Main episode intelligence display component.
 *
 * Displays rule-based episode detection results, trajectory,
 * weather context, and narrative. This is NOT machine learning --
 * it is rule-based detection using ML forecasts as one input.
 *
 * Design principles:
 * - Show what the rules decided, not a black-box score
 * - All numbers are from the backend; no client-side calculation
 * - Standard caveats displayed prominently
 */

import { PM25_LEVELS } from '../../constants';

/**
 * Get severity color for a PM2.5 value.
 */
function getSeverityColor(pm25) {
  if (pm25 == null) return { color: '#64748b', bg: '#f8fafc', label: 'Unknown' };
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) {
      return { color: level.color, bg: level.bg, label: level.label };
    }
  }
  return { color: PM25_LEVELS[PM25_LEVELS.length - 1].color, bg: PM25_LEVELS[PM25_LEVELS.length - 1].bg, label: 'Hazardous' };
}

/**
 * State badge component.
 */
function StateBadge({ state, description }) {
  const stateStyles = {
    normal: { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', label: 'No Episode' },
    episode: { color: '#dc2626', bg: '#fef2f2', border: '#fecaca', label: 'Episode Active' },
    improving: { color: '#a16207', bg: '#fefce8', border: '#fde68a', label: 'Improving' },
    uncertain: { color: '#64748b', bg: '#f8fafc', border: '#e2e8f0', label: 'Uncertain' },
  };
  const s = stateStyles[state] || stateStyles.uncertain;

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      padding: '6px 14px',
      borderRadius: '8px',
      background: s.bg,
      border: `1px solid ${s.border}`,
      fontSize: '14px',
      fontWeight: 600,
      color: s.color,
    }}>
      <span style={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: s.color,
        flexShrink: 0,
      }} />
      {s.label}
    </div>
  );
}

/**
 * Data status indicator.
 */
function DataStatus({ dataStatus, freshnessHours }) {
  const statusStyles = {
    fresh: { color: '#16a34a', label: 'Data Fresh' },
    degraded: { color: '#a16207', label: 'Data Degraded' },
    stale: { color: '#dc2626', label: 'Data Stale' },
    unavailable: { color: '#64748b', label: 'Data Unavailable' },
    unknown: { color: '#64748b', label: 'Unknown' },
  };
  const s = statusStyles[dataStatus] || statusStyles.unknown;
  const freshnessText = freshnessHours != null ? ` (${freshnessHours}h ago)` : '';

  return (
    <span style={{
      fontSize: '12px',
      color: s.color,
      fontWeight: 500,
    }}>
      {s.label}{freshnessText}
    </span>
  );
}

/**
 * Main EpisodeIntelligence component.
 */
export default function EpisodeIntelligence({ episode }) {
  if (!episode) return null;

  const severity = getSeverityColor(episode.current_pm25);

  return (
    <div style={{
      border: '1px solid var(--slate-200)',
      borderRadius: 'var(--radius)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--sp-3) var(--sp-4)',
        background: episode.state === 'episode' ? '#fef2f2' : episode.state === 'improving' ? '#fefce8' : '#f8fafc',
        borderBottom: '1px solid var(--slate-200)',
        flexWrap: 'wrap',
        gap: '8px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
          <StateBadge state={episode.state} description={episode.state_description} />
        </div>
        <DataStatus dataStatus={episode.data_status} freshnessHours={episode.freshness_hours} />
      </div>

      {/* Current conditions */}
      <div style={{ padding: 'var(--sp-4)' }}>
        {episode.current_pm25 != null && (
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 'var(--sp-3)',
            marginBottom: 'var(--sp-3)',
          }}>
            <span style={{
              fontSize: '32px',
              fontWeight: 700,
              color: severity.color,
              lineHeight: 1,
            }}>
              {Math.round(episode.current_pm25)}
            </span>
            <span style={{ fontSize: '14px', color: 'var(--slate-500)' }}>
              ug/m3
            </span>
            <span style={{
              fontSize: '12px',
              fontWeight: 500,
              color: severity.color,
              background: severity.bg,
              padding: '2px 8px',
              borderRadius: 4,
            }}>
              {severity.label}
            </span>
          </div>
        )}

        {episode.current_6h_delta != null && (
          <div style={{
            fontSize: '13px',
            color: 'var(--slate-600)',
            marginBottom: 'var(--sp-3)',
          }}>
            6h change: {episode.current_6h_delta > 0 ? '+' : ''}{Math.round(episode.current_6h_delta)} ug/m3
          </div>
        )}

        {/* Narrative */}
        {episode.narrative && (
          <div style={{
            fontSize: '14px',
            lineHeight: 1.6,
            color: 'var(--slate-700)',
            marginBottom: 'var(--sp-3)',
          }}>
            {episode.narrative}
          </div>
        )}

        {/* Caveat */}
        {episode.narrative_caveat && (
          <div style={{
            fontSize: '12px',
            color: 'var(--slate-400)',
            fontStyle: 'italic',
            padding: 'var(--sp-2) var(--sp-3)',
            background: 'var(--slate-50)',
            borderRadius: '6px',
            borderLeft: '3px solid var(--slate-200)',
          }}>
            {episode.narrative_caveat}
          </div>
        )}

        {/* Warnings */}
        {episode.warnings && episode.warnings.length > 0 && (
          <div style={{
            marginTop: 'var(--sp-3)',
            padding: 'var(--sp-2) var(--sp-3)',
            background: '#fefce8',
            borderRadius: '6px',
            borderLeft: '3px solid #ca8a04',
            fontSize: '12px',
            color: '#854d0e',
          }}>
            {episode.warnings.map((w, i) => (
              <div key={i}>{w}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
