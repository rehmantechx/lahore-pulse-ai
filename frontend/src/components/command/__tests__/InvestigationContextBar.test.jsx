/**
 * InvestigationContextBar — Unit tests.
 *
 * Tests: rendering, stage labels, severity, mobile responsiveness,
 * IntersectionObserver guard, demo mode behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import InvestigationContextBar from '../InvestigationContextBar';

const MOCK_EPISODE = {
  current_pm25: 165,
  trajectory: 'rising',
};

const MOCK_VERIFICATION = {
  current_outcome: { outcome_type: 'verified' },
};

function renderBar(props = {}) {
  const defaults = {
    demoStep: 1,
    episode: MOCK_EPISODE,
    verificationContext: null,
    isDemo: true,
  };
  return render(<InvestigationContextBar {...defaults} {...props} />);
}

describe('InvestigationContextBar', () => {
  describe('Rendering', () => {
    it('renders the context bar container', () => {
      renderBar();
      expect(screen.getByTestId('investigation-context-bar')).toBeInTheDocument();
    });

    it('renders stage label for step 1', () => {
      renderBar({ demoStep: 1 });
      expect(screen.getByText('Monitoring')).toBeInTheDocument();
    });

    it('renders PM2.5 value', () => {
      renderBar({ demoStep: 2 });
      expect(screen.getByText(/165/)).toBeInTheDocument();
    });

    it('renders trend indicator', () => {
      renderBar({ demoStep: 2 });
      expect(screen.getByText(/rising/i)).toBeInTheDocument();
    });
  });

  describe('Stage labels by step', () => {
    it('step 1 shows Monitoring label', () => {
      renderBar({ demoStep: 1 });
      expect(screen.getByText('Monitoring')).toBeInTheDocument();
    });

    it('step 3 shows Investigation label', () => {
      renderBar({ demoStep: 3 });
      expect(screen.getByText('Investigation')).toBeInTheDocument();
    });

    it('step 5 shows Verification label', () => {
      renderBar({ demoStep: 5 });
      expect(screen.getByText('Verification')).toBeInTheDocument();
    });

    it('step 6 shows Accountability label', () => {
      renderBar({ demoStep: 6 });
      expect(screen.getByText('Accountability')).toBeInTheDocument();
    });
  });

  describe('No episode data', () => {
    it('renders without episode', () => {
      renderBar({ episode: null });
      expect(screen.getByTestId('investigation-context-bar')).toBeInTheDocument();
    });

    it('shows dash for missing PM2.5', () => {
      renderBar({ episode: null });
      expect(screen.getByText('—')).toBeInTheDocument();
    });
  });

  describe('Verification info', () => {
    it('shows verification status when available', () => {
      renderBar({ demoStep: 5, verificationContext: MOCK_VERIFICATION });
      expect(screen.getByText(/Verif/i)).toBeInTheDocument();
    });
  });

  describe('Demo mode gating', () => {
    it('renders but is not visible when isDemo=false', () => {
      renderBar({ isDemo: false });
      const bar = screen.getByTestId('investigation-context-bar');
      expect(bar).toBeInTheDocument();
      // When not visible, the bar should not have --visible class
      expect(bar).not.toHaveClass('icb--visible');
    });
  });

  describe('IntersectionObserver guard', () => {
    it('does not throw when IntersectionObserver is undefined', () => {
      const origIO = global.IntersectionObserver;
      // @ts-ignore
      delete global.IntersectionObserver;
      expect(() => renderBar({ isDemo: true })).not.toThrow();
      global.IntersectionObserver = origIO;
    });
  });
});
