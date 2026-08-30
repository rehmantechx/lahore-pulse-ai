/**
 * DecisionTrace Component Tests.
 *
 * Tests: rendering, stages, layer badges, empty states.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { EvidenceProvider } from '../../../context/EvidenceContext';
import DecisionTrace from '../DecisionTrace';

function renderWithProvider(ui, options) {
  return render(<EvidenceProvider>{ui}</EvidenceProvider>, options);
}

const MOCK_EPISODE = {
  id: 'ep-001',
  station_id: 'stn-kot-lakhpat',
  severity: 'severe',
  pm25_peak: 185,
  current_pm25: 185,
  detected_at: '2025-01-15T15:15:00Z',
};

const MOCK_ANALYSIS = {
  episode_id: 'ep-001',
  confidence: 0.85,
  recommended_areas: [
    { area: 'NE Quadrant', priority: 'High', confidence: 0.85, reasoning: 'Wind from SW carrying pollution NE' },
  ],
  reasoning: 'PM2.5 spike at Kot Lakhpat with SW winds suggests NE investigation.',
};

const MOCK_VERIFICATION = {
  episode_id: 'ep-001',
  is_useful: true,
  findings: 'Found active construction site with no dust suppression.',
  officer_name: 'Inspector Khan',
};

describe('DecisionTrace', () => {
  describe('Rendering', () => {
    it('renders the section with decision trace class', () => {
      const { container } = renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(container.querySelector('.decision-trace')).toBeInTheDocument();
    });

    it('renders observed event stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('Observed Event')).toBeInTheDocument();
    });

    it('renders environmental context stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('Environmental Context')).toBeInTheDocument();
    });

    it('renders AI investigation hypothesis stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('AI Investigation Hypothesis')).toBeInTheDocument();
    });

    it('renders human verification stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('Human Verification')).toBeInTheDocument();
    });

    it('renders deterministic analysis stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('Deterministic Analysis')).toBeInTheDocument();
    });

    it('renders investigation priority stage', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('Investigation Priority')).toBeInTheDocument();
    });
  });

  describe('Layer Badges', () => {
    it('displays OBSERVED badge', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('OBSERVED')).toBeInTheDocument();
    });

    it('displays DETERMINISTIC badge', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      const badges = screen.getAllByText('DETERMINISTIC');
      expect(badges.length).toBeGreaterThanOrEqual(1);
    });

    it('displays AI HYPOTHESIS badge', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      const badges = screen.getAllByText('AI HYPOTHESIS');
      expect(badges.length).toBeGreaterThanOrEqual(1);
    });

    it('displays HUMAN VERIFIED badge', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByText('HUMAN VERIFIED')).toBeInTheDocument();
    });
  });

  describe('Empty / Partial States', () => {
    it('renders with episode only (no analysis)', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={null} verification={null} />);
      expect(screen.getByText('Observed Event')).toBeInTheDocument();
    });

    it('shows awaiting verification when no verification data', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={null} />);
      expect(screen.getByText('Human Verification')).toBeInTheDocument();
      expect(screen.getByText(/Awaiting field verification/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has 6 stages and renders region with aria-label', () => {
      const { container } = renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByRole('region', { name: /decision trace/i })).toBeInTheDocument();
      const stages = container.querySelectorAll('.decision-trace__stage');
      expect(stages.length).toBe(6);
    });

    it('each stage card is a button for evidence selection', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      expect(screen.getByTestId('trace-stage-observed')).toBeInTheDocument();
      expect(screen.getByTestId('trace-stage-context')).toBeInTheDocument();
      expect(screen.getByTestId('trace-stage-analysis')).toBeInTheDocument();
      expect(screen.getByTestId('trace-stage-hypothesis')).toBeInTheDocument();
      expect(screen.getByTestId('trace-stage-priority')).toBeInTheDocument();
      expect(screen.getByTestId('trace-stage-verification')).toBeInTheDocument();
    });

    it('clicking a stage card selects it', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      const observedBtn = screen.getByTestId('trace-stage-observed');
      fireEvent.click(observedBtn);
      expect(observedBtn).toHaveAttribute('aria-pressed', 'true');
    });

    it('clicking same stage again deselects it', () => {
      renderWithProvider(<DecisionTrace episode={MOCK_EPISODE} analysis={MOCK_ANALYSIS} verification={MOCK_VERIFICATION} />);
      const observedBtn = screen.getByTestId('trace-stage-observed');
      fireEvent.click(observedBtn);
      expect(observedBtn).toHaveAttribute('aria-pressed', 'true');
      fireEvent.click(observedBtn);
      expect(observedBtn).toHaveAttribute('aria-pressed', 'false');
    });
  });
});
