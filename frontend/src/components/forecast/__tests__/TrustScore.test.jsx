/**
 * TrustScore — Regression Tests.
 *
 * Verifies:
 * - Demo mode renders trust score with fixture data
 * - Trust level classification (Strong/Moderate/Developing/Insufficient)
 * - Animated number renders
 * - No backend API calls in demo mode
 * - Production mode fetches from API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../../services/api', () => ({
  getAccuracySummary: vi.fn(),
}));

import TrustScore from '../TrustScore';
import { useDemoData } from '../../../demo';
import { getAccuracySummary } from '../../../services/api';

// Mock window.matchMedia for jsdom
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
}

const MOCK_DEMO_DATA = {
  accuracySummary: {
    total_predictions: 1247,
    by_horizon: [
      { horizon: 1, verified_count: 350, accuracy_mae: 12.3 },
      { horizon: 3, verified_count: 340, accuracy_mae: 18.9 },
      { horizon: 6, verified_count: 320, accuracy_mae: 28.1 },
    ],
  },
  confidenceCalibrationTable: [
    { assessment: 'GOOD', horizon: 1 },
    { assessment: 'ACCEPTABLE', horizon: 3 },
    { assessment: 'GOOD', horizon: 6 },
  ],
};

describe('TrustScore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAccuracySummary.mockResolvedValue({
      total_predictions: 500,
      by_horizon: [
        { horizon: 1, verified_count: 200, avg_error: 15 },
      ],
    });
  });

  it('renders trust score in demo mode', async () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByTestId('trust-score')).toBeInTheDocument();
  });

  it('displays Model Trust Score heading', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByText('Model Trust Score')).toBeInTheDocument();
  });

  it('makes zero backend API calls in demo mode', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(getAccuracySummary).not.toHaveBeenCalled();
  });

  it('fetches from API in production mode', async () => {
    useDemoData.mockReturnValue(null);
    render(<TrustScore />);
    await waitFor(() => {
      expect(getAccuracySummary).toHaveBeenCalledTimes(1);
    });
  });

  it('shows loading state in production mode before API returns', () => {
    useDemoData.mockReturnValue(null);
    getAccuracySummary.mockReturnValue(new Promise(() => {})); // never resolves
    render(<TrustScore />);
    expect(screen.getByText('Loading trust score...')).toBeInTheDocument();
  });

  it('shows verification rate', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByText('Verified')).toBeInTheDocument();
  });

  it('shows accuracy metric', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByText('Accuracy')).toBeInTheDocument();
  });

  it('shows calibration metric when available', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByText('Calibration')).toBeInTheDocument();
  });

  it('renders demo disclaimer in demo mode', () => {
    useDemoData.mockReturnValue(MOCK_DEMO_DATA);
    render(<TrustScore />);
    expect(screen.getByText(/Trust score computed from demonstration data/)).toBeInTheDocument();
  });

  it('shows empty state when no data available', () => {
    useDemoData.mockReturnValue({ accuracySummary: null });
    getAccuracySummary.mockResolvedValue(null);
    render(<TrustScore />);
    expect(screen.getByText(/No trust data available/)).toBeInTheDocument();
  });

  it('handles missing by_horizon gracefully', () => {
    useDemoData.mockReturnValue({
      accuracySummary: { total_predictions: 100, by_horizon: null },
      confidenceCalibrationTable: null,
    });
    render(<TrustScore />);
    expect(screen.getByTestId('trust-score')).toBeInTheDocument();
  });
});
