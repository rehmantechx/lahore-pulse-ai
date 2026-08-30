/**
 * HealthGuidance — Targeted health recommendations based on PM2.5 severity.
 *
 * Displays audience-specific guidance cards:
 *   - Everyone (general precautions)
 *   - Children & Elderly
 *   - People with Asthma/Heart Conditions
 *   - Outdoor Workers
 *   - Schools & Activities
 *
 * Each card adapts its message based on the current severity level.
 * Does NOT make medical claims — references health authorities.
 *
 * Based on PM25_LEVELS guidance field from constants/index.js.
 */

import { PM25_LEVELS } from '../../constants';

/* ── Audience Guidance Data ──────────────────────────────────── */

const AUDIENCES = [
  {
    id: 'everyone',
    label: 'Everyone',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
    guidance: {
      good: 'Enjoy outdoor activities. Air quality is satisfactory.',
      fair: 'Air quality is acceptable for most people.',
      moderate: 'Consider reducing prolonged outdoor exertion if you feel unusual symptoms.',
      usg: 'Limit prolonged outdoor activity. Take breaks if you must be outside.',
      unhealthy: 'Reduce time outdoors. Move activities indoors when possible.',
      veryUnhealthy: 'Avoid prolonged outdoor activity. Stay in well-ventilated indoor spaces.',
      hazardous: 'Stay indoors with windows closed. Use air purification if available.',
    },
  },
  {
    id: 'sensitive',
    label: 'Children & Elderly',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
    guidance: {
      good: 'No special precautions needed.',
      fair: 'No special precautions needed.',
      moderate: 'Children and elderly should reduce prolonged outdoor play and walks.',
      usg: 'Keep children indoors for outdoor play. Elderly should avoid outdoor walks.',
      unhealthy: 'Children should not play outdoors. Elderly should stay indoors.',
      veryUnhealthy: 'All children and elderly must stay indoors.',
      hazardous: 'Strict indoor shelter for children and elderly. Keep windows closed.',
    },
  },
  {
    id: 'respiratory',
    label: 'Asthma & Heart Conditions',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    ),
    guidance: {
      good: 'No special precautions. Continue normal medication routines.',
      fair: 'No special precautions needed.',
      moderate: 'Keep rescue medication handy. Reduce outdoor exertion.',
      usg: 'Stay indoors. Ensure medication is accessible. Monitor symptoms.',
      unhealthy: 'Remain indoors. Use prescribed medication as directed. Seek medical advice if symptoms worsen.',
      veryUnhealthy: 'Stay indoors with medication. Contact your doctor if you experience difficulty breathing.',
      hazardous: 'Stay indoors. Follow your emergency action plan. Seek medical help for severe symptoms.',
    },
  },
  {
    id: 'outdoor',
    label: 'Outdoor Workers',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    ),
    guidance: {
      good: 'Normal working conditions. No restrictions.',
      fair: 'Normal working conditions. Stay hydrated.',
      moderate: 'Take regular breaks in clean air. Stay hydrated.',
      usg: 'Schedule heavy outdoor work during lower-pollution hours. Take frequent breaks.',
      unhealthy: 'Minimize strenuous outdoor work. Wear a mask if available. Take breaks indoors.',
      veryUnhealthy: 'Postpone non-essential outdoor work. If essential, use N95 masks and frequent indoor breaks.',
      hazardous: 'Postpone all non-essential outdoor work. Essential workers must use proper respiratory protection.',
    },
  },
  {
    id: 'schools',
    label: 'Schools & Activities',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    ),
    guidance: {
      good: 'Outdoor activities and recess can proceed as normal.',
      fair: 'Outdoor activities can proceed normally.',
      moderate: 'Consider moving PE and recess indoors for sensitive students.',
      usg: 'Move all outdoor activities indoors. Cancel outdoor sports events.',
      unhealthy: 'All outdoor activities cancelled. Indoor alternatives only.',
      veryUnhealthy: 'All outdoor activities cancelled. Consider early dismissal if ventilation is poor.',
      hazardous: 'Indoor activities only. Consider closing school if indoor air quality is compromised.',
    },
  },
];

/* ── Severity Key Mapping ────────────────────────────────────── */

function getSeverityKey(pm25) {
  if (pm25 == null || isNaN(pm25)) return 'good';
  if (pm25 <= 12) return 'good';
  if (pm25 <= 25) return 'fair';
  if (pm25 <= 45) return 'moderate';
  if (pm25 <= 65) return 'usg';
  if (pm25 <= 90) return 'unhealthy';
  if (pm25 <= 150) return 'veryUnhealthy';
  return 'hazardous';
}

function getLevel(pm25) {
  if (pm25 == null || isNaN(pm25)) return PM25_LEVELS[0];
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level;
  }
  return PM25_LEVELS[PM25_LEVELS.length - 1];
}

/* ── Component ───────────────────────────────────────────────── */

export default function HealthGuidance({ pm25 }) {
  const level = getLevel(pm25);
  const severityKey = getSeverityKey(pm25);

  return (
    <section className="gov-section" aria-label="Health guidance by audience">
      <div className="gov-section__header">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
        <h2 className="gov-section__title">Health Guidance</h2>
        <span
          style={{
            fontSize: 'var(--text-xs)',
            color: level.color,
            fontWeight: 600,
            padding: '2px 8px',
            background: level.bg,
            borderRadius: 'var(--lp-radius-sm)',
          }}
        >
          {level.label}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--sp-3)',
        }}
      >
        {AUDIENCES.map((audience) => (
          <div
            key={audience.id}
            style={{
              padding: 'var(--sp-4)',
              background: 'var(--lp-bg-primary)',
              border: '1px solid var(--lp-border-subtle)',
              borderRadius: 'var(--lp-radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--sp-2)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--sp-2)',
                color: 'var(--lp-text-secondary)',
              }}
            >
              {audience.icon}
              <span
                style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 600,
                  color: 'var(--lp-text-primary)',
                }}
              >
                {audience.label}
              </span>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: 'var(--text-sm)',
                color: 'var(--lp-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              {audience.guidance[severityKey]}
            </p>
          </div>
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
        This is general guidance based on air quality levels. For medical advice, consult a healthcare professional or refer to{' '}
        <a
          href="https://www.who.int/health-topics/air-pollution"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--lp-brand-600)' }}
        >
          WHO air quality guidelines
        </a>.
      </p>
    </section>
  );
}
