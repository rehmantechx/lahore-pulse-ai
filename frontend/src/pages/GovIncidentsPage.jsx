/**
 * GovIncidentsPage — Government incident lifecycle management.
 *
 * Full incident tracking with:
 * - Lifecycle stages: Detected → Investigating → Responding → Monitoring → Resolved
 * - Severity classification from PM2.5 readings
 * - Timeline of events for each incident
 * - Filtering by status and severity
 * - Search by ID, title, or area
 * - Auto-derivation from episode intelligence
 *
 * Incidents are stored in localStorage (prototype).
 * Production would use a backend API with database persistence.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useForecast } from '../hooks/useForecast';
import {
  getIncidents,
  getIncidentStats,
  createIncident,
  seedDemoIncidents,
  INCIDENT_STAGES,
  SEVERITY_CONFIG,
} from '../lib/incidentStore';
import IncidentCard from '../components/incident/IncidentCard';
import LoadingState from '../components/common/LoadingState';
import {
  Filter,
  Search,
  PlusCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
} from 'lucide-react';

// ── Stat badge helper ────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color, bg }) {
  return (
    <div className="card" style={{
      display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
      padding: 'var(--sp-3) var(--sp-4)',
      borderLeft: `3px solid ${color || 'var(--lp-border-subtle)'}`,
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 'var(--lp-radius-md)',
        background: bg || 'var(--slate-50)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={16} color={color || 'var(--lp-text-muted)'} />
      </div>
      <div>
        <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--lp-text-primary)', lineHeight: 1.2 }}>
          {value}
        </div>
        <div style={{ fontSize: '0.6875rem', color: 'var(--lp-text-muted)' }}>{label}</div>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export default function GovIncidentsPage() {
  const { episode, loading: episodeLoading } = useEpisodeIntelligence();
  const { forecasts, loading: forecastLoading } = useForecast();

  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [statusFilter, setStatusFilter] = useState('active');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [updateKey, setUpdateKey] = useState(0);

  // Load/refresh incidents from store
  const refreshIncidents = useCallback(() => {
    const statusParam = statusFilter === 'active' ? undefined : statusFilter;
    const all = getIncidents({
      status: statusParam === 'active' ? undefined : statusParam,
      severity: severityFilter !== 'all' ? severityFilter : undefined,
      search: searchQuery || undefined,
    });

    // Filter "active" = all non-resolved
    const filtered = statusFilter === 'active'
      ? all.filter(i => i.stage !== 'resolved')
      : statusFilter === 'resolved'
        ? all.filter(i => i.stage === 'resolved')
        : all;

    setIncidents(filtered);
    setStats(getIncidentStats());
  }, [statusFilter, severityFilter, searchQuery, updateKey]);

  useEffect(() => {
    refreshIncidents();
  }, [refreshIncidents]);

  // Seed demo incidents on first load
  useEffect(() => {
    seedDemoIncidents();
    refreshIncidents();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-create incident when episode is detected
  useEffect(() => {
    if (!episode || episodeLoading) return;

    const pm25 = episode.current_pm25 ?? forecasts?.['1']?.predicted_pm25 ?? null;
    if (pm25 != null && episode.state === 'episode') {
      createIncident({
        pm25,
        state: episode.state,
        trajectory: episode.trajectory,
        narrative: episode.narrative,
        area: 'Lahore City Center',
      });
      refreshIncidents();
    }
  }, [episode, episodeLoading, forecasts]); // eslint-disable-line react-hooks/exhaustive-deps

  const loading = episodeLoading || forecastLoading;
  const handleUpdate = useCallback(() => setUpdateKey(k => k + 1), []);

  // Active stage filter chips
  const statusChips = useMemo(() => [
    { id: 'active', label: 'Active', icon: AlertTriangle },
    ...INCIDENT_STAGES.filter(s => s.id !== 'resolved').map(s => ({ id: s.id, label: s.label })),
    { id: 'resolved', label: 'Resolved', icon: CheckCircle },
  ], []);

  return (
    <div className="page page--wide">
      <h1 className="page__title">Incident Lifecycle</h1>
      <p className="page__subtitle">
        Track and manage pollution incidents through detection, investigation, response, and resolution
      </p>

      {/* Stats row */}
      {stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 'var(--sp-3)',
          marginTop: 'var(--sp-4)',
        }}>
          <StatCard icon={AlertTriangle} label="Active Incidents" value={stats.activeCount} color="#dc2626" bg="#fef2f2" />
          <StatCard icon={Activity} label="Investigating" value={stats.byStage.investigating || 0} color="#ea580c" bg="#fff7ed" />
          <StatCard icon={Clock} label="Monitoring" value={stats.byStage.monitoring || 0} color="#2563eb" bg="#eff6ff" />
          <StatCard icon={CheckCircle} label="Resolved" value={stats.resolvedCount} color="#16a34a" bg="#f0fdf4" />
        </div>
      )}

      {/* Filters bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--sp-3)',
        marginTop: 'var(--sp-4)',
        flexWrap: 'wrap',
      }}>
        {/* Status chips */}
        <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
          {statusChips.map(chip => {
            const isActive = statusFilter === chip.id;
            const Icon = chip.icon;
            return (
              <button
                key={chip.id}
                className={`btn btn--sm ${isActive ? 'btn--primary' : 'btn--ghost'}`}
                onClick={() => setStatusFilter(chip.id)}
                style={{
                  fontSize: '0.6875rem',
                  display: 'flex', alignItems: 'center', gap: 3,
                  padding: '4px 10px',
                }}
              >
                {Icon && <Icon size={12} />}
                {chip.label}
                {chip.id === 'active' && stats && (
                  <span style={{
                    marginLeft: 2,
                    fontSize: '0.625rem',
                    background: isActive ? 'rgba(255,255,255,0.3)' : 'var(--slate-200)',
                    borderRadius: 8,
                    padding: '0 5px',
                    lineHeight: '14px',
                  }}>
                    {stats.activeCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Severity filter */}
        <select
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
          className="select"
          style={{
            fontSize: '0.75rem',
            padding: '4px 8px',
            borderRadius: 'var(--lp-radius-md)',
            border: '1px solid var(--lp-border-subtle)',
          }}
        >
          <option value="all">All Severity</option>
          {Object.entries(SEVERITY_CONFIG).filter(([k]) => k !== 'unknown').map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label}</option>
          ))}
        </select>

        {/* Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)', flex: 1, minWidth: 200 }}>
          <Search size={14} color="var(--lp-text-muted)" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search incidents..."
            className="input"
            style={{
              flex: 1, fontSize: '0.75rem', padding: '4px 8px',
              border: '1px solid var(--lp-border-subtle)',
              borderRadius: 'var(--lp-radius-md)',
            }}
          />
        </div>
      </div>

      {/* Incident list */}
      {loading && !incidents.length ? (
        <LoadingState message="Loading incidents..." />
      ) : incidents.length === 0 ? (
        <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
          <div className="surface__body" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
            <CheckCircle size={32} color="var(--lp-text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.5 }} />
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-tertiary)' }}>
              {statusFilter === 'active'
                ? 'No active incidents. All clear!'
                : 'No incidents match your filters.'
              }
            </p>
          </div>
        </div>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--sp-3)',
          marginTop: 'var(--sp-4)',
        }}>
          {incidents.map(incident => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              onUpdate={handleUpdate}
            />
          ))}
        </div>
      )}

      {/* Data source note */}
      <div style={{
        marginTop: 'var(--sp-6)',
        padding: 'var(--sp-3)',
        background: 'var(--slate-50)',
        borderRadius: 'var(--lp-radius-md)',
        fontSize: '0.6875rem',
        color: 'var(--lp-text-muted)',
        lineHeight: 1.6,
      }}>
        <strong>Incident Lifecycle:</strong> Incidents are automatically created when episodes are detected by the rule-based system
        (PM2.5 &gt; 120 μg/m³ AND increase ≥ 30 in 6h, sustained ≥ 3h). Officers advance incidents through lifecycle stages.
        Data is stored locally — production would use a backend database.
      </div>
    </div>
  );
}
