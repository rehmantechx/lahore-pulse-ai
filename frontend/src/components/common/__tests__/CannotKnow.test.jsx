/**
 * CannotKnow Component Tests.
 *
 * Tests: rendering, all 7 limitation items, accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import CannotKnow from '../CannotKnow';

describe('CannotKnow', () => {
  describe('Rendering', () => {
    it('renders the limitations heading', () => {
      render(<CannotKnow />);
      expect(screen.getByText('What Lahore+ Cannot Know')).toBeInTheDocument();
    });

    it('renders the subtitle text', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Understanding these limits/i)).toBeInTheDocument();
    });

    it('renders exactly 7 limitation items', () => {
      const { container } = render(<CannotKnow />);
      const items = container.querySelectorAll('.cannot-know__item');
      expect(items).toHaveLength(7);
    });

    it('renders the region with aria-label', () => {
      render(<CannotKnow />);
      expect(screen.getByRole('region', { name: /what lahore\+ cannot know/i })).toBeInTheDocument();
    });
  });

  describe('Limitation Content', () => {
    it('includes directional analysis limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Directional analysis is not source attribution/i)).toBeInTheDocument();
    });

    it('includes AI hypotheses limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/AI hypotheses are not confirmed facts/i)).toBeInTheDocument();
    });

    it('includes exposure geometry limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Exposure geometry is approximate/i)).toBeInTheDocument();
    });

    it('includes weather data limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Weather and environmental data/i)).toBeInTheDocument();
    });

    it('includes historical patterns limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Historical patterns show association/i)).toBeInTheDocument();
    });

    it('includes specific polluter limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/does not identify specific polluters/i)).toBeInTheDocument();
    });

    it('includes human verification limitation', () => {
      render(<CannotKnow />);
      expect(screen.getByText(/Human verification is required/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<CannotKnow />);
      const heading = screen.getByRole('heading', { level: 3 });
      expect(heading).toHaveTextContent('What Lahore+ Cannot Know');
    });

    it('list container has proper class', () => {
      const { container } = render(<CannotKnow />);
      const list = container.querySelector('.cannot-know__list');
      expect(list).toBeInTheDocument();
    });
  });
});
