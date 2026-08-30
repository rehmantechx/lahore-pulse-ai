/**
 * GovCommandCenter — Phase 29 DecisionState & AuditTrail Tests.
 *
 * Verifies:
 * - DecisionState badge renders in command strip in demo mode
 * - AuditTrail renders after AccountabilityChain
 * - DecisionState derives correct state from PM2.5 values
 * - data-demo-section attributes on new sections
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

/* ── Mocks ──────────────────────────────────────────────── */

vi.mock('../../demo', () => ({
  useDemoData: vi.fn(),
}));

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

// Mock child components — minimal stubs
vi.mock('../../components/common/DataFreshness', () => ({
  default: () => <span data-testid="data-freshness" />,
}));
vi.mock('../../components/common/LoadingState', () => ({
  default: () => <div data-testid="loading-state" />,
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
vi.mock('../../components/command/DecisionTrace', () => ({
  default: () => <div data-testid="decision-trace" />,
}));
vi.mock('../../components/command/WhyDifferent', () => ({
  default: () => <div data-testid="why-different" />,
}));
vi.mock('../../components/common/CannotKnow', () => ({
  default: () => <div data-testid="cannot-know" />,
}));
vi.mock('../../components/common/ProgressiveDisclosure', () => ({
  default: ({ children }) => <div data-testid="progressive-disclosure">{children}</div>,
}));
vi.mock('../../components/forecast/PredictionReceipt', () => ({
  default: () => <div data-testid="prediction-receipt" />,
}));
vi.mock('../../components/forecast/ModelMistakes', () => ({
  default: () => <div data-testid="model-mistakes" />,
}));
vi.mock('../../components/forecast/ModelSuccesses', () => ({
  default: () => <div data-testid="model-successes" />,
}));
vi.mock('../../components/forecast/ConfidenceCalibration', () => ({
  default: () => <div data-testid="confidence-calibration" />,
}));
vi.mock('../../components/forecast/WhyTrustThis', () => ({
  default: () => <div data-testid="why-trust-this" />,
}));
vi.mock('../../components/command/InvestigationProgress', () => ({
  default: () => <div data-testid="investigation-progress" />,
}));
vi.mock('../../components/command/AccountabilityChain', () => ({
  default: () => <div data-testid="accountability-chain" />,
}));
vi.mock('../../components/command/AccountabilityLoop', () => ({
  default: () => <div data-testid="accountability-loop" />,
}));
vi.mock('../../components/command/WhyAccountability', () => ({
  default: () => <div data-testid="why-accountability" />,
}));
vi.mock('../../components/command/ExecutiveDecisionSummary', () => ({
  default: () => <div data-testid="executive-decision-summary" />,
}));
vi.mock('../../components/command/InvestigationContextBar', () => ({
  default: () => <div data-testid="investigation-context-bar" />,
}));
vi.mock('../../components/command/AuditTrail', () => ({
  default: () => <div data-testid="audit-trail" />,
}));
vi.mock('../../context/EvidenceContext', () => ({
  EvidenceProvider: ({ children }) => <div>{children}</div>,
  useEvidenceSelection: vi.fn(() => ({
    hasSelection: false,
    isHighlighted: () => false,
  })),
}));

import { useDemoData } from '../../demo';
import GovCommandCenter from '../GovCommandCenter';

function makeDemoContext(overrides = {}) {
  return {
    episodeNormal: { state: 'normal', current_pm25: 85, trajectory: 'stable' },
    episode: {
      state: 'episode',
      trajectory: 'rising',
      current_pm25: 165,
      trajectory_description: 'PM2.5 is rising.',
      narrative: 'Pollution episode detected.',
      source_compass: { current_wind: { sector: 'E', wind_speed_ms: 5 } },
    },
    forecasts: {
      '1': { predicted_pm25: 165, horizon_hours: 1, data_quality: { data_timestamp: new Date().toISOString() } },
    },
    forecastStatus: { freshness: 'fresh' },
    analogs: [],
    alertHistory: [],
    reports: [],
    favorites: [],
    stations: [],
    investigationAnalysis: {
      analysis: {
        ai_summary: { summary: 'Test summary' },
        investigation_priority: { level: 'HIGH', score: 85 },
        investigation_hypotheses: [{ hypothesis: 'test', confidence: 0.8 }],
        recommended_actions: [{ action: 'test action' }],
        limitations: [],
        risk_factors: [],
        key_findings: [],
        analysis_status: 'complete',
      },
    },
    exposureGeometry: { corridor: [] },
    verificationPending: { current_outcome: null },
    verificationCompleted: {
      current_outcome: { outcome_type: 'USEFUL', field_notes: 'Confirmed' },
    },
    verificationStats: { total: 5, useful: 3 },
    investigationLearning: { total_cases: 12 },
    predictionReceipt: { prediction: { value: 165, horizon: '+1h' } },
    modelMistakes: [],
    modelSuccesses: [],
    whyTrust: { total_evaluated: 184, within_tolerance_pct: 76 },
    confidenceCalibrationTable: [],
    demoStep: 7,
    setDemoStep: vi.fn(),
    resetDemo: vi.fn(),
    ...overrides,
  };
}

describe('GovCommandCenter — Phase 29 DecisionState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders DecisionState badge in demo mode at step 7', () => {
    useDemoData.mockReturnValue(makeDemoContext({ demoStep: 7 }));
    render(<GovCommandCenter />);
    // Step 7: PM2.5 = 165 + verification completed → VERIFIED CRITICAL
    expect(screen.getByText('VERIFIED CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('DECISION')).toBeInTheDocument();
  });

  it('renders MONITOR state at step 1 (PM2.5 = 85)', () => {
    useDemoData.mockReturnValue(makeDemoContext({
      demoStep: 1,
      episodeNormal: { state: 'normal', current_pm25: 85, trajectory: 'stable' },
      episode: { state: 'normal', current_pm25: 85, trajectory: 'stable', source_compass: { current_wind: { sector: 'N', wind_speed_ms: 2 } } },
    }));
    render(<GovCommandCenter />);
    expect(screen.getByText('MONITOR')).toBeInTheDocument();
  });

  it('renders AuditTrail in accountability section in demo mode', () => {
    useDemoData.mockReturnValue(makeDemoContext({ demoStep: 7 }));
    render(<GovCommandCenter />);
    expect(screen.getByTestId('audit-trail')).toBeInTheDocument();
  });

  it('data-demo-section cc-section-trust-snapshot exists', () => {
    useDemoData.mockReturnValue(makeDemoContext({ demoStep: 7 }));
    const { container } = render(<GovCommandCenter />);
    expect(container.querySelector('[data-demo-section="cc-section-trust-snapshot"]')).toBeInTheDocument();
  });

  it('data-demo-section cc-section-why-different exists', () => {
    useDemoData.mockReturnValue(makeDemoContext({ demoStep: 7 }));
    const { container } = render(<GovCommandCenter />);
    expect(container.querySelector('[data-demo-section="cc-section-why-different"]')).toBeInTheDocument();
  });
});
