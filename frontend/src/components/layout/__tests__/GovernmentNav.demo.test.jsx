/**
 * GovernmentNav — Demo Mode Tests.
 *
 * Tests: navigation hardening, demo mode detection, de-emphasis behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

import { useDemoData } from '../../../demo';
import GovernmentNav from '../GovernmentNav';

function renderNav(demoData = null) {
  useDemoData.mockReturnValue(demoData);
  return render(
    <MemoryRouter initialEntries={['/government']}>
      <GovernmentNav />
    </MemoryRouter>
  );
}

describe('GovernmentNav — Demo Mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('adds gov-nav--demo class when in demo mode', () => {
    const { container } = renderNav({ demoStep: 1, setDemoStep: vi.fn() });
    const nav = container.querySelector('.gov-nav');
    expect(nav).toHaveClass('gov-nav--demo');
  });

  it('does not add gov-nav--demo class when not in demo mode', () => {
    const { container } = renderNav(null);
    const nav = container.querySelector('.gov-nav');
    expect(nav).not.toHaveClass('gov-nav--demo');
  });

  it('sets aria-disabled on non-Overview links in demo mode', () => {
    renderNav({ demoStep: 1, setDemoStep: vi.fn() });
    const incidentsLink = screen.getByText('Incidents').closest('a');
    expect(incidentsLink).toHaveAttribute('aria-disabled', 'true');
  });

  it('does not set aria-disabled on Overview link in demo mode', () => {
    renderNav({ demoStep: 1, setDemoStep: vi.fn() });
    const overviewLink = screen.getByText('Overview').closest('a');
    expect(overviewLink).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('renders all nav items regardless of demo mode', () => {
    renderNav({ demoStep: 1, setDemoStep: vi.fn() });
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Incidents')).toBeInTheDocument();
    expect(screen.getByText('Forecasts')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Replay')).toBeInTheDocument();
  });
});
