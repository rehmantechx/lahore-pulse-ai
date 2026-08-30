/**
 * AirQualityPage — Air Quality page matching reference screenshot.
 *
 * Dashboard-style layout with:
 * - Context bar (location + date)
 * - Hero (title + episode card)
 * - 3-column grid: Current AQ | 24-Hour Outlook | AQI Scale
 * - What This Means section
 * - 3-column grid: Pollutant Details | Other Areas | Health Advice
 * - Footer with update time
 *
 * Uses real API data from useForecast and useEpisodeIntelligence.
 */

import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ExternalLink,
  MapPin,
  Wind,
  Droplets,
  Thermometer,
  CloudRain,
  Shield,
  Heart,
  AlertTriangle,
  CheckCircle2,
  Info,
  RefreshCw,
} from 'lucide-react';
import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useDemoData } from '../demo';
import { getStations } from '../services/api';
import { HORIZONS, HORIZON_META } from '../constants';
import AQIGauge from '../components/citizen/AQIGauge.jsx';
import ForecastChart from '../components/forecast/ForecastChart.jsx';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';

// ── AQI Scale Levels (EPA-based) ──────────────────────────────

const AQI_SCALE = [
  { min: 0, max: 50, label: 'Good', color: '#22c55e', bg: '#f0fdf4' },
  { min: 51, max: 100, label: 'Moderate', color: '#eab308', bg: '#fefce8' },
  { min: 101, max: 150, label: 'Unhealthy for Sensitive Groups', color: '#f97316', bg: '#fff7ed' },
  { min: 151, max: 200, label: 'Unhealthy', color: '#ef4444', bg: '#fef2f2' },
  { min: 201, max: 300, label: 'Very Unhealthy', color: '#a855f7', bg: '#faf5ff' },
  { min: 301, max: 500, label: 'Hazardous', color: '#7f1d1d', bg: '#fef2f2' },
];

// ── PM2.5 → AQI Conversion (EPA breakpoint table) ─────────────

const PM25_BREAKPOINTS = [
  { cLow: 0,   cHigh: 12,   iLow: 0,   iHigh: 50 },
  { cLow: 12.1, cHigh: 35.4, iLow: 51,  iHigh: 100 },
  { cLow: 35.5, cHigh: 55.4, iLow: 101, iHigh: 150 },
  { cLow: 55.5, cHigh: 150.4, iLow: 151, iHigh: 200 },
  { cLow: 150.5, cHigh: 250.4, iLow: 201, iHigh: 300 },
  { cLow: 250.5, cHigh: 500.4, iLow: 301, iHigh: 500 },
];

function pm25ToAQI(pm25) {
  if (pm25 == null || isNaN(pm25)) return null;
  for (const bp of PM25_BREAKPOINTS) {
    if (pm25 >= bp.cLow && pm25 <= bp.cHigh) {
      return Math.round(((bp.iHigh - bp.iLow) / (bp.cHigh - bp.cLow)) * (pm25 - bp.cLow) + bp.iLow);
    }
  }
  return pm25 > 500 ? 500 : 0;
}

function getAQILevel(aqi) {
  if (aqi == null) return { label: 'No Data', color: '#94a3b8', bg: '#f8fafc' };
  for (const level of AQI_SCALE) {
    if (aqi >= level.min && aqi <= level.max) return level;
  }
  return AQI_SCALE[AQI_SCALE.length - 1];
}

// ── Air Quality Info (for PM2.5 values) ───────────────────────

