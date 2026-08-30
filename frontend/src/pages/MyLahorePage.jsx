/**
 * MyLahorePage — Personalized air quality dashboard.
 *
 * Citizen-friendly. Shows saved locations with live AQ data,
 * location comparison table, quick access links, and health tips.
 * All data is real — no decorative elements.
 */

import { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { getStations } from '../services/api';
import { useDemoData } from '../demo/index';
import {
  Heart,
  MapPin,
  Plus,
  ChevronRight,
  GitCompareArrows,
  Share2,
  Download,
  Leaf,
  Wind,
  Droplets,
  Thermometer,
  Home,
  Building2,
  School,
  TreePine,
  X,
  Trash2,
  ExternalLink,
  Map,
  Zap,
  Activity,
} from 'lucide-react';
import Breadcrumb from '../components/common/Breadcrumb.jsx';

/* ── Helpers ──────────────────────────────────────────────── */

const ICON_MAP = {
  home: Home,
  building: Building2,
  school: School,
  tree: TreePine,
  'map-pin': MapPin,
  pin: MapPin,
};

function getIcon(iconName) {
  return ICON_MAP[iconName] || MapPin;
}

function getAirQualityInfo(value) {
  if (value == null || isNaN(value))
    return { label: 'No Data', color: '#A09A93', bg: '#F8F7F5' };
  if (value <= 12) return { label: 'Excellent', color: '#22C55E', bg: '#F0FDF4' };
  if (value <= 25) return { label: 'Good', color: '#84CC16', bg: '#F7FEE7' };
  if (value <= 35) return { label: 'Fair', color: '#EAB308', bg: '#FEFCE8' };
  if (value <= 55) return { label: 'Moderate', color: '#F97316', bg: '#FFF7ED' };
  if (value <= 90) return { label: 'Poor', color: '#EF4444', bg: '#FEF2F2' };
  if (value <= 150) return { label: 'Very Poor', color: '#DC2626', bg: '#FEF2F2' };
  return { label: 'Hazardous', color: '#7F1D1D', bg: '#FEF2F2' };
}

/* ── Air Quality Tips ─────────────────────────────────────── */

const HEALTH_TIPS = [
  {
    icon: Leaf,
    title: 'Check Air Quality Before Going Outside',
    desc: 'Always check AQI before outdoor activities. Plan exercise for times when air quality is better.',
  },
  {
    icon: Wind,
    title: 'Use Air Purifiers When AQI Is High',
    desc: 'Run air purifiers indoors during poor air quality periods to keep your home air clean.',
  },
  {
    icon: Droplets,
    title: 'Wear a Mask During Poor Air Days',
    desc: 'Use N95 or KN95 masks when going outside during poor air quality to reduce inhalation.',
  },
  {
    icon: Thermometer,
    title: 'Stay Hydrated and Rest Often',
    desc: 'Drink plenty of water and take breaks during outdoor activities, especially in poor air.',
  },
];

/* ── Quick Access Links ───────────────────────────────────── */

const QUICK_ACCESS = [
  { icon: Map, label: 'View All on Map', path: '/city-map', desc: 'See all locations on the interactive map' },
  { icon: GitCompareArrows, label: 'Compare Locations', path: '/city-map', desc: 'Side-by-side station comparison' },
  { icon: Share2, label: 'Share My Locations', path: '/alerts', desc: 'Share your saved places with others' },
  { icon: Download, label: 'Export My Data', path: '/alerts', desc: 'Download your location history' },
];

/* ── Add Location Modal ───────────────────────────────────── */

function AddLocationModal({ isOpen, onClose, onAdd, stations, existingLocations }) {
  const [selectedStation, setSelectedStation] = useState(null);
  const [customName, setCustomName] = useState('');
  const [customLabel, setCustomLabel] = useState('');
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  // Filter out already-saved stations
  const existingStationIds = new Set(
    existingLocations.map((l) => l.station_id).filter(Boolean),
  );
  const availableStations = (stations || []).filter(
    (s) => !existingStationIds.has(s.station_id),
  );

  const handleAdd = async () => {
    if (!selectedStation && !customName.trim()) {
      setError('Please select a station or enter a location name');
      return;
    }
    try {
      setError(null);
      await onAdd({
        station_id: selectedStation?.station_id || null,
        name: selectedStation?.name || customName.trim(),
        label: customLabel.trim() || null,
        latitude: selectedStation?.latitude || null,
        longitude: selectedStation?.longitude || null,
      });
      setSelectedStation(null);
      setCustomName('');
      setCustomLabel('');
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to add location');
    }
  };

  return (
    <div className="ml-modal-overlay" onClick={onClose}>
      <div className="ml-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ml-modal__header">
          <h3 className="ml-modal__title">
            <Plus size={20} /> Add Location
          </h3>
          <button className="ml-modal__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="ml-modal__body">
          {/* Available monitoring stations */}
          {availableStations.length > 0 && (
            <div className="ml-modal__section">
              <label className="ml-modal__label">Choose a monitoring station:</label>
              <div className="ml-modal__station-list">
                {availableStations.map((station) => (
                  <button
                    key={station.station_id}
                    className={`ml-modal__station-item ${
                      selectedStation?.station_id === station.station_id ? 'ml-modal__station-item--selected' : ''
                    }`}
                    onClick={() => {
                      setSelectedStation(station);
                      setCustomName('');
                    }}
                  >
                    <MapPin size={14} />
                    <span className="ml-modal__station-name">{station.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Custom location */}
          <div className="ml-modal__section">
            <label className="ml-modal__label">Or enter a custom location:</label>
            <input
              type="text"
              className="ml-modal__input"
              placeholder="Location name (e.g., Home, Park)"
              value={customName}
              onChange={(e) => {
                setCustomName(e.target.value);
                setSelectedStation(null);
              }}
            />
            <input
              type="text"
              className="ml-modal__input"
              placeholder="Label (e.g., Work, School)"
              value={customLabel}
              onChange={(e) => setCustomLabel(e.target.value)}
            />
          </div>

          {error && <p className="ml-modal__error">{error}</p>}
        </div>

        <div className="ml-modal__footer">
          <button className="ml-btn ml-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="ml-btn ml-btn--primary" onClick={handleAdd}>
            <Plus size={16} /> Add Location
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────── */

export default function MyLahorePage() {
  const { locations, loading, error, add, remove } = useFavorites();
  const { forecasts, loading: forecastLoading } = useForecast();
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const navigate = useNavigate();
  const [showAddModal, setShowAddModal] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [stations, setStations] = useState([]);
  const demoData = useDemoData();

  // Fetch available monitoring stations for the modal
  useEffect(() => {
    // In demo mode, use demo stations
    if (demoData?.stations) {
      setStations(demoData.stations);
      return;
    }
    const ctrl = new AbortController();
    getStations({ signal: ctrl.signal })
      .then((data) => {
        const list = Array.isArray(data) ? data : (data?.stations || []);
        setStations(list);
      })
      .catch(() => setStations([]));
    return () => ctrl.abort();
  }, [demoData]);

  // Station data for comparison table — use live data from locations
  const comparisonRows = useMemo(
    () =>
      locations.map((loc) => ({
        id: loc.id,
        name: loc.name,
        pm25: loc.pm25,
        pm10: loc.pm10,
        temperature: loc.temperature,
        humidity: loc.humidity,
        aqi: loc.aqi,
      })),
    [locations],
  );

  const currentPM25 = forecasts?.['1']?.predicted_pm25;
  const isLoading = loading || forecastLoading || episodeLoading;

  const handleRemove = async (locationId) => {
    setRemovingId(locationId);
    try {
      await remove(locationId);
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="ml-page">
      {/* Breadcrumb */}
      <Breadcrumb pageName="My Lahore" />

      {/* Page Header */}
      <div className="ml-header">
        <h1 className="ml-header__title">My Favorites</h1>
        <p className="ml-header__subtitle">
          Your saved locations and preferences
        </p>
      </div>

      {/* Hero Banner */}
      <div className="ml-hero">
        <div className="ml-hero__content">
          <div className="ml-hero__icon">
            <Heart size={24} />
          </div>
          <div className="ml-hero__text">
            <h2 className="ml-hero__count">
              {loading ? '...' : `${locations.length} Location${locations.length !== 1 ? 's' : ''} Saved`}
            </h2>
            <p className="ml-hero__desc">
              Quick access to the places that matter to you
            </p>
          </div>
        </div>
        <div className="lh-skyline" aria-hidden="true" />
      </div>

      {/* Main Two-Column Layout */}
      <div className="ml-layout">
        {/* Left Column — Main Content */}
        <div className="ml-main">
          {/* Saved Locations Section */}
          <div className="ml-section">
            <div className="ml-section__header">
              <div className="ml-section__header-left">
                <MapPin size={20} />
                <h2 className="ml-section__title">Saved Locations</h2>
              </div>
              <button
                className="ml-section__link"
                onClick={() => setShowAddModal(true)}
              >
                <Plus size={14} /> Manage Locations
              </button>
            </div>

            {error && (
              <div className="ml-error">
                <p>Failed to load locations: {error}</p>
                <button onClick={() => window.location.reload()}>Retry</button>
              </div>
            )}

            <div className="ml-locations-grid">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="ml-location-card ml-location-card--loading">
                    <div className="ml-location-card__skeleton-icon" />
                    <div className="ml-location-card__skeleton-text" />
                    <div className="ml-location-card__skeleton-text ml-location-card__skeleton-text--short" />
                  </div>
                ))
              ) : (
                locations.map((loc) => {
                  const Icon = getIcon(loc.icon);
                  const aqiInfo = loc.aqi || getAirQualityInfo(loc.pm25);
                  return (
                    <div key={loc.id} className="ml-location-card">
                      <div className="ml-location-card__top">
                        <div className="ml-location-card__icon-wrap">
                          <Icon size={20} />
                        </div>
                        <div className="ml-location-card__info">
                          <h3 className="ml-location-card__name">{loc.name}</h3>
                          {loc.label && (
                            <span className="ml-location-card__label">{loc.label}</span>
                          )}
                        </div>
                        <button
                          className="ml-location-card__remove"
                          onClick={() => handleRemove(loc.id)}
                          disabled={removingId === loc.id}
                          aria-label={`Remove ${loc.name}`}
                          title="Remove location"
                        >
                          {removingId === loc.id ? '...' : <Trash2 size={14} />}
                        </button>
                      </div>

                      <div className="ml-location-card__aqi">
                        <span
                          className="ml-location-card__aqi-badge"
                          style={{ background: aqiInfo.bg, color: aqiInfo.color }}
                        >
                          {loc.pm25 != null ? loc.pm25 : '—'}
                        </span>
                        <span className="ml-location-card__aqi-label">
                          {aqiInfo.label}
                        </span>
                      </div>

                      <button
                        className="ml-location-card__details"
                        onClick={() => navigate('/city-map')}
                      >
                        View Details <ChevronRight size={14} />
                      </button>
                    </div>
                  );
                })
              )}

              {/* Add Location Card */}
              <button
                className="ml-location-card ml-location-card--add"
                onClick={() => setShowAddModal(true)}
              >
                <div className="ml-location-card__add-icon">
                  <Plus size={24} />
                </div>
                <span className="ml-location-card__add-text">Add Location</span>
              </button>
            </div>
          </div>

          {/* Location Comparison Table */}
          {comparisonRows.length > 0 && (
            <div className="ml-section">
              <div className="ml-section__header">
                <div className="ml-section__header-left">
                  <GitCompareArrows size={20} />
                  <h2 className="ml-section__title">Location Comparison</h2>
                </div>
                <Link to="/city-map" className="ml-section__link">
                  View Full Comparison <ExternalLink size={12} />
                </Link>
              </div>

              <div className="ml-table-wrap">
                <table className="ml-table">
                  <thead>
                    <tr>
                      <th>Location</th>
                      <th>AQI</th>
                      <th>PM2.5 (μg/m³)</th>
                      <th>PM10 (μg/m³)</th>
                      <th>Temp (°C)</th>
                      <th>Humidity (%)</th>
                      <th>Trend (24h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonRows.map((row) => (
                      <tr key={row.id}>
                        <td className="ml-table__name">{row.name}</td>
                        <td>
                          <span
                            className="ml-table__badge"
                            style={{
                              background: (row.aqi || getAirQualityInfo(null)).bg,
                              color: (row.aqi || getAirQualityInfo(null)).color,
                            }}
                          >
                            {row.pm25 != null ? row.pm25 : '—'}
                          </span>
                        </td>
                        <td className="ml-table__num">{row.pm25 != null ? row.pm25.toFixed(1) : '—'}</td>
                        <td className="ml-table__num">{row.pm10 != null ? row.pm10.toFixed(1) : '—'}</td>
                        <td className="ml-table__num">{row.temperature != null ? row.temperature.toFixed(1) : '—'}</td>
                        <td className="ml-table__num">{row.humidity != null ? row.humidity.toFixed(0) : '—'}</td>
                        <td className="ml-table__trend">
                          {row.pm25 != null ? (
                            <Activity size={16} className="ml-trend-icon" />
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Right Column — Sidebar */}
        <div className="ml-sidebar">
          {/* Quick Access */}
          <div className="ml-sidebar-section">
            <h3 className="ml-sidebar-section__title">
              <Zap size={16} /> Quick Access
            </h3>
            <div className="ml-sidebar-links">
              {QUICK_ACCESS.map((item) => (
                <Link
                  key={item.label}
                  to={item.path}
                  className="ml-sidebar-link"
                >
                  <div className="ml-sidebar-link__left">
                    <item.icon size={16} />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight size={14} />
                </Link>
              ))}
            </div>
          </div>

          {/* Air Quality Tips */}
          <div className="ml-sidebar-section">
            <h3 className="ml-sidebar-section__title">
              <Leaf size={16} /> Air Quality Tips
            </h3>
            <div className="ml-tips-list">
              {HEALTH_TIPS.map((tip) => (
                <div key={tip.title} className="ml-tip">
                  <div className="ml-tip__icon">
                    <tip.icon size={16} />
                  </div>
                  <div className="ml-tip__content">
                    <h4 className="ml-tip__title">{tip.title}</h4>
                    <p className="ml-tip__desc">{tip.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <Link to="/city-map" className="ml-sidebar-footer-link">
              View All Health Advice <ExternalLink size={12} />
            </Link>
          </div>
        </div>
      </div>

      {/* Footer Note */}
      <div className="ml-footer-note">
        <MapPin size={14} />
        <span>Your favorite locations help us provide more personalized insights and recommendations.</span>
      </div>

      {/* Add Location Modal */}
      <AddLocationModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={add}
        stations={stations}
        existingLocations={locations}
      />
    </div>
  );
}

