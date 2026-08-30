/**
 * HistoricalVerificationContext — Component tests.
 *
 * Tests: rendering with stats, no data, insufficient data threshold, current outcome.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import HistoricalVerificationContext from '../HistoricalVerificationContext';

// ── Mock data ────────────────────────────────────────────────

const STATS_SUFFICIENT = {
  total_verifications: 5,
  useful_count: 3,
  partially_useful_count: 1,
  not_supported_count: 0,
  inconclusive_count: 1,
  recommendation_supported_pct: 80,
  area_supported_pct: 60,
  hypothesis_hit_rate: 70,
};

const STATS_INSUFFICIENT = {
  total_verifications: 2,
  useful_count: 1,
  partially_useful_count: 0,
  not_supported_count: 0,
  inconclusive_count: 1,
  recommendation_supported_pct: null,
  area_supported_pct: null,
  hypothesis_hit_rate: null,
};

const CURRENT_OUTCOME = {
  outcome_id: 'vout-001',
  investigation_id: 'inv-001',
  overall_status: 'USEFUL',
  recommendation_verification: 'SUPPORTED',
  investigation_area_verification: 'PARTIALLY_SUPPORTED',
  hypothesis_verifications: [],
  field_notes: 'Confirmed industrial activity in corridor',
  verified_by: 'Officer Khan',
  verified_at: '2024-12-15T14:30:00Z',
};

// ── Tests ────────────────────────────────────────────────────

describe('HistoricalVerificationContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders no data message when stats is null', () => {
    render(<HistoricalVerificationContext stats={null} />);
    expect(screen.getByText('No verification data available yet.')).toBeInTheDocument();
  });

  it('renders verification header', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText('Verification Context')).toBeInTheDocument();
  });

  it('displays total verification count', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText('5 verified')).toBeInTheDocument();
  });

  it('displays status distribution counts', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText('3')).toBeInTheDocument(); // useful_count
    // '1' appears for both partially_useful and inconclusive counts
    expect(screen.getAllByText('1').length).toBe(2);
    // '0' appears for not_supported count
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(1);
  });

  it('shows percentage bars when sufficient data (>= 3)', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText('80%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
  });

  it('shows percentage bar labels', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText('Corridor recommendations supported')).toBeInTheDocument();
    expect(screen.getByText('Investigation areas verified')).toBeInTheDocument();
    expect(screen.getByText('Hypotheses verified')).toBeInTheDocument();
  });

  it('shows insufficient data message when < 3 verifications', () => {
    render(<HistoricalVerificationContext stats={STATS_INSUFFICIENT} />);
    expect(screen.getByText(/At least 3 verified investigations needed/)).toBeInTheDocument();
    expect(screen.getByText(/Currently 2 verified/)).toBeInTheDocument();
  });

  it('does not show percentage bars when insufficient data', () => {
    render(<HistoricalVerificationContext stats={STATS_INSUFFICIENT} />);
    expect(screen.queryByText('Corridor recommendations supported')).not.toBeInTheDocument();
  });

  it('displays current outcome when provided', () => {
    const { container } = render(
      <HistoricalVerificationContext
        stats={STATS_SUFFICIENT}
        currentOutcome={CURRENT_OUTCOME}
      />
    );
    expect(screen.getByText('Current Investigation Status')).toBeInTheDocument();
    // 'Useful' appears in both distribution label and outcome status badge
    const usefulElements = screen.getAllByText(/Useful/);
    expect(usefulElements.length).toBeGreaterThanOrEqual(2);
  });

  it('displays field notes in current outcome', () => {
    render(
      <HistoricalVerificationContext
        stats={STATS_SUFFICIENT}
        currentOutcome={CURRENT_OUTCOME}
      />
    );
    expect(screen.getByText(/Confirmed industrial activity/)).toBeInTheDocument();
  });

  it('displays custom disclaimer', () => {
    render(
      <HistoricalVerificationContext
        stats={STATS_SUFFICIENT}
        disclaimer="Custom disclaimer text"
      />
    );
    expect(screen.getByText('Custom disclaimer text')).toBeInTheDocument();
  });

  it('displays default disclaimer when none provided', () => {
    render(<HistoricalVerificationContext stats={STATS_SUFFICIENT} />);
    expect(screen.getByText(/Historical verification data provides context/)).toBeInTheDocument();
  });

  it('handles missing field_notes gracefully', () => {
    const outcomeNoNotes = { ...CURRENT_OUTCOME, field_notes: '' };
    render(
      <HistoricalVerificationContext
        stats={STATS_SUFFICIENT}
        currentOutcome={outcomeNoNotes}
      />
    );
    expect(screen.getByText('Current Investigation Status')).toBeInTheDocument();
  });
});
