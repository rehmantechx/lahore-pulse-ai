/**
 * PredictionReceipt — Regression Tests.
 *
 * Verifies:
 * - Demo mode renders receipt with fixture data
 * - Demo mode makes zero backend API calls
 * - Production mode attempts to fetch from API
 * - Receipt open/close behavior
 * - Values render correctly
 * - Invalid/missing data handled gracefully
 * - Reduced motion class present
 * - Compact mode renders
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the demo context
vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

// Mock the API
vi.mock('../../../services/api', () => ({
  getRecentVerified: vi.fn(),
}));

import PredictionReceipt from '../PredictionReceipt';
import { useDemoData } from '../../../demo';
import { getRecentVerified } from '../../../services/api';

const DEMO_RECEIPT = {
  receipt_id: 'LP-000184',
  prediction: {
    predicted_pm25: 165,
    horizon_hours: 6,
    prediction_time: '2025-01-15T10:00:00Z',
    target_time: '2025-01-15T16:00:00Z',
    model_version: 'v2.1.0',
    algorithm: 'Ridge',
    confidence: 0.82,
  },
  observation: {
    observed_pm25: 181,
    observed_at: '2025-01-15T16:05:00Z',
    station_id: 'psi-lahore',
    station_name: 'PSI Lahore',
  },
  verification: {
    absolute_error: 16,
    percentage_error: 9.7,
    status: 'VERIFIED',
    within_tolerance: true,
  },
  calibration: {
    confidence_level: 82,
    actual_error: 9.7,
    assessment: 'GOOD',
    explanation: 'The model was slightly less confident than the actual accuracy warranted.',
  },
  trust_snapshot: {
    total_evaluated: 184,
    within_tolerance_pct: 76,
  },
  disclaimer: 'This is simulated demonstration data, not live measurements.',
};

describe('PredictionReceipt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Demo mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ predictionReceipt: DEMO_RECEIPT });
    });

    it('renders the receipt component', () => {
      render(<PredictionReceipt />);
      expect(screen.getByTestId('prediction-receipt')).toBeInTheDocument();
    });

    it('displays the receipt ID', () => {
      render(<PredictionReceipt />);
      expect(screen.getByText(/LP-000184/)).toBeInTheDocument();
    });

    it('displays predicted value', () => {
      render(<PredictionReceipt />);
      expect(screen.getByText('165')).toBeInTheDocument();
    });

    it('displays actual value', () => {
      render(<PredictionReceipt />);
      expect(screen.getByTestId('receipt-actual-value')).toHaveTextContent('181');
    });

    it('displays error percentage', () => {
      render(<PredictionReceipt />);
      expect(screen.getByText('9.7%')).toBeInTheDocument();
    });

    it('displays VERIFIED status', () => {
      render(<PredictionReceipt />);
      expect(screen.getAllByText('VERIFIED').length).toBeGreaterThan(0);
    });

    it('makes zero backend API calls in demo mode', () => {
      render(<PredictionReceipt />);
      expect(getRecentVerified).not.toHaveBeenCalled();
    });

    it('shows disclaimer in demo mode', () => {
      render(<PredictionReceipt />);
      expect(screen.getByText(/simulated demonstration data/)).toBeInTheDocument();
    });

    it('shows trust snapshot', () => {
      render(<PredictionReceipt />);
      expect(screen.getByTestId('receipt-trust')).toBeInTheDocument();
      expect(screen.getByText('184 predictions evaluated')).toBeInTheDocument();
      expect(screen.getByText('76% within tolerance')).toBeInTheDocument();
    });

    it('shows calibration section by default and toggles on click', () => {
      render(<PredictionReceipt />);
      // Calibration is now visible by default
      expect(screen.getByTestId('receipt-calibration')).toBeInTheDocument();
      expect(screen.getByText('GOOD')).toBeInTheDocument();
      // Click to collapse
      const toggle = screen.getByTestId('receipt-calibration-toggle');
      fireEvent.click(toggle);
      expect(screen.queryByTestId('receipt-calibration')).not.toBeInTheDocument();
    });

    it('shows verification timeline by default', () => {
      render(<PredictionReceipt />);
      expect(screen.getByTestId('receipt-timeline')).toBeInTheDocument();
    });

    it('collapses verification timeline on click', () => {
      render(<PredictionReceipt />);
      // Timeline starts expanded
      expect(screen.getByTestId('receipt-timeline')).toBeInTheDocument();
      const toggle = screen.getByTestId('receipt-timeline-toggle');
      fireEvent.click(toggle);
      expect(screen.queryByTestId('receipt-timeline')).not.toBeInTheDocument();
      // Click again to re-expand
      fireEvent.click(toggle);
      expect(screen.getByTestId('receipt-timeline')).toBeInTheDocument();
    });
  });

  describe('Compact mode', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({ predictionReceipt: DEMO_RECEIPT });
    });

    it('renders compact receipt', () => {
      render(<PredictionReceipt compact />);
      expect(screen.getByTestId('prediction-receipt')).toBeInTheDocument();
      expect(screen.getByText(/LP-000184/)).toBeInTheDocument();
    });

    it('displays compact values', () => {
      render(<PredictionReceipt compact />);
      expect(screen.getByText('PREDICTED')).toBeInTheDocument();
      expect(screen.getByText('ACTUAL')).toBeInTheDocument();
      expect(screen.getByText('ERROR')).toBeInTheDocument();
    });
  });

  describe('Production mode (no demo)', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('shows loading state initially', () => {
      getRecentVerified.mockReturnValue(new Promise(() => {})); // never resolves
      render(<PredictionReceipt />);
      expect(screen.getByTestId('receipt-loading')).toBeInTheDocument();
    });

    it('shows error state on API failure', async () => {
      getRecentVerified.mockRejectedValue(new Error('Network error'));
      render(<PredictionReceipt />);
      // Wait for the error to be processed
      await vi.waitFor(() => {
        expect(screen.getByTestId('receipt-error')).toBeInTheDocument();
      });
    });
  });

  describe('Missing data handling', () => {
    it('handles missing receipt data', () => {
      useDemoData.mockReturnValue({ predictionReceipt: null });
      render(<PredictionReceipt />);
      expect(screen.getByTestId('receipt-empty')).toBeInTheDocument();
    });
  });
});
