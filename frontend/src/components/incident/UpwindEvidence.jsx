import React from 'react';
import SourceCompass from '../compass/SourceCompass';

const CORRIDOR_LABELS = {
  'NE Corridor': 'NE industrial–urban corridor (Shahdara, Ravi Road, GT Road)',
  'SE Corridor': 'SE peri-urban–industrial zone (Multan Road, Bund Road)',
  'NW Corridor': 'NW peri-urban–industrial zone (Canal Road, IB Select)',
  'SW Corridor': 'SW agricultural–peri-urban belt (Walton, Cantonment)',
  'East Corridor': 'East Ravi riverbank corridor',
  'West Corridor': 'West peri-urban corridor',
  'North Corridor': 'North peri-urban corridor',
  'South Corridor': 'South peri-urban corridor',
};

export default function UpwindEvidence({ episode }) {
  const compass = episode?.source_compass;
  const wind = compass?.current_wind;
  const enrichment = compass?.enrichment;
  const hint = compass?.investigation_hint;
  const seasonContext = compass?.season_context;

  const hasData = Boolean(compass && wind && wind.sector);

  if (!hasData) {
    // Compass enrichment not available — wind info shown in command strip
    return null;
  }

  const hasEnrichment = enrichment && enrichment.sector;
  const hasHint = hint && hint.suggested_response_corridor;
  const enrichmentPct = enrichment?.enrichment_factor
    ? `${(enrichment.enrichment_factor * 100).toFixed(0)}%`
    : null;

  return (
    <div className="cc-upwind">
      {/* Two-column layout: Compass (left) + Key Findings (right) */}
      <div className="cc-upwind__layout">
        {/* Left: Compass Visualization */}
        <div className="cc-upwind__compass">
          <SourceCompass compass={compass} />
        </div>

        {/* Right: Key wind/enrichment findings */}
        <div className="cc-upwind__findings">
          <div className="cc-upwind__finding">
            <span className="cc-upwind__finding-label">Current Wind</span>
            <span className="cc-upwind__finding-value">
              {wind.sector} · {wind.wind_speed_ms?.toFixed?.(1)} m/s
              {wind.beaufort_scale != null ? ` (Beaufort ${wind.beaufort_scale})` : ''}
            </span>
          </div>

          {hasEnrichment && (
            <div className="cc-upwind__finding">
              <span className="cc-upwind__finding-label">Strongest Upwind Sector</span>
              <span className="cc-upwind__finding-value">
                {enrichment.sector}
                {enrichment.evidence_hours ? ` · ${enrichment.evidence_hours}h evidence` : ''}
                {enrichmentPct ? ` · ${enrichmentPct} enrichment` : ''}
              </span>
            </div>
          )}

          {enrichment?.nearest_monitor_station_km != null && (
            <div className="cc-upwind__finding">
              <span className="cc-upwind__finding-label">Nearest Monitor</span>
              <span className="cc-upwind__finding-value">
                {enrichment.nearest_monitor_station_km} km
              </span>
            </div>
          )}

          {hasHint && (
            <div className="cc-upwind__finding">
              <span className="cc-upwind__finding-label">Suggested Corridor</span>
              <span className="cc-upwind__finding-value cc-upwind__finding-value--corridor">
                {hint.suggested_response_corridor}
              </span>
              {hint.corridor_rationale && (
                <span className="cc-upwind__finding-detail">
                  {hint.corridor_rationale}
                </span>
              )}
              {hint.association_level && (
                <span className="cc-upwind__finding-detail">
                  Association strength: {hint.association_level}
                </span>
              )}
            </div>
          )}

          {seasonContext && (
            <div className="cc-upwind__finding cc-upwind__finding--context">
              <span className="cc-upwind__finding-label">Winter Context</span>
              <span className="cc-upwind__finding-value cc-upwind__finding-value--small">
                {seasonContext}
              </span>
            </div>
          )}

          {/* Compact Corridor Guide */}
          {hasHint && hint.suggested_response_corridor && (
            <div className="cc-upwind__corridors">
              <span className="cc-upwind__corridors-title">Corridor Guide</span>
              {Object.entries(CORRIDOR_LABELS).map(([corridor, detail]) => (
                <div
                  key={corridor}
                  className={`cc-upwind__corridor ${
                    corridor === hint.suggested_response_corridor ? 'cc-upwind__corridor--active' : ''
                  }`}
                >
                  <span className="cc-upwind__corridor-name">{corridor}</span>
                  <span className="cc-upwind__corridor-detail">{detail}</span>
                </div>
              ))}
            </div>
          )}

          {/* Safety disclaimer */}
          <div className="cc-upwind__disclaimer">
            Statistically associated wind sectors. Visual trace only, not a deterministic attribution.
          </div>
        </div>
      </div>
    </div>
  );
}
