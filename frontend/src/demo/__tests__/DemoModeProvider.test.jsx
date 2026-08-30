/**
 * DemoModeProvider — Deterministic state management tests.
 *
 * Tests: URL precedence, sessionStorage fallback, deep linking,
 * URL synchronization, reset behavior, edge cases.
 *
 * Phase 14: Demo Control, Deep Linking & Presentation Reliability
 *
 * Note: jsdom doesn't support history.replaceState with cross-origin URLs.
 * We mock replaceState to track URL changes while testing the logic.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

/* ── Helpers ────────────────────────────────────────────── */

import {
  DemoModeProvider,
  useDemoData,
  isDemoUrl,
  parseStepFromUrl,
  syncStepToUrl,
  persistStepToSession,
  clearDemoSession,
} from '../index';

import { TOTAL_STEPS } from '../stateMachine';

/* ── Test consumer ──────────────────────────────────────── */

function DemoConsumer() {
  const data = useDemoData();
  if (!data) return <div data-testid="no-demo">Not in demo mode</div>;
  return (
    <div data-testid="demo-active">
      <span data-testid="demo-step">{data.demoStep}</span>
      <button data-testid="btn-next" onClick={() => data.setDemoStep((s) => s + 1)}>
        Next
      </button>
      <button data-testid="btn-prev" onClick={() => data.setDemoStep((s) => s - 1)}>
        Prev
      </button>
      <button data-testid="btn-set3" onClick={() => data.setDemoStep(3)}>
        Set 3
      </button>
      <button data-testid="btn-reset" onClick={data.resetDemo}>
        Reset
      </button>
    </div>
  );
}

/* ── URL / sessionStorage helpers ───────────────────────── */

let replaceStateSpy;
let _originalLocation;

function setupUrlMocks() {
  // Mock history.replaceState to track calls without actually navigating
  replaceStateSpy = vi.fn((_state, _title, url) => {
    try {
      const u = new URL(url, window.location.origin);
      _setSearch(u.search);
    } catch {
      // If URL parsing fails, ignore
    }
  });
  window.history.replaceState = replaceStateSpy;
}

/** Internal: directly set the search portion of the current URL object */
function _setSearch(search) {
  // jsdom: rebuild location as a new URL
  _originalLocation = new URL(`http://localhost:5173/government${search}`);
}

function setUrlSearch(search) {
  _setSearch(search);
  // Also update the jsdom location object
  Object.defineProperty(window, 'location', {
    value: new URL(`http://localhost:5173/government${search}`),
    writable: true,
    configurable: true,
  });
  // Keep the original for replaceState spy to build URLs from
  _originalLocation = new URL(`http://localhost:5173/government${search}`);
}

function clearSessionStorage() {
  try {
    sessionStorage.removeItem('lahore_plus_demo_step');
    sessionStorage.removeItem('lahore_plus_demo_mode');
  } catch {}
}

/* ── Tests ──────────────────────────────────────────────── */

