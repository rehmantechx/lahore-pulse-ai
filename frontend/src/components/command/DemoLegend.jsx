/**
 * DemoLegend — Progressive data layer legend for demo mode.
 *
 * Shows only the layers relevant to the current step,
 * building the story as the demonstration progresses.
 */

const LAYER_DEFS = {
  observed: {
    label: 'OBSERVED',
    color: 'var(--lp-brand)',
    desc: 'Directly measured data',
  },
  deterministic: {
    label: 'DETERMINISTIC',
    color: '#3b82f6',
    desc: 'Rules-based analysis',
  },
  ai: {
    label: 'AI HYPOTHESIS',
    color: '#d97706',
    desc: 'Hypotheses from evidence',
  },
  verified: {
    label: 'HUMAN VERIFIED',
    color: '#16a34a',
    desc: 'Field verification',
  },
  accountability: {
    label: 'ACCOUNTABILITY',
    color: '#16a34a',
    desc: 'Historical comparison',
  },
};

export default function DemoLegend({ activeLayers = [], transitionKey }) {
  const visible = activeLayers
    .map((key) => LAYER_DEFS[key])
    .filter(Boolean);

  if (visible.length === 0) return null;

  return (
    <div className="demo-legend" aria-label="Active data layers">
      <div className="demo-legend__items lp-motion-stagger" key={transitionKey}>
        {visible.map((layer) => (
          <div key={layer.label} className="demo-legend__item">
            <span
              className="demo-legend__dot"
              style={{ background: layer.color }}
              aria-hidden="true"
            />
            <span className="demo-legend__label">{layer.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
