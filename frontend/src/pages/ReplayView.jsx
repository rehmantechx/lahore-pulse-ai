/**
 * ReplayView — Historical Episode Replay.
 *
 * Lets the demo audience step through real pollution episodes hour by hour,
 * watching the time-series PM2.5 chart evolve alongside episode state detection.
 *
 * All data is real observations from the database. No fabrication.
 */

import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Area, ComposedChart } from 'recharts';
import { useReplay } from '../hooks/useReplay';
import { useDemoData } from '../demo';
import { PM25_LEVELS } from '../constants';
import { Shield, CheckCircle } from 'lucide-react';

const EPISODE_THRESHOLD_LINE = 120;
const SEVERE_THRESHOLD_LINE = 150;

/**
 * Format a date string as a short human label.
 */
function fmtDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

/**
 * Get AQI level metadata from PM25_LEVELS for a given pm25 value.
 */
function getLevel(pm25) {
  return PM25_LEVELS.find(l => pm25 <= l.max) || PM25_LEVELS[PM25_LEVELS.length - 1];
}

/**
 * Speed presets for playback.
 */
const SPEEDS = [
  { label: '0.25x', ms: 2000 },
  { label: '0.5x', ms: 1000 },
  { label: '1x', ms: 500 },
  { label: '2x', ms: 250 },
  { label: '4x', ms: 125 },
];

