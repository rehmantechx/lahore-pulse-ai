/**
 * ModelSuccesses — Regression Tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../../services/api', () => ({
  getAccountabilityTimeline: vi.fn(),
}));

import ModelSuccesses from '../ModelSuccesses';
import { useDemoData } from '../../../demo';
import { getAccountabilityTimeline } from '../../../services/api';

const DEMO_SUCCESSES = {
  successes: [
    { date: '2025-01-12', predicted: 145, actual: 148, error_percentage: '2.3', horizon: 1, explanation: 'Short-term forecast closely matched observation' },
    { date: '2025-01-11', predicted: 132, actual: 128, error_percentage: '3.0', horizon: 1, explanation: 'Wind patterns well-captured by model' },
    { date: '2025-01-09', predicted: 155, actual: 150, error_percentage: '3.2', horizon: 3, explanation: 'Stable episode conditions predicted accurately' },
  ],
};

describe('ModelSuccesses', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ modelSuccesses: DEMO_SUCCESSES });
    });

    it('renders the successes component', () => {
      render(<ModelSuccesses />);
      expect(screen.getByTestId('model-successes')).toBeInTheDocument();
    });

    it('renders 3 success cards', () => {
      render(<ModelSuccesses />);
      expect(screen.getByTestId('success-card-0')).toBeInTheDocument();
      expect(screen.getByTestId('success-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('success-card-2')).toBeInTheDocument();
    });

    it('displays error percentages', () => {
      render(<ModelSuccesses />);
      expect(screen.getByText('2.3%')).toBeInTheDocument();
      expect(screen.getByText('3.0%')).toBeInTheDocument();
    });

    it('makes zero backend API calls', () => {
      render(<ModelSuccesses />);
      expect(getAccountabilityTimeline).not.toHaveBeenCalled();
    });
  });

  describe('Production mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('shows loading state', () => {
      getAccountabilityTimeline.mockReturnValue(new Promise(() => {}));
      render(<ModelSuccesses />);
      expect(screen.getByTestId('successes-loading')).toBeInTheDocument();
    });

    it('shows error state on failure', async () => {
      getAccountabilityTimeline.mockRejectedValue(new Error('fail'));
      render(<ModelSuccesses />);
      await vi.waitFor(() => {
        expect(screen.getByTestId('successes-error')).toBeInTheDocument();
      });
    });
  });
});
