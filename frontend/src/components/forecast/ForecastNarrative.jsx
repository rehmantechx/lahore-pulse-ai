/**
 * ForecastNarrative — Two-layer forecast explanation.
 *
 * Citizen layer: "Air quality is expected to improve over the next 6 hours.
 * By evening, conditions should drop to moderate levels. Outdoor activity
 * may become safer later today."
 *
 * Detail layer (expandable): Model info, confidence, validation metrics,
 * data sources, and grid resolution disclaimer.
 *
 * Safe language principles:
 * - Always use "expected to" / "should" — never "will"
 * - Qualify with "based on available data" for longer horizons
 * - Never show fake confidence percentages
 * - Distinguish measured from predicted values
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, TrendingDown, TrendingUp, Minus, Info } from 'lucide-react';
import { HORIZONS, HORIZON_META, PM25_LEVELS } from '../../constants';

function getSeverityLabel(pm25) {
  if (pm25 == null) return null;
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}

function getPlainLanguageSummary(forecasts) {
  if (!forecasts) return null;

  const currentPM25 = forecasts['1']?.predicted_pm25;
  if (currentPM25 == null) return null;

  const currentLabel = getSeverityLabel(currentPM25);

  // Get key forecast points
  const h3 = forecasts['3']?.predicted_pm25;
  const h6 = forecasts['6']?.predicted_pm25;
  const h12 = forecasts['12']?.predicted_pm25;
  const h24 = forecasts['24']?.predicted_pm25;

  // Overall trend
  const recentTrend = h6 != null ? h6 - currentPM25 : null;
  const longerTrend = h24 != null ? h24 - currentPM25 : null;

  // Find peak
  const allValues = [currentPM25, h3, h6, h12, h24].filter(v => v != null);
  const peakValue = Math.max(...allValues);
  const peakHorizon = [1, 3, 6, 12, 24][allValues.indexOf(peakValue)];

  // Find lowest
  const lowValue = Math.min(...allValues);
  const lowHorizon = [1, 3, 6, 12, 24][allValues.indexOf(lowValue)];

  // Determine if improving or worsening
  let trend;
  if (recentTrend != null) {
    if (recentTrend < -8) trend = 'improving';
    else if (recentTrend > 8) trend = 'worsening';
    else trend = 'stable';
  } else {
    trend = 'unknown';
  }

  // Determine severity transition
  const currentSev = getSeverityLabel(currentPM25);
  const h6Sev = h6 != null ? getSeverityLabel(h6) : null;
  const h24Sev = h24 != null ? getSeverityLabel(h24) : null;

  // Build summary parts
  const parts = [];

  // Opening: current state
  parts.push(
    `Air quality is currently ${currentSev?.toLowerCase() || 'unknown'} in Lahore.`
  );

  // Middle: trend direction
  if (trend === 'improving') {
    parts.push(
      `Conditions are expected to improve over the coming hours.`
    );
    if (h6 != null && h6 < currentPM25) {
      const h6Label = getSeverityLabel(h6);
      if (h6Label !== currentSev) {
        parts.push(
          `By ${peakHorizon <= 6 ? 'later today' : 'the next several hours'}, ` +
          `air quality should reach ${h6Label?.toLowerCase()} levels.`
        );
      }
    }
  } else if (trend === 'worsening') {
    parts.push(
      `Conditions are expected to worsen over the coming hours.`
    );
    if (peakValue > currentPM25 + 10) {
      const peakLabel = getSeverityLabel(peakValue);
      parts.push(
        `Air quality may reach ${peakLabel?.toLowerCase()} levels ` +
        `at the ${HORIZON_META[peakHorizon]?.shortLabel || ''} mark.`
      );
    }
  } else if (trend === 'stable') {
    parts.push(
      `Conditions are expected to remain roughly similar over the next 24 hours.`
    );
  }

  // Actionable advice (very brief, non-medical)
  if (trend === 'worsening' || peakValue > 75) {
    parts.push(
      `Consider limiting extended outdoor activity, especially during peak hours.`
    );
  } else if (trend === 'improving' && h6 != null && h6 < 50) {
    parts.push(
      `If conditions improve as forecasted, outdoor activity may become more comfortable later.`
    );
  }

  return parts.join(' ');
}

function getTrendDirection(forecasts) {
  const current = forecasts['1']?.predicted_pm25;
  const h6 = forecasts['6']?.predicted_pm25;
  if (current == null || h6 == null) return null;
  const diff = h6 - current;
  if (diff < -8) return { direction: 'improving', Icon: TrendingDown, color: 'var(--lp-severity-good)' };
  if (diff > 8) return { direction: 'worsening', Icon: TrendingUp, color: 'var(--lp-severity-unhealthy)' };
  return { direction: 'stable', Icon: Minus, color: 'var(--lp-severity-moderate)' };
}

/**
 * @param {object} props
 * @param {object} props.forecasts - Forecast data keyed by horizon number
 */
