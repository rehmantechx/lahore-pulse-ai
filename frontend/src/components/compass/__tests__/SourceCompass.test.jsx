/**
 * SourceCompass Component Tests.
 *
 * Tests: empty state, full rendering, compact mode,
 * compass rose, current wind, investigation hint,
 * disclaimer, association badges.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SourceCompass from '../SourceCompass';

// ── Mock Data ────────────────────────────────────────────────

const MOCK_COMPASS_DATA = {
  current_wind: {
    direction_degrees: 90.0,
    sector: 'E',
    wind_speed_ms: 3.5,
    is_calm: false,
  },
  historical: {
    profile: [
      { sector: 'N', enrichment: 0.85, episode_hours: 10, total_hours: 100, avg_pm25: 85.0 },
      { sector: 'NE', enrichment: 0.92, episode_hours: 12, total_hours: 90, avg_pm25: 92.0 },
      { sector: 'E', enrichment: 1.44, episode_hours: 40, total_hours: 80, avg_pm25: 135.0 },
      { sector: 'SE', enrichment: 1.12, episode_hours: 18, total_hours: 70, avg_pm25: 112.0 },
      { sector: 'S', enrichment: 0.78, episode_hours: 8, total_hours: 95, avg_pm25: 78.0 },
      { sector: 'SW', enrichment: 0.95, episode_hours: 10, total_hours: 85, avg_pm25: 95.0 },
      { sector: 'W', enrichment: 0.88, episode_hours: 9, total_hours: 90, avg_pm25: 88.0 },
      { sector: 'NW', enrichment: 1.05, episode_hours: 13, total_hours: 90, avg_pm25: 105.0 },
    ],
    strongest_sector: 'E',
    strongest_enrichment: 1.44,
    association_label: 'HIGH',
    evidence_count: 40,
    total_episode_hours: 120,
    total_observations: 5000,
    season: 'winter',
    season_month_count: 6,
  },
  investigation_hint: {
    corridor_sectors: ['E', 'NE', 'SE'],
    description: 'Wind arriving from the East sector shows high association with episodes',
    strongest_enrichment: 1.44,
    association: 'HIGH',
    suggested_response_domains: ['industrial', 'open-burning'],
  },
  disclaimer: 'Directional evidence does not confirm a pollution source.',
};

const MOCK_LOW_ASSOCIATION = {
  ...MOCK_COMPASS_DATA,
  historical: {
    ...MOCK_COMPASS_DATA.historical,
    strongest_sector: 'N',
    strongest_enrichment: 1.02,
    association_label: 'LOW',
    evidence_count: 15,
  },
  investigation_hint: null,
};

const MOCK_INSUFFICIENT = {
  ...MOCK_COMPASS_DATA,
  historical: {
    ...MOCK_COMPASS_DATA.historical,
    strongest_sector: 'N',
    strongest_enrichment: 0.0,
    association_label: 'INSUFFICIENT',
    evidence_count: 0,
  },
  investigation_hint: null,
};

const MOCK_CALM_WIND = {
  ...MOCK_COMPASS_DATA,
  current_wind: {
    direction_degrees: 45.0,
    sector: 'NE',
    wind_speed_ms: 0.8,
    is_calm: true,
  },
};

const MOCK_UNAVAILABLE_WIND = {
  ...MOCK_COMPASS_DATA,
  current_wind: {
    direction_degrees: null,
    sector: null,
    wind_speed_ms: null,
    is_calm: true,
  },
};

// ── Empty State ──────────────────────────────────────────────

describe('SourceCompass', () => {
  it('shows empty state when sourceCompass is null', () => {
    render(<SourceCompass sourceCompass={null} />);
    expect(screen.getByText('Source Compass data not available')).toBeInTheDocument();
  });

  it('renders the compass header with title', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText('Source Compass')).toBeInTheDocument();
  });

  it('renders the strongest sector label', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    const eElements = screen.getAllByText('E');
    expect(eElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders the enrichment value', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText(/1\.44x enrichment/)).toBeInTheDocument();
  });

  it('renders evidence count', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText(/40 episode-hours/)).toBeInTheDocument();
  });

  it('renders season as winter', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText(/Winter/)).toBeInTheDocument();
  });

  it('renders the disclaimer', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText(/Directional evidence does not confirm a pollution source/)).toBeInTheDocument();
  });

  // ── Association Badge ──────────────────────────────────────

  it('renders HIGH association badge for high enrichment', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText('Strong directional signal')).toBeInTheDocument();
  });

  it('renders LOW association badge for low enrichment', () => {
    render(<SourceCompass sourceCompass={MOCK_LOW_ASSOCIATION} />);
    expect(screen.getByText('Weak directional signal')).toBeInTheDocument();
  });

  it('renders INSUFFICIENT badge when data is insufficient', () => {
    render(<SourceCompass sourceCompass={MOCK_INSUFFICIENT} />);
    expect(screen.getByText('Insufficient data')).toBeInTheDocument();
  });

  // ── Current Wind ───────────────────────────────────────────

  it('renders wind direction when available', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    // 'East' appears in wind label
    const eastElements = screen.getAllByText(/East/);
    expect(eastElements.length).toBeGreaterThanOrEqual(1);
    // JS renders 90.0 as '90' in template literals, not '90.0'
    expect(screen.getByText(/90.*°/)).toBeInTheDocument();
  });

  it('renders wind speed when not calm', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText('3.5 m/s')).toBeInTheDocument();
  });

  it('renders calm wind message when is_calm is true', () => {
    // Calm wind needs a valid direction — null direction shows 'unavailable' instead
    render(<SourceCompass sourceCompass={MOCK_CALM_WIND} />);
    expect(screen.getByText(/Calm/)).toBeInTheDocument();
  });

  it('renders unavailable message when direction is null', () => {
    render(<SourceCompass sourceCompass={MOCK_UNAVAILABLE_WIND} />);
    expect(screen.getByText(/unavailable/)).toBeInTheDocument();
  });

  // ── Investigation Hint ─────────────────────────────────────

  it('renders investigation hint when present', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    expect(screen.getByText(/Investigation Corridor/)).toBeInTheDocument();
    expect(screen.getByText(/East sector shows/)).toBeInTheDocument();
  });

  it('renders corridor sector badges', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    // NE and SE appear in both SVG compass rose and investigation hint badges
    const neElements = screen.getAllByText('NE');
    expect(neElements.length).toBeGreaterThanOrEqual(2);
    const seElements = screen.getAllByText('SE');
    expect(seElements.length).toBeGreaterThanOrEqual(2);
  });

  it('renders suggested domains in hint', () => {
    render(<SourceCompass sourceCompass={MOCK_COMPASS_DATA} />);
    const industrialElements = screen.getAllByText(/industrial/);
    expect(industrialElements.length).toBeGreaterThanOrEqual(1);
  });

  it('does not render investigation hint when null', () => {
    render(<SourceCompass sourceCompass={MOCK_LOW_ASSOCIATION} />);
    expect(screen.queryByText(/Investigation Corridor/)).not.toBeInTheDocument();
  });

  // ── Compact Mode ───────────────────────────────────────────

  it('renders in compact mode without compass rose', () => {
    const { container } = render(
      <SourceCompass sourceCompass={MOCK_COMPASS_DATA} compact={true} />
    );
    // Compact mode should not have the SVG compass rose (which has role="img")
    expect(container.querySelector('svg[role="img"]')).not.toBeInTheDocument();
    // But should still show the header
    expect(screen.getByText('Source Compass')).toBeInTheDocument();
  });

  it('renders full mode with compass rose SVG', () => {
    const { container } = render(
      <SourceCompass sourceCompass={MOCK_COMPASS_DATA} compact={false} />
    );
    // Full mode should have SVG compass rose
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('shows compact empty state when null', () => {
    render(<SourceCompass sourceCompass={null} compact={true} />);
    expect(screen.getByText('Source Compass data not available')).toBeInTheDocument();
  });

  // ── Accessibility ──────────────────────────────────────────

  it('compass rose has aria-label', () => {
    const { container } = render(
      <SourceCompass sourceCompass={MOCK_COMPASS_DATA} compact={false} />
    );
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('aria-label');
    expect(svg.getAttribute('aria-label')).toContain('Strongest sector: E');
  });
});
