/**
 * ConfidenceCalibration — Regression Tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../../services/api', () => ({
  getHorizonComparison: vi.fn(),
}));

import ConfidenceCalibration from '../ConfidenceCalibration';
import { useDemoData } from '../../../demo';
import { getHorizonComparison } from '../../../services/api';

const DEMO_CALIBRATION = [
  { horizon: 1, algorithm: 'Ridge', confidence_level: 92, accuracy: 89, mae: 4.5, r_squared: 0.975, count: 312, assessment: 'GOOD', note: 'Confidence closely tracks accuracy' },
  { horizon: 6, algorithm: 'HGB', confidence_level: 78, accuracy: 71, mae: 14.45, r_squared: 0.823, count: 287, assessment: 'ACCEPTABLE', note: 'Slight overconfidence' },
  { horizon: 24, algorithm: 'Ridge', confidence_level: 65, accuracy: 52, mae: 17.97, r_squared: 0.703, count: 241, assessment: 'OVERCONFIDENT', note: 'Model claims more confidence than warranted' },
];

describe('ConfidenceCalibration', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ confidenceCalibrationTable: DEMO_CALIBRATION });
    });

    it('renders the calibration component', () => {
      render(<ConfidenceCalibration />);
      expect(screen.getByTestId('confidence-calibration')).toBeInTheDocument();
    });

    it('renders 3 horizon rows', () => {
      render(<ConfidenceCalibration />);
      expect(screen.getByTestId('calibration-row-1')).toBeInTheDocument();
      expect(screen.getByTestId('calibration-row-6')).toBeInTheDocument();
      expect(screen.getByTestId('calibration-row-24')).toBeInTheDocument();
    });

    it('displays assessment badges', () => {
      render(<ConfidenceCalibration />);
      expect(screen.getByText('GOOD')).toBeInTheDocument();
      expect(screen.getByText('ACCEPTABLE')).toBeInTheDocument();
      expect(screen.getByText('OVERCONFIDENT')).toBeInTheDocument();
    });

    it('displays MAE values', () => {
      render(<ConfidenceCalibration />);
      expect(screen.getByText('4.5 μg/m3')).toBeInTheDocument();
      expect(screen.getByText('14.45 μg/m3')).toBeInTheDocument();
    });

    it('makes zero backend API calls', () => {
      render(<ConfidenceCalibration />);
      expect(getHorizonComparison).not.toHaveBeenCalled();
    });

    it('shows explanation footer', () => {
      render(<ConfidenceCalibration />);
      expect(screen.getByText(/Good calibration means/)).toBeInTheDocument();
    });
  });

  describe('Production mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('shows loading state', () => {
      getHorizonComparison.mockReturnValue(new Promise(() => {}));
      render(<ConfidenceCalibration />);
      expect(screen.getByTestId('calibration-loading')).toBeInTheDocument();
    });

    it('shows error state on failure', async () => {
      getHorizonComparison.mockRejectedValue(new Error('fail'));
      render(<ConfidenceCalibration />);
      await vi.waitFor(() => {
        expect(screen.getByTestId('calibration-error')).toBeInTheDocument();
      });
    });
  });
});
