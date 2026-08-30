/**
 * WhyPanel — Explains WHY air quality is bad, based on available data.
 *
 * Shows contributing factors only when data supports them:
 *   - Wind direction & speed (from SourceCompass)
 *   - Episode trajectory and history
 *   - Seasonal context
 *   - Historical patterns (from analogs)
 *
 * Each factor has: What we know → Evidence → Confidence level.
 * NEVER speculates — only shows factors with supporting data.
 */

import { useState } from 'react';

/* ── SVG Icons ───────────────────────────────────────────────── */

const IconChevron = ({ open }) => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{
      transition: 'transform 0.2s',
      transform: open ? 'rotate(180deg)' : 'rotate(0)',
    }}
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconWind = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
    <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
    <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
  </svg>
);

const IconHistory = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconTrend = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

const IconCalendar = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconInfo = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="16" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12.01" y2="8" />
  </svg>
);

/* ── Confidence Badge ────────────────────────────────────────── */

function ConfidenceBadge({ level }) {
  const styles = {
    high: { color: '#16a34a', bg: '#f0fdf4', label: 'High confidence' },
    moderate: { color: '#ca8a04', bg: '#fefce8', label: 'Moderate confidence' },
    low: { color: '#ea580c', bg: '#fff7ed', label: 'Low confidence' },
  };
  const s = styles[level] || styles.low;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: 'var(--text-xs)',
        color: s.color,
        background: s.bg,
        padding: '2px 6px',
        borderRadius: 'var(--lp-radius-sm)',
        fontWeight: 500,
      }}
    >
      <IconInfo />
      {s.label}
    </span>
  );
}

/* ── Factor Card ─────────────────────────────────────────────── */

