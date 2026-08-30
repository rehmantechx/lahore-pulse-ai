/**
 * AlertsPage — Air quality alerts and episode notifications.
 *
 * Citizen-friendly. Shows current episode status, alert configuration,
 * and recent alert history. Two-column layout for preferences + history.
 * No technical jargon.
 */

import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useAlertHistory } from '../hooks/useAlertHistory';
import { useAlertPreferences } from '../hooks/useAlertPreferences';
import { useState } from 'react';
import {
  AlertTriangle,
  TrendingDown,
  RefreshCw,
  CheckCircle,
  Bell,
  Shield,
  Search,
  Clock,
  Info,
} from 'lucide-react';
import Breadcrumb from '../components/common/Breadcrumb.jsx';

/* ── Helpers ─────────────────────────────────────────── */

function getEpisodeInfo(state) {
  switch (state) {
    case 'episode':
      return {
        label: 'Active Incident',
        color: '#EF4444',
        bg: '#FEF2F2',
        icon: <AlertTriangle size={18} />,
        iconBg: '#FEF2F2',
      };
    case 'improving':
      return {
        label: 'Improving',
        color: '#F97316',
        bg: '#FFF7ED',
        icon: <TrendingDown size={18} />,
        iconBg: '#FFF7ED',
      };
    case 'uncertain':
      return {
        label: 'Uncertain',
        color: '#EAB308',
        bg: '#FEFCE8',
        icon: <RefreshCw size={18} />,
        iconBg: '#FEFCE8',
      };
    default:
      return {
        label: 'No Active Incidents',
        color: '#16A34A',
        bg: '#F0FDF4',
        icon: <CheckCircle size={18} />,
        iconBg: '#DCFCE7',
      };
  }
}

function getSeverityColor(severity) {
  switch (severity) {
    case 'good': return '#22C55E';
    case 'fair': return '#EAB308';
    case 'moderate': return '#F97316';
    case 'poor': return '#EF4444';
    case 'dangerous': return '#DC2626';
    default: return '#A09A93';
  }
}

function getSeverityIcon(severity) {
  switch (severity) {
    case 'good': return <CheckCircle size={16} />;
    case 'fair': return <Shield size={16} />;
    case 'moderate': return <AlertTriangle size={16} />;
    case 'poor': return <AlertTriangle size={16} />;
    case 'dangerous': return <AlertTriangle size={16} />;
    default: return <Bell size={16} />;
  }
}

function formatTimeAgo(timestamp) {
  if (!timestamp) return '';
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
  }
  return `${Math.floor(days / 30)} months ago`;
}

