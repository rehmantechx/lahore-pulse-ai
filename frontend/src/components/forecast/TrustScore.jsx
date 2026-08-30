/**
 * TrustScore — Model Trust summary card for Analytics page.
 *
 * Provides a single-glance trust assessment combining:
 * - Verification rate (how many predictions have been checked)
 * - Calibration score (are confidence levels honest?)
 * - Overall accuracy rating
 *
 * This is the "Model Trust" summary that connects Analytics to Accountability.
 * It does NOT claim the system is trustworthy — it shows the evidence.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getAccuracySummary } from '../../services/api';
import { Shield, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

function getTrustLevel(score) {
  if (score >= 80) return { label: 'Strong', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', icon: CheckCircle };
  if (score >= 60) return { label: 'Moderate', color: '#a16207', bg: '#fefce8', border: '#fef08a', icon: Shield };
  if (score >= 40) return { label: 'Developing', color: '#ea580c', bg: '#fff7ed', border: '#fed7aa', icon: AlertTriangle };
  return { label: 'Insufficient', color: '#dc2626', bg: '#fef2f2', border: '#fecaca', icon: AlertTriangle };
}

function AnimatedNumber({ value, decimals = 0 }) {
  const prefersReduced = typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [display, setDisplay] = useState(prefersReduced ? value : 0);

  useEffect(() => {
    if (prefersReduced) { setDisplay(value); return; }
    const start = Date.now();
    const duration = 600;
    const animate = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Number((value * eased).toFixed(decimals)));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value, decimals, prefersReduced]);

  return <span>{display.toFixed(decimals)}</span>;
}

export default function TrustScore() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(!isDemo);

  useEffect(() => {
    if (isDemo) {
      const summary = demoData.accuracySummary;
      if (summary) {
        const totalVerified = summary.by_horizon?.reduce((s, h) => s + (h.verified_count || 0), 0) || 0;
        const totalPreds = summary.total_predictions || 1;
        const verificationRate = Math.round((totalVerified / totalPreds) * 100);
        // Trust score = weighted combination of verification rate and accuracy
        const avgError = summary.by_horizon?.reduce((s, h) => s + (h.accuracy_mae || 0), 0) / (summary.by_horizon?.length || 1);
        const accuracyScore = Math.max(0, 100 - avgError);
        const trustScore = Math.round((verificationRate * 0.5 + accuracyScore * 0.5));

        setData({
          trustScore,
          verificationRate,
          accuracyScore: Math.round(accuracyScore),
          totalPredictions: totalPreds,
          totalVerified,
          calibrationScore: demoData.confidenceCalibrationTable
            ? Math.round(demoData.confidenceCalibrationTable.reduce((s, c) => s + (c.assessment === 'GOOD' ? 100 : c.assessment === 'ACCEPTABLE' ? 60 : 20), 0) / demoData.confidenceCalibrationTable.length)
            : 72,
        });
      }
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetch() {
      try {
        setLoading(true);
        const summary = await getAccuracySummary({ signal: AbortSignal.timeout(10000) });
        if (!cancelled && summary) {
          const totalVerified = summary.by_horizon?.reduce((s, h) => s + (h.verified_count || 0), 0) || 0;
          const totalPreds = summary.total_predictions || 1;
          const verificationRate = Math.round((totalVerified / totalPreds) * 100);
          const avgError = summary.by_horizon?.reduce((s, h) => s + (h.avg_error || 0), 0) / (summary.by_horizon?.length || 1);
          const accuracyScore = Math.max(0, 100 - avgError);
          setData({
            trustScore: Math.round((verificationRate * 0.5 + accuracyScore * 0.5)),
            verificationRate,
            accuracyScore: Math.round(accuracyScore),
            totalPredictions: totalPreds,
            totalVerified,
            calibrationScore: null,
          });
        }
      } catch { /* optional */ }
      finally { if (!cancelled) setLoading(false); }
    }
    fetch();
    return () => { cancelled = true; };
  }, [isDemo, demoData]);

  if (loading) {
    return (
      <div className="surface" style={{ padding: 'var(--sp-4)', textAlign: 'center', color: 'var(--lp-text-muted)' }}>
        Loading trust score...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="surface" style={{ padding: 'var(--sp-4)', textAlign: 'center', color: 'var(--lp-text-muted)' }}>
        <Shield size={16} /> No trust data available
      </div>
    );
  }

  const level = getTrustLevel(data.trustScore);
  const LevelIcon = level.icon;

  return (
    <div
      className="surface trust-score"
      data-testid="trust-score"
      style={{ padding: 'var(--sp-5)', borderLeft: `4px solid ${level.color}` }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--sp-4)', flexWrap: 'wrap' }}>
        {/* Left: Main score */}
        <div>
          <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--lp-text-secondary)', marginBottom: 'var(--sp-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Model Trust Score
          </h3>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-3)' }}>
            <span style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, color: level.color, fontFamily: 'var(--font-mono)' }}>
              <AnimatedNumber value={data.trustScore} />
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)', fontWeight: 600, background: level.bg, color: level.color, border: `1px solid ${level.border}` }}>
              <LevelIcon size={12} />
              {level.label}
            </span>
          </div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)', marginTop: 'var(--sp-2)', maxWidth: 420 }}>
            Based on {data.totalPredictions.toLocaleString()} predictions evaluated across all forecast horizons.
            Score reflects verification rate and average accuracy.
          </p>
        </div>

        {/* Right: Breakdown metrics */}
        <div style={{ display: 'flex', gap: 'var(--sp-4)', flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'center', minWidth: 80 }}>
            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--lp-text-primary)', fontFamily: 'var(--font-mono)' }}>
              <AnimatedNumber value={data.verificationRate} />%
            </div>
            <div style={{ fontSize: '10px', color: 'var(--lp-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Verified
            </div>
          </div>
          <div style={{ textAlign: 'center', minWidth: 80 }}>
            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--lp-text-primary)', fontFamily: 'var(--font-mono)' }}>
              <AnimatedNumber value={data.accuracyScore} />
            </div>
            <div style={{ fontSize: '10px', color: 'var(--lp-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Accuracy
            </div>
          </div>
          {data.calibrationScore != null && (
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--lp-text-primary)', fontFamily: 'var(--font-mono)' }}>
                <AnimatedNumber value={data.calibrationScore} />
              </div>
              <div style={{ fontSize: '10px', color: 'var(--lp-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Calibration
              </div>
            </div>
          )}
        </div>
      </div>

      {isDemo && (
        <div style={{ fontSize: '10px', color: 'var(--lp-text-muted)', marginTop: 'var(--sp-3)', fontStyle: 'italic' }}>
          Trust score computed from demonstration data. Real-time scores update with each verified prediction.
        </div>
      )}
    </div>
  );
}
