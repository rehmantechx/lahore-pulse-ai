/**
 * Government Page — Lahore Pollution Incident Intelligence & Response Command Center.
 *
 * EXACT HIERARCHY (final competition gate):
 *   1. HEADER — "PUNJAB POLLUTION COMMAND CENTER" / Lahore / STATUS / FRESHNESS / clock
 *   2. STRIP — operational chips (STATUS, TRAJECTORY, WIND, ANALOG, COMPASS, SEVERITY)
 *   3. INCIDENT — state badge / PM2.5 / severity label / trajectory / direction
 *   4. TRAJECTORY — simple forecast visualization (1h, 3h, 6h, 12h, 24h)
 *   5. ANALOGS — "Have we seen this before?" + 3 analogs (visual centerpiece)
 *   6. UPWIND — compass direction / enrichment / episode-hours / disclaimer
 *   7. INVESTIGATION — domains ranked by weather (hidden when NOMINAL)
 *   ── BELOW THE FOLD ──
 *   8. Geographic Coverage (map)
 *   9. Trust & Accountability
 *  10. Historical Trend
 *  11. Technical Deep Dive
 *
 * Constraints: No backend changes. No new ML. All scientific disclaimers preserved.
 */

import { useState, useEffect, useMemo } from 'react';
import { useForecast } from '../hooks/useForecast';
import DataFreshness from '../components/common/DataFreshness';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import LahoreMap from '../components/map/LahoreMap';
import EpisodeStateHero from '../components/incident/EpisodeStateHero';
import ForecastTrajectory from '../components/forecast/ForecastTrajectory';
import InvestigationBrief from '../components/incident/InvestigationBrief';
import TrustSnapshot from '../components/incident/TrustSnapshot';
import TechnicalDeepDive from '../components/forecast/TechnicalDeepDive';
import PredictionAccountability from '../components/forecast/PredictionAccountability';
import HistoricalTrendChart from '../components/forecast/HistoricalTrendChart';
import HistoricalAnalogPanel from '../components/analogs/HistoricalAnalogPanel';
import UpwindEvidence from '../components/incident/UpwindEvidence';
import { useHistoricalAnalogs } from '../hooks/useHistoricalAnalogs';
import { useHealth } from '../hooks/useHealth';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { getStations } from '../services/api';
import { Diamond, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { PM25_LEVELS } from '../constants';
import { useDemoData } from '../demo';

/* ── Helpers ───────────────────────────────────────────────── */

/** Map episode state to a human label for the status chip. */
function statusChip(state) {
  switch (state) {
    case 'EPISODE':
      return { label: 'ACTIVE INCIDENT', cls: 'cc-chip--danger' };
    case 'IMPROVING':
      return { label: 'IMPROVING', cls: 'cc-chip--warn' };
    case 'UNCERTAIN':
      return { label: 'UNCERTAIN', cls: '' };
    default:
      return { label: 'NOMINAL', cls: 'cc-chip--success' };
  }
}

/** Map trend direction to a chip style. */
function trendChip(direction) {
  switch (direction) {
    case 'worsening':
      return { label: 'RISING', cls: 'cc-chip--danger', Icon: TrendingUp };
    case 'improving':
      return { label: 'FALLING', cls: 'cc-chip--success', Icon: TrendingDown };
    default:
      return { label: 'STABLE', cls: 'cc-chip--active', Icon: Minus };
  }
}

/* ── Component ─────────────────────────────────────────────── */

export default function GovernmentPage() {
  /* ── Demo mode override ──────────────────────────────── */
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  /* ── Live data hooks ──────────────────────────────────── */
  const liveForecast = useForecast();
  const liveEpisode = useEpisodeIntelligence();
  const liveAnalogs = useHistoricalAnalogs();

  /* ── Use demo data when available, else live ──────────── */
  const forecasts = isDemo ? demoData.forecasts : liveForecast.forecasts;
  const errors = isDemo ? [] : liveForecast.errors;
  const forecastStatus = isDemo ? demoData.forecastStatus : liveForecast.forecastStatus;
  const loading = isDemo ? false : liveForecast.loading;
  const error = isDemo ? null : liveForecast.error;
  const refresh = liveForecast.refresh;
  const episode = isDemo ? demoData.episode : liveEpisode.episode;
  const analogs = isDemo ? demoData.analogs : liveAnalogs.analogs;
  const loadingAnalogs = isDemo ? false : liveAnalogs.loading;
  const { online } = useHealth();
  const [selectedHorizon, setSelectedHorizon] = useState(1);
  const [stations, setStations] = useState([]);
  const [clock, setClock] = useState(() => new Date());

  /* ── Derived data ──────────────────────────────────────── */
  const currentPM25 = episode?.current_pm25 ?? forecasts?.['1']?.predicted_pm25 ?? null;
  const dataQuality = forecasts?.['1']?.data_quality;
  const episodeState = (episode?.state || 'normal').toUpperCase();
  const episodeTrajectory = (episode?.trajectory || 'unknown').toLowerCase();
  const trend = episodeTrajectory === 'rising' ? 'worsening'
    : episodeTrajectory === 'falling' ? 'improving'
    : 'stable';
  const analogCount = analogs?.analogs?.length || 0;
  const hasCompass = Boolean(episode?.source_compass);
  const windDir = episode?.source_compass?.current_wind?.sector || null;
  const windSpeed = episode?.source_compass?.current_wind?.wind_speed_ms || null;

  const status = useMemo(() => statusChip(episodeState), [episodeState]);
  const trendInfo = useMemo(() => trendChip(trend), [trend]);

  /* ── Clock ─────────────────────────────────────────────── */
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  /* ── Stations ──────────────────────────────────────────── */
  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetchStations() {
      try {
        const data = await getStations({ signal: AbortSignal.timeout(10000) });
        if (!cancelled) setStations(data.stations || []);
      } catch { /* optional */ }
    }
    fetchStations();
    return () => { cancelled = true; };
  }, [isDemo]);

  /* ── Loading / Error states ────────────────────────────── */
  if (error && !forecasts) {
    return (
      <div className="page page--wide">
        <div className="cc-header">
          <div className="cc-header__title">
            <span className="cc-header__title-main">Punjab Pollution Command Center</span>
            <span className="cc-header__title-sub">Lahore — System Error</span>
          </div>
        </div>
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="page page--wide">

      {/* ═══════════════════════════════════════════════════════
          1. COMMAND CENTER HEADER — Title + Live Clock + Data Freshness
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-header">
        <div className="cc-header__title">
          <span className="cc-header__title-main">Punjab Pollution Command Center</span>
          <span className="cc-header__title-sub">
            Lahore — {isDemo ? (
              <span style={{ color: '#fbbf24', fontWeight: 600 }}>DEMO MODE — Active Incident Scenario</span>
            ) : loading ? 'Connecting...' : 'Live Intelligence'}
          </span>
        </div>
        <div className="cc-header__status">
          <span className="cc-header__clock">
            {clock.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })} PKT
          </span>
          {!loading && (
            <DataFreshness
              timestamp={dataQuality?.data_timestamp}
              freshnessHours={dataQuality?.freshness_hours}
              freshness={forecastStatus?.freshness}
            />
          )}
          <span
            className={`status-dot ${online ? 'status-dot--online' : 'status-dot--offline'}`}
            aria-hidden="true"
          />
        </div>
      </div>

      {loading && <LoadingState message="Initializing command center..." />}

      {!loading && (<>

      {/* ═══════════════════════════════════════════════════════
          2. COMMAND STRIP — 6 operational status chips
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-strip" role="status" aria-label="Operational status summary">
        <span className={`cc-chip ${status.cls}`}>
          <span className="cc-chip__label">STATUS</span> {status.label}
        </span>
        <span className={`cc-chip ${trendInfo.cls}`}>
          <span className="cc-chip__label">TRAJECTORY</span> {trendInfo.Icon && <trendInfo.Icon size={14} />} {trendInfo.label}
        </span>
        <span className={`cc-chip ${windDir ? 'cc-chip--active' : ''}`}>
          <span className="cc-chip__label">WIND</span>{' '}
          {windDir ? `${windDir} ${windSpeed ? `${windSpeed} m/s` : ''}` : '—'}
        </span>
        <span className={`cc-chip ${analogCount > 0 ? 'cc-chip--active' : ''}`}>
          <span className="cc-chip__label">ANALOG</span>{' '}
          {analogCount > 0 ? `${analogCount} MATCH${analogCount !== 1 ? 'ES' : ''}` : 'NONE'}
        </span>
        <span className={`cc-chip ${hasCompass ? 'cc-chip--active' : ''}`}>
          <span className="cc-chip__label">COMPASS</span>{' '}
          {hasCompass ? (windDir || 'ACTIVE') : 'NO DATA'}
        </span>
        <span className={`cc-chip ${episodeState === 'EPISODE' ? 'cc-chip--danger' : episodeState === 'IMPROVING' ? 'cc-chip--warn' : 'cc-chip--success'}`}>
          <span className="cc-chip__label">SEVERITY</span>{' '}
          {currentPM25 != null
            ? (PM25_LEVELS.find(l => currentPM25 <= l.max)?.label || '—')
            : '—'}
        </span>
      </div>

      {/* Partial failure banner */}
      {errors.length > 0 && (
        <div className="info-box info-box--warn" style={{ marginBottom: 'var(--sp-4)' }}>
          <strong>Partial response:</strong> {errors.length} horizon(s) returned errors.
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          3. INCIDENT HERO — PM2.5, state, trajectory, 1h/6h outlook
          Compact. Single PM2.5 value. No redundant data.
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-section">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Incident Status
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <EpisodeStateHero />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          4. TRAJECTORY — What Happens Next (simple forecast visualization)
          Positioned above Analogs per final hierarchy.
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-section">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> What Happens Next
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <ForecastTrajectory
            forecasts={forecasts}
            selectedHorizon={selectedHorizon}
            onSelectHorizon={setSelectedHorizon}
          />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          5. HISTORICAL ANALOGS — PRIMARY INTELLIGENCE (visual centerpiece)
          Dark hero section. "Have we seen this before?"
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-analog-hero">
        <div className="cc-analog-hero__title">Have we seen this before?</div>
        <div className="cc-analog-hero__subtitle">
          {analogCount > 0
            ? `${analogCount} historical Lahore episode${analogCount !== 1 ? 's' : ''} resemble${analogCount === 1 ? 's' : ''} the current conditions.`
            : 'Analyzing historical patterns against current conditions.'}
        </div>
        <HistoricalAnalogPanel analogs={analogs} loading={loadingAnalogs} />
      </div>

      {/* ═══════════════════════════════════════════════════════
          6. UPWIND EVIDENCE — Directional intelligence
          Only shown when compass enrichment data is available.
          ═══════════════════════════════════════════════════════ */}
      {hasCompass && (
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Upwind Evidence
          </div>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <UpwindEvidence episode={episode} />
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          7. INVESTIGATION — Domains ranked by weather compatibility
          Hidden when NOMINAL (no active incident to investigate).
          ═══════════════════════════════════════════════════════ */}
      {episodeState !== 'NORMAL' && (
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Investigation Status
          </div>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <InvestigationBrief episode={episode} onStartWorkflow={() => {}} />
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          BELOW THE FOLD — Supporting Evidence
          ═══════════════════════════════════════════════════════ */}
      <div className="cc-below-fold">
        <div className="cc-below-fold__title">Supporting Evidence</div>

        {/* ── 8. GEOGRAPHIC COVERAGE ─────────────────────── */}
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Geographic Coverage
          </div>
          <div className="surface" style={{ overflow: 'hidden', minHeight: 420 }}>
            <div style={{ height: 370 }}>
              <LahoreMap pm25Value={currentPM25} label="Lahore" stations={stations} />
            </div>
          </div>
        </div>

        {/* ── 9. TRUST & ACCOUNTABILITY ──────────────────── */}
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Data Trust
          </div>
          <TrustSnapshot horizon={selectedHorizon} forecastStatus={forecastStatus} />
        </div>

        <div className="cc-section">
          <PredictionAccountability />
        </div>

        {/* ── 10. HISTORICAL TREND ──────────────────────── */}
        <div className="cc-section">
          <HistoricalTrendChart />
        </div>

        {/* ── 11. TECHNICAL DEEP DIVE ───────────────────── */}
        <div className="cc-section">
          <TechnicalDeepDive forecastStatus={forecastStatus} horizon={selectedHorizon} />
        </div>
      </div>

      </>)}
    </div>
  );
}
