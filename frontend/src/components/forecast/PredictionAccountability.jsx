/**
 * PredictionAccountability — Core differentiator component.
 *
 * Shows the "Predict → Verify → Learn" lifecycle:
 * 1. When a prediction was made
 * 2. What it predicted
 * 3. What actually happened
 * 4. The error (and whether the system learns)
 *
 * No AQ platform in the world does this transparently.
 * This is the single most defensible differentiator.
 */

import { useState, useEffect } from 'react';
import { getAccountabilityTimeline, triggerVerification } from '../../services/api';
import { HORIZON_META } from '../../constants';
import { formatTime } from '../../utils/format';
import { useDemoData } from '../../demo';
import { useAuth } from '../../contexts/AuthContext.jsx';

function getStatusColor(error) {
  if (error === null || error === undefined) return { bg: '#f8fafc', text: '#94a3b8', label: 'Pending' };
  const abs = Math.abs(error);
  if (abs <= 5) return { bg: '#f0fdf4', text: '#16a34a', label: 'Accurate' };
  if (abs <= 10) return { bg: '#fefce8', text: '#a16207', label: 'Close' };
  if (abs <= 20) return { bg: '#fff7ed', text: '#ea580c', label: 'Moderate' };
  return { bg: '#fef2f2', text: '#dc2626', label: 'High error' };
}

function ErrorBar({ predicted, actual, maxScale = 80 }) {
  if (predicted === null || actual === null) return null;
  const diff = actual - predicted;
  const barWidth = Math.min(Math.abs(diff) / maxScale * 100, 100);
  const isPositive = diff > 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-xs)' }}>
      <div style={{ position: 'relative', width: 80, height: 6, background: 'var(--slate-100)', borderRadius: 3 }}>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: isPositive ? '50%' : `${50 - barWidth / 2}%`,
            width: `${barWidth / 2}%`,
            height: '100%',
            background: isPositive ? '#dc2626' : '#16a34a',
            borderRadius: 3,
          }}
        />
        <div style={{ position: 'absolute', top: -1, left: '50%', width: 2, height: 8, background: 'var(--slate-400)' }} />
      </div>
      <span style={{ color: isPositive ? '#dc2626' : '#16a34a', fontFamily: 'var(--font-mono)', minWidth: 48, textAlign: 'right' }}>
        {isPositive ? '+' : ''}{diff.toFixed(1)}
      </span>
    </div>
  );
}

