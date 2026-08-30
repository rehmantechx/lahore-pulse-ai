/**
 * DemoController Component Tests.
 *
 * Tests: rendering, step navigation, reset, progressive legend, accessibility.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the demo context
vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

// Mock DemoLegend to avoid nested rendering
vi.mock('../DemoLegend', () => ({
  default: function MockDemoLegend({ activeLayers }) {
    return (
      <div data-testid="demo-legend-mock" data-layers={JSON.stringify(activeLayers)}>
        Legend
      </div>
    );
  },
}));

import { useDemoData } from '../../../demo';
import DemoController from '../DemoController';

function renderController(overrides = {}) {
  const defaults = {
    demoStep: 1,
    setDemoStep: vi.fn(),
    resetDemo: vi.fn(),
  };
  useDemoData.mockReturnValue({ ...defaults, ...overrides });
  return render(<DemoController />);
}

describe('DemoController', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the demo controller container', () => {
      renderController();
      expect(screen.getByRole('complementary', { name: /demo walkthrough/i })).toBeInTheDocument();
    });

    it('renders "LAHORE+" brand in header', () => {
      renderController();
      expect(screen.getByText('LAHORE+')).toBeInTheDocument();
    });

    it('renders "DEMONSTRATION" subtitle', () => {
      renderController();
      expect(screen.getByText('DEMONSTRATION')).toBeInTheDocument();
    });

    it('renders 7 step progress indicators', () => {
      renderController();
      const indicators = screen.getAllByTestId('demo-step-indicator');
      expect(indicators).toHaveLength(7);
    });

    it('renders step info panel', () => {
      renderController();
      expect(screen.getByTestId('demo-step-info')).toBeInTheDocument();
    });
  });

  describe('Step 1 display', () => {
    it('shows "Step 1: Normal Conditions" title', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByText('Step 1: Normal Conditions')).toBeInTheDocument();
    });

    it('shows step 1 question in active indicator', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByText('What is normal?')).toBeInTheDocument();
    });

    it('shows step 1 description', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByText(/continuously monitors/)).toBeInTheDocument();
    });

    it('shows step 1 narration', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByText(/Current conditions are elevated/)).toBeInTheDocument();
    });

    it('Prev button is disabled at step 1', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByTestId('demo-prev')).toBeDisabled();
    });

    it('Next button is enabled at step 1', () => {
      renderController({ demoStep: 1 });
      expect(screen.getByTestId('demo-next')).not.toBeDisabled();
    });
  });

  describe('Step 7 (final) display', () => {
    it('shows "Step 7: Every Prediction Becomes Evidence" title', () => {
      renderController({ demoStep: 7 });
      expect(screen.getByText('Step 7: Every Prediction Becomes Evidence')).toBeInTheDocument();
    });

    it('Next button is disabled at step 7', () => {
      renderController({ demoStep: 7 });
      expect(screen.getByTestId('demo-next')).toBeDisabled();
    });

    it('Prev button is enabled at step 7', () => {
      renderController({ demoStep: 7 });
      expect(screen.getByTestId('demo-prev')).not.toBeDisabled();
    });

    it('shows final message at step 7', () => {
      renderController({ demoStep: 7 });
      expect(screen.getByText(/not just an AQI dashboard/)).toBeInTheDocument();
    });
  });

  describe('Progressive legend', () => {
    it('passes observed layer for step 1', () => {
      renderController({ demoStep: 1 });
      const legend = screen.getByTestId('demo-legend-mock');
      expect(legend.dataset.layers).toContain('observed');
      expect(legend.dataset.layers).not.toContain('deterministic');
    });

    it('passes observed+deterministic+ai for step 3', () => {
      renderController({ demoStep: 3 });
      const legend = screen.getByTestId('demo-legend-mock');
      const layers = JSON.parse(legend.dataset.layers);
      expect(layers).toEqual(['observed', 'deterministic', 'ai']);
    });

    it('passes ai+verified for step 5', () => {
      renderController({ demoStep: 5 });
      const legend = screen.getByTestId('demo-legend-mock');
      const layers = JSON.parse(legend.dataset.layers);
      expect(layers).toEqual(['ai', 'verified']);
    });

    it('passes verified+accountability for step 7', () => {
      renderController({ demoStep: 7 });
      const legend = screen.getByTestId('demo-legend-mock');
      const layers = JSON.parse(legend.dataset.layers);
      expect(layers).toEqual(['verified', 'accountability']);
    });
  });

  describe('Caveat rendering', () => {
    it('shows caveat on step 3', () => {
      renderController({ demoStep: 3 });
      const caveat = document.querySelector('.demo-controller__caveat');
      expect(caveat).toBeInTheDocument();
      expect(caveat.textContent).toContain('investigation hypotheses');
    });

    it('does not show caveat on step 1', () => {
      renderController({ demoStep: 1 });
      expect(document.querySelector('.demo-controller__caveat')).not.toBeInTheDocument();
    });

    it('does not show caveat on step 5', () => {
      renderController({ demoStep: 5 });
      expect(document.querySelector('.demo-controller__caveat')).not.toBeInTheDocument();
    });
  });

  describe('Emphasis rendering', () => {
    it('shows emphasis alert on step 5', () => {
      renderController({ demoStep: 5 });
      const alert = document.querySelector('[role="alert"]');
      expect(alert).toBeInTheDocument();
      expect(alert.textContent).toContain('AI OUTPUT');
    });

    it('does not show emphasis on other steps', () => {
      renderController({ demoStep: 3 });
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Question display', () => {
    it('shows question for step 2', () => {
      renderController({ demoStep: 2 });
      expect(screen.getByText('What changed?')).toBeInTheDocument();
    });

    it('shows question for step 5', () => {
      renderController({ demoStep: 5 });
      expect(screen.getByText('What did humans verify?')).toBeInTheDocument();
    });
  });

  describe('Navigation controls', () => {
    it('calls setDemoStep with next step on Next click', () => {
      const setDemoStep = vi.fn();
      renderController({ demoStep: 3, setDemoStep });
      fireEvent.click(screen.getByTestId('demo-next'));
      expect(setDemoStep).toHaveBeenCalledWith(4);
    });

    it('calls setDemoStep with prev step on Prev click', () => {
      const setDemoStep = vi.fn();
      renderController({ demoStep: 3, setDemoStep });
      fireEvent.click(screen.getByTestId('demo-prev'));
      expect(setDemoStep).toHaveBeenCalledWith(2);
    });

    it('calls resetDemo on Reset click', () => {
      const resetDemo = vi.fn();
      renderController({ demoStep: 4, resetDemo });
      fireEvent.click(screen.getByTestId('demo-reset'));
      expect(resetDemo).toHaveBeenCalledTimes(1);
    });

    it('Next disabled does not call setDemoStep', () => {
      const setDemoStep = vi.fn();
      renderController({ demoStep: 7, setDemoStep });
      fireEvent.click(screen.getByTestId('demo-next'));
      expect(setDemoStep).not.toHaveBeenCalled();
    });

    it('Prev disabled does not call setDemoStep', () => {
      const setDemoStep = vi.fn();
      renderController({ demoStep: 1, setDemoStep });
      fireEvent.click(screen.getByTestId('demo-prev'));
      expect(setDemoStep).not.toHaveBeenCalled();
    });
  });

  describe('Step progress indicators', () => {
    it('marks current step as active', () => {
      renderController({ demoStep: 3 });
      const indicators = screen.getAllByTestId('demo-step-indicator');
      expect(indicators[2]).toHaveAttribute('aria-current', 'step');
    });

    it('does not mark non-current steps as active', () => {
      renderController({ demoStep: 3 });
      const indicators = screen.getAllByTestId('demo-step-indicator');
      expect(indicators[0]).not.toHaveAttribute('aria-current');
      expect(indicators[6]).not.toHaveAttribute('aria-current');
    });
  });

  describe('Button labels', () => {
    it('has accessible labels for navigation', () => {
      renderController({ demoStep: 3 });
      expect(screen.getByRole('button', { name: /previous step/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next step/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reset demo/i })).toBeInTheDocument();
    });

    it('SVG icons have aria-hidden', () => {
      const { container } = renderController({ demoStep: 3 });
      const hiddenIcons = container.querySelectorAll('[aria-hidden="true"]');
      expect(hiddenIcons.length).toBeGreaterThan(0);
    });
  });

  describe('No garbled text', () => {
    it('does not contain "svgPrevNext"', () => {
      renderController({ demoStep: 3 });
      const text = document.body.textContent;
      expect(text).not.toContain('svgPrevNext');
    });

    it('does not contain "Monitoring" (old step label)', () => {
      renderController({ demoStep: 1 });
      const title = screen.getByTestId('demo-step-info');
      expect(title.textContent).not.toContain('Monitoring');
    });

    it('does not contain "Data Layer Legend" (old legend title)', () => {
      renderController({ demoStep: 3 });
      const text = document.body.textContent;
      expect(text).not.toContain('Data Layer Legend');
    });
  });
});