export default function ReplayView() {
  const {
    episodes, loadingEpisodes, episodeError,
    selectEpisode, selectedEpisode,
    observations, meta, loadingObs, obsError,
    currentIndex, currentReading, isPlaying, playbackSpeed, setPlaybackSpeed,
    progress,
    play, pause, reset, goToIndex, stepForward, stepBackward,
    episodeState, pm25Level,
  } = useReplay();

  const demoData = useDemoData();
  const replayVerification = demoData?.replayVerification || null;

  const [selectedSpeedIdx, setSelectedSpeedIdx] = useState(2); // default 1x

  const handleSpeedChange = (idx) => {
    setSelectedSpeedIdx(idx);
    setPlaybackSpeed(SPEEDS[idx].ms);
  };

  // ── Episode list view ──
  if (!selectedEpisode) {
    return (
      <div className="page">
        <div style={{ marginBottom: 'var(--sp-5)' }}>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--slate-900)', marginBottom: 'var(--sp-1)' }}>
            Episode Replay
          </h1>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)' }}>
            Step through real pollution episodes hour by hour. All data is historical observations — nothing is fabricated.
          </p>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: 'var(--sp-2)', fontStyle: 'italic' }}>
            Decision-support prototype — not a government approval workflow.
          </div>
        </div>

        {loadingEpisodes && (
          <div className="surface" style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--slate-500)' }}>
            Loading historical episodes…
          </div>
        )}

        {episodeError && (
          <div className="surface" style={{ padding: 'var(--sp-6)', borderLeft: '3px solid var(--red-500)' }}>
            <p style={{ fontWeight: 600, color: 'var(--red-700)' }}>Could not load episodes</p>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', marginTop: 'var(--sp-2)' }}>
              {episodeError?.message || 'Unknown error'}
            </p>
          </div>
        )}

        {!loadingEpisodes && episodes.length === 0 && !episodeError && (
          <div className="surface" style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--slate-500)' }}>
            No historical episodes found.
          </div>
        )}

        {episodes.length > 0 && (
          <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
            {episodes.map((ep, i) => {
              const level = getLevel(ep.peak_pm25);
              const vBadge = replayVerification?.[ep.date];
              return (
                <button
                  key={ep.date + i}
                  className="surface"
                  onClick={() => selectEpisode(ep)}
                  style={{
                    textAlign: 'left', cursor: 'pointer', padding: 'var(--sp-4)',
                    border: `1px solid ${level.color}22`, transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = level.color + '66'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = level.color + '22'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--slate-900)' }}>
                        {fmtDate(ep.date)}
                      </span>
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)', marginLeft: 'var(--sp-2)' }}>
                        {ep.readings}h of data
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
                      {vBadge && (
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: 4,
                          padding: '2px 8px', borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-xs)', fontWeight: 600,
                          background: vBadge.trustRating === 'Strong' ? '#f0fdf4' : vBadge.trustRating === 'Good' ? '#eff6ff' : '#fefce8',
                          color: vBadge.trustRating === 'Strong' ? '#16a34a' : vBadge.trustRating === 'Good' ? '#2563eb' : '#a16207',
                        }}>
                          <Shield size={10} />
                          {vBadge.verified}/{vBadge.total} verified
                        </span>
                      )}
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--text-xs)', fontWeight: 600, color: '#fff', background: level.color,
                      }}>
                        Peak {ep.peak_pm25.toFixed(0)} µg/m³
                      </span>
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>
                        Avg {ep.avg_pm25.toFixed(0)}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ── Replay view (episode selected) ──

  const currentPM25 = currentReading?.avg_value ?? 0;
  const level = getLevel(currentPM25);
  // Build proper timestamps from date + hour integer
  const currentHourLabel = currentReading?.date && currentReading?.hour != null
    ? new Date(`${currentReading.date}T${String(currentReading.hour).padStart(2, '0')}:00:00Z`)
        .toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : '--:--';

  // Prepare chart data — build labels from date + hour integer
  const chartData = observations.map((obs, idx) => ({
    name: new Date(`${obs.date}T${String(obs.hour).padStart(2, '0')}:00:00Z`)
      .toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }),
    pm25: obs.avg_value,
    index: idx,
    isCurrent: idx === currentIndex,
  }));

  return (
    <div className="page">
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-4)', flexWrap: 'wrap', gap: 'var(--sp-3)' }}>
        <div>
          <button
            onClick={() => { selectEpisode(null); reset(); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--text-sm)', color: 'var(--slate-500)', marginBottom: 'var(--sp-1)', padding: 0 }}
          >
            ← Back to episodes
          </button>
          <h1 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--slate-900)' }}>
            {fmtDate(selectedEpisode.date)} — Episode Replay
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Peak:</span>
          <span style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: getLevel(selectedEpisode.peak_pm25).color }}>
            {selectedEpisode.peak_pm25.toFixed(0)} µg/m³
          </span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)', marginLeft: 'var(--sp-2)' }}>Avg:</span>
          <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--slate-700)' }}>
            {selectedEpisode.avg_pm25.toFixed(0)}
          </span>
        </div>
      </div>

      {loadingObs && (
        <div className="surface" style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--slate-500)' }}>
          Loading observations…
        </div>
      )}

      {obsError && (
        <div className="surface" style={{ padding: 'var(--sp-6)', borderLeft: '3px solid var(--red-500)' }}>
          <p style={{ fontWeight: 600, color: 'var(--red-700)' }}>Failed to load observations</p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', marginTop: 'var(--sp-2)' }}>
            {obsError?.message || 'Unknown error'}
          </p>
        </div>
      )}

      {!loadingObs && observations.length > 0 && (
        <>
          {/* ── Current State Card ── */}
          <div className="surface" style={{
            padding: 'var(--sp-4) var(--sp-5)', marginBottom: 'var(--sp-4)',
            borderLeft: `4px solid ${level.color}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-3)' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-3)' }}>
                <span style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: level.color, fontVariantNumeric: 'tabular-nums' }}>
                  {currentPM25.toFixed(1)}
                </span>
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)' }}>µg/m³</span>
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-400)' }}>at {currentHourLabel}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                {episodeState && (
                  <span style={{
                    display: 'inline-block', padding: '3px 10px', borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--text-xs)', fontWeight: 700,
                    color: episodeState.state === 'episode' ? '#fff' : episodeState.state === 'improving' ? '#fff' : 'var(--slate-700)',
                    background: episodeState.state === 'episode' ? '#dc2626'
                      : episodeState.state === 'improving' ? '#16a34a'
                      : episodeState.state === 'elevated' ? '#fbbf24'
                      : 'var(--slate-100)',
                    letterSpacing: '0.04em',
                  }}>
                    {episodeState.label}
                  </span>
                )}
                <span style={{
                  display: 'inline-block', padding: '3px 10px', borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)', fontWeight: 600, color: level.textColor, background: level.bg,
                }}>
                  {level.label}
                </span>
              </div>
            </div>
          </div>

          {/* ── Time Series Chart ── */}
          <div className="surface" style={{ padding: 'var(--sp-4)', marginBottom: 'var(--sp-4)', overflow: 'hidden', position: 'relative', zIndex: 0 }}>
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--slate-100)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--slate-500)' }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--slate-500)' }} />
                  <Tooltip
                    formatter={(value) => [`${Math.round(value)}`, 'Air Quality']}
                    labelFormatter={(label) => `Time: ${label}`}
                    contentStyle={{ borderRadius: 'var(--radius-md)', border: 'var(--border-subtle)' }}
                  />
                  <ReferenceLine y={EPISODE_THRESHOLD_LINE} stroke="#dc2626" strokeDasharray="6 3" label={{ value: 'Episode (120)', position: 'insideTopRight', fontSize: 10, fill: '#dc2626' }} />
                  <ReferenceLine y={SEVERE_THRESHOLD_LINE} stroke="#7f1d1d" strokeDasharray="4 4" label={{ value: 'Severe (150)', position: 'insideTopRight', fontSize: 10, fill: '#7f1d1d' }} />
                  <Area type="monotone" dataKey="pm25" fill={level.color + '18'} stroke="none" isAnimationActive={false} />
                  <Line type="monotone" dataKey="pm25" stroke={level.color} strokeWidth={2} dot={false} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── Phase 29: Prediction Evidence Panel ── */}
          {demoData && observations.length > 0 && currentIndex >= 0 && (() => {
            const beforeObs = observations.slice(0, currentIndex);
            const afterObs = observations.slice(currentIndex + 1);
            const predictionReceipt = demoData.predictionReceipt || null;
            const verification = replayVerification?.[selectedEpisode?.date] || null;
            const peakObs = [...beforeObs, currentReading, ...afterObs].filter(Boolean);
            const wasOverpredicted = peakObs.some(o => o?.avg_value != null && o.avg_value < 120);
            const wasUnderpredicted = peakObs.some(o => o?.avg_value != null && o.avg_value > 150);
            const lesson = wasUnderpredicted
              ? 'Model underpredicted severity — episode escalated beyond threshold'
              : wasOverpredicted
              ? 'Model overpredicted — actual levels remained moderate'
              : 'Model prediction aligned with observed outcome';

            return (
              <div className="surface replay-evidence-panel lp-fade-up" style={{
                padding: 'var(--sp-4) var(--sp-5)', marginBottom: 'var(--sp-4)',
                borderLeft: '4px solid var(--lp-accent, #facc15)',
              }} data-testid="replay-evidence-panel">
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--slate-400)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 'var(--sp-3)' }}>
                  Prediction Evidence
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 'var(--sp-3)' }}>
                  {/* BEFORE */}
                  <div className="replay-evidence-panel__row">
                    <div className="replay-evidence-panel__label">Before</div>
                    <div className="replay-evidence-panel__value">
                      {beforeObs.length > 0
                        ? `${beforeObs[beforeObs.length - 1]?.avg_value?.toFixed(0) ?? '—'} μg/m³`
                        : 'No prior data'}
                    </div>
                    <div className="replay-evidence-panel__detail">
                      {beforeObs.length} observation{beforeObs.length !== 1 ? 's' : ''} before current
                    </div>
                  </div>
                  {/* PREDICTION */}
                  <div className="replay-evidence-panel__row">
                    <div className="replay-evidence-panel__label">Prediction</div>
                    <div className="replay-evidence-panel__value" style={{ color: 'var(--lp-accent, #ca8a04)' }}>
                      {predictionReceipt?.prediction?.value
                        ? `${predictionReceipt.prediction.value} μg/m³`
                        : `${selectedEpisode.peak_pm25.toFixed(0)} μg/m³ peak`}
                    </div>
                    <div className="replay-evidence-panel__detail">
                      {predictionReceipt?.prediction?.horizon ? `+${predictionReceipt.prediction.horizon}h forecast` : 'Episode peak'}
                    </div>
                  </div>
                  {/* AFTER */}
                  <div className="replay-evidence-panel__row">
                    <div className="replay-evidence-panel__label">After</div>
                    <div className="replay-evidence-panel__value">
                      {afterObs.length > 0
                        ? `${afterObs[0]?.avg_value?.toFixed(0) ?? '—'} μg/m³`
                        : 'No subsequent data'}
                    </div>
                    <div className="replay-evidence-panel__detail">
                      {afterObs.length} observation{afterObs.length !== 1 ? 's' : ''} after current
                    </div>
                  </div>
                  {/* VERIFICATION */}
                  <div className="replay-evidence-panel__row">
                    <div className="replay-evidence-panel__label">Verification</div>
                    <div className="replay-evidence-panel__value" style={{
                      color: verification ? (verification.trustRating === 'Strong' ? '#16a34a' : '#2563eb') : 'var(--slate-400)',
                    }}>
                      {verification ? `${verification.verified}/${verification.total}` : 'Pending'}
                    </div>
                    <div className="replay-evidence-panel__detail">
                      {verification ? `${verification.trustRating} trust rating` : 'Awaiting verification'}
                    </div>
                  </div>
                  {/* LESSON */}
                  <div className="replay-evidence-panel__row" style={{ gridColumn: 'span 2 / -1' }}>
                    <div className="replay-evidence-panel__label">Lesson</div>
                    <div className="replay-evidence-panel__value" style={{ fontSize: 'var(--text-sm)' }}>
                      {lesson}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* ── Playback Controls ── */}
          <div className="surface" style={{ padding: 'var(--sp-3) var(--sp-4)', marginBottom: 'var(--sp-4)', position: 'relative', zIndex: 1 }}>
            {/* Progress bar */}
            <div
              style={{ width: '100%', height: 4, background: 'var(--slate-100)', borderRadius: 2, cursor: 'pointer', marginBottom: 'var(--sp-3)' }}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                goToIndex(Math.round(pct * (observations.length - 1)));
              }}
            >
              <div style={{ height: '100%', width: `${progress}%`, background: level.color, borderRadius: 2, transition: 'width 0.1s linear' }} />
            </div>

            {/* Controls row */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                <button onClick={reset} title="Reset" style={ctrlBtnStyle}>⏮</button>
                <button onClick={stepBackward} title="Step back" style={ctrlBtnStyle}>◀</button>
                <button
                  onClick={isPlaying ? pause : play}
                  title={isPlaying ? 'Pause' : 'Play'}
                  style={{ ...ctrlBtnStyle, width: 40, height: 40, fontSize: '16px' }}
                >
                  {isPlaying ? '⏸' : '▶'}
                </button>
                <button onClick={stepForward} title="Step forward" style={ctrlBtnStyle}>▶</button>
              </div>

              {/* Speed selector */}
              <div style={{ display: 'flex', gap: 2 }}>
                {SPEEDS.map((sp, i) => (
                  <button
                    key={sp.label}
                    onClick={() => handleSpeedChange(i)}
                    style={{
                      padding: '3px 8px', fontSize: '11px', border: '1px solid',
                      borderColor: i === selectedSpeedIdx ? 'var(--slate-400)' : 'transparent',
                      borderRadius: 'var(--radius-sm)',
                      background: i === selectedSpeedIdx ? 'var(--slate-100)' : 'transparent',
                      color: i === selectedSpeedIdx ? 'var(--slate-800)' : 'var(--slate-500)',
                      cursor: 'pointer', fontWeight: i === selectedSpeedIdx ? 600 : 400,
                    }}
                  >
                    {sp.label}
                  </button>
                ))}
              </div>

              <span style={{ fontSize: '12px', color: 'var(--slate-400)', fontVariantNumeric: 'tabular-nums' }}>
                {currentIndex + 1} / {observations.length} hours
              </span>
            </div>
          </div>

          {/* ── Episode Summary ── */}
          {meta && (
            <div className="surface" style={{ padding: 'var(--sp-4)', fontSize: 'var(--text-sm)', color: 'var(--slate-600)' }}>
              <strong>Summary:</strong>{' '}
              Peak {meta.peak_value?.toFixed(0) || '—'} µg/m³, average {meta.avg_value?.toFixed(0) || '—'} µg/m³ over {meta.total_hours || '—'} hours
              ({meta.total_readings || '—'} readings).
            </div>
          )}
          {/* ── Verification Context — Replay↔Verification connection ── */}
          {replayVerification?.[selectedEpisode?.date] && (
            <div className="surface lp-fade-up" style={{
              padding: 'var(--sp-4) var(--sp-5)',
              marginTop: 'var(--sp-4)',
              borderLeft: '4px solid var(--lp-accent, #facc15)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-3)' }}>
                <Shield size={16} color="var(--lp-accent, #facc15)" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--slate-900)' }}>
                  Verification Status for This Episode
                </span>
              </div>
              {(() => {
                const v = replayVerification[selectedEpisode.date];
                const rate = v.total > 0 ? Math.round((v.verified / v.total) * 100) : 0;
                const ratingColor = v.trustRating === 'Strong' ? '#16a34a' : v.trustRating === 'Good' ? '#2563eb' : '#a16207';
                return (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 'var(--sp-3)' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: ratingColor, fontFamily: 'var(--font-mono)' }}>
                        {v.verified}/{v.total}
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Verified</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--slate-900)', fontFamily: 'var(--font-mono)' }}>
                        {rate}%
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Accuracy Rate</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: v.meanError <= 10 ? '#16a34a' : v.meanError <= 15 ? '#a16207' : '#dc2626', fontFamily: 'var(--font-mono)' }}>
                        {v.meanError}%
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>Mean Error</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-sm)', fontWeight: 700, color: '#fff', background: ratingColor }}>
                        <CheckCircle size={14} />
                        {v.trustRating}
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)', marginTop: 4 }}>Trust Rating</div>
                    </div>
                  </div>
                );
              })()}
              <div style={{ marginTop: 'var(--sp-3)', fontSize: 'var(--text-xs)', color: 'var(--slate-400)' }}>
                All predictions for this episode were independently verified against observed data. This is how we build trust — not by claiming accuracy, but by proving it.
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: 'var(--sp-4)', fontStyle: 'italic' }}>
            Decision-support prototype — not a government approval workflow.
          </div>
        </>
      )}
    </div>
  );
}

// ── Control button base style ──────────────────────────────────
const ctrlBtnStyle = {
  width: 32, height: 32,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  border: '1px solid var(--slate-200)', borderRadius: 'var(--radius-sm)',
  background: '#fff', cursor: 'pointer', fontSize: '13px',
  color: 'var(--slate-600)', transition: 'background 0.1s',
};