describe('DemoModeProvider — Deterministic State', () => {
  beforeEach(() => {
    clearSessionStorage();
    setupUrlMocks();
    setUrlSearch('?demo=true');
  });

  afterEach(() => {
    clearSessionStorage();
    vi.restoreAllMocks();
  });

  /* ── parseStepFromUrl ──────────────────────────────────── */

  describe('parseStepFromUrl()', () => {
    it('returns null when no step param', () => {
      setUrlSearch('?demo=true');
      expect(parseStepFromUrl()).toBeNull();
    });

    it('returns valid step number', () => {
      setUrlSearch('?demo=true&step=3');
      expect(parseStepFromUrl()).toBe(3);
    });

    it('returns 1 for step=1', () => {
      setUrlSearch('?step=1');
      expect(parseStepFromUrl()).toBe(1);
    });

    it('returns TOTAL_STEPS for max valid step', () => {
      setUrlSearch(`?step=${TOTAL_STEPS}`);
      expect(parseStepFromUrl()).toBe(TOTAL_STEPS);
    });

    it('returns null for step=0 (below range)', () => {
      setUrlSearch('?step=0');
      expect(parseStepFromUrl()).toBeNull();
    });

    it('returns null for step above TOTAL_STEPS', () => {
      setUrlSearch(`?step=${TOTAL_STEPS + 1}`);
      expect(parseStepFromUrl()).toBeNull();
    });

    it('returns null for non-numeric step', () => {
      setUrlSearch('?step=abc');
      expect(parseStepFromUrl()).toBeNull();
    });

    it('returns null for empty step param', () => {
      setUrlSearch('?step=');
      expect(parseStepFromUrl()).toBeNull();
    });

    it('returns null for negative step', () => {
      setUrlSearch('?step=-3');
      expect(parseStepFromUrl()).toBeNull();
    });
  });

  /* ── syncStepToUrl ────────────────────────────────────── */

  describe('syncStepToUrl()', () => {
    it('calls history.replaceState with step param', () => {
      setUrlSearch('?demo=true');
      syncStepToUrl(4);
      expect(replaceStateSpy).toHaveBeenCalled();
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('step')).toBe('4');
    });

    it('preserves existing URL params', () => {
      setUrlSearch('?demo=true&foo=bar');
      syncStepToUrl(2);
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('demo')).toBe('true');
      expect(url.searchParams.get('foo')).toBe('bar');
      expect(url.searchParams.get('step')).toBe('2');
    });

    it('overwrites existing step param', () => {
      setUrlSearch('?demo=true&step=1');
      syncStepToUrl(5);
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('step')).toBe('5');
    });
  });

  /* ── persistStepToSession / clearDemoSession ──────────── */

  describe('persistStepToSession()', () => {
    it('writes step to sessionStorage', () => {
      persistStepToSession(3);
      expect(sessionStorage.getItem('lahore_plus_demo_step')).toBe('3');
    });

    it('overwrites existing value', () => {
      persistStepToSession(1);
      persistStepToSession(5);
      expect(sessionStorage.getItem('lahore_plus_demo_step')).toBe('5');
    });
  });

  describe('clearDemoSession()', () => {
    it('removes both sessionStorage keys', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '3');
      sessionStorage.setItem('lahore_plus_demo_mode', '1');
      clearDemoSession();
      expect(sessionStorage.getItem('lahore_plus_demo_step')).toBeNull();
      expect(sessionStorage.getItem('lahore_plus_demo_mode')).toBeNull();
    });
  });

  /* ── Scenario A: Direct deep-link ─────────────────────── */

  describe('Scenario A: Deep link to step 3', () => {
    it('initializes at step 3 from URL', () => {
      setUrlSearch('?demo=true&step=3');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('3');
    });

    it('initializes at step 5 from URL', () => {
      setUrlSearch('?demo=true&step=5');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('5');
    });
  });

  /* ── Scenario B: URL overrides stale sessionStorage ────── */

  describe('Scenario B: URL overrides stale sessionStorage', () => {
    it('URL step=2 wins over sessionStorage step=6', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '6');
      setUrlSearch('?demo=true&step=2');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('2');
    });

    it('URL step=1 wins over sessionStorage step=4', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '4');
      setUrlSearch('?demo=true&step=1');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });
  });

  /* ── Scenario C: No URL step → sessionStorage fallback ─── */

  describe('Scenario C: SessionStorage fallback when no URL step', () => {
    it('uses sessionStorage step=4 when no URL step', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '4');
      setUrlSearch('?demo=true');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('4');
    });

    it('defaults to step 1 when no URL and no sessionStorage', () => {
      setUrlSearch('?demo=true');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });
  });

  /* ── Scenario D: Invalid URL step falls back ───────────── */

  describe('Scenario D: Invalid URL step fallback', () => {
    it('falls back to sessionStorage for step=99', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '3');
      setUrlSearch('?demo=true&step=99');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('3');
    });

    it('falls back to sessionStorage for step=abc', () => {
      sessionStorage.setItem('lahore_plus_demo_step', '5');
      setUrlSearch('?demo=true&step=abc');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('5');
    });

    it('defaults to step 1 for invalid URL and no sessionStorage', () => {
      setUrlSearch('?demo=true&step=0');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });
  });

  /* ── URL synchronization on step change ────────────────── */

  describe('URL sync on step change', () => {
    it('replaceState called when navigating to next step', () => {
      setUrlSearch('?demo=true&step=1');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      replaceStateSpy.mockClear();
      fireEvent.click(screen.getByTestId('btn-next'));
      expect(replaceStateSpy).toHaveBeenCalled();
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('step')).toBe('2');
    });

    it('replaceState called when setting step directly', () => {
      setUrlSearch('?demo=true&step=1');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      replaceStateSpy.mockClear();
      fireEvent.click(screen.getByTestId('btn-set3'));
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('step')).toBe('3');
    });

    it('sessionStorage updates when navigating', () => {
      setUrlSearch('?demo=true&step=1');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      fireEvent.click(screen.getByTestId('btn-next'));
      expect(sessionStorage.getItem('lahore_plus_demo_step')).toBe('2');
    });
  });

  /* ── Reset behavior ────────────────────────────────────── */

  describe('Reset', () => {
    it('reset clears sessionStorage', () => {
      setUrlSearch('?demo=true&step=4');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('demo-step')).toHaveTextContent('4');
      fireEvent.click(screen.getByTestId('btn-reset'));
      expect(sessionStorage.getItem('lahore_plus_demo_step')).toBeNull();
      expect(sessionStorage.getItem('lahore_plus_demo_mode')).toBeNull();
    });

    it('reset sets step to 1', () => {
      setUrlSearch('?demo=true&step=5');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      fireEvent.click(screen.getByTestId('btn-reset'));
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });

    it('reset calls replaceState with step=1', () => {
      setUrlSearch('?demo=true&step=4');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      replaceStateSpy.mockClear();
      fireEvent.click(screen.getByTestId('btn-reset'));
      expect(replaceStateSpy).toHaveBeenCalled();
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      const url = new URL(lastCall[2], window.location.origin);
      expect(url.searchParams.get('step')).toBe('1');
    });
  });

  /* ── Non-demo mode passthrough ────────────────────────── */

  describe('Non-demo mode', () => {
    it('passes children through when not demo', () => {
      setUrlSearch('');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      expect(screen.getByTestId('no-demo')).toBeInTheDocument();
    });
  });

  /* ── Step clamping ─────────────────────────────────────── */

  describe('Step clamping', () => {
    it('clamps step above max to max via direct set', () => {
      setUrlSearch('?demo=true&step=1');
      function ClampConsumer() {
        const data = useDemoData();
        if (!data) return <div>No demo</div>;
        return (
          <div>
            <span data-testid="demo-step">{data.demoStep}</span>
            <button data-testid="btn-set-high" onClick={() => data.setDemoStep(TOTAL_STEPS + 1)}>
              Set High
            </button>
          </div>
        );
      }
      render(
        <DemoModeProvider>
          <ClampConsumer />
        </DemoModeProvider>
      );
      fireEvent.click(screen.getByTestId('btn-set-high'));
      expect(screen.getByTestId('demo-step')).toHaveTextContent(String(TOTAL_STEPS));
    });

    it('clamps step below 1 to 1 via direct set', () => {
      setUrlSearch('?demo=true&step=1');
      function ClampConsumer() {
        const data = useDemoData();
        if (!data) return <div>No demo</div>;
        return (
          <div>
            <span data-testid="demo-step">{data.demoStep}</span>
            <button data-testid="btn-set-zero" onClick={() => data.setDemoStep(0)}>
              Set Zero
            </button>
          </div>
        );
      }
      render(
        <DemoModeProvider>
          <ClampConsumer />
        </DemoModeProvider>
      );
      fireEvent.click(screen.getByTestId('btn-set-zero'));
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });

    it('clamps step below 1 to 1 via prev from step 1', () => {
      setUrlSearch('?demo=true&step=1');
      render(
        <DemoModeProvider>
          <DemoConsumer />
        </DemoModeProvider>
      );
      fireEvent.click(screen.getByTestId('btn-prev'));
      expect(screen.getByTestId('demo-step')).toHaveTextContent('1');
    });
  });

  /* ── isDemoUrl ─────────────────────────────────────────── */

  describe('isDemoUrl()', () => {
    it('returns true when ?demo=true in URL', () => {
      setUrlSearch('?demo=true');
      expect(isDemoUrl()).toBe(true);
    });

    it('returns false when ?demo is missing', () => {
      setUrlSearch('');
      expect(isDemoUrl()).toBe(false);
    });

    it('returns false when ?demo=false', () => {
      setUrlSearch('?demo=false');
      expect(isDemoUrl()).toBe(false);
    });
  });
});
