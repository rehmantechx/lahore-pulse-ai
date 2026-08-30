/**
 * ForecastTrustLayer — Composite trust signal for forecast reliability.
 *
 * Aggregates 4 independent signals into a single transparent trust assessment:
 * 1. Data freshness (how recent is the input data?)
 * 2. Model availability (are the models loaded?)
 * 3. Historical accuracy (how well did past predictions perform?)
 * 4. Horizon confidence (how reliable is this forecast horizon?)
 *
 * This is NOT a proprietary black-box "trust score".
 * Each component is independently verifiable and explained.
 */

import { useState, useEffect } from 'react';
import { getAccuracySummary } from '../../services/api';
import { HORIZON_META } from '../../constants';

const TRUST_SIGNALS = {
  freshness: {
    label: 'Data Freshness',
    description: 'How recent is the input data?',
  },
  models: {
    label: 'Model Availability',
    description: 'Are the forecasting models loaded?',
  },
  accuracy: {
    label: 'Historical Accuracy',
    description: 'How well did past predictions perform?',
  },
  horizon: {
    label: 'Horizon Confidence',
    description: 'How reliable is this forecast horizon?',
  },
};

function TrustDot({ level }) {
  const colors = {
    strong: { bg: '#16a34a', ring: '#bbf7d0' },
    moderate: { bg: '#a16207', ring: '#fde68a' },
    weak: { bg: '#dc2626', ring: '#fecaca' },
    unknown: { bg: '#94a3b8', ring: '#e2e8f0' },
  };
  const c = colors[level] || colors.unknown;

  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: c.bg,
        boxShadow: `0 0 0 3px ${c.ring}`,
        flexShrink: 0,
      }}
      aria-label={`Trust level: ${level}`}
    />
  );
}

function evaluateFreshness(freshnessState) {
  if (!freshnessState) return 'unknown';
  switch (freshnessState) {
    case 'fresh': return 'strong';
    case 'degraded': return 'moderate';
    case 'stale': return 'weak';
    case 'unavailable': return 'weak';
    default: return 'unknown';
  }
}

function evaluateModels(modelStatus) {
  if (!modelStatus) return 'unknown';
  // Support both string status and object with loaded_count/horizons
  if (modelStatus === 'available' || modelStatus?.status === 'available') return 'strong';
  if (modelStatus?.status === 'degraded') return 'moderate';
  if (modelStatus?.loaded_count != null && modelStatus.loaded_count > 0) {
    const horizons = modelStatus.horizons || {};
    const loaded = Object.values(horizons).filter(h => h?.status === 'loaded').length;
    const total = Object.keys(horizons).length;
    if (loaded === total && total > 0) return 'strong';
    if (loaded > 0) return 'moderate';
    return 'weak';
  }
  return 'weak';
}

function evaluateAccuracy(summary) {
  if (!summary || summary.total_predictions === 0) return 'unknown';
  // Check if any horizon has avg_error < 15 (reasonable for PM2.5)
  const hasGoodAccuracy = summary.by_horizon?.some(h => h.avg_error != null && h.avg_error < 15);
  const hasBadAccuracy = summary.by_horizon?.every(h => h.avg_error != null && h.avg_error > 25);
  if (hasGoodAccuracy) return 'strong';
  if (hasBadAccuracy) return 'weak';
  return 'moderate';
}

function evaluateHorizon(horizon, forecastData) {
  const meta = HORIZON_META[horizon];
  if (!meta) return 'unknown';
  // Use the confidence label from validated metrics
  switch (meta.confidence) {
    case 'high': return 'strong';
    case 'moderate': return 'moderate';
    case 'lower': return 'weak';
    default: return 'unknown';
  }
}

function getOverallLevel(signals) {
  const levels = Object.values(signals);
  if (levels.every(l => l === 'strong')) return 'strong';
  if (levels.some(l => l === 'weak')) return 'weak';
  if (levels.some(l => l === 'moderate')) return 'moderate';
  return 'unknown';
}

const LEVEL_LABELS = {
  strong: { text: 'Strong', color: '#16a34a', bg: '#f0fdf4' },
  moderate: { text: 'Moderate', color: '#a16207', bg: '#fefce8' },
  weak: { text: 'Weak', color: '#dc2626', bg: '#fef2f2' },
  unknown: { text: 'Unknown', color: '#64748b', bg: '#f8fafc' },
};

export default function ForecastTrustLayer({ horizon = 1, forecastData = null, forecastStatus = null }) {
  const [accuracySummary, setAccuracySummary] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function fetch() {
      try {
        const data = await getAccuracySummary({ signal: AbortSignal.timeout(35000) });
        if (!cancelled) setAccuracySummary(data);
      } catch {
        // Trust layer works without accuracy data
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, []);

  const signals = {
    freshness: evaluateFreshness(forecastStatus?.freshness?.state),
    models: evaluateModels(forecastStatus?.model_store),
    accuracy: evaluateAccuracy(accuracySummary),
    horizon: evaluateHorizon(horizon, forecastData),
  };

  const overall = getOverallLevel(signals);
  const overallInfo = LEVEL_LABELS[overall];

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
        background: overallInfo.bg,
        borderBottom: '1px solid var(--slate-200)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <TrustDot level={overall} />
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--slate-800)' }}>
            Forecast Trust
          </span>
        </div>
        <span style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          color: overallInfo.color,
          background: 'white',
          padding: '2px 8px',
          borderRadius: 4,
          border: `1px solid ${overallInfo.color}33`,
        }}>
          {overallInfo.text}
        </span>
      </div>

      {/* Signal breakdown */}
      <div style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
        {Object.entries(TRUST_SIGNALS).map(([key, config]) => (
          <div key={key} style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 0',
            borderBottom: key !== 'horizon' ? '1px solid var(--slate-100)' : undefined,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
              <TrustDot level={signals[key]} />
              <div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--slate-700)' }}>
                  {config.label}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--slate-400)' }}>
                  {config.description}
                </div>
              </div>
            </div>
            <span style={{
              fontSize: 'var(--text-xs)',
              color: LEVEL_LABELS[signals[key]].color,
              fontWeight: 500,
            }}>
              {LEVEL_LABELS[signals[key]].text}
            </span>
          </div>
        ))}
      </div>

      {/* Explanation */}
      <div style={{
        padding: 'var(--sp-2) var(--sp-4)',
        background: 'var(--slate-50)',
        borderTop: '1px solid var(--slate-100)',
        fontSize: '10px',
        color: 'var(--slate-400)',
      }}>
        Trust is computed from 4 independent signals. Each signal is independently verifiable.
        {accuracySummary?.total_predictions === 0 && ' Accuracy signal will strengthen as predictions are verified.'}
      </div>
    </div>
  );
}
