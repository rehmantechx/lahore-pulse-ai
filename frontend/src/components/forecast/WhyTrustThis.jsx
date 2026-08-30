/**
 * WhyTrustThis — Evidence-based trust panel.
 *
 * Answers the judge's question: "Why should I trust this system?"
 * Provides concrete, verifiable trust signals rather than claims.
 *
 * In demo mode: fixture data from DemoDataContext.
 * In production: aggregated from multiple API endpoints.
 */

import { useState, useEffect } from 'react';
import { useDemoData } from '../../demo';
import { getAccuracySummary } from '../../services/api';
import { Shield, CheckCircle, Eye, Lock, FileText, ChevronRight } from 'lucide-react';
import DecisionEvidenceChain from './DecisionEvidenceChain';

/* ── Trust Signal Item ────────────────────────────────────── */

function TrustSignal({ signal, index }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Stagger: each signal fades in with increasing delay
    const timeout = setTimeout(() => setVisible(true), index * 80);
    return () => clearTimeout(timeout);
  }, [index]);

  return (
    <div
      className="trust-signal"
      data-testid={`trust-signal-${index}`}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(6px)',
        transition: 'opacity 200ms ease, transform 200ms ease',
      }}
    >
      <CheckCircle size={16} className="trust-signal__icon" />
      <span className="trust-signal__text">{signal}</span>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export default function WhyTrustThis({ showEvidenceChain, onToggleEvidenceChain }) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [trustData, setTrustData] = useState(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  // Local toggle when parent doesn't control evidence chain
  const [localChainOpen, setLocalChainOpen] = useState(false);
  const chainOpen = showEvidenceChain !== undefined ? showEvidenceChain : localChainOpen;

  useEffect(() => {
    if (isDemo) {
      const raw = demoData.whyTrust;
      if (raw) {
        setTrustData({
          ...raw,
          signals: raw.signals || [
            `${(raw.total_evaluated || 0).toLocaleString()} predictions evaluated`,
            `${raw.within_tolerance_pct || 0}% within tolerance`,
            'Confidence tracked against outcomes',
            'Forecasts independently verified after target time',
            'Errors remain visible',
          ],
        });
      }
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function fetchTrust() {
      try {
        setLoading(true);
        const data = await getAccuracySummary({ signal: AbortSignal.timeout(10000) });
        if (!cancelled && data) {
          setTrustData({
            total_evaluated: data.total_predictions || 0,
            within_tolerance_pct: data.overall_accuracy?.within_tolerance_pct || 0,
            calibration_status: data.calibration?.overall_status || 'UNKNOWN',
            signals: [
              `${(data.total_predictions || 0).toLocaleString()} predictions evaluated`,
              `${data.overall_accuracy?.within_tolerance_pct || 0}% within tolerance`,
              'Confidence tracked against outcomes',
              'Forecasts independently verified after target time',
              'Errors remain visible',
            ],
          });
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchTrust();
    return () => { cancelled = true; };
  }, [isDemo, demoData]);

  if (loading) {
    return (
      <div className="why-trust why-trust--loading" data-testid="why-trust-loading">
        <div className="why-trust__skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="why-trust why-trust--error" data-testid="why-trust-error">
        <Shield size={16} />
        <span>Unable to load trust data: {error}</span>
      </div>
    );
  }

  if (!trustData) {
    return (
      <div className="why-trust why-trust--empty" data-testid="why-trust-empty">
        <Shield size={16} />
        <span>No trust data available yet.</span>
      </div>
    );
  }

  return (
    <div className="why-trust" data-testid="why-trust">
      <div className="why-trust__header">
        <Shield size={18} className="why-trust__header-icon" />
        <div>
          <h3 className="why-trust__title">Why Trust This Forecast?</h3>
          <p className="why-trust__subtitle">
            Not because we say so — because you can verify it.
          </p>
        </div>
      </div>

      <div className="why-trust__signals">
        {trustData.signals?.map((signal, i) => (
          <TrustSignal key={i} signal={signal} index={i} />
        ))}
      </div>

      <div className="why-trust__principles">
        <div className="why-trust__principle">
          <Eye size={14} className="why-trust__principle-icon" />
          <div>
            <span className="why-trust__principle-label">Transparency</span>
            <span className="why-trust__principle-text">Errors are shown, not hidden</span>
          </div>
        </div>
        <div className="why-trust__principle">
          <Lock size={14} className="why-trust__principle-icon" />
          <div>
            <span className="why-trust__principle-label">Accountability</span>
            <span className="why-trust__principle-text">Outcomes are recorded permanently</span>
          </div>
        </div>
        <div className="why-trust__principle">
          <FileText size={14} className="why-trust__principle-icon" />
          <div>
            <span className="why-trust__principle-label">Verification</span>
            <span className="why-trust__principle-text">Predictions checked against observations</span>
          </div>
        </div>
      </div>

      {/* Expandable evidence chain */}
      <button
        type="button"
        className="why-trust__expand"
        onClick={() => {
          if (onToggleEvidenceChain) {
            onToggleEvidenceChain(!chainOpen);
          } else {
            setLocalChainOpen((prev) => !prev);
          }
        }}
        aria-expanded={chainOpen}
        data-testid="evidence-chain-toggle"
      >
        <ChevronRight
          size={14}
          className={`why-trust__expand-icon ${chainOpen ? 'why-trust__expand-icon--open' : ''}`}
        />
        {chainOpen ? 'Hide evidence chain' : 'See the full evidence chain — why do we trust this alert?'}
      </button>

      <DecisionEvidenceChain open={chainOpen} />

      <div className="why-trust__footer">
        <p className="why-trust__footer-note">
          The system is designed to be wrong in ways you can catch. That's the point.
        </p>
      </div>
    </div>
  );
}
