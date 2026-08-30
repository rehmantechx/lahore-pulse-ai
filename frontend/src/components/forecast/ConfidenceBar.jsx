/**
 * ConfidenceBar — Visual uncertainty display for forecasts.
 *
 * Shows:
 * 1. PM2.5 value as a horizontal bar with estimated uncertainty range
 *    (derived from MAE: Mean Absolute Error per horizon)
 * 2. Confidence labels (High/Moderate/Lower) prominently displayed
 * 3. Clear distinction between measured vs predicted values
 * 4. "Based on 45km grid data — your neighborhood may differ" disclaimer
 *
 * Does NOT create fake confidence percentages.
 * Uses existing HORIZON_META validation metrics (MAE, R²) honestly.
 */

import { HORIZONS, HORIZON_META, PM25_LEVELS } from '../../constants';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

function getSeverityColor(pm25) {
  if (pm25 == null) return '#94a3b8';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.color;
  }
  return '#7f1d1d';
}

function getSeverityLabel(pm25) {
  if (pm25 == null) return 'Unknown';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}

function getConfidenceStyles(confidence) {
  switch (confidence) {
    case 'high':
      return {
        bg: '#f0fdf4', color: '#166534', border: '#bbf7d0',
        label: 'High confidence',
        description: 'Strong historical validation',
      };
    case 'moderate':
      return {
        bg: '#fefce8', color: '#854d0e', border: '#fde68a',
        label: 'Moderate confidence',
        description: 'Weather-driven variability increases',
      };
    case 'lower':
      return {
        bg: '#fef2f2', color: '#991b1b', border: '#fecaca',
        label: 'Lower confidence',
        description: 'Greater uncertainty — general trend only',
      };
    default:
      return {
        bg: '#f1f5f9', color: '#64748b', border: '#e2e8f0',
        label: 'Unknown',
        description: '',
      };
  }
}

/**
 * @param {object} props
 * @param {object} props.forecasts - Forecast data keyed by horizon number
 * @param {number|null} props.currentPM25 - Current measured PM2.5 value (from observation, not prediction)
 */
