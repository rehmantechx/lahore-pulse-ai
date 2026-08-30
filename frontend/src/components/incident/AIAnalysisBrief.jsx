/**
 * AIAnalysisBrief — Section 4: Three-category investigation brief.
 *
 * Clearly separates:
 *   - OBSERVED FACTS (directly measured data, highest trust)
 *   - MODEL INFERENCES (statistical conclusions with confidence)
 *   - HYPOTHESES (possible explanations requiring field verification)
 *
 * Each category is visually distinct with clear labels.
 */

import { Eye, Cpu, HelpCircle } from 'lucide-react';

function ConfidenceBadge({ value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <span className="ai-brief__confidence">{pct}%</span>
  );
}

function FactRow({ fact, index }) {
  return (
    <div className="ai-brief__row ai-brief__row--fact">
      <span className="ai-brief__index">{index + 1}</span>
      <div className="ai-brief__content">
        <span className="ai-brief__statement">{fact.statement}</span>
        {fact.evidence_references?.length > 0 && (
          <span className="ai-brief__refs">
            Evidence: {fact.evidence_references.join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}

function InferenceRow({ inference, index }) {
  return (
    <div className="ai-brief__row ai-brief__row--inference">
      <span className="ai-brief__index">{index + 1}</span>
      <div className="ai-brief__content">
        <div className="ai-brief__statement-row">
          <span className="ai-brief__statement">{inference.statement}</span>
          <ConfidenceBadge value={inference.confidence} />
        </div>
        {inference.supporting_evidence?.length > 0 && (
          <span className="ai-brief__refs">
            Evidence: {inference.supporting_evidence.join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}

function HypothesisRow({ hypothesis, index }) {
  return (
    <div className="ai-brief__row ai-brief__row--hypothesis">
      <div className="ai-brief__hypothesis-header">
        <span className="ai-brief__index">{index + 1}</span>
        <span className="ai-brief__hypothesis-label">HYPOTHESIS — REQUIRES FIELD VERIFICATION</span>
        <ConfidenceBadge value={hypothesis.confidence} />
      </div>
      <div className="ai-brief__content">
        <span className="ai-brief__factor">{hypothesis.factor}</span>
        {hypothesis.reasoning && (
          <span className="ai-brief__reasoning">{hypothesis.reasoning}</span>
        )}
        {hypothesis.verification_needed && (
          <div className="ai-brief__verification">
            <span className="ai-brief__verification-label">Verification needed:</span>{' '}
            {hypothesis.verification_needed}
          </div>
        )}
        {hypothesis.supporting_evidence?.length > 0 && (
          <span className="ai-brief__refs">
            Evidence: {hypothesis.supporting_evidence.join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, label, count, color }) {
  return (
    <div className="ai-brief__section-header">
      <Icon size={14} color={color} aria-hidden="true" />
      <span className="ai-brief__section-label" style={{ color }}>{label}</span>
      <span className="ai-brief__section-count">{count}</span>
    </div>
  );
}

export default function AIAnalysisBrief({ analysis }) {
  if (!analysis) return null;

  const facts = analysis.observed_facts || [];
  const inferences = analysis.model_inferences || [];
  const hypotheses = analysis.investigation_hypotheses || [];

  if (facts.length === 0 && inferences.length === 0 && hypotheses.length === 0) {
    return (
      <div className="ai-brief ai-brief--empty">
        <span className="ai-brief__empty-text">No investigation analysis available.</span>
      </div>
    );
  }

  return (
    <div className="ai-brief">
      {/* Observed Facts */}
      {facts.length > 0 && (
        <div className="ai-brief__section">
          <SectionHeader icon={Eye} label="OBSERVED FACTS" count={facts.length} color="#0d9488" />
          {facts.map((fact, i) => (
            <FactRow key={i} fact={fact} index={i} />
          ))}
        </div>
      )}

      {/* Model Inferences */}
      {inferences.length > 0 && (
        <div className="ai-brief__section">
          <SectionHeader icon={Cpu} label="MODEL INFERENCES" count={inferences.length} color="#7c3aed" />
          {inferences.map((inf, i) => (
            <InferenceRow key={i} inference={inf} index={i} />
          ))}
        </div>
      )}

      {/* Hypotheses */}
      {hypotheses.length > 0 && (
        <div className="ai-brief__section">
          <SectionHeader icon={HelpCircle} label="HYPOTHESES" count={hypotheses.length} color="#d97706" />
          {hypotheses.map((hyp, i) => (
            <HypothesisRow key={i} hypothesis={hyp} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
