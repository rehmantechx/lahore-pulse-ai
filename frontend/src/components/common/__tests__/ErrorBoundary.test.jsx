/**
 * ErrorBoundary Component Tests.
 *
 * Tests: error catching, fallback UI, retry button, custom props.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import ErrorBoundary from '../ErrorBoundary';

// Suppress React error boundary console noise in tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
  return () => { console.error = originalConsoleError; };
});

function ThrowingComponent() {
  throw new Error('Test error');
}

function SafeComponent() {
  return <div>Safe content</div>;
}

describe('ErrorBoundary', () => {
  describe('Normal Rendering', () => {
    it('renders children when no error', () => {
      render(
        <ErrorBoundary>
          <SafeComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText('Safe content')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('renders fallback UI when child throws', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('renders default fallback message', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText(/unexpected error occurred/i)).toBeInTheDocument();
    });

    it('renders custom fallback title', () => {
      render(
        <ErrorBoundary fallbackTitle="Custom Title">
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom Title')).toBeInTheDocument();
    });

    it('renders custom fallback message', () => {
      render(
        <ErrorBoundary fallbackMessage="Custom message here">
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom message here')).toBeInTheDocument();
    });

    it('does not render children in error state', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.queryByText('Safe content')).not.toBeInTheDocument();
    });
  });

  describe('Retry', () => {
    it('renders retry button', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('retry button clears error state when child recovers', () => {
      // Use a component that tracks whether it should throw
      let shouldThrow = true;
      function ConditionalThrower() {
        if (shouldThrow) throw new Error('Test error');
        return <div>Recovered content</div>;
      }

      function Wrapper() {
        return (
          <ErrorBoundary>
            <ConditionalThrower />
          </ErrorBoundary>
        );
      }

      const { unmount } = render(<Wrapper />);
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.queryByText('Recovered content')).not.toBeInTheDocument();

      // Fix the error condition before retry
      shouldThrow = false;

      // Click retry - this will call setState({ hasError: false })
      // which triggers a re-render, and since shouldThrow is now false,
      // ConditionalThrower will render normally
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));

      expect(screen.getByText('Recovered content')).toBeInTheDocument();
      expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();

      unmount();
    });
  });

  describe('Accessibility', () => {
    it('has error state role', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );
      const errorEl = screen.getByRole('alert');
      expect(errorEl).toBeInTheDocument();
    });
  });
});
