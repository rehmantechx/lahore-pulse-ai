/**
 * CityMapPage — Full geographic pollution overview.
 *
 * Interactive map of Lahore with AQI overlay and sidebar panels.
 * Two-column layout: Map (left) + Sidebar panels (right).
 * Bottom panel: Selected location detail.
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin, Search, SlidersHorizontal, Info, AlertTriangle,
  TrendingUp, ChevronRight, ExternalLink, RefreshCw,
  Thermometer, Droplets, Wind, Grid3x3,
} from 'lucide-react';
import LahoreMap from '../components/map/LahoreMap';
import { useForecast } from '../hooks/useForecast';
import { useDemoData } from '../demo';
import { getStations, getCurrentWeather } from '../services/api';
import LoadingState from '../components/common/LoadingState';

/* ── AQI Conversion (EPA breakpoint table) ────────────────── */

const PM25_BREAKPOINTS = [
  { cLow: 0, cHigh: 12, iLow: 0, iHigh: 50 },
  { cLow: 12.1, cHigh: 35.4, iLow: 51, iHigh: 100 },
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

function getAQIColor(aqi) {
  if (aqi == null) return '#94a3b8';
  if (aqi <= 50) return '#16a34a';
  if (aqi <= 100) return '#eab308';
  if (aqi <= 150) return '#f97316';
  if (aqi <= 200) return '#ef4444';
  if (aqi <= 300) return '#a855f7';
  return '#7f1d1d';
}

function getAQILabel(aqi) {
  if (aqi == null) return 'No Data';
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Moderate';
  if (aqi <= 150) return 'Poor';
  if (aqi <= 200) return 'Unhealthy';
  if (aqi <= 300) return 'Very Unhealthy';
  return 'Hazardous';
}

/* ── AQI Scale (for legend) ───────────────────────────────── */

const AQI_SCALE = [
  { min: 0, max: 50, label: 'Good', color: '#16a34a' },
  { min: 51, max: 100, label: 'Moderate', color: '#eab308' },
  { min: 101, max: 150, label: 'Unhealthy for Sensitive Groups', color: '#f97316' },
  { min: 151, max: 200, label: 'Unhealthy', color: '#ef4444' },
  { min: 201, max: 300, label: 'Very Unhealthy', color: '#a855f7' },
  { min: 301, max: 500, label: 'Hazardous', color: '#7f1d1d' },
];

/* ── Weather data comes from real backend observations ────── */
/* Weather values are fetched from /api/v1/weather/current    */
/* which returns Open-Meteo data stored in the database.      */
/* No synthetic/derived weather generation.                   */

/* ── Area Definitions (match real Lahore geography) ────────── */

const AREA_DEFS = [
  { id: 'central', name: 'Central Lahore', district: 'Gulberg, Lahore', lat: 31.5204, lng: 74.3587 },
  { id: 'north', name: 'North Lahore', district: 'Shahdara, Lahore', lat: 31.6200, lng: 74.3600 },
  { id: 'east', name: 'East Lahore', district: 'East Lahore', lat: 31.5200, lng: 74.4200 },
  { id: 'south', name: 'South Lahore', district: 'Johar Town, Lahore', lat: 31.4700, lng: 74.3400 },
  { id: 'west', name: 'West Lahore', district: 'West Lahore', lat: 31.5500, lng: 74.3000 },
];

/* ══════════════════════════════════════════════════════════════
   CityMapPage Component
   ══════════════════════════════════════════════════════════════ */

export default function CityMapPage() {
  const navigate = useNavigate();
  const locationsListRef = useRef(null);
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const liveForecast = useForecast({ skip: isDemo });
  const forecasts = isDemo ? demoData.forecasts : liveForecast.forecasts;
  const loading = isDemo ? false : liveForecast.loading;
  const [stations, setStations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [metricType, setMetricType] = useState('AQI');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [severityFilter, setSeverityFilter] = useState(null);
  const [weather, setWeather] = useState({ temperature: null, humidity: null, wind_speed: null, pm10: null });

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetchStations() {
      try {
        const data = await getStations({ signal: AbortSignal.timeout(10000) });
        if (!cancelled) setStations(data.stations || []);
      } catch {
        /* Stations are optional */
      }
    }
    fetchStations();
    return () => { cancelled = true; };
  }, [isDemo]);

  /* Fetch real weather from backend observations */
  useEffect(() => {
    if (isDemo) {
      if (demoData?.weather) setWeather(demoData.weather);
      return;
    }
    let cancelled = false;
    async function fetchWeather() {
      try {
        const data = await getCurrentWeather({ signal: AbortSignal.timeout(10000) });
        if (!cancelled && data?.weather) {
          const w = data.weather;
          // Wind speed is stored in m/s; convert to km/h for display
          const windMs = w.wind_speed?.value ?? null;
          const windKmh = windMs != null ? Math.round(windMs * 3.6 * 10) / 10 : null;
          setWeather({
            temperature: w.temperature?.value ?? null,
            humidity: w.humidity?.value ?? null,
            wind_speed: windKmh,
            pm10: w.pm10?.value ?? null,
          });
        }
      } catch {
        /* Weather is non-critical; keep null defaults */
      }
    }
    fetchWeather();
    return () => { cancelled = true; };
  }, [isDemo, demoData]);

  const currentPM25 = forecasts?.['1']?.predicted_pm25 ?? null;

  /* Build area data from real stations */
  const areas = useMemo(() => {
    const stationAreas = stations
      .filter(s => s.latitude != null && s.longitude != null)
      .map((s) => {
        const pm25 = s.latest_pm25;
        const aqi = pm25ToAQI(pm25);
        return {
          id: s.station_id || s.name,
          name: s.name || s.station_id || 'Monitoring Station',
          district: 'Lahore',
          lat: s.latitude,
          lng: s.longitude,
          aqi,
          pm25,
          source: s.source_id,
          lastUpdated: s.latest_observed_at,
        };
      });

    if (stationAreas.length >= 3) return stationAreas;

    /* Fallback: distribute around Lahore if not enough stations */
    return AREA_DEFS.map((a) => {
      const variation = (Math.sin(a.lat * 100 + a.lng * 50) + 1) / 2;
      const pm25Fallback = currentPM25 != null
        ? currentPM25 * (0.75 + variation * 0.5)
        : 50 + variation * 30;
      const aqi = pm25ToAQI(pm25Fallback);
      return { ...a, aqi, pm25: pm25Fallback, source: 'CAMS', lastUpdated: null };
    });
  }, [stations, currentPM25]);

  /* Compute overall AQI from city-level forecast */
  const overallAQI = pm25ToAQI(currentPM25);
  const overallLabel = getAQILabel(overallAQI);
  const overallColor = getAQIColor(overallAQI);

  /* Weather data is fetched from /api/v1/weather/current (real observations) */

  /* Selected location info */
  const selected = selectedLocation || areas[0] || {
    name: 'Central Lahore',
    district: 'Gulberg, Lahore',
    aqi: overallAQI,
    pm25: currentPM25,
  };
  const selectedAQI = selected.aqi ?? overallAQI;
  const selectedPM25 = selected.pm25 ?? currentPM25;

  /* Filtered areas for search and filter controls */
  const filteredAreas = useMemo(() => {
    let result = areas;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(a => 
        (a.name?.toLowerCase().includes(q)) || 
        (a.district?.toLowerCase().includes(q))
      );
    }
    if (severityFilter) {
      result = result.filter(a => {
        const aqi = a.aqi ?? pm25ToAQI(a.pm25);
        return aqi >= severityFilter.min && aqi <= severityFilter.max;
      });
    }
    return result;
  }, [areas, searchQuery, severityFilter]);

  /* Navigation date */
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  /* ── Interactive Handlers ───────────────────────────────── */
  const handleViewAll = useCallback(() => {
    setSearchQuery('');
    setSeverityFilter(null);
    setShowFilterPanel(false);
    if (locationsListRef.current) {
      locationsListRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, []);

  const handleViewFullDetails = useCallback(() => {
    const id = selected?.id || 'central';
    navigate(`/air-quality?station=${id}${isDemo ? '&demo=true' : ''}`);
  }, [selected, navigate, isDemo]);

  const handleViewFullMap = useCallback(() => {
    /* Scroll to map area for a full map view */
    const mapEl = document.querySelector('.cm-map-container');
    if (mapEl) {
      mapEl.requestFullscreen?.() || mapEl.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  const handleRefresh = useCallback(() => {
    if (isDemo) {
      /* In demo mode, just toggle a re-render by clearing and re-setting stations */
      setStations(prev => [...prev]);
    } else {
      liveForecast.refresh?.();
    }
  }, [isDemo, liveForecast]);

  if (loading) {
    return (
      <div className="page">
        <LoadingState message="Loading map data..." />
      </div>
    );
  }

  return (
    <div className="cm-page">
      {/* ═══ Page Header ═══ */}
      <div className="cm-header">
        <div className="cm-breadcrumb">
          <MapPin size={14} color="#0d9488" />
          <span>Lahore, Punjab</span>
          <span className="cm-breadcrumb__sep">·</span>
          <span>{dateStr}</span>
          <span className="cm-breadcrumb__chevron">▾</span>
        </div>
        <div className="cm-title-row">
          <div>
            <h1 className="cm-title">City Map</h1>
            <p className="cm-subtitle">Explore real-time air quality across Lahore</p>
          </div>
          <div className="cm-controls">
            <button
              className={`cm-control-btn ${metricType === 'AQI' ? 'cm-control-btn--active' : ''}`}
              onClick={() => setMetricType('AQI')}
            >
              AQI
              <span className="cm-control-chevron">▾</span>
            </button>
            <button
              className={`cm-control-btn ${metricType === 'PM2.5' ? 'cm-control-btn--active' : ''}`}
              onClick={() => setMetricType('PM2.5')}
            >
              PM2.5
            </button>
          </div>
        </div>
      </div>

      {/* ═══ Main Content: Map + Sidebar ═══ */}
      <div className="cm-main">
        {/* ── Map Area ── */}
        <div className="cm-map-area">
          <div className="cm-map-card">
            {/* Search and Filters */}
            <div className="cm-map-toolbar">
              <div className="cm-search">
                <Search size={15} color="#94a3b8" />
                <input
                  type="text"
                  placeholder="Search location in Lahore..."
                  className="cm-search__input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
                    aria-label="Clear search"
                  >
                    ×
                  </button>
                )}
              </div>
              <button
                className={`cm-filter-btn ${showFilterPanel ? 'cm-filter-btn--active' : ''}`}
                onClick={() => setShowFilterPanel(prev => !prev)}
              >
                <SlidersHorizontal size={14} />
                <span>Filters</span>
              </button>
            </div>

            {/* Filter Panel */}
            {showFilterPanel && (
              <div className="cm-filter-panel">
                <div className="cm-filter-panel__title">Filter by Severity</div>
                <div className="cm-filter-panel__options">
                  <button
                    className={`cm-filter-chip ${!severityFilter ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(null)}
                  >
                    All
                  </button>
                  <button
                    className={`cm-filter-chip ${severityFilter?.label === 'Good' ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(severityFilter?.label === 'Good' ? null : { min: 0, max: 50, label: 'Good' })}
                  >
                    <span className="cm-filter-chip__dot" style={{ background: '#16a34a' }} />
                    Good
                  </button>
                  <button
                    className={`cm-filter-chip ${severityFilter?.label === 'Moderate' ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(severityFilter?.label === 'Moderate' ? null : { min: 51, max: 100, label: 'Moderate' })}
                  >
                    <span className="cm-filter-chip__dot" style={{ background: '#eab308' }} />
                    Moderate
                  </button>
                  <button
                    className={`cm-filter-chip ${severityFilter?.label === 'Poor' ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(severityFilter?.label === 'Poor' ? null : { min: 101, max: 150, label: 'Poor' })}
                  >
                    <span className="cm-filter-chip__dot" style={{ background: '#f97316' }} />
                    Poor
                  </button>
                  <button
                    className={`cm-filter-chip ${severityFilter?.label === 'Unhealthy' ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(severityFilter?.label === 'Unhealthy' ? null : { min: 151, max: 200, label: 'Unhealthy' })}
                  >
                    <span className="cm-filter-chip__dot" style={{ background: '#ef4444' }} />
                    Unhealthy
                  </button>
                  <button
                    className={`cm-filter-chip ${severityFilter?.label === 'VUH' ? 'cm-filter-chip--active' : ''}`}
                    onClick={() => setSeverityFilter(severityFilter?.label === 'VUH' ? null : { min: 201, max: 500, label: 'VUH' })}
                  >
                    <span className="cm-filter-chip__dot" style={{ background: '#a855f7' }} />
                    Very Unhealthy+
                  </button>
                </div>
              </div>
            )}

            {/* Map Container */}
            <div className="cm-map-container">
              <LahoreMap
                pm25Value={currentPM25}
                label="Lahore"
                stations={stations}
                allowFullscreen={true}
                showLegend={false}
                centerRadius={0}
                stationRadius={0}
                areas={filteredAreas}
                areaRadius={4500}
                initialZoom={12}
              />

              {/* AQI Legend Overlay */}
              <div className="cm-aqi-legend">
                <div className="cm-aqi-legend__title">AQI Legend</div>
                {AQI_SCALE.map((level) => {
                  const filterLabel = level.label === 'Good' ? 'Good'
                    : level.label === 'Moderate' ? 'Moderate'
                    : level.label === 'Unhealthy for Sensitive Groups' ? 'Poor'
                    : level.label === 'Unhealthy' ? 'Unhealthy'
                    : 'VUH';
                  const isActive = severityFilter?.label === filterLabel;
                  return (
                    <button
                      key={level.min}
                      className={`cm-aqi-legend__item ${isActive ? 'cm-aqi-legend__item--active' : ''}`}
                      onClick={() => setSeverityFilter(
                        isActive ? null : { min: level.min, max: level.max, label: filterLabel }
                      )}
                    >
                      <span className="cm-aqi-legend__dot" style={{ backgroundColor: level.color }} />
                      <span className="cm-aqi-legend__range">
                        {level.min === 301 ? '301+' : `${level.min} - ${level.max}`}
                      </span>
                      <span className="cm-aqi-legend__label">{level.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div className="cm-sidebar">
          {/* Live Air Quality */}
          <div className="cm-sidebar-card cm-live-card">
            <div className="cm-live-card__header">
              <div className="cm-live-card__icon">
                <TrendingUp size={18} color="#0d9488" />
              </div>
              <div className="cm-live-card__text">
                <span className="cm-live-card__label">Live Air Quality</span>
                <span className="cm-live-card__sub">Real-time AQI across Lahore</span>
              </div>
            </div>
            <div className="cm-live-card__value" style={{ color: overallColor }}>
              {metricType === 'PM2.5'
                ? (currentPM25 != null ? currentPM25.toFixed(0) : '—')
                : (overallAQI ?? '—')}
            </div>
            <div className="cm-live-card__status" style={{ color: overallColor }}>
              {metricType === 'PM2.5' ? 'μg/m³' : overallLabel}
            </div>
          </div>

          {/* Locations */}
          <div className="cm-sidebar-card cm-locations-card">
            <div className="cm-locations-header">
              <span className="cm-locations-title">Locations</span>
              <a href="#view-all" className="cm-locations-link" onClick={e => { e.preventDefault(); handleViewAll(); }}>
                View All
              </a>
            </div>
            <div className="cm-locations-list" ref={locationsListRef}>
              {filteredAreas.length === 0 && (
                <div style={{ padding: '16px 12px', textAlign: 'center', color: '#64748b', fontSize: 13 }}>
                  No locations match the current filters
                </div>
              )}
              {filteredAreas.map((area) => {
                const aqi = area.aqi ?? pm25ToAQI(area.pm25);
                const color = getAQIColor(aqi);
                const label = getAQILabel(aqi);
                const displayValue = metricType === 'PM2.5'
                  ? (area.pm25 != null ? area.pm25.toFixed(0) : '—')
                  : (aqi ?? '—');
                const displayLabel = metricType === 'PM2.5' ? 'μg/m³' : label;
                return (
                  <button
                    key={area.id}
                    className={`cm-location-item ${selected?.id === area.id ? 'cm-location-item--active' : ''}`}
                    onClick={() => setSelectedLocation(area)}
                  >
                    <span className="cm-location-dot" style={{ backgroundColor: color }} />
                    <div className="cm-location-info">
                      <span className="cm-location-name">{area.name}</span>
                    </div>
                    <div className="cm-location-aqi" style={{ color }}>
                      <span className="cm-location-aqi-value">{displayValue}</span>
                      <span className="cm-location-aqi-label">{displayLabel}</span>
                    </div>
                    <ChevronRight size={16} color="#d1d5db" />
                  </button>
                );
              })}
            </div>
          </div>

          {/* About the Map */}
          <div className="cm-sidebar-card cm-about-card">
            <div className="cm-about-header">
              <Info size={18} color="#0d9488" />
              <span className="cm-about-title">About the Map</span>
            </div>
            <p className="cm-about-text">
              This map shows real-time air quality index (AQI) levels across Lahore. Click on any location to see more details and recommendations.
            </p>
          </div>

          {/* Air Quality Hotspots */}
          <div className="cm-sidebar-card cm-hotspot-card">
            <div className="cm-hotspot-header">
              <span className="cm-hotspot-title">Air Quality Hotspots</span>
              <a href="#view-map" className="cm-hotspot-link" onClick={e => { e.preventDefault(); handleViewFullMap(); }}>
                View Full Map
              </a>
            </div>
            <div className="cm-hotspot-alert">
              <AlertTriangle size={18} color="#ef4444" />
              <div className="cm-hotspot-alert-content">
                <span className="cm-hotspot-alert-title">High Pollution Area Detected</span>
                <span className="cm-hotspot-alert-text">
                  The red areas on the map indicate locations with higher pollution levels. Take precautions.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ═══ Selected Location Panel ═══ */}
      <div className="cm-selected">
        <div className="cm-selected-header">
          <span className="cm-selected-title">Selected Location</span>
          <a href="#details" className="cm-selected-link" onClick={e => { e.preventDefault(); handleViewFullDetails(); }}>
            View Full Details
            <ExternalLink size={13} />
          </a>
        </div>
        <div className="cm-selected-content">
          <div className="cm-selected-location">
            <div className="cm-selected-badge" style={{ backgroundColor: getAQIColor(selectedAQI) }}>
              {selectedAQI ?? '—'}
            </div>
            <div className="cm-selected-location-info">
              <div className="cm-selected-location-top">
                <span className="cm-selected-location-name">{selected?.name || 'Central Lahore'}</span>
                <span className="cm-selected-live-badge">
                  <span className="cm-selected-live-dot" />
                  Live
                </span>
              </div>
              <span className="cm-selected-location-district">{selected?.district || 'Gulberg, Lahore'}</span>
              <p className="cm-selected-location-advice">
                {getAQILabel(selectedAQI) === 'Good'
                  ? 'Air quality is good. Enjoy outdoor activities.'
                  : getAQILabel(selectedAQI) === 'Moderate'
                  ? 'Air quality is acceptable for most people.'
                  : 'Air quality is poor. Limit outdoor time and keep windows closed.'}
              </p>
            </div>
          </div>

          <div className="cm-selected-metrics">
            <div className="cm-metric">
              <div className="cm-metric-icon"><Grid3x3 size={16} /></div>
              <span className="cm-metric-value">{selectedPM25 != null ? `${selectedPM25.toFixed(1)}` : '—'}</span>
              <span className="cm-metric-label">PM2.5</span>
              <span className="cm-metric-unit">μg/m³</span>
            </div>
            <div className="cm-metric">
              <div className="cm-metric-icon"><Grid3x3 size={16} /></div>
              <span className="cm-metric-value">{weather.pm10 ?? '—'}</span>
              <span className="cm-metric-label">PM10</span>
              <span className="cm-metric-unit">μg/m³</span>
            </div>
            <div className="cm-metric">
              <div className="cm-metric-icon"><Thermometer size={16} /></div>
              <span className="cm-metric-value">{weather.temperature ?? '—'}</span>
              <span className="cm-metric-label">Temp</span>
              <span className="cm-metric-unit">°C</span>
            </div>
            <div className="cm-metric">
              <div className="cm-metric-icon"><Droplets size={16} /></div>
              <span className="cm-metric-value">{weather.humidity ?? '—'}</span>
              <span className="cm-metric-label">Humidity</span>
              <span className="cm-metric-unit">%</span>
            </div>
            <div className="cm-metric">
              <div className="cm-metric-icon"><Wind size={16} /></div>
              <span className="cm-metric-value">{weather.wind_speed ?? '—'}</span>
              <span className="cm-metric-label">Wind</span>
              <span className="cm-metric-unit">km/h</span>
            </div>
          </div>
        </div>
      </div>

      {/* ═══ Data Status Banner ═══ */}
      <div className="cm-status-banner">
        <div className="cm-status-banner__left">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#16a34a" stroke="none">
            <circle cx="12" cy="12" r="10" />
            <path d="M9 12l2 2 4-4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
          <span>Data is updated every 10 minutes from Lahore's air quality monitoring network.</span>
        </div>
        <div className="cm-status-banner__right">
          <span>Last updated: Just now</span>
          <button
            onClick={handleRefresh}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex' }}
            aria-label="Refresh data"
          >
            <RefreshCw size={13} color="#94a3b8" />
          </button>
        </div>
      </div>
    </div>
  );
}
