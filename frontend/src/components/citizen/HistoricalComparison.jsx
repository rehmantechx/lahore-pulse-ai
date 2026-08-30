/**
 * HistoricalComparison — "How does today compare?"
 *
 * Citizen-facing panel showing historical context for current air quality.
 * Simplified version of operator analog panel — focuses on outcomes.
 *
 * Shows:
 * - "Last time conditions were this bad..." with outcome
 * - Simple comparison: similar date, similar severity, what happened
 * - Only visible when analog matches exist
 *
 * CONSTRAINTS:
 *   - Only shows data when analogs exist — never fabricates
 *   - Plain language, no technical jargon
 *   - Links to detailed replay for citizens who want more
 */

import { Link } from 'react-router-dom';

function fmtDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function ComparisonCard({ analog }) {
  const peak = Math.round(analog.peak_pm25);
  const duration = analog.duration_hours;
  const outcome = analog.what_happened_next?.summary || 'No outcome data available.';

  return (
    <div className="hc-card">
      <div className="hc-card__header">
        <span className="hc-card__date">{fmtDate(analog.date)}</span>
        <span className="hc-card__badge" style={{
          background: analog.similarity_label === 'Closest match' ? '#ecfdf5'
            : analog.similarity_label === 'Strong match' ? '#f0f9ff' : '#fffbeb',
          color: analog.similarity_label === 'Closest match' ? '#166534'
            : analog.similarity_label === 'Strong match' ? '#075985' : '#92400e',
        }}>
          {analog.similarity_label}
        </span>
      </div>

      <div className="hc-card__stats">
        <div className="hc-card__stat">
          <span className="hc-card__stat-value">{peak}</span>
          <span className="hc-card__stat-label">peak μg/m³</span>
        </div>
        <div className="hc-card__stat">
          <span className="hc-card__stat-value">{duration}h</span>
          <span className="hc-card__stat-label">duration</span>
        </div>
      </div>

      <p className="hc-card__outcome">{outcome}</p>

      <Link to={`/replay?date=${analog.date}`} className="hc-card__link">
        View full timeline
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </Link>
    </div>
  );
}

export default function HistoricalComparison({ analogs, loading }) {
  if (loading) {
    return (
      <section className="gov-section" aria-label="Historical comparison">
        <div className="gov-section__header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <h2 className="gov-section__title">How Does Today Compare?</h2>
        </div>
        <div className="hc-loading">Searching historical records...</div>
      </section>
    );
  }

  const items = analogs?.analogs || [];
  if (items.length === 0) return null;

  const closest = items[0];

  return (
    <section className="gov-section" aria-label="Historical comparison">
      <div className="gov-section__header">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <h2 className="gov-section__title">How Does Today Compare?</h2>
        <span className="gov-section__count">
          {items.length} similar episode{items.length !== 1 ? 's' : ''} found
        </span>
      </div>

      <div className="hc-intro">
        <p>
          Last time conditions were similar (peak {Math.round(closest.peak_pm25)} μg/m³),
          the episode lasted about {closest.duration_hours} hours.
        </p>
      </div>

      <div className="hc-grid">
        {items.map((analog, i) => (
          <ComparisonCard key={analog.date || i} analog={analog} />
        ))}
      </div>
    </section>
  );
}
