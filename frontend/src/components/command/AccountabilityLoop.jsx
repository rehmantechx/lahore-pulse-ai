/**
 * AccountabilityLoop — Data-driven visual showing the Predict → Record → Verify → Learn cycle.
 *
 * This is the single most important visual element for judge comprehension.
 * It appears ABOVE THE FOLD on the Government Command Center.
 *
 * Accepts an optional `receipt` prop (prediction receipt data) to show REAL values:
 *   - PREDICT: shows predicted value + timestamp
 *   - RECORD: shows the receipt ID + confidence
 *   - VERIFY: shows actual value + error percentage
 *   - LEARN: shows calibration assessment
 *
 * When no receipt is provided, falls back to generic labels.
 * Pure CSS transitions. No framer-motion. Respects prefers-reduced-motion.
 */

import { Target, Eye, CheckCircle, TrendingUp, FileText, Clock } from 'lucide-react';

/* ── Error Color ──────────────────────────────────────────── */

function getErrorColor(pct) {
  if (pct <= 5) return '#16a34a';
  if (pct <= 10) return '#a16207';
  if (pct <= 20) return '#ea580c';
  return '#dc2626';
}

function getCalibrationBadge(assessment) {
  switch (assessment) {
    case 'GOOD': return { label: 'GOOD', color: '#16a34a', bg: '#f0fdf4' };
    case 'ACCEPTABLE': return { label: 'ACCEPTABLE', color: '#a16207', bg: '#fefce8' };
    case 'OVERCONFIDENT': return { label: 'OVERCONFIDENT', color: '#dc2626', bg: '#fef2f2' };
    default: return { label: 'MEASURED', color: '#0d9488', bg: '#f0fdfa' };
  }
}

/* ── Main Component ───────────────────────────────────────── */

export default function AccountabilityLoop({ receipt = null }) {
  const p = receipt?.prediction;
  const o = receipt?.observation;
  const v = receipt?.verification;
  const cal = receipt?.calibration;
  const isDataDriven = Boolean(p && v);

  const errorPct = v?.percentage_error ?? 0;
  const errorColor = getErrorColor(errorPct);
  const badge = getCalibrationBadge(cal?.assessment);

  const steps = isDataDriven ? [
    {
      icon: Target,
      label: 'PREDICT',
      detail: `${p.predicted_pm25} μg/m3`,
      subdetail: `${p.horizon_hours}h forecast`,
      time: p.prediction_time ? new Date(p.prediction_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) : null,
      color: '#0d9488',
      accent: '#0d9488',
      delay: 0,
    },
    {
      icon: FileText,
      label: 'RECORD',
      detail: `Receipt #${receipt.receipt_id}`,
      subdetail: `${Math.round((p.confidence || 0) * 100)}% confidence`,
      time: null,
      color: '#0d9488',
      accent: '#0d9488',
      delay: 150,
    },
    {
      icon: CheckCircle,
      label: 'VERIFY',
      detail: `${o?.observed_pm25 ?? '—'} μg/m3`,
      subdetail: `${errorPct}% error`,
      time: o?.observed_at ? new Date(o.observed_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) : null,
      color: errorColor,
      accent: errorColor,
      delay: 300,
    },
    {
      icon: TrendingUp,
      label: 'LEARN',
      detail: badge.label,
      subdetail: `Error: ${errorPct}%`,
      time: null,
      color: badge.color,
      accent: badge.color,
      delay: 450,
    },
  ] : [
    { icon: Target, label: 'PREDICT', detail: 'Forecast issued', color: '#0d9488', accent: '#0d9488', delay: 0 },
    { icon: Eye, label: 'RECORD', detail: 'Prediction stored', color: '#0d9488', accent: '#0d9488', delay: 150 },
    { icon: CheckCircle, label: 'VERIFY', detail: 'Reality checked', color: '#16a34a', accent: '#16a34a', delay: 300 },
    { icon: TrendingUp, label: 'LEARN', detail: 'Error measured', color: '#16a34a', accent: '#16a34a', delay: 450 },
  ];

  return (
    <div
      className={`cc-section cc-section--compact ${isDataDriven ? 'cc-section--accountability-hero' : ''}`}
      data-testid="accountability-loop"
    >
      <div className="cc-section__label">
        <span className="cc-section__label-icon" aria-hidden="true">⟳</span>
        Prediction Accountability Loop
        {isDataDriven && (
          <span className="cc-section__live-badge" aria-label="Live data">
            <Clock size={10} /> LIVE
          </span>
        )}
      </div>
      <div className="surface surface--accountability" style={{ padding: 'var(--sp-3) var(--sp-5)' }}>
        <div className={`accountability-loop ${isDataDriven ? 'accountability-loop--data' : ''}`}>
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <div
                key={step.label}
                className="accountability-loop__step"
                style={{
                  opacity: 1,
                  transform: 'translateY(0)',
                  transition: `opacity 300ms cubic-bezier(0.22, 1, 0.36, 1) ${step.delay}ms, transform 300ms cubic-bezier(0.22, 1, 0.36, 1) ${step.delay}ms`,
                }}
              >
                <div
                  className="accountability-loop__icon"
                  style={{ color: step.accent, borderColor: `${step.accent}20` }}
                  aria-hidden="true"
                >
                  <Icon size={isDataDriven ? 20 : 18} />
                </div>
                <div className="accountability-loop__label">{step.label}</div>
                <div className="accountability-loop__detail" style={isDataDriven ? { color: step.color, fontWeight: 600 } : undefined}>
                  {step.detail}
                </div>
                {step.subdetail && (
                  <div className="accountability-loop__subdetail">{step.subdetail}</div>
                )}
                {step.time && (
                  <div className="accountability-loop__time">{step.time}</div>
                )}
                {i < steps.length - 1 && (
                  <div className="accountability-loop__connector" aria-hidden="true">
                    <div className="accountability-loop__connector-line" />
                    <span className="accountability-loop__connector-arrow">→</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {isDataDriven ? (
          <div className="accountability-loop__proof">
            <span className="accountability-loop__proof-text">
              Receipt #{receipt.receipt_id} — Predicted {p.predicted_pm25} μg/m3 at {p.prediction_time ? new Date(p.prediction_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) : '—'}
              {' '}→ Observed {o?.observed_pm25 ?? '—'} μg/m3 →{' '}
              <span style={{ color: errorColor, fontWeight: 600 }}>{errorPct}% error</span>
            </span>
          </div>
        ) : (
          <p className="accountability-loop__tagline">
            Every forecast becomes a measurable record once reality arrives.
          </p>
        )}
      </div>
    </div>
  );
}
