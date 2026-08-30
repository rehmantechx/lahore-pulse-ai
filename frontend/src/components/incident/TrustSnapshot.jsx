/**
 * TrustSnapshot — Compact trust signal summary.
 *
 * Answers 3 questions:
 * 1. Is the data trustworthy enough?
 * 2. How reliable is the current forecast horizon?
 * 3. Can we verify the forecast later?
 *
 * Uses existing data: DataFreshness, ForecastTrustLayer logic,
 * HORIZON_META, PredictionAccountability.
 *
 * Shows simple labels: HIGH, MODERATE, LOW, UNKNOWN
 * where those labels already exist in the system.
 * Does NOT convert them into arbitrary percentages.
 */

import { useState, useEffect } from 'react';
import { getAccuracySummary } from '../../services/api';
import { HORIZON_META } from '../../constants';
import { useDemoData } from '../../demo';

function evaluateFreshness(freshnessState) {
  if (!freshnessState) return { level: 'unknown', label: 'Unknown', detail: 'Data freshness status unavailable' };
  switch (freshnessState) {
    case 'fresh':
      return { level: 'high', label: 'High', detail: 'Input data is fresh' };
    case 'degraded':
      return { level: 'moderate', label: 'Moderate', detail: 'Some data sources are slow' };
    case 'stale':
      return { level: 'low', label: 'Low', detail: 'Input data is stale' };
    default:
      return { level: 'unknown', label: 'Unknown', detail: 'Data status unclear' };
  }
}

function evaluateHorizon(horizon) {
  const meta = HORIZON_META[horizon];
  if (!meta) return { level: 'unknown', label: 'Unknown', detail: 'No metadata' };
  switch (meta.confidence) {
    case 'high':
      return { level: 'high', label: 'High', detail: 'Strong historical validation' };
    case 'moderate':
      return { level: 'moderate', label: 'Moderate', detail: 'Reasonable trend indication' };
    case 'lower':
      return { level: 'low', label: 'Low', detail: 'Greater uncertainty' };
    default:
      return { level: 'unknown', label: 'Unknown', detail: '' };
  }
}

function evaluateVerification(summary) {
  if (!summary || summary.total_predictions === 0) {
    return { level: 'unknown', label: 'Unknown', detail: 'No predictions verified yet' };
  }
  if (summary.total_predictions >= 10) {
    return { level: 'high', label: 'High', detail: `${summary.total_predictions} predictions tracked` };
  }
  return { level: 'moderate', label: 'Moderate', detail: `${summary.total_predictions} predictions tracked` };
}

export default function TrustSnapshot({ horizon = 1, forecastStatus }) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const [accuracySummary, setAccuracySummary] = useState(() => isDemo ? demoData.accuracySummary : null);

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetch() {
      try {
        const data = await getAccuracySummary({ signal: AbortSignal.timeout(20000) });
        if (!cancelled) setAccuracySummary(data);
      } catch {
        // Retry once after a short delay to handle race conditions
        try {
          await new Promise(r => setTimeout(r, 2000));
          if (cancelled) return;
          const data = await getAccuracySummary({ signal: AbortSignal.timeout(20000) });
          if (!cancelled) setAccuracySummary(data);
        } catch {
          // Works without accuracy data after retry
        }
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [isDemo]);

  const freshness = evaluateFreshness(forecastStatus?.freshness?.state);
  const reliability = evaluateHorizon(horizon);
  const verification = evaluateVerification(accuracySummary);

  const signals = [
    { ...freshness, label: 'Data Quality' },
    { ...reliability, label: 'Forecast Reliability' },
    { ...verification, label: 'Verification Track' },
  ];

  return (
    <div>
      <div className="section-header">
        <h2 className="section-header__title">Trust Snapshot</h2>
        <span className="section-header__subtitle">Can this forecast be trusted?</span>
      </div>

      <div className="trust-snapshot">
        {signals.map(signal => (
          <div key={signal.label} className="trust-signal">
            <span className="trust-signal__label">{signal.label}</span>
            <span className={`trust-signal__value trust-signal__value--${signal.level}`}>
              {signal.level === 'unknown' && signal.label === 'Verification Track'
                ? 'No Data Yet'
                : signal.label}
            </span>
            <span className="trust-signal__detail">{signal.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
