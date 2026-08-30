/**
 * DecisionTrace — Evidence chain visualization for the Command Center.
 *
 * Shows: "What led the system to recommend this investigation area?"
 *
 * Visual flow: OBSERVED → DETERMINISTIC → AI → HUMAN VERIFICATION
 * Each stage connects to existing product data.
 * Clear labeling separates measured data from inference from AI.
 *
 * Phase 13: Interactive — clicking a stage selects that evidence layer,
 * dimming unrelated stages and highlighting related evidence across components.
 */

import {
  Eye, Wind, Brain, MapPin, ClipboardCheck, HelpCircle,
  ArrowDown, AlertTriangle, Database
} from 'lucide-react';
import { useEvidenceSelection, EVIDENCE_LAYERS, COMPONENT_GROUPS } from '../../context/EvidenceContext';

/* ── Stage definitions ─────────────────────────────────── */

const STAGES = [
  {
    id: 'observed',
    label: 'Observed Event',
    layer: 'observed',
    icon: Eye,
    description: 'Directly measured or retrieved data.',
    relatedGroups: [COMPONENT_GROUPS.OBSERVATION],
  },
  {
    id: 'context',
    label: 'Environmental Context',
    layer: 'deterministic',
    icon: Wind,
    description: 'Wind, weather, historical patterns.',
    relatedGroups: [COMPONENT_GROUPS.ENVIRONMENTAL_CONTEXT, COMPONENT_GROUPS.SOURCE_COMPASS],
  },
  {
    id: 'analysis',
    label: 'Deterministic Analysis',
    layer: 'deterministic',
    icon: Database,
    description: 'Episode detection, source compass, trajectory.',
    relatedGroups: [COMPONENT_GROUPS.EPISODE_DETECTION, COMPONENT_GROUPS.SOURCE_COMPASS],
  },
  {
    id: 'hypothesis',
    label: 'AI Investigation Hypothesis',
    layer: 'ai',
    icon: Brain,
    description: 'Possible contributing factors with uncertainty.',
    relatedGroups: [COMPONENT_GROUPS.HYPOTHESIS, COMPONENT_GROUPS.RECOMMENDED_ACTION],
  },
  {
    id: 'priority',
    label: 'Investigation Priority',
    layer: 'ai',
    icon: MapPin,
    description: 'Where the officer should investigate first.',
    relatedGroups: [COMPONENT_GROUPS.INVESTIGATION_PRIORITY, COMPONENT_GROUPS.EXPOSURE_CORRIDOR],
  },
  {
    id: 'verification',
    label: 'Human Verification',
    layer: 'verified',
    icon: ClipboardCheck,
    description: 'Was the recommendation useful?',
    relatedGroups: [COMPONENT_GROUPS.VERIFICATION_OUTCOME],
  },
];

const STAGE_GROUP_MAP = {
  observed: COMPONENT_GROUPS.OBSERVATION,
  context: COMPONENT_GROUPS.ENVIRONMENTAL_CONTEXT,
  analysis: COMPONENT_GROUPS.EPISODE_DETECTION,
  hypothesis: COMPONENT_GROUPS.HYPOTHESIS,
  priority: COMPONENT_GROUPS.INVESTIGATION_PRIORITY,
  verification: COMPONENT_GROUPS.VERIFICATION_OUTCOME,
};

/* ── Sub-step data extractors ──────────────────────────── */

function getStageData(stageId, episode, analysis, verification) {
  switch (stageId) {
    case 'observed':
      return [
        episode?.current_pm25 != null
          ? `PM2.5 at ${episode.current_pm25.toFixed(0)} μg/m³`
          : 'PM2.5 measurement unavailable',
        episode?.trajectory
          ? `Trajectory: ${episode.trajectory}`
          : null,
        episode?.weather_context?.variables
          ? `${episode.weather_context.variables.length} weather variables`
          : null,
      ].filter(Boolean);

    case 'context':
      return [
        episode?.source_compass?.current_wind?.sector
          ? `Wind from ${episode.source_compass.current_wind.sector} sector`
          : 'Wind data unavailable',
        episode?.source_compass?.historical?.strongest_sector
          ? `Strongest historical association: ${episode.source_compass.historical.strongest_sector} sector`
          : null,
        episode?.source_compass?.enrichment?.enrichment_factor
          ? `${episode.source_compass.enrichment.enrichment_factor.toFixed(2)}× enrichment in current sector`
          : null,
      ].filter(Boolean);

    case 'analysis':
      return [
        episode?.state ? `Episode state: ${episode.state}` : null,
        episode?.source_compass?.investigation_hint?.suggested_response_corridor
          ? `Suggested corridor: ${episode.source_compass.investigation_hint.suggested_response_corridor}`
          : null,
        episode?.source_compass?.investigation_hint?.association_level
          ? `Association level: ${episode.source_compass.investigation_hint.association_level}`
          : null,
      ].filter(Boolean);

    case 'hypothesis':
      if (!analysis?.investigation_hypotheses?.length) return ['No hypotheses generated'];
      return analysis.investigation_hypotheses.slice(0, 3).map(
        (h) => `${h.factor || h.hypothesis} (${h.confidence != null ? `${(h.confidence * 100).toFixed(0)}%` : 'N/A'})`
      );

    case 'priority':
      if (!analysis?.investigation_priority) return ['Priority not calculated'];
      const p = analysis.investigation_priority;
      return [
        `Priority: ${p.level || 'Unknown'} (score ${p.score ?? 'N/A'})`,
        p.area ? `Area: ${p.area}` : null,
        p.rationale || null,
      ].filter(Boolean);

    case 'verification':
      if (!verification?.current_outcome) return ['Awaiting field verification'];
      return [
        `Outcome: ${verification.current_outcome.outcome_type || 'Unknown'}`,
        verification.current_outcome.field_notes
          ? `Field notes: "${verification.current_outcome.field_notes}"`
          : null,
      ].filter(Boolean);

    default:
      return [];
  }
}

