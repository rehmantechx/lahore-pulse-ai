/**
 * SourceCompass -- Directional investigation intelligence.
 *
 * Displays a visual compass rose showing wind-driven enrichment
 * analysis.  The compass does NOT identify pollution sources --
 * it suggests an investigation corridor based on how often winds
 * from each sector coincide with elevated PM2.5 episodes.
 *
 * Data source: Phase 2 hostile validation (10/10 attacks passed).
 * 96% of episodes occur October–March; analysis defaults to winter.
 *
 * Design: Inline styles matching the Episode Intelligence system.
 */

import { AlertTriangle } from 'lucide-react';
import { SOURCE_COMPASS_SECTORS, SOURCE_COMPASS_ASSOCIATIONS, SOURCE_COMPASS_DISCLAIMER } from '../../constants';

/**
 * SVG compass rose — 8 sectors with the strongest highlighted.
 */
function CompassRose({ profile, strongestSector, associationLabel }) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 85;
  const innerR = 30;
  const labelR = outerR + 16;

  const associationMeta = SOURCE_COMPASS_ASSOCIATIONS[associationLabel] || SOURCE_COMPASS_ASSOCIATIONS.INSUFFICIENT;

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      role="img"
      aria-label={`Compass rose. Strongest sector: ${strongestSector}, ${associationLabel} association.`}
      style={{ display: 'block' }}
    >
      {/* Sector wedges */}
      {profile.map((entry, i) => {
        const sectorDef = SOURCE_COMPASS_SECTORS.find(s => s.key === entry.sector);
        if (!sectorDef) return null;

        const startAngle = (i * 45 - 22.5) * (Math.PI / 180);
        const endAngle = (i * 45 + 22.5) * (Math.PI / 180);
        const midAngle = i * 45 * (Math.PI / 180);

        // Enrichment scales the radius: 1.0 = innerR, 2.0+ = outerR
        const enrichmentRatio = Math.min(entry.enrichment, 2.0);
        const norm = (enrichmentRatio - 1.0); // 0..1
        const wedgeR = innerR + norm * (outerR - innerR);

        const x1o = cx + wedgeR * Math.cos(startAngle);
        const y1o = cy + wedgeR * Math.sin(startAngle);
        const x2o = cx + wedgeR * Math.cos(endAngle);
        const y2o = cy + wedgeR * Math.sin(endAngle);
        const x1i = cx + innerR * Math.cos(startAngle);
        const y1i = cy + innerR * Math.sin(startAngle);
        const x2i = cx + innerR * Math.cos(endAngle);
        const y2i = cy + innerR * Math.sin(endAngle);

        const largeArc = 0;
        const d = [
          `M ${x1i} ${y1i}`,
          `L ${x1o} ${y1o}`,
          `A ${wedgeR} ${wedgeR} 0 ${largeArc} 1 ${x2o} ${y2o}`,
          `L ${x2i} ${y2i}`,
          `A ${innerR} ${innerR} 0 ${largeArc} 0 ${x1i} ${y1i}`,
          'Z',
        ].join(' ');

        const isStrongest = entry.sector === strongestSector;
        const fillColor = isStrongest ? associationMeta.color : sectorDef.color;
        const fillOpacity = isStrongest ? 0.85 : 0.35;

        return (
          <g key={entry.sector}>
            <path
              d={d}
              fill={fillColor}
              fillOpacity={fillOpacity}
              stroke="#fff"
              strokeWidth={1.5}
            />
            {/* Sector label */}
            <text
              x={cx + labelR * Math.cos(midAngle)}
              y={cy + labelR * Math.sin(midAngle)}
              textAnchor="middle"
              dominantBaseline="central"
              style={{
                fontSize: '10px',
                fontWeight: isStrongest ? 700 : 500,
                fill: isStrongest ? associationMeta.color : '#64748b',
                fontFamily: 'system-ui, sans-serif',
              }}
            >
              {entry.sector}
            </text>
          </g>
        );
      })}

      {/* Center circle */}
      <circle cx={cx} cy={cy} r={innerR - 2} fill="#f8fafc" stroke="#e2e8f0" strokeWidth={1} />

      {/* Center label */}
      <text
        x={cx}
        y={cy - 4}
        textAnchor="middle"
        style={{ fontSize: '8px', fill: '#94a3b8', fontFamily: 'system-ui, sans-serif' }}
      >
        ENRICHMENT
      </text>
      <text
        x={cx}
        y={cy + 6}
        textAnchor="middle"
        style={{ fontSize: '8px', fill: '#94a3b8', fontFamily: 'system-ui, sans-serif' }}
      >
        RATIO
      </text>
    </svg>
  );
}

