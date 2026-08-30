/**
 * EpisodeStateHero — The "money screen" component.
 *
 * Makes the unique product concept obvious within 5 seconds.
 * Shows episode state, PM2.5, severity, narrative, and trust signals.
 *
 * Adapts to 4 states: NORMAL, EPISODE, IMPROVING, UNCERTAIN.
 * Does NOT show algorithm names next to PM2.5.
 * Does NOT create numeric confidence scores.
 */

import { useState, useEffect, useRef } from 'react';
import { useEpisodeIntelligence } from '../../hooks/useEpisodeIntelligence';
import { useForecast } from '../../hooks/useForecast';
import { useDemoData } from '../../demo';

const STATE_CONFIG = {
  normal: {
    label: 'No Episode',
    color: '#16a34a',
    bg: '#f0fdf4',
    border: '#bbf7d0',
    dot: '#16a34a',
    heroClass: 'incident-hero--normal',
    narrative: 'No active pollution episode detected.',
  },
  episode: {
    label: 'Episode Active',
    color: '#dc2626',
    bg: '#fef2f2',
    border: '#fecaca',
    dot: '#dc2626',
    heroClass: 'incident-hero--episode',
    narrative: 'An active pollution episode is underway.',
  },
  improving: {
    label: 'Improving',
    color: '#a16207',
    bg: '#fefce8',
    border: '#fde68a',
    dot: '#a16207',
    heroClass: 'incident-hero--improving',
    narrative: 'The current episode is showing signs of improvement.',
  },
  uncertain: {
    label: 'Uncertain',
    color: '#64748b',
    bg: '#f8fafc',
    border: '#e2e8f0',
    dot: '#94a3b8',
    heroClass: 'incident-hero--uncertain',
    narrative: 'Episode status cannot be determined reliably because current data is insufficient.',
  },
};



export default function EpisodeStateHero() {
  const demoData = useDemoData();
  const liveEpisode = useEpisodeIntelligence();
  const liveForecast = useForecast();

  const episode = demoData?.episode ?? liveEpisode.episode;
  const loading = demoData ? false : liveEpisode.loading;
  const forecasts = demoData?.forecasts ?? liveForecast.forecasts;

  const currentForecast = forecasts?.['1'];
  // Use observed PM2.5 from episode endpoint (actual current reading).
  // Only fall back to forecast prediction if episode data unavailable.
  const currentPM25 = episode?.current_pm25 ?? currentForecast?.predicted_pm25 ?? null;

  const state = episode?.state || 'uncertain';
  const config = STATE_CONFIG[state] || STATE_CONFIG.uncertain;

  // Get narrative from backend, fallback to default.
  // Truncate to first sentence — full narrative in supporting evidence.
  const rawNarrative = episode?.narrative || config.narrative;
  const narrative = rawNarrative.split(/(?<=[.!])\s+/)[0];

  /* ── PM2.5 value flash animation ──────────────────── */
  const [flashValue, setFlashValue] = useState(false);
  const prevPM25Ref = useRef(currentPM25);

  useEffect(() => {
    if (currentPM25 !== null && prevPM25Ref.current !== null && currentPM25 !== prevPM25Ref.current) {
      setFlashValue(true);
      const timer = setTimeout(() => setFlashValue(false), 600);
      prevPM25Ref.current = currentPM25;
      return () => clearTimeout(timer);
    }
    prevPM25Ref.current = currentPM25;
  }, [currentPM25]);

  if (loading && !episode) {
    return (
      <div className="incident-hero">
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)' }}>
          Loading incident status...
        </div>
      </div>
    );
  }

  return (
    <div className={`incident-hero ${config.heroClass}`}>
      {/* Single-column compact layout */}
      <div className="incident-hero__compact">
        {/* State badge + PM2.5 inline */}
        <div className="incident-hero__top">
          <span
            className="incident-hero__state"
            style={{ color: config.color, background: config.bg, border: `1px solid ${config.border}` }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: config.color, flexShrink: 0 }} />
            {config.label}
          </span>

          {currentPM25 !== null && (
            <span className="incident-hero__reading">
              <span className={`incident-hero__value ${flashValue ? 'lp-motion-value-flash' : ''}`}>{currentPM25.toFixed(0)}</span>
              <span className="incident-hero__unit">reading</span>
            </span>
          )}
        </div>

        {/* Narrative — short, one line */}
        <p className="incident-hero__narrative">
          {narrative}
        </p>

        {/* Trajectory from episode */}
        {episode?.trajectory_description && (
          <div className="evidence-link">
            <span className="evidence-link__arrow">→</span>
            <span>{episode.trajectory_description}</span>
          </div>
        )}
      </div>
    </div>
  );
}
