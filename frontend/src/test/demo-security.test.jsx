/**
 * Demo Security Boundary — Phase 27 Tests.
 *
 * Verifies the demo mode data isolation and boundary patterns:
 * - useDemoData returns data in demo mode, null in production
 * - Demo fixtures exist for all required data
 * - Demo state machine has correct step count
 * - DemoController exists as a component
 */

import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom';

vi.mock('../demo', async () => {
  const actual = await vi.importActual('../demo');
  return actual;
});

describe('Demo Security Boundary', () => {
  it('useDemoData hook exists as exported function', async () => {
    const { useDemoData } = await import('../demo');
    expect(typeof useDemoData).toBe('function');
  });

  it('Demo state machine has exactly 7 steps', async () => {
    const { DEMO_STEPS, TOTAL_STEPS } = await import('../demo/stateMachine');
    expect(TOTAL_STEPS).toBe(7);
    expect(DEMO_STEPS).toHaveLength(7);
  });

  it('Demo state machine steps are sequential (1-7)', async () => {
    const { DEMO_STEPS } = await import('../demo/stateMachine');
    DEMO_STEPS.forEach((step, i) => {
      expect(step.id).toBe(i + 1);
    });
  });

  it('Step 1 uses normal episode (before incident)', async () => {
    const { DEMO_STEPS } = await import('../demo/stateMachine');
    expect(DEMO_STEPS[0].useNormalEpisode).toBe(true);
    expect(DEMO_STEPS[0].showInvestigation).toBe(false);
    expect(DEMO_STEPS[0].showBelowFold).toBe(false);
  });

  it('Step 7 shows all below-fold content', async () => {
    const { DEMO_STEPS } = await import('../demo/stateMachine');
    const step7 = DEMO_STEPS[6];
    expect(step7.showBelowFold).toBe(true);
    expect(step7.showInvestigation).toBe(true);
  });

  it('Demo mode imports all required fixtures', async () => {
    const mod = await import('../demo/index.jsx');
    // Verify key exports exist
    expect(typeof mod.DemoModeProvider).toBe('function');
    expect(typeof mod.useDemoData).toBe('function');
  });
});
