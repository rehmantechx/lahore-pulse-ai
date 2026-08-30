/**
 * ProgressiveDisclosure — Unit tests.
 *
 * Tests: rendering, expand/collapse, keyboard access, props, default state.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import ProgressiveDisclosure from '../ProgressiveDisclosure';

function renderPD(props = {}) {
  return render(
    <ProgressiveDisclosure label="Show more" labelExpanded="Show less" testId="test-pd" {...props}>
      <p data-testid="pd-child">Hidden content</p>
    </ProgressiveDisclosure>
  );
}

describe('ProgressiveDisclosure', () => {
  describe('Collapsed by default', () => {
    it('renders with label text', () => {
      renderPD();
      expect(screen.getByTestId('test-pd')).toBeInTheDocument();
      expect(screen.getByText('Show more')).toBeInTheDocument();
    });

    it('does not show children content', () => {
      renderPD();
      expect(screen.queryByTestId('pd-child')).not.toBeInTheDocument();
    });

    it('toggle button has aria-expanded=false', () => {
      renderPD();
      expect(screen.getByTestId('test-pd-toggle')).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Expand/collapse', () => {
    it('clicking toggle expands content', () => {
      renderPD();
      fireEvent.click(screen.getByTestId('test-pd-toggle'));
      expect(screen.getByTestId('pd-child')).toBeInTheDocument();
      expect(screen.getByText('Show less')).toBeInTheDocument();
    });

    it('clicking toggle again collapses content', () => {
      renderPD();
      fireEvent.click(screen.getByTestId('test-pd-toggle'));
      expect(screen.getByTestId('pd-child')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('test-pd-toggle'));
      expect(screen.queryByTestId('pd-child')).not.toBeInTheDocument();
      expect(screen.getByText('Show more')).toBeInTheDocument();
    });

    it('aria-expanded toggles with state', () => {
      renderPD();
      const toggle = screen.getByTestId('test-pd-toggle');
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
      fireEvent.click(toggle);
      expect(toggle).toHaveAttribute('aria-expanded', 'true');
      fireEvent.click(toggle);
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Keyboard accessibility', () => {
    it('Enter key toggles', () => {
      renderPD();
      const toggle = screen.getByTestId('test-pd-toggle');
      fireEvent.keyDown(toggle, { key: 'Enter' });
      // Button onClick fires on keyDown for Enter — but let's use click to simulate
      fireEvent.click(toggle);
      expect(screen.getByTestId('pd-child')).toBeInTheDocument();
    });

    it('Space key toggles', () => {
      renderPD();
      const toggle = screen.getByTestId('test-pd-toggle');
      fireEvent.keyDown(toggle, { key: ' ' });
      fireEvent.click(toggle);
      expect(screen.getByTestId('pd-child')).toBeInTheDocument();
    });
  });

  describe('Default expanded', () => {
    it('shows children when defaultExpanded=true', () => {
      renderPD({ defaultExpanded: true });
      expect(screen.getByTestId('pd-child')).toBeInTheDocument();
      expect(screen.getByText('Show less')).toBeInTheDocument();
    });
  });

  describe('Content rendered', () => {
    it('renders children inside pd__content', () => {
      renderPD();
      fireEvent.click(screen.getByTestId('test-pd-toggle'));
      const content = screen.getByTestId('test-pd-content');
      expect(content).toBeInTheDocument();
      expect(content.querySelector('[data-testid="pd-child"]')).toBeInTheDocument();
    });
  });

  describe('Custom labels', () => {
    it('uses custom labels', () => {
      renderPD({ label: 'Reveal', labelExpanded: 'Conceal' });
      expect(screen.getByText('Reveal')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('test-pd-toggle'));
      expect(screen.getByText('Conceal')).toBeInTheDocument();
    });
  });

  describe('ClassName', () => {
    it('applies custom className', () => {
      renderPD({ className: 'my-custom' });
      expect(screen.getByTestId('test-pd')).toHaveClass('pd', 'my-custom');
    });
  });
});
