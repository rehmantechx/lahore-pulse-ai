/**
 * WhyTrustThis — Expandable Evidence Chain Tests (Phase 29).
 *
 * Verifies that clicking the evidence chain toggle shows/hides
 * the DecisionEvidenceChain component below the trust signals.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../../services/api', () => ({
  getAccuracySummary: vi.fn(),
}));

vi.mock('../DecisionEvidenceChain', () => ({
  __esModule: true,
  default: function MockDecisionEvidenceChain({ open }) {
    return open ? <div data-testid="mock-evidence-chain">Evidence Chain</div> : null;
  },
}));

import WhyTrustThis from '../WhyTrustThis';
import { useDemoData } from '../../../demo';

const DEMO_TRUST = {
  total_evaluated: 184,
  within_tolerance_pct: 76,
  calibration_status: 'ACCEPTABLE',
  signals: [
    '184 predictions evaluated',
    '76% within tolerance',
    'Confidence tracked against outcomes',
    'Forecasts independently verified after target time',
    'Errors remain visible',
  ],
};

describe('WhyTrustThis — Evidence Chain Expansion', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ whyTrust: DEMO_TRUST });
    });

    it('does not show evidence chain initially', () => {
      render(<WhyTrustThis />);
      expect(screen.queryByTestId('mock-evidence-chain')).not.toBeInTheDocument();
    });

    it('shows expand toggle button', () => {
      render(<WhyTrustThis />);
      expect(screen.getByTestId('evidence-chain-toggle')).toBeInTheDocument();
    });

    it('shows evidence chain when toggle clicked', () => {
      render(<WhyTrustThis />);
      fireEvent.click(screen.getByTestId('evidence-chain-toggle'));
      expect(screen.getByTestId('mock-evidence-chain')).toBeInTheDocument();
    });

    it('hides evidence chain when toggle clicked again', () => {
      render(<WhyTrustThis />);
      const toggle = screen.getByTestId('evidence-chain-toggle');
      fireEvent.click(toggle);
      expect(screen.getByTestId('mock-evidence-chain')).toBeInTheDocument();
      fireEvent.click(toggle);
      expect(screen.queryByTestId('mock-evidence-chain')).not.toBeInTheDocument();
    });

    it('toggle aria-expanded changes on click', () => {
      render(<WhyTrustThis />);
      const toggle = screen.getByTestId('evidence-chain-toggle');
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
      fireEvent.click(toggle);
      expect(toggle).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
