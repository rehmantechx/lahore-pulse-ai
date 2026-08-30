/**
 * Citizen Page — Focused citizen experience.
 *
 * Answers:
 * - Now: What is the current situation?
 * - Next: What is expected in the near future?
 * - Meaning: What does that mean in plain language?
 * - Timing: When is the situation expected to be better/worse?
 * - Trust: How fresh is the data? How reliable is the forecast?
 *
 * Phase 14 polish: Visual consistency with incident console.
 * Does NOT turn this into an operations console — keeps plain language.
 * Minor: uses brand color tokens, adds EpisodeStateHero at top.
 *
 * No ML jargon. No fear-inducing language.
 * Honest, evidence-based, cautious.
 */

import { useState } from 'react';
import { useForecast } from '../hooks/useForecast';
import { HORIZONS, HORIZON_META, PM25_LEVELS } from '../constants';
import { formatPM25, formatTime, formatTimeAgo } from '../utils/format';
import SeverityBadge from '../components/common/SeverityBadge';
import DataFreshness from '../components/common/DataFreshness';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import EpisodeStateHero from '../components/incident/EpisodeStateHero';
import ModelTransparency from '../components/forecast/ModelTransparency';
import ForecastTrustLayer from '../components/forecast/ForecastTrustLayer';

function getPM25Guidance(value) {
  if (value === null || value === undefined) return null;
  for (const level of PM25_LEVELS) {
    if (value <= level.max) return level;
  }
  return PM25_LEVELS[PM25_LEVELS.length - 1];
}

function getTrendText(currentPM25, forecastPM25) {
  if (currentPM25 === null || forecastPM25 === null) return null;
  const diff = forecastPM25 - currentPM25;
  if (diff < -3) return 'improving';
  if (diff > 3) return 'worsening';
  return 'relatively stable';
}

function getTimingText(forecasts) {
  if (!forecasts) return null;
  const h6 = forecasts['6'];
  const h24 = forecasts['24'];
  const h1 = forecasts['1'];

  if (!h1?.predicted_pm25 && !h6?.predicted_pm25 && !h24?.predicted_pm25) return null;

  const values = [1, 3, 6, 12, 24]
    .map(h => ({ h, v: forecasts[String(h)]?.predicted_pm25 }))
    .filter(x => x.v !== null && x.v !== undefined);

  if (values.length < 2) return null;

  const worst = values.reduce((a, b) => b.v > a.v ? b : a);
  const best = values.reduce((a, b) => b.v < a.v ? b : a);

  if (worst.h === best.h) return null;

  return {
    peak: worst,
    best: best,
  };
}

