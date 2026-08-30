/**
 * ReportPage — Download and share air quality reports.
 *
 * Citizen-friendly. Shows recent reports in a table, available report
 * types as cards, and current air quality snapshot. Two-column layout.
 * No technical jargon.
 */

import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useReports } from '../hooks/useReports';
import { generateReport } from '../services/api';
import { useState } from 'react';
import {
  FileText,
  BarChart3,
  AlertTriangle,
  Link2,
  Radio,
  Download,
  Share2,
  ChevronRight,
  Clock,
  CheckCircle,
  RefreshCw,
  Calendar,
  Info,
} from 'lucide-react';
import Breadcrumb from '../components/common/Breadcrumb.jsx';

/* ── Helpers ─────────────────────────────────────────── */

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

function getReportTypeColor(type) {
  switch (type) {
    case 'Daily': return { color: '#22C55E', bg: '#F0FDF4' };
    case 'Weekly': return { color: '#F97316', bg: '#FFF7ED' };
    case 'Monthly': return { color: '#3B82F6', bg: '#EFF6FF' };
    case 'Episode': return { color: '#EF4444', bg: '#FEF2F2' };
    case 'Snapshot': return { color: '#8B5CF6', bg: '#F5F3FF' };
    default: return { color: '#A09A93', bg: '#F8F7F5' };
  }
}

/* ── Available Report Types ──────────────────────────── */

const REPORT_CARDS = [
  {
    id: 'daily',
    title: 'Daily Summary',
    desc: 'Air quality overview for today — what the air was like and what to expect',
    icon: <FileText size={20} />,
    color: '#22C55E',
    bg: '#F0FDF4',
  },
  {
    id: 'weekly',
    title: 'Weekly Report',
    desc: 'A week of air quality data with trends and comparisons',
    icon: <BarChart3 size={20} />,
    color: '#F97316',
    bg: '#FFF7ED',
  },
  {
    id: 'episode',
    title: 'Episode Report',
    desc: 'Detailed breakdown of a specific pollution episode or incident',
    icon: <AlertTriangle size={20} />,
    color: '#EF4444',
    bg: '#FEF2F2',
  },
  {
    id: 'share',
    title: 'Share Snapshot',
    desc: 'Share a quick snapshot of current air quality with friends or family',
    icon: <Share2 size={20} />,
    color: '#8B5CF6',
    bg: '#F5F3FF',
  },
];

/* ── Component ──────────────────────────────────────── */

