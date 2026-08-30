/**
 * WhyDifferent Component Tests.
 *
 * Tests: rendering, differentiator cards, disclaimer, accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import WhyDifferent from '../WhyDifferent';

describe('WhyDifferent', () => {
  describe('Rendering', () => {
    it('renders the differentiation heading', () => {
      render(<WhyDifferent />);
      expect(screen.getByText('How Our Solution Is Different')).toBeInTheDocument();
    });

    it('renders the region with aria-label', () => {
      render(<WhyDifferent />);
      expect(screen.getByRole('region', { name: /how our solution is different/i })).toBeInTheDocument();
    });

    it('renders 6 differentiator cards', () => {
      const { container } = render(<WhyDifferent />);
      const cards = container.querySelectorAll('.why-different__card');
      expect(cards).toHaveLength(6);
    });

    it('renders the footer disclaimer', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/does not claim source attribution/i)).toBeInTheDocument();
    });

    it('renders WHO/PROBLEM/DECISION context', () => {
      render(<WhyDifferent />);
      expect(screen.getByText('WHO')).toBeInTheDocument();
      expect(screen.getByText('PROBLEM')).toBeInTheDocument();
      expect(screen.getByText('DECISION')).toBeInTheDocument();
    });
  });

  describe('Differentiator Content', () => {
    it('includes Beyond AQI Dashboards differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText('Beyond AQI Dashboards')).toBeInTheDocument();
    });

    it('includes AI evidence constraint differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/AI Receives Evidence/i)).toBeInTheDocument();
    });

    it('includes facts separation differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/Facts, Inference, and Hypotheses Are Separated/i)).toBeInTheDocument();
    });

    it('includes exposure direction differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/Predicts Approximate Exposure/i)).toBeInTheDocument();
    });

    it('includes human control differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/Human Decision-Maker/i)).toBeInTheDocument();
    });

    it('includes verification over time differentiator', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/Recommendations Are Verified/i)).toBeInTheDocument();
    });
  });

  describe('Disclaimer', () => {
    it('includes non-claims in footer', () => {
      render(<WhyDifferent />);
      expect(screen.getByText(/does not claim source attribution/i)).toBeInTheDocument();
      expect(screen.getByText(/does not claim.*100% accuracy/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<WhyDifferent />);
      const heading = screen.getByRole('heading', { level: 3 });
      expect(heading).toHaveTextContent('How Our Solution Is Different');
    });

    it('each card has proper class', () => {
      const { container } = render(<WhyDifferent />);
      const cards = container.querySelectorAll('.why-different__card');
      cards.forEach((card) => {
        expect(card).toHaveClass('why-different__card');
      });
    });
  });
});