function formatAlertDate(timestamp) {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/* ── Alert Types Explained ──────────────────────────── */

const ALERT_TYPES = [
  {
    label: 'Fair Warning',
    description: 'Air may affect sensitive groups',
    detail: 'People with asthma, elderly, children',
    color: '#EAB308',
    bg: '#FEFCE8',
    icon: <Shield size={20} />,
  },
  {
    label: 'Moderate Warning',
    description: 'Consider reducing outdoor time',
    detail: 'Limit prolonged outdoor activities',
    color: '#F97316',
    bg: '#FFF7ED',
    icon: <AlertTriangle size={20} />,
  },
  {
    label: 'Poor Air Warning',
    description: 'Stay indoors if possible',
    detail: 'Keep windows closed, use purifiers',
    color: '#EF4444',
    bg: '#FEF2F2',
    icon: <AlertTriangle size={20} />,
  },
  {
    label: 'Dangerous Conditions',
    description: 'Emergency — stay inside',
    detail: 'Seal all windows, avoid outdoor activity',
    color: '#DC2626',
    bg: '#FEF2F2',
    icon: <AlertTriangle size={20} />,
  },
  {
    label: 'Severe Alerts',
    description: 'Hazardous to everyone',
    detail: 'Follow emergency protocols immediately',
    color: '#7F1D1D',
    bg: '#FEF2F2',
    icon: <AlertTriangle size={20} />,
  },
];

/* ── Alert Preferences Config ───────────────────────── */

const ALERT_PREFS = [
  { id: 'fair', label: 'Fair conditions', color: '#EAB308', description: 'AQI > 35' },
  { id: 'moderate', label: 'Moderate conditions', color: '#F97316', description: 'AQI > 55' },
  { id: 'poor', label: 'Poor conditions', color: '#EF4444', description: 'AQI > 90' },
  { id: 'dangerous', label: 'Dangerous conditions', color: '#DC2626', description: 'AQI > 150' },
];

/* ── Component ──────────────────────────────────────── */

export default function AlertsPage() {
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const { alerts, loading: alertsLoading } = useAlertHistory();
  const { prefs, loading: prefsLoading, togglePref } = useAlertPreferences();

  const state = episode?.state || 'normal';
  const epInfo = getEpisodeInfo(state);

  const isPrefEnabled = (alertType) => {
    const pref = prefs.find((p) => p.alert_type === alertType);
    return pref?.enabled ?? false;
  };

  return (
    <div className="page">
      {/* Breadcrumb */}
      <Breadcrumb pageName="Alerts" />

      {/* Header with Lahore Skyline */}
      <div className="al-hero" style={{ position: 'relative', overflow: 'hidden', borderRadius: 12, marginBottom: 'var(--sp-4)' }}>
        <h1 className="page__title" style={{ position: 'relative', zIndex: 1 }}>Alerts</h1>
        <p className="page__subtitle" style={{ position: 'relative', zIndex: 1 }}>
          Stay informed about dangerous air conditions in Lahore
        </p>
        <div className="lh-skyline" aria-hidden="true" />
      </div>

      {/* Status Banner */}
      <div className={`al-status-banner ${state !== 'normal' ? 'al-status-banner--active' : 'al-status-banner--clear'}`}>
        <div className="al-status-banner__icon" style={{ background: epInfo.iconBg, color: epInfo.color }}>
          {episodeLoading ? <RefreshCw size={18} className="al-spin" /> : epInfo.icon}
        </div>
        <div className="al-status-banner__content">
          <h2 className="al-status-banner__title" style={{ color: epInfo.color }}>
            {episodeLoading ? 'Checking status...' : epInfo.label}
          </h2>
          <p className="al-status-banner__subtitle">
            {episode?.trajectory === 'rising'
              ? 'Conditions are getting worse'
              : episode?.trajectory === 'falling'
                ? 'Conditions are improving'
                : state === 'normal'
                  ? 'No active incidents — air quality is safe'
                  : 'Monitoring current conditions'}
          </p>
          {episode?.narrative && (
            <p className="al-status-banner__narrative">{episode.narrative}</p>
          )}
        </div>
      </div>

      {/* How Alerts Work — 5 horizontal cards */}
      <div className="al-section">
        <div className="al-section__header">
          <Shield size={20} className="al-section__icon" />
          <h2 className="al-section__title">How Alerts Work</h2>
        </div>
        <div className="al-alert-types">
          {ALERT_TYPES.map((type) => (
            <div key={type.label} className="al-alert-type-card" style={{ borderLeftColor: type.color }}>
              <div className="al-alert-type-card__icon" style={{ background: type.bg, color: type.color }}>
                {type.icon}
              </div>
              <div className="al-alert-type-card__content">
                <h3 className="al-alert-type-card__title">{type.label}</h3>
                <p className="al-alert-type-card__desc">{type.description}</p>
                <p className="al-alert-type-card__detail">{type.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Two-column: Preferences + History */}
      <div className="al-two-col">
        {/* Left Column — Alert Preferences */}
        <div className="al-panel">
          <div className="al-panel__header">
            <Bell size={20} className="al-panel__icon" />
            <h2 className="al-panel__title">Alert Preferences</h2>
          </div>
          <p className="al-panel__desc">
            Choose when to be notified about air quality changes.
          </p>
          <div className="al-prefs-list">
            {ALERT_PREFS.map((pref) => (
              <button
                key={pref.id}
                className={`al-pref-item ${isPrefEnabled(pref.id) ? 'al-pref-item--active' : ''}`}
                onClick={() => togglePref(pref.id)}
                disabled={prefsLoading}
                type="button"
              >
                <span className="al-pref-dot" style={{ background: pref.color }} />
                <span className="al-pref-info">
                  <span className="al-pref-label">{pref.label}</span>
                  <span className="al-pref-desc">{pref.description}</span>
                </span>
                <span className={`al-toggle ${isPrefEnabled(pref.id) ? 'al-toggle--on' : ''}`} role="switch" aria-checked={isPrefEnabled(pref.id)}>
                  <span className="al-toggle__knob" />
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Right Column — Recent Alerts */}
        <div className="al-panel">
          <div className="al-panel__header">
            <Clock size={20} className="al-panel__icon" />
            <h2 className="al-panel__title">Recent Alerts</h2>
          </div>
          <div className="al-alerts-list">
            {alertsLoading ? (
              <div className="al-empty-state">
                <RefreshCw size={24} className="al-spin" />
                <p>Loading alert history...</p>
              </div>
            ) : alerts.length === 0 ? (
              <div className="al-empty-state">
                <Bell size={24} />
                <p>No alerts recorded yet</p>
                <span>Alerts will appear here when air quality changes significantly</span>
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.id} className="al-alert-item">
                  <div className="al-alert-item__icon" style={{ color: getSeverityColor(alert.severity) }}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div className="al-alert-item__content">
                    <div className="al-alert-item__header">
                      <span className="al-alert-item__type">{alert.type}</span>
                      {alert.aqi != null && (
                        <span className="al-alert-item__aqi" style={{ color: getSeverityColor(alert.severity) }}>
                          AQI {alert.aqi}
                        </span>
                      )}
                    </div>
                    <p className="al-alert-item__msg">{alert.message}</p>
                    <span className="al-alert-item__time">{formatAlertDate(alert.timestamp)}</span>
                  </div>
                  <span className="al-alert-item__ago">{formatTimeAgo(alert.timestamp)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="al-info-banner">
        <Info size={16} className="al-info-banner__icon" />
        <p className="al-info-banner__text">
          Alerts are generated based on real-time air quality data from Lahore's monitoring network.
          You'll receive notifications on this page when levels reach your configured thresholds.
        </p>
      </div>
    </div>
  );
}