export default function ReportPage() {
  const { forecasts, loading: forecastLoading } = useForecast();
  const { episode } = useEpisodeIntelligence();
  const { reports, loading: reportsLoading, refetch: reportsRefetch } = useReports();
  const [generating, setGenerating] = useState(null);
  const [generated, setGenerated] = useState(null);
  const [generateError, setGenerateError] = useState(null);

  const currentPM25 = forecasts?.['1']?.predicted_pm25;
  const airInfo = getAirQualityInfo(currentPM25);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const handleGenerate = async (reportType) => {
    setGenerating(reportType);
    setGenerateError(null);
    try {
      // Real API call — generates report on backend, persists to DB
      await generateReport(reportType);
      setGenerated(reportType);
      // Refetch reports list to show the new one
      if (reportsRefetch) reportsRefetch();
    } catch (err) {
      setGenerateError(err.message || 'Failed to generate report');
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="page">
      {/* Breadcrumb */}
      <Breadcrumb pageName="Reports" />

      {/* Header with Lahore Skyline */}
      <div className="rp-hero" style={{ position: 'relative', overflow: 'hidden', borderRadius: 12, marginBottom: 'var(--sp-4)' }}>
        <h1 className="page__title" style={{ position: 'relative', zIndex: 1 }}>Reports</h1>
        <p className="page__subtitle" style={{ position: 'relative', zIndex: 1 }}>
          Generate, download, and share air quality information for Lahore
        </p>
        <div className="lh-skyline" aria-hidden="true" />
      </div>

      {/* Current Air Quality Snapshot */}
      <div className="rp-status-banner" style={{ background: airInfo.bg, border: `1px solid ${airInfo.color}20` }}>
        <div className="rp-status-banner__icon" style={{ background: `${airInfo.color}15`, color: airInfo.color }}>
          <Radio size={18} />
        </div>
        <div className="rp-status-banner__content">
          <h2 className="rp-status-banner__title" style={{ color: airInfo.color }}>
            Current Air: {airInfo.label}
          </h2>
          <p className="rp-status-banner__subtitle">
            {today} · {forecastLoading ? 'Loading...' : 'Live data'}
          </p>
        </div>
      </div>

      {/* Two-column layout: Recent Reports + Sidebar */}
      <div className="rp-two-col">
        {/* Main Column — Recent Reports Table */}
        <div className="rp-main">
          <div className="rp-section">
            <div className="rp-section__header">
              <Clock size={20} className="rp-section__icon" />
              <h2 className="rp-section__title">Recent Reports</h2>
            </div>

            {reportsLoading ? (
              <div className="rp-empty-state">
                <RefreshCw size={24} className="al-spin" />
                <p>Loading reports...</p>
              </div>
            ) : reports.length === 0 ? (
              <div className="rp-empty-state">
                <FileText size={24} />
                <p>No reports generated yet</p>
                <span>Generate your first report using the options below</span>
              </div>
            ) : (
              <div className="rp-table-wrapper">
                <table className="rp-table">
                  <thead>
                    <tr>
                      <th>Report</th>
                      <th>Type</th>
                      <th>Generated On</th>
                      <th>Range</th>
                      <th>Format</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((report) => {
                      const typeStyle = getReportTypeColor(report.type);
                      return (
                        <tr key={report.id} className="rp-table__row">
                          <td className="rp-table__name">{report.name}</td>
                          <td>
                            <span
                              className="rp-type-badge"
                              style={{ color: typeStyle.color, background: typeStyle.bg }}
                            >
                              {report.type}
                            </span>
                          </td>
                          <td className="rp-table__meta">{report.generatedOn}</td>
                          <td className="rp-table__meta">{report.range}</td>
                          <td>
                            <span className="rp-format-badge">{report.format}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Available Reports */}
          <div className="rp-section">
            <div className="rp-section__header">
              <FileText size={20} className="rp-section__icon" />
              <h2 className="rp-section__title">Available Reports</h2>
            </div>
            <div className="rp-report-cards">
              {REPORT_CARDS.map((card) => (
                <div
                  key={card.id}
                  className={`rp-report-card ${generating === card.id ? 'rp-report-card--generating' : ''} ${generated === card.id ? 'rp-report-card--done' : ''}`}
                  onClick={() => handleGenerate(card.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleGenerate(card.id); }}
                >
                  <div className="rp-report-card__icon" style={{ background: card.bg, color: card.color }}>
                    {card.icon}
                  </div>
                  <div className="rp-report-card__content">
                    <h3 className="rp-report-card__title">{card.title}</h3>
                    <p className="rp-report-card__desc">{card.desc}</p>
                  </div>
                  <div className="rp-report-card__action">
                    {generating === card.id ? (
                      <RefreshCw size={16} className="al-spin" style={{ color: 'var(--lp-brand-500)' }} />
                    ) : generated === card.id ? (
                      <Download size={16} style={{ color: '#22C55E' }} />
                    ) : (
                      <ChevronRight size={16} style={{ color: 'var(--lp-text-tertiary)' }} />
                    )}
                  </div>
                  {generated === card.id && (
                    <div className="rp-report-card__status">
                      <CheckCircle size={12} />
                      <span>Ready to download</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="rp-sidebar">
          {/* Air Quality Summary Card */}
          <div className="rp-sidebar-card">
            <div className="rp-sidebar-card__header">
              <Radio size={16} className="rp-sidebar-card__icon" />
              <h3 className="rp-sidebar-card__title">Air Quality Summary</h3>
            </div>
            <p className="rp-sidebar-card__text">
              {currentPM25 != null
                ? `Today's air quality in Lahore is ${airInfo.label.toLowerCase()}. ${
                    currentPM25 <= 25
                      ? "It's safe to enjoy outdoor activities."
                      : currentPM25 <= 55
                        ? 'Most people can go outside, but sensitive individuals should take care.'
                        : 'Consider spending more time indoors today.'
                  }`
                : 'Sensor data is currently being refreshed.'}
            </p>
            <div className="rp-sidebar-metrics">
              <div className="rp-sidebar-metric">
                <span className="rp-sidebar-metric__label">Current Air</span>
                <span className="rp-sidebar-metric__value" style={{ color: airInfo.color }}>{airInfo.label}</span>
              </div>
              <div className="rp-sidebar-metric">
                <span className="rp-sidebar-metric__label">Episode Status</span>
                <span className="rp-sidebar-metric__value">
                  {episode?.state
                    ? episode.state.charAt(0).toUpperCase() + episode.state.slice(1)
                    : 'Clear'}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Actions Card */}
          <div className="rp-sidebar-card">
            <div className="rp-sidebar-card__header">
              <Download size={16} className="rp-sidebar-card__icon" />
              <h3 className="rp-sidebar-card__title">Quick Actions</h3>
            </div>
            <div className="rp-sidebar-actions">
              <button
                className="rp-sidebar-btn rp-sidebar-btn--primary"
                onClick={() => handleGenerate('daily')}
                disabled={!!generating}
              >
                <Download size={14} />
                <span>Download Report</span>
              </button>
              <button
                className="rp-sidebar-btn rp-sidebar-btn--secondary"
                onClick={() => handleGenerate('share')}
                disabled={!!generating}
              >
                <Link2 size={14} />
                <span>Share Link</span>
              </button>
            </div>
            {generateError && (
              <div className="rp-generate-error">
                <AlertTriangle size={14} />
                <span>{generateError}</span>
              </div>
            )}
          </div>

          {/* Report Schedule Card */}
          <div className="rp-sidebar-card">
            <div className="rp-sidebar-card__header">
              <Calendar size={16} className="rp-sidebar-card__icon" />
              <h3 className="rp-sidebar-card__title">Report Schedule</h3>
            </div>
            <div className="rp-schedule-list">
              <div className="rp-schedule-item">
                <span className="rp-schedule-item__dot" style={{ background: '#22C55E' }} />
                <span className="rp-schedule-item__label">Daily</span>
                <span className="rp-schedule-item__time">7:30 AM</span>
              </div>
              <div className="rp-schedule-item">
                <span className="rp-schedule-item__dot" style={{ background: '#F97316' }} />
                <span className="rp-schedule-item__label">Weekly</span>
                <span className="rp-schedule-item__time">Monday 8:15 AM</span>
              </div>
              <div className="rp-schedule-item">
                <span className="rp-schedule-item__dot" style={{ background: '#3B82F6' }} />
                <span className="rp-schedule-item__label">Monthly</span>
                <span className="rp-schedule-item__time">1st of month</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="rp-info-banner">
        <Info size={16} className="rp-info-banner__icon" />
        <p className="rp-info-banner__text">
          All data comes from Lahore's air quality monitoring network. Reports are generated in real
          time and reflect current or recent conditions. Historical reports may be added in future updates.
        </p>
      </div>
    </div>
  );
}
