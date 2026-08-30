/**
 * Forecast Component Tests.
 *
 * Tests: ForecastCard, ForecastTimeline.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ForecastCard from '../ForecastCard';
import ForecastTimeline from '../ForecastTimeline';

// Mock react-router-dom NavLink for ForecastCard (which doesn't use it directly)
// but the parent may. For ForecastCard tests we don't need router context.

describe('ForecastCard', () => {
  const mockOnSelect = vi.fn();

  beforeEach(() => {
    mockOnSelect.mockClear();
  });

  it('renders horizon label', () => {
    render(
      <ForecastCard
        horizon={1}
        forecast={{ predicted_pm25: 35.2 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText('1h')).toBeInTheDocument();
  });

  it('renders predicted PM2.5 value', () => {
    render(
      <ForecastCard
        horizon={3}
        forecast={{ predicted_pm25: 40.1 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText('40.1')).toBeInTheDocument();
  });

  it('renders "No data" when forecast is null', () => {
    render(
      <ForecastCard
        horizon={6}
        forecast={null}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('renders "Unavailable" when forecast has errors', () => {
    render(
      <ForecastCard
        horizon={12}
        forecast={{ errors: ['Model not found'], predicted_pm25: null }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    render(
      <ForecastCard
        horizon={6}
        forecast={{ predicted_pm25: 42.0 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(mockOnSelect).toHaveBeenCalledWith(6);
  });

  it('applies selected class when isSelected is true', () => {
    render(
      <ForecastCard
        horizon={1}
        forecast={{ predicted_pm25: 35.0 }}
        isSelected={true}
        onSelect={mockOnSelect}
      />
    );
    const button = screen.getByRole('button');
    expect(button.className).toContain('forecast-card--selected');
  });

  it('has correct aria-label with PM2.5 value', () => {
    render(
      <ForecastCard
        horizon={1}
        forecast={{ predicted_pm25: 35.2 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    const button = screen.getByRole('button');
    expect(button.getAttribute('aria-label')).toContain('35.2');
  });

  it('shows reliability text', () => {
    render(
      <ForecastCard
        horizon={1}
        forecast={{ predicted_pm25: 35.0 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText(/Strong historical validation/)).toBeInTheDocument();
  });

  it('shows lower confidence for 24h horizon', () => {
    render(
      <ForecastCard
        horizon={24}
        forecast={{ predicted_pm25: 38.0 }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText(/Greater uncertainty/)).toBeInTheDocument();
  });

  it('shows target time when available', () => {
    render(
      <ForecastCard
        horizon={6}
        forecast={{ predicted_pm25: 42.0, timing: { target_time: '2025-01-15T20:30:00Z' } }}
        isSelected={false}
        onSelect={mockOnSelect}
      />
    );
    expect(screen.getByText(/Target/)).toBeInTheDocument();
  });
});

describe('ForecastTimeline', () => {
  const mockOnSelect = vi.fn();
  const forecasts = {
    '1': { predicted_pm25: 35.2 },
    '3': { predicted_pm25: 40.1 },
    '6': { predicted_pm25: 42.0 },
    '12': { predicted_pm25: 45.5 },
    '24': { predicted_pm25: 38.0 },
  };

  beforeEach(() => {
    mockOnSelect.mockClear();
  });

  it('renders all 5 horizon cards', () => {
    render(
      <ForecastTimeline
        forecasts={forecasts}
        selectedHorizon={1}
        onSelectHorizon={mockOnSelect}
      />
    );
    expect(screen.getByText('1h')).toBeInTheDocument();
    expect(screen.getByText('3h')).toBeInTheDocument();
    expect(screen.getByText('6h')).toBeInTheDocument();
    expect(screen.getByText('12h')).toBeInTheDocument();
    expect(screen.getByText('24h')).toBeInTheDocument();
  });

  it('has group role with aria-label', () => {
    render(
      <ForecastTimeline
        forecasts={forecasts}
        selectedHorizon={null}
        onSelectHorizon={mockOnSelect}
      />
    );
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', 'Forecast horizons');
  });

  it('renders 5 buttons', () => {
    render(
      <ForecastTimeline
        forecasts={forecasts}
        selectedHorizon={null}
        onSelectHorizon={mockOnSelect}
      />
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(5);
  });

  it('passes null forecast for missing horizons', () => {
    render(
      <ForecastTimeline
        forecasts={{ '1': { predicted_pm25: 35.0 } }}
        selectedHorizon={1}
        onSelectHorizon={mockOnSelect}
      />
    );
    // 4 cards should show "No data"
    const noData = screen.getAllByText('No data');
    expect(noData).toHaveLength(4);
  });
});
