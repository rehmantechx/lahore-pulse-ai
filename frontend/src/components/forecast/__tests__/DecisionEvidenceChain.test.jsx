/**
 * DecisionEvidenceChain — Phase 29 Tests.
 *
 * 5-step visual chain: Data Foundation → AI Prediction → Investigation Brief → Verification → Accountability.
 * Renders with demo data (useDemoData) or explicit `steps` prop.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

import DecisionEvidenceChain from '../DecisionEvidenceChain';
import { useDemoData } from '../../../demo';

const DEMO_STEPS = [
  { id: 'dec-step-1', title: 'Data Foundation', icon: 'database', status: 'complete', data: { label: '47 features ingested', source: 'Monitoring station + ECMWF', freshness: '18 minutes before prediction', detail: 'Air quality sensors, wind speed/direction, temperature, humidity, pressure, and historical baselines' } },
  { id: 'dec-step-2', title: 'AI Prediction', icon: 'brain', status: 'complete', data: { label: '165 μg/m3 predicted at 6h horizon', source: 'HistGradientBoosting ensemble (v3.2)', confidence: '82%', detail: 'Algorithm trained on verified historical episodes.' } },
  { id: 'dec-step-3', title: 'Investigation Brief', icon: 'search', status: 'complete', data: { label: '3 constrained hypotheses', source: 'Evidence chain + historical analog matching', bestMatch: 'Industrial emissions (67% match)', detail: 'Hypotheses bounded by physical plausibility.' } },
  { id: 'dec-step-4', title: 'Verification', icon: 'check-circle', status: 'complete', data: { label: '9.7% error (within tolerance)', source: 'Observed 181 μg/m3 vs. predicted 165 μg/m3', calibration: 'GOOD — confidence matched accuracy', detail: 'Prediction was conservative (underestimated).' } },
  { id: 'dec-step-5', title: 'Accountability', icon: 'shield', status: 'complete', data: { label: 'Receipt LP-000184 finalized', source: 'Prediction verified, investigation reviewed, record stored', permanent: 'Cannot be edited after the fact', detail: 'Full audit trail from data ingestion to verification is preserved.' } },
];

describe('DecisionEvidenceChain', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode (no steps prop)', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({
        evidenceChain: DEMO_STEPS,
      });
    });

    it('renders the evidence chain container', () => {
      render(<DecisionEvidenceChain open={true} />);
      expect(screen.getByTestId('evidence-chain')).toBeInTheDocument();
    });

    it('renders all 5 evidence steps', () => {
      render(<DecisionEvidenceChain open={true} />);
      const steps = screen.getAllByTestId('evidence-step');
      expect(steps).toHaveLength(5);
    });

    it('displays step titles', () => {
      render(<DecisionEvidenceChain open={true} />);
      expect(screen.getByText('Data Foundation')).toBeInTheDocument();
      expect(screen.getByText('AI Prediction')).toBeInTheDocument();
      expect(screen.getByText('Verification')).toBeInTheDocument();
      expect(screen.getByText('Accountability')).toBeInTheDocument();
    });

    it('displays step data labels', () => {
      render(<DecisionEvidenceChain open={true} />);
      expect(screen.getByText('47 features ingested')).toBeInTheDocument();
      expect(screen.getByText('165 μg/m3 predicted at 6h horizon')).toBeInTheDocument();
    });

    it('displays the prototype disclaimer', () => {
      render(<DecisionEvidenceChain open={true} />);
      expect(screen.getByText(/Decision-support prototype/)).toBeInTheDocument();
    });
  });

  describe('Explicit steps prop', () => {
    it('renders steps from props when provided', () => {
      render(<DecisionEvidenceChain open={true} steps={DEMO_STEPS} />);
      expect(screen.getByTestId('evidence-chain')).toBeInTheDocument();
      expect(screen.getAllByTestId('evidence-step')).toHaveLength(5);
    });
  });

  describe('Closed state', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({
        evidenceChain: DEMO_STEPS,
      });
    });

    it('renders without the open class when closed', () => {
      const { container } = render(<DecisionEvidenceChain open={false} />);
      const evidenceChain = container.querySelector('.why-trust__evidence-container');
      expect(evidenceChain).toBeInTheDocument();
      expect(evidenceChain).not.toHaveClass('why-trust__evidence-container--open');
    });
  });

  describe('Production mode (no demo data, no props)', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('renders nothing when no data available', () => {
      const { container } = render(<DecisionEvidenceChain open={true} />);
      expect(container.innerHTML).toBe('');
    });
  });
});
