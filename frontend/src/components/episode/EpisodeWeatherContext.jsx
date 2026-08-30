/**
 * EpisodeWeatherContext -- Weather context for episode detection.
 *
 * Shows individual weather variable comparisons against historical
 * episode profiles. Each variable is shown INDEPENDENTLY.
 *
 * IMPORTANT: Weather conditions show STATISTICAL ASSOCIATION,
 * NOT causation. This is clearly communicated in the UI.
 *
 * No composite weather score. No numeric confidence.
 */

/**
 * Single weather variable indicator.
 */
function WeatherVariable({ variable }) {
  const { label, current_value, episode_median, matches_pattern, direction, unit } = variable;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 0',
      borderBottom: '1px solid var(--slate-100)',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{
          fontSize: '13px',
          fontWeight: 500,
          color: 'var(--slate-700)',
        }}>
          {label}
        </div>
        <div style={{
          fontSize: '11px',
          color: 'var(--slate-400)',
        }}>
          Episodes: {episode_median} {unit} (median)
        </div>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        {current_value != null && (
          <span style={{
            fontSize: '14px',
            fontWeight: 600,
            color: 'var(--slate-700)',
          }}>
            {current_value.toFixed(1)} {unit}
          </span>
        )}

        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '12px',
          fontWeight: 500,
          padding: '2px 8px',
          borderRadius: 4,
          background: matches_pattern ? '#f0fdf4' : 'var(--slate-50)',
          color: matches_pattern ? '#166534' : 'var(--slate-500)',
          border: `1px solid ${matches_pattern ? '#bbf7d0' : 'var(--slate-200)'}`,
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: matches_pattern ? '#16a34a' : 'var(--slate-300)',
          }} />
          {matches_pattern ? `Typically ${direction} in episodes` : 'Within normal range'}
        </span>
      </div>
    </div>
  );
}

/**
 * Main EpisodeWeatherContext component.
 */
export default function EpisodeWeatherContext({ episode }) {
  if (!episode?.weather_context) return null;

  const { variables, note } = episode.weather_context;

  return (
    <div style={{
      border: '1px solid var(--slate-200)',
      borderRadius: 'var(--radius)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: 'var(--sp-3) var(--sp-4)',
        background: 'var(--slate-50)',
        borderBottom: '1px solid var(--slate-200)',
        fontSize: 'var(--text-sm)',
        fontWeight: 600,
        color: 'var(--slate-800)',
      }}>
        Weather Context
      </div>

      <div style={{ padding: 'var(--sp-4)' }}>
        {/* Individual variables */}
        {variables && variables.map((v, i) => (
          <WeatherVariable key={v.label || i} variable={v} />
        ))}

        {/* Summary note */}
        {note && (
          <div style={{
            marginTop: 'var(--sp-3)',
            fontSize: '13px',
            color: 'var(--slate-600)',
          }}>
            {note}
          </div>
        )}

        {/* Association caveat */}
        <div style={{
          marginTop: 'var(--sp-3)',
          padding: 'var(--sp-2) var(--sp-3)',
          background: 'var(--slate-50)',
          borderRadius: '6px',
          borderLeft: '3px solid var(--slate-200)',
          fontSize: '12px',
          color: 'var(--slate-400)',
          fontStyle: 'italic',
        }}>
          Weather conditions shown indicate statistical association with past episodes,
          not causal relationship. Current weather alone does not determine episode risk.
        </div>
      </div>
    </div>
  );
}
