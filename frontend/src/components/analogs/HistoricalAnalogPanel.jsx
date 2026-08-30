/**
 * HistoricalAnalogPanel — "Have we seen this before?"
 *
 * Shows top 3 historical episodes with similar meteorological conditions.
 * Each card explains WHY it was selected and what happened next.
 * Links to existing Historical Replay for full episode playback.
 *
 * All data is real. No fabrication. No predictive claims.
 */

import { useNavigate } from 'react-router-dom';

/** Format a date string as short label. */
function fmtDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/** Color for similarity label. */
function matchColor(label) {
  if (label === 'Closest match') return { bg: '#ecfdf5', fg: '#166534' };
  if (label === 'Strong match') return { bg: '#f0f9ff', fg: '#075985' };
  if (label === 'Moderate match') return { bg: '#fffbeb', fg: '#92400e' };
  return { bg: '#f8fafc', fg: '#64748b' };
}

/** PM2.5 severity label. */
function pm25Label(val) {
  if (val <= 12) return 'Good';
  if (val <= 25) return 'Fair';
  if (val <= 45) return 'Moderate';
  if (val <= 90) return 'Unhealthy for Sensitive';
  if (val <= 150) return 'Very Unhealthy';
  return 'Hazardous';
}

function AnalogCard({ analog, onReplay }) {
  const mc = matchColor(analog.similarity_label);
  const similar = (analog.similarity_factors || []).filter(f => f.matches);
  const different = (analog.similarity_factors || []).filter(f => !f.matches);

  return (
    <div className="ha-card">
      {/* Header */}
      <div className="ha-card__header">
        <span className="ha-card__date">{fmtDate(analog.date)}</span>
        <span
          className="ha-card__badge"
          style={{ background: mc.bg, color: mc.fg }}
        >
          {analog.similarity_label}
        </span>
      </div>

      {/* Key stats */}
      <div className="ha-card__stats">
        <div className="ha-card__stat">
          <span className="ha-card__stat-value" style={{ color: analog.peak_pm25 > 150 ? 'var(--red-700, #b91c1c)' : 'var(--slate-900, #0f172a)' }}>
            {Math.round(analog.peak_pm25)}
          </span>
          <span className="ha-card__stat-unit">ug/m3 peak</span>
        </div>
        <div className="ha-card__stat">
          <span className="ha-card__stat-value">{analog.duration_hours}h</span>
          <span className="ha-card__stat-unit">recorded</span>
        </div>
      </div>

      {/* Similarity factors */}
      {similar.length > 0 && (
        <div className="ha-card__section">
          <div className="ha-card__section-label">Similar:</div>
          {similar.map((f, i) => (
            <div key={i} className="ha-card__factor ha-card__factor--match">
              <span className="ha-card__check">&#10003;</span>
              <span>{f.label}</span>
            </div>
          ))}
        </div>
      )}

      {different.length > 0 && (
        <div className="ha-card__section">
          <div className="ha-card__section-label">Different:</div>
          {different.slice(0, 2).map((f, i) => (
            <div key={i} className="ha-card__factor ha-card__factor--diff">
              <span className="ha-card__delta">&#9651;</span>
              <span>{f.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* What happened next */}
      {analog.what_happened_next && (
        <div className="ha-card__outcome">
          <div className="ha-card__section-label">What happened next:</div>
          <div className="ha-card__outcome-text">
            {analog.what_happened_next.summary}
          </div>
        </div>
      )}

      {/* Replay button */}
      <button
        className="ha-card__replay"
        onClick={() => onReplay(analog)}
      >
        REPLAY EPISODE &rarr;
      </button>
    </div>
  );
}

/**
 * HistoricalAnalogPanel — main component.
 *
 * @param {object} props
 * @param {object|null} props.analogs - Analog response from API
 * @param {boolean} props.loading - Loading state
 * @param {Error|null} props.error - Error state
 */
export default function HistoricalAnalogPanel({ analogs, loading, error }) {
  const navigate = useNavigate();

  const handleReplay = (analog) => {
    navigate(`/replay?date=${analog.date}`);
  };

  if (loading) {
    return (
      <div className="ha-panel">
        <div className="ha-panel__header">
          <h3 className="ha-panel__title">Similar Historical Episodes</h3>
          <p className="ha-panel__subtitle">Searching historical records...</p>
        </div>
        <div className="ha-panel__loading">Loading analog episodes...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ha-panel">
        <div className="ha-panel__header">
          <h3 className="ha-panel__title">Similar Historical Episodes</h3>
          <p className="ha-panel__subtitle" style={{ color: 'var(--red-600, #dc2626)' }}>
            Unable to load analog episodes
          </p>
        </div>
      </div>
    );
  }

  const items = analogs?.analogs || [];

  if (items.length === 0) {
    return (
      <div className="ha-panel">
        <div className="ha-panel__header">
          <h3 className="ha-panel__title">Similar Historical Episodes</h3>
          <p className="ha-panel__subtitle">
            No closely matching historical episodes found for current conditions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="ha-panel">
      <div className="ha-panel__header">
        <h3 className="ha-panel__title">Similar Historical Episodes</h3>
        <p className="ha-panel__subtitle">
          This incident resembles {items.length} previous Lahore pollution event{items.length !== 1 ? 's' : ''}.
        </p>
      </div>

      <div className="ha-panel__grid">
        {items.map((analog, i) => (
          <AnalogCard
            key={analog.date || i}
            analog={analog}
            onReplay={handleReplay}
          />
        ))}
      </div>

      {/* Caveat */}
      <div className="ha-panel__caveat">
        {analogs?.caveat || 'Historical analogs describe similarity to past observations. They are not guarantees about the current event.'}
      </div>
    </div>
  );
}
