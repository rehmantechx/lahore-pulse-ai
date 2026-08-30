/**
 * Response Domains — Single source of truth for investigation domain
 * definitions and weather-trigger evaluation logic.
 *
 * Based on Punjab's environmental response framework.
 * Each domain is an INVESTIGATION area, NOT a confirmed source.
 *
 * Used by: ResponseOrchestrator, InvestigationBrief
 */

// ── Domain Definitions ──────────────────────────────────────

export const RESPONSE_DOMAINS = [
  {
    id: 'open-burning',
    icon: '🔥',
    name: 'Open Burning',
    description: 'Agricultural residue, waste burning, or biomass combustion',
    officialBasis:
      'Punjab EPA: Open burning ban under Punjab Environmental Protection Act; smog emergency orders target crop residue burning',
    triggers: {
      temperature: (v) => v !== null && v < 18.0,
      humidity: (v) => v !== null && v < 60.0,
      wind_speed: (v) => v !== null && v < 6.0,
    },
  },
  {
    id: 'traffic-emissions',
    icon: '🚗',
    name: 'Traffic Emissions',
    description: 'Vehicle exhaust and transport-related particulate accumulation',
    officialBasis:
      'Punjab Transport Department: vehicle emission standards; Lahore Traffic Engineering & Planning Agency traffic management during smog',
    triggers: {
      wind_speed: (v) => v !== null && v < 6.0,
      humidity: (v) => v !== null && v > 70.0,
    },
  },
  {
    id: 'road-dust',
    icon: '🏗',
    name: 'Road / Construction Dust',
    description: 'Suspension of particulates from road surface and construction activity',
    officialBasis:
      'Punjab EPA: Construction activity restrictions during smog season; Lahore Development Authority dust suppression orders',
    triggers: {
      humidity: (v) => v !== null && v < 60.0,
      wind_speed: (v) => v !== null && v > 4.0,
    },
  },
  {
    id: 'industrial',
    icon: '🏭',
    name: 'Industrial Emissions',
    description: 'Factory, brick kiln, and industrial process emissions',
    officialBasis:
      'Punjab EPA: Brick kiln conversion order; industrial emission standards under Punjab Environmental Protection Act 1997',
    triggers: {
      pressure: (v) => v !== null && v > 1010.0,
      wind_speed: (v) => v !== null && v < 6.0,
    },
  },
];

// ── Weather-Trigger Evaluation ──────────────────────────────

/**
 * Evaluate whether current weather conditions match a domain's
 * historical trigger pattern.
 *
 * @param {object} domain - A domain from RESPONSE_DOMAINS
 * @param {Array} weatherVariables - Weather variables from episode API
 * @returns {{ matchCount: number, total: number, matchedVars: string[], reason: string }}
 */
export function evaluateDomain(domain, weatherVariables) {
  if (!weatherVariables || weatherVariables.length === 0) {
    return {
      matchCount: 0,
      total: 0,
      matchedVars: [],
      reason: 'Insufficient weather data for evaluation',
    };
  }

  const varMap = {};
  for (const v of weatherVariables) {
    if (v.label === 'Temperature') varMap.temperature = v.current_value;
    else if (v.label === 'Humidity') varMap.humidity = v.current_value;
    else if (v.label === 'Wind speed') varMap.wind_speed = v.current_value;
    else if (v.label === 'Pressure') varMap.pressure = v.current_value;
  }

  let matchCount = 0;
  let total = 0;
  const matchedVars = [];

  for (const [key, testFn] of Object.entries(domain.triggers)) {
    total++;
    const val = varMap[key];
    if (val !== undefined && val !== null && testFn(val)) {
      matchCount++;
      matchedVars.push(key.replace('_', ' '));
    }
  }

  const reasons = [];
  if (matchCount >= 2) {
    reasons.push(
      `${matchCount} of ${total} weather factors match historical patterns for ${domain.name.toLowerCase()}.`
    );
  } else if (matchCount === 1) {
    reasons.push(`1 of ${total} weather factors match.`);
  } else {
    reasons.push(
      'Weather factors do not currently match typical patterns for this domain.'
    );
  }

  return { matchCount, total, matchedVars, reason: reasons.join(' ') };
}

// ── Domain Status Derivation ────────────────────────────────

/**
 * Derive domain status from weather evaluation and episode state.
 *
 * @param {{ matchCount: number }} evaluation - Result from evaluateDomain
 * @param {string} episodeState - 'episode' | 'improving' | 'normal' | 'uncertain'
 * @returns {{ status: string, statusColor: string, statusBg: string, statusBorder: string }}
 */
export function getDomainStatus(evaluation, episodeState) {
  if (episodeState === 'normal' || episodeState === 'uncertain') {
    return {
      status: 'NOT AVAILABLE',
      statusColor: 'var(--slate-400)',
      statusBg: 'var(--slate-50)',
      statusBorder: 'var(--slate-200)',
    };
  }
  if (evaluation.matchCount >= 1) {
    return {
      status: 'INVESTIGATE',
      statusColor: '#92400e',
      statusBg: '#fffbeb',
      statusBorder: '#fde68a',
    };
  }
  return {
    status: 'LOW',
    statusColor: 'var(--slate-400)',
    statusBg: 'var(--slate-50)',
    statusBorder: 'var(--slate-200)',
  };
}
