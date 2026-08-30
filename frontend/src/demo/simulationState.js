/**
 * Simulation State Model — Deterministic incident timeline.
 *
 * Extends the existing stateMachine.js with simulation data.
 * All state is derived purely from demoStep — no timers, no randomness.
 *
 * getSimulationState(demoStep) returns:
 *   - timeline: array of incident events with visibility per step
 *   - activityFeed: array of processing activity entries
 *   - investigationProgress: step 3 evidence-processing sequence
 *   - exposureReveal: map layer reveal sequence for step 4
 *   - accountabilityChain: full chain for step 6
 *   - auditEvents: step 6–7 audit trail with progressive reveal
 */

import { DEMO_STEPS } from './stateMachine';

/* ── Timeline Events ──────────────────────────────────────── */

export const TIMELINE_EVENTS = [
  {
    id: 'normal-monitoring',
    time: '08:00',
    label: 'Normal monitoring',
    detail: 'PM2.5 within seasonal norms. No episode detected.',
    category: 'observed',
    visibleFrom: 1,
  },
  {
    id: 'anomaly-detected',
    time: '09:15',
    label: 'PM2.5 anomaly detected',
    detail: 'Sharp rise beyond expected pattern. Threshold exceeded.',
    category: 'observed',
    visibleFrom: 2,
  },
  {
    id: 'episode-created',
    time: '09:17',
    label: 'Pollution episode created',
    detail: 'Episode boundaries calculated. Trajectory: rising.',
    category: 'deterministic',
    visibleFrom: 2,
  },
  {
    id: 'evidence-collected',
    time: '09:19',
    label: 'Environmental evidence collected',
    detail: 'Wind, weather, source compass assembled.',
    category: 'deterministic',
    visibleFrom: 3,
  },
  {
    id: 'analogs-retrieved',
    time: '09:21',
    label: 'Historical analogs retrieved',
    detail: '972 similar episode-hours found in East sector.',
    category: 'deterministic',
    visibleFrom: 3,
  },
  {
    id: 'hypotheses-generated',
    time: '09:23',
    label: 'AI investigation hypotheses generated',
    detail: '3 constrained hypotheses produced. Confidence range: 65–70%.',
    category: 'ai',
    visibleFrom: 3,
  },
  {
    id: 'exposure-analyzed',
    time: '09:25',
    label: 'Exposure analysis completed',
    detail: 'Investigation corridor, exposure cone, vulnerable locations identified.',
    category: 'deterministic',
    visibleFrom: 4,
  },
  {
    id: 'outcome-recorded',
    time: '09:30',
    label: 'Human investigation outcome recorded',
    detail: 'Investigator verified: industrial emissions confirmed. Recommendation: Useful.',
    category: 'verified',
    visibleFrom: 5,
  },
  {
    id: 'performance-updated',
    time: '09:32',
    label: 'Prediction receipt generated',
    detail: 'Prediction verified against observation. Error: 9.7%. Confidence calibration: GOOD.',
    category: 'accountability',
    visibleFrom: 6,
  },
  {
    id: 'accountability-recorded',
    time: '09:33',
    label: 'Accountability record updated',
    detail: 'Outcome added to permanent verification history. Available for future evaluation.',
    category: 'accountability',
    visibleFrom: 7,
  },
];

/* ── Activity Feed Entries ─────────────────────────────────── */

