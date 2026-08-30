/**
 * InvestigationBrief — Evidence-to-investigation bridge.
 *
 * Combines episode state, Source Compass directional evidence,
 * and weather-compatible investigation domains into a single
 * incident briefing card.
 *
 * CRITICAL SAFETY RULES:
 * - Source Compass strongest sector does NOT choose the domain
 * - Domains are evaluated by weather triggers only
 * - Directional evidence is context, not proof
 * - This is NOT a source attribution
 */

import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, ClipboardList } from 'lucide-react';
import { PM25_LEVELS, SOURCE_COMPASS_SECTORS, SOURCE_COMPASS_ASSOCIATIONS } from '../../constants';
import { RESPONSE_DOMAINS, evaluateDomain, getDomainStatus } from '../../config/responseDomains';

// ── Helpers ─────────────────────────────────────────────────

function severityFor(pm25) {
  if (pm25 == null) return { label: 'Unknown', color: '#6b7280' };
  for (const lv of PM25_LEVELS) {
    if (pm25 <= lv.max) return { label: lv.label, color: lv.color };
  }
  return { label: 'Hazardous', color: '#7f1d1d' };
}

const BADGES = {
  episode:   { label: 'ACTIVE EPISODE',    color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  improving: { label: 'IMPROVING',          color: '#a16207', bg: '#fefce8', border: '#fde68a' },
  normal:    { label: 'NO INCIDENT',        color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  uncertain: { label: 'INSUFFICIENT DATA',  color: '#6b7280', bg: '#f8fafc', border: '#e2e8f0' },
};

const EvRow = ({ label, children, color }) => (
  <div className="ib-evidence__row">
    <span className="ib-evidence__label">{label}</span>
    <span className="ib-evidence__value" style={color ? { color } : undefined}>{children}</span>
  </div>
);

// ── Sub-components ──────────────────────────────────────────

function Header({ badge }) {
  return (
    <div className="ib-header">
      <div className="ib-header__left">
        <ClipboardList size={16} color="var(--slate-600)" aria-hidden="true" />
        <span className="ib-header__title">Investigation Brief</span>
      </div>
      <span className="ib-badge" style={{ background: badge.bg, color: badge.color, borderColor: badge.border }}>
        {badge.label}
      </span>
    </div>
  );
}

// ── Component ───────────────────────────────────────────────

export default function InvestigationBrief({ episode, onStartWorkflow }) {
  const state = episode?.state || 'uncertain';
  const badge = BADGES[state] || BADGES.uncertain;
  const pm25 = episode?.current_pm25 ?? null;
  const sv = severityFor(pm25);
  const compass = episode?.source_compass;
  const weatherVars = episode?.weather_context?.variables || [];
  const isEpisode = state === 'episode';
  const isShort = state === 'normal' || state === 'uncertain';

  const domainResults = useMemo(() =>
    RESPONSE_DOMAINS.map((d) => {
      const ev = evaluateDomain(d, weatherVars);
      return { ...d, ev, ...getDomainStatus(ev, state) };
    }), [weatherVars, state]);

  const historical = compass?.historical;
  const currentWind = compass?.current_wind;
  const assocLabel = historical?.association_label || 'INSUFFICIENT DATA';
  const assocMeta = SOURCE_COMPASS_ASSOCIATIONS[assocLabel] || SOURCE_COMPASS_ASSOCIATIONS.INSUFFICIENT;
  const sectorDef = historical?.strongest_sector
    ? SOURCE_COMPASS_SECTORS.find((s) => s.key === historical.strongest_sector)
    : null;

  // ── Short states (normal / uncertain) ─────────────────────
  if (isShort) {
    const msg = state === 'normal'
      ? { text: 'No active pollution incident.', color: '#166534',
          sub: 'Investigation brief is not applicable during normal conditions.' }
      : { text: 'Insufficient data for investigation recommendations.', color: '#6b7280',
          sub: 'Current data conditions do not support reliable domain evaluation.' };
    return (
      <div className="ib">
        <Header badge={badge} />
        <div className="ib-short">
          <div className="ib-short__title" style={{ color: msg.color }}>{msg.text}</div>
          <div className="ib-short__sub">{msg.sub}</div>
        </div>
      </div>
    );
  }

  // ── Active / Improving ────────────────────────────────────
  const posture = state === 'improving' ? 'MONITOR / REVIEW' : 'INVESTIGATION RECOMMENDED';

  return (
    <div className="ib">
      <Header badge={badge} />

      {/* Incident row */}
      <div className="ib-incident" style={{ background: badge.bg, borderBottom: `1px solid ${badge.border}` }}>
        <div className="ib-incident__dot" style={{ background: badge.color }} />
        <div>
          <div className="ib-incident__label" style={{ color: badge.color }}>{posture}</div>
          <div className="ib-incident__detail">
            PM2.5: <strong style={{ color: sv.color }}>{pm25 != null ? `${pm25.toFixed(1)} μg/m³` : '—'}</strong>
            {pm25 != null && (
              <span style={{ marginLeft: 6, color: sv.color, fontWeight: 600 }}>{sv.label}</span>
            )}
            {episode?.trajectory && episode.trajectory !== 'unknown' && (
              <span style={{ marginLeft: 6, color: '#94a3b8', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                · {episode.trajectory === 'rising' ? <TrendingUp size={14} /> : episode.trajectory === 'falling' ? <TrendingDown size={14} /> : <Minus size={14} />}{' '}
                {episode.trajectory}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Directional evidence */}
      <div className="ib-section">Directional Evidence</div>
      <div className="ib-evidence">
        <EvRow label="Current wind">
          {currentWind?.sector
            ? `${currentWind.sector} (${currentWind.direction_degrees}°)` : '—'}
          {currentWind?.wind_speed_ms != null && (
            <span className="ib-evidence__sub"> at {currentWind.wind_speed_ms} m/s</span>
          )}
          {currentWind?.is_calm && (
            <span className="ib-evidence__sub" style={{ color: '#ca8a04' }}> (calm)</span>
          )}
        </EvRow>
        <EvRow label="Strongest sector">
          {sectorDef ? `${historical.strongest_sector} (${sectorDef.label})` : '—'}
          {historical?.strongest_enrichment >= 1.0 && (
            <span className="ib-evidence__sub"> {historical.strongest_enrichment.toFixed(2)}×</span>
          )}
        </EvRow>
        <EvRow label="Evidence">
          {historical?.evidence_count ?? '—'} episode-hours
          {historical?.total_episode_hours > 0 && (
            <span className="ib-evidence__sub"> of {historical.total_episode_hours} total</span>
          )}
        </EvRow>
        <EvRow label="Association" color={assocMeta.color}>{assocLabel}</EvRow>
        <EvRow label="Analysis season">
          {historical?.season === 'winter' ? '❄ Winter (Oct–Mar)' : '☀ Non-winter'}
        </EvRow>
      </div>

      <div className="ib-divider" />

      {/* Investigation domains */}
      <div className="ib-section">Investigation Domains</div>
      {domainResults.map((d) => (
        <div key={d.id} className="ib-domain">
          <div className="ib-domain__left">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 12 }}>{d.icon}</span>
                <span className="ib-domain__name">{d.name}</span>
              </div>
              <div className="ib-domain__reason">{d.ev.reason}</div>
              {d.status === 'INVESTIGATE' && (
                <div className="ib-domain__context">
                  {historical?.strongest_sector
                    ? `${historical.strongest_sector} directional association is present`
                    : 'No directional data'}
                </div>
              )}
            </div>
          </div>
          <span className="ib-badge"
            style={{ background: d.statusBg, color: d.statusColor, borderColor: d.statusBorder }}>
            {d.status}
          </span>
        </div>
      ))}

      {/* Disclaimer */}
      <div className="ib-disclaimer">
        Directional evidence is a statistical association and does not confirm a pollution source.
        Investigation domains are weather-compatible response areas, not confirmed emission sources.
        No government dispatch.
      </div>

      {/* Response handoff */}
      {isEpisode && (
        <div className="ib-handoff">
          <span className="ib-handoff__label">Investigation workflow available</span>
          <button
            className="btn btn--primary btn--sm"
            onClick={onStartWorkflow}
            aria-label="Start response workflow"
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            Start Response Workflow
          </button>
        </div>
      )}
    </div>
  );
}
