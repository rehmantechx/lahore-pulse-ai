/**
 * ForecastTrajectory — Compact 6-point forecast visualization.
 *
 * Shows NOW + 5 forecast horizons in a single horizontal bar.
 * Each point: PM2.5, severity color, direction indicator.
 *
 * Does NOT show algorithm names on every card.
 * Does NOT create fake confidence percentages.
 * Uses existing horizon reliability metadata.
 *
 * Safe language: "Highest forecast point: X at Yh"
 * only when data supports it.
 */

import { Circle, ArrowRight, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { HORIZONS, HORIZON_META, PM25_LEVELS } from '../../constants';

function getSeverityColor(pm25) {
  if (pm25 == null) return { color: '#94a3b8', bg: '#f1f5f9' };
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return { color: level.color, bg: level.bg };
  }
  return { color: '#7f1d1d', bg: '#fef2f2' };
}

function getSeverityLabel(pm25) {
  if (pm25 == null) return 'Unknown';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}

function getDirection(current, future) {
  if (current == null || future == null) return { symbol: '—', color: '#94a3b8', Icon: null };
  const diff = future - current;
  if (diff > 5) return { symbol: '↗', color: '#dc2626', Icon: ArrowUpRight };
  if (diff < -5) return { symbol: '↘', color: '#16a34a', Icon: ArrowDownRight };
  return { symbol: '→', color: '#a16207', Icon: ArrowRight };
}

function getConfidenceBadge(confidence) {
  const styles = {
    high: { bg: '#f0fdf4', color: '#166534', border: '#bbf7d0' },
    moderate: { bg: '#fefce8', color: '#854d0e', border: '#fde68a' },
    lower: { bg: '#fef2f2', color: '#991b1b', border: '#fecaca' },
  };
  return styles[confidence] || styles.moderate;
}

export default function ForecastTrajectory({ forecasts, selectedHorizon, onSelectHorizon }) {
  if (!forecasts) return null;

  const currentPM25 = forecasts['1']?.predicted_pm25;

  // Find highest forecast point
  let highestValue = null;
  let highestHorizon = null;
  for (const h of HORIZONS) {
    const val = forecasts[String(h)]?.predicted_pm25;
    if (val != null && (highestValue === null || val > highestValue)) {
      highestValue = val;
      highestHorizon = h;
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-header__title">Forecast Trajectory</h2>
        <span className="section-header__subtitle">
          {highestValue != null && highestHorizon != null && highestHorizon !== 1
            ? `Peak expected: ${getSeverityLabel(highestValue)} at +${HORIZON_META[highestHorizon].shortLabel}`
            : 'Air quality forecast across time horizons'}
        </span>
      </div>

      <div className="trajectory" role="group" aria-label="Forecast trajectory">
        {/* NOW point */}
        {(() => {
          const pm25 = currentPM25;
          const sev = getSeverityColor(pm25);
          return (
            <button
              className="trajectory__point trajectory__point--active"
              onClick={() => onSelectHorizon(1)}
              aria-label={`Now: ${pm25 != null ? pm25.toFixed(1) + ' micrograms per cubic meter' : 'no data'}`}
            >
              <span className="trajectory__label">Now</span>
              <span className="trajectory__value" style={{ color: sev.color }}>
                {pm25 != null ? pm25.toFixed(0) : '—'}
              </span>
              {pm25 != null && (
                <span className="trajectory__badge" style={{ background: sev.bg, color: sev.color }}>
                  {PM25_LEVELS.find(l => pm25 <= l.max)?.label || '—'}
                </span>
              )}
              <span className="trajectory__arrow" aria-hidden="true">
                <Circle size={12} fill={sev.color} color={sev.color} />
              </span>
            </button>
          );
        })()}

        {/* Forecast points */}
        {HORIZONS.map(h => {
          const f = forecasts[String(h)];
          const pm25 = f?.predicted_pm25;
          const meta = HORIZON_META[h];
          const sev = getSeverityColor(pm25);
          const dir = getDirection(currentPM25, pm25);
          const confStyle = getConfidenceBadge(meta.confidence);
          const isSelected = selectedHorizon === h;

          return (
            <button
              key={h}
              className={`trajectory__point ${isSelected ? 'trajectory__point--active' : ''}`}
              onClick={() => onSelectHorizon(h)}
              aria-label={`+${meta.shortLabel}: ${pm25 != null ? pm25.toFixed(1) + ' micrograms per cubic meter' : 'no data'}`}
              style={isSelected ? { background: 'var(--slate-100)', boxShadow: 'inset 0 -2px 0 var(--brand-600)' } : {}}
            >
              <span className="trajectory__label">+{meta.shortLabel}</span>
              <span className="trajectory__value" style={{ color: pm25 != null ? sev.color : '#94a3b8' }}>
                {pm25 != null ? pm25.toFixed(0) : '—'}
              </span>
              {pm25 != null && (
                <span className="trajectory__badge" style={{ background: sev.bg, color: sev.color }}>
                  {PM25_LEVELS.find(l => pm25 <= l.max)?.label || '—'}
                </span>
              )}
              <span className="trajectory__arrow" style={{ color: dir.color }} aria-hidden="true">
                {dir.Icon ? <dir.Icon size={14} /> : dir.symbol}
              </span>
              <span
                className="trajectory__badge"
                style={{ background: confStyle.bg, color: confStyle.color, border: `1px solid ${confStyle.border}` }}
              >
                {meta.confidence}
              </span>
            </button>
          );
        })}
      </div>

      {/* Compact selected horizon detail */}
      {selectedHorizon && forecasts[String(selectedHorizon)] && (() => {
        const f = forecasts[String(selectedHorizon)];
        const meta = HORIZON_META[selectedHorizon];
        return (
          <div className="narrative-block" style={{ marginTop: 'var(--sp-2)', fontSize: '11px', color: 'var(--slate-500)' }}>
            {meta.confidence === 'high' && 'Strong historical validation.'}
            {meta.confidence === 'moderate' && 'Moderate reliability, weather-driven variability increases.'}
            {meta.confidence === 'lower' && 'Greater uncertainty, useful for general trend only.'}
          </div>
        );
      })()}
    </div>
  );
}
