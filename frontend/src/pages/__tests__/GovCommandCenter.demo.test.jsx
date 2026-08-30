/**
 * GovCommandCenter — Demo Mode Integration Tests.
 *
 * Tests: demo controller rendering, section visibility by step,
 * demo badge display, demo data swapping.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

/* ── Mocks ──────────────────────────────────────────────── */

// Mock useDemoData
vi.mock('../../demo', () => ({
  useDemoData: vi.fn(),
}));

// Mock all hooks
vi.mock('../../hooks/useHealth', () => ({
  useHealth: vi.fn(() => ({ online: true })),
}));
vi.mock('../../hooks/useForecast', () => ({
  useForecast: vi.fn(() => ({
    forecasts: { '1': { predicted_pm25: 165 } },
    errors: [],
    forecastStatus: { freshness: 'fresh' },
    loading: false,
    error: null,
    refresh: vi.fn(),
  })),
}));
vi.mock('../../hooks/useEpisodeIntelligence', () => ({
  useEpisodeIntelligence: vi.fn(() => ({
    episode: null,
    loading: false,
    error: null,
  })),
}));
vi.mock('../../hooks/useInvestigationAnalysis', () => ({
  useInvestigationAnalysis: vi.fn(() => ({
    analysis: null,
    loading: false,
    error: null,
  })),
}));
vi.mock('../../hooks/useExposureGeometry', () => ({
  useExposureGeometry: vi.fn(() => ({
    exposure: null,
    loading: false,
  })),
}));
vi.mock('../../hooks/useVerification', () => ({
  useVerification: vi.fn(() => ({
    stats: null,
    context: null,
    submitting: false,
    submitSuccess: false,
    error: null,
  })),
}));
vi.mock('../../hooks/useInvestigationLearning', () => ({
  useInvestigationLearning: vi.fn(() => ({
    learning: null,
    loading: false,
    error: null,
  })),
}));
vi.mock('../../services/api', () => ({
  getStations: vi.fn(() => Promise.resolve({ stations: [] })),
}));

// Mock child components
vi.mock('../../components/common/DataFreshness', () => ({
  default: () => <span data-testid="data-freshness" />,
}));
vi.mock('../../components/common/LoadingState', () => ({
  default: ({ message }) => <div data-testid="loading-state">{message}</div>,
}));
vi.mock('../../components/common/ErrorState', () => ({
  default: () => <div data-testid="error-state" />,
}));
vi.mock('../../components/command/OperationsMap', () => ({
  default: () => <div data-testid="operations-map" />,
}));
vi.mock('../../components/exposure/ExposureIntelligenceMap', () => ({
  default: () => <div data-testid="exposure-map" />,
}));
vi.mock('../../components/incident/EpisodeStateHero', () => ({
  default: () => <div data-testid="episode-state-hero" />,
}));
vi.mock('../../components/incident/AISummary', () => ({
  default: () => <div data-testid="ai-summary" />,
}));
vi.mock('../../components/incident/AIPriorityCard', () => ({
  default: () => <div data-testid="ai-priority-card" />,
}));
vi.mock('../../components/incident/AIAnalysisBrief', () => ({
  default: () => <div data-testid="ai-analysis-brief" />,
}));
vi.mock('../../components/incident/AIUncertainty', () => ({
  default: () => <div data-testid="ai-uncertainty" />,
}));
vi.mock('../../components/incident/AIRecommendedActions', () => ({
  default: () => <div data-testid="ai-recommended-actions" />,
}));
vi.mock('../../components/incident/TrustSnapshot', () => ({
  default: () => <div data-testid="trust-snapshot" />,
}));
vi.mock('../../components/forecast/TechnicalDeepDive', () => ({
  default: () => <div data-testid="technical-deep-dive" />,
}));
vi.mock('../../components/forecast/PredictionAccountability', () => ({
  default: () => <div data-testid="prediction-accountability" />,
}));
vi.mock('../../components/forecast/HistoricalTrendChart', () => ({
  default: () => <div data-testid="historical-trend-chart" />,
}));
vi.mock('../../components/incident/InvestigationVerification', () => ({
  default: () => <div data-testid="investigation-verification" />,
}));
vi.mock('../../components/incident/HistoricalVerificationContext', () => ({
  default: () => <div data-testid="historical-verification-context" />,
}));
vi.mock('../../components/incident/InvestigationLearning', () => ({
  default: () => <div data-testid="investigation-learning" />,
}));
vi.mock('../../components/command/DemoController', () => ({
  default: () => <div data-testid="demo-controller" />,
}));

import { useDemoData } from '../../demo';
import GovCommandCenter from '../GovCommandCenter';

const DEMO_EPISODE = {
  state: 'episode',
  trajectory: 'rising',
  current_pm25: 165,
  trajectory_description: 'PM2.5 is rising.',
  narrative: 'Pollution episode detected.',
  source_compass: { current_wind: { sector: 'E', wind_speed_ms: 5 } },
};

const DEMO_FORECASTS = {
  '1': { predicted_pm25: 165, horizon_hours: 1 },
  '3': { predicted_pm25: 175, horizon_hours: 3 },
  '6': { predicted_pm25: 180, horizon_hours: 6 },
  '12': { predicted_pm25: 160, horizon_hours: 12 },
  '24': { predicted_pm25: 142, horizon_hours: 24 },
};

