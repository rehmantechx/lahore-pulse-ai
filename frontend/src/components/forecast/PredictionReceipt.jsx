/**
 * PredictionReceipt — The centerpiece of Lahore+ accountability.
 *
 * Interactive "digital forensic record" that answers:
 *   1. What did we predict?
 *   2. When did we predict it?
 *   3. What actually happened?
 *   4. How wrong were we?
 *   5. Was the confidence justified?
 *
 * In demo mode: deterministic fixture data.
 * In production: fetched from /api/v1/accuracy/recent.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getRecentVerified } from '../../services/api';
import { ChevronDown, ChevronUp, FileText, CheckCircle, AlertTriangle, Clock, Target, BarChart3 } from 'lucide-react';

/* ── Helpers ──────────────────────────────────────────────── */

function getCalibrationColor(assessment) {
  switch (assessment) {
    case 'GOOD': return { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' };
    case 'ACCEPTABLE': return { bg: '#fefce8', text: '#a16207', border: '#fef08a' };
    case 'OVERCONFIDENT': return { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' };
    case 'UNDERESTIMATED': return { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa' };
    default: return { bg: '#f8fafc', text: '#64748b', border: '#e2e8f0' };
  }
}

function getErrorColor(errorPct) {
  if (errorPct <= 5) return '#16a34a';
  if (errorPct <= 10) return '#a16207';
  if (errorPct <= 20) return '#ea580c';
  return '#dc2626';
}

function getStatusIcon(status) {
  switch (status) {
    case 'VERIFIED': return <CheckCircle size={16} />;
    case 'PENDING': return <Clock size={16} />;
    default: return <AlertTriangle size={16} />;
  }
}

/* ── Animated Number ──────────────────────────────────────── */

function AnimatedValue({ value, decimals = 0, delay = 0 }) {
  const prefersReduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [display, setDisplay] = useState(prefersReduced ? value : 0);

  useEffect(() => {
    if (prefersReduced) {
      setDisplay(value);
      return;
    }
    const timeout = setTimeout(() => {
      const duration = 600;
      const startTime = Date.now();
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplay(Number((value * eased).toFixed(decimals)));
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }, delay);
    return () => clearTimeout(timeout);
  }, [value, decimals, delay, prefersReduced]);

  return <span>{display.toFixed(decimals)}</span>;
}

/* ── Receipt Section ──────────────────────────────────────── */

function ReceiptSection({ label, icon: Icon, children, delay = 0, visible = true }) {
  if (!visible) return null;
  return (
    <div
      className="receipt-section"
      data-testid={`receipt-section-${label?.toLowerCase().replace(/\s+/g, '-')}`}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        transition: `opacity 300ms cubic-bezier(0.22, 1, 0.36, 1) ${delay}ms, transform 300ms cubic-bezier(0.22, 1, 0.36, 1) ${delay}ms`,
      }}
    >
      <div className="receipt-section__header">
        {Icon && <Icon size={14} className="receipt-section__icon" aria-hidden="true" />}
        <span className="receipt-section__label">{label}</span>
      </div>
      <div className="receipt-section__body">{children}</div>
    </div>
  );
}

/* ── Confidence Calibration ───────────────────────────────── */

function ConfidenceCalibration({ confidence, error, assessment, explanation }) {
  const calColor = getCalibrationColor(assessment);
  return (
    <div className="receipt-calibration" data-testid="receipt-calibration">
      <div className="receipt-calibration__row">
        <div className="receipt-calibration__item">
          <span className="receipt-calibration__label">MODEL SAID</span>
          <span className="receipt-calibration__value">{confidence}% confidence</span>
        </div>
        <div className="receipt-calibration__arrow" aria-hidden="true">→</div>
        <div className="receipt-calibration__item">
          <span className="receipt-calibration__label">OUTCOME</span>
          <span className="receipt-calibration__value" style={{ color: getErrorColor(error) }}>
            {error}% error
          </span>
        </div>
        <div className="receipt-calibration__arrow" aria-hidden="true">→</div>
        <div className="receipt-calibration__item">
          <span className="receipt-calibration__label">CALIBRATION</span>
          <span
            className="receipt-calibration__badge"
            style={{ background: calColor.bg, color: calColor.text, borderColor: calColor.border }}
          >
            {assessment}
          </span>
        </div>
      </div>
      {explanation && (
        <p className="receipt-calibration__explanation">{explanation}</p>
      )}
    </div>
  );
}

/* ── Verification Timeline ────────────────────────────────── */

function VerificationTimeline({ prediction, observation, verification }) {
  const steps = [
    { label: 'PREDICTED', time: prediction.prediction_time, detail: `${prediction.predicted_pm25} μg/m3 · ${prediction.horizon_hours}h horizon` },
    { label: 'TARGET TIME REACHED', time: prediction.target_time, detail: 'Observation window opened' },
    { label: 'OBSERVATION AVAILABLE', time: observation.observed_at, detail: `${observation.observed_pm25} μg/m3 · ${observation.station_name}` },
    { label: 'VERIFIED', time: verification.verified_at, detail: `Error: ${verification.percentage_error}% · Status: ${verification.status}` },
    { label: 'ACCOUNTABILITY RECORD UPDATED', time: verification.verified_at, detail: 'Outcome recorded permanently' },
  ];

  return (
    <div className="receipt-timeline" data-testid="receipt-timeline">
      {steps.map((step, i) => (
        <div key={step.label} className="receipt-timeline__step">
          <div className="receipt-timeline__dot" />
          {i < steps.length - 1 && <div className="receipt-timeline__line" />}
          <div className="receipt-timeline__content">
            <span className="receipt-timeline__label">{step.label}</span>
            <span className="receipt-timeline__detail">{step.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export default function PredictionReceipt({ compact = false }) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [showObservation, setShowObservation] = useState(false);
  const [showCalibration, setShowCalibration] = useState(true);

  // Load receipt data
  useEffect(() => {
    if (isDemo) {
      setReceipt(demoData.predictionReceipt);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchReceipt() {
      try {
        setLoading(true);
        const data = await getRecentVerified({ limit: 1, signal: AbortSignal.timeout(10000) });
        if (!cancelled && data.predictions?.length > 0) {
          const p = data.predictions[0];
          setReceipt({
            receipt_id: `LP-${String(p.prediction_id || '000000').slice(-6).toUpperCase()}`,
            prediction: {
              predicted_pm25: p.predicted,
              horizon_hours: p.horizon,
              prediction_time: p.prediction_time,
              target_time: p.target_time,
              model_version: p.model_version,
              algorithm: p.algorithm,
            },
            observation: {
              observed_pm25: p.actual,
              observed_at: p.target_time,
              station_id: p.station_id || null,
              station_name: p.station_name || null,
            },
            verification: {
              absolute_error: Math.abs(p.error || 0),
              percentage_error: p.predicted ? Math.abs(((p.predicted - p.actual) / p.predicted) * 100).toFixed(1) : 0,
              status: 'VERIFIED',
              within_tolerance: Math.abs(p.error || 0) <= p.predicted * 0.2,
            },
          });
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchReceipt();
    return () => { cancelled = true; };
  }, [isDemo, demoData]);

  if (loading) {
    return (
      <div className="receipt receipt--loading" data-testid="receipt-loading">
        <div className="receipt__skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="receipt receipt--error" data-testid="receipt-error">
        <AlertTriangle size={16} />
        <span>Unable to load prediction receipt: {error}</span>
      </div>
    );
  }

  if (!receipt) {
    return (
      <div className="receipt receipt--empty" data-testid="receipt-empty">
        <FileText size={16} />
        <span>No verified predictions available yet.</span>
      </div>
    );
  }

  const { prediction, observation, verification, calibration, trust_snapshot } = receipt;
  const errorPct = verification?.percentage_error || 0;
  const errorAbs = verification?.absolute_error || 0;

  if (compact) {
    return (
      <div className="receipt receipt--compact" data-testid="prediction-receipt">
        <div className="receipt__compact-header">
          <FileText size={14} />
          <span className="receipt__compact-id">Receipt #{receipt.receipt_id}</span>
          <span className={`receipt__compact-status receipt__compact-status--${verification?.status?.toLowerCase() || 'pending'}`}>
            {getStatusIcon(verification?.status)}
            {verification?.status || 'PENDING'}
          </span>
        </div>
        <div className="receipt__compact-values">
          <div className="receipt__compact-pair">
            <span className="receipt__compact-label">PREDICTED</span>
            <span className="receipt__compact-value">{prediction.predicted_pm25} <small>μg/m3</small></span>
          </div>
          <div className="receipt__compact-pair">
            <span className="receipt__compact-label">ACTUAL</span>
            <span className="receipt__compact-value">{observation.observed_pm25} <small>μg/m3</small></span>
          </div>
          <div className="receipt__compact-pair">
            <span className="receipt__compact-label">ERROR</span>
            <span className="receipt__compact-value" style={{ color: getErrorColor(errorPct) }}>
              {errorPct}%
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="receipt" data-testid="prediction-receipt">
      {/* Header */}
      <div className="receipt__header">
        <div className="receipt__header-top">
          <FileText size={18} className="receipt__header-icon" />
          <div>
            <h3 className="receipt__title">Prediction Receipt</h3>
            <span className="receipt__id">Receipt #{receipt.receipt_id}</span>
          </div>
          <span className={`receipt__status receipt__status--${verification?.status?.toLowerCase() || 'pending'}`}>
            {getStatusIcon(verification?.status)}
            {verification?.status || 'PENDING VERIFICATION'}
          </span>
        </div>
        {isDemo && receipt.disclaimer && (
          <div className="receipt__disclaimer">{receipt.disclaimer}</div>
        )}
      </div>

      {/* Core Values Grid */}
      <div className="receipt__grid">
        <ReceiptSection label="PREDICTED" icon={Target} delay={0}>
          <div className="receipt__big-value">{prediction.predicted_pm25} <small>μg/m3</small></div>
          <div className="receipt__meta">
            Target: +{prediction.horizon_hours} hours
          </div>
        </ReceiptSection>

        <ReceiptSection label="ACTUAL" icon={BarChart3} delay={100}>
          <div className="receipt__big-value" data-testid="receipt-actual-value">
            {observation.observed_pm25} <small>μg/m3</small>
          </div>
          <div className="receipt__meta">
            Observed: +{prediction.horizon_hours}h
          </div>
        </ReceiptSection>

        <ReceiptSection label="ERROR" icon={AlertTriangle} delay={200}>
          <div className="receipt__big-value" style={{ color: getErrorColor(errorPct) }}>
            {errorAbs > 0 ? '+' : ''}{errorAbs} <small>μg/m3</small>
          </div>
          <div className="receipt__meta" style={{ color: getErrorColor(errorPct) }}>
            {errorPct}%
          </div>
        </ReceiptSection>

        <ReceiptSection label="CONFIDENCE" icon={BarChart3} delay={300}>
          <div className="receipt__big-value">{prediction.confidence ? `${Math.round(prediction.confidence * 100)}%` : '—'}</div>
          <div className="receipt__meta">
            {prediction.algorithm || '—'}
          </div>
        </ReceiptSection>
      </div>

      {/* Outcome */}
      <ReceiptSection label="OUTCOME" delay={400}>
        <div className="receipt__outcome">
          <span className={`receipt__outcome-badge receipt__outcome-badge--${verification?.within_tolerance ? 'pass' : 'fail'}`}>
            {verification?.within_tolerance ? 'Within expected confidence range' : 'Outside expected confidence range'}
          </span>
        </div>
      </ReceiptSection>

      {/* Model Provenance */}
      <ReceiptSection label="MODEL" icon={FileText} delay={500}>
        <div className="receipt__provenance">
          <div className="receipt__provenance-row">
            <span className="receipt__provenance-label">Algorithm</span>
            <span className="receipt__provenance-value">{prediction.algorithm || '—'}</span>
          </div>
          <div className="receipt__provenance-row">
            <span className="receipt__provenance-label">Version</span>
            <span className="receipt__provenance-value">{prediction.model_version || '—'}</span>
          </div>
          <div className="receipt__provenance-row">
            <span className="receipt__provenance-label">Issued</span>
            <span className="receipt__provenance-value">{prediction.prediction_time || '—'}</span>
          </div>
          <div className="receipt__provenance-row">
            <span className="receipt__provenance-label">Target</span>
            <span className="receipt__provenance-value">{prediction.target_time || '—'}</span>
          </div>
        </div>
      </ReceiptSection>

      {/* Confidence Calibration (expandable) */}
      {calibration && (
        <div className="receipt__expandable">
          <button
            className="receipt__expand-trigger"
            onClick={() => setShowCalibration(!showCalibration)}
            aria-expanded={showCalibration}
            data-testid="receipt-calibration-toggle"
          >
            <span>Confidence Calibration</span>
            {showCalibration ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showCalibration && (
            <ConfidenceCalibration
              confidence={calibration.confidence_level}
              error={calibration.actual_error}
              assessment={calibration.assessment}
              explanation={calibration.explanation}
            />
          )}
        </div>
      )}

      {/* Verification Timeline — Interactive reveal */}
      <div className="receipt__expandable receipt__expandable--timeline">
        <button
          className={`receipt__expand-trigger receipt__expand-trigger--proof ${expanded ? 'receipt__expand-trigger--active' : ''}`}
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          data-testid="receipt-timeline-toggle"
        >
          <span>{expanded ? 'Verification Timeline' : '⏱ Open Verification Timeline — See the Proof'}</span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {expanded && (
          <VerificationTimeline
            prediction={prediction}
            observation={observation}
            verification={verification}
          />
        )}
      </div>

      {/* Trust Snapshot */}
      {trust_snapshot && (
        <ReceiptSection label="WHY TRUST THIS FORECAST?" delay={600}>
          <div className="receipt__trust" data-testid="receipt-trust">
            <div className="receipt__trust-item">
              <CheckCircle size={14} className="receipt__trust-icon" />
              <span>{trust_snapshot.total_evaluated.toLocaleString()} predictions evaluated</span>
            </div>
            <div className="receipt__trust-item">
              <CheckCircle size={14} className="receipt__trust-icon" />
              <span>{trust_snapshot.within_tolerance_pct}% within tolerance</span>
            </div>
            <div className="receipt__trust-item">
              <CheckCircle size={14} className="receipt__trust-icon" />
              <span>Confidence tracked against outcomes</span>
            </div>
            <div className="receipt__trust-item">
              <CheckCircle size={14} className="receipt__trust-icon" />
              <span>Forecasts independently verified after target time</span>
            </div>
            <div className="receipt__trust-item">
              <CheckCircle size={14} className="receipt__trust-icon" />
              <span>Errors remain visible</span>
            </div>
          </div>
        </ReceiptSection>
      )}

      {/* Footer */}
      <div className="receipt__footer">
        <span className="receipt__footer-text">
          Prediction recorded for accountability. This receipt cannot be edited after the fact.
        </span>
      </div>
    </div>
  );
}
