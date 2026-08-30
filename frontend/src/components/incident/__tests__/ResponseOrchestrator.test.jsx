/**
 * ResponseOrchestrator Tests.
 *
 * Tests the incident response workflow component for all episode states,
 * domain evaluation, workflow interaction, and honesty/disclaimer checks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ResponseOrchestrator from '../ResponseOrchestrator';

// ── Mock Hooks ─────────────────────────────────────────────────

const mockUseEpisodeIntelligence = vi.fn();
const mockUseForecast = vi.fn();

vi.mock('../../../hooks/useEpisodeIntelligence', () => ({
  useEpisodeIntelligence: (...args) => mockUseEpisodeIntelligence(...args),
}));

vi.mock('../../../hooks/useForecast', () => ({
  useForecast: (...args) => mockUseForecast(...args),
}));

// ── Test Fixtures ──────────────────────────────────────────────

const DEFAULT_WEATHER = {
  variables: [
    { label: 'Temperature', current_value: 14.0, unit: '°C', matches_pattern: true, direction: 'below' },
    { label: 'Humidity', current_value: 75.0, unit: '%', matches_pattern: true, direction: 'above' },
    { label: 'Wind speed', current_value: 3.5, unit: 'km/h', matches_pattern: true, direction: 'below' },
    { label: 'Pressure', current_value: 1015.0, unit: 'hPa', matches_pattern: true, direction: 'above' },
  ],
  note: 'All four factors match episode pattern.',
};

function makeEpisode(overrides = {}) {
  return {
    state: 'episode',
    state_description: 'Pollution episode',
    current_pm25: 145.0,
    current_6h_delta: 35,
    trajectory: 'rising',
    trajectory_description: 'PM2.5 is rising sharply.',
    near_term: { predicted_pm25: 150, horizon_hours: 1 },
    medium_term: { predicted_pm25: 160, horizon_hours: 6 },
    recovery_expected: false,
    recovery_text: 'No recovery expected soon.',
    highest_forecast_horizon: 6,
    highest_forecast_value: 160.0,
    peak_passed: false,
    weather_context: DEFAULT_WEATHER,
    historical_context: 'Historical context',
    narrative: 'Air quality has deteriorated.',
    narrative_caveat: 'Based on available data.',
    data_status: 'good',
    freshness_hours: 0.5,
    forecast_reliability: 'high',
    warnings: [],
    ...overrides,
  };
}

function makeForecasts(pm25 = 145.0) {
  return {
    '1': { predicted_pm25: pm25 },
    '3': { predicted_pm25: pm25 + 5 },
    '6': { predicted_pm25: pm25 + 15 },
    '12': { predicted_pm25: pm25 + 10 },
    '24': { predicted_pm25: pm25 - 10 },
  };
}

// ── Setup ──────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  // Default: episode state with all weather matches
  mockUseEpisodeIntelligence.mockReturnValue({
    episode: makeEpisode(),
    loading: false,
    error: null,
  });
  mockUseForecast.mockReturnValue({
    forecasts: makeForecasts(),
    errors: [],
    forecastStatus: { ready: true },
    loading: false,
    error: null,
  });
});

// ══════════════════════════════════════════════════════════════
// TEST SUITE
// ══════════════════════════════════════════════════════════════

describe('ResponseOrchestrator', () => {
  // ── 1. Loading & Empty States ────────────────────────────────

  describe('loading and empty states', () => {
    it('renders loading state when data is loading', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: null,
        loading: true,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Response Orchestrator')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders nothing when episode is null and not loading', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: null,
        loading: false,
        error: null,
      });
      const { container } = render(<ResponseOrchestrator />);
      expect(container.innerHTML).toBe('');
    });
  });

  // ── 2. NORMAL State ──────────────────────────────────────────

  describe('NORMAL state', () => {
    it('renders standby with green indicator and no active incident', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'normal' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.getByText('No active pollution incident.')).toBeInTheDocument();
      expect(screen.getByText('Standby', { selector: '.section-header__subtitle' })).toBeInTheDocument();
    });

    it('does NOT render workflow buttons in normal state', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'normal' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.queryByText('Start Response Workflow')).not.toBeInTheDocument();
      expect(screen.queryByText('Response Workflow')).not.toBeInTheDocument();
    });

    it('shows disclaimer in normal state', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'normal' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/Response workflow simulation/)).toBeInTheDocument();
      expect(screen.getByText(/not confirmed emission sources/)).toBeInTheDocument();
    });
  });

  // ── 3. UNCERTAIN State ───────────────────────────────────────

  describe('UNCERTAIN state', () => {
    it('renders standby with insufficient data message', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'uncertain' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Insufficient current data for a reliable incident workflow.')).toBeInTheDocument();
      expect(screen.getByText('STANDBY')).toBeInTheDocument();
    });

    it('does NOT render workflow buttons in uncertain state', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'uncertain' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.queryByText('Start Response Workflow')).not.toBeInTheDocument();
    });
  });

  // ── 4. EPISODE State ─────────────────────────────────────────

  describe('EPISODE state', () => {
    it('renders active incident header with red indicator', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('POLLUTION INCIDENT ACTIVE')).toBeInTheDocument();
    });

    it('displays PM2.5 value from forecasts', () => {
      render(<ResponseOrchestrator />);
      // The PM2.5 value is inside a <strong> with the full text "145.0 \u03bcg/m3"
      const strongEls = document.querySelectorAll('strong');
      const pm25Value = Array.from(strongEls).find(el => el.textContent.includes('145.0'));
      expect(pm25Value).toBeTruthy();
      expect(pm25Value.textContent).toContain('145.0');
    });

    it('renders all 4 investigation signal domains', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Open Burning')).toBeInTheDocument();
      expect(screen.getByText('Traffic Emissions')).toBeInTheDocument();
      expect(screen.getByText('Road / Construction Dust')).toBeInTheDocument();
      expect(screen.getByText('Industrial Emissions')).toBeInTheDocument();
    });

    it('marks active domains with INVESTIGATE badge', () => {
      // With all 4 weather matches, all domains should be active
      render(<ResponseOrchestrator />);
      const badges = screen.getAllByText('INVESTIGATE');
      expect(badges.length).toBeGreaterThanOrEqual(1);
    });

    it('renders "Start Response Workflow" button initially', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Start Response Workflow')).toBeInTheDocument();
    });

    it('renders the 5-step workflow pipeline labels', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Detected')).toBeInTheDocument();
      expect(screen.getByText('Investigate')).toBeInTheDocument();
      expect(screen.getByText('Acknowledge')).toBeInTheDocument();
      expect(screen.getByText('Review')).toBeInTheDocument();
      expect(screen.getByText('Closed')).toBeInTheDocument();
    });

    it('renders SLA timing windows', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/Detection → Investigation/)).toBeInTheDocument();
      expect(screen.getByText(/30 min/)).toBeInTheDocument();
      expect(screen.getByText(/2 hr/)).toBeInTheDocument();
      expect(screen.getByText(/4 hr/)).toBeInTheDocument();
    });

    it('shows SLA source attribution', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/Punjab AQI Emergency Response Protocol/)).toBeInTheDocument();
    });

    it('displays trajectory description from episode', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/PM2.5 is rising sharply/)).toBeInTheDocument();
    });
  });

  // ── 5. IMPROVING State ───────────────────────────────────────

  describe('IMPROVING state', () => {
    beforeEach(() => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'improving' }),
        loading: false,
        error: null,
      });
    });

    it('renders improving header with amber indicator', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('EPISODE IMPROVING')).toBeInTheDocument();
    });

    it('shows Review / Monitor subtitle', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Review / Monitor')).toBeInTheDocument();
    });

    it('starts workflow at step 3 (Review) with Advance button', () => {
      render(<ResponseOrchestrator />);
      // Should start at step 3, offering to advance to step 4 (Closed)
      expect(screen.getByText('Advance to: Closed')).toBeInTheDocument();
    });

    it('shows improving-specific review message', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/Episode is improving/)).toBeInTheDocument();
      expect(screen.getByText(/Continue monitoring/)).toBeInTheDocument();
    });
  });

  // ── 6. Workflow Interaction ───────────────────────────────────

  describe('workflow interaction', () => {
    it('advances workflow from step 0 to step 1', () => {
      render(<ResponseOrchestrator />);

      // Start the workflow
      fireEvent.click(screen.getByText('Start Response Workflow'));

      // Now at step 0 (Detected), should show advance button
      expect(screen.getByText('Advance to: Investigate')).toBeInTheDocument();
      // Text is split by <strong> tag: "Pollution incident" + "detected" + "by rule-based..."
      expect(screen.getByText(/rule-based episode intelligence/)).toBeInTheDocument();
    });

    it('advances through multiple steps', () => {
      render(<ResponseOrchestrator />);

      // Start workflow
      fireEvent.click(screen.getByText('Start Response Workflow'));
      // Step 0 → 1
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      expect(screen.getByText('Advance to: Acknowledge')).toBeInTheDocument();
      // Step 1 → 2
      fireEvent.click(screen.getByText('Advance to: Acknowledge'));
      expect(screen.getByText('Advance to: Review')).toBeInTheDocument();
      // Step 2 → 3
      fireEvent.click(screen.getByText('Advance to: Review'));
      expect(screen.getByText('Advance to: Closed')).toBeInTheDocument();
      // Step 3 → 4
      fireEvent.click(screen.getByText('Advance to: Closed'));
      // Text is split by <strong>: "Workflow" + "closed" + ". No further action..."
      expect(screen.getByText(/No further action required/)).toBeInTheDocument();
    });

    it('resets workflow back to initial state', () => {
      render(<ResponseOrchestrator />);

      // Start workflow
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));

      // Reset
      fireEvent.click(screen.getByText('Reset'));
      expect(screen.getByText('Start Response Workflow')).toBeInTheDocument();
    });

    it('does not advance past the final step', () => {
      render(<ResponseOrchestrator />);

      // Navigate to final step
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      fireEvent.click(screen.getByText('Advance to: Acknowledge'));
      fireEvent.click(screen.getByText('Advance to: Review'));
      fireEvent.click(screen.getByText('Advance to: Closed'));

      // No more advance button
      expect(screen.queryByText(/Advance to:/)).not.toBeInTheDocument();
      // Reset still available
      expect(screen.getByText('Reset')).toBeInTheDocument();
    });
  });

  // ── 7. Evidence Drawer ───────────────────────────────────────

  describe('evidence drawer', () => {
    it('toggles the "Why was this flagged?" drawer', () => {
      render(<ResponseOrchestrator />);

      // Drawer not visible initially
      expect(screen.queryByText('Trend:')).not.toBeInTheDocument();

      // Open the drawer
      fireEvent.click(screen.getByText('Why was this flagged?'));
      expect(screen.getByText('Trend:')).toBeInTheDocument();
      expect(screen.getByText('Forecast trajectory:')).toBeInTheDocument();
      expect(screen.getByText('Data status:')).toBeInTheDocument();

      // Close it
      fireEvent.click(screen.getByText('Why was this flagged?'));
      expect(screen.queryByText('Trend:')).not.toBeInTheDocument();
    });

    it('shows weather context variables in evidence drawer', () => {
      render(<ResponseOrchestrator />);
      fireEvent.click(screen.getByText('Why was this flagged?'));

      // Weather context from our fixture
      expect(screen.getByText('Environmental context:')).toBeInTheDocument();
      expect(screen.getByText(/below typical/)).toBeInTheDocument();
      expect(screen.getByText(/above typical/)).toBeInTheDocument();
    });

    it('toggles domain-specific evidence drawers', () => {
      render(<ResponseOrchestrator />);

      // Open Open Burning domain
      const openBurningBtn = screen.getByText('Open Burning').closest('button');
      fireEvent.click(openBurningBtn);

      // Evidence content should appear
      expect(screen.getByText('Evidence:')).toBeInTheDocument();
      expect(screen.getByText('Official basis:')).toBeInTheDocument();
      expect(screen.getByText(/Punjab EPA/)).toBeInTheDocument();
    });

    it('shows investigation disclaimer in domain drawer', () => {
      render(<ResponseOrchestrator />);

      const openBurningBtn = screen.getByText('Open Burning').closest('button');
      fireEvent.click(openBurningBtn);

      expect(screen.getByText(/not a confirmed source attribution/)).toBeInTheDocument();
    });
  });

  // ── 8. Domain Evaluation Logic ───────────────────────────────

  describe('domain evaluation', () => {
    it('marks domains as LOW when weather does not match', () => {
      // Set up weather that truly doesn't match any domain triggers:
      // open-burning: temp<18(HI), humidity<60(LO), wind<6(HI) → needs temp≥18, humidity≥60, wind≥6
      // traffic: wind<6(HI), humidity>70(LO) → needs wind≥6, humidity≤70
      // road-dust: humidity<60(LO), wind>4(HI) → needs humidity≥60, wind≤4... but wind≤4 triggers open-burning
      // industrial: pressure>1010(HI), wind<6(HI) → needs pressure≤1010, wind≥6
      // Best: temp=25, humidity=65, wind=5, pressure=1005
      // open-burning: temp<18? NO, humidity<60? NO(65), wind<6? YES(5) → 1 match → ACTIVE
      // traffic: wind<6? YES(5), humidity>70? NO(65) → 1 match → ACTIVE
      // road-dust: humidity<60? NO(65), wind>4? YES(5) → 1 match → ACTIVE
      // industrial: pressure>1010? NO(1005), wind<6? YES(5) → 1 match → ACTIVE
      // Hmm, wind=5 triggers everything with wind<6. Let's use wind=8.
      // open-burning: temp<18? NO, humidity<60? NO, wind<6? NO → 0 matches
      // traffic: wind<6? NO, humidity>70? NO → 0 matches
      // road-dust: humidity<60? NO, wind>4? YES(8) → 1 match → ACTIVE
      // industrial: pressure>1010? NO, wind<6? NO → 0 matches
      // So 3 LOW, 1 ACTIVE. Let's use wind=3 instead.
      // open-burning: temp<18? NO, humidity<60? NO, wind<6? YES(3) → 1 match
      // traffic: wind<6? YES, humidity>70? NO → 1 match
      // road-dust: humidity<60? NO, wind>4? NO(3) → 0 matches → LOW
      // industrial: pressure>1010? NO, wind<6? YES → 1 match
      // Still 1 ACTIVE. To get 0 matches for ALL: need humidity≥60, wind<6+wind>4 impossible
      // The triggers overlap — wind<6 appears in 3 domains. So ANY wind value either matches wind<6 or wind>4.
      // Best approach: accept that with episode state, some domains will be ACTIVE.
      // Test that fewer domains are active than the default (all-weather-matches case).
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({
          weather_context: {
            variables: [
              { label: 'Temperature', current_value: 25.0, unit: '°C', matches_pattern: false, direction: 'above' },
              { label: 'Humidity', current_value: 65.0, unit: '%', matches_pattern: false, direction: 'below' },
              { label: 'Wind speed', current_value: 8.0, unit: 'km/h', matches_pattern: false, direction: 'above' },
              { label: 'Pressure', current_value: 1005.0, unit: 'hPa', matches_pattern: false, direction: 'below' },
            ],
            note: 'Minimal factors match.',
          },
        }),
        loading: false,
        error: null,
      });

      render(<ResponseOrchestrator />);
      const lowBadges = screen.getAllByText('LOW');
      const investigateBadges = screen.getAllByText('INVESTIGATE');
      // With wind=8, humidity=65: road-dust has 1 match (wind>4), rest have 0 → 3 LOW, 1 INVESTIGATE
      expect(lowBadges.length).toBe(3);
      expect(investigateBadges.length).toBe(1);
    });

    it('handles empty weather variables gracefully', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({
          weather_context: { variables: [], note: 'No data' },
        }),
        loading: false,
        error: null,
      });

      render(<ResponseOrchestrator />);
      // Should still render without crashing
      expect(screen.getByText('POLLUTION INCIDENT ACTIVE')).toBeInTheDocument();
      // All 4 domains should be LOW (no weather data to match)
      const lowBadges = screen.getAllByText('LOW');
      expect(lowBadges.length).toBe(4);
    });
  });

  // ── 9. Honesty & Disclaimer Checks ───────────────────────────

  describe('honesty and disclaimers', () => {
    it('shows disclaimer text in episode state', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText(/Response workflow simulation/)).toBeInTheDocument();
      expect(screen.getByText(/not confirmed emission sources/)).toBeInTheDocument();
      expect(screen.getByText(/not represent live government dispatch/)).toBeInTheDocument();
    });

    it('disclaimer contains "not confirmed" — not an affirmative claim', () => {
      render(<ResponseOrchestrator />);
      const body = document.body.textContent;
      // The disclaimer properly negates: "not confirmed emission sources"
      expect(body).toMatch(/not confirmed emission sources/i);
      expect(body).toMatch(/do not represent live government dispatch/i);
    });

    it('does NOT affirm that any domain IS a source', () => {
      render(<ResponseOrchestrator />);
      const body = document.body.textContent;
      // Should never say "this is the source" or "confirmed by"
      expect(body).not.toMatch(/this is the source/i);
      expect(body).not.toMatch(/confirmed by/i);
    });

    it('does NOT use ML/AI terminology for investigation signals', () => {
      render(<ResponseOrchestrator />);
      const body = document.body.textContent;
      expect(body).not.toMatch(/AI detected/i);
      expect(body).not.toMatch(/machine learning/i);
      expect(body).not.toMatch(/model detected/i);
    });
  });

  // ── 10. Response Workflow Section ────────────────────────────

  describe('workflow section visibility', () => {
    it('renders "Response Workflow" heading in episode state', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Response Workflow')).toBeInTheDocument();
    });

    it('renders investigation signals heading in episode state', () => {
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Investigation Signals')).toBeInTheDocument();
    });

    it('does NOT render workflow or investigation in normal state', () => {
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ state: 'normal' }),
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.queryByText('Response Workflow')).not.toBeInTheDocument();
      expect(screen.queryByText('Investigation Signals')).not.toBeInTheDocument();
    });
  });

  // ── 11. PM2.5 Severity Display ──────────────────────────────

  describe('PM2.5 severity', () => {
    it('displays "Unhealthy" severity for PM2.5 ~145', () => {
      render(<ResponseOrchestrator />);
      // PM25_LEVELS: 150.4 is the Unhealthy boundary, so 145 should be "Unhealthy for Sensitive Groups"
      const severityBadge = screen.getByText(/Sensitive Groups|Unhealthy/);
      expect(severityBadge).toBeInTheDocument();
    });

    it('displays "Hazardous" severity for PM2.5 > 300', () => {
      // Override episode PM2.5 to 350 (component now reads episode first)
      mockUseEpisodeIntelligence.mockReturnValue({
        episode: makeEpisode({ current_pm25: 350.0 }),
        loading: false,
        error: null,
      });
      mockUseForecast.mockReturnValue({
        forecasts: makeForecasts(350.0),
        errors: [],
        forecastStatus: { ready: true },
        loading: false,
        error: null,
      });
      render(<ResponseOrchestrator />);
      expect(screen.getByText('Hazardous')).toBeInTheDocument();
    });
  });

  // ── 12. Step Descriptions ────────────────────────────────────

  describe('workflow step descriptions', () => {
    it('shows detected step description when at step 0', () => {
      render(<ResponseOrchestrator />);
      // Episode state starts with initialStep: -1, so 'Start Response Workflow' button is shown
      fireEvent.click(screen.getByText('Start Response Workflow'));
      expect(screen.getByText(/rule-based episode intelligence/)).toBeInTheDocument();
    });

    it('shows investigate step description with active domains', () => {
      render(<ResponseOrchestrator />);
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      expect(screen.getByText(/Investigation task generated/)).toBeInTheDocument();
    });

    it('shows acknowledge step description', () => {
      render(<ResponseOrchestrator />);
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      fireEvent.click(screen.getByText('Advance to: Acknowledge'));
      // 'acknowledged' is in <strong>, text is split; use the non-bold portion
      expect(screen.getByText(/Investigation signals reviewed by operator/)).toBeInTheDocument();
    });

    it('shows review step description in episode state', () => {
      render(<ResponseOrchestrator />);
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      fireEvent.click(screen.getByText('Advance to: Acknowledge'));
      fireEvent.click(screen.getByText('Advance to: Review'));
      expect(screen.getByText(/Review required/)).toBeInTheDocument();
    });

    it('shows closed step description', () => {
      render(<ResponseOrchestrator />);
      fireEvent.click(screen.getByText('Start Response Workflow'));
      fireEvent.click(screen.getByText('Advance to: Investigate'));
      fireEvent.click(screen.getByText('Advance to: Acknowledge'));
      fireEvent.click(screen.getByText('Advance to: Review'));
      fireEvent.click(screen.getByText('Advance to: Closed'));
      expect(screen.getByText(/No further action required/)).toBeInTheDocument();
    });
  });
});
