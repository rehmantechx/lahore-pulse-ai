/**
 * GovAnalyticsPage — ModelHealthStrip Tests (Phase 29).
 *
 * Verifies the compact 3-metric model-health strip:
 * accuracy trend, verification rate, calibration.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  getAccuracySummary: vi.fn(),
  getHorizonComparison: vi.fn(),
}));

vi.mock('../../components/forecast/HistoricalTrendChart', () => ({
  __esModule: true,
  default: () => <div data-testid="mock-trend" />,
}));

vi.mock('../../components/forecast/TrustScore', () => ({
  __esModule: true,
  default: () => <div data-testid="mock-trust" />,
}));

vi.mock('../../components/forecast/PredictionAccountability', () => ({
  __esModule: true,
  default: () => <div data-testid="mock-accountability" />,
}));

import GovAnalyticsPage from '../GovAnalyticsPage';
import { useDemoData } from '../../demo';

const DEMO_SUMMARY = {
  total_predictions: 200,
  by_horizon: [
    { horizon: 1, total_predictions: 100, verified_count: 80, avg_error: 8.5, max_error: 22.3 },
    { horizon: 3, total_predictions: 100, verified_count: 60, avg_error: 12.1, max_error: 35.7 },
  ],
};

const DEMO_COMPARISON = {
  count: 2,
  horizons: [
    { horizon: 1, avg_error: 8.5, accuracy_mae: 8.5, verified_count: 80 },
    { horizon: 3, avg_error: 12.1, accuracy_mae: 12.1, verified_count: 60 },
  ],
};

const DEMO_CALIBRATION = [
  { predicted_range: '0-50', within_band: true },
  { predicted_range: '50-100', within_band: true },
  { predicted_range: '100-150', within_band: false },
  { predicted_range: '150+', within_band: true },
];

describe('GovAnalyticsPage — ModelHealthStrip', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('With demo data', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({
        accuracySummary: DEMO_SUMMARY,
        horizonComparison: DEMO_COMPARISON,
        confidenceCalibrationTable: DEMO_CALIBRATION,
      });
    });

    it('renders the model health strip', () => {
      render(<GovAnalyticsPage />);
      expect(screen.getByTestId('model-health-strip')).toBeInTheDocument();
    });

    it('displays average error metric in health strip', () => {
      render(<GovAnalyticsPage />);
      const strip = screen.getByTestId('model-health-strip');
      expect(strip).toHaveTextContent('Avg Error');
      expect(strip).toHaveTextContent('10.3 μg/m³');
    });

    it('displays verification rate metric in health strip', () => {
      render(<GovAnalyticsPage />);
      const strip = screen.getByTestId('model-health-strip');
      expect(strip).toHaveTextContent('Verified');
      expect(strip).toHaveTextContent('70%');
    });

    it('displays calibration metric in health strip', () => {
      render(<GovAnalyticsPage />);
      const strip = screen.getByTestId('model-health-strip');
      expect(strip).toHaveTextContent('Calibration');
      expect(strip).toHaveTextContent('75%');
    });

    it('shows Model Health label in health strip', () => {
      render(<GovAnalyticsPage />);
      const strip = screen.getByTestId('model-health-strip');
      expect(strip).toHaveTextContent('Model Health');
    });
  });

  describe('Without data', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({
        accuracySummary: null,
        horizonComparison: null,
        confidenceCalibrationTable: null,
      });
    });

    it('shows insufficient data message', () => {
      render(<GovAnalyticsPage />);
      expect(screen.getByText(/Not enough verified observations/)).toBeInTheDocument();
    });
  });
});
