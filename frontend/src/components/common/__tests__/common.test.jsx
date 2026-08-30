/**
 * Common Component Tests.
 *
 * Tests: SeverityBadge, DataFreshness, ErrorState, LoadingState.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SeverityBadge from '../SeverityBadge';
import DataFreshness from '../DataFreshness';
import ErrorState from '../ErrorState';
import LoadingState from '../LoadingState';
import { ApiError, NetworkError } from '../../../services/api';

// ── SeverityBadge ──────────────────────────────────────────────

describe('SeverityBadge', () => {
  it('renders "Good" for low PM2.5', () => {
    render(<SeverityBadge value={8} />);
    expect(screen.getByText('Good')).toBeInTheDocument();
  });

  it('renders "Moderate" for mid-range PM2.5', () => {
    render(<SeverityBadge value={30} />);
    expect(screen.getByText('Moderate')).toBeInTheDocument();
  });

  it('renders "Unhealthy" for high PM2.5', () => {
    render(<SeverityBadge value={75} />);
    expect(screen.getByText('Unhealthy')).toBeInTheDocument();
  });

  it('renders "Hazardous" for extreme PM2.5', () => {
    render(<SeverityBadge value={200} />);
    expect(screen.getByText('Hazardous')).toBeInTheDocument();
  });

  it('renders "Unknown" for null', () => {
    render(<SeverityBadge value={null} />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('has an aria-label with the full description', () => {
    render(<SeverityBadge value={30} />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('aria-label');
    expect(badge.getAttribute('aria-label')).toContain('Moderate');
  });

  it('applies small size variant', () => {
    render(<SeverityBadge value={8} size="sm" />);
    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
  });
});

// ── DataFreshness ──────────────────────────────────────────────

describe('DataFreshness', () => {
  it('renders with a timestamp', () => {
    render(<DataFreshness timestamp={new Date().toISOString()} freshnessHours={0.5} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/Data updated/i)).toBeInTheDocument();
  });

  it('shows "Degraded" badge when freshness is 2–6 hours', () => {
    render(<DataFreshness timestamp={new Date(Date.now() - 3 * 3600000).toISOString()} freshnessHours={3} />);
    expect(screen.getByText('Degraded')).toBeInTheDocument();
  });

  it('shows "Stale" badge when freshness is 6–12 hours', () => {
    render(<DataFreshness timestamp={new Date(Date.now() - 8 * 3600000).toISOString()} freshnessHours={8} />);
    expect(screen.getByText('Stale')).toBeInTheDocument();
  });

  it('shows "Unavailable" badge when freshness exceeds 12 hours', () => {
    render(<DataFreshness timestamp={new Date(Date.now() - 15 * 3600000).toISOString()} freshnessHours={15} />);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
  });

  it('renders with freshness state from backend', () => {
    render(
      <DataFreshness
        freshness={{ state: 'stale', freshness_hours: 7.5, latest_observation_at: new Date(Date.now() - 7.5 * 3600000).toISOString(), parameters_available: 4, warnings: ['Data is stale'] }}
      />
    );
    expect(screen.getByText('Stale')).toBeInTheDocument();
    expect(screen.getByText('Data is stale')).toBeInTheDocument();
  });

  it('shows "Unknown" when timestamp is null', () => {
    render(<DataFreshness timestamp={null} freshnessHours={null} />);
    expect(screen.getByText(/Unknown|ago/i)).toBeInTheDocument();
  });
});

// ── ErrorState ─────────────────────────────────────────────────

describe('ErrorState', () => {
  it('renders a retry button', () => {
    const onRetry = vi.fn();
    render(<ErrorState error={new Error('Something failed')} onRetry={onRetry} />);
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('calls onRetry when retry is clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorState error={new Error('fail')} onRetry={onRetry} />);
    screen.getByRole('button', { name: /try again/i }).click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders ApiError message', () => {
    const err = new ApiError(404, 'NOT_FOUND', 'Resource not found');
    render(<ErrorState error={err} />);
    expect(screen.getByText('Data not found')).toBeInTheDocument();
  });

  it('renders NetworkError message', () => {
    const err = new NetworkError('Cannot connect to server');
    render(<ErrorState error={err} />);
    expect(screen.getByText('Cannot reach the server')).toBeInTheDocument();
  });
});

// ── LoadingState ───────────────────────────────────────────────

describe('LoadingState', () => {
  it('renders a loading message', () => {
    render(<LoadingState message="Loading data…" />);
    expect(screen.getByText('Loading data…')).toBeInTheDocument();
  });

  it('renders skeleton placeholders', () => {
    const { container } = render(<LoadingState />);
    const skeletons = container.querySelectorAll('.skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
