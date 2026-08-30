/**
 * GovAnalyticsPage — Government analytics dashboard.
 *
 * Shows model accuracy, forecast horizon comparison, historical trends,
 * trust score, and prediction accountability.
 */

import { useState, useEffect } from 'react';
import { getAccuracySummary, getHorizonComparison } from '../services/api';
import { useDemoData } from '../demo';
import HistoricalTrendChart from '../components/forecast/HistoricalTrendChart';
import TrustScore from '../components/forecast/TrustScore';
import PredictionAccountability from '../components/forecast/PredictionAccountability';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { HORIZON_META } from '../constants';

export default function GovAnalyticsPage() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [summary, setSummary] = useState(() => isDemo ? demoData.accuracySummary : null);
  const [comparison, setComparison] = useState(() => isDemo ? demoData.horizonComparison : null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function load() {
      try {
        const [s, c] = await Promise.all([
          getAccuracySummary({ signal: AbortSignal.timeout(10000) }),
          getHorizonComparison({ signal: AbortSignal.timeout(10000) }).catch(() => null),
        ]);
        if (!cancelled) {
          setSummary(s);
          setComparison(c);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load analytics');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [isDemo]);

  return (
    <div className="page page--wide">
      <h1 className="page__title">Analytics</h1>
      <p className="page__subtitle">Model accuracy, forecast performance, and trend analysis</p>

      {/* Summary Cards */}
      <div className="premium-metrics" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: '#F0FDF4' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Total Predictions</span>
            <span className="premium-metric__value" style={{ color: '#22C55E' }}>
              {loading ? '—' : (summary?.total_predictions ?? '—')}
            </span>
            <span className="premium-metric__sub">All horizons combined</span>
          </div>
        </div>

        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: '#EFF6FF' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Horizons Active</span>
            <span className="premium-metric__value" style={{ color: '#3B82F6' }}>
              {loading ? '—' : (summary?.by_horizon?.length ?? '—')}
            </span>
            <span className="premium-metric__sub">Forecast time horizons</span>
          </div>
        </div>

        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: '#FFF7ED' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F97316" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Verified</span>
            <span className="premium-metric__value" style={{ color: '#F97316' }}>
              {loading ? '—' : (summary?.by_horizon?.reduce((s, h) => s + (h.verified_count || 0), 0) ?? '—')}
            </span>
            <span className="premium-metric__sub">Predictions with actuals</span>
          </div>
        </div>
      </div>

      {/* Error State */}
      {!loading && error && (
        <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
          <div className="surface__body" style={{ textAlign: 'center', padding: 'var(--sp-6)' }}>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-secondary)' }}>{error}</p>
          </div>
        </div>
      )}

      {/* Accuracy by Horizon Table */}
      {!loading && summary?.by_horizon?.length > 0 && (
        <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
          <div className="surface__body">
            <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
              Accuracy by Forecast Horizon
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                    <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--lp-text-secondary)', fontWeight: 500 }}>Horizon</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--lp-text-secondary)', fontWeight: 500 }}>Total</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--lp-text-secondary)', fontWeight: 500 }}>Verified</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--lp-text-secondary)', fontWeight: 500 }}>Avg Error</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--lp-text-secondary)', fontWeight: 500 }}>Max Error</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_horizon.map((h) => {
                    const meta = HORIZON_META?.[h.horizon];
                    return (
                      <tr key={h.horizon} style={{ borderBottom: '1px solid var(--lp-border-light, var(--lp-border))' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>
                          +{meta?.shortLabel || h.horizon + 'h'}
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>{h.total_predictions}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>{h.verified_count}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', color: h.avg_error != null && h.avg_error < 10 ? '#22C55E' : h.avg_error < 20 ? '#F97316' : '#EF4444' }}>
                          {h.avg_error != null ? h.avg_error.toFixed(2) : '—'}
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--lp-text-secondary)' }}>
                          {h.max_error != null ? h.max_error.toFixed(2) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Historical Trend */}
      <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="surface__body">
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
            Historical Trend
          </h3>
          <HistoricalTrendChart />
        </div>
      </div>

      {/* Trust Score — Model Trust Summary */}
      <div style={{ marginTop: 'var(--sp-4)' }}>
        <ErrorBoundary fallbackTitle="Trust score unavailable">
          <TrustScore />
        </ErrorBoundary>
      </div>

      {/* Phase 29: Compact Model-Health Strip */}
      <ErrorBoundary fallbackTitle="Model health unavailable">
        <ModelHealthStrip summary={summary} comparison={comparison} demoData={demoData} />
      </ErrorBoundary>

      {/* Prediction Accountability — Connects Analytics to Verification */}
      <div style={{ marginTop: 'var(--sp-4)' }}>
        <ErrorBoundary fallbackTitle="Prediction accountability unavailable">
          <PredictionAccountability />
        </ErrorBoundary>
      </div>

      {/* Disclaimer */}
      <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: 'var(--sp-4)', fontStyle: 'italic' }}>
        Decision-support prototype — not a government approval workflow.
      </div>
    </div>
  );
}

