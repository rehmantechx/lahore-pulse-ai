/**
 * GovCommandCenter — AI Pollution Incident Investigation Workspace.
 *
 * Tells a story: SOMETHING HAPPENED → DATA → MODELS → AI INVESTIGATION → UNCERTAINTY → ACTIONS
 *
 * EXACT HIERARCHY:
 *   1. COMMAND CENTER HEADER
 *   2. COMMAND STRIP — operational status chips
 *   3. INCIDENT STATUS — compact: PM2.5, trajectory, severity, data status
 *   4. WHAT HAPPENED — AI event summary + severity assessment
 *   5. INVESTIGATION PRIORITY — visual centerpiece
 *   6. AI INVESTIGATION BRIEF — facts, inferences, hypotheses
 *   7. LIMITATIONS & UNCERTAINTY — responsible AI
 *   8. RECOMMENDED ACTIONS — top 3 actions
 *   ── BELOW THE FOLD ──
 *   9. Geographic Coverage (map)
 *  10. Verification Context — historical learning loop
 *  11. Submit Investigation Verification — human feedback form
 *  12. Investigation Accountability — historical context from verified outcomes
 *  13. Trust & Accountability
 *  14. Historical Trend
 *  15. Technical Deep Dive
 */

import { useState, useEffect, useMemo } from 'react';
import { useForecast } from '../hooks/useForecast';
import { useInvestigationAnalysis } from '../hooks/useInvestigationAnalysis';
import { useExposureGeometry } from '../hooks/useExposureGeometry';
import DataFreshness from '../components/common/DataFreshness';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import OperationsMap from '../components/command/OperationsMap';
import ExposureIntelligenceMap from '../components/exposure/ExposureIntelligenceMap';
import EpisodeStateHero from '../components/incident/EpisodeStateHero';
import AISummary from '../components/incident/AISummary';
import AIPriorityCard from '../components/incident/AIPriorityCard';
import AIAnalysisBrief from '../components/incident/AIAnalysisBrief';
import AIUncertainty from '../components/incident/AIUncertainty';
import AIRecommendedActions from '../components/incident/AIRecommendedActions';
import TrustSnapshot from '../components/incident/TrustSnapshot';
import TechnicalDeepDive from '../components/forecast/TechnicalDeepDive';
import PredictionAccountability from '../components/forecast/PredictionAccountability';
import HistoricalTrendChart from '../components/forecast/HistoricalTrendChart';
import InvestigationVerification from '../components/incident/InvestigationVerification';
import HistoricalVerificationContext from '../components/incident/HistoricalVerificationContext';
import InvestigationLearning from '../components/incident/InvestigationLearning';
import DemoController from '../components/command/DemoController';
import DecisionTrace from '../components/command/DecisionTrace';
import WhyDifferent from '../components/command/WhyDifferent';
import CannotKnow from '../components/common/CannotKnow';
import ErrorBoundary from '../components/common/ErrorBoundary';
import ProgressiveDisclosure from '../components/common/ProgressiveDisclosure';
import PredictionReceipt from '../components/forecast/PredictionReceipt';
import ModelMistakes from '../components/forecast/ModelMistakes';
import ModelSuccesses from '../components/forecast/ModelSuccesses';
import ConfidenceCalibration from '../components/forecast/ConfidenceCalibration';
import WhyTrustThis from '../components/forecast/WhyTrustThis';
import { getStep } from '../demo/stateMachine';
import { getSimulationState } from '../demo/simulationState';
import InvestigationProgress from '../components/command/InvestigationProgress';
import AccountabilityChain from '../components/command/AccountabilityChain';
import AccountabilityLoop from '../components/command/AccountabilityLoop';
import AuditTrail from '../components/command/AuditTrail';
import WhyAccountability from '../components/command/WhyAccountability';
import ExecutiveDecisionSummary from '../components/command/ExecutiveDecisionSummary';
import InvestigationContextBar from '../components/command/InvestigationContextBar';
import { EvidenceProvider, useEvidenceSelection } from '../context/EvidenceContext';
import { useHealth } from '../hooks/useHealth';
import { useEpisodeIntelligence } from '../hooks/useEpisodeIntelligence';
import { useVerification } from '../hooks/useVerification';
import useScrollReveal from '../hooks/useScrollReveal';
import useTilt3D from '../hooks/useTilt3D';
import { useInvestigationLearning } from '../hooks/useInvestigationLearning';
import { getStations } from '../services/api';
import { Diamond, TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { useDemoData } from '../demo';

/* ── Helpers ───────────────────────────────────────────────── */

function statusChip(state) {
  switch (state) {
    case 'EPISODE':
      return { label: 'ACTIVE INCIDENT', cls: 'cc-chip--danger' };
    case 'IMPROVING':
      return { label: 'IMPROVING', cls: 'cc-chip--warn' };
    case 'UNCERTAIN':
      return { label: 'UNCERTAIN', cls: '' };
    default:
      return { label: 'NOMINAL', cls: 'cc-chip--success' };
  }
}

function trendChip(direction) {
  switch (direction) {
    case 'worsening':
      return { label: 'RISING', cls: 'cc-chip--danger', Icon: TrendingUp };
    case 'improving':
      return { label: 'FALLING', cls: 'cc-chip--success', Icon: TrendingDown };
    default:
      return { label: 'STABLE', cls: 'cc-chip--active', Icon: Minus };
  }
}

/* ── ScrollReveal wrapper — 3D scroll-triggered reveal ──────── */
function ScrollReveal3D({ children, className = '', variant = 'default', ...props }) {
  const { ref, isVisible } = useScrollReveal({ threshold: 0.1 });
  const variantClass = variant === 'left' ? 'scroll-hidden-3d--left'
    : variant === 'right' ? 'scroll-hidden-3d--right'
    : variant === 'scale' ? 'scroll-hidden-3d--scale'
    : '';
  return (
    <div
      ref={ref}
      className={`${isVisible ? 'scroll-revealed-3d' : variantClass || 'scroll-hidden-3d'} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

/* ── TiltCard wrapper — mouse-driven 3D perspective tilt ──── */
function TiltCard({ children, className = '', ...props }) {
  const { ref, style } = useTilt3D({ maxTilt: 6, scale: 1.015, speed: 350, glare: true });
  return (
    <div
      ref={ref}
      className={`tilt-3d-card ${className}`}
      style={{ ...style, transformStyle: 'preserve-3d', position: 'relative' }}
      {...props}
    >
      {children}
    </div>
  );
}

/* ── Component ─────────────────────────────────────────────── */

export default function GovCommandCenter() {
  return (
    <EvidenceProvider>
      <GovCommandCenterInner />
    </EvidenceProvider>
  );
}

function GovCommandCenterInner() {
  /* ── Evidence selection context ──────────────────────── */
  const { hasSelection, isHighlighted } = useEvidenceSelection();
  /* ── Demo mode override ──────────────────────────────── */
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const demoStep = isDemo ? (demoData.demoStep || 1) : 1;
  const stepConfig = isDemo ? getStep(demoStep) : null;
  const simulation = isDemo ? getSimulationState(demoStep) : null;

  /* ── Live data hooks ──────────────────────────────────── */
  const liveForecast = useForecast();
  const liveEpisode = useEpisodeIntelligence();
  const liveInvestigation = useInvestigationAnalysis();
  const liveExposure = useExposureGeometry();

  /* ── Demo step-driven data selection ────────────────────── */
  const showInvestigation = isDemo ? stepConfig.showInvestigation : true;
  const showBelowFold = isDemo ? stepConfig.showBelowFold : true;
  const useCompletedVerification = isDemo ? stepConfig.useCompletedVerification : false;

  /* ── Use demo data when available, else live ──────────── */
  const forecasts = isDemo ? demoData.forecasts : liveForecast.forecasts;
  const errors = isDemo ? [] : liveForecast.errors;
  const forecastStatus = isDemo ? demoData.forecastStatus : liveForecast.forecastStatus;
  const loading = isDemo ? false : liveForecast.loading;
  const error = isDemo ? null : liveForecast.error;
  const refresh = liveForecast.refresh;

  // In demo: steps 1 uses normal episode, steps 2+ uses incident episode
  const demoEpisode = isDemo
    ? (stepConfig.useNormalEpisode ? demoData.episodeNormal : demoData.episode)
    : null;

  // Demo PM2.5 progression: 85→110→135→150→165→172→181 across 7 steps
  const STEP_PM25 = { 1: 85, 2: 110, 3: 135, 4: 150, 5: 165, 6: 172, 7: 181 };
  const demoEpisodeWithProgression = isDemo && demoEpisode
    ? { ...demoEpisode, current_pm25: STEP_PM25[demoStep] || demoEpisode.current_pm25 }
    : demoEpisode;

  const episode = isDemo ? demoEpisodeWithProgression : liveEpisode.episode;

  const investigationAnalysis = (isDemo && showInvestigation)
    ? demoData.investigationAnalysis?.analysis || null
    : isDemo ? null : liveInvestigation.analysis;
  const investigationLoading = isDemo ? false : liveInvestigation.loading;
  const investigationError = isDemo ? null : liveInvestigation.error;
  const exposureGeometry = (isDemo && showBelowFold)
    ? demoData.exposureGeometry || null
    : isDemo ? null : liveExposure.exposure;
  const exposureLoading = isDemo ? false : liveExposure.loading;
  const { online } = useHealth();

  /* ── Verification hook ────────────────────────────── */
  const liveVerification = useVerification({ autoRefresh: false });
  const verificationStats = isDemo
    ? demoData.verificationStats || null
    : liveVerification.stats;
  // In demo: step 5 uses pending verification, step 6+ uses completed verification
  const verificationContext = isDemo
    ? (useCompletedVerification ? demoData.verificationCompleted : demoData.verificationPending)
    : liveVerification.context;
  const verificationSubmitting = isDemo ? false : liveVerification.submitting;
  const verificationSubmitSuccess = isDemo ? false : liveVerification.submitSuccess;
  const verificationError = isDemo ? null : liveVerification.error;

  /* ── Investigation Learning hook ──────────────────────── */
  const liveLearning = useInvestigationLearning();
  const investigationLearning = isDemo
    ? demoData.investigationLearning || null
    : liveLearning.learning;
  const learningLoading = isDemo ? false : liveLearning.loading;
  const learningError = isDemo ? null : liveLearning.error;

  const [selectedHorizon, setSelectedHorizon] = useState(1);
  const [stations, setStations] = useState([]);
  const [clock, setClock] = useState(() => new Date());

  /* ── Derived data ──────────────────────────────────────── */
  const currentPM25 = episode?.current_pm25 ?? forecasts?.['1']?.predicted_pm25 ?? null;
  const dataQuality = forecasts?.['1']?.data_quality;
  const episodeState = (episode?.state || 'normal').toUpperCase();
  const episodeTrajectory = (episode?.trajectory || 'unknown').toLowerCase();
  const trend = episodeTrajectory === 'rising' ? 'worsening'
    : episodeTrajectory === 'falling' ? 'improving'
    : 'stable';
  const windDir = episode?.source_compass?.current_wind?.sector || null;
  const windSpeed = episode?.source_compass?.current_wind?.wind_speed_ms || null;
  const analysisComplete = investigationAnalysis?.analysis_status === 'complete';
  const hasAnalysis = Boolean(investigationAnalysis);
  const recommendedCount = investigationAnalysis?.recommended_actions?.length || 0;

  const status = useMemo(() => statusChip(episodeState), [episodeState]);
  const trendInfo = useMemo(() => trendChip(trend), [trend]);

  /* ── DecisionState — inline derivation from PM2.5 ───────── */
  const decisionState = useMemo(() => {
    const pm25 = currentPM25 ?? 0;
    const hasVerification = Boolean(verificationContext);
    if (hasVerification && pm25 >= 150) return { state: 'VERIFIED CRITICAL', cls: 'cc-chip--danger', color: '#B91C1C' };
    if (pm25 >= 150) return { state: 'CRITICAL', cls: 'cc-chip--danger', color: '#B91C1C' };
    if (pm25 >= 120) return { state: 'ELEVATED', cls: 'cc-chip--warn', color: '#B45309' };
    if (pm25 >= 100) return { state: 'WATCH', cls: 'cc-chip--active', color: '#0F766E' };
    return { state: 'MONITOR', cls: 'cc-chip--success', color: '#15803D' };
  }, [currentPM25, verificationContext]);

  /* ── Clock ─────────────────────────────────────────────── */
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  /* ── Stations ──────────────────────────────────────────── */
  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    async function fetchStations() {
      try {
        const data = await getStations({ signal: AbortSignal.timeout(10000) });
        if (!cancelled) setStations(data.stations || []);
      } catch { /* optional */ }
    }
    fetchStations();
    return () => { cancelled = true; };
  }, [isDemo]);

  /* ── Loading / Error states ────────────────────────────── */
  if (error && !forecasts) {
    return (
      <div className="page page--wide">
        <div className="cc-header">
          <div className="cc-header__title">
            <span className="cc-header__title-main">Lahore+ Command Center</span>
            <span className="cc-header__title-sub">Lahore — System Error</span>
          </div>
        </div>
        <ErrorState error={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="page page--wide">

      {/* 1. COMMAND CENTER HEADER */}
      <div className="cc-header cc-hero-3d">
        <div className="cc-header__title">
          <span className="cc-header__title-main">Lahore+ Command Center</span>
          <span className="cc-header__title-sub">
            Lahore — {isDemo ? (
              <span className="cc-demo-badge" data-testid="demo-badge">DEMO SCENARIO — Active Incident Investigation</span>
            ) : loading ? 'Connecting...' : 'Live Intelligence'}
          </span>
        </div>
        <div className="cc-header__status">
          <span className="cc-header__clock">
            {clock.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })} PKT
          </span>
          {!loading && (
            <DataFreshness
              timestamp={dataQuality?.data_timestamp}
              freshnessHours={dataQuality?.freshness_hours}
              freshness={forecastStatus?.freshness}
            />
          )}
          <span
            className={`status-dot ${online ? 'status-dot--online' : 'status-dot--offline'}`}
            aria-hidden="true"
          />
        </div>
      </div>

      {loading && <LoadingState message="Initializing investigation workspace..." />}

      {!loading && (<>

      {/* 2. COMMAND STRIP */}
      <div className="cc-strip cc-strip-3d" role="status" aria-label="Operational status summary">
        <span className={`cc-chip ${status.cls}`}>
          <span className="cc-chip__label">STATUS</span> {status.label}
        </span>
        <span className={`cc-chip ${trendInfo.cls}`}>
          <span className="cc-chip__label">TRAJECTORY</span> {trendInfo.Icon && <trendInfo.Icon size={14} />} {trendInfo.label}
        </span>
        <span className={`cc-chip ${windDir ? 'cc-chip--active' : ''}`}>
          <span className="cc-chip__label">WIND</span>{' '}
          {windDir ? `${windDir} ${windSpeed ? `${windSpeed} m/s` : ''}` : '—'}
        </span>
        <span className={`cc-chip ${currentPM25 != null ? 'cc-chip--active' : ''}`}>
          <span className="cc-chip__label">PM2.5</span>{' '}
          {currentPM25 != null ? `${currentPM25.toFixed(0)} μg/m³` : '—'}
        </span>
        <span className={`cc-chip ${hasAnalysis ? (analysisComplete ? 'cc-chip--success' : 'cc-chip--warn') : ''}`}>
          <span className="cc-chip__label">AI ANALYSIS</span>{' '}
          {investigationLoading ? 'ANALYZING...' : hasAnalysis ? (analysisComplete ? `${recommendedCount} ACTIONS` : 'PARTIAL') : 'UNAVAILABLE'}
        </span>
        {/* Phase 29: Inline DecisionState badge */}
        {isDemo && (
          <span className={`cc-chip ${decisionState.cls}`} style={{ borderLeft: `3px solid ${decisionState.color}` }}>
            <span className="cc-chip__label">DECISION</span> {decisionState.state}
          </span>
        )}
      </div>

      {errors.length > 0 && (
        <div className="info-box info-box--warn" style={{ marginBottom: 'var(--sp-4)' }}>
          <strong>Partial response:</strong> {errors.length} horizon(s) returned errors.
        </div>
      )}

      {/* SIGNATURE CTA — "Why do we trust this alert?" */}
      {showBelowFold && (
        <div
          className="cc-trust-cta demo-section-reveal lp-fade-up"
          data-demo-section="cc-trust-cta"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--sp-3)',
            padding: 'var(--sp-3) var(--sp-5)',
            marginBottom: 'var(--sp-4)',
            background: 'var(--lp-surface)',
            border: '1px solid var(--lp-border)',
            borderRadius: 8,
            cursor: 'pointer',
            transition: 'border-color 200ms ease, background 200ms ease',
          }}
          onClick={() => {
            const el = document.querySelector('[data-demo-section="cc-section-why-trust"]');
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              const el = document.querySelector('[data-demo-section="cc-section-why-trust"]');
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--lp-accent, #facc15)';
            e.currentTarget.style.background = 'var(--lp-surface-hover, #1e293b)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--lp-border)';
            e.currentTarget.style.background = 'var(--lp-surface)';
          }}
        >
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--lp-text-primary)' }}>
            Why do we trust this alert?
          </span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)' }}>
            See the evidence →
          </span>
        </div>
      )}

      {/* EXECUTIVE DECISION SUMMARY — Phase 12 */}
      <ExecutiveDecisionSummary
        demoStep={demoStep}
        episode={episode}
        investigationAnalysis={investigationAnalysis}
        verificationContext={verificationContext}
        exposureGeometry={exposureGeometry}
      />

      {/* ACCOUNTABILITY LOOP — Above-the-fold differentiation visual */}
      <AccountabilityLoop receipt={isDemo ? demoData.predictionReceipt : null} />

      {/* WHY ACCOUNTABILITY — One-line "Why This Matters" moment */}
      <WhyAccountability />

      {/* PERSISTENT INVESTIGATION CONTEXT — Phase 13 */}
      <InvestigationContextBar
        demoStep={demoStep}
        episode={episode}
        verificationContext={verificationContext}
        isDemo={isDemo}
      />

      {/* ── PHASE: DETECT ── What's happening with Lahore's air right now */}
      <div className="cc-phase-label" style={{
        display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
        margin: 'var(--sp-5) 0 var(--sp-3)', paddingBottom: 'var(--sp-2)',
        borderBottom: '2px solid var(--lp-border)',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--lp-accent)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Phase 1 — Detect
        </span>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)' }}>
          What's happening with Lahore's air right now
        </span>
      </div>

      {/* 3. INCIDENT STATUS */}
      <div className="cc-section lp-fade-up" data-demo-section="cc-section-status">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Incident Status
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <ErrorBoundary fallbackTitle="Incident Status unavailable">
            <EpisodeStateHero />
          </ErrorBoundary>
        </div>
      </div>

      {/* 3b. DECISION TRACE — How This Decision Was Produced */}
      {showInvestigation && (
      <div className="cc-section" data-demo-section="cc-section-trace">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Decision Trace
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <DecisionTrace
            episode={episode}
            analysis={investigationAnalysis}
            verification={verificationContext}
          />
          {/* Phase 11: Investigation Progress — deterministic step-3 evidence sequence */}
          {isDemo && demoStep === 3 && simulation && (
            <div style={{ marginTop: 'var(--sp-4)' }}>
              <InvestigationProgress progress={simulation.investigationProgress} />
            </div>
          )}
        </div>
      </div>
      )}

      {/* AI Analysis Loading State */}
      {investigationLoading && (
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> AI Investigation Analysis
          </div>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <div className="ai-skeleton">
              <div className="ai-skeleton__block ai-skeleton__block--medium" />
              <div className="ai-skeleton__block" />
              <div className="ai-skeleton__block ai-skeleton__block--short" />
            </div>
          </div>
        </div>
      )}

      {/* AI Analysis Error Fallback */}
      {investigationError && !investigationLoading && (
        <div className="ai-fallback">
          <AlertTriangle size={16} className="ai-fallback__icon" aria-hidden="true" />
          <span className="ai-fallback__text">
            <span className="ai-fallback__strong">AI REASONING UNAVAILABLE.</span>{' '}
            Showing deterministic investigation evidence. The AI reasoning service may be temporarily unavailable.
          </span>
        </div>
      )}

      {/* AI Analysis Complete — 6-section story */}

      {showInvestigation && (<>

      {/* ── PHASE: FORECAST — AI-powered investigation and predictions */}
      <div className="cc-phase-label" style={{
        display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
        margin: 'var(--sp-5) 0 var(--sp-3)', paddingBottom: 'var(--sp-2)',
        borderBottom: '2px solid var(--lp-border)',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--lp-accent)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Phase 2 — Forecast
        </span>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)' }}>
          AI investigation, predictions, and recommended actions
        </span>
      </div>


      {/* 4. WHAT HAPPENED */}
      <ScrollReveal3D>
      <div className="cc-section demo-section-reveal cc-card-3d" data-demo-section="cc-section-investigation">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> What Happened
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <AISummary analysis={investigationAnalysis} />
        </div>
      </div>
      </ScrollReveal3D>

      {/* 5. INVESTIGATION PRIORITY */}
      {investigationAnalysis?.investigation_priority && (
        <ScrollReveal3D variant="scale">
        <div className="cc-section cc-card-3d" data-demo-section="cc-section-priority">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Investigation Priority
          </div>
          <TiltCard>
            <AIPriorityCard priority={investigationAnalysis?.investigation_priority} />
          </TiltCard>
        </div>
        </ScrollReveal3D>
      )}

      {/* 6. AI INVESTIGATION BRIEF */}
      <ScrollReveal3D variant="left">
      <div className="cc-section cc-card-3d" data-demo-section="cc-section-brief">
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> AI Investigation Brief
        </div>
        <TiltCard>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <AIAnalysisBrief analysis={investigationAnalysis} />
          </div>
        </TiltCard>
      </div>
      </ScrollReveal3D>

      {/* 7. LIMITATIONS & UNCERTAINTY — progressive disclosure */}
      <ProgressiveDisclosure
        label="Show limitations & uncertainty details"
        labelExpanded="Hide limitations & uncertainty"
        testId="pd-uncertainty"
        className="cc-section"
      >
        <div className="cc-section__label">
          <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Limitations & Uncertainty
        </div>
        <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
          <AIUncertainty analysis={investigationAnalysis} />
        </div>
      </ProgressiveDisclosure>

      {/* 8. RECOMMENDED ACTIONS */}
      {investigationAnalysis?.recommended_actions?.length > 0 && (
        <ScrollReveal3D variant="right">
        <div className="cc-section cc-card-3d" data-demo-section="cc-section-actions">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Recommended Actions
          </div>
          <TiltCard>
            <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
              <AIRecommendedActions actions={investigationAnalysis?.recommended_actions} />
            </div>
          </TiltCard>
        </div>
        </ScrollReveal3D>
      )}

      </>)}

      </>)}

      {/* BELOW THE FOLD */}

      {/* ── PHASE: VERIFY — Observation, verification, and accountability */}
      <div className="cc-phase-label" style={{
        display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
        margin: 'var(--sp-5) 0 var(--sp-3)', paddingBottom: 'var(--sp-2)',
        borderBottom: '2px solid var(--lp-border)',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--lp-accent)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Phase 3 — Verify
        </span>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)' }}>
          Prediction receipt, verification, and accountability evidence
        </span>
      </div>

      {showBelowFold && (
      <div className="cc-below-fold demo-section-reveal">
        <div className="cc-below-fold__title">Verification &amp; Accountability Evidence</div>

        {/* 9. Geographic Coverage — Exposure Intelligence Map */}
        <ScrollReveal3D variant="scale">
        <div className={`cc-section demo-section-reveal cc-card-3d ${hasSelection && !isHighlighted('exposure-corridor') ? 'cc-section--dim' : ''}`} data-demo-section="cc-section-exposure">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Exposure Intelligence Map
          </div>
          <div className="surface" style={{ overflow: 'hidden', minHeight: 420 }}>
            {exposureLoading && !exposureGeometry ? (
              <div style={{ height: 370, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--lp-text-muted)' }}>
                <LoadingState message="Computing exposure geometry..." compact />
              </div>
            ) : (
              <div style={{ height: 370 }}>
                <ExposureIntelligenceMap
                  exposure={exposureGeometry}
                  allowFullscreen={true}
                />
              </div>
            )}
          </div>
        </div>
        </ScrollReveal3D>

        {/* 10. Verification Context — Historical learning loop */}
        <ScrollReveal3D variant="left">
        <div className={`cc-section demo-section-reveal ${hasSelection && !isHighlighted('verification-outcome') ? 'cc-section--dim' : ''}`} data-demo-section="cc-section-verification">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Verification Context
          </div>
          <HistoricalVerificationContext
            stats={verificationStats}
            currentOutcome={verificationContext?.current_outcome || null}
            disclaimer={verificationContext?.disclaimer || ''}
          />
        </div>
        </ScrollReveal3D>

        {/* 10b. PREDICTION RECEIPT — The core accountability record */}
        <ScrollReveal3D variant="right">
        <div className="cc-section demo-section-reveal lp-scale-in cc-card-3d" data-demo-section="cc-section-receipt">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Prediction Receipt
          </div>
          <ErrorBoundary fallbackTitle="Prediction Receipt unavailable">
            <PredictionReceipt />
          </ErrorBoundary>
        </div>
        </ScrollReveal3D>

        {/* 11. Submit Verification — Human feedback form */}
        <div className="cc-section">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Submit Investigation Verification
          </div>
          <InvestigationVerification
            investigationId={isDemo ? 'demo-investigation' : 'current-investigation'}
            hypotheses={investigationAnalysis?.investigation_hypotheses || []}
            existingOutcome={verificationContext?.current_outcome || null}
            onSubmit={isDemo ? undefined : liveVerification.submit}
            onUpdate={isDemo ? undefined : liveVerification.update}
            submitting={verificationSubmitting}
          />
          {verificationSubmitSuccess && (
            <div style={{ fontSize: 13, color: '#16a34a', padding: '8px 0', fontWeight: 500 }}>
              ✓ Verification submitted successfully
            </div>
          )}
        </div>

        {/* 12. Investigation Accountability — Historical learning context */}

        {/* ── PHASE: LEARN — What did the system learn from this episode? */}
        <div className="cc-phase-label" style={{
          display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
          margin: 'var(--sp-5) 0 var(--sp-3)', paddingBottom: 'var(--sp-2)',
          borderBottom: '2px solid var(--lp-border)',
        }}>
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--lp-accent)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Phase 4 — Learn
          </span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--lp-text-muted)' }}>
            Model performance, trust assessment, and continuous improvement
          </span>
        </div>

        <ScrollReveal3D>
        <div className={`cc-section demo-section-reveal cc-card-3d ${hasSelection && !isHighlighted('historical-case') ? 'cc-section--dim' : ''}`} data-demo-section="cc-section-accountability">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Investigation Accountability
          </div>
          <InvestigationLearning
            learning={investigationLearning}
            loading={learningLoading}
            error={learningError}
          />
          {/* Phase 11: Accountability Chain — full investigation chain at step 7 */}
          {isDemo && demoStep === 7 && simulation && (
            <div style={{ marginTop: 'var(--sp-4)' }}>
              <AccountabilityChain chain={simulation.accountabilityChain} />
            </div>
          )}
          {/* Phase 29: Audit Trail — prediction lifecycle timeline */}
          {isDemo && (
            <div style={{ marginTop: 'var(--sp-4)' }}>
              <AuditTrail />
            </div>
          )}
        </div>
        </ScrollReveal3D>

        <div className="cc-section" data-demo-section="cc-section-trust-snapshot">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> Data Trust
          </div>
          <TrustSnapshot horizon={selectedHorizon} forecastStatus={forecastStatus} />
        </div>

        {/* 13b. WHY TRUST THIS — Evidence-based trust panel + decision state */}
        <div className="cc-section demo-section-reveal" data-demo-section="cc-section-why-trust">
          <ErrorBoundary fallbackTitle="Trust data unavailable">
            <WhyTrustThis />
          </ErrorBoundary>
        </div>

        {/* 13c. MODEL MISTAKES — Transparent worst predictions */}
        <div className="cc-section demo-section-reveal" data-demo-section="cc-section-mistakes">
          <ErrorBoundary fallbackTitle="Model mistakes unavailable">
            <ModelMistakes limit={3} />
          </ErrorBoundary>
        </div>

        {/* 13d. MODEL SUCCESSES — Best predictions for context */}
        <div className="cc-section demo-section-reveal" data-demo-section="cc-section-successes">
          <ErrorBoundary fallbackTitle="Model successes unavailable">
            <ModelSuccesses limit={3} />
          </ErrorBoundary>
        </div>

        {/* 13e. CONFIDENCE CALIBRATION — Per-horizon accuracy analysis */}
        <div className="cc-section demo-section-reveal" data-demo-section="cc-section-calibration">
          <ErrorBoundary fallbackTitle="Confidence calibration unavailable">
            <ConfidenceCalibration />
          </ErrorBoundary>
        </div>

        <div className="cc-section" data-demo-section="cc-section-historical-trend">
          <HistoricalTrendChart />
        </div>

        <div className="cc-section" data-demo-section="cc-section-deep-dive">
          <TechnicalDeepDive forecastStatus={forecastStatus} horizon={selectedHorizon} />
        </div>

        {/* WHY THIS IS DIFFERENT — Judge panel */}
        <div className="cc-section" data-demo-section="cc-section-why-different">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> How Our Solution Is Different
          </div>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <WhyDifferent />
          </div>
        </div>

        {/* CANNOT KNOW — Limitations */}
        <div className="cc-section" data-demo-section="cc-section-cannot-know">
          <div className="cc-section__label">
            <Diamond size={14} className="cc-section__label-icon" aria-hidden="true" /> What Lahore+ Cannot Know
          </div>
          <div className="surface" style={{ padding: 'var(--sp-4) var(--sp-5)' }}>
            <CannotKnow />
          </div>
        </div>
      </div>
      )}

      {/* Demo Controller — fixed sidebar */}
      {isDemo && <DemoController />}
    </div>
  );
}