/* ── Component ─────────────────────────────────────────── */

export default function DecisionTrace({ episode, analysis, verification }) {
  const { selectEvidence, isHighlighted, isSelected, hasSelection } = useEvidenceSelection();

  const handleStageClick = (stage) => {
    const group = STAGE_GROUP_MAP[stage.id];
    const allRelated = STAGES.filter(s => s.layer === stage.layer).map(s => STAGE_GROUP_MAP[s.id]);
    const uniqueRelated = [...new Set([...stage.relatedGroups, ...allRelated])].filter(g => g !== group);
    selectEvidence(`trace-${stage.id}`, stage.layer, group, uniqueRelated);
  };

  return (
    <div className="decision-trace" role="region" aria-label="Decision trace — how this recommendation was produced">
      <div className="decision-trace__header">
        <HelpCircle size={16} className="decision-trace__header-icon" aria-hidden="true" />
        <div>
          <h3 className="decision-trace__title">How This Decision Was Produced</h3>
          <p className="decision-trace__subtitle">Evidence chain from observation to recommendation</p>
        </div>
        {hasSelection && (
          <button
            className="decision-trace__clear-btn"
            onClick={() => selectEvidence(null)}
            aria-label="Clear evidence selection"
            data-testid="decision-trace-clear"
          >
            Clear selection
          </button>
        )}
      </div>

      <div className="decision-trace__flow lp-motion-stagger">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          const data = getStageData(stage.id, episode, analysis, verification);
          const isLast = i === STAGES.length - 1;
          const stageGroup = STAGE_GROUP_MAP[stage.id];
          const highlighted = isHighlighted(stageGroup);
          const selected = isSelected(stageGroup);

          return (
            <div key={stage.id} className="decision-trace__stage">
              {/* Connector line */}
              {!isLast && (
                <div className={`decision-trace__connector ${!highlighted ? 'decision-trace__connector--dim' : ''}`} aria-hidden="true">
                  <ArrowDown size={12} />
                </div>
              )}

              {/* Stage card */}
              <button
                className={`decision-trace__card decision-trace__card--${stage.id} ${selected ? 'decision-trace__card--selected' : ''} ${!highlighted ? 'decision-trace__card--dim' : ''}`}
                onClick={() => handleStageClick(stage)}
                data-testid={`trace-stage-${stage.id}`}
                aria-pressed={selected}
              >
                <div className="decision-trace__card-header">
                  <Icon size={14} className="decision-trace__card-icon" aria-hidden="true" />
                  <span className="decision-trace__card-label">{stage.label}</span>
                  <span
                    className="decision-trace__layer-badge"
                    style={{
                      color: EVIDENCE_LAYERS[stage.layer]?.color,
                      borderColor: EVIDENCE_LAYERS[stage.layer]?.color,
                    }}
                  >
                    {EVIDENCE_LAYERS[stage.layer]?.label}
                  </span>
                </div>
                <p className="decision-trace__card-desc">{stage.description}</p>
                {data.length > 0 && (
                  <ul className="decision-trace__data-list">
                    {data.map((item, j) => (
                      <li key={j} className="decision-trace__data-item">{item}</li>
                    ))}
                  </ul>
                )}
              </button>
            </div>
          );
        })}
      </div>

      <div className="decision-trace__footer">
        <AlertTriangle size={12} aria-hidden="true" />
        <span>Every stage connects to existing system data. AI hypotheses are not facts — they require human field verification.</span>
      </div>
    </div>
  );
}
