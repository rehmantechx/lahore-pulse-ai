/**
 * Navbar Component Tests.
 *
 * Tests: brand identity, navigation links, connection status.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Navbar from '../Navbar';

// Mock useHealth hook
vi.mock('../../../hooks/useHealth', () => ({
  useHealth: vi.fn(),
}));

import { useHealth } from '../../../hooks/useHealth';

function renderNavbar(route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Navbar />
    </MemoryRouter>
  );
}

describe('Navbar', () => {
  beforeEach(() => {
    vi.mocked(useHealth).mockReturnValue({
      online: true,
      loading: false,
      status: { status: 'ready' },
      refresh: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders brand text "Lahore Pulse"', () => {
    renderNavbar();
    expect(screen.getByText('Lahore Pulse')).toBeInTheDocument();
  });

  it('renders brand icon "LP"', () => {
    renderNavbar();
    expect(screen.getByText('LP')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderNavbar();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Citizen')).toBeInTheDocument();
    expect(screen.getByText('Command Center')).toBeInTheDocument();
  });

  it('has banner role', () => {
    renderNavbar();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('has navigation role with aria-label', () => {
    renderNavbar();
    const nav = screen.getByRole('navigation');
    expect(nav).toHaveAttribute('aria-label', 'Main navigation');
  });

  it('shows online status dot when backend is up', () => {
    renderNavbar();
    const dot = document.querySelector('.status-dot--online');
    expect(dot).toBeInTheDocument();
  });

  it('shows offline status dot when backend is down', () => {
    vi.mocked(useHealth).mockReturnValue({
      online: false,
      loading: false,
      status: null,
      refresh: vi.fn(),
    });
    renderNavbar();
    const dot = document.querySelector('.status-dot--offline');
    expect(dot).toBeInTheDocument();
  });

  it('shows loading status dot while checking health', () => {
    vi.mocked(useHealth).mockReturnValue({
      online: false,
      loading: true,
      status: null,
      refresh: vi.fn(),
    });
    renderNavbar();
    const dot = document.querySelector('.status-dot--loading');
    expect(dot).toBeInTheDocument();
  });
});
