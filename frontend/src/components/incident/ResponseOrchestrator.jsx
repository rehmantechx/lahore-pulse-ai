/**
 * ResponseOrchestrator — Pollution incident response workflow.
 *
 * Turns a detected pollution episode into an explainable,
 * simulated response workflow based on Punjab's existing
 * published air-quality response structure.
 *
 * CRITICAL:
 * - This is a PROTOTYPE/SIMULATION, not live government integration.
 * - Investigation signals are NOT confirmed emission sources.
 * - No fake government dispatch, no fake department notifications.
 * - All response domains are traceable to Punjab's response framework.
 *
 * Consumes: GET /api/v1/episode (via useEpisodeIntelligence hook).
 * No new backend endpoint required.
 */

import { useState, useCallback, useMemo } from 'react';
import { useEpisodeIntelligence } from '../../hooks/useEpisodeIntelligence';
import {
  Circle,
  Play,
  CheckCircle,
  CircleDot,
  Square,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { useForecast } from '../../hooks/useForecast';
import { PM25_LEVELS } from '../../constants';
import SourceCompass from '../compass/SourceCompass';
import { RESPONSE_DOMAINS, evaluateDomain } from '../../config/responseDomains';

// ── Workflow States ──────────────────────────────────────────

const WORKFLOW_STATES = [
  { id: 'detected', label: 'Detected', icon: Circle, iconProps: { size: 14 } },
  { id: 'investigate', label: 'Investigate', icon: Play, iconProps: { size: 14 } },
  { id: 'acknowledge', label: 'Acknowledge', icon: CheckCircle, iconProps: { size: 14 } },
  { id: 'review', label: 'Review', icon: CircleDot, iconProps: { size: 14 } },
  { id: 'closed', label: 'Closed', icon: Square, iconProps: { size: 14 } },
];

// ── SLA Timing (from Punjab AQI emergency response protocols) ──

const SLA_TIMING = {
  detection_to_investigation: '30 min',
  investigation_to_acknowledgment: '2 hr',
  full_response_window: '4 hr',
  source: 'Punjab AQI Emergency Response Protocol — interim smog emergency orders',
};

// ── Helper: get PM2.5 severity label ────────────────────────

function getSeverityLabel(pm25) {
  if (pm25 === null || pm25 === undefined) return 'Unknown';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}



// ── Helper: determine workflow posture from episode state ────

function getWorkflowPosture(episodeState) {
  switch (episodeState) {
    case 'episode':
      return { mode: 'active', initialStep: -1, label: 'Active Investigation' };
    case 'improving':
      return { mode: 'review', initialStep: 3, label: 'Review / Monitor' };
    case 'normal':
      return { mode: 'standby', initialStep: -1, label: 'Standby' };
    case 'uncertain':
      return { mode: 'standby', initialStep: -1, label: 'Standby' };
    default:
      return { mode: 'standby', initialStep: -1, label: 'Standby' };
  }
}

// ═════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═════════════════════════════════════════════════════════════

export default function ResponseOrchestrator() {
  const { episode, loading } = useEpisodeIntelligence();
  const { forecasts } = useForecast();
  // Use observed PM2.5 from episode endpoint, fall back to forecast.
  const currentPM25 = episode?.current_pm25 ?? forecasts?.['1']?.predicted_pm25 ?? null;

  // Workflow interaction state (session-local, not persisted)
  const [currentStep, setCurrentStep] = useState(-1);
  const [expandedDomains, setExpandedDomains] = useState(new Set());
  const [showEvidence, setShowEvidence] = useState(false);

  // Reset workflow when episode state changes
  const episodeState = episode?.state || 'uncertain';
  const posture = getWorkflowPosture(episodeState);

  // Evaluate all domains
  const domainResults = useMemo(() => {
    if (!episode) return [];
    const weatherVars = episode.weather_context?.variables || [];
    return RESPONSE_DOMAINS.map((domain) => {
      const evaluation = evaluateDomain(domain, weatherVars);
      const isActive = episodeState === 'normal' || episodeState === 'uncertain'
        ? false
        : evaluation.matchCount >= 1;
      return { ...domain, evaluation, isActive };
    });
  }, [episode, episodeState]);

  // Active domains (only during episode/improving, with at least 1 match)
  const activeDomains = useMemo(() => {
    return domainResults.filter((d) => d.isActive);
  }, [domainResults]);

  // Initialize step when posture changes
  const effectiveStep = currentStep >= 0 ? currentStep : posture.initialStep;

  const toggleDomain = useCallback((id) => {
    setExpandedDomains((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const advanceWorkflow = useCallback(() => {
    setCurrentStep((prev) => {
      if (prev < 0) return posture.initialStep;
      if (prev >= WORKFLOW_STATES.length - 1) return prev;
      return prev + 1;
    });
  }, [posture.initialStep]);

  const resetWorkflow = useCallback(() => {
    setCurrentStep(-1);
    setShowEvidence(false);
  }, []);

  // ── Loading state ──────────────────────────────────────────
  if (loading && !episode) {
    return (
      <div className="surface" style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-4) var(--sp-5)' }}>
        <div className="section-header">
          <h2 className="section-header__title">Response Orchestrator</h2>
          <span className="section-header__subtitle">Loading...</span>
        </div>
      </div>
    );
  }

  // ── No episode data ────────────────────────────────────────
  if (!episode) return null;

  // ── UNCERTAIN state ────────────────────────────────────────
  if (episodeState === 'uncertain') {
    return (
      <div className="surface" style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-4) var(--sp-5)' }}>
        <div className="section-header">
          <h2 className="section-header__title">Response Orchestrator</h2>
          <span className="section-header__subtitle">STANDBY</span>
        </div>
        <div style={{
          padding: 'var(--sp-4)',
          background: 'var(--slate-50)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--slate-200)',
          fontSize: 'var(--text-sm)',
          color: 'var(--slate-500)',
        }}>
          Insufficient current data for a reliable incident workflow.
        </div>
        <div style={{
          marginTop: 'var(--sp-3)',
          fontSize: '10px',
          color: 'var(--slate-400)',
          fontStyle: 'italic',
        }}>
          Response workflow simulation. Investigation signals are not confirmed emission sources
          and do not represent live government dispatch.
        </div>
      </div>
    );
  }

  // ── NORMAL state ───────────────────────────────────────────
  if (episodeState === 'normal') {
    return (
      <div className="surface" style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-4) var(--sp-5)' }}>
        <div className="section-header">
          <h2 className="section-header__title">Response Orchestrator</h2>
          <span className="section-header__subtitle">Standby</span>
        </div>
        <div style={{
          padding: 'var(--sp-4)',
          background: 'var(--green-50, #f0fdf4)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid #bbf7d0',
          fontSize: 'var(--text-sm)',
          color: '#166534',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--sp-2)',
        }}>
          <Circle size={18} color="#166534" fill="#166534" />
          <div>
            <strong>No active pollution incident.</strong>
            <div style={{ marginTop: 4, fontSize: 'var(--text-xs)', color: '#15803d' }}>
              City status: NORMAL &middot; Response orchestration: Standby &middot; No investigation workflow currently required.
            </div>
          </div>
        </div>
        <div style={{
          marginTop: 'var(--sp-3)',
          fontSize: '10px',
          color: 'var(--slate-400)',
          fontStyle: 'italic',
        }}>
          Response workflow simulation. Investigation signals are not confirmed emission sources
          and do not represent live government dispatch.
        </div>
      </div>
    );
  }

  // ── ACTIVE / IMPROVING state ───────────────────────────────
  const isEpisode = episodeState === 'episode';
  const isImproving = episodeState === 'improving';

  const stateColor = isEpisode ? '#dc2626' : '#a16207';
  const stateBg = isEpisode ? '#fef2f2' : '#fefce8';
  const stateLabel = isEpisode ? 'POLLUTION INCIDENT ACTIVE' : 'EPISODE IMPROVING';

  return (
    <div className="surface" style={{ marginBottom: 'var(--sp-4)', padding: 'var(--sp-4) var(--sp-5)' }}>
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="section-header">
        <h2 className="section-header__title">Response Orchestrator</h2>
        <span className="section-header__subtitle">
          {isImproving ? 'Review / Monitor' : 'Response Workflow Simulation'}
        </span>
      </div>

      {/* ── 1. Incident Header ──────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'auto 1fr auto',
        gap: 'var(--sp-3)',
        alignItems: 'center',
        padding: 'var(--sp-3) var(--sp-4)',
        background: stateBg,
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${stateColor}22`,
        marginBottom: 'var(--sp-4)',
      }}>
        {/* State indicator */}
        <div style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: stateColor,
          animation: isEpisode ? 'pulse 2s infinite' : 'none',
        }} />
        {/* State label + PM2.5 */}
        <div>
          <div style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: stateColor,
          }}>
            {stateLabel}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', marginTop: 2 }}>
            PM2.5: <strong>{currentPM25 !== null ? `${currentPM25.toFixed(1)} μg/m³` : '—'}</strong>
            {episode.trajectory && episode.trajectory !== 'unknown' && (
              <span style={{ marginLeft: 'var(--sp-2)', color: 'var(--slate-400)' }}>
                · {episode.trajectory_description || episode.trajectory}
              </span>
            )}
          </div>
        </div>
        {/* Severity */}
        <div style={{
          fontSize: '10px',
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 3,
          background: `${stateColor}11`,
          color: stateColor,
          border: `1px solid ${stateColor}33`,
        }}>
          {getSeverityLabel(currentPM25)}
        </div>
      </div>

      {/* ── 2. Why Flagged ──────────────────────────────────── */}
      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <button
          onClick={() => setShowEvidence(!showEvidence)}
          aria-expanded={showEvidence}
          aria-controls="evidence-drawer"
          aria-label="Why was this flagged? Toggle evidence details"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            color: 'var(--slate-600)',
            padding: 'var(--sp-1) 0',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span style={{
            display: 'inline-block',
            transition: 'transform 0.15s',
            transform: showEvidence ? 'rotate(90deg)' : 'rotate(0deg)',
          }}>▶</span>
          Why was this flagged?
        </button>
        {showEvidence && (
          <div id="evidence-drawer" role="region" aria-label="Evidence details" style={{
            marginTop: 'var(--sp-2)',
            padding: 'var(--sp-3)',
            background: 'var(--slate-50)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--slate-100)',
            fontSize: 'var(--text-xs)',
            color: 'var(--slate-600)',
            lineHeight: 'var(--leading-relaxed)',
          }}>
            <div style={{ marginBottom: 'var(--sp-2)' }}>
              <strong>Trend:</strong> {episode.trajectory_description || `PM2.5 trajectory is ${episode.trajectory}.`}
            </div>
            <div style={{ marginBottom: 'var(--sp-2)' }}>
              <strong>Forecast trajectory:</strong> {episode.highest_forecast_horizon
                ? `Highest forecast: ${episode.highest_forecast_value?.toFixed(1)} μg/m³ at +${episode.highest_forecast_horizon}h`
                : 'Forecast trajectory data unavailable.'
              }
            </div>
            <div style={{ marginBottom: 'var(--sp-2)' }}>
              <strong>Data status:</strong> {episode.data_status || 'Unknown'}
              {episode.freshness_hours !== null && episode.freshness_hours !== undefined && (
                <span> · {episode.freshness_hours.toFixed(1)}h since last data</span>
              )}
            </div>
            {episode.weather_context?.variables?.length > 0 && (
              <div>
                <strong>Environmental context:</strong>{' '}
                {episode.weather_context.variables
                  .filter((v) => v.matches_pattern)
                  .map((v) => `${v.label} ${v.direction} typical (${v.current_value?.toFixed(1)} ${v.unit})`)
                  .join(', ') || 'No weather factors match episode patterns.'}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 2b. Source Compass — Directional Intelligence ──── */}
      {episode?.source_compass && (
        <div style={{ marginBottom: 'var(--sp-3)' }}>
          <SourceCompass sourceCompass={episode.source_compass} compact={true} />
        </div>
      )}

      {/* ── 3. Investigation Signals ────────────────────────── */}
      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <div style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--slate-500)',
          marginBottom: 'var(--sp-2)',
        }}>
          Investigation Signals
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
          {domainResults.map((domain) => {
            const statusLabel = domain.isActive ? 'INVESTIGATE' : 'LOW';
            const statusColor = domain.isActive ? '#92400e' : 'var(--slate-400)';
            const statusBg = domain.isActive ? '#fffbeb' : 'var(--slate-50)';
            const statusBorder = domain.isActive ? '#fde68a' : 'var(--slate-200)';
            const isExpanded = expandedDomains.has(domain.id);

            return (
              <div key={domain.id} style={{
                background: 'var(--surface-raised, #fff)',
                border: `1px solid ${domain.isActive ? '#fde68a' : 'var(--slate-100)'}`,
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
              }}>
                {/* Domain header */}
                <button
                  onClick={() => toggleDomain(domain.id)}
                  aria-expanded={isExpanded}
                  aria-controls={`domain-drawer-${domain.id}`}
                  aria-label={`${domain.name} investigation signal — ${statusLabel}. Click to ${isExpanded ? 'collapse' : 'expand'} details.`}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--sp-2) var(--sp-3)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                    <span style={{ fontSize: 'var(--text-sm)' }}>{domain.icon}</span>
                    <span style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 600,
                      color: 'var(--slate-800)',
                    }}>{domain.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                    <span style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: 2,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      background: statusBg,
                      color: statusColor,
                      border: `1px solid ${statusBorder}`,
                    }}>
                      {statusLabel}
                    </span>
                    <span style={{
                      fontSize: 10,
                      color: 'var(--slate-400)',
                      transition: 'transform 0.15s',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    }}>▶</span>
                  </div>
                </button>

                {/* Expanded evidence drawer */}
                {isExpanded && (
                  <div id={`domain-drawer-${domain.id}`} role="region" aria-label={`${domain.name} evidence details`} style={{
                    padding: '0 var(--sp-3) var(--sp-3)',
                    borderTop: '1px solid var(--slate-100)',
                    fontSize: 'var(--text-xs)',
                    color: 'var(--slate-500)',
                    lineHeight: 'var(--leading-relaxed)',
                  }}>
                    <div style={{ marginBottom: 'var(--sp-2)' }}>
                      {domain.description}
                    </div>
                    <div style={{ marginBottom: 'var(--sp-2)' }}>
                      <strong>Evidence:</strong> {domain.evaluation.reason}
                    </div>
                    <div style={{ marginBottom: 'var(--sp-2)' }}>
                      <strong>Matched factors:</strong>{' '}
                      {domain.evaluation.matchedVars.length > 0
                        ? domain.evaluation.matchedVars.join(', ')
                        : 'None'}
                    </div>
                    <div>
                      <strong>Official basis:</strong> {domain.officialBasis}
                    </div>
                    <div style={{
                      marginTop: 'var(--sp-2)',
                      paddingTop: 'var(--sp-2)',
                      borderTop: '1px solid var(--slate-50)',
                      fontStyle: 'italic',
                      color: 'var(--slate-400)',
                    }}>
                      This is an investigation signal, not a confirmed source attribution.
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 4. Workflow Pipeline ────────────────────────────── */}
      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <div style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--slate-500)',
          marginBottom: 'var(--sp-3)',
        }}>
          Response Workflow
        </div>

        {/* Pipeline visualization */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          overflowX: 'auto',
          padding: 'var(--sp-2) 0',
        }}>
          {WORKFLOW_STATES.map((step, idx) => {
            const isActive = idx <= effectiveStep;
            const isCurrent = idx === effectiveStep;
            return (
              <div key={step.id} style={{ display: 'flex', alignItems: 'center' }}>
                {/* Step node */}
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                  minWidth: 80,
                }}>
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    background: isActive ? stateColor : 'var(--slate-100)',
                    color: isActive ? '#fff' : 'var(--slate-400)',
                    border: isCurrent ? `2px solid ${stateColor}` : '2px solid transparent',
                    boxShadow: isCurrent ? `0 0 0 3px ${stateColor}22` : 'none',
                    transition: 'all 0.2s',
                  }}>
                    <step.icon {...step.iconProps} />
                  </div>
                  <span style={{
                    fontSize: 9,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: isActive ? stateColor : 'var(--slate-400)',
                    textAlign: 'center',
                    whiteSpace: 'nowrap',
                  }}>
                    {step.label}
                  </span>
                </div>
                {/* Connector line */}
                {idx < WORKFLOW_STATES.length - 1 && (
                  <div style={{
                    width: 24,
                    height: 2,
                    background: idx < effectiveStep ? stateColor : 'var(--slate-200)',
                    margin: '0 -4px',
                    marginTop: -14,
                    transition: 'background 0.3s',
                  }} />
                )}
              </div>
            );
          })}
        </div>

        {/* Current step description */}
        {effectiveStep >= 0 && effectiveStep < WORKFLOW_STATES.length && (
          <div style={{
            marginTop: 'var(--sp-3)',
            padding: 'var(--sp-3)',
            background: `${stateColor}08`,
            borderRadius: 'var(--radius-md)',
            border: `1px solid ${stateColor}22`,
            fontSize: 'var(--text-xs)',
            color: 'var(--slate-600)',
          }}>
            {effectiveStep === 0 && (
              <span>Pollution incident <strong>detected</strong> by rule-based episode intelligence. Investigation workflow initiated.</span>
            )}
            {effectiveStep === 1 && (
              <span>Investigation task generated for {activeDomains.length} domain{activeDomains.length !== 1 ? 's' : ''}: {activeDomains.map((d) => d.name).join(', ') || 'all domains'}.</span>
            )}
            {effectiveStep === 2 && (
              <span>Response step <strong>acknowledged</strong> (simulation). Investigation signals reviewed by operator.</span>
            )}
            {effectiveStep === 3 && (
              <span>
                {isImproving
                  ? 'Episode is improving. Continue monitoring before initiating additional investigation steps.'
                  : 'Review required. Assess whether episode conditions persist or are clearing.'}
              </span>
            )}
            {effectiveStep === 4 && (
              <span>Workflow <strong>closed</strong>. No further action required for this incident.</span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-3)' }}>
          {effectiveStep < 0 && (
            <button
              className="btn btn--primary btn--sm"
              onClick={() => setCurrentStep(0)}              aria-label="Start response workflow"              style={{ fontSize: 'var(--text-xs)' }}
            >
              Start Response Workflow
            </button>
          )}
          {effectiveStep >= 0 && effectiveStep < WORKFLOW_STATES.length - 1 && (
            <button
              className="btn btn--primary btn--sm"
              onClick={advanceWorkflow}
              aria-label={`Advance to ${WORKFLOW_STATES[effectiveStep + 1]?.label}`}
              style={{ fontSize: 'var(--text-xs)' }}
            >
              Advance to: {WORKFLOW_STATES[effectiveStep + 1]?.label}
            </button>
          )}
          {effectiveStep >= 0 && (
            <button
              className="btn btn--sm"
              onClick={resetWorkflow}
              aria-label="Reset workflow"
              style={{ fontSize: 'var(--text-xs)', color: 'var(--slate-500)' }}
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* ── 5. SLA / Timing ─────────────────────────────────── */}
      <div style={{
        marginBottom: 'var(--sp-3)',
        padding: 'var(--sp-2) var(--sp-3)',
        background: 'var(--slate-50)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--slate-100)',
      }}>
        <div style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--slate-500)',
          marginBottom: 4,
        }}>
          Target Response Windows
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-4)', fontSize: 'var(--text-xs)', color: 'var(--slate-600)' }}>
          <span>Detection → Investigation: <strong>{SLA_TIMING.detection_to_investigation}</strong></span>
          <span>Investigation → Acknowledgment: <strong>{SLA_TIMING.investigation_to_acknowledgment}</strong></span>
          <span>Full response: <strong>{SLA_TIMING.full_response_window}</strong></span>
        </div>
        <div style={{ fontSize: 9, color: 'var(--slate-400)', marginTop: 4 }}>
          Source: {SLA_TIMING.source}
        </div>
      </div>

      {/* ── 6. Disclaimer ───────────────────────────────────── */}
      <div style={{
        fontSize: 10,
        color: 'var(--slate-400)',
        fontStyle: 'italic',
        lineHeight: 'var(--leading-relaxed)',
      }}>
        Response workflow simulation. Investigation signals are not confirmed emission sources
        and do not represent live government dispatch.
      </div>
    </div>
  );
}
