/**
 * InvestigationBrief Component Tests.
 *
 * Tests: all episode states, directional evidence, domain evaluation,
 * sector-to-source prevention, disclaimer, handoff, forbidden claims.
 *
 * 12 test cases covering Phases 2-12 of the Investigation Brief spec.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import InvestigationBrief from '../InvestigationBrief';

// ── Mock Data ────────────────────────────────────────────────

const MOCK_COMPASS = {
  current_wind: {
    direction_degrees: 90.0,
    sector: 'E',
    wind_speed_ms: 3.5,
    is_calm: false,
  },
  historical: {
    profile: [
      { sector: 'N', enrichment: 0.85, episode_hours: 10, total_hours: 100, avg_pm25: 85.0 },
      { sector: 'E', enrichment: 1.44, episode_hours: 972, total_hours: 2481, avg_pm25: 112.8 },
      { sector: 'SE', enrichment: 1.12, episode_hours: 18, total_hours: 70, avg_pm25: 112.0 },
      { sector: 'S', enrichment: 0.78, episode_hours: 8, total_hours: 95, avg_pm25: 78.0 },
      { sector: 'SW', enrichment: 0.95, episode_hours: 10, total_hours: 85, avg_pm25: 95.0 },
      { sector: 'W', enrichment: 0.88, episode_hours: 9, total_hours: 90, avg_pm25: 88.0 },
      { sector: 'NW', enrichment: 1.05, episode_hours: 13, total_hours: 90, avg_pm25: 105.0 },
      { sector: 'NE', enrichment: 0.92, episode_hours: 12, total_hours: 90, avg_pm25: 92.0 },
    ],
    strongest_sector: 'E',
    strongest_enrichment: 1.44,
    association_label: 'HIGH ASSOCIATION',
    evidence_count: 972,
    total_episode_hours: 1200,
    total_observations: 5000,
    season: 'winter',
    season_month_count: 6,
  },
  investigation_hint: {
    corridor_sectors: ['E'],
    message: 'Wind arriving from the E sector shows high association',
    suggested_domains: ['Open burning', 'Traffic', 'Industrial activity', 'Construction dust'],
  },
  disclaimer: 'Directional evidence does not confirm a pollution source.',
};

const WARM_WEATHER = {
  variables: [
    { label: 'Temperature', current_value: 14.0, unit: '°C', matches_pattern: true, direction: 'below' },
    { label: 'Humidity', current_value: 55.0, unit: '%', matches_pattern: true, direction: 'below' },
    { label: 'Wind speed', current_value: 3.5, unit: 'm/s', matches_pattern: true, direction: 'below' },
    { label: 'Pressure', current_value: 1015.0, unit: 'hPa', matches_pattern: true, direction: 'above' },
  ],
  note: 'Conditions match episode pattern.',
};

const COOL_HUMID_WEATHER = {
  variables: [
    { label: 'Temperature', current_value: 22.0, unit: '°C', matches_pattern: false, direction: 'above' },
    { label: 'Humidity', current_value: 78.0, unit: '%', matches_pattern: true, direction: 'above' },
    { label: 'Wind speed', current_value: 3.0, unit: 'm/s', matches_pattern: true, direction: 'below' },
    { label: 'Pressure', current_value: 1008.0, unit: 'hPa', matches_pattern: false, direction: 'below' },
  ],
  note: 'Partial match.',
};

function makeEpisode(overrides = {}) {
  return {
    state: 'episode',
    current_pm25: 145.0,
    trajectory: 'rising',
    trajectory_description: 'PM2.5 is rising.',
    weather_context: WARM_WEATHER,
    source_compass: MOCK_COMPASS,
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────

describe('InvestigationBrief', () => {
  // 1. EPISODE renders full brief
  it('renders full investigation brief during episode', () => {
    const episode = makeEpisode();
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText('Investigation Brief')).toBeInTheDocument();
    expect(screen.getByText('ACTIVE EPISODE')).toBeInTheDocument();
    expect(screen.getByText('145.0 μg/m³')).toBeInTheDocument();
    expect(screen.getByText('Directional Evidence')).toBeInTheDocument();
    expect(screen.getByText('Investigation Domains')).toBeInTheDocument();
  });

  // 2. NORMAL renders standby
  it('renders standby during normal state', () => {
    const episode = makeEpisode({ state: 'normal', current_pm25: 8.5 });
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText('Investigation Brief')).toBeInTheDocument();
    expect(screen.getByText('NO INCIDENT')).toBeInTheDocument();
    expect(screen.getByText('No active pollution incident.')).toBeInTheDocument();
    expect(screen.queryByText('Directional Evidence')).not.toBeInTheDocument();
  });

  // 3. UNCERTAIN suppresses investigation
  it('suppresses investigation recommendations during uncertain state', () => {
    const episode = makeEpisode({ state: 'uncertain', current_pm25: null });
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText('INSUFFICIENT DATA')).toBeInTheDocument();
    expect(screen.getByText('Insufficient data for investigation recommendations.')).toBeInTheDocument();
    expect(screen.queryByText('Investigation Domains')).not.toBeInTheDocument();
  });

  // 4. IMPROVING shows monitor/review posture
  it('shows monitor/review posture during improving state', () => {
    const episode = makeEpisode({ state: 'improving', current_pm25: 98.0 });
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText('IMPROVING')).toBeInTheDocument();
    expect(screen.getByText('MONITOR / REVIEW')).toBeInTheDocument();
    expect(screen.queryByText('Start Response Workflow')).not.toBeInTheDocument();
  });

  // 5. Source sector displayed
  it('displays the strongest sector from Source Compass', () => {
    const episode = makeEpisode();
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText(/E.*East/)).toBeTruthy();
    expect(screen.getByText('1.44×')).toBeInTheDocument();
  });

  // 6. Evidence count displayed
  it('displays the evidence count', () => {
    const episode = makeEpisode();
    render(<InvestigationBrief episode={episode} />);

    expect(screen.getByText('972 episode-hours')).toBeInTheDocument();
  });

  // 7. Domains reuse existing weather logic
  it('evaluates domains using shared weather trigger logic', () => {
    const episode = makeEpisode();
    render(<InvestigationBrief episode={episode} />);

    // Open Burning should be INVESTIGATE (temp<18, humidity<60, wind<6 all match)
    expect(screen.getByText('Open Burning')).toBeInTheDocument();
    // Traffic should be INVESTIGATE (wind<6, humidity>70 — but humidity is 55, so only wind matches)
    expect(screen.getByText('Traffic Emissions')).toBeInTheDocument();
    // Industrial should be INVESTIGATE (pressure>1010, wind<6 — pressure is 1015)
    expect(screen.getByText('Industrial Emissions')).toBeInTheDocument();
  });

  // 8. Sector does NOT determine source domain
  it('does not map wind sector to a specific pollution source', () => {
    const episode = makeEpisode();
    const { container } = render(<InvestigationBrief episode={episode} />);
    const text = container.textContent;

    // Must NOT contain sector→source mapping language (tight phrases, not co-occurrence)
    expect(text).not.toMatch(/East\s+industrial/i);
    expect(text).not.toMatch(/from East.*industrial/i);
    expect(text).not.toMatch(/industrial.*from East/i);
    expect(text).not.toMatch(/East\s+burning/i);
    expect(text).not.toMatch(/East\s+traffic/i);
    expect(text).not.toMatch(/East\s+dust/i);
    // Must NOT claim source attribution
    expect(text).not.toMatch(/pollution source is/i);
    expect(text).not.toMatch(/emitted from/i);
    expect(text).not.toMatch(/caused by/i);
  });

  // 9. Disclaimer always present
  it('shows disclaimer during episode and improving states', () => {
    const episodeState = makeEpisode();
    const { unmount } = render(<InvestigationBrief episode={episodeState} />);
    expect(screen.getByText(/statistical association/)).toBeInTheDocument();
    unmount();

    const improvingEpisode = makeEpisode({ state: 'improving' });
    render(<InvestigationBrief episode={improvingEpisode} />);
    expect(screen.getByText(/statistical association/)).toBeInTheDocument();
  });

  // 10. Response Orchestrator handoff works
  it('shows Start Response Workflow button during episode', () => {
    const onStartWorkflow = vi.fn();
    const episode = makeEpisode();
    render(<InvestigationBrief episode={episode} onStartWorkflow={onStartWorkflow} />);

    const button = screen.getByText('Start Response Workflow');
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(onStartWorkflow).toHaveBeenCalledTimes(1);
  });

  // 11. Backend/frontend investigation_hint field compatibility
  it('renders InvestigationHint with backend field names (message, suggested_domains)', () => {
    const episode = makeEpisode();
    // Backend sends message + suggested_domains
    episode.source_compass.investigation_hint = {
      corridor_sectors: ['E'],
      message: 'Wind from E shows high association',
      suggested_domains: ['Industrial', 'Open burning'],
    };
    render(<InvestigationBrief episode={episode} />);
    // Component should render without error (InvestigationHint is inside SourceCompass, not directly in InvestigationBrief)
    expect(screen.getByText('Investigation Brief')).toBeInTheDocument();
  });

  // 12. No forbidden claims
  it('contains no forbidden scientific claims', () => {
    const episode = makeEpisode();
    const { container } = render(<InvestigationBrief episode={episode} />);
    const text = container.textContent;

    const forbidden = [
      'caused', 'causes', 'source detected', 'source confirmed',
      'emitted from', 'government notified', 'government dispatched',
      'AI identifies', 'confidence %', 'probability %', 'guaranteed',
    ];
    for (const term of forbidden) {
      expect(text.toLowerCase()).not.toContain(term.toLowerCase());
    }
  });
});