/**
 * ModelHealthStrip — Phase 29 compact 3-metric strip.
 * Shows accuracy trend, verification rate, and calibration in a single row.
 */
function ModelHealthStrip({ summary, comparison, demoData }) {
  const calibrationTable = demoData?.confidenceCalibrationTable || null;

  // Metric 1: Accuracy trend — average error across horizons
  const horizons = comparison?.horizons || [];
  const avgError = horizons.length > 0
    ? horizons.reduce((sum, h) => sum + (h.accuracy_mae ?? h.avg_error ?? 0), 0) / horizons.length
    : 0;
  const errorTrend = avgError < 10 ? 'good' : avgError < 20 ? 'warn' : 'poor';

  // Metric 2: Verification rate — total verified / total predictions
  const totalVerified = summary?.by_horizon?.reduce((s, h) => s + (h.verified_count || 0), 0)
    || horizons.reduce((s, h) => s + (h.verified_count || 0), 0);
  const totalPreds = summary?.total_predictions || 0;
  const verificationRate = totalPreds > 0 ? Math.round((totalVerified / totalPreds) * 100) : 0;

  // Metric 3: Calibration — % of predictions within expected confidence band
  const calibrated = calibrationTable?.filter(r => r.within_band)?.length || 0;
  const totalCalRows = calibrationTable?.length || 0;
  const calibrationPct = totalCalRows > 0 ? Math.round((calibrated / totalCalRows) * 100) : null;

  if (!summary && !comparison) {
    return (
      <div className="surface" style={{ marginTop: 'var(--sp-3)', padding: 'var(--sp-3) var(--sp-4)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-400)', textAlign: 'center' }}>
          Not enough verified observations for model health metrics
        </div>
      </div>
    );
  }

  const metricStyle = {
    display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
    padding: 'var(--sp-2) var(--sp-3)',
    borderRight: '1px solid var(--lp-border)',
  };

  const dotColor = (trend) => trend === 'good' ? '#22c55e' : trend === 'warn' ? '#f59e0b' : '#ef4444';

  return (
    <div className="surface" style={{ marginTop: 'var(--sp-3)' }} data-testid="model-health-strip">
      <div className="surface__body" style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-3)' }}>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--slate-400)', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
            Model Health
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'wrap' }}>
            {/* Accuracy Trend */}
            <div style={metricStyle}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor(errorTrend), display: 'inline-block' }} />
              <div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Avg Error</div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--slate-800)' }}>
                  {avgError != null ? `${avgError.toFixed(1)} μg/m³` : '—'}
                </div>
              </div>
            </div>
            {/* Verification Rate */}
            <div style={metricStyle}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: verificationRate > 60 ? '#22c55e' : verificationRate > 30 ? '#f59e0b' : '#ef4444', display: 'inline-block' }} />
              <div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Verified</div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--slate-800)' }}>
                  {verificationRate}%
                </div>
              </div>
            </div>
            {/* Calibration */}
            <div style={{ ...metricStyle, borderRight: 'none' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: calibrationPct != null && calibrationPct > 70 ? '#22c55e' : calibrationPct != null ? '#f59e0b' : '#94a3b8', display: 'inline-block' }} />
              <div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Calibration</div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--slate-800)' }}>
                  {calibrationPct != null ? `${calibrationPct}%` : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
