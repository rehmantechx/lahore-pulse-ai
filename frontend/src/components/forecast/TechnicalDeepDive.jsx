/**
 * TechnicalDeepDive — Single compact expandable for all technical details.
 *
 * Consolidates: ModelTransparency, AccuracyTracker, HorizonIntelligence,
 * TechnicalDetail, and PredictionAccountability into one coherent section.
 *
 * Uses tabs internally for navigation.
 * The main dashboard should NOT require clicking through 8 expandables.
 */

import { useState, useEffect } from 'react';
import { HORIZONS, HORIZON_META } from '../../constants';
import { getAccuracySummary, getRecentVerified, getAccountabilityTimeline, triggerVerification } from '../../services/api';
import { formatTime } from '../../utils/format';
import { useDemoData } from '../../demo';

const TABS = [
  { id: 'methodology', label: 'Methodology' },
  { id: 'validation', label: 'Validation' },
  { id: 'accountability', label: 'Accountability' },
  { id: 'horizons', label: 'Horizons' },
];

// ── Methodology Tab ─────────────────────────────────────────

function MethodologyTab() {
  return (
    <div style={{ display: 'grid', gap: 'var(--sp-4)' }}>
      <div>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
          What this system does
        </h4>
        <p style={{ color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
          Lahore Pulse AI forecasts PM2.5 air-quality levels 1 to 24 hours into the future using
          historical air-quality observations, weather data, and time-based patterns from Lahore.
        </p>
      </div>

      <div>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
          Data inputs
        </h4>
        <ul style={{ color: 'var(--slate-600)', paddingLeft: 'var(--sp-5)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
          <li>Recent PM2.5 history (up to 96 hours of observations)</li>
          <li>Weather conditions: temperature, humidity, wind speed, pressure</li>
          <li>Air-quality measurements: PM10, NO2, SO2, O3, CO</li>
          <li>Time-of-day and day-of-week patterns</li>
          <li>Historical training data from Lahore (2023–2025)</li>
        </ul>
      </div>

      <div>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
          Forecasting method
        </h4>
        <p style={{ color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
          Two validated statistical models — <strong>Ridge Regression</strong> for short-term and
          long-term horizons, and <strong>Histogram Gradient Boosting</strong> for 3, 6, and 12-hour
          horizons — selected through systematic evaluation on held-out data.
        </p>
      </div>

      <div>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
          Limitations
        </h4>
        <ul style={{ color: 'var(--slate-600)', paddingLeft: 'var(--sp-5)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
          <li>Data resolution: 45 km (CAMS grid) — local variations within Lahore not captured.</li>
          <li>Predictions reflect statistical patterns, not real-time causal understanding.</li>
          <li>Unusual events may not be captured by historical training data.</li>
          <li>Longer horizons carry greater uncertainty.</li>
        </ul>
      </div>
    </div>
  );
}

// ── Validation Tab ──────────────────────────────────────────

function ValidationTab() {
  return (
    <div>
      <div className="info-box info-box--info" style={{ marginBottom: 'var(--sp-4)' }}>
        These metrics are from historical model evaluation on held-out test data.
        They describe model quality, not certainty about any individual prediction.
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Horizon</th>
            <th>Algorithm</th>
            <th>Val MAE</th>
            <th>Val RMSE</th>
            <th>Val R²</th>
            <th>Reliability</th>
          </tr>
        </thead>
        <tbody>
          {HORIZONS.map(h => {
            const meta = HORIZON_META[h];
            return (
              <tr key={h}>
                <td style={{ fontWeight: 600 }}>{meta.label}</td>
                <td className="text-mono text-xs">{meta.algorithm}</td>
                <td className="text-mono">{meta.valMAE.toFixed(2)} μg/m3</td>
                <td className="text-mono">{meta.valRMSE.toFixed(2)} μg/m3</td>
                <td className="text-mono">{meta.valR2.toFixed(3)}</td>
                <td style={{ textTransform: 'capitalize' }}>{meta.confidence}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Accountability Tab ──────────────────────────────────────

function AccountabilityTab() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const [timeline, setTimeline] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [filter, setFilter] = useState(null);

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const params = { limit: 20 };
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
  }, [filter, isDemo]);

  async function handleVerify() {
    if (isDemo) return;
    setVerifying(true);
    try {
      await triggerVerification({ signal: AbortSignal.timeout(30000) });
      const params = { limit: 20 };
      if (filter !== null) params.horizon = filter;
      const data = await getAccountabilityTimeline(params, { signal: AbortSignal.timeout(10000) });
      setTimeline(data.timeline || []);
      setSummary(data.summary || null);
    } catch {
      // Best-effort
    } finally {
      setVerifying(false);
    }
  }

  function getStatusColor(error) {
    if (error === null || error === undefined) return { bg: '#f8fafc', text: '#94a3b8', label: 'Pending' };
    const abs = Math.abs(error);
    if (abs <= 5) return { bg: '#f0fdf4', text: '#16a34a', label: 'Accurate' };
    if (abs <= 10) return { bg: '#fefce8', text: '#a16207', label: 'Close' };
    if (abs <= 20) return { bg: '#fff7ed', text: '#ea580c', label: 'Moderate' };
    return { bg: '#fef2f2', text: '#dc2626', label: 'High error' };
  }

  return (
    <div>
      <div className="narrative-block" style={{ marginBottom: 'var(--sp-4)' }}>
        <strong>Predict → Observe → Verify:</strong> Every prediction is recorded with its target time.
        When the target time passes and an observation becomes available, the system compares
        predicted vs actual.
      </div>

      {summary && summary.total_predictions > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--sp-2)', marginBottom: 'var(--sp-3)' }}>
          {[
            { label: 'Total', value: summary.total_predictions, color: 'var(--slate-900)' },
            { label: 'Verified', value: summary.verified, color: '#16a34a' },
            { label: 'Awaiting', value: summary.awaiting_verification, color: '#a16207' },
            { label: 'Rate', value: `${summary.verification_rate}%`, color: 'var(--slate-900)' },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center', padding: 'var(--sp-2)', background: 'var(--slate-50)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: s.color }}>{s.value}</div>
              <div style={{ fontSize: '10px', color: 'var(--slate-500)' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 'var(--sp-2)', marginBottom: 'var(--sp-3)', flexWrap: 'wrap', alignItems: 'center' }}>
        <button className={`btn btn--sm ${filter === null ? 'btn--primary' : ''}`} onClick={() => setFilter(null)}>
          All
        </button>
        {[1, 3, 6, 12, 24].map(h => (
          <button key={h} className={`btn btn--sm ${filter === h ? 'btn--primary' : ''}`} onClick={() => setFilter(h)}>
            {HORIZON_META[h]?.label || `${h}h`}
          </button>
        ))}
        <button className="btn btn--sm" onClick={handleVerify} disabled={verifying} style={{ marginLeft: 'auto' }}>
          {verifying ? 'Verifying...' : '↻ Verify Now'}
        </button>
      </div>

      {loading && <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>Loading...</div>}
      {error && <div className="info-box info-box--warn">{error}</div>}

      {!loading && !error && timeline.length === 0 && (
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
          No prediction records yet.
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
                <th>Status</th>
                <th>Predicted At</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((item, idx) => {
                const status = getStatusColor(item.error);
                const meta = HORIZON_META[item.horizon];
                return (
                  <tr key={item.prediction_id || idx}>
                    <td style={{ fontWeight: 600 }}>{meta?.label || `${item.horizon}h`}</td>
                    <td className="text-mono">{item.predicted != null ? item.predicted.toFixed(1) : '—'}</td>
                    <td className="text-mono">{item.actual != null ? item.actual.toFixed(1) : '—'}</td>
                    <td className="text-mono" style={{ color: status.text, fontWeight: 600 }}>
                      {item.error != null ? `${Math.abs(item.error).toFixed(1)}` : '—'}
                    </td>
                    <td>
                      <span className="badge badge--sm" style={{ background: status.bg, color: status.text, fontSize: '10px' }}>
                        {status.label}
                      </span>
                    </td>
                    <td className="text-xs">{item.prediction_time ? formatTime(item.prediction_time) : '—'}</td>
                    <td className="text-xs">{item.target_time ? formatTime(item.target_time) : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Horizons Tab ────────────────────────────────────────────

function HorizonsTab() {
  return (
    <div>
      <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
        {HORIZONS.map(h => {
          const meta = HORIZON_META[h];
          const confColors = {
            high: { bg: '#f0fdf4', text: '#166534', border: '#bbf7d0' },
            moderate: { bg: '#fefce8', text: '#854d0e', border: '#fde68a' },
            lower: { bg: '#fef2f2', text: '#991b1b', border: '#fecaca' },
          };
          const c = confColors[meta.confidence] || confColors.moderate;

          return (
            <div key={h} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', padding: 'var(--sp-2) var(--sp-3)', background: 'var(--slate-50)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--slate-500)', width: 36, fontWeight: 600 }}>
                {meta.shortLabel}
              </span>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', flex: 1 }}>
                {meta.description}
              </span>
              <span style={{
                fontSize: '10px', fontWeight: 500, padding: '2px 6px', borderRadius: 3,
                background: c.bg, color: c.text, border: `1px solid ${c.border}`,
                textTransform: 'capitalize',
              }}>
                {meta.confidence}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────

export default function TechnicalDeepDive({ forecastStatus, horizon = 1 }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('methodology');

  return (
    <div className="deep-dive">
      <button
        className="deep-dive__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="deep-dive-content"
      >
        <span>Technical Deep Dive</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div id="deep-dive-content">
          {/* Tabs */}
          <div className="deep-dive__tabs">
            {TABS.map(tab => (
              <button
                key={tab.id}
                className={`deep-dive__tab ${activeTab === tab.id ? 'deep-dive__tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="deep-dive__content">
            {activeTab === 'methodology' && <MethodologyTab />}
            {activeTab === 'validation' && <ValidationTab />}
            {activeTab === 'accountability' && <AccountabilityTab />}
            {activeTab === 'horizons' && <HorizonsTab />}
          </div>
        </div>
      )}
    </div>
  );
}
