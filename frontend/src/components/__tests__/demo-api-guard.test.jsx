/**
 * Demo-Mode API Guard Tests.
 *
 * Verifies that 4 below-fold components do NOT make real API requests
 * when in demo mode, and DO make them in production mode.
 *
 * Components:
 *   - TrustSnapshot (getAccuracySummary)
 *   - HistoricalTrendChart (getStationHistory)
 *   - PredictionAccountability (getAccountabilityTimeline)
 *   - TechnicalDeepDive > AccountabilityTab (getAccountabilityTimeline)
 *
 * Phase 15: Demo Reliability & Judge-Ready Audit
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

/* ── Mocks ─────────────────────────────────────────────── */

const mockGetAccuracySummary = vi.fn();
const mockGetStationHistory = vi.fn();
const mockGetAccountabilityTimeline = vi.fn();
const mockTriggerVerification = vi.fn();

vi.mock('../../services/api', () => ({
  getAccuracySummary: (...args) => mockGetAccuracySummary(...args),
  getStationHistory: (...args) => mockGetStationHistory(...args),
  getAccountabilityTimeline: (...args) => mockGetAccountabilityTimeline(...args),
  triggerVerification: (...args) => mockTriggerVerification(...args),
  getRecentVerified: vi.fn().mockResolvedValue({ predictions: [] }),
}));

/* Leaflet / Recharts stubs to avoid heavy rendering */
vi.mock('leaflet', () => ({}));
vi.mock('leaflet/dist/leaflet.css', () => ({}));

/* Mock demo module (default: non-demo) */
vi.mock('../../demo', () => ({
  useDemoData: vi.fn(() => null),
}));

import { useDemoData } from '../../demo';
import { AuthProvider } from '../../contexts/AuthContext.jsx';

/* ── Components under test ─────────────────────────────── */

import TrustSnapshot from '../incident/TrustSnapshot';
import HistoricalTrendChart from '../forecast/HistoricalTrendChart';
import PredictionAccountability from '../forecast/PredictionAccountability';
import TechnicalDeepDive from '../forecast/TechnicalDeepDive';

/* ── Helpers ───────────────────────────────────────────── */

const DEMO_ACCURACY_SUMMARY = {
  total_predictions: 100,
  verified: 80,
  awaiting_verification: 20,
  verification_rate: 80,
  by_horizon: [],
};

const DEMO_DATA_MOCK = {
  accuracySummary: DEMO_ACCURACY_SUMMARY,
  forecastStatus: { freshness: { state: 'fresh' } },
};

function wrapInDemoMode(ui) {
  useDemoData.mockReturnValue(DEMO_DATA_MOCK);
  return render(<AuthProvider>{ui}</AuthProvider>);
}

function wrapInProductionMode(ui) {
  useDemoData.mockReturnValue(null);
  return render(<AuthProvider>{ui}</AuthProvider>);
}

/* ── Tests ─────────────────────────────────────────────── */

