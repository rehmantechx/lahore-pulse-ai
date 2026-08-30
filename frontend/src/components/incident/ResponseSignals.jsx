/**
 * ResponseSignals — Investigation signal layer.
 *
 * IMPORTANT: This is NOT a recommendation engine.
 * It is an INVESTIGATION layer showing which response domains
 * are compatible with current episode conditions.
 *
 * Uses existing backend episode intelligence data.
 * Does NOT claim to detect actual pollution sources.
 * Mandatory disclaimer displayed.
 *
 * Uses response domains from Lahore government response framework.
 */

import { useEpisodeIntelligence } from '../../hooks/useEpisodeIntelligence';

/**
 * Response domains based on Lahore environmental response framework.
 * Each domain maps to episode conditions that make it compatible.
 */
const RESPONSE_DOMAINS = [
  {
    id: 'open-burning',
    name: 'Open Burning',
    conditionKeys: ['wind', 'temperature', 'stability'],
    evidenceTemplate: 'Episode conditions and current environmental pattern are compatible with open burning as a response domain.',
  },
  {
    id: 'traffic-emissions',
    name: 'Traffic Emissions',
    conditionKeys: ['wind', 'time_of_day', 'visibility'],
    evidenceTemplate: 'Current atmospheric conditions are consistent with traffic emission accumulation patterns.',
  },
  {
    id: 'road-dust',
    name: 'Road / Construction Dust',
    conditionKeys: ['wind', 'humidity', 'visibility'],
    evidenceTemplate: 'Low humidity and wind conditions are compatible with dust suspension patterns.',
  },
  {
    id: 'industrial',
    name: 'Industrial Emissions',
    conditionKeys: ['wind', 'pressure', 'stability'],
    evidenceTemplate: 'Atmospheric stability and wind patterns are compatible with industrial emission accumulation.',
  },
];

/**
 * Evaluate whether weather context supports investigation
 * for a given response domain.
 */
function evaluateDomain(domain, episode) {
  if (!episode?.weather_context?.variables) return 'low';

  const vars = episode.weather_context.variables;
  const matchedVars = vars.filter(v => v.matches_pattern);

  // If we have episode state, use it to determine investigation level
  if (episode.state === 'normal') return 'low';
  if (episode.state === 'uncertain') return 'monitor';

  // During episode: if multiple weather patterns match, investigate
  if (matchedVars.length >= 2) return 'investigate';
  if (matchedVars.length === 1) return 'monitor';
  return 'low';
}

function getStatusConfig(status) {
  switch (status) {
    case 'investigate':
      return { label: 'Investigate', className: 'response-signal__status--investigate' };
    case 'monitor':
      return { label: 'Monitor', className: 'response-signal__status--monitor' };
    default:
      return { label: 'Low', className: 'response-signal__status--low' };
  }
}

export default function ResponseSignals() {
  const { episode, loading, error } = useEpisodeIntelligence();

  if (loading && !episode) return null;
  if (error && !episode) return null;
  if (!episode) return null;

  // Only show during active episodes
  if (episode.state === 'normal') {
    return (
      <div>
        <div className="section-header">
          <h2 className="section-header__title">Response Signals</h2>
          <span className="section-header__subtitle">Investigation domain analysis</span>
        </div>
        <div className="narrative-block narrative-block--normal">
          No active episode — response signal analysis is not applicable.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-header__title">Response Signals</h2>
        <span className="section-header__subtitle">Investigation domain analysis</span>
      </div>

      <div className="response-signals">
        {RESPONSE_DOMAINS.map(domain => {
          const status = evaluateDomain(domain, episode);
          const statusConfig = getStatusConfig(status);

          return (
            <div key={domain.id} className="response-signal">
              <div className="response-signal__header">
                <span className="response-signal__name">{domain.name}</span>
                <span className={`response-signal__status ${statusConfig.className}`}>
                  {statusConfig.label}
                </span>
              </div>
              <p className="response-signal__evidence">
                {domain.evidenceTemplate}
              </p>
            </div>
          );
        })}
      </div>

      {/* Mandatory disclaimer */}
      <div className="response-signal__disclaimer">
        Investigation signals are not confirmed emission sources. They indicate response domains
        that are statistically compatible with current episode conditions and weather patterns.
        Actual source identification requires ground-level investigation.
      </div>
    </div>
  );
}
