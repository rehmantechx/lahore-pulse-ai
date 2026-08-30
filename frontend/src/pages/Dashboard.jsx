/**
 * Dashboard — Public landing dashboard.
 *
 * Composes existing live air-quality capabilities into the primary dashboard
 * layout: current conditions, outlook, recommendations, map, insights, and alerts.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ExternalLink,
  Home,
  Info,
  Map as MapIcon,
  Radio,
  Wind,
} from 'lucide-react';
import { useForecast } from '../hooks/useForecast';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { getStations } from '../services/api';
import { HORIZONS, HORIZON_META } from '../constants';
import { useDemoData } from '../demo';
import AQIGauge from '../components/citizen/AQIGauge.jsx';
import ForecastChart from '../components/forecast/ForecastChart.jsx';
import LahoreMap from '../components/map/LahoreMap.jsx';

function getAirQualityInfo(value) {
  if (value == null || Number.isNaN(value)) return { label: 'No Data', color: '#64748b', bg: '#f8fafc' };
  if (value <= 12) return { label: 'Excellent', color: '#16a34a', bg: '#f0fdf4' };
  if (value <= 25) return { label: 'Good', color: '#65a30d', bg: '#f7fee7' };
  if (value <= 35) return { label: 'Fair', color: '#ca8a04', bg: '#fefce8' };
  if (value <= 55) return { label: 'Moderate', color: '#ea580c', bg: '#fff7ed' };
  if (value <= 90) return { label: 'Poor', color: '#ef4444', bg: '#fef2f2' };
  if (value <= 150) return { label: 'Very Poor', color: '#dc2626', bg: '#fef2f2' };
  return { label: 'Hazardous', color: '#7f1d1d', bg: '#fef2f2' };
}

function getForecastItems(forecasts) {
  return [1, ...HORIZONS.filter((horizon) => horizon !== 1)].map((horizon) => ({
    horizon,
    label: horizon === 1 ? 'Now' : `+${HORIZON_META[horizon].shortLabel}`,
    value: forecasts?.[String(horizon)]?.predicted_pm25,
  }));
}

function getAdvice(value) {
  if (value == null) return [
    { title: 'Check current conditions', detail: 'Review the latest reading before heading outside.', icon: Info, tone: 'blue' },
  ];
  if (value > 55) return [
    { title: 'Avoid outdoor exercise', detail: 'High pollution levels may cause breathing discomfort.', icon: Wind, tone: 'red' },
    { title: 'Keep windows closed', detail: 'Prevent polluted air from entering your home.', icon: Home, tone: 'amber' },
    { title: 'Use air purifiers', detail: 'Indoor air purification can help reduce health risks.', icon: Radio, tone: 'green' },
  ];
  return [
    { title: 'Enjoy outdoor time', detail: 'Conditions are suitable for most outdoor activities.', icon: Wind, tone: 'green' },
    { title: 'Check conditions before heading out', detail: 'Air quality can change across Lahore during the day.', icon: Info, tone: 'amber' },
    { title: 'Stay informed', detail: 'Keep an eye on the outlook as conditions change.', icon: Bell, tone: 'blue' },
  ];
}

function SectionHeader({ icon: Icon, title, link, to }) {
  return (
    <div className="dashboard-section__header">
      <div className="dashboard-section__title-wrap"><Icon size={18} strokeWidth={1.8} /><h2>{title}</h2></div>
      {link && <Link to={to} className="dashboard-section__link">{link}<ExternalLink size={13} /></Link>}
    </div>
  );
}

function CurrentQuality({ currentValue, loading, episode }) {
  const info = getAirQualityInfo(currentValue);
  const episodeActive = episode?.state === 'episode';
  return (
    <section className="dashboard-panel dashboard-current">
      <h2 className="dashboard-panel__title">Current Air Quality</h2>
      <div className="dashboard-current__main">
        <AQIGauge value={currentValue} size="medium" loading={loading} />
        <div className="dashboard-current__summary">
          <span className="dashboard-status-pill" style={{ color: info.color, background: info.bg }}><span style={{ background: info.color }} /> Live · {info.label}</span>
          <p>Air quality is {info.label.toLowerCase()}. {currentValue > 55 ? 'Limit outdoor time and keep windows closed.' : 'Enjoy Lahore while staying informed.'}</p>
        </div>
      </div>
      <div className="dashboard-current__stats">
        <span><Wind size={15} /><b>{currentValue != null ? currentValue.toFixed(1) : '—'}</b><small>Current reading</small></span>
        <span><Radio size={15} /><b>{episodeActive ? 'Active' : 'Clear'}</b><small>Episode status</small></span>
      </div>
      <div className={`dashboard-callout dashboard-callout--${episodeActive ? 'danger' : 'success'}`}>
        {episodeActive ? <AlertTriangle size={17} /> : <CheckCircle2 size={17} />}
        <div><strong>{episodeActive ? 'Pollution episode detected.' : 'No pollution episode is currently detected.'}</strong><span>{episode?.trajectory_description || 'Keep checking the outlook for changes.'}</span></div>
      </div>
    </section>
  );
}

function Outlook({ forecasts }) {
  const items = getForecastItems(forecasts);
  return (
    <section className="dashboard-panel dashboard-outlook">
      <h2 className="dashboard-panel__title">24-Hour Outlook</h2>
      <div className="dashboard-outlook__items">
        {items.map((item, index) => {
          const info = getAirQualityInfo(item.value);
          return <div key={item.horizon} className={`dashboard-outlook__item${index === 0 ? ' is-active' : ''}`}><b>{item.label}</b><strong style={{ color: info.color }}>{item.value != null ? Math.round(item.value) : '—'}</strong><span>{item.value != null ? info.label : 'No data'}</span></div>;
        })}
      </div>
      <ForecastChart forecasts={forecasts} currentObservation={forecasts?.['1']} />
    </section>
  );
}

function Recommendations({ currentValue }) {
  return <section className="dashboard-panel dashboard-advice"><h2 className="dashboard-panel__title">What You Should Do</h2><div className="dashboard-advice__list">{getAdvice(currentValue).map(({ title, detail, icon: Icon, tone }) => <div key={title} className="dashboard-advice__item"><span className={`dashboard-icon dashboard-icon--${tone}`}><Icon size={19} /></span><div><strong>{title}</strong><p>{detail}</p></div></div>)}</div><Link to="/air-quality" className="dashboard-panel__action">View All Recommendations <ExternalLink size={13} /></Link></section>;
}

export default function Dashboard() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const { forecasts, loading: forecastLoading } = useForecast();
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const [stations, setStations] = useState([]);
  const currentValue = forecasts?.['1']?.predicted_pm25 ?? episode?.current_pm25 ?? null;
  const loading = forecastLoading || episodeLoading;
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    getStations({ signal: AbortSignal.timeout(10000) }).then((data) => {
      if (!cancelled) setStations(data.stations || []);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [isDemo]);

  return (
    <div className="dashboard-page">
      <div className="dashboard-page__context"><MapIcon size={14} /><strong>Lahore, Punjab</strong><span>•</span><span>{today}</span><span>⌄</span></div>
      <header className="dashboard-page__hero"><div><h1>Know the air.<br /><em>Verify the forecast.</em></h1><p>Real-time air quality and forecasts —<br />every prediction checked against reality.</p></div><div className="dashboard-page__skyline" aria-hidden="true" /></header>
      <div className="dashboard-grid dashboard-grid--top"><CurrentQuality currentValue={currentValue} loading={loading} episode={episode} /><Outlook forecasts={forecasts} /><Recommendations currentValue={currentValue} /></div>
      <div className="dashboard-grid dashboard-grid--bottom">
        <section className="dashboard-panel dashboard-map"><SectionHeader icon={MapIcon} title="Air Quality Map" link="View Full Map" to="/city-map" /><div className="dashboard-map__canvas"><LahoreMap pm25Value={currentValue} label="Lahore" stations={stations} allowFullscreen={false} /></div></section>
        <section className="dashboard-panel dashboard-insights"><SectionHeader icon={Info} title="Today's Insights" link="View All Insights" to="/insights" /><div className="dashboard-insights__list"><div><span className="dashboard-icon dashboard-icon--red"><AlertTriangle size={18} /></span><p><strong>{episode?.trajectory === 'rising' ? 'Air quality is getting worse' : 'Air quality is being monitored'}</strong><small>{episode?.narrative || 'Live readings are being compared with the forecast.'}</small></p></div><div><span className="dashboard-icon dashboard-icon--amber"><Wind size={18} /></span><p><strong>Check the outlook before heading out</strong><small>Use the forecast to plan outdoor activities.</small></p></div><div><span className="dashboard-icon dashboard-icon--green"><CheckCircle2 size={18} /></span><p><strong>{episode?.state === 'episode' ? 'Stay alert to changes' : 'No active pollution episode'}</strong><small>{episode?.trajectory_description || 'Conditions are being tracked across Lahore.'}</small></p></div></div></section>
        <section className="dashboard-panel dashboard-alerts"><SectionHeader icon={Bell} title="Active Alerts" link="View All Alerts" to="/alerts" /><div className={`dashboard-alerts__state dashboard-alerts__state--${episode?.state === 'episode' ? 'danger' : 'clear'}`}>{episode?.state === 'episode' ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />}<div><strong>{episode?.state === 'episode' ? 'Active pollution episode' : 'No Active Alerts'}</strong><p>{episode?.narrative || 'There are currently no air quality alerts.'}</p></div></div><div className="dashboard-alerts__note"><Bell size={15} /> We’ll notify you when conditions change.</div></section>
      </div>
    </div>
  );
}
