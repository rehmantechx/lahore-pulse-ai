/**
 * HorizonIntelligence — Explains why different horizons use different models.
 *
 * This is the "Horizon Intelligence" differentiator:
 * Different forecast horizons have different characteristics.
 * Short-term is nearly linear. Long-term involves regime changes.
 * The system automatically selects the best algorithm per horizon.
 *
 * Makes the multi-model architecture visible as a product feature,
 * not just a technical detail.
 */

import { useState, useEffect } from 'react';
import { getHorizonComparison } from '../../services/api';
import { HORIZON_META, HORIZONS } from '../../constants';

function AlgorithmBadge({ algorithm }) {
  const isRidge = algorithm?.toLowerCase().includes('ridge');
  return (
    <span
      className="badge badge--sm"
      style={{
        background: isRidge ? '#eff6ff' : '#f0fdf4',
        color: isRidge ? '#1d4ed8' : '#16a34a',
        border: `1px solid ${isRidge ? '#bfdbfe' : '#bbf7d0'}`,
        fontSize: '10px',
        fontFamily: 'var(--font-mono)',
      }}
    >
      {algorithm || '—'}
    </span>
  );
}

function ValidationBar({ valMAE, valRMSE, maxScale = 30 }) {
  if (valMAE === null || valMAE === undefined) return null;
  const width = Math.min(valMAE / maxScale * 100, 100);
  const color = valMAE < 8 ? '#16a34a' : valMAE < 15 ? '#a16207' : '#dc2626';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ position: 'relative', width: 60, height: 6, background: 'var(--slate-100)', borderRadius: 3 }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: `${width}%`,
          height: '100%',
          background: color,
          borderRadius: 3,
        }} />
      </div>
      <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--slate-500)', minWidth: 40 }}>
        {valMAE.toFixed(1)}
      </span>
    </div>
  );
}

export default function HorizonIntelligence({ selectedHorizon = null }) {
  const [comparison, setComparison] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const data = await getHorizonComparison({ signal: AbortSignal.timeout(20000) });
        if (!cancelled) {
          setComparison(data.horizons || []);
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
  }, [isOpen]);

  // Find the selected horizon's data
  const selectedData = selectedHorizon
    ? comparison.find(h => h.horizon === selectedHorizon)
    : null;

  return (
    <div className="expandable">
      <button
        className="expandable__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="horizon-intelligence-content"
      >
        <span>Why Different Horizons Use Different Models</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div className="expandable__content" id="horizon-intelligence-content">
          <div className="info-box info-box--info" style={{ marginBottom: 'var(--sp-4)' }}>
            Prediction difficulty changes with time. Short-horizon (1h) is nearly linear — past observations
            strongly predict the future. Long-horizon (12–24h) involves weather regime changes that require
            non-linear models. The system automatically selects the best algorithm for each horizon.
          </div>

          {loading && (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
              Loading horizon comparison...
            </div>
          )}

          {error && (
            <div className="info-box info-box--warn" style={{ marginBottom: 'var(--sp-3)' }}>
              Unable to load horizon comparison: {error}
            </div>
          )}

          {!loading && !error && comparison.length > 0 && (
            <>
              {/* Algorithm selection story */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
                {comparison.map(h => {
                  const meta = HORIZON_META[h.horizon];
                  const isSelected = selectedHorizon === h.horizon;
                  return (
                    <div
                      key={h.horizon}
                      className="surface"
                      style={{
                        padding: 'var(--sp-3)',
                        border: isSelected ? '2px solid var(--slate-800)' : undefined,
                        background: isSelected ? 'var(--slate-50)' : undefined,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-2)' }}>
                        <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>
                          {meta?.label || `${h.horizon}h`}
                        </span>
                        <AlgorithmBadge algorithm={h.algorithm} />
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--slate-500)', lineHeight: 'var(--leading-relaxed)', marginBottom: 'var(--sp-2)' }}>
                        {h.why}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '10px', color: 'var(--slate-400)' }}>Val MAE</span>
                        <ValidationBar valMAE={h.validation?.val_mae} />
                      </div>
                      {h.live?.verified_count > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
                          <span style={{ fontSize: '10px', color: 'var(--slate-400)' }}>Verified MAE</span>
                          <ValidationBar valMAE={h.live?.live_mae} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Linear vs Non-linear comparison */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)', marginBottom: 'var(--sp-3)' }}>
                <div className="surface" style={{ padding: 'var(--sp-3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
                    <AlgorithmBadge algorithm="Ridge Regression" />
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--slate-700)' }}>Linear Models</span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                    Used for <strong>1h and 24h</strong>. At 1h, the relationship between consecutive observations
                    is nearly linear. At 24h, predictions revert to seasonal baselines where linear regression is
                    more robust to noise.
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--slate-400)', marginTop: 'var(--sp-2)' }}>
                    {comparison.filter(h => h.algorithm?.includes('Ridge')).map(h => `${HORIZON_META[h.horizon]?.label} (MAE: ${h.validation?.val_mae?.toFixed(1)})`).join(' · ')}
                  </div>
                </div>
                <div className="surface" style={{ padding: 'var(--sp-3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
                    <AlgorithmBadge algorithm="HistGradientBoosting" />
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--slate-700)' }}>Non-Linear Models</span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                    Used for <strong>3h, 6h, 12h</strong>. These horizons involve weather-pollutant interactions
                    and regime changes that linear models cannot capture. Tree-based gradient boosting handles
                    these complex dynamics.
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--slate-400)', marginTop: 'var(--sp-2)' }}>
                    {comparison.filter(h => h.algorithm?.includes('Hist')).map(h => `${HORIZON_META[h.horizon]?.label} (MAE: ${h.validation?.val_mae?.toFixed(1)})`).join(' · ')}
                  </div>
                </div>
              </div>

              {/* Methodology note */}
              <div style={{ fontSize: '10px', color: 'var(--slate-400)', lineHeight: 'var(--leading-relaxed)' }}>
                Algorithm selection was determined through systematic backtesting on held-out data from Lahore (2023–2025).
                Each algorithm was validated on the same dataset with the same features. The selected algorithm for each
                horizon is the one that achieved the lowest validation MAE while maintaining reasonable complexity.
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
