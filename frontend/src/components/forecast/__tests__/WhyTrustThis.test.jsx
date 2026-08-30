/**
 * WhyTrustThis — Regression Tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../../services/api', () => ({
  getAccuracySummary: vi.fn(),
}));

import WhyTrustThis from '../WhyTrustThis';
import { useDemoData } from '../../../demo';
import { getAccuracySummary } from '../../../services/api';

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

describe('WhyTrustThis', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ whyTrust: DEMO_TRUST });
    });

    it('renders the trust component', () => {
      render(<WhyTrustThis />);
      expect(screen.getByTestId('why-trust')).toBeInTheDocument();
    });

    it('renders 5 trust signals', () => {
      render(<WhyTrustThis />);
      expect(screen.getByTestId('trust-signal-0')).toBeInTheDocument();
      expect(screen.getByTestId('trust-signal-4')).toBeInTheDocument();
    });

    it('displays key trust stats', () => {
      render(<WhyTrustThis />);
      expect(screen.getByText('184 predictions evaluated')).toBeInTheDocument();
      expect(screen.getByText('76% within tolerance')).toBeInTheDocument();
    });

    it('shows transparency, accountability, and verification principles', () => {
      render(<WhyTrustThis />);
      expect(screen.getByText('Transparency')).toBeInTheDocument();
      expect(screen.getByText('Accountability')).toBeInTheDocument();
      expect(screen.getByText('Verification')).toBeInTheDocument();
    });

    it('makes zero backend API calls', () => {
      render(<WhyTrustThis />);
      expect(getAccuracySummary).not.toHaveBeenCalled();
    });

    it('shows footer note', () => {
      render(<WhyTrustThis />);
      expect(screen.getByText(/designed to be wrong in ways you can catch/)).toBeInTheDocument();
    });
  });

  describe('Production mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('shows loading state', () => {
      getAccuracySummary.mockReturnValue(new Promise(() => {}));
      render(<WhyTrustThis />);
      expect(screen.getByTestId('why-trust-loading')).toBeInTheDocument();
    });

    it('shows error state on failure', async () => {
      getAccuracySummary.mockRejectedValue(new Error('fail'));
      render(<WhyTrustThis />);
      await vi.waitFor(() => {
        expect(screen.getByTestId('why-trust-error')).toBeInTheDocument();
      });
    });
  });
});
