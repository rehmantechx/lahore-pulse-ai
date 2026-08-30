/**
 * DemoLegend Component Tests.
 *
 * Tests: progressive layer rendering, prop-based filtering, accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import DemoLegend from '../DemoLegend';

describe('DemoLegend', () => {
  describe('Empty state', () => {
    it('renders nothing when no activeLayers provided', () => {
      const { container } = render(<DemoLegend />);
      expect(container.querySelector('.demo-legend')).not.toBeInTheDocument();
    });

    it('renders nothing when activeLayers is empty', () => {
      const { container } = render(<DemoLegend activeLayers={[]} />);
      expect(container.querySelector('.demo-legend')).not.toBeInTheDocument();
    });
  });

  describe('Progressive rendering', () => {
    it('renders 1 item for step 1 (observed only)', () => {
      const { container } = render(<DemoLegend activeLayers={['observed']} />);
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(1);
    });

    it('renders 2 items for step 2 (observed + deterministic)', () => {
      const { container } = render(
        <DemoLegend activeLayers={['observed', 'deterministic']} />
      );
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(2);
    });

    it('renders 3 items for step 3 (observed + deterministic + ai)', () => {
      const { container } = render(
        <DemoLegend activeLayers={['observed', 'deterministic', 'ai']} />
      );
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(3);
    });

    it('renders 2 items for step 5 (ai + verified)', () => {
      const { container } = render(
        <DemoLegend activeLayers={['ai', 'verified']} />
      );
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(2);
    });

    it('renders 2 items for step 6 (verified + accountability)', () => {
      const { container } = render(
        <DemoLegend activeLayers={['verified', 'accountability']} />
      );
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(2);
    });
  });

  describe('Layer labels', () => {
    it('renders OBSERVED label', () => {
      render(<DemoLegend activeLayers={['observed']} />);
      expect(screen.getByText('OBSERVED')).toBeInTheDocument();
    });

    it('renders DETERMINISTIC label', () => {
      render(<DemoLegend activeLayers={['deterministic']} />);
      expect(screen.getByText('DETERMINISTIC')).toBeInTheDocument();
    });

    it('renders AI HYPOTHESIS label', () => {
      render(<DemoLegend activeLayers={['ai']} />);
      expect(screen.getByText('AI HYPOTHESIS')).toBeInTheDocument();
    });

    it('renders HUMAN VERIFIED label', () => {
      render(<DemoLegend activeLayers={['verified']} />);
      expect(screen.getByText('HUMAN VERIFIED')).toBeInTheDocument();
    });

    it('renders ACCOUNTABILITY label', () => {
      render(<DemoLegend activeLayers={['accountability']} />);
      expect(screen.getByText('ACCOUNTABILITY')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has aria-label on container', () => {
      render(<DemoLegend activeLayers={['observed']} />);
      expect(screen.getByLabelText('Active data layers')).toBeInTheDocument();
    });

    it('color dots have aria-hidden', () => {
      const { container } = render(<DemoLegend activeLayers={['observed']} />);
      const dot = container.querySelector('.demo-legend__dot');
      expect(dot).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Unknown layer keys', () => {
    it('ignores unknown layer keys', () => {
      const { container } = render(
        <DemoLegend activeLayers={['observed', 'nonexistent']} />
      );
      const items = container.querySelectorAll('.demo-legend__item');
      expect(items).toHaveLength(1);
    });
  });
});
