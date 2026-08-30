/**
 * ModelSuccesses — Shows the best prediction outcomes.
 *
 * Paired with ModelMistakes for honest accountability:
 *   - Shows best predictions with explanations
 *   - Identifies what the model does well
 *   - Provides context for reliability claims
 *
 * In demo mode: fixture data from DemoDataContext.
 * In production: fetched from /api/v1/accuracy/accountability.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getAccountabilityTimeline } from '../../services/api';
import { CheckCircle, TrendingUp, Star } from 'lucide-react';

/* ── Helpers ──────────────────────────────────────────────── */

function getSuccessColor(errorPct) {
  if (errorPct <= 3) return '#16a34a';
  if (errorPct <= 5) return '#a16207';
  return '#64748b';
}

/* ── Individual Success Card ──────────────────────────────── */

function SuccessCard({ success, index }) {
  const successErrorPct = success.error_percentage ?? success.error_pct ?? 0;

  return (
    <div
      className="success-card"
      data-testid={`success-card-${index}`}
      style={{
        opacity: 1,
        transform: 'translateY(0)',
        transition: `opacity 200ms ease ${index * 100}ms, transform 200ms ease ${index * 100}ms`,
      }}
    >
      <div className="success-card__header">
        <div className="success-card__rank">
          <span className="success-card__rank-number">#{index + 1}</span>
          <span className="success-card__rank-label">BEST PREDICTION</span>
        </div>
        <div className="success-card__error" style={{ color: getSuccessColor(successErrorPct) }}>
          <CheckCircle size={14} className="success-card__error-icon" />
          <span className="success-card__error-value">{successErrorPct}%</span>
          <span className="success-card__error-label">ERROR</span>
        </div>
      </div>

      <div className="success-card__values">
        <div className="success-card__pair">
          <span className="success-card__label">PREDICTED</span>
          <span className="success-card__value">{success.predicted} μg/m3</span>
        </div>
        <div className="success-card__pair">
          <span className="success-card__label">ACTUAL</span>
          <span className="success-card__value">{success.actual} μg/m3</span>
        </div>
      </div>

      <div className="success-card__context">
        <span className="success-card__date">{success.target_time || success.date || '—'}</span>
        <span className="success-card__horizon">{success.horizon}h forecast</span>
      </div>

      <div className="success-card__explanation">
        <Star size={12} className="success-card__explanation-icon" />
        <span>{success.explanation}</span>
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export default function ModelSuccesses({ limit = 3 }) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [successes, setSuccesses] = useState([]);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  // Load successes data
  useEffect(() => {
    if (isDemo) {
      setSuccesses(Array.isArray(demoData.modelSuccesses) ? demoData.modelSuccesses : demoData.modelSuccesses?.successes || []);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchSuccesses() {
      try {
        setLoading(true);
        const data = await getAccountabilityTimeline({
          limit: 50,
          signal: AbortSignal.timeout(10000),
        });
        if (!cancelled && data.timeline) {
          const sorted = [...data.timeline]
            .filter(t => t.error_percentage != null)
            .sort((a, b) => Math.abs(a.error_percentage) - Math.abs(b.error_percentage))
            .slice(0, limit)
            .map(t => ({
              date: t.target_time || t.verified_at,
              predicted: t.predicted_pm25,
              actual: t.actual_pm25,
              error_percentage: Math.abs(t.error_percentage).toFixed(1),
              horizon: t.horizon,
              explanation: 'Low error — prediction closely matched observation',
            }));
          setSuccesses(sorted);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchSuccesses();
    return () => { cancelled = true; };
  }, [isDemo, demoData, limit]);

  if (loading) {
    return (
      <div className="model-successes model-successes--loading" data-testid="successes-loading">
        <div className="model-successes__skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="model-successes model-successes--error" data-testid="successes-error">
        <CheckCircle size={16} />
        <span>Unable to load model successes: {error}</span>
      </div>
    );
  }

  if (!successes.length) {
    return (
      <div className="model-successes model-successes--empty" data-testid="successes-empty">
        <TrendingUp size={16} />
        <span>No verified predictions available yet.</span>
      </div>
    );
  }

  return (
    <div className="model-successes" data-testid="model-successes">
      <div className="model-successes__header">
        <TrendingUp size={18} className="model-successes__header-icon" />
        <div>
          <h3 className="model-successes__title">Where the Model Was Right</h3>
          <p className="model-successes__subtitle">
            {successes.length} best predictions, showing what works reliably
          </p>
        </div>
      </div>

      <div className="model-successes__list">
        {successes.map((success, i) => (
          <SuccessCard key={i} success={success} index={i} />
        ))}
      </div>
    </div>
  );
}