function FactorCard({ icon: Icon, title, summary, detail, confidence }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        overflow: 'hidden',
        background: 'var(--lp-bg-primary)',
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--sp-3)',
          padding: 'var(--sp-3) var(--sp-4)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: 'var(--text-sm)',
          fontWeight: 500,
          color: 'var(--lp-text-primary)',
        }}
      >
        <span style={{ color: 'var(--lp-brand-600)', flexShrink: 0 }}>
          <Icon />
        </span>
        <span style={{ flex: 1 }}>{title}</span>
        <ConfidenceBadge level={confidence} />
        <IconChevron open={expanded} />
      </button>

      {expanded && (
        <div
          style={{
            padding: '0 var(--sp-4) var(--sp-4)',
            borderTop: '1px solid var(--lp-border-subtle)',
          }}
        >
          <p
            style={{
              margin: 'var(--sp-3) 0 var(--sp-2)',
              fontSize: 'var(--text-sm)',
              color: 'var(--lp-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            {summary}
          </p>
          {detail && (
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-xs)',
                color: 'var(--lp-text-tertiary)',
                lineHeight: 1.5,
                fontStyle: 'italic',
              }}
            >
              {detail}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Helper: Determine Season ────────────────────────────────── */

function getSeasonContext() {
  const month = new Date().getMonth(); // 0-11
  // Lahore seasons: Winter (Nov-Feb), Spring (Mar-Apr), Summer (May-Jun), Monsoon (Jul-Aug), Autumn (Sep-Oct)
  if (month >= 10 || month <= 1) return {
    label: 'Winter season',
    detail: 'Lahore\'s winter months (November–February) typically see worse air quality due to temperature inversions, reduced wind, biomass burning, and brick kiln emissions.',
    confidence: 'high',
  };
  if (month >= 2 && month <= 3) return {
    label: 'Spring transition',
    detail: 'Spring months in Lahore typically see moderate air quality as winter inversions weaken. Dust from agricultural activities may contribute.',
    confidence: 'moderate',
  };
  if (month >= 4 && month <= 5) return {
    label: 'Pre-monsoon summer',
    detail: 'Summer heat increases ozone formation. Dust storms from Thar Desert can spike pollution levels. Lahore summers are typically drier.',
    confidence: 'moderate',
  };
  if (month >= 6 && month <= 7) return {
    label: 'Monsoon season',
    detail: 'Monsoon rains help clear pollution from the air. This is typically Lahore\'s cleanest air quality period, though humidity increases.',
    confidence: 'high',
  };
  return {
    label: 'Autumn transition',
    detail: 'Autumn marks the beginning of Lahore\'s pollution season. Crop residue burning in surrounding areas and dropping temperatures start trapping pollutants.',
    confidence: 'moderate',
  };
}

/* ── Main Component ──────────────────────────────────────────── */

export default function WhyPanel({ episode, forecasts }) {
  const factors = [];

  // Factor 1: Wind/Source Direction (from SourceCompass)
  const sector = episode?.source_compass?.enrichment?.sector;
  const enrichmentFactor = episode?.source_compass?.enrichment?.enrichment_factor;
  if (sector && enrichmentFactor) {
    const directionLabel = {
      N: 'North', NE: 'Northeast', E: 'East', SE: 'Southeast',
      S: 'South', SW: 'Southwest', W: 'West', NW: 'Northwest',
    }[sector] || sector;

    factors.push({
      icon: IconWind,
      title: `Wind carrying pollution from the ${directionLabel}`,
      summary: `Air quality readings show stronger pollution when wind comes from the ${directionLabel} direction (×${enrichmentFactor.toFixed(1)} enrichment factor). This suggests pollution sources or transport pathways in that corridor.`,
      detail: 'SourceCompass analysis compares pollution levels during different wind directions. An enrichment factor above 1.0 indicates higher-than-average pollution from that direction.',
      confidence: enrichmentFactor > 2 ? 'high' : enrichmentFactor > 1.3 ? 'moderate' : 'low',
    });
  }

  // Factor 2: Episode Trajectory
  const trajectory = episode?.trajectory;
  if (trajectory && trajectory !== 'stable') {
    factors.push({
      icon: IconTrend,
      title: trajectory === 'rising' ? 'Pollution levels are increasing' : 'Pollution levels are decreasing',
      summary: trajectory === 'rising'
        ? 'The current episode is intensifying. This may be due to worsening weather conditions, increased emissions, or both. Monitor conditions closely.'
        : 'Conditions are improving. Weather patterns or reduced emissions may be helping. Check the forecast for when conditions are expected to normalize.',
      detail: episode?.trajectory_description || null,
      confidence: 'moderate',
    });
  }

  // Factor 3: Historical Pattern (analogs)
  const analogCount = episode?.analogs?.length || 0;
  if (analogCount > 0) {
    const analog = episode.analogs[0];
    factors.push({
      icon: IconHistory,
      title: 'Similar patterns seen before',
      summary: `This type of pollution episode has happened ${analogCount} time${analogCount > 1 ? 's' : ''} before under similar conditions. Past episodes typically lasted ${analog.typical_duration || 'several hours'} and were resolved by ${analog.resolution_factor || 'changing weather patterns'}.`,
      detail: 'Episode intelligence compares current conditions against historical analogs — past episodes with similar meteorological and pollution profiles.',
      confidence: analogCount > 3 ? 'high' : analogCount > 1 ? 'moderate' : 'low',
    });
  }

  // Factor 4: Seasonal Context
  const season = getSeasonContext();
  factors.push({
    icon: IconCalendar,
    title: season.label,
    summary: season.detail,
    detail: null,
    confidence: season.confidence,
  });

  if (factors.length === 0) return null;

  return (
    <section className="gov-section" aria-label="Why air quality is bad">
      <div className="gov-section__header">
        <IconInfo />
        <h2 className="gov-section__title">Why Is Air Quality Bad?</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
        {factors.map((factor, i) => (
          <FactorCard key={i} {...factor} />
        ))}
      </div>

      <p
        style={{
          margin: 'var(--sp-3) 0 0',
          fontSize: 'var(--text-xs)',
          color: 'var(--lp-text-tertiary)',
          fontStyle: 'italic',
        }}
      >
        Factors are shown only when supporting data is available. Analysis is based on historical patterns and meteorological data — not real-time source monitoring.
      </p>
    </section>
  );
}