/**
 * Current wind indicator — shows direction arrow and speed.
 */
function CurrentWind({ wind }) {
  if (!wind || wind.direction_degrees == null) {
    return (
      <div style={styles.mutedBox}>
        <span style={styles.mutedText}>Current wind data unavailable</span>
      </div>
    );
  }

  const arrowRotation = wind.direction_degrees;
  const sectorDef = SOURCE_COMPASS_SECTORS.find(s => s.key === wind.sector);

  return (
    <div style={styles.windRow}>
      <div style={{
        width: 36,
        height: 36,
        borderRadius: '50%',
        border: '2px solid #e2e8f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        <span
          style={{
            display: 'inline-block',
            fontSize: '18px',
            transform: `rotate(${arrowRotation}deg)`,
            transformOrigin: 'center center',
            color: sectorDef?.color || '#64748b',
          }}
          aria-label={`Wind from ${wind.sector || 'unknown'} at ${wind.direction_degrees} degrees`}
        >
          ↓
        </span>
      </div>
      <div>
        <div style={styles.windLabel}>
          {sectorDef?.label || wind.sector || '—'} ({wind.direction_degrees}°)
        </div>
        <div style={styles.windSpeed}>
          {wind.is_calm
            ? 'Calm (< 1 m/s)'
            : `${wind.wind_speed_ms} m/s`
          }
        </div>
      </div>
    </div>
  );
}

/**
 * Investigation corridor summary for the Response Orchestrator.
 */
function InvestigationHint({ hint }) {
  if (!hint) return null;

  const sectors = hint.corridor_sectors || [];
  const description = hint.description || hint.message || '';
  const suggestedDomains = hint.suggested_response_domains || hint.suggested_domains || [];

  return (
    <div style={styles.hintBox}>
      <div style={styles.hintTitle}>⬆ Investigation Corridor</div>
      <div style={styles.hintDescription}>{description}</div>
      {sectors.length > 0 && (
        <div style={styles.hintSectors}>
          {sectors.map(s => (
            <span key={s} style={styles.sectorBadge}>{s}</span>
          ))}
        </div>
      )}
      {suggestedDomains.length > 0 && (
        <div style={styles.hintDomains}>
          Suggested: {suggestedDomains.join(' · ')}
        </div>
      )}
    </div>
  );
}

/**
 * SourceCompass -- Main exported component.
 *
 * Props:
 *   sourceCompass: The source_compass object from episode endpoint response.
 *     { current_wind, historical, investigation_hint, disclaimer }
 *   compact: boolean — if true, render in compact mode (for sidebar).
 */
export default function SourceCompass({ sourceCompass, compact = false }) {
  if (!sourceCompass) {
    return (
      <div style={compact ? styles.compactEmpty : styles.empty}>
        <span style={styles.emptyIcon}>🧭</span>
        <span style={styles.emptyText}>Source Compass data not available</span>
      </div>
    );
  }

  const { current_wind, historical, investigation_hint, disclaimer } = sourceCompass;

  const associationMeta = SOURCE_COMPASS_ASSOCIATIONS[historical.association_label]
    || SOURCE_COMPASS_ASSOCIATIONS.INSUFFICIENT;

  return (
    <div style={compact ? styles.compactContainer : styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerIcon}>🧭</span>
        <span style={styles.headerTitle}>Source Compass</span>
        <span style={{
          ...styles.associationBadge,
          background: associationMeta.bg || '#f1f5f9',
          color: associationMeta.color,
          border: `1px solid ${associationMeta.color}30`,
        }}>
          {associationMeta.label}
        </span>
      </div>

      {/* Compass Rose + Current Wind */}
      <div style={compact ? styles.compactContent : styles.content}>
        {!compact && (
          <CompassRose
            profile={historical.profile}
            strongestSector={historical.strongest_sector}
            associationLabel={historical.association_label}
          />
        )}

        <div style={compact ? {} : styles.detailsColumn}>
          <CurrentWind wind={current_wind} />

          {/* Strongest sector */}
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Strongest sector</span>
            <span style={{ ...styles.statValue, color: associationMeta.color }}>
              {historical.strongest_sector}
              {historical.strongest_enrichment >= 1.0 && (
                <span style={styles.statSub}>
                  {historical.strongest_enrichment.toFixed(2)}x enrichment
                </span>
              )}
            </span>
          </div>

          {/* Evidence */}
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Evidence</span>
            <span style={styles.statValue}>
              {historical.evidence_count} episode-hours
              <span style={styles.statSub}>
                out of {historical.total_episode_hours} total
              </span>
            </span>
          </div>

          {/* Season */}
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Analysis season</span>
            <span style={styles.statValue}>
              {historical.season === 'winter' ? '❄ Winter (Oct–Mar)' : '☀ Non-winter'}
              <span style={styles.statSub}>
                {historical.season_month_count} months
              </span>
            </span>
          </div>

          {/* Investigation hint */}
          <InvestigationHint hint={investigation_hint} />
        </div>
      </div>

      {/* Disclaimer */}
      <div style={styles.disclaimer}>
        <AlertTriangle size={14} style={{ color: '#d97706', flexShrink: 0 }} aria-hidden="true" />
        {disclaimer || SOURCE_COMPASS_DISCLAIMER}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────

const styles = {
  container: {
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '16px',
  },
  compactContainer: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '12px',
  },
  empty: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '24px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
  },
  compactEmpty: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '12px',
    textAlign: 'center',
    fontSize: '13px',
    color: '#94a3b8',
  },
  emptyIcon: { fontSize: '24px' },
  emptyText: { fontSize: '14px', color: '#94a3b8' },

  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '12px',
  },
  headerIcon: { fontSize: '18px' },
  headerTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#0f172a',
    flex: 1,
  },
  associationBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: '6px',
    whiteSpace: 'nowrap',
  },

  content: {
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-start',
  },
  compactContent: {},

  detailsColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },

  windRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px',
    background: '#f8fafc',
    borderRadius: '8px',
  },
  windLabel: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#334155',
  },
  windSpeed: {
    fontSize: '12px',
    color: '#64748b',
  },

  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    padding: '4px 0',
  },
  statLabel: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  statValue: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#334155',
    display: 'flex',
    alignItems: 'baseline',
    gap: '4px',
  },
  statSub: {
    fontSize: '11px',
    fontWeight: 400,
    color: '#94a3b8',
  },

  hintBox: {
    background: '#eff6ff',
    border: '1px solid #bfdbfe',
    borderRadius: '8px',
    padding: '10px',
    marginTop: '4px',
  },
  hintTitle: {
    fontSize: '12px',
    fontWeight: 700,
    color: '#1e40af',
    marginBottom: '4px',
  },
  hintDescription: {
    fontSize: '12px',
    color: '#334155',
    lineHeight: '1.4',
  },
  hintSectors: {
    display: 'flex',
    gap: '4px',
    marginTop: '6px',
    flexWrap: 'wrap',
  },
  sectorBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 6px',
    borderRadius: '4px',
    background: '#dbeafe',
    color: '#1e40af',
  },
  hintDomains: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '4px',
    fontStyle: 'italic',
  },

  disclaimer: {
    marginTop: '10px',
    padding: '8px 10px',
    background: '#fefce8',
    border: '1px solid #fde68a',
    borderRadius: '6px',
    fontSize: '11px',
    color: '#92400e',
    lineHeight: '1.4',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '6px',
  },
  disclaimerIcon: { flexShrink: 0 },
  mutedBox: {
    padding: '8px',
    background: '#f8fafc',
    borderRadius: '8px',
    textAlign: 'center',
  },
  mutedText: {
    fontSize: '12px',
    color: '#94a3b8',
  },
};
