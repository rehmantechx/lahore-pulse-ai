/**
 * ProductNarrative Component Tests.
 *
 * Tests: rendering, title, layers, decision callout.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import ProductNarrative from '../ProductNarrative';

describe('ProductNarrative', () => {
  describe('Rendering', () => {
    it('renders the narrative section', () => {
      const { container } = render(<ProductNarrative />);
      expect(container.querySelector('.lp-narrative')).toBeInTheDocument();
    });

    it('renders the title', () => {
      render(<ProductNarrative />);
      expect(screen.getByText(/Not another AQI dashboard/i)).toBeInTheDocument();
    });

    it('renders the section label', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('How It Works')).toBeInTheDocument();
    });

    it('renders the problem statement', () => {
      render(<ProductNarrative />);
      expect(screen.getByText(/pollution spike tells authorities/i)).toBeInTheDocument();
    });

    it('renders the decision callout', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('THE DECISION')).toBeInTheDocument();
      expect(screen.getByText(/Where should we investigate first/i)).toBeInTheDocument();
    });

    it('renders the solution description', () => {
      render(<ProductNarrative />);
      expect(screen.getByText(/detects abnormal pollution events/i)).toBeInTheDocument();
    });

    it('renders the AI disclaimer note', () => {
      render(<ProductNarrative />);
      expect(screen.getByText(/does not decide what caused pollution/i)).toBeInTheDocument();
    });
  });

  describe('4-Layer Breakdown', () => {
    it('renders exactly 4 layers', () => {
      const { container } = render(<ProductNarrative />);
      const layers = container.querySelectorAll('.lp-narrative__layer');
      expect(layers).toHaveLength(4);
    });

    it('includes Observed layer', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('Observed')).toBeInTheDocument();
    });

    it('includes Deterministic layer', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('Deterministic')).toBeInTheDocument();
    });

    it('includes AI Hypothesis layer', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('AI Hypothesis')).toBeInTheDocument();
    });

    it('includes Human Verification layer', () => {
      render(<ProductNarrative />);
      expect(screen.getByText('Human Verification')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('uses section element', () => {
      const { container } = render(<ProductNarrative />);
      const section = container.querySelector('.lp-narrative');
      expect(section.tagName).toBe('SECTION');
    });
  });
});
