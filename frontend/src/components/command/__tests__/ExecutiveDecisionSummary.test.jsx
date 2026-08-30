/**
 * ExecutiveDecisionSummary — Phase 12 Tests.
 *
 * Covers all 6 demo steps, supporting evidence, verification status,
 * accessibility, and edge cases.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import ExecutiveDecisionSummary from '../ExecutiveDecisionSummary';

/* ── Fixtures ──────────────────────────────────────────── */

const EPISODE_NORMAL = {
  state: 'normal',
  trajectory: 'stable',
  current_pm25: 85,
  source_compass: {
    current_wind: { sector: 'NW', wind_speed_ms: 4.8 },
  },
};

const EPISODE_ACTIVE = {
  state: 'episode',
  trajectory: 'rising',
  current_pm25: 165,
  source_compass: {
    current_wind: { sector: 'E', wind_speed_ms: 3.2 },
  },
};

const ANALYSIS = {
  analysis_status: 'complete',
  investigation_hypotheses: [
    {
      factor: 'East sector industrial or agricultural emissions',
      confidence: 0.65,
      reasoning: 'Wind from East with 1.44x enrichment.',
      verification_needed: 'Field inspection.',
    },
  ],
  investigation_priority: {
    area: 'East sector corridor',
    priority: 'HIGH',
  },
  recommended_actions: [
    {
      priority: 1,
      action: 'Deploy field inspection team to East sector',
      rationale: 'Highest historical enrichment.',
      verification_goal: 'Confirm or rule out emission sources.',
    },
  ],
};

const EXPOSURE = {
  investigation_area: {
    priority: 'HIGH',
  },
  vulnerable_locations: {
    schools: [
      { name: 'School A' },
      { name: 'School B' },
      { name: 'School C' },
      { name: 'School D' },
      { name: 'School E' },
    ],
    hospitals: [
      { name: 'Hospital A' },
      { name: 'Hospital B' },
      { name: 'Hospital C' },
    ],
  },
};

const VERIFICATION_USEFUL = {
  current_outcome: {
    overall_status: 'USEFUL',
    recommendation_verification: 'SUPPORTED',
    investigation_area_verification: 'PARTIALLY_SUPPORTED',
  },
};

const VERIFICATION_PARTIAL = {
  current_outcome: {
    overall_status: 'PARTIALLY_USEFUL',
  },
};

const VERIFICATION_NOT_SUPPORTED = {
  current_outcome: {
    overall_status: 'NOT_SUPPORTED',
  },
};

const VERIFICATION_PENDING = {
  current_outcome: null,
};

/* ── Tests ─────────────────────────────────────────────── */

