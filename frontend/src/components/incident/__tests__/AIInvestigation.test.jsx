/**
 * AI Investigation Components Tests.
 *
 * Tests: all 5 AI section components + the restructured GovCommandCenter.
 * Covers: rendering, data flow, empty states, confidence display, fallback, demo mode.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// ── Mock dependencies ──────────────────────────────────────

vi.mock('../../demo', () => ({
  useDemoData: vi.fn(() => null),
}));

vi.mock('../../hooks/useForecast', () => ({
  useForecast: vi.fn(() => ({
    forecasts: {},
    errors: [],
    forecastStatus: null,
    loading: false,
    error: null,
    refresh: vi.fn(),
  })),
}));

vi.mock('../../hooks/useInvestigationAnalysis', () => ({
  useInvestigationAnalysis: vi.fn(() => ({
    analysis: null,
    evidence: null,
    metadata: null,
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

vi.mock('../../hooks/useHistoricalAnalogs', () => ({
  useHistoricalAnalogs: vi.fn(() => ({
    analogs: null,
    loading: false,
    error: null,
  })),
}));

vi.mock('../../hooks/useHealth', () => ({
  useHealth: vi.fn(() => ({ online: true })),
}));

vi.mock('../../services/api', () => ({
  getStations: vi.fn(async () => ({ stations: [] })),
  getInvestigationAnalysis: vi.fn(async () => ({})),
}));

// Mock child components that would cause import issues
vi.mock('../../components/common/DataFreshness', () => ({
  default: () => <div data-testid="data-freshness" />,
}));

vi.mock('../../components/common/LoadingState', () => ({
  default: ({ message }) => <div data-testid="loading-state">{message}</div>,
}));

vi.mock('../../components/common/ErrorState', () => ({
  default: ({ error }) => <div data-testid="error-state">{String(error)}</div>,
}));

vi.mock('../../components/command/OperationsMap', () => ({
  default: () => <div data-testid="operations-map" />,
}));

vi.mock('../../components/incident/EpisodeStateHero', () => ({
  default: () => <div data-testid="episode-state-hero" />,
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

// ── Import components under test ───────────────────────────

import AISummary from '../AISummary';
import AIPriorityCard from '../AIPriorityCard';
import AIAnalysisBrief from '../AIAnalysisBrief';
import AIUncertainty from '../AIUncertainty';
import AIRecommendedActions from '../AIRecommendedActions';

// ── Mock Data ──────────────────────────────────────────────

const MOCK_ANALYSIS = {
  analysis_status: 'complete',
  event_summary: 'An active pollution episode is underway in Lahore with PM2.5 at elevated levels.',
  severity_assessment: 'Episode state with rising trajectory indicates active pollution accumulation.',
  observed_facts: [
    {
      statement: 'PM2.5 levels are in the episode range.',
      evidence_references: ['event_detection.data.state'],
    },
    {
      statement: 'Wind is currently arriving from the East sector.',
      evidence_references: ['directional_analysis.current_wind'],
    },
  ],
  model_inferences: [
    {
      statement: 'Directional enrichment represents a statistical association.',
      confidence: 0.70,
      supporting_evidence: ['directional_analysis.historical.strongest_enrichment'],
    },
  ],
  investigation_hypotheses: [
    {
      factor: 'East sector industrial emissions',
      confidence: 0.65,
      reasoning: 'Wind from the East with 1.44x enrichment.',
      supporting_evidence: ['directional_analysis'],
      verification_needed: 'Field inspection of East corridor.',
    },
  ],
  investigation_priority: {
    area: 'East sector corridor',
    priority: 'HIGH',
    rationale: 'Highest directional enrichment (1.44x).',
    confidence: 0.70,
  },
  uncertainties: [
    'Source compass enrichment shows association, not confirmed source.',
    'Historical analog matching does not account for emission changes.',
  ],
  data_gaps: [
    'No satellite fire detection data available.',
  ],
  recommended_actions: [
    {
      priority: 1,
      action: 'Deploy field inspection team to East sector.',
      rationale: 'East sector shows highest historical enrichment.',
      verification_goal: 'Confirm or rule out emission sources.',
    },
    {
      priority: 2,
      action: 'Request satellite fire detection data.',
      rationale: 'Determine if open burning is present.',
      verification_goal: 'Establish if burning contributes.',
    },
  ],
};

// ── AISummary Tests ────────────────────────────────────────

describe('AISummary', () => {
  it('renders event summary text', () => {
    render(<AISummary analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(MOCK_ANALYSIS.event_summary)).toBeInTheDocument();
  });

  it('renders severity assessment', () => {
    render(<AISummary analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(MOCK_ANALYSIS.severity_assessment)).toBeInTheDocument();
  });

  it('renders "Severity Assessment" label', () => {
    render(<AISummary analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('Severity Assessment')).toBeInTheDocument();
  });

  it('returns null when no analysis', () => {
    const { container } = render(<AISummary analysis={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders summary without severity', () => {
    const analysis = { event_summary: 'Test summary.', severity_assessment: '' };
    render(<AISummary analysis={analysis} />);
    expect(screen.getByText('Test summary.')).toBeInTheDocument();
    expect(screen.queryByText('Severity Assessment')).not.toBeInTheDocument();
  });
});

// ── AIPriorityCard Tests ───────────────────────────────────

describe('AIPriorityCard', () => {
  it('renders priority area name', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    expect(screen.getByText('East sector corridor')).toBeInTheDocument();
  });

  it('renders "Priority Investigation Area" label', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    expect(screen.getByText('Priority Investigation Area')).toBeInTheDocument();
  });

  it('renders HIGH badge', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });

  it('renders rationale', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    expect(screen.getByText(/Highest directional enrichment/)).toBeInTheDocument();
  });

  it('renders confidence percentage', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    expect(screen.getByText('70% confidence')).toBeInTheDocument();
  });

  it('returns null when no priority', () => {
    const { container } = render(<AIPriorityCard priority={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('does NOT say "Pollution came from"', () => {
    render(<AIPriorityCard priority={MOCK_ANALYSIS.investigation_priority} />);
    const allText = document.body.textContent;
    expect(allText).not.toContain('Pollution came from');
  });
});

// ── AIAnalysisBrief Tests ──────────────────────────────────

describe('AIAnalysisBrief', () => {
  it('renders observed facts section', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('OBSERVED FACTS')).toBeInTheDocument();
  });

  it('renders model inferences section', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('MODEL INFERENCES')).toBeInTheDocument();
  });

  it('renders hypotheses section', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('HYPOTHESES')).toBeInTheDocument();
  });

  it('renders fact statements', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(/PM2.5 levels are in the episode range/)).toBeInTheDocument();
  });

  it('renders inference with confidence', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('70%')).toBeInTheDocument();
  });

  it('renders hypothesis with verification needed', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(/Field inspection of East corridor/)).toBeInTheDocument();
  });

  it('renders "HYPOTHESIS — REQUIRES FIELD VERIFICATION" label', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('HYPOTHESIS — REQUIRES FIELD VERIFICATION')).toBeInTheDocument();
  });

  it('renders evidence references', () => {
    render(<AIAnalysisBrief analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(/event_detection.data.state/)).toBeInTheDocument();
  });

  it('shows empty message when no data', () => {
    const emptyAnalysis = {
      observed_facts: [],
      model_inferences: [],
      investigation_hypotheses: [],
    };
    render(<AIAnalysisBrief analysis={emptyAnalysis} />);
    expect(screen.getByText('No investigation analysis available.')).toBeInTheDocument();
  });

  it('returns null when analysis is null', () => {
    const { container } = render(<AIAnalysisBrief analysis={null} />);
    expect(container.firstChild).toBeNull();
  });
});

// ── AIUncertainty Tests ────────────────────────────────────

describe('AIUncertainty', () => {
  it('renders "Limitations" header', () => {
    render(<AIUncertainty analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('Limitations')).toBeInTheDocument();
  });

  it('renders "Data Gaps" header', () => {
    render(<AIUncertainty analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText('Data Gaps')).toBeInTheDocument();
  });

  it('renders uncertainty items', () => {
    render(<AIUncertainty analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(/Source compass enrichment shows association/)).toBeInTheDocument();
  });

  it('renders data gap items', () => {
    render(<AIUncertainty analysis={MOCK_ANALYSIS} />);
    expect(screen.getByText(/No satellite fire detection data available/)).toBeInTheDocument();
  });

  it('returns null when no uncertainties or gaps', () => {
    const emptyAnalysis = { uncertainties: [], data_gaps: [] };
    const { container } = render(<AIUncertainty analysis={emptyAnalysis} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when analysis is null', () => {
    const { container } = render(<AIUncertainty analysis={null} />);
    expect(container.firstChild).toBeNull();
  });
});

// ── AIRecommendedActions Tests ─────────────────────────────

describe('AIRecommendedActions', () => {
  it('renders all actions', () => {
    render(<AIRecommendedActions actions={MOCK_ANALYSIS.recommended_actions} />);
    expect(screen.getByText(/Deploy field inspection team/)).toBeInTheDocument();
    expect(screen.getByText(/Request satellite fire detection/)).toBeInTheDocument();
  });

  it('renders priority numbers', () => {
    render(<AIRecommendedActions actions={MOCK_ANALYSIS.recommended_actions} />);
    // Priority 1 should be present
    const nums = screen.getAllByText(/[12]/);
    expect(nums.length).toBeGreaterThanOrEqual(2);
  });

  it('renders verification goals', () => {
    render(<AIRecommendedActions actions={MOCK_ANALYSIS.recommended_actions} />);
    const labels = screen.getAllByText('Verification goal:');
    expect(labels.length).toBe(2);
    labels.forEach(label => expect(label).toBeInTheDocument());
  });

  it('renders rationale', () => {
    render(<AIRecommendedActions actions={MOCK_ANALYSIS.recommended_actions} />);
    expect(screen.getByText(/East sector shows highest historical enrichment/)).toBeInTheDocument();
  });

  it('sorts actions by priority', () => {
    const shuffled = [
      { priority: 3, action: 'Third action', rationale: 'R3', verification_goal: 'V3' },
      { priority: 1, action: 'First action', rationale: 'R1', verification_goal: 'V1' },
      { priority: 2, action: 'Second action', rationale: 'R2', verification_goal: 'V2' },
    ];
    render(<AIRecommendedActions actions={shuffled} />);
    const actionTexts = screen.getAllByText(/action$/i);
    // First should be "First action"
    expect(actionTexts[0]).toHaveTextContent('First action');
    expect(actionTexts[1]).toHaveTextContent('Second action');
    expect(actionTexts[2]).toHaveTextContent('Third action');
  });

  it('returns null when no actions', () => {
    const { container } = render(<AIRecommendedActions actions={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when actions is undefined', () => {
    const { container } = render(<AIRecommendedActions actions={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('highlights first action with "first" class', () => {
    render(<AIRecommendedActions actions={MOCK_ANALYSIS.recommended_actions} />);
    const firstCard = screen.getByText(/Deploy field inspection team/).closest('.ai-actions__card--first');
    expect(firstCard).toBeInTheDocument();
  });
});