describe('Demo-Mode API Guards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useDemoData.mockReturnValue(null);
  });

  /* ── TrustSnapshot ──────────────────────────────────── */

  describe('TrustSnapshot', () => {
    it('does NOT call getAccuracySummary in demo mode', async () => {
      wrapInDemoMode(
        <TrustSnapshot horizon={1} forecastStatus={{ freshness: { state: 'fresh' } }} />
      );
      await waitFor(() => {
        expect(mockGetAccuracySummary).not.toHaveBeenCalled();
      });
    });

    it('DOES call getAccuracySummary in production mode', async () => {
      mockGetAccuracySummary.mockResolvedValue({ total_predictions: 0 });
      wrapInProductionMode(
        <TrustSnapshot horizon={1} forecastStatus={{ freshness: { state: 'fresh' } }} />
      );
      await waitFor(() => {
        expect(mockGetAccuracySummary).toHaveBeenCalled();
      });
    });

    it('renders without crashing in demo mode', () => {
      wrapInDemoMode(
        <TrustSnapshot horizon={1} forecastStatus={{ freshness: { state: 'fresh' } }} />
      );
      expect(screen.getByText('Trust Snapshot')).toBeInTheDocument();
    });
  });

  /* ── HistoricalTrendChart ───────────────────────────── */

  describe('HistoricalTrendChart', () => {
    it('does NOT call getStationHistory in demo mode', async () => {
      wrapInDemoMode(<HistoricalTrendChart />);
      await waitFor(() => {
        expect(mockGetStationHistory).not.toHaveBeenCalled();
      });
    });

    it('DOES call getStationHistory in production mode', async () => {
      mockGetStationHistory.mockResolvedValue({ observations: [] });
      wrapInProductionMode(<HistoricalTrendChart />);
      await waitFor(() => {
        expect(mockGetStationHistory).toHaveBeenCalled();
      });
    });

    it('generates demo observations in demo mode (no API call)', () => {
      wrapInDemoMode(<HistoricalTrendChart />);
      expect(screen.getByText(/PM2\.5 observations from ground stations/)).toBeInTheDocument();
    });
  });

  /* ── PredictionAccountability ───────────────────────── */

  describe('PredictionAccountability', () => {
    it('does NOT call getAccountabilityTimeline in demo mode when expanded', async () => {
      wrapInDemoMode(<PredictionAccountability />);
      fireEvent.click(screen.getByText(/Prediction Accountability/i));
      await waitFor(() => {
        expect(mockGetAccountabilityTimeline).not.toHaveBeenCalled();
      });
    });

    it('DOES call getAccountabilityTimeline in production mode when expanded', async () => {
      mockGetAccountabilityTimeline.mockResolvedValue({ timeline: [], summary: null });
      wrapInProductionMode(<PredictionAccountability />);
      fireEvent.click(screen.getByText(/Prediction Accountability/i));
      await waitFor(() => {
        expect(mockGetAccountabilityTimeline).toHaveBeenCalled();
      });
    });

    it('does NOT call triggerVerification when Verify Now clicked in demo mode', async () => {
      wrapInDemoMode(<PredictionAccountability />);
      fireEvent.click(screen.getByText(/Prediction Accountability/i));
      const verifyBtn = screen.getByText(/Verify Now/i);
      fireEvent.click(verifyBtn);
      await waitFor(() => {
        expect(mockTriggerVerification).not.toHaveBeenCalled();
      });
    });

    it('renders without crashing in demo mode', () => {
      wrapInDemoMode(<PredictionAccountability />);
      expect(screen.getByText(/Prediction Accountability/i)).toBeInTheDocument();
    });
  });

  /* ── TechnicalDeepDive > AccountabilityTab ──────────── */

  describe('TechnicalDeepDive — AccountabilityTab', () => {
    it('does NOT call getAccountabilityTimeline in demo mode when tab opened', async () => {
      wrapInDemoMode(<TechnicalDeepDive forecastStatus={{}} horizon={1} />);
      // Open the deep dive
      fireEvent.click(screen.getByText('Technical Deep Dive'));
      // Switch to Accountability tab
      fireEvent.click(screen.getByText('Accountability'));
      await waitFor(() => {
        expect(mockGetAccountabilityTimeline).not.toHaveBeenCalled();
      });
    });

    it('DOES call getAccountabilityTimeline in production mode when tab opened', async () => {
      mockGetAccountabilityTimeline.mockResolvedValue({ timeline: [], summary: null });
      wrapInProductionMode(<TechnicalDeepDive forecastStatus={{}} horizon={1} />);
      // Open the deep dive
      fireEvent.click(screen.getByText('Technical Deep Dive'));
      // Switch to Accountability tab
      fireEvent.click(screen.getByText('Accountability'));
      await waitFor(() => {
        expect(mockGetAccountabilityTimeline).toHaveBeenCalled();
      });
    });

    it('renders without crashing in demo mode', () => {
      wrapInDemoMode(<TechnicalDeepDive forecastStatus={{}} horizon={1} />);
      expect(screen.getByText('Technical Deep Dive')).toBeInTheDocument();
    });
  });
});
