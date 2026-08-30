/**
 * ForecastCard — Displays a single-horizon prediction.
 *
 * Shows: horizon label, predicted value, severity badge, confidence.
 * Does NOT show algorithm name on every card.
 * Subtle visual hierarchy: 1h = high reliability, 6h = moderate, 12h/24h = greater uncertainty.
 */

import { HORIZON_META } from '../../constants';
import { formatPM25, formatTime } from '../../utils/format';
import SeverityBadge from '../common/SeverityBadge';

/**
 * @param {object} props
 * @param {number} props.horizon - Forecast horizon in hours
 * @param {object|null} props.forecast - Forecast data from API, or null
 * @param {boolean} props.isSelected - Currently selected horizon
 * @param {Function} props.onSelect - Click handler
 */
export default function ForecastCard({ horizon, forecast, isSelected, onSelect }) {
  const meta = HORIZON_META[horizon];

  if (!forecast) {
    return (
      <button
        className={`forecast-card ${isSelected ? 'forecast-card--selected' : ''}`}
        onClick={() => onSelect(horizon)}
        aria-label={`${meta.label} forecast — no data available`}
        aria-pressed={isSelected}
        style={{ opacity: 0.5 }}
      >
        <span className="forecast-card__horizon">{meta.shortLabel}</span>
        <span className="forecast-card__value" style={{ color: 'var(--slate-400)' }}>—</span>
        <span className="forecast-card__label" style={{ color: 'var(--slate-400)' }}>No data</span>
      </button>
    );
  }

  const isError = forecast.errors && forecast.errors.length > 0;
  const pm25 = forecast.predicted_pm25;

  // Subtle confidence hierarchy via opacity
  const confOpacity = meta.confidence === 'high' ? 1 : meta.confidence === 'moderate' ? 0.95 : 0.85;

  return (
    <button
      className={`forecast-card ${isSelected ? 'forecast-card--selected' : ''}`}
      onClick={() => onSelect(horizon)}
      aria-label={`${meta.label} forecast: ${pm25 != null ? `${pm25.toFixed(1)} micrograms per cubic meter` : 'unavailable'}`}
      aria-pressed={isSelected}
      style={{ opacity: confOpacity }}
    >
      <span className="forecast-card__horizon">{meta.shortLabel}</span>

      {isError ? (
        <span className="forecast-card__value" style={{ color: 'var(--red-600)', fontSize: 'var(--text-lg)' }}>
          Unavailable
        </span>
      ) : (
        <>
          <span className="forecast-card__value">
            {pm25 !== null ? pm25.toFixed(1) : '—'}
            {pm25 !== null && <span className="forecast-card__unit"> μg/m³</span>}
          </span>
          <SeverityBadge value={pm25} size="sm" />
        </>
      )}

      <span className="forecast-card__meta">
        {meta.confidence === 'high' && 'Strong historical validation'}
        {meta.confidence === 'moderate' && 'Moderate reliability'}
        {meta.confidence === 'lower' && 'Greater uncertainty'}
      </span>

      {forecast.timing?.target_time && (
        <span className="forecast-card__time">
          Target: {formatTime(forecast.timing.target_time)} PKT
        </span>
      )}
    </button>
  );
}
