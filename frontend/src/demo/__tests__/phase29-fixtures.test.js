/**
 * Demo Fixtures — Phase 29 Tests.
 *
 * Verifies DEMO_AUDIT_TRAIL and DEMO_DECISION_EVIDENCE_CHAIN
 * are correctly structured and exported.
 */

import { describe, it, expect } from 'vitest';

/* We need to import the named exports from the demo module.
   Because the demo module uses React context internally,
   we test the fixture data objects directly. */

import {
  DEMO_AUDIT_TRAIL,
  DEMO_DECISION_EVIDENCE_CHAIN,
} from '../index';

describe('DEMO_AUDIT_TRAIL', () => {
  it('is an array', () => {
    expect(Array.isArray(DEMO_AUDIT_TRAIL)).toBe(true);
  });

  it('has 8 events', () => {
    expect(DEMO_AUDIT_TRAIL).toHaveLength(8);
  });

  it('each event has required fields', () => {
    DEMO_AUDIT_TRAIL.forEach((event) => {
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('timestamp');
      expect(event).toHaveProperty('action');
      expect(event).toHaveProperty('actor');
      expect(event).toHaveProperty('detail');
      expect(event).toHaveProperty('icon');
    });
  });

  it('events have unique ids', () => {
    const ids = DEMO_AUDIT_TRAIL.map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('events have valid actors', () => {
    const validActors = ['System', 'AI', 'Officer'];
    DEMO_AUDIT_TRAIL.forEach((event) => {
      expect(validActors).toContain(event.actor);
    });
  });
});

describe('DEMO_DECISION_EVIDENCE_CHAIN', () => {
  it('is an array of steps', () => {
    expect(Array.isArray(DEMO_DECISION_EVIDENCE_CHAIN)).toBe(true);
    expect(DEMO_DECISION_EVIDENCE_CHAIN).toHaveLength(5);
  });

  it('each step has required fields', () => {
    DEMO_DECISION_EVIDENCE_CHAIN.forEach((step) => {
      expect(step).toHaveProperty('id');
      expect(step).toHaveProperty('title');
      expect(step).toHaveProperty('icon');
      expect(step).toHaveProperty('status');
      expect(step).toHaveProperty('data');
    });
  });

  it('step titles form the evidence chain narrative', () => {
    const titles = DEMO_DECISION_EVIDENCE_CHAIN.map((s) => s.title);
    expect(titles).toContain('Data Foundation');
    expect(titles).toContain('AI Prediction');
    expect(titles).toContain('Verification');
    expect(titles).toContain('Accountability');
  });

  it('all steps have status complete', () => {
    DEMO_DECISION_EVIDENCE_CHAIN.forEach((step) => {
      expect(step.status).toBe('complete');
    });
  });

  it('step data has label and source', () => {
    DEMO_DECISION_EVIDENCE_CHAIN.forEach((step) => {
      expect(step.data).toHaveProperty('label');
      expect(step.data).toHaveProperty('source');
      expect(step.data).toHaveProperty('detail');
    });
  });
});
