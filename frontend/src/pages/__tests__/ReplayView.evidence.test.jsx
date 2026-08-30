/**
 * ReplayView — Phase 29 Evidence Panel Tests.
 *
 * Verifies the BEFORE/PREDICTION/AFTER/VERIFICATION/LESSON panel
 * renders when an episode is selected in demo mode.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';

/* ── Mocks ─────────────────────────────────────────────── */

vi.mock('../../demo', () => ({
  useDemoData: vi.fn(),
}));

vi.mock('../../hooks/useReplay', () => ({
  useReplay: vi.fn(),
}));

vi.mock('recharts', () => ({
  LineChart: ({ children }) => <div data-testid="mock-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  Area: () => null,
  ComposedChart: ({ children }) => <div>{children}</div>,
}));

import ReplayView from '../ReplayView';
import { useDemoData } from '../../demo';
import { useReplay } from '../../hooks/useReplay';

const DEMO_OBSERVATIONS = [
  { date: '2025-01-15', hour: 8, avg_value: 95 },
  { date: '2025-01-15', hour: 9, avg_value: 110 },
  { date: '2025-01-15', hour: 10, avg_value: 135 },
  { date: '2025-01-15', hour: 11, avg_value: 150 },
];

const DEMO_REPLAY = {
  episodes: [{ date: '2025-01-15', readings: 4, peak_pm25: 150, avg_pm25: 122.5 }],
  loadingEpisodes: false,
  episodeError: null,
  selectEpisode: vi.fn(),
  selectedEpisode: { date: '2025-01-15', readings: 4, peak_pm25: 150, avg_pm25: 122.5 },
  observations: DEMO_OBSERVATIONS,
  meta: { peak_value: 150, avg_value: 122.5, total_hours: 4, total_readings: 4 },
  loadingObs: false,
  obsError: null,
  currentIndex: 2,
  currentReading: { date: '2025-01-15', hour: 10, avg_value: 135 },
  isPlaying: false,
  playbackSpeed: 500,
  setPlaybackSpeed: vi.fn(),
  progress: 75,
  play: vi.fn(),
  pause: vi.fn(),
  reset: vi.fn(),
  goToIndex: vi.fn(),
  stepForward: vi.fn(),
  stepBackward: vi.fn(),
  episodeState: { state: 'episode', label: 'EPISODE' },
  pm25Level: { color: '#dc2626', label: 'Very Unhealthy' },
};

describe('ReplayView — Evidence Panel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useReplay.mockReturnValue(DEMO_REPLAY);
  });

  it('shows evidence panel when episode is selected in demo mode', () => {
    useDemoData.mockReturnValue({
      replayVerification: {
        '2025-01-15': { verified: 3, total: 4, trustRating: 'Strong', meanError: 8.2 },
      },
    });
    render(<ReplayView />);
    expect(screen.getByTestId('replay-evidence-panel')).toBeInTheDocument();
  });

  it('does not show evidence panel without demo data', () => {
    useDemoData.mockReturnValue(null);
    render(<ReplayView />);
    expect(screen.queryByTestId('replay-evidence-panel')).not.toBeInTheDocument();
  });

  it('displays Prediction label in evidence panel', () => {
    useDemoData.mockReturnValue({
      replayVerification: {},
    });
    render(<ReplayView />);
    expect(screen.getByText('Prediction')).toBeInTheDocument();
  });

  it('displays Verification data when available', () => {
    useDemoData.mockReturnValue({
      replayVerification: {
        '2025-01-15': { verified: 3, total: 4, trustRating: 'Strong', meanError: 8.2 },
      },
    });
    render(<ReplayView />);
    const panel = screen.getByTestId('replay-evidence-panel');
    expect(within(panel).getByText('3/4')).toBeInTheDocument();
    expect(within(panel).getByText('Strong trust rating')).toBeInTheDocument();
  });

  it('shows Lesson section in evidence panel', () => {
    useDemoData.mockReturnValue({
      replayVerification: {},
    });
    render(<ReplayView />);
    expect(screen.getByText('Lesson')).toBeInTheDocument();
  });

  it('does not show the episode list view when episode is selected', () => {
    useDemoData.mockReturnValue({
      replayVerification: {},
    });
    render(<ReplayView />);
    // When episode is selected, we see the replay header, not the episode list
    expect(screen.getByText(/Episode Replay/)).toBeInTheDocument();
    // The back button is visible in replay mode
    expect(screen.getByText(/← Back to episodes/)).toBeInTheDocument();
  });
});