export const ACTIVITY_FEED_ENTRIES = [
  { id: 'af-anomaly', category: 'OBSERVED', label: 'PM2.5 anomaly detected', icon: 'dot', visibleFrom: 2 },
  { id: 'af-threshold', category: 'DETERMINISTIC', label: 'Episode threshold exceeded', icon: 'check', visibleFrom: 2 },
  { id: 'af-wind', category: 'DETERMINISTIC', label: 'Wind conditions retrieved', icon: 'check', visibleFrom: 2 },
  { id: 'af-evidence', category: 'DETERMINISTIC', label: 'Environmental evidence assembled', icon: 'check', visibleFrom: 3 },
  { id: 'af-analogs', category: 'DATA RETRIEVAL', label: 'Historical episodes compared', icon: 'check', visibleFrom: 3 },
  { id: 'af-ranking', category: 'DETERMINISTIC', label: 'Supporting evidence ranked', icon: 'check', visibleFrom: 3 },
  { id: 'af-hypotheses', category: 'AI ANALYSIS', label: 'Generating constrained hypotheses', icon: 'dot', visibleFrom: 3 },
  { id: 'af-brief', category: 'AI OUTPUT', label: 'Investigation brief generated', icon: 'check', visibleFrom: 3 },
  { id: 'af-exposure', category: 'DETERMINISTIC', label: 'Exposure analysis completed', icon: 'check', visibleFrom: 4 },
  { id: 'af-human', category: 'HUMAN', label: 'Investigator outcome recorded', icon: 'check', visibleFrom: 5 },
  { id: 'af-receipt', category: 'ACCOUNTABILITY', label: 'Prediction receipt generated', icon: 'check', visibleFrom: 6 },
  { id: 'af-accountability', category: 'ACCOUNTABILITY', label: 'Accountability record updated', icon: 'check', visibleFrom: 7 },
];

/* ── Investigation Progress (Step 3 sequence) ─────────────── */

export const INVESTIGATION_STEPS = [
  { id: 'ip-anomaly', label: 'Pollution anomaly confirmed', visibleFrom: 3, order: 0 },
  { id: 'ip-boundaries', label: 'Episode boundaries calculated', visibleFrom: 3, order: 1 },
  { id: 'ip-meteo', label: 'Meteorological context assembled', visibleFrom: 3, order: 2 },
  { id: 'ip-historical', label: 'Historical episodes compared', visibleFrom: 3, order: 3 },
  { id: 'ip-ranked', label: 'Supporting evidence ranked', visibleFrom: 3, order: 4 },
  { id: 'ip-hypotheses', label: 'Constrained hypotheses generated', visibleFrom: 3, order: 5 },
];

/* ── Exposure Reveal Sequence (Step 4) ────────────────────── */

export const EXPOSURE_REVEAL_STEPS = [
  { id: 'er-location', label: 'Incident location identified', visibleFrom: 4, order: 0 },
  { id: 'er-wind', label: 'Wind direction mapped', visibleFrom: 4, order: 1 },
  { id: 'er-corridor', label: 'Investigation corridor highlighted', visibleFrom: 4, order: 2 },
  { id: 'er-cone', label: 'Exposure cone visualized', visibleFrom: 4, order: 3 },
  { id: 'er-vulnerable', label: 'Vulnerable locations marked', visibleFrom: 4, order: 4 },
];

/* ── Audit Trail Events (Step 6–7) ──────────────────────── */

export const AUDIT_EVENTS = [
  { id: 'ae-001', time: '13:42:00', label: 'Data ingested', detail: '47 features from station, weather, history', visibleFrom: 6 },
  { id: 'ae-002', time: '13:42:12', label: 'Evidence assembled', detail: 'Wind, source compass, analogs combined', visibleFrom: 6 },
  { id: 'ae-003', time: '13:42:18', label: 'Investigation brief generated', detail: '3 hypotheses produced', visibleFrom: 6 },
  { id: 'ae-004', time: '13:42:24', label: 'Prediction made', detail: 'PM2.5: 165 µg/m³ at 6h', visibleFrom: 6 },
  { id: 'ae-005', time: '13:42:30', label: 'Alert issued', detail: 'Threshold exceeded — notification sent', visibleFrom: 6 },
  { id: 'ae-006', time: '20:05:00', label: 'Observation verified', detail: '181 µg/m³ observed, 9.7% error', visibleFrom: 7 },
  { id: 'ae-007', time: '20:05:12', label: 'Investigation reviewed', detail: 'Officer confirmed industrial emissions', visibleFrom: 7 },
  { id: 'ae-008', time: '20:06:00', label: 'Receipt finalized', detail: 'LP-000184 — record permanently stored', visibleFrom: 7 },
];