export default function ForecastNarrative({ forecasts }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!forecasts) return null;

  const summary = getPlainLanguageSummary(forecasts);
  const trend = getTrendDirection(forecasts);

  if (!summary) return null;

  // Collect model details for technical section
  const modelDetails = HORIZONS
    .filter(h => forecasts[String(h)])
    .map(h => {
      const f = forecasts[String(h)];
      const meta = HORIZON_META[h];
      return {
        horizon: h,
        label: meta?.label || `+${h}h`,
        shortLabel: meta?.shortLabel || `${h}h`,
        algorithm: f.model?.algorithm?.toUpperCase() || 'Unknown',
        version: f.model?.version || '',
        confidence: meta?.confidence || 'unknown',
        pm25: f.predicted_pm25,
        dataQuality: f.data_quality,
        warnings: f.warnings || [],
        errors: f.errors || [],
      };
    });

  const currentPM25 = forecasts['1']?.predicted_pm25;
  const currentDataQuality = forecasts['1']?.data_quality;

  return (
    <div className="forecast-narrative" role="region" aria-label="Forecast explanation">
      {/* Citizen Layer — Plain language summary */}
      <div className="card" style={{ padding: 'var(--sp-5)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--sp-3)' }}>
          {trend?.Icon && (
            <div
              style={{
                width: 32, height: 32, borderRadius: 'var(--lp-radius-md)',
                background: trend.color, opacity: 0.1,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, marginTop: 2,
              }}
            >
              <trend.Icon size={18} color={trend.color} />
            </div>
          )}
          <div style={{ flex: 1 }}>
            <h3 style={{
              fontSize: 'var(--text-base)',
              fontWeight: 600,
              color: 'var(--lp-text-primary)',
              marginBottom: 'var(--sp-2)',
              marginTop: 0,
            }}>
              Forecast Summary
            </h3>
            <p style={{
              fontSize: 'var(--text-sm)',
              lineHeight: 'var(--leading-relaxed)',
              color: 'var(--lp-text-secondary)',
              margin: 0,
            }}>
              {summary}
            </p>
          </div>
        </div>

        {/* Data freshness note */}
        {currentDataQuality && (
          <div style={{
            marginTop: 'var(--sp-3)',
            paddingTop: 'var(--sp-3)',
            borderTop: '1px solid var(--lp-border-subtle)',
            fontSize: 'var(--text-xs)',
            color: 'var(--lp-text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-1)',
          }}>
            <Info size={12} />
            <span>
              Based on data from {currentDataQuality.data_timestamp
                ? new Date(currentDataQuality.data_timestamp).toLocaleString('en-US', {
                    hour: '2-digit', minute: '2-digit', hour12: true,
                  })
                : 'recent measurements'}
              {currentDataQuality.feature_count
                ? ` using ${currentDataQuality.feature_count} atmospheric features`
                : ''}
              {' · '}Grid resolution: ~45km — neighborhood conditions may differ
            </span>
          </div>
        )}
      </div>

      {/* Expandable Technical Detail Layer */}
      <div style={{ marginTop: 'var(--sp-2)' }}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            background: 'none',
            border: 'none',
            padding: 'var(--sp-2) var(--sp-3)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-2)',
            fontSize: 'var(--text-xs)',
            color: 'var(--lp-text-muted)',
            borderRadius: 'var(--lp-radius-md)',
            transition: 'background 150ms',
          }}
          aria-expanded={isExpanded}
          aria-controls="forecast-technical-details"
          onMouseEnter={e => e.currentTarget.style.background = 'var(--lp-surface-elevated)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span>Technical details</span>
        </button>

        {isExpanded && (
          <div
            id="forecast-technical-details"
            className="card"
            style={{
              padding: 'var(--sp-4)',
              marginTop: 'var(--sp-1)',
              fontSize: 'var(--text-xs)',
            }}
          >
            <h4 style={{
              margin: '0 0 var(--sp-3) 0',
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              color: 'var(--lp-text-primary)',
            }}>
              Model Details by Horizon
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {modelDetails.map(d => (
                <div
                  key={d.horizon}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '60px 80px 1fr auto',
                    alignItems: 'center',
                    gap: 'var(--sp-2)',
                    padding: 'var(--sp-2)',
                    background: d.horizon === 1 ? 'var(--lp-brand-50)' : 'transparent',
                    borderRadius: 'var(--lp-radius-sm)',
                  }}
                >
                  <span style={{ fontWeight: 600, color: 'var(--lp-text-primary)' }}>
                    {d.label}
                  </span>
                  <span style={{ fontWeight: 500 }}>
                    {d.pm25 != null ? `${d.pm25.toFixed(1)} μg/m³` : '—'}
                  </span>
                  <span style={{ color: 'var(--lp-text-secondary)' }}>
                    {d.algorithm}
                    {d.version && (
                      <span style={{ color: 'var(--lp-text-muted)', marginLeft: 4 }}>
                        ({d.version.split('_').slice(0, 2).join('_')})
                      </span>
                    )}
                  </span>
                  <span style={{
                    padding: '1px 8px',
                    borderRadius: 10,
                    background: d.confidence === 'high' ? '#f0fdf4' : d.confidence === 'moderate' ? '#fefce8' : '#fef2f2',
                    color: d.confidence === 'high' ? '#166534' : d.confidence === 'moderate' ? '#854d0e' : '#991b1b',
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}>
                    {d.confidence}
                  </span>
                </div>
              ))}
            </div>

            {/* Validation note */}
            <div style={{
              marginTop: 'var(--sp-3)',
              paddingTop: 'var(--sp-3)',
              borderTop: '1px solid var(--lp-border-subtle)',
              color: 'var(--lp-text-muted)',
              lineHeight: 'var(--leading-relaxed)',
            }}>
              <p style={{ margin: '0 0 var(--sp-1) 0' }}>
                <strong>Validation:</strong> Models are validated using historical backtesting.
                "High confidence" horizons (1h, 3h) have strong correlation with observed values.
                "Moderate" and "lower" confidence horizons (6h+) are driven more by weather forecasts
                and have greater uncertainty.
              </p>
              <p style={{ margin: 0 }}>
                <strong>Data source:</strong> CAMS (Copernicus Atmosphere Monitoring Service)
                reanalysis data at ~45km grid resolution. Meteorological data from Open-Meteo.
                Your neighborhood conditions may differ from the regional average shown here.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
