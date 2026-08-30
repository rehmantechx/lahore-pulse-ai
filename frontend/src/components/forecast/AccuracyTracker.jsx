/**
 * AccuracyTracker — Shows how well past predictions performed.
 *
 * Displays verified prediction accuracy by horizon:
 * - Average error, max error, verified count
 * - Recent predictions with actual vs predicted
 *
 * Uses the /api/v1/accuracy/* endpoints.
 * Clearly labeled as historical accuracy, not current certainty.
 */

import { useState, useEffect } from 'react';
import { getAccuracySummary, getRecentVerified } from '../../services/api';
import { HORIZON_META } from '../../constants';
import { HORIZONS } from '../../constants';

export default function AccuracyTracker() {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const [summaryData, recentData] = await Promise.all([
          getAccuracySummary({ signal: AbortSignal.timeout(20000) }),
          getRecentVerified({ limit: 10, signal: AbortSignal.timeout(20000) }),
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setRecent(recentData.predictions || []);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [isOpen]);

  return (
    <div className="expandable">
      <button
        className="expandable__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="accuracy-tracker-content"
      >
        <span>Prediction Track Record</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div className="expandable__content" id="accuracy-tracker-content">
          <div className="info-box info-box--info" style={{ marginBottom: 'var(--sp-4)' }}>
            This shows how well past predictions matched actual observations.
            Accuracy is computed by comparing predicted PM2.5 values against real measurements
            that became available after the prediction was made.
          </div>

          {loading && (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
              Loading accuracy data...
            </div>
          )}

          {error && (
            <div className="info-box info-box--warn" style={{ marginBottom: 'var(--sp-3)' }}>
              Unable to load accuracy data: {error}
            </div>
          )}

          {!loading && !error && summary && (
            <>
              {summary.total_predictions === 0 ? (
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
                  No prediction records yet. Accuracy data will appear after the system has
                  been running and producing predictions that can be verified against observations.
                </div>
              ) : (
                <>
                  <h4 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--slate-600)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--sp-2)' }}>
                    Accuracy by Horizon ({summary.total_predictions} total predictions)
                  </h4>
                  <table className="data-table" style={{ marginBottom: 'var(--sp-4)' }}>
                    <thead>
                      <tr>
                        <th>Horizon</th>
                        <th>Algorithm</th>
                        <th>Verified</th>
                        <th>Avg Error</th>
                        <th>Max Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.by_horizon.map(h => {
                        const meta = HORIZON_META[h.horizon];
                        return (
                          <tr key={h.horizon}>
                            <td style={{ fontWeight: 600 }}>{meta?.label || `${h.horizon}h`}</td>
                            <td className="text-mono text-xs">{meta?.algorithm || '—'}</td>
                            <td>{h.verified_count}</td>
                            <td className="text-mono">
                              {h.avg_error != null ? `${h.avg_error.toFixed(1)} μg/m³` : '—'}
                            </td>
                            <td className="text-mono">
                              {h.max_error != null ? `${h.max_error.toFixed(1)} μg/m³` : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {recent.length > 0 && (
                    <>
                      <h4 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--slate-600)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--sp-2)' }}>
                        Recent Verified Predictions
                      </h4>
                      <div style={{ display: 'grid', gap: 'var(--sp-2)' }}>
                        {recent.map(p => (
                          <div key={p.prediction_id} style={{
                            display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
                            padding: 'var(--sp-2) var(--sp-3)',
                            background: 'var(--slate-50)', borderRadius: 'var(--radius-sm)',
                            fontSize: 'var(--text-xs)',
                          }}>
                            <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', width: 28 }}>{p.horizon}h</span>
                            <span className="text-mono" style={{ color: 'var(--slate-700)' }}>
                              Predicted: {p.predicted.toFixed(1)}
                            </span>
                            <span className="text-mono" style={{ color: 'var(--slate-700)' }}>
                              Actual: {p.actual.toFixed(1)}
                            </span>
                            <span className="text-mono" style={{
                              color: p.error != null && p.error < 10 ? 'var(--green-600)' : p.error < 20 ? 'var(--amber-600)' : 'var(--red-600)',
                              fontWeight: 600,
                            }}>
                              Error: {p.error?.toFixed(1) || '—'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