export default function PredictionAccountability() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const { user } = useAuth();
  const isVerifier = user?.role === 'officer' || user?.role === 'admin';
  const [timeline, setTimeline] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [filter, setFilter] = useState(null);

  useEffect(() => {
    if (!isOpen) return;

    if (isDemo) {
      const timelineData = demoData?.accountabilityTimeline;
      if (timelineData) {
        let filtered = timelineData.timeline || [];
        if (filter !== null) filtered = filtered.filter(t => t.horizon === filter);
        setTimeline(filtered);
        setSummary(timelineData.summary || null);
      }
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const params = { limit: 30 };
        if (filter !== null) params.horizon = filter;
        const data = await getAccountabilityTimeline(params, { signal: AbortSignal.timeout(10000) });
        if (!cancelled) {
          setTimeline(data.timeline || []);
          setSummary(data.summary || null);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [isOpen, filter, isDemo, demoData]);

  async function handleVerify() {
    if (isDemo) return;
    setVerifying(true);
    try {
      await triggerVerification({ signal: AbortSignal.timeout(30000) });
      // Re-fetch after verification
      const params = { limit: 30 };
      if (filter !== null) params.horizon = filter;
      const data = await getAccountabilityTimeline(params, { signal: AbortSignal.timeout(10000) });
      setTimeline(data.timeline || []);
      setSummary(data.summary || null);
    } catch {
      // Silently handle — verification is best-effort
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="expandable">
      <button
        className="expandable__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="accountability-content"
      >
        <span>Prediction Accountability</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div className="expandable__content" id="accountability-content">
          <div className="info-box info-box--info" style={{ marginBottom: 'var(--sp-4)' }}>
            <strong>Predict → Verify → Learn:</strong> Every prediction is recorded with its target time.
            When the target time passes and an observation becomes available, the system compares
            predicted vs actual. This transparency is how we build trust — and how the system improves.
          </div>

          {summary && summary.total_predictions > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
              <div className="surface" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--slate-900)' }}>
                  {summary.total_predictions}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Total Predictions</div>
              </div>
              <div className="surface" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#16a34a' }}>
                  {summary.verified}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Verified</div>
              </div>
              <div className="surface" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#a16207' }}>
                  {summary.awaiting_verification}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Awaiting</div>
              </div>
              <div className="surface" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--slate-900)' }}>
                  {summary.verification_rate}%
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Verification Rate</div>
              </div>
            </div>
          )}

          {/* Horizon filter */}
          <div style={{ display: 'flex', gap: 'var(--sp-2)', marginBottom: 'var(--sp-3)', flexWrap: 'wrap' }}>
            <button
              className={`btn btn--sm ${filter === null ? 'btn--primary' : ''}`}
              onClick={() => setFilter(null)}
              style={filter === null ? {} : { background: 'var(--slate-100)', color: 'var(--slate-600)' }}
            >
              All
            </button>
            {[1, 3, 6, 12, 24].map(h => (
              <button
                key={h}
                className={`btn btn--sm ${filter === h ? 'btn--primary' : ''}`}
                onClick={() => setFilter(h)}
                style={filter === h ? {} : { background: 'var(--slate-100)', color: 'var(--slate-600)' }}
              >
                {HORIZON_META[h]?.label || `${h}h`}
              </button>
            ))}
            <button
              className="btn btn--sm"
              onClick={handleVerify}
              disabled={verifying || !isVerifier}
              title={!isVerifier ? 'Verification requires officer or admin role' : undefined}
              style={{ marginLeft: 'auto', background: verifying || !isVerifier ? 'var(--slate-100)' : undefined, opacity: !isVerifier ? 0.6 : 1 }}
            >
              {verifying ? 'Verifying...' : isVerifier ? '↻ Verify Now' : '↻ Verify Now (officer)'}
            </button>
          </div>

          {loading && (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
              Loading accountability data...
            </div>
          )}

          {error && (
            <div className="info-box info-box--warn" style={{ marginBottom: 'var(--sp-3)' }}>
              Unable to load accountability data: {error}
            </div>
          )}

          {!loading && !error && timeline.length === 0 && (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
              No prediction records yet. Accountability data appears after predictions reach their target time.
            </div>
          )}

          {!loading && !error && timeline.length > 0 && (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table" style={{ fontSize: 'var(--text-xs)' }}>
                <thead>
                  <tr>
                    <th>Horizon</th>
                    <th>Predicted</th>
                    <th>Actual</th>
                    <th>Error</th>
                    <th>Visual</th>
                    <th>Algorithm</th>
                    <th>Prediction Time</th>
                    <th>Target Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.map((item, idx) => {
                    const status = getStatusColor(item.error);
                    const meta = HORIZON_META[item.horizon];
                    return (
                      <tr key={item.prediction_id || idx}>
                        <td style={{ fontWeight: 600 }}>{meta?.label || `${item.horizon}h`}</td>
                        <td className="text-mono">
                          {item.predicted != null ? item.predicted.toFixed(1) : '—'}
                        </td>
                        <td className="text-mono">
                          {item.actual != null ? item.actual.toFixed(1) : '—'}
                        </td>
                        <td className="text-mono" style={{ color: status.text, fontWeight: 600 }}>
                          {item.error != null ? `${Math.abs(item.error).toFixed(1)}` : '—'}
                        </td>
                        <td>
                          <ErrorBar predicted={item.predicted} actual={item.actual} />
                        </td>
                        <td className="text-xs">{item.algorithm || '—'}</td>
                        <td className="text-xs">{item.prediction_time ? formatTime(item.prediction_time) : '—'}</td>
                        <td className="text-xs">{item.target_time ? formatTime(item.target_time) : '—'}</td>
                        <td>
                          <span
                            className="badge badge--sm"
                            style={{ background: status.bg, color: status.text, fontSize: '10px' }}
                          >
                            {status.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
