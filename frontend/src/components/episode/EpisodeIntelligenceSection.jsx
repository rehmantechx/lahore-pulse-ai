/**
 * EpisodeIntelligenceSection -- Dashboard section wrapper for episode intelligence.
 *
 * Fetches episode intelligence data and renders the three sub-components:
 * EpisodeIntelligence, EpisodeTrajectory, and EpisodeWeatherContext.
 *
 * This is a thin wrapper that handles loading/error states and layout.
 */

import { useEpisodeIntelligence } from '../../hooks/useEpisodeIntelligence';
import EpisodeIntelligence from './EpisodeIntelligence';
import EpisodeTrajectory from './EpisodeTrajectory';
import EpisodeWeatherContext from './EpisodeWeatherContext';

export default function EpisodeIntelligenceSection() {
  const { episode, loading, error } = useEpisodeIntelligence();

  // Don't render anything if there's a permanent error
  if (error && !episode) {
    return (
      <div className="surface" style={{ marginBottom: 'var(--sp-4)' }}>
        <div className="surface__header">
          <span className="surface__title">Episode Intelligence</span>
        </div>
        <div className="surface__body">
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)' }}>
            Episode intelligence is temporarily unavailable.
          </p>
        </div>
      </div>
    );
  }

  // Show loading placeholder only on first load
  if (loading && !episode) {
    return (
      <div className="surface" style={{ marginBottom: 'var(--sp-4)' }}>
        <div className="surface__header">
          <span className="surface__title">Episode Intelligence</span>
        </div>
        <div className="surface__body">
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)' }}>
            Loading episode intelligence...
          </p>
        </div>
      </div>
    );
  }

  if (!episode) return null;

  return (
    <div style={{ marginBottom: 'var(--sp-4)' }}>
      {/* Section header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 'var(--sp-3)',
      }}>
        <div>
          <h2 style={{
            fontSize: 'var(--text-lg)',
            fontWeight: 700,
            color: 'var(--slate-900)',
            marginBottom: '2px',
          }}>
            Episode Intelligence
          </h2>
          <p style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--slate-500)',
          }}>
            Rule-based pollution episode detection using ML forecasts as input.
            Detection is NOT machine learning.
          </p>
        </div>
      </div>

      {/* Main layout: 2-column on desktop, stacked on mobile */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
        gap: 'var(--sp-4)',
      }}>
        {/* Left column: Episode state + trajectory */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <EpisodeIntelligence episode={episode} />
          <EpisodeTrajectory episode={episode} />
        </div>

        {/* Right column: Weather context */}
        <div>
          <EpisodeWeatherContext episode={episode} />
        </div>
      </div>

      {/* Historical context callout */}
      {episode.historical_context && (
        <div style={{
          marginTop: 'var(--sp-4)',
          padding: 'var(--sp-3) var(--sp-4)',
          background: 'var(--slate-50)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--slate-200)',
        }}>
          <div style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            color: 'var(--slate-600)',
            marginBottom: 'var(--sp-2)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            Historical Context
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 'var(--sp-3)',
            fontSize: '13px',
          }}>
            <div>
              <span style={{ color: 'var(--slate-500)' }}>Episodes studied: </span>
              <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                {episode.historical_context.total_episodes}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--slate-500)' }}>Seasonal peak: </span>
              <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                {episode.historical_context.seasonal_frequency}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--slate-500)' }}>Average duration: </span>
              <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                {episode.historical_context.average_duration_hours} hours
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--slate-500)' }}>Peaks within 6h: </span>
              <span style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
                {episode.historical_context.peaks_within_6h_pct}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
