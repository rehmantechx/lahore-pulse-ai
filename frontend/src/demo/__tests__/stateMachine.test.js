/**
 * Demo State Machine — Unit Tests.
 *
 * Tests: step definitions, navigation helpers, step configuration flags.
 */

import { describe, it, expect } from 'vitest';
import {
  DEMO_STEPS,
  TOTAL_STEPS,
  getStep,
  nextStep,
  prevStep,
  FINAL_MESSAGE,
} from '../stateMachine';

describe('Demo State Machine', () => {
  describe('DEMO_STEPS definition', () => {
    it('defines exactly 7 steps', () => {
      expect(DEMO_STEPS).toHaveLength(7);
    });

    it('has sequential IDs from 1 to 7', () => {
      DEMO_STEPS.forEach((step, i) => {
        expect(step.id).toBe(i + 1);
      });
    });

    it('has required fields for every step', () => {
      DEMO_STEPS.forEach((step) => {
        expect(step).toHaveProperty('id');
        expect(step).toHaveProperty('key');
        expect(step).toHaveProperty('label');
        expect(step).toHaveProperty('question');
        expect(step).toHaveProperty('description');
        expect(step).toHaveProperty('narration');
        expect(step).toHaveProperty('sectionId');
        expect(step).toHaveProperty('showInvestigation');
        expect(step).toHaveProperty('showBelowFold');
        expect(step).toHaveProperty('useCompletedVerification');
        expect(step).toHaveProperty('useNormalEpisode');
        expect(step).toHaveProperty('layers');
        expect(Array.isArray(step.layers)).toBe(true);
      });
    });

    it('step 1 uses normal episode', () => {
      expect(getStep(1).useNormalEpisode).toBe(true);
    });

    it('steps 2-7 use incident episode', () => {
      for (let i = 2; i <= 7; i++) {
        expect(getStep(i).useNormalEpisode).toBe(false);
      }
    });

    it('steps 1-2 hide investigation section', () => {
      expect(getStep(1).showInvestigation).toBe(false);
      expect(getStep(2).showInvestigation).toBe(false);
    });

    it('steps 3-7 show investigation section', () => {
      for (let i = 3; i <= 7; i++) {
        expect(getStep(i).showInvestigation).toBe(true);
      }
    });

    it('steps 1-3 hide below-fold', () => {
      expect(getStep(1).showBelowFold).toBe(false);
      expect(getStep(2).showBelowFold).toBe(false);
      expect(getStep(3).showBelowFold).toBe(false);
    });

    it('steps 4-7 show below-fold', () => {
      for (let i = 4; i <= 7; i++) {
        expect(getStep(i).showBelowFold).toBe(true);
      }
    });

    it('step 5+ uses completed verification', () => {
      expect(getStep(4).useCompletedVerification).toBe(false);
      expect(getStep(5).useCompletedVerification).toBe(true);
      expect(getStep(6).useCompletedVerification).toBe(true);
      expect(getStep(7).useCompletedVerification).toBe(true);
    });

    it('each step maps to a sectionId', () => {
      DEMO_STEPS.forEach((step) => {
        expect(typeof step.sectionId).toBe('string');
        expect(step.sectionId.length).toBeGreaterThan(0);
      });
    });

    it('steps 1-2 share the same status sectionId', () => {
      expect(getStep(1).sectionId).toBe(getStep(2).sectionId);
    });

    it('steps 3-7 each have distinct sectionIds', () => {
      const sectionIds = [3, 4, 5, 6, 7].map((i) => getStep(i).sectionId);
      const unique = new Set(sectionIds);
      expect(unique.size).toBe(5);
    });
  });

  describe('TOTAL_STEPS', () => {
    it('equals 7', () => {
      expect(TOTAL_STEPS).toBe(7);
    });
  });

  describe('getStep()', () => {
    it('returns the correct step for valid IDs', () => {
      for (let i = 1; i <= 7; i++) {
        expect(getStep(i).id).toBe(i);
      }
    });

    it('returns step 1 for out-of-range high value', () => {
      expect(getStep(99).id).toBe(1);
    });

    it('returns step 1 for out-of-range low value', () => {
      expect(getStep(-5).id).toBe(1);
    });

    it('returns step 1 for 0', () => {
      expect(getStep(0).id).toBe(1);
    });
  });

  describe('nextStep()', () => {
    it('advances from step 1 to step 2', () => {
      expect(nextStep(1)).toBe(2);
    });

    it('advances from step 6 to step 7', () => {
      expect(nextStep(6)).toBe(7);
    });

    it('stays at step 7 when at end', () => {
      expect(nextStep(7)).toBe(7);
    });

    it('does not go beyond TOTAL_STEPS', () => {
      expect(nextStep(TOTAL_STEPS)).toBe(TOTAL_STEPS);
    });
  });

  describe('prevStep()', () => {
    it('goes from step 2 back to step 1', () => {
      expect(prevStep(2)).toBe(1);
    });

    it('stays at step 1 when at start', () => {
      expect(prevStep(1)).toBe(1);
    });

    it('does not go below 1', () => {
      expect(prevStep(0)).toBe(1);
    });

    it('goes from step 7 back to step 6', () => {
      expect(prevStep(7)).toBe(6);
    });
  });

  describe('FINAL_MESSAGE', () => {
    it('is a non-empty string', () => {
      expect(typeof FINAL_MESSAGE).toBe('string');
      expect(FINAL_MESSAGE.length).toBeGreaterThan(0);
    });

    it('mentions "accountable"', () => {
      expect(FINAL_MESSAGE.toLowerCase()).toContain('accountable');
    });
  });

  describe('Step key names', () => {
    it('step keys follow expected pattern', () => {
      const keys = DEMO_STEPS.map((s) => s.key);
      expect(keys).toEqual([
        'NORMAL',
        'EVENT_DETECTED',
        'INVESTIGATION_ACTIVE',
        'EXPOSURE_ACTIVE',
        'VERIFICATION_COMPLETE',
        'PREDICTION_RECEIPT',
        'ACCOUNTABILITY_VISIBLE',
      ]);
    });
  });

  describe('Progressive layers', () => {
    it('step 1 has only observed layer', () => {
      expect(getStep(1).layers).toEqual(['observed']);
    });

    it('step 2 adds deterministic', () => {
      expect(getStep(2).layers).toEqual(['observed', 'deterministic']);
    });

    it('step 3 adds AI', () => {
      expect(getStep(3).layers).toEqual(['observed', 'deterministic', 'ai']);
    });

    it('step 4 same as step 3', () => {
      expect(getStep(4).layers).toEqual(['observed', 'deterministic', 'ai']);
    });

    it('step 5 shifts to ai + verified', () => {
      expect(getStep(5).layers).toEqual(['ai', 'verified']);
    });

    it('step 6 ends with verified + accountability', () => {
      expect(getStep(6).layers).toEqual(['verified', 'accountability']);
    });
  });

  describe('Caveat and emphasis fields', () => {
    it('steps 3-4 have caveat text', () => {
      expect(getStep(3).caveat).toBeTruthy();
      expect(getStep(4).caveat).toBeTruthy();
    });

    it('steps 1-2, 5-7 have no caveat', () => {
      expect(getStep(1).caveat).toBeFalsy();
      expect(getStep(2).caveat).toBeFalsy();
      expect(getStep(5).caveat).toBeFalsy();
      expect(getStep(6).caveat).toBeFalsy();
      expect(getStep(7).caveat).toBeFalsy();
    });

    it('step 5 has emphasis text', () => {
      expect(getStep(5).emphasis).toBeTruthy();
      expect(getStep(5).emphasis).toContain('\u2260');
    });

    it('other steps have no emphasis', () => {
      [1, 2, 3, 4, 7].forEach((i) => {
        expect(getStep(i).emphasis).toBeFalsy();
      });
    });
  });

  describe('Question field', () => {
    it('every step has a question', () => {
      DEMO_STEPS.forEach((step) => {
        expect(step.question).toBeTruthy();
        expect(step.question.endsWith('?')).toBe(true);
      });
    });
  });
});
