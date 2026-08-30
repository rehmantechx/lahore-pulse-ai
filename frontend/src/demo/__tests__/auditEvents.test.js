/**
 * SimulationState — Phase 29 AUDIT_EVENTS Tests.
 *
 * Verifies AUDIT_EVENTS array structure and
 * that auditEvents appears in getSimulationState().
 */

import { describe, it, expect } from 'vitest';

import {
  AUDIT_EVENTS,
  getSimulationState,
} from '../simulationState';

describe('AUDIT_EVENTS', () => {
  it('is an array', () => {
    expect(Array.isArray(AUDIT_EVENTS)).toBe(true);
  });

  it('has 8 events', () => {
    expect(AUDIT_EVENTS).toHaveLength(8);
  });

  it('each event has required fields', () => {
    AUDIT_EVENTS.forEach((event) => {
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('time');
      expect(event).toHaveProperty('label');
      expect(event).toHaveProperty('detail');
      expect(event).toHaveProperty('visibleFrom');
    });
  });

  it('events have unique ids', () => {
    const ids = AUDIT_EVENTS.map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('getSimulationState — auditEvents', () => {
  it('includes auditEvents in step 1', () => {
    const state = getSimulationState(1);
    expect(state).toHaveProperty('auditEvents');
    expect(Array.isArray(state.auditEvents)).toBe(true);
  });

  it('step 1 shows no audit events (first visible at step 6)', () => {
    const state = getSimulationState(1);
    const visible = state.auditEvents.filter((e) => e.visible);
    expect(visible).toHaveLength(0);
  });

  it('step 6 shows first 5 events as visible', () => {
    const state = getSimulationState(6);
    const visible = state.auditEvents.filter((e) => e.visible);
    expect(visible.length).toBe(5);
  });

  it('step 7 shows all events as visible', () => {
    const state = getSimulationState(7);
    const visible = state.auditEvents.filter((e) => e.visible);
    expect(visible.length).toBe(AUDIT_EVENTS.length);
  });

  it('progressively reveals events across steps', () => {
    const step1Visible = getSimulationState(1).auditEvents.filter((e) => e.visible).length;
    const step6Visible = getSimulationState(6).auditEvents.filter((e) => e.visible).length;
    const step7Visible = getSimulationState(7).auditEvents.filter((e) => e.visible).length;
    expect(step1Visible).toBeLessThanOrEqual(step6Visible);
    expect(step6Visible).toBeLessThanOrEqual(step7Visible);
  });
});