export default function CitizenPage() {
  const { forecasts, forecastStatus, loading, error, lastFetchTime, refresh } = useForecast();
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <div className="page">
        <LoadingState message="Loading air-quality information…" />
      </div>
    );
  }

  if (error && !forecasts) {
    return (
      <div className="page">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 'var(--sp-4)', color: 'var(--slate-900)' }}>
          Lahore Air Quality
        </h1>
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  const current = forecasts?.['1'];
  const currentPM25 = current?.predicted_pm25 ?? null;
  const guidance = getPM25Guidance(currentPM25);
  const trend = getTrendText(currentPM25, forecasts?.['6']?.predicted_pm25);
  const timing = getTimingText(forecasts);

  return (
    <div className="page">
      {/* ── Incident Hero (shared with Dashboard) ────────── */}
      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <EpisodeStateHero />
      </div>

      {/* ── Header ────────────────────────────────────────── */}
      <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 'var(--sp-1)', color: 'var(--slate-900)' }}>
        Lahore Air Quality
      </h1>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', marginBottom: 'var(--sp-5)' }}>
        What you need to know about current and upcoming air conditions
      </p>

      {/* ── NOW Section ───────────────────────────────────── */}
      <section style={{ marginBottom: 'var(--sp-6)' }} aria-labelledby="citizen-now">
        <h2 id="citizen-now" style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--slate-800)', marginBottom: 'var(--sp-3)', borderBottom: '2px solid var(--slate-200)', paddingBottom: 'var(--sp-2)' }}>
          Current Conditions
        </h2>

        <div className="surface">
          <div className="surface__body" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-6)', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Air Quality
              </div>
              <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, color: 'var(--slate-900)', lineHeight: 1, marginBottom: 'var(--sp-2)' }}>
                {currentPM25 !== null ? guidance?.label || '—' : '—'}
              </div>
              <SeverityBadge value={currentPM25} />
            </div>

            {guidance && (
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-700)', lineHeight: 'var(--leading-relaxed)' }}>
                  {guidance.guidance}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── NEXT Section ──────────────────────────────────── */}
      <section style={{ marginBottom: 'var(--sp-6)' }} aria-labelledby="citizen-next">
        <h2 id="citizen-next" style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--slate-800)', marginBottom: 'var(--sp-3)', borderBottom: '2px solid var(--slate-200)', paddingBottom: 'var(--sp-2)' }}>
          What to Expect
        </h2>

        <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
          {HORIZONS.map(h => {
            const f = forecasts?.[String(h)];
            const pm25 = f?.predicted_pm25;
            if (pm25 === null || pm25 === undefined) return null;
            const meta = HORIZON_META[h];
            const level = getPM25Guidance(pm25);

            return (
              <div key={h} className="surface" style={{ padding: 'var(--sp-3) var(--sp-4)', display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
                <div style={{ minWidth: 50, textAlign: 'center' }}>
                  <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{meta.shortLabel}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-400)' }}>ahead</div>
                </div>
                <div style={{ width: 1, height: 32, background: 'var(--slate-200)' }} aria-hidden="true" />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 'var(--text-md)', fontWeight: 600 }}>
                    {level?.label || '—'}
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}>
                    {meta.description}
                  </div>
                </div>
                <SeverityBadge value={pm25} size="sm" />
              </div>
            );
          })}
        </div>
      </section>

      {/* ── MEANING Section ───────────────────────────────── */}
      <section style={{ marginBottom: 'var(--sp-6)' }} aria-labelledby="citizen-meaning">
        <h2 id="citizen-meaning" style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--slate-800)', marginBottom: 'var(--sp-3)', borderBottom: '2px solid var(--slate-200)', paddingBottom: 'var(--sp-2)' }}>
          What This Means
        </h2>

        <div className="surface">
          <div className="surface__body" style={{ display: 'grid', gap: 'var(--sp-3)' }}>
            {trend && (
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                Air quality is <strong>{trend}</strong> over the next 6 hours.
                {trend === 'worsening' && ' Consider reducing prolonged outdoor activity later today.'}
                {trend === 'improving' && ' Conditions are expected to get better.'}
                {trend === 'relatively stable' && ' Conditions are expected to remain similar.'}
              </div>
            )}

            {timing && (
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                The worst air quality in the next 24 hours is expected to be{' '}
                <strong>{getPM25Guidance(timing.peak.v)?.label || 'elevated'}</strong> at{' '}
                <strong>+{HORIZON_META[timing.peak.h].shortLabel}</strong>.
                {timing.best.h !== timing.peak.h && (
                  <> The best conditions are expected to be <strong>{getPM25Guidance(timing.best.v)?.label || 'better'}</strong> at <strong>+{HORIZON_META[timing.best.h].shortLabel}</strong>.</>
                )}
              </div>
            )}

            {!trend && !timing && currentPM25 !== null && (
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)' }}>
                The current air quality is {guidance?.label || 'unknown'}. Check the forecast above for expected changes.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── TRUST Section ─────────────────────────────────── */}
      <section style={{ marginBottom: 'var(--sp-4)' }} aria-labelledby="citizen-trust">
        <h2 id="citizen-trust" style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--slate-800)', marginBottom: 'var(--sp-3)', borderBottom: '2px solid var(--slate-200)', paddingBottom: 'var(--sp-2)' }}>
          About This Forecast
        </h2>

        <div className="surface">
          <div className="surface__body" style={{ display: 'grid', gap: 'var(--sp-3)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
              This forecast uses statistical models trained on historical air-quality and weather data from Lahore (2023–2025). Short-horizon forecasts (1–3 hours) have strong historical performance. Longer forecasts (12–24 hours) carry greater uncertainty and should be used as general guidance, not precise values.
            </div>

            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
              Data comes from CAMS (Copernicus Atmosphere Monitoring Service) at <strong>45 km grid resolution</strong>. This means the reading represents a regional average across a large area — actual conditions at specific locations within Lahore may differ.
            </div>

            <DataFreshness
              timestamp={current?.data_quality?.data_timestamp}
              freshnessHours={current?.data_quality?.freshness_hours}
              freshness={forecastStatus?.freshness}
            />

            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-400)' }}>
              This system does not provide medical advice. For health-related concerns, consult local health authorities.
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust Layer (simplified for citizens) ─────────── */}
      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <ForecastTrustLayer
          horizon={1}
          forecastData={current}
          forecastStatus={forecastStatus}
        />
      </div>

      {/* ── Model Transparency ─────────────────────────────── */}
      <ModelTransparency />
    </div>
  );
}