export default function ConfidenceBar({ forecasts, currentPM25 }) {
  if (!forecasts) return null;

  const values = HORIZONS
    .filter(h => forecasts[String(h)]?.predicted_pm25 != null)
    .map(h => ({
      horizon: h,
      pm25: forecasts[String(h)].predicted_pm25,
      meta: HORIZON_META[h],
      isCurrent: h === 1,
    }));

  if (values.length === 0) return null;

  // Calculate chart scale
  const allPM25 = values.map(v => v.pm25);
  if (currentPM25 != null) allPM25.push(currentPM25);
  const maxPM25 = Math.max(...allPM25);
  const minPM25 = 0;
  const range = Math.max(maxPM25 * 1.1, 100); // At least show 0-100

  return (
    <div className="confidence-bar" role="region" aria-label="Forecast confidence display">
      <div className="section-header">
        <h2 className="section-header__title">Forecast with Confidence</h2>
        <span className="section-header__subtitle">
          Uncertainty grows with forecast horizon
        </span>
      </div>

      {/* Visual bar chart */}
      <div
        className="card"
        style={{
          padding: 'var(--sp-4) var(--sp-5)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--sp-3)',
        }}
      >
        {values.map(({ horizon, pm25, meta, isCurrent }) => {
          const color = getSeverityColor(pm25);
          const sevLabel = getSeverityLabel(pm25);
          const confStyles = getConfidenceStyles(meta.confidence);
          const mae = meta.valMAE;
          const barWidth = Math.min((pm25 / range) * 100, 100);
          const uncertaintyWidth = Math.min((mae / range) * 100, 30);
          const leftOffset = Math.max(0, barWidth - uncertaintyWidth);
          const totalWidth = Math.min(barWidth + uncertaintyWidth, 100);

          return (
            <div
              key={horizon}
              style={{
                display: 'grid',
                gridTemplateColumns: '50px 1fr auto',
                alignItems: 'center',
                gap: 'var(--sp-3)',
                padding: isCurrent ? 'var(--sp-2)' : 0,
                background: isCurrent ? 'var(--lp-brand-50)' : 'transparent',
                borderRadius: isCurrent ? 'var(--lp-radius-md)' : 0,
              }}
            >
              {/* Horizon label */}
              <div style={{ textAlign: 'right' }}>
                <span style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: isCurrent ? 600 : 400,
                  color: isCurrent ? 'var(--brand-600)' : 'var(--lp-text-secondary)',
                }}>
                  {isCurrent ? 'Now' : `+${meta.shortLabel}`}
                </span>
              </div>

              {/* Bar */}
              <div style={{ position: 'relative', height: 20 }}>
                {/* Uncertainty range (lighter background) */}
                <div style={{
                  position: 'absolute',
                  left: `${leftOffset}%`,
                  width: `${totalWidth}%`,
                  height: '100%',
                  background: `${color}22`,
                  borderRadius: 'var(--lp-radius-sm)',
                }} />

                {/* Core value bar */}
                <div style={{
                  position: 'absolute',
                  left: 0,
                  width: `${barWidth}%`,
                  height: '100%',
                  background: color,
                  borderRadius: 'var(--lp-radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: 'var(--sp-2)',
                  transition: 'width 300ms ease',
                }}>
                  <span style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#fff',
                    whiteSpace: 'nowrap',
                    textShadow: '0 1px 2px rgba(0,0,0,0.2)',
                  }}>
                    {pm25.toFixed(0)}
                  </span>
                </div>
              </div>

              {/* Confidence badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                <span style={{
                  fontSize: 10,
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: 10,
                  background: confStyles.bg,
                  color: confStyles.color,
                  border: `1px solid ${confStyles.border}`,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  whiteSpace: 'nowrap',
                }}>
                  {meta.confidence}
                </span>
                <span style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--lp-text-muted)',
                  whiteSpace: 'nowrap',
                }}>
                  ±{mae.toFixed(0)} margin
                </span>
              </div>
            </div>
          );
        })}

        {/* Uncertainty legend */}
        <div style={{
          marginTop: 'var(--sp-2)',
          paddingTop: 'var(--sp-3)',
          borderTop: '1px solid var(--lp-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--sp-3)',
          fontSize: 'var(--text-xs)',
          color: 'var(--lp-text-muted)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
            <div style={{ width: 12, height: 8, background: '#94a3b8', borderRadius: 2 }} />
            <span>Predicted value</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
            <div style={{ width: 12, height: 8, background: '#94a3b822', borderRadius: 2 }} />
            <span>Uncertainty range (±MAE)</span>
          </div>
        </div>
      </div>

      {/* Confidence explanation */}
      <div style={{
        marginTop: 'var(--sp-3)',
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 'var(--sp-2)',
      }}>
        {['high', 'moderate', 'lower'].map(conf => {
          const styles = getConfidenceStyles(conf);
          const meta = Object.values(HORIZON_META).find(m => m.confidence === conf);
          return (
            <div
              key={conf}
              style={{
                padding: 'var(--sp-3)',
                background: styles.bg,
                border: `1px solid ${styles.border}`,
                borderRadius: 'var(--lp-radius-md)',
                fontSize: 'var(--text-xs)',
              }}
            >
              <div style={{ fontWeight: 600, color: styles.color, marginBottom: 2 }}>
                {styles.label}
              </div>
              <div style={{ color: styles.color, opacity: 0.8 }}>
                {meta?.label || 'N/A'} — {styles.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* Grid resolution disclaimer */}
      <div style={{
        marginTop: 'var(--sp-3)',
        padding: 'var(--sp-2) var(--sp-3)',
        background: 'var(--lp-surface-elevated)',
        borderRadius: 'var(--lp-radius-md)',
        fontSize: 'var(--text-xs)',
        color: 'var(--lp-text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--sp-2)',
      }}>
        <AlertTriangle size={12} />
        <span>
          Based on ~45km grid resolution data (CAMS Copernicus).
          Your neighborhood conditions may differ from the regional average.
          Longer forecasts are less precise — use for general trend only.
        </span>
      </div>
    </div>
  );
}