/* ── Accountability Chain (Step 6) ────────────────────────── */

export const ACCOUNTABILITY_CHAIN = [
  { id: 'ac-observation', label: 'Observation', detail: 'PM2.5 reading captured from monitoring station', visibleFrom: 1 },
  { id: 'ac-episode', label: 'Episode Detected', detail: 'System identified abnormal pollution event', visibleFrom: 2 },
  { id: 'ac-evidence', label: 'Evidence Assembled', detail: 'Environmental context, historical patterns, source compass', visibleFrom: 3 },
  { id: 'ac-hypothesis', label: 'AI Hypothesis', detail: 'Constrained investigation hypotheses generated from evidence', visibleFrom: 3 },
  { id: 'ac-verification', label: 'Human Verification', detail: 'Field investigator confirmed or rejected recommendations', visibleFrom: 5 },
  { id: 'ac-outcome', label: 'Outcome Recorded', detail: 'Verification stored separately from AI analysis', visibleFrom: 5 },
  { id: 'ac-receipt', label: 'Prediction Receipt', detail: 'Prediction verified against observation — error, confidence calibration, and status recorded', visibleFrom: 6 },
  { id: 'ac-future', label: 'Accountability Record', detail: 'Verified outcome retained permanently — cannot be edited after the fact', visibleFrom: 7 },
];

/**
 * Get all simulation data for a given demo step.
 *
 * @param {number} demoStep - Current demo step (1–6)
 * @returns {{ timeline: Array, activityFeed: Array, investigationProgress: Array, exposureReveal: Array, accountabilityChain: Array }}
 */
export function getSimulationState(demoStep) {
  const step = Math.max(1, Math.min(7, demoStep));

  const timeline = TIMELINE_EVENTS.map((event) => ({
    ...event,
    status: event.visibleFrom < step
      ? 'completed'
      : event.visibleFrom === step
        ? 'current'
        : 'future',
    visible: event.visibleFrom <= step,
  }));

  const activityFeed = ACTIVITY_FEED_ENTRIES.map((entry) => {
    const isActive = entry.visibleFrom === step;
    const isCompleted = entry.visibleFrom < step;
    return {
      ...entry,
      status: isCompleted ? 'completed' : isActive ? 'current' : 'future',
      visible: entry.visibleFrom <= step,
      isLatest: isActive,
    };
  });

  const investigationProgress = INVESTIGATION_STEPS.map((s) => ({
    ...s,
    status: s.visibleFrom < step
      ? 'completed'
      : s.visibleFrom === step
        ? 'current'
        : 'future',
    visible: s.visibleFrom <= step,
  }));

  const exposureReveal = EXPOSURE_REVEAL_STEPS.map((s) => ({
    ...s,
    status: s.visibleFrom < step
      ? 'completed'
      : s.visibleFrom === step
        ? 'current'
        : 'future',
    visible: s.visibleFrom <= step,
  }));

  const accountabilityChain = ACCOUNTABILITY_CHAIN.map((s) => ({
    ...s,
    status: s.visibleFrom < step
      ? 'completed'
      : s.visibleFrom === step
        ? 'current'
        : 'future',
    visible: s.visibleFrom <= step,
  }));

  const auditEvents = AUDIT_EVENTS.map((e) => ({
    ...e,
    status: e.visibleFrom < step
      ? 'completed'
      : e.visibleFrom === step
        ? 'current'
        : 'future',
    visible: e.visibleFrom <= step,
  }));

  return {
    timeline,
    activityFeed,
    investigationProgress,
    exposureReveal,
    accountabilityChain,
    auditEvents,
  };
}
