/**
 * InvestigationLearning — Component tests.
 *
 * Tests: rendering states, reliability section, similar cases, limitations,
 * framing safety, expandable cards, evidence status badges.
 *
 * Design Rules tested:
 * - Minimum 3 verified cases before showing percentage statistics
 * - Language: "Similar previously verified investigations showed..." NOT "The AI learned..."
 * - Every response contains limitations
 * - Historical verification is context only
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import InvestigationLearning from '../InvestigationLearning';

// ── Mock data ────────────────────────────────────────────────

const FULL_LEARNING = {
  historical_investigations_found: 8,
  verified_outcomes: {
    total: 8,
    useful: 5,
    partially_useful: 2,
    not_supported: 1,
    inconclusive: 0,
    pending: 0,
  },
  recommendation_reliability: {
    score: 0.79,
    classification: 'MODERATE',
    description: 'Based on 8 similar verified investigations.',
    useful_count: 5,
    partially_useful_count: 2,
    not_supported_count: 1,
    inconclusive_count: 0,
    total_evaluated: 8,
  },
  similar_cases: [
    {
      investigation_id: 'INV-2024-001',
      outcome_id: 'VER-001',
      similarity_score: 0.87,
      date: '2024-09-15',
      overall_status: 'USEFUL',
      recommendation_verification: 'SUPPORTED',
      summary: 'Similar PM2.5 episode with industrial corridor pattern.',
      matching_dimensions: ['pm25_severity_band', 'wind_sector', 'trajectory'],
      differing_dimensions: ['temperature_band'],
    },
    {
      investigation_id: 'INV-2024-003',
      outcome_id: 'VER-003',
      similarity_score: 0.72,
      date: '2024-08-22',
      overall_status: 'PARTIALLY_USEFUL',
      recommendation_verification: 'PARTIALLY_SUPPORTED',
      summary: 'Similar wind conditions but different primary source.',
      matching_dimensions: ['pm25_severity_band', 'wind_speed_band'],
      differing_dimensions: ['wind_sector', 'investigation_corridor'],
    },
  ],
  limitations: [
    'Historical context is not a guarantee of future outcomes.',
    'Based on 8 verified cases from a limited geographic area.',
    'Similarity matching is deterministic, not a prediction.',
  ],
  evidence_status: 'MODERATE',
  historical_context_message: 'Similar previously verified investigations with matching PM2.5 and wind patterns showed that targeted ground-level monitoring improved source identification accuracy.',
  disclaimer: 'This context is derived from verified historical investigations for accountability purposes. It does not constitute a guarantee.',
};

const INSUFFICIENT_LEARNING = {
  historical_investigations_found: 2,
  verified_outcomes: { total: 2, useful: 1, partially_useful: 1, not_supported: 0, inconclusive: 0, pending: 0 },
  recommendation_reliability: { score: null, classification: 'INSUFFICIENT', description: 'Not enough data.', useful_count: 1, partially_useful_count: 1, not_supported_count: 0, inconclusive_count: 0, total_evaluated: 2 },
  similar_cases: [],
  limitations: ['Minimum 3 verified cases needed for reliability statistics.'],
  evidence_status: 'INSUFFICIENT',
  historical_context_message: '',
  disclaimer: 'Not enough historical data for context.',
};

// ── Tests ────────────────────────────────────────────────────

describe('InvestigationLearning', () => {
  it('renders loading state', () => {
    render(<InvestigationLearning learning={null} loading={true} error={null} />);
    expect(screen.getByText('Investigation Accountability')).toBeInTheDocument();
    expect(screen.getByText(/Loading historical context/)).toBeInTheDocument();
  });

  it('renders error state', () => {
    render(<InvestigationLearning learning={null} loading={false} error={new Error('network')} />);
    expect(screen.getByText('Investigation Accountability')).toBeInTheDocument();
    expect(screen.getByText(/temporarily unavailable/)).toBeInTheDocument();
  });

  it('renders no data state', () => {
    render(<InvestigationLearning learning={null} loading={false} error={null} />);
    expect(screen.getByText(/No historical investigation data available/)).toBeInTheDocument();
  });

  it('renders full learning data with evidence badge', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    expect(screen.getByTestId('evidence-status')).toHaveTextContent('MODERATE');
    expect(screen.getByTestId('case-count')).toHaveTextContent('8 historical cases');
  });

  it('renders reliability section with score and breakdown', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const section = screen.getByTestId('reliability-section');
    expect(section).toBeInTheDocument();
    expect(screen.getByTestId('reliability-classification')).toHaveTextContent('MODERATE');
    expect(screen.getByTestId('reliability-score')).toHaveTextContent('79%');
    // Breakdown counts — use getAllByText since "Useful" also appears in case statuses
    const usefulElements = screen.getAllByText('Useful');
    expect(usefulElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Partially')).toBeInTheDocument();
    expect(screen.getByText('Not Supported')).toBeInTheDocument();
  });

  it('does not render reliability section when data is insufficient', () => {
    render(<InvestigationLearning learning={INSUFFICIENT_LEARNING} loading={false} error={null} />);
    expect(screen.queryByTestId('reliability-section')).not.toBeInTheDocument();
  });

  it('shows insufficient data warning when < 3 cases', () => {
    render(<InvestigationLearning learning={INSUFFICIENT_LEARNING} loading={false} error={null} />);
    expect(screen.getByText(/At least 3 verified investigations needed/)).toBeInTheDocument();
  });

  it('renders similar cases', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const cases = screen.getAllByTestId('similar-case');
    expect(cases).toHaveLength(2);
    expect(screen.getByText('INV-2024-001')).toBeInTheDocument();
    expect(screen.getByText('INV-2024-003')).toBeInTheDocument();
  });

  it('renders similarity scores on case cards', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const scores = screen.getAllByTestId('similarity-score');
    expect(scores[0]).toHaveTextContent('87%');
    expect(scores[1]).toHaveTextContent('72%');
  });

  it('case card expand/collapse works', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    // Details should not be visible initially
    expect(screen.queryByText('Recommendation verification:')).not.toBeInTheDocument();

    // Click expand button
    const expandButtons = screen.getAllByText('More detail');
    fireEvent.click(expandButtons[0]);

    // Details should now be visible
    expect(screen.getByText('Recommendation verification:')).toBeInTheDocument();
    expect(screen.getByText('Outcome ID:')).toBeInTheDocument();
  });

  it('renders limitations section', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const section = screen.getByTestId('limitations');
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/not a guarantee/)).toBeInTheDocument();
    expect(screen.getByText(/8 verified cases/)).toBeInTheDocument();
    expect(screen.getByText(/deterministic, not a prediction/)).toBeInTheDocument();
  });

  it('renders disclaimer', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const disclaimer = screen.getByTestId('disclaimer');
    expect(disclaimer).toHaveTextContent('accountability purposes');
    expect(disclaimer).toHaveTextContent('does not constitute a guarantee');
  });

  it('renders context message', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const msg = screen.getByTestId('context-message');
    expect(msg).toHaveTextContent('Similar previously verified investigations');
  });

  it('framing does NOT contain "AI learned"', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const container = screen.getByTestId('investigation-learning');
    const text = container.textContent.toLowerCase();
    expect(text).not.toMatch(/ai learned/);
    expect(text).not.toMatch(/machine learning/);
    expect(text).not.toMatch(/the model learned/);
    expect(text).not.toMatch(/neural network/);
  });

  it('framing uses correct language "Similar previously verified investigations"', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    expect(screen.getByText(/Similar previously verified investigations/)).toBeInTheDocument();
  });

  it('renders correct status icons for similar cases', () => {
    render(<InvestigationLearning learning={FULL_LEARNING} loading={false} error={null} />);
    const statuses = screen.getAllByTestId('case-status');
    expect(statuses[0]).toHaveTextContent('Useful');
    expect(statuses[1]).toHaveTextContent('Partially Useful');
  });
});