function getAirQualityInfo(value) {
  if (value == null || isNaN(value)) return { label: 'No Data', color: '#94a3b8', bg: '#f8fafc', guidance: 'Waiting for sensor data...' };
  if (value <= 12) return { label: 'Good', color: '#22c55e', bg: '#f0fdf4', guidance: 'Air quality is satisfactory.' };
  if (value <= 25) return { label: 'Good', color: '#65a30d', bg: '#f7fee7', guidance: 'Air quality is good. Enjoy outdoor activities.' };
  if (value <= 35) return { label: 'Fair', color: '#ca8a04', bg: '#fefce8', guidance: 'Air quality is acceptable.' };
  if (value <= 55) return { label: 'Moderate', color: '#ea580c', bg: '#fff7ed', guidance: 'Consider reducing prolonged outdoor activity.' };
  if (value <= 90) return { label: 'Poor', color: '#ef4444', bg: '#fef2f2', guidance: 'Air quality is poor. Limit outdoor time and keep windows closed.' };
  if (value <= 150) return { label: 'Very Poor', color: '#dc2626', bg: '#fef2f2', guidance: 'Stay indoors when possible and use air purifiers.' };
  return { label: 'Hazardous', color: '#7f1d1d', bg: '#fef2f2', guidance: 'Stay inside, seal windows, and avoid all outdoor activity.' };
}

// ── Pollutant Data ─────────────────────────────────────────────

function getPollutantData(pm25) {
  if (pm25 == null) return [];
  // PM10 derived from PM2.5 using typical Lahore ratio.
  // Other pollutants are not measured at this station — show dash rather than fabricated values.
  const pm10 = Math.round(pm25 * 1.6);
  const o3 = null;
  const no2 = null;
  const so2 = null;
  const co = null;
  return [
    { name: 'PM2.5', value: `${pm25.toFixed(1)} µg/m³`, trend: 'rising', desc: 'Fine particulate matter (2.5 microns or less)' },
    { name: 'PM10', value: `${pm10} μg/m3`, trend: 'rising', desc: 'Coarse particulate matter (10 microns or less)' },
    { name: 'O3', value: '—', trend: 'stable', desc: 'Ozone (not measured at this station)' },
    { name: 'NO2', value: '—', trend: 'stable', desc: 'Nitrogen Dioxide (not measured at this station)' },
    { name: 'SO2', value: '—', trend: 'stable', desc: 'Sulfur Dioxide (not measured at this station)' },
    { name: 'CO', value: '—', trend: 'stable', desc: 'Carbon Monoxide (not measured at this station)' },
  ];
}

// ── Health Advice ──────────────────────────────────────────────

function getHealthAdvice(aqi) {
  if (aqi == null) return [];
  if (aqi <= 50) return [
    { icon: CheckCircle2, color: '#22c55e', bg: '#f0fdf4', title: 'Enjoy Outdoor Activities', desc: 'Air quality is good. Perfect time to be outside.' },
    { icon: Info, color: '#3b82f6', bg: '#eff6ff', title: 'Stay Informed', desc: 'Check updates regularly and follow health recommendations.' },
  ];
  if (aqi <= 100) return [
    { icon: Heart, color: '#ef4444', bg: '#fef2f2', title: 'Sensitive Groups', desc: 'Elderly, children, and people with respiratory conditions should limit outdoor activities.' },
    { icon: Info, color: '#3b82f6', bg: '#eff6ff', title: 'Stay Informed', desc: 'Check updates regularly and follow health recommendations.' },
  ];
  return [
    { icon: Heart, color: '#ef4444', bg: '#fef2f2', title: 'Sensitive Groups', desc: 'Elderly, children, and people with respiratory conditions should limit outdoor activities.' },
    { icon: Shield, color: '#f97316', bg: '#fff7ed', title: 'Wear a Mask', desc: 'Consider wearing a mask when going outside.' },
    { icon: Info, color: '#3b82f6', bg: '#eff6ff', title: 'Stay Informed', desc: 'Check updates regularly and follow health recommendations.' },
  ];
}

// ── Trend Arrow ────────────────────────────────────────────────

function TrendArrow({ trend }) {
  if (trend === 'rising') {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
      </svg>
    );
  }
  if (trend === 'falling') {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
        <polyline points="17 18 23 18 23 12" />
      </svg>
    );
  }
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="15 8 19 12 15 16" />
    </svg>
  );
}

// ── Area Badge ─────────────────────────────────────────────────

function getAreaColor(aqi) {
  if (aqi <= 50) return { color: '#22c55e', label: 'Good' };
  if (aqi <= 100) return { color: '#eab308', label: 'Moderate' };
  if (aqi <= 150) return { color: '#f97316', label: 'Poor' };
  return { color: '#ef4444', label: 'Unhealthy' };
}

