/**
 * PollutionStory — Converts forecast data into a simple chronological narrative.
 *
 * Instead of raw numbers, citizens see a plain-language story:
 * "Right now: Unhealthy → In 3 hours: Still unhealthy but improving → By evening: Should drop to moderate"
 *
 * Visual: Timeline with colored dots, simple text, no technical jargon.
 */

import { ArrowUpRight, ArrowDownRight, Minus, Clock } from 'lucide-react';
import { HORIZONS, HORIZON_META, PM25_LEVELS } from '../../constants';

function getSeverityForPM25(pm25) {
  if (pm25 == null) return { label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' };
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return { label: level.label, color: level.color, bg: level.bg };
  }
  return { label: 'Hazardous', color: '#7f1d1d', bg: '#fef2f2' };
}

function getPlainLanguageVerb(pm25, nextPM25) {
  if (nextPM25 == null || pm25 == null) return null;
  const diff = nextPM25 - pm25;
  if (diff < -8) return 'should improve significantly';
  if (diff < -3) return 'should improve';
  if (diff > 8) return 'is expected to worsen';
  if (diff > 3) return 'may get worse';
  return 'should stay similar';
}

function getTimelineLabel(horizon) {
  if (horizon === 1) return 'Right now';
  const meta = HORIZON_META[horizon];
  if (!meta) return `+${horizon}h`;
  const hours = meta.shortLabel;
  if (hours === '1h') return 'In 1 hour';
  if (hours === '3h') return 'In 3 hours';
  if (hours === '6h') return 'In 6 hours';
  if (hours === '12h') return 'In 12 hours';
  if (hours === '24h') return 'Tomorrow';
  return `In ${hours}`;
}

function getTrendIcon(pm25, nextPM25) {
  if (nextPM25 == null || pm25 == null) return null;
  const diff = nextPM25 - pm25;
  if (diff < -3) return ArrowDownRight;
  if (diff > 3) return ArrowUpRight;
  return Minus;
}

/**
 * @param {object} props
 * @param {object} props.forecasts - Forecast data keyed by horizon number
 */
export default function PollutionStory({ forecasts }) {
  if (!forecasts || Object.keys(forecasts).length === 0) return null;

  const currentPM25 = forecasts['1']?.predicted_pm25;
  const currentSeverity = getSeverityForPM25(currentPM25);

  // Build narrative timeline from available horizons
  const timeline = HORIZONS
    .filter(h => forecasts[String(h)]?.predicted_pm25 != null)
    .map(h => {
      const pm25 = forecasts[String(h)].predicted_pm25;
      const severity = getSeverityForPM25(pm25);
      const nextH = HORIZONS[HORIZONS.indexOf(h) + 1];
      const nextPM25 = nextH ? forecasts[String(nextH)]?.predicted_pm25 : null;
      const verb = getPlainLanguageVerb(pm25, nextPM25);
      const TrendIcon = getTrendIcon(pm25, nextPM25);

      return {
        horizon: h,
        label: getTimelineLabel(h),
        pm25,
        severity,
        verb,
        TrendIcon,
        isNow: h === 1,
      };
    });

  if (timeline.length === 0) return null;

  // Build summary sentence
  const last = timeline[timeline.length - 1];
  const secondLast = timeline.length > 1 ? timeline[timeline.length - 2] : null;
  const overallTrend = secondLast
    ? (last.pm25 < secondLast.pm25 - 3 ? 'improving' : last.pm25 > secondLast.pm25 + 3 ? 'worsening' : 'stable')
    : 'stable';

  let summaryText;
  if (overallTrend === 'improving') {
    summaryText = `Air quality is expected to improve over the coming hours.`;
  } else if (overallTrend === 'worsening') {
    summaryText = `Air quality may worsen over the coming hours. Stay cautious.`;
  } else {
    summaryText = `Air quality is expected to remain similar throughout the coming hours.`;
  }

  return (
    <section className="pollution-story" aria-label="Air quality forecast story">
      <div className="section-header">
        <h2 className="section-header__title">What to Expect</h2>
        <span className="section-header__subtitle">
          <Clock size={12} style={{ verticalAlign: -1, marginRight: 4 }} />
          Plain-language forecast
        </span>
      </div>

      {/* Summary */}
      <div
        className="card"
        style={{
          marginBottom: 'var(--sp-4)',
          padding: 'var(--sp-4)',
          borderLeft: `3px solid ${currentSeverity.color}`,
        }}
      >
        <p className="type-body" style={{ color: 'var(--lp-text-secondary)', margin: 0 }}>
          {summaryText}
        </p>
      </div>

      {/* Timeline */}
      <div className="story-timeline" role="list">
        {timeline.map((item, idx) => (
          <div
            key={item.horizon}
            className={`story-timeline__item ${item.isNow ? 'story-timeline__item--now' : ''}`}
            role="listitem"
          >
            {/* Connector */}
            <div className="story-timeline__connector" aria-hidden="true">
              <div
                className="story-timeline__dot"
                style={{ background: item.severity.color }}
              />
              {idx < timeline.length - 1 && (
                <div className="story-timeline__line" />
              )}
            </div>

            {/* Content */}
            <div className="story-timeline__content">
              <div className="story-timeline__header">
                <span className="story-timeline__label" style={{
                  fontWeight: item.isNow ? 600 : 400,
                }}>
                  {item.label}
                </span>
                <span
                  className="story-timeline__severity"
                  style={{
                    background: item.severity.bg,
                    color: item.severity.color,
                    padding: '1px 8px',
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {item.severity.label}
                </span>
                {item.TrendIcon && (
                  <item.TrendIcon
                    size={14}
                    color={item.severity.color}
                    aria-hidden="true"
                  />
                )}
              </div>

              <div className="story-timeline__detail">
                <span style={{ fontWeight: 600 }}>
                  {item.severity.label}
                </span>
                {item.verb && (
                  <span style={{ color: 'var(--slate-500)', marginLeft: 6 }}>
                    — {item.verb}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
