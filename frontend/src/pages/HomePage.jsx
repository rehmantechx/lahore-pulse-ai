/**
 * HomePage — Lahore+ Citizen Dashboard
 *
 * Premium civic-tech design. NO technical jargon.
 * Human-friendly labels. AQI gauge hero. Clean, spacious layout.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useHealth } from '../hooks/useHealth';
import { useHistoricalAnalogs } from '../hooks/useHistoricalAnalogs';
import { getStations } from '../services/api';
import { useDemoData } from '../demo';
import AQIGauge from '../components/citizen/AQIGauge.jsx';
import AlertBanner from '../components/citizen/AlertBanner.jsx';
import HealthGuidance from '../components/citizen/HealthGuidance.jsx';
import WhyPanel from '../components/citizen/WhyPanel.jsx';
import PollutionStory from '../components/citizen/PollutionStory.jsx';
import HistoricalComparison from '../components/citizen/HistoricalComparison.jsx';
import { HORIZONS, HORIZON_META } from '../constants';
import { MapPin, Wind, Clock, Radio, Map, BarChart3, Bell, TrendingUp, Zap, AlertTriangle, TrendingDown, RefreshCw, CheckCircle } from 'lucide-react';


/* ═══════════════════════════════════════════════════════════════
   HELPERS — Citizen-friendly labels (no jargon)
   ═══════════════════════════════════════════════════════════════ */

function getAirQualityInfo(value) {
  if (value == null || isNaN(value)) return { label: 'No Data', color: '#A09A93', bg: '#F8F7F5' };
  if (value <= 12)  return { label: 'Excellent', color: '#22C55E', bg: '#F0FDF4' };
  if (value <= 25)  return { label: 'Good',      color: '#84CC16', bg: '#F7FEE7' };
  if (value <= 35)  return { label: 'Fair',      color: '#EAB308', bg: '#FEFCE8' };
  if (value <= 55)  return { label: 'Moderate',  color: '#F97316', bg: '#FFF7ED' };
  if (value <= 90)  return { label: 'Poor',      color: '#EF4444', bg: '#FEF2F2' };
  if (value <= 150) return { label: 'Very Poor', color: '#DC2626', bg: '#FEF2F2' };
  return { label: 'Hazardous', color: '#7F1D1D', bg: '#FEF2F2' };
}

function getEpisodeInfo(state) {
  switch (state) {
    case 'episode':   return { label: 'Active Incident', color: '#EF4444', bg: '#FEF2F2', icon: <AlertTriangle size={18} /> };
    case 'improving': return { label: 'Improving',       color: '#F97316', bg: '#FFF7ED', icon: <TrendingDown size={18} /> };
    case 'uncertain': return { label: 'Uncertain',       color: '#EAB308', bg: '#FEFCE8', icon: <RefreshCw size={18} /> };
    default:          return { label: 'All Clear',       color: '#22C55E', bg: '#F0FDF4', icon: <CheckCircle size={18} /> };
  }
}

function getTimingSummary(forecasts) {
  if (!forecasts) return null;
  let peak = { horizon: 1, value: -Infinity };
  let best = { horizon: 1, value: Infinity };
  for (const h of HORIZONS) {
    const val = forecasts[String(h)]?.predicted_pm25;
    if (val == null) continue;
    if (val > peak.value) peak = { horizon: h, value: val };
    if (val < best.value) best = { horizon: h, value: val };
  }
  if (peak.value === -Infinity) return null;
  return {
    peakLabel: `+${peak.h}h`,
    peakValue: peak.value,
    bestLabel: `+${best.h}h`,
    bestValue: best.value,
  };
}


/* ═══════════════════════════════════════════════════════════════
   SKELETON LOADERS
   ═══════════════════════════════════════════════════════════════ */