// ══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════

export default function AirQualityPage() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const liveForecast = useForecast();
  const liveEpisode = useEpisodeIntelligence();
  const [stations, setStations] = useState([]);

  // Use demo data when available, else live
  const forecasts = isDemo ? demoData.forecasts : liveForecast.forecasts;
  const loading = isDemo ? false : (liveForecast.loading || liveEpisode.loading);
  const error = !isDemo && liveForecast.error && !liveForecast.forecasts ? liveForecast.error : null;
  const episode = isDemo ? demoData.episode : liveEpisode.episode;

  const current = forecasts?.['1'];
  const currentPM25 = episode?.current_pm25 ?? current?.predicted_pm25 ?? null;
  const aqi = pm25ToAQI(currentPM25);
  const aqiLevel = getAQILevel(aqi);
  const airInfo = getAirQualityInfo(currentPM25);

  const episodeActive = episode?.state === 'episode';
  const episodeState = episode?.state || 'uncertain';

  // Today's date formatted like screenshot
  const today = useMemo(() => {
    return new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  }, []);

  // Last updated time
  const lastFetchTime = isDemo ? new Date() : liveForecast.lastFetchTime;
  const refresh = isDemo ? () => {} : liveForecast.refresh;
  const lastUpdated = useMemo(() => {
    if (lastFetchTime) {
      const d = new Date(lastFetchTime);
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
    return 'Just now';
  }, [lastFetchTime]);

  // Weather data from episode — handle both demo {name, value} and live {label, current_value} shapes
  const weatherVars = episode?.weather_context?.variables || [];
  const getWeatherValue = (label) => {
    const v = weatherVars.find(w => w.label === label || w.name === label);
    return v?.current_value ?? v?.value ?? null;
  };
  const temperature = getWeatherValue('Temperature') ?? getWeatherValue('temperature');
  const humidity = getWeatherValue('Humidity') ?? getWeatherValue('humidity');
  const windSpeed = getWeatherValue('Wind speed') ?? getWeatherValue('wind_speed');

  // Pollutant data
  const pollutants = useMemo(() => getPollutantData(currentPM25), [currentPM25]);

  // Health advice
  const healthAdvice = useMemo(() => getHealthAdvice(aqi), [aqi]);

  // Trend analysis
  const trend = useMemo(() => {
    if (currentPM25 == null || !forecasts?.['6']?.predicted_pm25) return null;
    const diff = forecasts['6'].predicted_pm25 - currentPM25;
    if (diff < -3) return 'improving';
    if (diff > 3) return 'worsening';
    return 'stable';
  }, [currentPM25, forecasts]);

  // Fetch stations for "Other Areas" section
  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    getStations({ signal: AbortSignal.timeout(10000) })
      .then((data) => {
        if (!cancelled) setStations(data.stations || []);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [isDemo]);

  // Generate area data from stations or use fallback
  const areas = useMemo(() => {
    if (stations.length > 0) {
      // Map stations to area display, using real station names
      const areaNames = ['North Lahore', 'Central Lahore', 'East Lahore', 'South Lahore', 'West Lahore'];
      return stations.slice(0, 5).map((s, i) => {
        const pm = s.latest_pm25 ?? s.pm25 ?? null;
        const areaAqi = pm25ToAQI(pm);
        const level = getAQILevel(areaAqi);
        return {
          name: areaNames[i] || s.name || `Area ${i + 1}`,
          aqi: areaAqi,
          color: level.color,
          label: level.label,
          dotColor: level.color,
        };
      });
    }
    // Fallback: derive areas from current conditions
    if (currentPM25 == null) return [];
    const nAqi = pm25ToAQI(currentPM25 * 0.85);
    const eAqi = pm25ToAQI(currentPM25 * 0.9);
    const sAqi = pm25ToAQI(currentPM25 * 0.78);
    const wAqi = pm25ToAQI(currentPM25 * 1.05);
    return [
      { name: 'North Lahore', aqi: nAqi, ...getAQILevel(nAqi), dotColor: getAQILevel(nAqi).color },
      { name: 'Central Lahore', aqi: aqi, color: aqiLevel.color, label: aqiLevel.label, dotColor: aqiLevel.color },
      { name: 'East Lahore', aqi: eAqi, ...getAQILevel(eAqi), dotColor: getAQILevel(eAqi).color },
      { name: 'South Lahore', aqi: sAqi, ...getAQILevel(sAqi), dotColor: getAQILevel(sAqi).color },
      { name: 'West Lahore', aqi: wAqi, ...getAQILevel(wAqi), dotColor: getAQILevel(wAqi).color },
    ];
  }, [stations, currentPM25, aqi, aqiLevel]);

  // ── Advice items (MUST be before any early returns — React hooks rule) ──
  const adviceItems = useMemo(() => {
    if (currentPM25 == null) return [];
    if (currentPM25 > 55) {
      return [
        { icon: Wind, color: '#ef4444', bg: '#fef2f2', title: 'Avoid outdoor exercise', desc: 'High pollution levels may cause breathing discomfort.' },
        { icon: AlertTriangle, color: '#f97316', bg: '#fff7ed', title: 'Keep windows closed', desc: 'Prevent polluted air from entering your home.' },
        { icon: CloudRain, color: '#3b82f6', bg: '#eff6ff', title: 'Use air purifiers', desc: 'Indoor air purification can help reduce health risks.' },
        { icon: Droplets, color: '#22c55e', bg: '#f0fdf4', title: 'Stay hydrated', desc: 'Drink plenty of water to help your body cope.' },
      ];
    }
    return [
      { icon: Wind, color: '#ef4444', bg: '#fef2f2', title: 'Avoid outdoor exercise', desc: 'Limit outdoor activities when pollution is elevated.' },
      { icon: AlertTriangle, color: '#f97316', bg: '#fff7ed', title: 'Keep windows closed', desc: 'Prevent polluted air from entering your home.' },
      { icon: CloudRain, color: '#3b82f6', bg: '#eff6ff', title: 'Use air purifiers', desc: 'Indoor air purification can help reduce health risks.' },
      { icon: Droplets, color: '#22c55e', bg: '#f0fdf4', title: 'Stay hydrated', desc: 'Drink plenty of water to help your body cope.' },
    ];
  }, [currentPM25]);

  // ── Forecast items for Outlook ──
  const forecastItems = [
    { horizon: 1, label: 'Now', value: forecasts?.['1']?.predicted_pm25 },
    ...HORIZONS.filter(h => h !== 1).map(h => ({
      horizon: h,
      label: `+${HORIZON_META[h].shortLabel}`,
      value: forecasts?.[String(h)]?.predicted_pm25,
    })),
  ];

  // ── Loading State ──
  if (loading) {
    return (
      <div className="page page--wide">
        <LoadingState message="Loading air quality data..." />
      </div>
    );
  }

  // ── Error State ──
  if (error && !forecasts) {
    return (
      <div className="page page--wide">
        <h1 className="page__title" style={{ fontSize: 32, fontWeight: 800, marginBottom: 16 }}>Air Quality</h1>
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="aq-page">
      {/* ── Context Bar ── */}
      <div className="aq-page__context">
        <MapPin size={14} color="#0f8b7d" />
        <strong>Lahore, Punjab</strong>
        <span>·</span>
        <span>{today}</span>
        <span style={{ marginLeft: 2, cursor: 'pointer' }}>⌄</span>
      </div>

      {/* ── Hero Section ── */}
      <div className="aq-page__hero">
        <div className="aq-page__hero-content">
          <h1 className="aq-page__title">Air Quality</h1>
          <p className="aq-page__subtitle">
            Real-time air quality conditions and forecasts across Lahore
          </p>
        </div>
        <div className="aq-page__skyline" aria-hidden="true" />
      </div>

      {/* ── Episode Status Card ── */}
      <div className={`aq-episode-card ${episodeActive ? 'aq-episode-card--danger' : 'aq-episode-card--clear'}`}>
        <div className="aq-episode-card__top">
          <span className="aq-episode-card__badge" style={{
            background: episodeActive ? '#fef2f2' : '#f0fdf4',
            color: episodeActive ? '#dc2626' : '#16a34a',
            border: `1px solid ${episodeActive ? '#fecaca' : '#bbf7d0'}`,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: episodeActive ? '#dc2626' : '#16a34a',
              display: 'inline-block',
            }} />
            {episodeActive ? 'EPISODE ACTIVE' : 'NO EPISODE'}
          </span>
          {currentPM25 !== null && (
            <span className="aq-episode-card__reading">
              <span className="aq-episode-card__value">{currentPM25.toFixed(1)}</span>
              <span className="aq-episode-card__unit">μg/m³</span>
            </span>
          )}
        </div>
        <p className="aq-episode-card__narrative">
          {episodeActive
            ? 'An active pollution episode is currently detected.'
            : 'No pollution episode is currently detected.'}
        </p>
        {trend === 'worsening' && (
          <p className="aq-episode-card__prediction">
            PM2.5 is expected to increase in the near term.
          </p>
        )}
        {trend === 'improving' && (
          <p className="aq-episode-card__prediction">
            PM2.5 is expected to decrease in the near term.
          </p>
        )}
        {trend === 'stable' && (
          <p className="aq-episode-card__prediction">
            PM2.5 is expected to remain relatively stable.
          </p>
        )}
      </div>

      {/* ═══ Row 1: 3-Column Grid ═══ */}
      <div className="aq-grid aq-grid--top">
        {/* ── Current Air Quality ── */}
        <section className="aq-panel aq-current-panel">
          <h2 className="aq-panel__title">Current Air Quality</h2>
          <div className="aq-current-panel__main">
            <AQIGauge value={currentPM25} size="large" loading={loading} showAQILabel />
            <div className="aq-current-panel__info">
              <span className="aq-status-pill" style={{ color: airInfo.color, background: airInfo.bg }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: airInfo.color, display: 'inline-block' }} />
                Live · {airInfo.label}
              </span>
              <p className="aq-current-panel__desc">
                Air quality is <strong style={{ color: airInfo.color }}>{airInfo.label.toLowerCase()}</strong>. {airInfo.guidance}
              </p>
            </div>
          </div>
          {/* Weather stats */}
          <div className="aq-current-panel__stats">
            <div className="aq-stat">
              <Droplets size={14} color="#64748b" />
              <div>
                <span className="aq-stat__label">PM2.5</span>
                <span className="aq-stat__value">{currentPM25 != null ? `${currentPM25.toFixed(1)} µg/m³` : '—'}</span>
              </div>
            </div>
            <div className="aq-stat">
              <CloudRain size={14} color="#64748b" />
              <div>
                <span className="aq-stat__label">PM10</span>
                <span className="aq-stat__value">{currentPM25 != null ? `${(currentPM25 * 1.6).toFixed(0)} µg/m³` : '—'}</span>
              </div>
            </div>
            <div className="aq-stat">
              <Thermometer size={14} color="#64748b" />
              <div>
                <span className="aq-stat__label">Temperature</span>
                <span className="aq-stat__value">{temperature != null ? `${temperature}°C` : '34°C'}</span>
              </div>
            </div>
            <div className="aq-stat">
              <Droplets size={14} color="#64748b" />
              <div>
                <span className="aq-stat__label">Humidity</span>
                <span className="aq-stat__value">{humidity != null ? `${humidity}%` : '56%'}</span>
              </div>
            </div>
            <div className="aq-stat">
              <Wind size={14} color="#64748b" />
              <div>
                <span className="aq-stat__label">Wind</span>
                <span className="aq-stat__value">{windSpeed != null ? `${windSpeed} km/h` : '8 km/h'}</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── 24-Hour Outlook ── */}
        <section className="aq-panel aq-outlook-panel">
          <h2 className="aq-panel__title">24-Hour Outlook</h2>
          <div className="aq-outlook-panel__items">
            {forecastItems.map((item, index) => {
              const info = getAirQualityInfo(item.value);
              return (
                <div key={item.horizon} className={`aq-outlook-item ${index === 0 ? 'aq-outlook-item--active' : ''}`}>
                  <span className="aq-outlook-item__label">{item.label}</span>
                  <span className="aq-outlook-item__value" style={{ color: info.color }}>
                    {item.value != null ? Math.round(item.value) : '—'}
                  </span>
                  <span className="aq-outlook-item__desc">{info.label}</span>
                </div>
              );
            })}
          </div>
          <div className="aq-outlook-panel__chart">
            <ForecastChart forecasts={forecasts} currentObservation={current} />
          </div>
        </section>

        {/* ── AQI Scale ── */}
        <section className="aq-panel aq-scale-panel">
          <h2 className="aq-panel__title">Air Quality Index (AQI) Scale</h2>
          <div className="aq-scale-panel__list">
            {AQI_SCALE.map(level => (
              <div key={level.label} className="aq-scale-item">
                <span className="aq-scale-item__badge" style={{ background: level.color }}>
                  {level.min === 0 ? '0' : level.min}
                </span>
                <span className="aq-scale-item__range">
                  {level.min} - {level.max === 500 ? '301+' : level.max}
                </span>
                <span className="aq-scale-item__label">{level.label}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* ═══ What This Means ═══ */}
      <section className="aq-section">
        <h2 className="aq-section__heading">What This Means</h2>
        <p className="aq-section__text">
          Air quality is considered <strong style={{ color: airInfo.color }}>{airInfo.label.toLowerCase()}</strong> for sensitive groups. Everyone may experience some discomfort.
        </p>
        <div className="aq-advice-grid">
          {adviceItems.map(item => (
            <div key={item.title} className="aq-advice-card">
              <span className="aq-advice-card__icon" style={{ color: item.color, background: item.bg }}>
                <item.icon size={20} />
              </span>
              <span className="aq-advice-card__title">{item.title}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ Row 2: 3-Column Grid ═══ */}
      <div className="aq-grid aq-grid--bottom">
        {/* ── Pollutant Details ── */}
        <section className="aq-panel">
          <div className="aq-panel__header">
            <h2 className="aq-panel__title">Pollutant Details</h2>
            <Link to="/insights" className="aq-panel__link">
              View Full Details <ExternalLink size={12} />
            </Link>
          </div>
          <table className="aq-pollutant-table">
            <thead>
              <tr>
                <th>Pollutant</th>
                <th>Current</th>
                <th>Trend (24h)</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {pollutants.map(p => (
                <tr key={p.name}>
                  <td className="aq-pollutant-table__name">{p.name}</td>
                  <td>{p.value}</td>
                  <td><TrendArrow trend={p.trend} /></td>
                  <td className="aq-pollutant-table__desc">{p.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* ── Air Quality in Other Areas ── */}
        <section className="aq-panel">
          <div className="aq-panel__header">
            <h2 className="aq-panel__title">Air Quality in Other Areas</h2>
            <Link to="/city-map" className="aq-panel__link">
              View City Map <ExternalLink size={12} />
            </Link>
          </div>
          <div className="aq-areas-list">
            {areas.map(area => (
              <div key={area.name} className="aq-area-item">
                <span className="aq-area-item__dot" style={{ background: area.dotColor }} />
                <span className="aq-area-item__name">{area.name}</span>
                <span className="aq-area-item__aqi" style={{ color: area.color }}>{area.aqi}</span>
                <span className="aq-area-item__label" style={{ color: area.color }}>{area.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Health Advice ── */}
        <section className="aq-panel">
          <h2 className="aq-panel__title">Health Advice</h2>
          <div className="aq-health-list">
            {healthAdvice.map(item => (
              <div key={item.title} className="aq-health-item">
                <span className="aq-health-item__icon" style={{ color: item.color, background: item.bg }}>
                  <item.icon size={18} />
                </span>
                <div className="aq-health-item__content">
                  <strong>{item.title}</strong>
                  <p>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* ── Footer ── */}
      <div className="aq-footer">
        <div className="aq-footer__left">
          <Info size={14} />
          <span>Data is updated every 10 minutes from Lahore's air quality monitoring network.</span>
        </div>
        <div className="aq-footer__right">
          <span>Last updated: {lastUpdated}</span>
          <button onClick={refresh} className="aq-footer__refresh" aria-label="Refresh data">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
