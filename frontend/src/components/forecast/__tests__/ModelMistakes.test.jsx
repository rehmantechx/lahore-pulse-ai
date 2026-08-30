/**
 * ModelMistakes — Regression Tests.
 *
 * Verifies:
 * - Demo mode renders mistakes with fixture data
 * - Demo mode makes zero backend API calls
 * - Production mode attempts to fetch from API
 * - Root cause explanations render
 * - Empty/error states handled
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

import ModelMistakes from '../ModelMistakes';
import { useDemoData } from '../../../demo';
import { getAccountabilityTimeline } from '../../../services/api';

const DEMO_MISTAKES = {
  mistakes: [
    {
      date: '2025-01-10',
      predicted: 120,
      actual: 185,
      error_percentage: '41.1',
      horizon: 24,
      root_cause: 'Model overconfident at 24h horizon — insufficient training data for rapid winter episodes',
      explanation: 'The 24h forecast underestimated a rapid episode buildup',
    },
    {
      date: '2025-01-08',
      predicted: 160,
      actual: 210,
      error_percentage: '25.0',
      horizon: 12,
      root_cause: 'Localized monitoring station outage — interpolation introduced error',
      explanation: 'Missing data from one station forced wider interpolation',
    },
    {
      date: '2025-01-05',
      predicted: 95,
      actual: 118,
      error_percentage: '24.2',
      horizon: 6,
      root_cause: 'Algorithm bias during rapid wind direction changes',
      explanation: 'Wind shifted mid-episode, shifting the pollution corridor',
    },
  ],
};

describe('ModelMistakes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ modelMistakes: DEMO_MISTAKES });
    });

    it('renders the mistakes component', () => {
      render(<ModelMistakes />);
      expect(screen.getByTestId('model-mistakes')).toBeInTheDocument();
    });

    it('renders 3 mistake cards', () => {
      render(<ModelMistakes />);
      expect(screen.getByTestId('mistake-card-0')).toBeInTheDocument();
      expect(screen.getByTestId('mistake-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('mistake-card-2')).toBeInTheDocument();
    });

    it('displays root cause explanations', () => {
      render(<ModelMistakes />);
      expect(screen.getByText(/overconfident at 24h horizon/)).toBeInTheDocument();
      expect(screen.getByText(/monitoring station outage/)).toBeInTheDocument();
      expect(screen.getByText(/wind direction changes/)).toBeInTheDocument();
    });

    it('displays error percentages', () => {
      render(<ModelMistakes />);
      expect(screen.getByText('41.1%')).toBeInTheDocument();
      expect(screen.getByText('25.0%')).toBeInTheDocument();
      expect(screen.getByText('24.2%')).toBeInTheDocument();
    });

    it('makes zero backend API calls in demo mode', () => {
      render(<ModelMistakes />);
      expect(getAccountabilityTimeline).not.toHaveBeenCalled();
    });

    it('shows transparency footer', () => {
      render(<ModelMistakes />);
      expect(screen.getByText(/Errors are shown transparently/)).toBeInTheDocument();
    });
  });

  describe('Production mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('shows loading state initially', () => {
      getAccountabilityTimeline.mockReturnValue(new Promise(() => {}));
      render(<ModelMistakes />);
      expect(screen.getByTestId('mistakes-loading')).toBeInTheDocument();
    });

    it('shows error state on API failure', async () => {
      getAccountabilityTimeline.mockRejectedValue(new Error('API error'));
      render(<ModelMistakes />);
      await vi.waitFor(() => {
        expect(screen.getByTestId('mistakes-error')).toBeInTheDocument();
      });
    });
  });
});
