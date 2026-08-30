/**
 * OperatorMetrics — Operational KPIs for government command center.
 *
 * Shows system health and operational metrics at a glance:
 * - Active incidents count
 * - Data freshness
 * - Station health (online/total)
 * - Model performance (R² from forecast status)
 * - Forecast confidence
 * - Current severity level
 *
 * Pure display component — reads from props only.
 */

import { PM25_LEVELS } from '../../constants';
import {
  AlertTriangle,
  Activity,
  Radio,
  BarChart3,
  Clock,
  Shield,
} from 'lucide-react';

function MetricCard({ icon: Icon, label, value, sub, color, bg }) {
  return (
    <div className="op-metric lp-card-depth">
      <div className="op-metric__icon" style={{ color: color || 'var(--lp-brand-600)', background: bg || 'var(--lp-brand-50, #f0fdfa)' }}>
        <Icon size={18} />
      </div>
      <div className="op-metric__content">
        <span className="op-metric__label">{label}</span>
        <span className="op-metric__value" style={{ color }}>{value}</span>
        {sub && <span className="op-metric__sub">{sub}</span>}
      </div>
    </div>
  );
}

export default function OperatorMetrics({
  currentPM25,
  episode,
  stations,
  forecastStatus,
  online,
}) {
  const level = currentPM25 != null
    ? PM25_LEVELS.find(l => currentPM25 <= l.max) || PM25_LEVELS[PM25_LEVELS.length - 1]
    : null;

  const activeIncidents = episode?.state === 'episode' ? 1 : 0;
  const stationCount = stations?.length || 0;
  const r2 = forecastStatus?.metrics?.r2 ?? null;
  const freshness = forecastStatus?.freshness || 'unknown';

  const freshnessColor = freshness === 'fresh' ? '#16a34a'
    : freshness === 'aging' ? '#ca8a04'
    : freshness === 'stale' ? '#dc2626'
    : '#6b7280';

  const freshnessLabel = freshness === 'fresh' ? 'Fresh'
    : freshness === 'aging' ? 'Aging'
    : freshness === 'stale' ? 'Stale'
    : 'Unknown';

  return (
    <div className="op-metrics lp-motion-stagger" role="region" aria-label="Operator dashboard metrics">
      <MetricCard
        icon={AlertTriangle}
        label="Active Incidents"
        value={activeIncidents > 0 ? activeIncidents : 'None'}
        sub={activeIncidents > 0 ? 'Requires attention' : 'All clear'}
        color={activeIncidents > 0 ? '#dc2626' : '#16a34a'}
        bg={activeIncidents > 0 ? '#fef2f2' : '#f0fdf4'}
      />
      <MetricCard
        icon={Radio}
        label="Station Coverage"
        value={stationCount > 0 ? stationCount : '—'}
        sub={stationCount > 0 ? `${stationCount} monitoring` : 'No stations'}
        color="var(--lp-brand-600)"
        bg="var(--lp-brand-50, #f0fdfa)"
      />
      <MetricCard
        icon={Clock}
        label="Data Freshness"
        value={freshnessLabel}
        sub={online ? 'API online' : 'API offline'}
        color={freshnessColor}
        bg={freshness === 'fresh' ? '#f0fdf4' : freshness === 'stale' ? '#fef2f2' : '#fefce8'}
      />
      <MetricCard
        icon={BarChart3}
        label="Model R²"
        value={r2 != null ? r2.toFixed(3) : '—'}
        sub={r2 != null ? (r2 >= 0.9 ? 'Strong fit' : r2 >= 0.7 ? 'Moderate' : 'Weak') : 'No metrics'}
        color={r2 != null ? (r2 >= 0.9 ? '#16a34a' : r2 >= 0.7 ? '#ca8a04' : '#dc2626') : '#6b7280'}
        bg={r2 != null ? (r2 >= 0.9 ? '#f0fdf4' : '#fefce8') : '#f9fafb'}
      />
      <MetricCard
        icon={Shield}
        label="Severity"
        value={level?.label || '—'}
        sub={currentPM25 != null ? `${Math.round(currentPM25)} μg/m³` : 'No data'}
        color={level?.color || '#6b7280'}
        bg={level?.bg || '#f9fafb'}
      />
      <MetricCard
        icon={Activity}
        label="Episode State"
        value={episode?.state ? episode.state.charAt(0).toUpperCase() + episode.state.slice(1) : 'Normal'}
        sub={episode?.trajectory ? `Trending ${episode.trajectory}` : 'Stable'}
        color={episode?.state === 'episode' ? '#dc2626' : episode?.state === 'improving' ? '#16a34a' : 'var(--lp-text-secondary)'}
        bg={episode?.state === 'episode' ? '#fef2f2' : episode?.state === 'improving' ? '#f0fdf4' : '#f9fafb'}
      />
    </div>
  );
}