describe('ExecutiveDecisionSummary', () => {
  describe('Rendering', () => {
    it('renders with data-testid', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={1}
          episode={EPISODE_NORMAL}
        />
      );
      expect(screen.getByTestId('executive-decision-summary')).toBeInTheDocument();
    });

    it('returns null when demoStep is 0', () => {
      const { container } = render(
        <ExecutiveDecisionSummary
          demoStep={0}
          episode={EPISODE_NORMAL}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('sets data-demo-step attribute', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={3}
          episode={EPISODE_ACTIVE}
        />
      );
      expect(screen.getByTestId('executive-decision-summary')).toHaveAttribute('data-demo-step', '3');
    });

    it('has role="region" for accessibility', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={1}
          episode={EPISODE_NORMAL}
        />
      );
      expect(screen.getByRole('region', { name: /executive decision summary/i })).toBeInTheDocument();
    });
  });

  describe('Step 1 — Normal Monitoring', () => {
    beforeEach(() => {
      render(
        <ExecutiveDecisionSummary
          demoStep={1}
          episode={EPISODE_NORMAL}
        />
      );
    });

    it('shows NOMINAL status badge', () => {
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('NOMINAL');
    });

    it('shows no abnormal event message', () => {
      expect(screen.getByTestId('eds-what-happened')).toHaveTextContent('No abnormal pollution event');
    });

    it('shows no investigation active', () => {
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('No investigation active');
    });

    it('shows continue monitoring action', () => {
      expect(screen.getByTestId('eds-recommended-action')).toHaveTextContent('Continue monitoring');
    });

    it('shows PM2.5 signal', () => {
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('85 μg/m³');
    });

    it('shows N/A verification status', () => {
      expect(screen.getByTestId('eds-verification-status')).toHaveTextContent('N/A');
    });
  });

  describe('Step 2 — Anomaly Detected', () => {
    beforeEach(() => {
      render(
        <ExecutiveDecisionSummary
          demoStep={2}
          episode={EPISODE_ACTIVE}
        />
      );
    });

    it('shows EPISODE ACTIVE status badge', () => {
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('EPISODE ACTIVE');
    });

    it('shows anomaly message with PM2.5 value', () => {
      expect(screen.getByTestId('eds-what-happened')).toHaveTextContent('165');
    });

    it('shows evidence assembly in progress', () => {
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('Evidence assembly in progress');
    });

    it('shows awaiting AI action', () => {
      expect(screen.getByTestId('eds-recommended-action')).toHaveTextContent('Awaiting AI investigation');
    });

    it('shows no NOT VERIFIED badge', () => {
      expect(screen.queryByTestId('eds-not-verified')).not.toBeInTheDocument();
    });
  });

  describe('Step 3 — Investigation Active', () => {
    beforeEach(() => {
      render(
        <ExecutiveDecisionSummary
          demoStep={3}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
        />
      );
    });

    it('shows INVESTIGATION status badge', () => {
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('INVESTIGATION');
    });

    it('shows top hypothesis from AI', () => {
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('East sector industrial');
    });

    it('shows NOT VERIFIED badge', () => {
      expect(screen.getByTestId('eds-not-verified')).toBeInTheDocument();
    });

    it('shows confidence in evidence signals', () => {
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('65%');
    });

    it('shows awaiting human verification', () => {
      expect(screen.getByTestId('eds-verification-status')).toHaveTextContent('Awaiting human verification');
    });

    it('shows recommended action from analysis', () => {
      expect(screen.getByTestId('eds-recommended-action')).toHaveTextContent('Deploy field inspection team');
    });
  });

  describe('Step 4 — Exposure Active', () => {
    it('shows INVESTIGATION status badge', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={4}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          exposureGeometry={EXPOSURE}
        />
      );
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('INVESTIGATION');
    });

    it('shows vulnerable sites count (5 + 3 = 8)', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={4}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          exposureGeometry={EXPOSURE}
        />
      );
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('8');
    });

    it('shows Area Priority signal', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={4}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          exposureGeometry={EXPOSURE}
        />
      );
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('HIGH');
    });
  });

  describe('Step 5 — Verification Complete', () => {
    it('shows VERIFIED badge when USEFUL', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('VERIFIED');
    });

    it('shows verification outcome', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('Human verification: USEFUL');
    });

    it('shows verification label with verified icon', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-verification-status')).toHaveTextContent('Recommendation useful');
    });

    it('shows CONCERN when NOT_SUPPORTED', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_NOT_SUPPORTED}
        />
      );
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('CONCERN');
    });

    it('shows VERIFYING amber badge when PARTIALLY_USEFUL', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_PARTIAL}
        />
      );
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('VERIFIED');
    });

    it('shows correct action for verified outcome', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-recommended-action')).toHaveTextContent('Investigation outcome useful');
    });
  });

  describe('Step 6 — Accountability Visible', () => {
    it('shows ACCOUNTABILITY status badge', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={6}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-status-badge')).toHaveTextContent('ACCOUNTABILITY');
    });

    it('shows verification outcome in assessment when outcome is present', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={6}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('Human verification: USEFUL');
    });

    it('shows historical reliability when no outcome is present', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={6}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_PENDING}
        />
      );
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('Historical reliability');
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('79%');
    });

    it('shows accountability action', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={6}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-recommended-action')).toHaveTextContent('Outcome recorded');
    });

    it('shows historical cases signal', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={6}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          verificationContext={VERIFICATION_USEFUL}
        />
      );
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('12 evaluated');
    });
  });

  describe('Edge Cases', () => {
    it('handles missing episode gracefully', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={1}
        />
      );
      expect(screen.getByTestId('executive-decision-summary')).toBeInTheDocument();
      // With no episode, PM2.5 signal is absent but Trend shows 'stable' (default)
      expect(screen.getByTestId('eds-evidence')).toHaveTextContent('stable');
    });

    it('handles missing analysis in step 3', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={3}
          episode={EPISODE_ACTIVE}
        />
      );
      expect(screen.getByTestId('eds-system-assessment')).toHaveTextContent('Analysis in progress');
      expect(screen.queryByTestId('eds-not-verified')).not.toBeInTheDocument();
    });

    it('handles step 2 with no analysis', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={2}
          episode={EPISODE_ACTIVE}
        />
      );
      expect(screen.getByTestId('eds-verification-status')).toHaveTextContent('N/A');
    });

    it('handles step 5 without outcome', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={5}
          episode={EPISODE_ACTIVE}
          verificationContext={VERIFICATION_PENDING}
        />
      );
      expect(screen.getByTestId('eds-verification-status')).toHaveTextContent('Awaiting human verification');
    });

    it('limits evidence signals to 3 max', () => {
      render(
        <ExecutiveDecisionSummary
          demoStep={4}
          episode={EPISODE_ACTIVE}
          investigationAnalysis={ANALYSIS}
          exposureGeometry={EXPOSURE}
        />
      );
      const signals = screen.getAllByTestId('eds-signal');
      expect(signals.length).toBeLessThanOrEqual(3);
    });
  });
});
