/**
 * ModelMistakes — Shows the worst prediction errors.
 *
 * Demonstrates that Lahore+ is honest about its failures:
 *   - Shows worst errors with explanations
 *   - Identifies root causes (outliers, algorithmic gaps, missing data)
 *   - Tracks whether mistakes improve over time
 *
 * In demo mode: fixture data from DemoDataContext.
 * In production: fetched from /api/v1/accuracy/accountability.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getAccountabilityTimeline } from '../../services/api';
import { AlertTriangle, TrendingDown, Eye, ArrowDown } from 'lucide-react';

/* ── Helpers ──────────────────────────────────────────────── */

function getErrorSeverity(errorPct) {
  if (errorPct <= 10) return { color: '#a16207', bg: '#fefce8' };
  if (errorPct <= 25) return { color: '#ea580c', bg: '#fff7ed' };
  return { color: '#dc2626', bg: '#fef2f2' };
}

function getRootCauseIcon(rootCause) {
  if (rootCause?.includes('outlier')) return '⚡';
  if (rootCause?.includes('algorithm')) return '🔧';
  if (rootCause?.includes('monitor')) return '📡';
  if (rootCause?.includes('rapid')) return '📈';
  return '🔍';
}

/* ── Individual Mistake Card ──────────────────────────────── */

function MistakeCard({ mistake, index }) {
  const errorPct = mistake.error_percentage ?? mistake.error_pct ?? 0;
  const severity = getErrorSeverity(errorPct);

  return (
    <div
      className="mistake-card"
      data-testid={`mistake-card-${index}`}
      style={{
        opacity: 1,
        transform: 'translateY(0)',
        transition: `opacity 200ms ease ${index * 100}ms, transform 200ms ease ${index * 100}ms`,
      }}
    >
      <div className="mistake-card__header">
        <div className="mistake-card__rank">
          <span className="mistake-card__rank-number">#{index + 1}</span>
          <span className="mistake-card__rank-label">WORST PREDICTION</span>
        </div>
        <div className="mistake-card__error" style={{ background: severity.bg, color: severity.color }}>
          <span className="mistake-card__error-value">{errorPct}%</span>
          <span className="mistake-card__error-label">ERROR</span>
        </div>
      </div>

      <div className="mistake-card__values">
        <div className="mistake-card__pair">
          <span className="mistake-card__label">PREDICTED</span>
          <span className="mistake-card__value">{mistake.predicted} μg/m3</span>
        </div>
        <div className="mistake-card__arrow">
          <ArrowDown size={16} className="mistake-card__arrow-icon" aria-hidden="true" />
        </div>
        <div className="mistake-card__pair">
          <span className="mistake-card__label">ACTUAL</span>
          <span className="mistake-card__value">{mistake.actual} μg/m3</span>
        </div>
      </div>

      <div className="mistake-card__context">
        <span className="mistake-card__date">{mistake.target_time || mistake.date || '—'}</span>
        <span className="mistake-card__horizon">{mistake.horizon}h forecast</span>
      </div>

      <div className="mistake-card__root-cause">
        <span className="mistake-card__root-icon">{getRootCauseIcon(mistake.root_cause)}</span>
        <span className="mistake-card__root-label">ROOT CAUSE:</span>
        <span className="mistake-card__root-text">{mistake.root_cause}</span>
      </div>

      {mistake.explanation && (
        <div className="mistake-card__explanation">
          <Eye size={12} className="mistake-card__explanation-icon" />
          <span>{mistake.explanation}</span>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export default function ModelMistakes({ limit = 3 }) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [mistakes, setMistakes] = useState([]);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  // Load mistakes data
  useEffect(() => {
    if (isDemo) {
      setMistakes(Array.isArray(demoData.modelMistakes) ? demoData.modelMistakes : demoData.modelMistakes?.mistakes || []);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchMistakes() {
      try {
        setLoading(true);
        const data = await getAccountabilityTimeline({
          limit: 50,
          signal: AbortSignal.timeout(10000),
        });
        if (!cancelled && data.timeline) {
          // Sort by error descending, take worst N
          const sorted = [...data.timeline]
            .filter(t => t.error_percentage != null)
            .sort((a, b) => Math.abs(b.error_percentage) - Math.abs(a.error_percentage))
            .slice(0, limit)
            .map(t => ({
              date: t.target_time || t.verified_at,
              predicted: t.predicted_pm25,
              actual: t.actual_pm25,
              error_percentage: Math.abs(t.error_percentage).toFixed(1),
              horizon: t.horizon,
              root_cause: 'Insufficient root cause data in production mode',
              explanation: t.verification_notes || 'Prediction error identified',
            }));
          setMistakes(sorted);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchMistakes();
    return () => { cancelled = true; };
  }, [isDemo, demoData, limit]);

  if (loading) {
    return (
      <div className="model-mistakes model-mistakes--loading" data-testid="mistakes-loading">
        <div className="model-mistakes__skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="model-mistakes model-mistakes--error" data-testid="mistakes-error">
        <AlertTriangle size={16} />
        <span>Unable to load model mistakes: {error}</span>
      </div>
    );
  }

  if (!mistakes.length) {
    return (
      <div className="model-mistakes model-mistakes--empty" data-testid="mistakes-empty">
        <TrendingDown size={16} />
        <span>No prediction errors available yet.</span>
      </div>
    );
  }

  return (
    <div className="model-mistakes" data-testid="model-mistakes">
      <div className="model-mistakes__header">
        <AlertTriangle size={18} className="model-mistakes__header-icon" />
        <div>
          <h3 className="model-mistakes__title">Where the Model Was Wrong</h3>
          <p className="model-mistakes__subtitle">
            {mistakes.length} highest-error predictions, with root cause analysis
          </p>
        </div>
      </div>

      <div className="model-mistakes__list">
        {mistakes.map((mistake, i) => (
          <MistakeCard key={i} mistake={mistake} index={i} />
        ))}
      </div>

      <div className="model-mistakes__footer">
        <p className="model-mistakes__footer-note">
          Errors are shown transparently to build trust. If we hid our worst predictions, you couldn't verify our claims.
        </p>
      </div>
    </div>
  );
}
