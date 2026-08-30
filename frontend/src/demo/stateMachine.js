/**
 * Demo State Machine — Deterministic demonstration flow.
 *
 * Controls which data is active, which sections are highlighted,
 * and what narration text accompanies each step.
 *
 * 7 steps tell ONE coherent story:
 *   NORMAL → EVENT → INVESTIGATION → EXPOSURE → VERIFICATION → RECEIPT → ACCOUNTABILITY
 *
 * All transitions are user-controlled via Next/Previous buttons.
 * No timers. No randomness. Fully deterministic.
 */

export const DEMO_STEPS = [
  {
    id: 1,
    key: 'NORMAL',
    label: 'Normal Conditions',
    question: 'What is normal?',
    description:
      'Lahore+ continuously monitors pollution patterns before an incident occurs.',
    narration:
      'Current conditions are elevated but stable. No abnormal episode has been detected.',
    sectionId: 'cc-section-status',
    useNormalEpisode: true,
    useCompletedVerification: false,
    showInvestigation: false,
    showBelowFold: false,
    layers: ['observed'],
  },
  {
    id: 2,
    key: 'EVENT_DETECTED',
    label: 'An Abnormal Event Emerges',
    question: 'What changed?',
    description: 'PM2.5 rises sharply beyond the expected pattern.',
    narration:
      'The system detects an unusual pollution episode and begins assembling the environmental context.',
    sectionId: 'cc-section-status',
    useNormalEpisode: false,
    useCompletedVerification: false,
    showInvestigation: false,
    showBelowFold: false,
    layers: ['observed', 'deterministic'],
  },
  {
    id: 3,
    key: 'INVESTIGATION_ACTIVE',
    label: 'From Detection to Investigation',
    question: 'What evidence suggests possible explanations?',
    description:
      'Instead of guessing the cause, Lahore+ assembles evidence.',
    narration:
      'Observed conditions, weather patterns, directional analysis, and historical similarities are combined to generate constrained investigation hypotheses.',
    caveat: 'These are investigation hypotheses — not confirmed source attribution.',
    sectionId: 'cc-section-investigation',
    useNormalEpisode: false,
    useCompletedVerification: false,
    showInvestigation: true,
    showBelowFold: false,
    layers: ['observed', 'deterministic', 'ai'],
  },
  {
    id: 4,
    key: 'EXPOSURE_ACTIVE',
    label: 'Where Could the Pollution Travel?',
    question: 'Where could the impact spread?',
    description:
      'Wind-driven analysis estimates where the pollution may move.',
    narration:
      'The system highlights an investigation corridor, potential exposure area, and vulnerable locations that may be affected.',
    caveat: 'These are estimates based on current wind and weather patterns.',
    sectionId: 'cc-section-exposure',
    useNormalEpisode: false,
    useCompletedVerification: false,
    showInvestigation: true,
    showBelowFold: true,
    layers: ['observed', 'deterministic', 'ai'],
  },
  {
    id: 5,
    key: 'VERIFICATION_COMPLETE',
    label: 'AI Recommends. Humans Verify.',
    question: 'What did humans verify?',
    description: 'An investigator records what was actually found.',
    narration:
      'The recommendation is not automatically treated as fact. Human verification determines whether the investigation was useful, unsupported, or requires further evidence.',
    emphasis: 'AI OUTPUT \u2260 TRUTH',
    sectionId: 'cc-section-verification',
    useNormalEpisode: false,
    useCompletedVerification: true,
    showInvestigation: true,
    showBelowFold: true,
    layers: ['ai', 'verified'],
  },
  {
    id: 6,
    key: 'PREDICTION_RECEIPT',
    label: 'The Prediction Receipt',
    question: 'Was the forecast right?',
    description:
      'Six hours ago, the system predicted 165 μg/m3. The actual observed value was 181 μg/m3.',
    narration:
      'Every prediction is recorded. When the target time passes, the system verifies the result. The receipt shows what was predicted, what actually happened, the error, and whether the confidence was justified. Click "Why do we trust this alert?" to trace the full evidence chain from data to decision.',
    emphasis: 'EVERY PREDICTION IS CHECKED',
    sectionId: 'cc-section-receipt',
    useNormalEpisode: false,
    useCompletedVerification: true,
    showInvestigation: true,
    showBelowFold: true,
    showEvidenceChain: true,
    layers: ['verified', 'accountability'],
  },
  {
    id: 7,
    key: 'ACCOUNTABILITY_VISIBLE',
    label: 'Every Prediction Becomes Evidence',
    question: 'What did we learn?',
    description: 'Verified outcomes are preserved and evaluated against similar future pollution events.',
    narration:
      'Decision-makers can see what the system predicted, what actually happened, and whether the confidence was justified. Mistakes remain visible. The accountability record cannot be edited after the fact.',
    sectionId: 'cc-section-accountability',
    useNormalEpisode: false,
    useCompletedVerification: true,
    showInvestigation: true,
    showBelowFold: true,
    showEvidenceChain: true,
    layers: ['verified', 'accountability'],
  },
];

export const TOTAL_STEPS = DEMO_STEPS.length;

/**
 * Get step definition by 1-indexed step number.
 */
export function getStep(step) {
  return DEMO_STEPS.find((s) => s.id === step) || DEMO_STEPS[0];
}

/**
 * Advance to next step. Returns same step if already at end.
 */
export function nextStep(current) {
  return Math.min(current + 1, TOTAL_STEPS);
}

/**
 * Go back to previous step. Returns same step if already at start.
 */
export function prevStep(current) {
  return Math.max(current - 1, 1);
}

/**
 * Final message shown after step 6 narration.
 */
export const FINAL_MESSAGE =
  'Lahore+ is not just an AQI dashboard. It is an accountable AI decision-support system for investigating pollution events.';