function HeroSkeleton() {
  return (
    <div className="premium-hero" aria-busy="true">
      <div className="premium-hero__text">
        <div style={{ width: 140, height: 12, borderRadius: 4, background: 'var(--lp-bg-tertiary)' }} />
        <div style={{ width: 280, height: 28, borderRadius: 6, background: 'var(--lp-bg-tertiary)', marginTop: 12 }} />
        <div style={{ width: 220, height: 14, borderRadius: 4, background: 'var(--lp-bg-tertiary)', marginTop: 8 }} />
      </div>
      <div className="premium-hero__gauge">
        <AQIGauge value={null} size="hero" loading />
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   SECTION 1: PREMIUM HERO — AQI Gauge + Current Status
   ═══════════════════════════════════════════════════════════════ */

function HeroSection({ currentPM25, loading }) {
  const info = getAirQualityInfo(currentPM25);
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <section className="premium-hero" aria-label="Current air quality in Lahore">
      <div className="premium-hero__text">
        <div className="premium-hero__eyebrow">
          <MapPin size={16} />
          <span>Lahore, Punjab</span>
          <span style={{ color: 'var(--lp-text-muted)' }}>·</span>
          <span>{today}</span>
        </div>
        <h1 className="premium-hero__title">
          How's the Air<br />Right Now?
        </h1>
        <p className="premium-hero__subtitle">
          {loading
            ? 'Checking air quality sensors across Lahore...'
            : currentPM25 != null
              ? (
                <>
                  Air quality is currently{' '}
                  <strong style={{ color: info.color }}>
                    {info.label.toLowerCase()}
                  </strong>.
                  {currentPM25 <= 25 && " It's safe to be outside."}
                  {currentPM25 > 25 &&
                    currentPM25 <= 55 &&
                    " Most people can go outside, but take care if you're sensitive."}
                  {currentPM25 > 55 &&
                    currentPM25 <= 150 &&
                    ' Consider staying indoors if possible.'}
                  {currentPM25 > 150 &&
                    ' Please stay inside and keep windows closed.'}
                </>
              )
              : 'Waiting for sensor data...'}
        </p>

        <div className="premium-hero__status">
          <span
            className="premium-hero__status-chip"
            style={{
              background: loading ? 'var(--lp-bg-tertiary)' : info.bg,
              color: loading ? 'var(--lp-text-muted)' : info.color,
            }}
          >
            <span
              className="premium-hero__live-dot"
              style={{ background: loading ? 'var(--lp-text-muted)' : info.color }}
            />
            {loading ? 'Loading...' : 'Live'}
          </span>
          {currentPM25 != null && (
            <span className="premium-hero__status-chip">{info.label}</span>
          )}
        </div>
      </div>

      <div className="premium-hero__gauge">
        <AQIGauge value={currentPM25} size="hero" loading={loading} />
      </div>
    </section>
  );
}


/* ═══════════════════════════════════════════════════════════════
   SECTION 2: FORECAST STRIP — Simple timeline
   ═══════════════════════════════════════════════════════════════ */

function ForecastStrip({ forecasts, loading }) {
  if (loading || !forecasts) return null;

  const items = [
    { label: 'Now', horizon: '1' },
    ...HORIZONS.filter(h => h !== 1).map(h => ({
      label: `+${HORIZON_META[h].shortLabel}`,
      horizon: String(h),
    })),
  ];

  return (
    <div className="premium-forecast">
      <div className="premium-forecast__title">24-Hour Outlook</div>
      <div className="premium-forecast__items">
        {items.map((item, idx) => {
          const f = forecasts[item.horizon];
          const pm25 = f?.predicted_pm25;
          const itemInfo = getAirQualityInfo(pm25);

          return (
            <div
              key={item.horizon}
              className={`premium-forecast__item${idx === 0 ? ' premium-forecast__item--active' : ''}`}
            >
              <span className="premium-forecast__time">{item.label}</span>
              <span
                className="premium-forecast__value"
                style={{
                  color:
                    pm25 != null ? itemInfo.color : 'var(--lp-text-muted)',
                }}
              >
                {pm25 != null ? Math.round(pm25) : '—'}
              </span>
              <span className="premium-forecast__label">
                {pm25 != null ? itemInfo.label : 'No data'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   SECTION 3: PRIMARY INSIGHT — Human-readable assessment
   ═══════════════════════════════════════════════════════════════ */

function PrimaryInsight({ episode, forecasts }) {
  const state = episode?.state || 'normal';
  const epInfo = getEpisodeInfo(state);
  const narrative = episode?.narrative;
  const trajectory = episode?.trajectory;
  const currentPM25 = forecasts?.['1']?.predicted_pm25;
  const timing = getTimingSummary(forecasts);

  return (
    <div className="premium-insight">
      <div className="premium-insight__header">
        <span
          className="premium-insight__badge"
          style={{ color: epInfo.color, background: epInfo.bg }}
        >
          {epInfo.icon} {epInfo.label}
        </span>
        {trajectory && (
          <span
            className="premium-insight__trend"
            style={{ color: 'var(--lp-text-secondary)' }}
          >
            {trajectory === 'rising' && '↗ Trending upward'}
            {trajectory === 'falling' && '↘ Trending downward'}
            {trajectory === 'stable' && '→ Holding steady'}
          </span>
        )}
      </div>

      {narrative ? (
        <p className="premium-insight__narrative">{narrative}</p>
      ) : currentPM25 != null ? (
        <p className="premium-insight__narrative">
          The air in Lahore is currently{' '}
          {getAirQualityInfo(currentPM25).label.toLowerCase()}.
          {timing && (
            <>
              {timing.peakValue > currentPM25 ? (
                <>
                  It may get worse around{' '}
                  <strong>{timing.peakLabel}</strong>, then improve toward{' '}
                  <strong>{timing.bestLabel}</strong>.
                </>
              ) : (
                <>
                  It should improve toward{' '}
                  <strong>{timing.bestLabel}</strong>.
                </>
              )}
            </>
          )}
        </p>
      ) : (
        <p className="premium-insight__narrative">
          Waiting for current conditions...
        </p>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   SECTION 4: QUICK ACTIONS — Service cards
   ═══════════════════════════════════════════════════════════════ */

const QUICK_ACTIONS = [
  {
    to: '/city-map',
    icon: <Map size={24} />,
    title: 'City Map',
    desc: 'See pollution levels across every neighborhood',
    color: 'var(--lp-brand-50)',
  },
  {
    to: '/air-quality',
    icon: <BarChart3 size={24} />,
    title: 'Full Forecast',
    desc: 'Detailed forecast and what to expect',
    color: '#FFF7ED',
  },
  {
    to: '/alerts',
    icon: <Bell size={24} />,
    title: 'Alerts',
    desc: 'Get notified about dangerous conditions',
    color: '#FEF2F2',
  },
  {
    to: '/insights',
    icon: <TrendingUp size={24} />,
    title: 'Trends',
    desc: 'Historical patterns and seasonal analysis',
    color: '#F0FDF4',
  },
];

function QuickActions() {
  return (
    <div className="premium-section">
      <div className="premium-section__header">
        <div className="premium-section__icon"><Zap size={20} /></div>
        <span className="premium-section__title">Explore</span>
      </div>
      <div className="premium-actions">
        {QUICK_ACTIONS.map(action => (
          <Link key={action.to} to={action.to} className="premium-action-card">
            <div
              className="premium-action-card__icon"
              style={{ background: action.color, fontSize: '24px' }}
            >
              {action.icon}
            </div>
            <span className="premium-action-card__title">{action.title}</span>
            <span className="premium-action-card__desc">{action.desc}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   SECTION 5: TODAY IN LAHORE — Key metrics
   ═══════════════════════════════════════════════════════════════ */

function TodayMetrics({ forecasts, stations, episode }) {
  const currentPM25 = forecasts?.['1']?.predicted_pm25;
  const info = getAirQualityInfo(currentPM25);
  const timing = getTimingSummary(forecasts);
  const epInfo = getEpisodeInfo(episode?.state);
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="premium-section">
      <div className="premium-section__header">
        <div className="premium-section__icon"><BarChart3 size={20} /></div>
        <span className="premium-section__title">Today in Lahore</span>
        <span className="premium-section__subtitle">{today}</span>
      </div>

      <div className="premium-metrics">
        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: info.bg }}>
            <Wind size={20} />
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Air Quality</span>
            <span className="premium-metric__value" style={{ color: info.color }}>
              {currentPM25 != null ? info.label : '—'}
            </span>
            <span className="premium-metric__sub">
              {currentPM25 != null ? 'Right now' : 'Loading...'}
            </span>
          </div>
        </div>

        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: '#FFF7ED' }}>
            <Clock size={20} />
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Forecast Peak</span>
            <span className="premium-metric__value">
              {timing ? getAirQualityInfo(timing.peakValue).label : '—'}
            </span>
            <span className="premium-metric__sub">
              {timing ? `Expected ${timing.peakLabel}` : 'Checking forecasts...'}
            </span>
          </div>
        </div>

        <div className="premium-metric">
          <div className="premium-metric__icon" style={{ background: epInfo.bg }}>
            {epInfo.icon}
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Status</span>
            <span className="premium-metric__value" style={{ color: epInfo.color }}>
              {epInfo.label}
            </span>
            <span className="premium-metric__sub">
              {episode?.trajectory === 'rising'
                ? 'Getting worse'
                : episode?.trajectory === 'falling'
                  ? 'Getting better'
                  : 'Steady conditions'}
            </span>
          </div>
        </div>

        <div className="premium-metric">
          <div
            className="premium-metric__icon"
            style={{ background: 'var(--lp-brand-50, #f0fdf4)' }}
          >
            <Radio size={20} />
          </div>
          <div className="premium-metric__text">
            <span className="premium-metric__label">Sensors</span>
            <span className="premium-metric__value">{stations.length || '—'}</span>
            <span className="premium-metric__sub">
              {stations.length > 0 ? 'Active monitors' : 'Loading stations...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */

export default function HomePage() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const { forecasts, loading: forecastLoading } = useForecast();
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const { online } = useHealth();
  const { analogs, loading: analogsLoading } = useHistoricalAnalogs();
  const [stations, setStations] = useState([]);

  const loading = forecastLoading || episodeLoading;
  const currentPM25 = forecasts?.['1']?.predicted_pm25 ?? null;

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetchStations() {
      try {
        const data = await getStations({ signal: AbortSignal.timeout(10000) });
        if (!cancelled) setStations(data.stations || []);
      } catch {
        /* optional — stations degrade gracefully */
      }
    }
    fetchStations();
    return () => {
      cancelled = true;
    };
  }, [isDemo]);

  return (
    <div className="page page--home">
      {/* Alert Banner — Danger warning */}
      <AlertBanner pm25={currentPM25} />

      {/* Hero — AQI Gauge + Current Status */}
      {loading && !currentPM25 ? (
        <HeroSkeleton />
      ) : (
        <HeroSection currentPM25={currentPM25} loading={forecastLoading} />
      )}

      {/* Forecast Strip — 24-hour outlook */}
      <ForecastStrip forecasts={forecasts} loading={forecastLoading} />

      {/* Primary Insight — What's happening */}
      {!loading && <PrimaryInsight episode={episode} forecasts={forecasts} />}

      {/* Quick Actions */}
      <QuickActions />

      {/* Today in Lahore — Key metrics */}
      <TodayMetrics forecasts={forecasts} stations={stations} episode={episode} />

      {/* Health Guidance */}
      {!loading && currentPM25 != null && (
        <HealthGuidance pm25={currentPM25} />
      )}

      {/* Pollution Story */}
      {!loading && forecasts && <PollutionStory forecasts={forecasts} />}

      {/* Why Panel */}
      {!loading && <WhyPanel episode={episode} forecasts={forecasts} />}

      {/* Historical Comparison */}
      {!loading && (
        <HistoricalComparison analogs={analogs} loading={analogsLoading} />
      )}
    </div>
  );
}
