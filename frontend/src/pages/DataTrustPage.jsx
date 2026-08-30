/**
 * DataTrustPage — Transparent explanation of data sources,
 * methodology, limitations, and confidence.
 *
 * Citizens can understand what the system knows, how it works,
 * and its limitations. No technical jargon.
 */

import { Shield, Database, Clock, BarChart3, Map, AlertTriangle, RefreshCw, ExternalLink } from 'lucide-react';
import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { HORIZON_META } from '../constants';
import DataFreshness from '../components/common/DataFreshness';
import { useDemoData } from '../demo';

/* ── Data Sources ──────────────────────────────────────────── */

const DATA_SOURCES = [
  {
    name: 'CAMS Copernicus',
    fullName: 'Copernicus Atmosphere Monitoring Service',
    what: 'Global atmospheric composition data including particulate matter concentrations',
    frequency: 'Updated every 3 hours',
    resolution: '~45km grid cells',
    url: 'https://atmosphere.copernicus.eu/',
    icon: Database,
    note: 'Data is interpolated to our grid — individual stations may differ.',
  },
  {
    name: 'Open-Meteo',
    fullName: 'Open-Meteo Weather API',
    what: 'Weather data: wind speed, temperature, humidity, precipitation',
    frequency: 'Updated hourly',
    resolution: 'Point-level forecasts',
    url: 'https://open-meteo.com/',
    icon: RefreshCw,
    note: 'Free weather service using multiple global weather models.',
  },
];

/* ── Methodology Cards ──────────────────────────────────────── */

const METHODOLOGY = [
  {
    title: 'PM2.5 Estimation',
    description: 'We use machine learning models (Ridge Regression, Histogram-Based Gradient Boosting) to estimate PM2.5 levels across Lahore from atmospheric data.',
    detail: 'Models are trained on historical patterns and validated against ground-truth measurements.',
    icon: BarChart3,
  },
  {
    title: 'Forecast System',
    description: 'Forecasts are generated at 5 time horizons: +1h, +3h, +6h, +12h, +24h.',
    detail: 'Shorter forecasts (+1h, +3h) are generally more reliable than longer ones (+12h, +24h). Confidence badges indicate expected reliability.',
    icon: Clock,
  },
  {
    title: 'Episode Detection',
    description: 'The system detects pollution episodes by combining current readings with historical pattern matching.',
    detail: 'When a current pattern closely resembles a known historical event, we use that history to provide context about what may happen next.',
    icon: AlertTriangle,
  },
  {
    title: 'Geographic Coverage',
    description: 'Lahore is covered by a grid of estimated readings. Individual neighborhoods may vary from the grid estimate.',
    detail: 'Wind direction and local sources (traffic, industry, construction) create micro-variations within the city.',
    icon: Map,
  },
];

/* ── Limitations ──────────────────────────────────────────── */

const LIMITATIONS = [
  {
    title: 'Grid Resolution',
    description: 'Our 45km grid cells cover the entire city with a single estimate. Actual pollution can vary significantly within a grid cell — a location near a busy road may be worse than the grid average.',
  },
  {
    title: 'No Direct Sensors',
    description: 'Lahore does not have a dense network of ground-level PM2.5 sensors. Our estimates are derived from atmospheric models, not direct measurements at each location.',
  },
  {
    title: 'Forecast Uncertainty',
    description: 'Forecasts become less reliable further into the future. +1h and +3h forecasts are most accurate. +12h and +24h forecasts indicate general trends but should not be treated as precise predictions.',
  },
  {
    title: 'Model Limitations',
    description: 'Machine learning models can only learn from patterns in historical data. Unprecedented events (sudden industrial accidents, unusual weather) may not be predicted accurately.',
  },
];

/* ── Component ─────────────────────────────────────────────── */

