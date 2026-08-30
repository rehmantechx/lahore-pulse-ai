/**
 * ConfidenceCalibration — Shows how the model's confidence correlates with accuracy.
 *
 * Answers: "When the model says 80% confidence, is it right 80% of the time?"
 * This is a critical trust signal for judges and end users.
 *
 * In demo mode: fixture data from DemoDataContext.
 * In production: fetched from /api/v1/accuracy/horizon-comparison.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getHorizonComparison } from '../../services/api';
import { BarChart3, TrendingUp } from 'lucide-react';

/* ── Helpers ──────────────────────────────────────────────── */

function getCalibrationBarColor(confidence, actual) {
  const diff = Math.abs(confidence - actual);
  if (diff <= 3) return '#16a34a';
  if (diff <= 6) return '#a16207';
  return '#dc2626';
}

/* ── Individual Horizon Row ───────────────────────────────── */

function HorizonRow({ horizon, index }) {
  const confidenceLevel = horizon.confidence_level ?? horizon.avg_confidence ?? 0;
  const accuracyValue = horizon.accuracy ?? (horizon.avg_error != null ? Math.max(0, 100 - horizon.avg_error) : 0);
  const barColor = getCalibrationBarColor(confidenceLevel, accuracyValue);
  const confidenceWidth = Math.min(confidenceLevel, 100);
  const accuracyWidth = Math.min(accuracyValue, 100);

  return (
    <div
      className="calibration-row"
      data-testid={`calibration-row-${horizon.horizon}`}
      style={{
        opacity: 1,
        transform: 'translateY(0)',
        transition: `opacity 200ms ease ${index * 60}ms, transform 200ms ease ${index * 60}ms`,
      }}
    >
      <div className="calibration-row__header">
        <span className="calibration-row__horizon">{horizon.horizon}h</span>
        {horizon.algorithm && <span className="calibration-row__algorithm">{horizon.algorithm}</span>}
      </div>

      <div className="calibration-row__bars">
        <div className="calibration-row__bar-group">
          <span className="calibration-row__bar-label">CONFIDENCE</span>
          <div className="calibration-row__bar-track">
            <div
              className="calibration-row__bar calibration-row__bar--confidence"
              style={{ width: `${confidenceWidth}%` }}
            />
          </div>
          <span className="calibration-row__bar-value">{confidenceLevel}%</span>
        </div>

        <div className="calibration-row__bar-group">
          <span className="calibration-row__bar-label">ACCURACY</span>
          <div className="calibration-row__bar-track">
            <div
              className="calibration-row__bar calibration-row__bar--accuracy"
              style={{ width: `${accuracyWidth}%`, background: barColor }}
            />
          </div>
          <span className="calibration-row__bar-value" style={{ color: barColor }}>
            {horizon.avg_error != null ? `${horizon.avg_error} avg error` : `${accuracyValue}%`}
          </span>
        </div>
      </div>

      <div className="calibration-row__metrics">
        <div className="calibration-row__metric">
          <span className="calibration-row__metric-label">MAE</span>
          <span className="calibration-row__metric-value">{horizon.mae ?? horizon.avg_error ?? 0} μg/m3</span>
        </div>
        {horizon.r_squared != null && (
        <div className="calibration-row__metric">
          <span className="calibration-row__metric-label">R2</span>
          <span className="calibration-row__metric-value">{horizon.r_squared}</span>
        </div>
        )}
        <div className="calibration-row__metric">
          <span className="calibration-row__metric-label">N</span>
          <span className="calibration-row__metric-value">{horizon.count ?? horizon.predictions ?? 0}</span>
        </div>
      </div>

      <div className="calibration-row__assessment">
        <span className={`calibration-row__badge calibration-row__badge--${horizon.assessment?.toLowerCase() || 'acceptable'}`}>
          {horizon.assessment || 'ACCEPTABLE'}
        </span>
        {horizon.note && (
          <span className="calibration-row__note">{horizon.note}</span>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export default function ConfidenceCalibration() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [calibration, setCalibration] = useState([]);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isDemo) {
      setCalibration(demoData.confidenceCalibrationTable || []);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchCalibration() {
      try {
        setLoading(true);
        const data = await getHorizonComparison({ signal: AbortSignal.timeout(10000) });
        if (!cancelled && data?.live) {
          const horizons = data.live.map(h => ({
            horizon: h.horizon,
            algorithm: h.algorithm,
            confidence_level: h.confidence_level || 80,
            accuracy: h.accuracy || 0,
            mae: h.mae,
            r_squared: h.r_squared,
            count: h.count || 0,
            assessment: h.calibration_assessment || 'UNKNOWN',
            note: h.calibration_note || null,
          }));
          setCalibration(horizons);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchCalibration();
    return () => { cancelled = true; };
  }, [isDemo, demoData]);

  if (loading) {
    return (
      <div className="confidence-calibration confidence-calibration--loading" data-testid="calibration-loading">
        <div className="confidence-calibration__skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="confidence-calibration confidence-calibration--error" data-testid="calibration-error">
        <BarChart3 size={16} />
        <span>Unable to load calibration data: {error}</span>
      </div>
    );
  }

  if (!calibration.length) {
    return (
      <div className="confidence-calibration confidence-calibration--empty" data-testid="calibration-empty">
        <TrendingUp size={16} />
        <span>No calibration data available yet.</span>
      </div>
    );
  }

  return (
    <div className="confidence-calibration" data-testid="confidence-calibration">
      <div className="confidence-calibration__header">
        <BarChart3 size={18} className="confidence-calibration__header-icon" />
        <div>
          <h3 className="confidence-calibration__title">Confidence Calibration</h3>
          <p className="confidence-calibration__subtitle">
            When the model says it's confident, does the outcome match?
          </p>
        </div>
      </div>

      <div className="confidence-calibration__legend">
        <div className="confidence-calibration__legend-item">
          <span className="confidence-calibration__legend-bar confidence-calibration__legend-bar--confidence" />
          <span>Model Confidence</span>
        </div>
        <div className="confidence-calibration__legend-item">
          <span className="confidence-calibration__legend-bar confidence-calibration__legend-bar--accuracy" />
          <span>Actual Accuracy</span>
        </div>
      </div>

      <div className="confidence-calibration__list">
        {calibration.map((h, i) => (
          <HorizonRow key={h.horizon} horizon={h} index={i} />
        ))}
      </div>

      <div className="confidence-calibration__footer">
        <p className="confidence-calibration__footer-note">
          Good calibration means confidence percentages reflect actual accuracy. If the model says 80% confident, it should be right roughly 80% of the time.
        </p>
      </div>
    </div>
  );
}
