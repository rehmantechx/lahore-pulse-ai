/**
 * State Machine — Phase 29 showEvidenceChain Tests.
 *
 * Verifies that steps 6 and 7 have showEvidenceChain: true,
 * and earlier steps do not.
 */

import { describe, it, expect } from 'vitest';

import { getStep, TOTAL_STEPS } from '../stateMachine';

describe('State Machine — showEvidenceChain', () => {
  it('TOTAL_STEPS is 7', () => {
    expect(TOTAL_STEPS).toBe(7);
  });

  it('step 6 has showEvidenceChain: true', () => {
    const step = getStep(6);
    expect(step.showEvidenceChain).toBe(true);
  });

  it('step 7 has showEvidenceChain: true', () => {
    const step = getStep(7);
    expect(step.showEvidenceChain).toBe(true);
  });

  it('steps 1-5 do not have showEvidenceChain', () => {
    for (let i = 1; i <= 5; i++) {
      const step = getStep(i);
      expect(step.showEvidenceChain).toBeFalsy();
    }
  });

  it('every step has required fields', () => {
    for (let i = 1; i <= TOTAL_STEPS; i++) {
      const step = getStep(i);
      expect(step).toHaveProperty('id', i);
      expect(step).toHaveProperty('label');
      expect(step).toHaveProperty('question');
      expect(step).toHaveProperty('sectionId');
      expect(step).toHaveProperty('layers');
    }
  });
});
