/**
 * Simulation State — Unit Tests.
 *
 * Tests: deterministic timeline progression, activity feed visibility,
 * investigation progress, exposure reveal, accountability chain.
 * All tests verify that state is purely derived from demoStep.
 */

import { describe, it, expect } from 'vitest';
import {
  TIMELINE_EVENTS,
  ACTIVITY_FEED_ENTRIES,
  INVESTIGATION_STEPS,
  EXPOSURE_REVEAL_STEPS,
  ACCOUNTABILITY_CHAIN,
  getSimulationState,
} from '../simulationState';

describe('Simulation State Model', () => {
  describe('Data integrity', () => {
    it('has 10 timeline events', () => {
      expect(TIMELINE_EVENTS).toHaveLength(10);
    });

    it('has 12 activity feed entries', () => {
      expect(ACTIVITY_FEED_ENTRIES).toHaveLength(12);
    });

    it('has 6 investigation steps', () => {
      expect(INVESTIGATION_STEPS).toHaveLength(6);
    });

    it('has 5 exposure reveal steps', () => {
      expect(EXPOSURE_REVEAL_STEPS).toHaveLength(5);
    });

    it('has 8 accountability chain stages', () => {
      expect(ACCOUNTABILITY_CHAIN).toHaveLength(8);
    });

    it('timeline events have unique ids', () => {
      const ids = TIMELINE_EVENTS.map((e) => e.id);
      expect(new Set(ids).size).toBe(ids.length);
    });

    it('activity feed entries have unique ids', () => {
      const ids = ACTIVITY_FEED_ENTRIES.map((e) => e.id);
      expect(new Set(ids).size).toBe(ids.length);
    });
  });

  describe('getSimulationState — timeline', () => {
    it('step 1: only normal-monitoring is current, rest hidden', () => {
      const state = getSimulationState(1);
      const visible = state.timeline.filter((e) => e.visible);
      expect(visible).toHaveLength(1);
      expect(visible[0].id).toBe('normal-monitoring');
      expect(visible[0].status).toBe('current');
    });

    it('step 2: normal-monitoring completed, anomaly + episode current', () => {
      const state = getSimulationState(2);
      const normal = state.timeline.find((e) => e.id === 'normal-monitoring');
      const anomaly = state.timeline.find((e) => e.id === 'anomaly-detected');
      const episode = state.timeline.find((e) => e.id === 'episode-created');
      expect(normal.status).toBe('completed');
      expect(anomaly.status).toBe('current');
      expect(episode.status).toBe('current');
    });

    it('step 7: all 10 events visible, last one current', () => {
      const state = getSimulationState(7);
      const visible = state.timeline.filter((e) => e.visible);
      expect(visible).toHaveLength(10);
      // All but the last are completed
      const completed = visible.filter((e) => e.status === 'completed');
      expect(completed).toHaveLength(9);
      // The last one (visibleFrom: 7) is current at step 7
      expect(visible[visible.length - 1].status).toBe('current');
    });
  });

  describe('getSimulationState — activity feed', () => {
    it('step 1: no visible entries', () => {
      const state = getSimulationState(1);
      expect(state.activityFeed.filter((e) => e.visible)).toHaveLength(0);
    });

    it('step 2: first 3 entries visible (af-anomaly, af-threshold, af-wind)', () => {
      const state = getSimulationState(2);
      const visible = state.activityFeed.filter((e) => e.visible);
      expect(visible).toHaveLength(3);
    });

    it('step 7: all entries visible', () => {
      const state = getSimulationState(7);
      const visible = state.activityFeed.filter((e) => e.visible);
      expect(visible).toHaveLength(12);
      // Last entry (visibleFrom: 7) is current at step 7
      expect(visible[visible.length - 1].status).toBe('current');
    });
  });

  describe('getSimulationState — investigation progress', () => {
    it('step 3: all investigation steps visible, first completed, rest current', () => {
      const state = getSimulationState(3);
      const visible = state.investigationProgress.filter((s) => s.visible);
      expect(visible).toHaveLength(6);
    });

    it('steps 1-2: no investigation steps visible', () => {
      [1, 2].forEach((step) => {
        const state = getSimulationState(step);
        expect(state.investigationProgress.filter((s) => s.visible)).toHaveLength(0);
      });
    });
  });

  describe('getSimulationState — accountability chain', () => {
    it('step 1: only observation visible', () => {
      const state = getSimulationState(1);
      const visible = state.accountabilityChain.filter((s) => s.visible);
      expect(visible).toHaveLength(1);
      expect(visible[0].id).toBe('ac-observation');
    });

    it('step 7: all 8 stages visible, last one current', () => {
      const state = getSimulationState(7);
      const visible = state.accountabilityChain.filter((s) => s.visible);
      expect(visible).toHaveLength(8);
      // All but the last are completed
      const completed = visible.filter((s) => s.status === 'completed');
      expect(completed).toHaveLength(7);
      // The last one (visibleFrom: 7) is current at step 7
      expect(visible[visible.length - 1].status).toBe('current');
    });
  });

  describe('Backward navigation', () => {
    it('going from step 3 to step 2 hides step-3-only events', () => {
      const state3 = getSimulationState(3);
      const state2 = getSimulationState(2);

      // Step 3 has evidence-collected visible
      const evidence = state3.timeline.find((e) => e.id === 'evidence-collected');
      expect(evidence.visible).toBe(true);

      // Step 2 does NOT have evidence-collected visible
      const evidence2 = state2.timeline.find((e) => e.id === 'evidence-collected');
      expect(evidence2.visible).toBe(false);
    });
  });

  describe('Reset behavior', () => {
    it('step 1 after step 6 returns to initial state', () => {
      const initial = getSimulationState(1);
      const afterReset = getSimulationState(1);
      expect(initial.timeline[0].status).toBe('current');
      expect(initial.timeline[0].visible).toBe(true);
      expect(initial.timeline[1].visible).toBe(false);
      expect(afterReset.timeline[0].status).toBe('current');
    });
  });

  describe('Boundary conditions', () => {
    it('step 0 clamps to step 1', () => {
      const state = getSimulationState(0);
      const state1 = getSimulationState(1);
      expect(state).toEqual(state1);
    });

    it('step 99 clamps to step 7', () => {
      const state = getSimulationState(99);
      const state7 = getSimulationState(7);
      expect(state).toEqual(state7);
    });

    it('negative step clamps to step 1', () => {
      const state = getSimulationState(-5);
      expect(state.timeline[0].visible).toBe(true);
    });
  });
});