export default function DataTrustPage() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const liveForecast = useForecast();
  const liveEpisode = useEpisodeIntelligence();

  const freshness = isDemo ? null : liveForecast.freshness;

  return (
    <div className="page-container" style={{ maxWidth: 960, margin: '0 auto', padding: 'var(--sp-6) var(--sp-4)' }}>
      {/* Header with Lahore Skyline */}
      <header style={{ position: 'relative', overflow: 'hidden', borderRadius: 12, marginBottom: 'var(--sp-8)' }}>
        <div style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-3)' }}>
          <Shield size={24} color="var(--lp-brand-600)" />
          <h1 className="type-h1">Data Trust Center</h1>
        </div>
        <p className="type-body" style={{ position: 'relative', zIndex: 1, color: 'var(--lp-text-secondary)', maxWidth: 640 }}>
          Transparency about where our data comes from, how we process it,
          and what it can and cannot tell us. Understanding these limits
          helps you make better decisions.
        </p>
        <div className="lh-skyline" aria-hidden="true" />
      </header>

      {/* Demo notice */}
      {isDemo && (
        <div className="card card--accent card--severity-warning" style={{ marginBottom: 'var(--sp-6)' }}>
          <div className="type-small" style={{ fontWeight: 600, color: 'var(--lp-severity-usg)', marginBottom: 4 }}>
            Demo Mode Active
          </div>
          <div className="type-small" style={{ color: 'var(--slate-600)' }}>
            You are viewing simulated data for demonstration purposes.
            Live data from atmospheric models will appear when connected to the production backend.
          </div>
        </div>
      )}

      {/* Data Freshness */}
      {freshness && (
        <section style={{ marginBottom: 'var(--sp-8)' }}>
          <h2 className="type-h3" style={{ marginBottom: 'var(--sp-3)' }}>Current Data Status</h2>
          <div className="card">
            <DataFreshness freshness={freshness} />
          </div>
        </section>
      )}

      {/* Data Sources */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 className="type-h3" style={{ marginBottom: 'var(--sp-4)' }}>Data Sources</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          {DATA_SOURCES.map(source => {
            const Icon = source.icon;
            return (
              <div key={source.name} className="card">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--sp-3)' }}>
                  <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--lp-radius-md)',
                    background: 'var(--lp-brand-50)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Icon size={18} color="var(--lp-brand-600)" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 4 }}>
                      <span className="type-body" style={{ fontWeight: 600 }}>{source.name}</span>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`${source.fullName} (opens in new tab)`}
                        style={{ color: 'var(--lp-brand-600)' }}
                      >
                        <ExternalLink size={12} />
                      </a>
                    </div>
                    <div className="type-small" style={{ color: 'var(--lp-text-secondary)', marginBottom: 8 }}>
                      {source.description || source.what}
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--sp-4)', flexWrap: 'wrap' }}>
                      <span className="type-caption" style={{ color: 'var(--slate-500)' }}>
                        Update: {source.frequency}
                      </span>
                      <span className="type-caption" style={{ color: 'var(--slate-500)' }}>
                        Resolution: {source.resolution}
                      </span>
                    </div>
                    {source.note && (
                      <div className="type-caption" style={{ color: 'var(--slate-500)', marginTop: 8, fontStyle: 'italic' }}>
                        {source.note}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* How We Process Data */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 className="type-h3" style={{ marginBottom: 'var(--sp-4)' }}>How We Process Data</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--sp-4)' }}>
          {METHODOLOGY.map(item => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
                  <Icon size={16} color="var(--lp-brand-600)" />
                  <span className="type-body" style={{ fontWeight: 600 }}>{item.title}</span>
                </div>
                <p className="type-small" style={{ color: 'var(--lp-text-secondary)', margin: 0, marginBottom: 8 }}>
                  {item.description}
                </p>
                <p className="type-caption" style={{ color: 'var(--slate-500)', margin: 0, fontStyle: 'italic' }}>
                  {item.detail}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Forecast Reliability */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 className="type-h3" style={{ marginBottom: 'var(--sp-4)' }}>Understanding Forecast Confidence</h2>
        <div className="card">
          <p className="type-small" style={{ color: 'var(--lp-text-secondary)', marginBottom: 'var(--sp-4)' }}>
            Each forecast horizon has an expected reliability level. This is based on how atmospheric conditions
            typically behave at different time scales — it is not a guarantee.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--sp-3)' }}>
            {Object.entries(HORIZON_META).map(([h, meta]) => (
              <div key={h} style={{
                padding: 'var(--sp-3)',
                borderRadius: 'var(--lp-radius-md)',
                border: '1px solid var(--lp-border-subtle)',
                textAlign: 'center',
              }}>
                <div className="type-small" style={{ fontWeight: 600, marginBottom: 4 }}>+{meta.shortLabel}</div>
                <div style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  borderRadius: 12,
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  ...(meta.confidence === 'high'
                    ? { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' }
                    : meta.confidence === 'moderate'
                    ? { background: '#fefce8', color: '#854d0e', border: '1px solid #fde68a' }
                    : { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' }
                  ),
                }}>
                  {meta.confidence}
                </div>
              </div>
            ))}
          </div>
          <p className="type-caption" style={{ color: 'var(--slate-500)', marginTop: 'var(--sp-3)' }}>
            Confidence levels reflect typical forecast reliability. Actual accuracy varies with
            weather conditions, seasonal patterns, and atmospheric stability.
          </p>
        </div>
      </section>

      {/* Limitations */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 className="type-h3" style={{ marginBottom: 'var(--sp-4)' }}>Known Limitations</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
          {LIMITATIONS.map(item => (
            <div key={item.title} className="card card--accent" style={{ borderLeftColor: 'var(--lp-severity-usg)' }}>
              <div className="type-body" style={{ fontWeight: 600, marginBottom: 4 }}>{item.title}</div>
              <p className="type-small" style={{ color: 'var(--lp-text-secondary)', margin: 0 }}>
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Privacy Note */}
      <section style={{ marginBottom: 'var(--sp-6)' }}>
        <div className="card card--elevated" style={{ padding: 'var(--sp-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
            <Shield size={16} color="var(--lp-brand-600)" />
            <span className="type-body" style={{ fontWeight: 600 }}>Your Privacy</span>
          </div>
          <p className="type-small" style={{ color: 'var(--lp-text-secondary)', margin: 0 }}>
            Lahore+ does not collect personal data. No cookies, no tracking, no accounts required for the citizen interface.
            The Command Center uses role-based authentication for authorized personnel only.
          </p>
        </div>
      </section>
    </div>
  );
}