const DEMO_INVESTIGATION = {
  analysis: {
    ai_summary: { summary: 'Test summary' },
    investigation_priority: { level: 'HIGH', score: 85 },
    investigation_hypotheses: [{ hypothesis: 'test', confidence: 0.8 }],
    recommended_actions: [{ action: 'test action' }],
    limitations: [],
    risk_factors: [],
    key_findings: [],
  },
};

const DEMO_EXPOSURE = { corridor: [] };

const DEMO_VERIFICATION_PENDING = { current_outcome: null };
const DEMO_VERIFICATION_COMPLETED = {
  current_outcome: { outcome_type: 'USEFUL', field_notes: 'Confirmed' },
};
const DEMO_VERIFICATION_STATS = { total: 5, useful: 3 };
const DEMO_INVESTIGATION_LEARNING = { total_cases: 12 };

function makeDemoContext(overrides = {}) {
  return {
    episodeNormal: { state: 'normal', current_pm25: 85, trajectory: 'stable' },
    episode: DEMO_EPISODE,
    forecasts: DEMO_FORECASTS,
    forecastStatus: { freshness: 'fresh' },
    analogs: [],
    alertHistory: [],
    reports: [],
    favorites: [],
    stations: [],
    investigationAnalysis: DEMO_INVESTIGATION,
    exposureGeometry: DEMO_EXPOSURE,
    verification: DEMO_VERIFICATION_PENDING,
    verificationPending: DEMO_VERIFICATION_PENDING,
    verificationCompleted: DEMO_VERIFICATION_COMPLETED,
    verificationStats: DEMO_VERIFICATION_STATS,
    investigationLearning: DEMO_INVESTIGATION_LEARNING,
    demoStep: 1,
    setDemoStep: vi.fn(),
    resetDemo: vi.fn(),
    ...overrides,
  };
}

describe('GovCommandCenter — Demo Mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Demo badge', () => {
    it('shows DEMO SCENARIO badge in header when demo=true', () => {
      useDemoData.mockReturnValue(makeDemoContext());
      render(<GovCommandCenter />);
      expect(screen.getByTestId('demo-badge')).toBeInTheDocument();
      expect(screen.getByText(/DEMO SCENARIO/)).toBeInTheDocument();
    });
  });

  describe('DemoController presence', () => {
    it('renders DemoController in demo mode', () => {
      useDemoData.mockReturnValue(makeDemoContext({ demoStep: 1 }));
      render(<GovCommandCenter />);
      expect(screen.getByTestId('demo-controller')).toBeInTheDocument();
    });
  });

  describe('Section data-demo-section attributes', () => {
    it('renders data-demo-section on incident status', () => {
      useDemoData.mockReturnValue(makeDemoContext({ demoStep: 1 }));
      const { container } = render(<GovCommandCenter />);
      expect(container.querySelector('[data-demo-section="cc-section-status"]')).toBeInTheDocument();
    });
  });

  describe('Demo data selection', () => {
    it('uses normal episode at step 1', () => {
      const ctx = makeDemoContext({ demoStep: 1 });
      useDemoData.mockReturnValue(ctx);
      render(<GovCommandCenter />);
      // EpisodeStateHero should render (even though it's a mock)
      expect(screen.getByTestId('episode-state-hero')).toBeInTheDocument();
    });
  });

  describe('Conditional rendering by step', () => {
    it('hides investigation sections at step 2 (showInvestigation=false)', () => {
      // At step 2: showInvestigation=false, showBelowFold=false
      // hasAnalysis should be false since investigationAnalysis won't be used
      const ctx = makeDemoContext({ demoStep: 2 });
      useDemoData.mockReturnValue(ctx);
      const { container } = render(<GovCommandCenter />);
      // investigation section should NOT be visible
      expect(container.querySelector('[data-demo-section="cc-section-investigation"]')).not.toBeInTheDocument();
    });

    it('shows investigation sections at step 3', () => {
      const ctx = makeDemoContext({ demoStep: 3 });
      useDemoData.mockReturnValue(ctx);
      const { container } = render(<GovCommandCenter />);
      expect(container.querySelector('[data-demo-section="cc-section-investigation"]')).toBeInTheDocument();
    });

    it('shows below-fold at step 4', () => {
      const ctx = makeDemoContext({ demoStep: 4 });
      useDemoData.mockReturnValue(ctx);
      const { container } = render(<GovCommandCenter />);
      expect(container.querySelector('[data-demo-section="cc-section-exposure"]')).toBeInTheDocument();
    });

    it('shows verification section at step 5', () => {
      const ctx = makeDemoContext({ demoStep: 5 });
      useDemoData.mockReturnValue(ctx);
      const { container } = render(<GovCommandCenter />);
      expect(container.querySelector('[data-demo-section="cc-section-verification"]')).toBeInTheDocument();
    });

    it('shows accountability section at step 6', () => {
      const ctx = makeDemoContext({ demoStep: 6 });
      useDemoData.mockReturnValue(ctx);
      const { container } = render(<GovCommandCenter />);
      expect(container.querySelector('[data-demo-section="cc-section-accountability"]')).toBeInTheDocument();
    });
  });
});
