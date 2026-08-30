/**
 * Demo Mode — Deterministic fixture for competition demo.
 *
 * Activated by adding ?demo=true to the Command Center URL.
 * Does NOT modify production detection logic.
 * Does NOT fabricate production database records.
 * All data is shaped exactly like real API responses.
 */

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { TOTAL_STEPS } from './stateMachine';

/* ── Normal State Episode (before incident) ─────────────── */

const DEMO_EPISODE_NORMAL = {
  state: 'normal',
  trajectory: 'stable',
  current_pm25: 85.0,
  trajectory_description: 'PM2.5 is within seasonal norms. No episode conditions detected.',
  narrative: 'Environmental conditions are within seasonal norms. PM2.5 at 85 μg/m3 is below the episode threshold. Wind is calm. No abnormal pollution event detected.',
  weather_context: {
    variables: [
      { name: 'temperature', value: 16.5, unit: '°C' },
      { name: 'humidity', value: 58, unit: '%' },
      { name: 'wind_speed', value: 4.8, unit: 'm/s' },
      { name: 'pressure', value: 1013.2, unit: 'hPa' },
    ],
  },
  source_compass: {
    current_wind: {
      sector: 'NW',
      direction_degrees: 315,
      wind_speed_ms: 4.8,
      is_calm: false,
      beaufort_scale: 3,
    },
    historical: {
      strongest_sector: 'E',
      strongest_enrichment: 1.44,
      evidence_count: 972,
      total_episode_hours: 12480,
      season: 'winter',
      association_label: 'MODERATE',
    },
    enrichment: {
      sector: 'NW',
      enrichment_factor: 0.82,
      evidence_hours: 410,
      nearest_monitor_station_km: 8.2,
    },
    investigation_hint: {
      suggested_response_corridor: null,
      corridor_rationale: 'No investigation required under current conditions.',
      association_level: 'LOW',
    },
    season_context: 'Current wind sector does not show strong episode association.',
  },
};

/* ── Episode Intelligence (GET /api/v1/episode) ─────────── */

const DEMO_EPISODE = {
  state: 'episode',
  trajectory: 'rising',
  current_pm25: 165.0,
  trajectory_description: 'PM2.5 is rising sharply. Expect continued deterioration over the next 6 hours.',
  narrative: 'An active pollution episode is underway in Lahore. PM2.5 has reached 165 μg/m3, classified as Unhealthy. Wind is from the East at 3.2 m/s — the strongest historical enrichment sector at 1.44×. Temperature is 14°C with 68% humidity, conditions consistent with winter episode accumulation. Open burning, traffic, and industrial domains are weather-compatible.',
  weather_context: {
    variables: [
      { name: 'temperature', value: 14.2, unit: '°C' },
      { name: 'humidity', value: 68, unit: '%' },
      { name: 'wind_speed', value: 3.2, unit: 'm/s' },
      { name: 'pressure', value: 1015.3, unit: 'hPa' },
    ],
  },
  source_compass: {
    current_wind: {
      sector: 'E',
      direction_degrees: 90,
      wind_speed_ms: 3.2,
      is_calm: false,
      beaufort_scale: 2,
    },
    historical: {
      strongest_sector: 'E',
      strongest_enrichment: 1.44,
      evidence_count: 972,
      total_episode_hours: 12480,
      season: 'winter',
      association_label: 'MODERATE',
    },
    enrichment: {
      sector: 'E',
      enrichment_factor: 1.44,
      evidence_hours: 972,
      nearest_monitor_station_km: 8.2,
    },
    investigation_hint: {
      suggested_response_corridor: 'East Corridor',
      corridor_rationale: 'Ravi riverbank corridor — industrial, agricultural residue transport, and seasonal brick kiln activity',
      association_level: 'MODERATE',
    },
    season_context: 'Winter episodes (Oct–Mar) show 44% higher PM2.5 when winds originate from the East sector, likely influenced by the Ravi riverbank corridor and seasonal agricultural residue burning.',
  },
};

/* ── Forecasts (GET /api/v1/forecast/all) ────────────────── */

const DEMO_FORECASTS = {
  '1': {
    predicted_pm25: 172,
    horizon_hours: 1,
    data_quality: {
      data_timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      freshness_hours: 0.42,
      data_quality_score: 'good',
    },
  },
  '3': {
    predicted_pm25: 198,
    horizon_hours: 3,
  },
  '6': {
    predicted_pm25: 224,
    horizon_hours: 6,
  },
  '12': {
    predicted_pm25: 189,
    horizon_hours: 12,
  },
  '24': {
    predicted_pm25: 142,
    horizon_hours: 24,
  },
};

const DEMO_FORECAST_STATUS = {
  freshness: 'fresh',
  reliability: 'strong',
  track_record: { total_predictions: 4788 },
};

/* ── Historical Analogs (GET /api/v1/episode/analogs) ────── */

const DEMO_ANALOGS = {
  analogs: [
    {
      date: '2022-11-06',
      peak_pm25: 275,
      duration_hours: 36,
      similarity_label: 'Closest match',
      similarity_factors: [
        { label: 'wind speed', matches: true },
        { label: 'humidity', matches: true },
        { label: 'seasonal timing', matches: true },
        { label: 'temperature', matches: true },
        { label: 'PM2.5 severity', matches: false },
      ],
      what_happened_next: {
        summary: 'Peak arrived 3h later at 275 μg/m3; recovery began after 24h with wind shift to NW.',
      },
    },
    {
      date: '2023-11-12',
      peak_pm25: 248,
      duration_hours: 30,
      similarity_label: 'Strong match',
      similarity_factors: [
        { label: 'wind speed', matches: true },
        { label: 'humidity', matches: true },
        { label: 'temperature', matches: true },
        { label: 'atmospheric pressure', matches: true },
        { label: 'PM2.5 severity', matches: false },
      ],
      what_happened_next: {
        summary: 'Intensified for 6h before a rain event cleared the episode; PM2.5 dropped to 68 μg/m3 within 12h.',
      },
    },
    {
      date: '2022-10-30',
      peak_pm25: 231,
      duration_hours: 24,
      similarity_label: 'Moderate match',
      similarity_factors: [
        { label: 'wind speed', matches: true },
        { label: 'seasonal timing', matches: true },
        { label: 'temperature', matches: false },
      ],
      what_happened_next: {
        summary: 'Peak held for 12h; gradual improvement over 2 days as wind speed increased to 7 m/s.',
      },
    },
  ],
  current_context: {
    pm25: 165,
    wind_sector: 'E',
    temperature: 14.2,
    humidity: 68,
    season: 'winter',
  },
  caveat: 'Historical analogs describe similarity to past observations. They are not guarantees about the current event.',
  total_episodes_searched: 386,
};

/* ── Alert History (GET /api/v1/alerts/history) ──────────── */

const DEMO_ALERT_HISTORY = [
  {
    id: 'alert-001',
    type: 'Poor Air Warning',
    severity: 'poor',
    aqi: 152,
    level: 'Unhealthy',
    message: 'Air quality has deteriorated to unhealthy levels.',
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    read: true,
  },
  {
    id: 'alert-002',
    type: 'Moderate Warning',
    severity: 'moderate',
    aqi: 98,
    level: 'Moderate',
    message: 'Air quality is moderate. Sensitive groups should limit outdoor activity.',
    timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    read: true,
  },
  {
    id: 'alert-003',
    type: 'Fair Warning',
    severity: 'fair',
    aqi: 62,
    level: 'Moderate',
    message: 'Air quality may affect sensitive groups.',
    timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    read: true,
  },
  {
    id: 'alert-004',
    type: 'All Clear',
    severity: 'good',
    aqi: 38,
    level: 'Good',
    message: 'Air quality has returned to safe levels.',
    timestamp: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    read: true,
  },
];

/* ── Recent Reports ─────────────────────────────────────── */

const DEMO_REPORTS = [
  {
    id: 'rpt-001',
    name: 'Daily Summary – Aug 26, 2026',
    type: 'Daily',
    generatedOn: 'Aug 26, 2026 · 7:30 AM',
    range: 'Aug 26, 2026',
    format: 'PDF',
  },
  {
    id: 'rpt-002',
    name: 'Weekly Report – Aug 17 to Aug 23',
    type: 'Weekly',
    generatedOn: 'Aug 24, 2026 · 8:15 AM',
    range: 'Aug 17 – Aug 23, 2026',
    format: 'PDF',
  },
  {
    id: 'rpt-003',
    name: 'Monthly Report – July 2026',
    type: 'Monthly',
    generatedOn: 'Aug 1, 2026 · 9:05 AM',
    range: 'Jul 1 – Jul 31, 2026',
    format: 'PDF',
  },
  {
    id: 'rpt-004',
    name: 'Episode Report – Aug 18, 2026',
    type: 'Episode',
    generatedOn: 'Aug 19, 2026 · 10:20 AM',
    range: 'Aug 18 – Aug 18, 2026',
    format: 'PDF',
  },
  {
    id: 'rpt-005',
    name: 'Share Snapshot – Aug 26, 2026',
    type: 'Snapshot',
    generatedOn: 'Aug 26, 2026 · 6:45 AM',
    range: 'Aug 26, 2026',
    format: 'PNG',
  },
];

/* ── Monitoring Stations (GET /api/v1/stations) ───────────── */

const DEMO_STATIONS = [
  { station_id: 'us-embassy', name: 'US Embassy', source: 'embassy', latitude: 31.5204, longitude: 74.3587, pm25: 165.0, pm10: 248.0 },
  { station_id: 'lahore-epa', name: 'Lahore EPA', source: 'epa', latitude: 31.5450, longitude: 74.3406, pm25: 142.0, pm10: 210.0 },
  { station_id: 'pak-epa-tcp', name: 'Pak-EPA TCP', source: 'epa', latitude: 31.5600, longitude: 74.3300, pm25: 128.0, pm10: 195.0 },
  { station_id: 'dha-phase5', name: 'DHA Phase 5', source: 'citizen', latitude: 31.4700, longitude: 74.3700, pm25: 98.0, pm10: 155.0 },
  { station_id: 'johar-town', name: 'Johar Town', source: 'citizen', latitude: 31.4600, longitude: 74.2900, pm25: 110.0, pm10: 175.0 },
  { station_id: 'gulberg-iii', name: 'Gulberg III', source: 'citizen', latitude: 31.5130, longitude: 74.3450, pm25: 135.0, pm10: 205.0 },
];

/* ── Saved Locations (GET /api/v1/favorites) ───────────────── */

const DEMO_FAVORITES = {
  locations: [
    {
      id: 'loc-demo-001',
      station_id: 'us-embassy',
      name: 'US Embassy',
      label: 'Home',
      latitude: 31.5204,
      longitude: 74.3587,
      icon: 'home',
      sort_order: 1,
      pm25: 165.0,
      pm10: 248.0,
      temperature: 14.2,
      humidity: 68,
      aqi: { label: 'Poor', color: '#EF4444', band: 'poor' },
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'loc-demo-002',
      station_id: 'lahore-epa',
      name: 'Lahore EPA',
      label: 'Workplace',
      latitude: 31.5450,
      longitude: 74.3406,
      icon: 'building',
      sort_order: 2,
      pm25: 142.0,
      pm10: 210.0,
      temperature: 13.8,
      humidity: 72,
      aqi: { label: 'Poor', color: '#EF4444', band: 'poor' },
      created_at: new Date(Date.now() - 25 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'loc-demo-003',
      station_id: null,
      name: "Children's School",
      label: 'School',
      latitude: 31.5100,
      longitude: 74.3500,
      icon: 'school',
      sort_order: 3,
      pm25: null,
      pm10: null,
      temperature: null,
      humidity: null,
      aqi: { label: 'No Data', color: '#A09A93', band: 'none' },
      created_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'loc-demo-004',
      station_id: null,
      name: 'Shalimar Gardens',
      label: 'Park',
      latitude: 31.5860,
      longitude: 74.3240,
      icon: 'tree',
      sort_order: 4,
      pm25: null,
      pm10: null,
      temperature: null,
      humidity: null,
      aqi: { label: 'No Data', color: '#A09A93', band: 'none' },
      created_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ],
  count: 4,
};

/* ── AI Investigation Analysis ────────────────────────────── */

const DEMO_EXPOSURE = {
  event_location: {
    lat: 31.5204,
    lng: 74.3587,
    pm25: 165.0,
    severity: 'episode',
    trajectory: 'rising',
  },
  investigation_area: {
    type: 'upwind_investigation_corridor',
    coordinates: [
      [31.5204, 74.3587],
      [31.5264, 74.3780],
      [31.5324, 74.3900],
      [31.5384, 74.4020],
      [31.5324, 74.4140],
      [31.5264, 74.4260],
      [31.5204, 74.4380],
      [31.5144, 74.4260],
      [31.5084, 74.4140],
      [31.5024, 74.4020],
      [31.5084, 74.3900],
      [31.5144, 74.3780],
      [31.5204, 74.3587],
    ],
    center: { lat: 31.5204, lng: 74.3587 },
    direction_degrees: 90.0,
    direction_label: 'From East',
    distance_km: 8.0,
    width_degrees: 60,
    priority: 'HIGH',
    label: 'Priority Investigation Area',
    requires_ground_verification: true,
    uncertainty: 'Investigation corridor based on current wind direction. Local atmospheric conditions may alter actual pollutant transport.',
  },
  exposure_path: {
    type: 'approximate_downwind_cone',
    coordinates: [
      [31.5204, 74.3587],
      [31.5164, 74.3500],
      [31.5124, 74.3380],
      [31.5084, 74.3260],
      [31.5044, 74.3140],
      [31.5004, 74.3020],
      [31.4964, 74.2900],
      [31.4924, 74.2780],
      [31.4964, 74.2680],
      [31.5004, 74.2780],
      [31.5044, 74.2900],
      [31.5084, 74.3020],
      [31.5124, 74.3140],
      [31.5164, 74.3260],
      [31.5204, 74.3380],
      [31.5204, 74.3587],
    ],
    center: { lat: 31.5204, lng: 74.3587 },
    direction_degrees: 270.0,
    direction_label: 'Moving toward West',
    distance_km: 9.6,
    cone_width_degrees: 60,
    confidence: 'MODERATE',
    uncertainty: 'Approximate wind-driven trajectory. Local atmospheric conditions may change the actual dispersion path.',
  },
  vulnerable_locations: {
    schools: [
      { name: 'Government Primary School', type: 'school', lat: 31.5150, lng: 74.3450 },
      { name: 'Model School Lahore', type: 'school', lat: 31.5100, lng: 74.3300 },
      { name: 'Government High School', type: 'school', lat: 31.5080, lng: 74.3200 },
      { name: 'Allied School DHA', type: 'school', lat: 31.4950, lng: 74.3100 },
      { name: 'Beaconhouse School', type: 'school', lat: 31.5050, lng: 74.3400 },
    ],
    hospitals: [
      { name: 'Jinnah Hospital', type: 'hospital', lat: 31.5050, lng: 74.3350 },
      { name: 'Services Hospital', type: 'hospital', lat: 31.5120, lng: 74.3500 },
      { name: 'Mayo Hospital', type: 'hospital', lat: 31.5180, lng: 74.3350 },
    ],
    summary: {
      schools_in_path: 5,
      hospitals_in_path: 3,
    },
  },
  metadata: {
    wind_direction_degrees: 90.0,
    movement_bearing: 270.0,
    wind_speed_ms: 3.2,
    corridor_length_km: 8.0,
    cone_length_km: 9.6,
    computed_at: new Date().toISOString(),
  },
  uncertainty: null,
};

/**
 * DEMO_VERIFICATION — Simulated verification context response.
 * Shows what a response officer would see after submitting verification.
 */
const DEMO_VERIFICATION = {
  current_outcome: null,
  stats: {
    total_verifications: 5,
    useful_count: 3,
    partially_useful_count: 1,
    not_supported_count: 0,
    inconclusive_count: 1,
    recommendation_supported_pct: 80,
    area_supported_pct: 60,
    hypothesis_hit_rate: 70,
  },
  has_sufficient_data: true,
  disclaimer: 'Historical verification data provides context for ongoing investigations. It does not guarantee the accuracy of current AI analysis.',
};

/**
 * DEMO_VERIFICATION_PENDING — Pre-submission state with no outcome yet.
 */
const DEMO_VERIFICATION_PENDING = {
  current_outcome: null,
  stats: {
    total_verifications: 2,
    useful_count: 1,
    partially_useful_count: 0,
    not_supported_count: 0,
    inconclusive_count: 1,
    recommendation_supported_pct: null,
    area_supported_pct: null,
    hypothesis_hit_rate: null,
  },
  has_sufficient_data: false,
  disclaimer: 'Historical verification data provides context for ongoing investigations. It does not guarantee the accuracy of current AI analysis.',
};

/**
 * DEMO_VERIFICATION_COMPLETED — Pre-filled outcome showing completed verification.
 */
const DEMO_VERIFICATION_COMPLETED = {
  current_outcome: {
    outcome_id: 'vout-demo001',
    investigation_id: 'demo-investigation',
    overall_status: 'USEFUL',
    recommendation_verification: 'SUPPORTED',
    investigation_area_verification: 'PARTIALLY_SUPPORTED',
    hypothesis_verifications: [
      { factor: 'Industrial activity in Sahiwal corridor', verified: true, notes: 'Verified — multiple brick kilns observed' },
      { factor: 'Crop residue burning', verified: false, notes: 'Not observed in the field' },
      { factor: 'Traffic congestion', verified: true, notes: 'Heavy traffic at Ring Road junction' },
    ],
    field_notes: 'Investigation confirmed industrial emissions from Sahiwal corridor. Traffic contribution from Ring Road junction notable.',
    verified_by: 'Response Officer Khan',
    verified_at: '2024-12-15T14:30:00Z',
    created_at: '2024-12-15T14:30:00Z',
    updated_at: '2024-12-15T14:30:00Z',
  },
  stats: {
    total_verifications: 5,
    useful_count: 3,
    partially_useful_count: 1,
    not_supported_count: 0,
    inconclusive_count: 1,
    recommendation_supported_pct: 80,
    area_supported_pct: 60,
    hypothesis_hit_rate: 70,
  },
  has_sufficient_data: true,
  disclaimer: 'Historical verification data provides context for ongoing investigations. It does not guarantee the accuracy of current AI analysis.',
};

/**
 * DEMO_VERIFICATION_STATS — Aggregated statistics (used separately when needed).
 */
const DEMO_VERIFICATION_STATS = {
  total_verifications: 5,
  useful_count: 3,
  partially_useful_count: 1,
  not_supported_count: 0,
  inconclusive_count: 1,
  recommendation_supported_pct: 80,
  area_supported_pct: 60,
  hypothesis_hit_rate: 70,
};

/**
 * DEMO_INVESTIGATION_LEARNING — Historical investigation accountability context.
 * 12 cases: 8 USEFUL, 3 PARTIALLY_USEFUL, 1 NOT_SUPPORTED ≈ 79% reliability.
 * Framing: "Similar previously verified investigations showed..."
 */
const DEMO_INVESTIGATION_LEARNING = {
  historical_investigations_found: 12,
  verified_outcomes: {
    useful: 8,
    partially_useful: 3,
    not_supported: 1,
    inconclusive: 0,
    pending: 0,
    total_verified: 12,
  },
  recommendation_reliability: {
    score: 0.79,
    classification: 'MODERATE',
    description:
      'Of 12 similar previously verified investigations, 8 were found useful, 3 partially useful, and 1 not supported. This suggests moderate reliability for similar conditions.',
    useful_count: 8,
    partially_useful_count: 3,
    not_supported_count: 1,
    inconclusive_count: 0,
    total_evaluated: 12,
  },
  similar_cases: [
    {
      investigation_id: 'INV-2024-0892',
      outcome_id: 'VER-2024-0892',
      similarity_score: 0.92,
      date: '2024-11-15',
      overall_status: 'USEFUL',
      recommendation_verification: 'SUPPORTED',
      summary:
        'High PM25 episode with east wind sector. Open burning and traffic emissions confirmed as primary sources. Investigation corridor aligned with known industrial zone.',
      matching_dimensions: ['pm25_severity_band', 'wind_sector', 'trajectory', 'investigation_corridor'],
      differing_dimensions: ['humidity_band'],
    },
    {
      investigation_id: 'INV-2024-0756',
      outcome_id: 'VER-2024-0756',
      similarity_score: 0.87,
      date: '2024-10-28',
      overall_status: 'USEFUL',
      recommendation_verification: 'SUPPORTED',
      summary:
        'Similar episode-level PM25 with moderate wind. Road dust and traffic emissions were primary contributors.',
      matching_dimensions: ['pm25_severity_band', 'wind_sector', 'wind_speed_band'],
      differing_dimensions: ['temperature_band', 'investigation_corridor'],
    },
    {
      investigation_id: 'INV-2024-0634',
      outcome_id: 'VER-2024-0634',
      similarity_score: 0.81,
      date: '2024-10-12',
      overall_status: 'PARTIALLY_USEFUL',
      recommendation_verification: 'PARTIALLY_SUPPORTED',
      summary:
        'Episode PM25 with east wind. Industrial sources were overestimated; actual primary source was agricultural burning.',
      matching_dimensions: ['pm25_severity_band', 'wind_sector'],
      differing_dimensions: ['investigation_corridor', 'eligible_domains', 'humidity_band'],
    },
    {
      investigation_id: 'INV-2024-0501',
      outcome_id: 'VER-2024-0501',
      similarity_score: 0.76,
      date: '2024-09-22',
      overall_status: 'USEFUL',
      recommendation_verification: 'SUPPORTED',
      summary:
        'Moderate-high PM25 with light east wind. Traffic emissions and road dust confirmed.',
      matching_dimensions: ['wind_sector', 'wind_speed_band', 'eligible_domains'],
      differing_dimensions: ['pm25_severity_band', 'investigation_corridor'],
    },
    {
      investigation_id: 'INV-2024-0389',
      outcome_id: 'VER-2024-0389',
      similarity_score: 0.73,
      date: '2024-09-08',
      overall_status: 'NOT_SUPPORTED',
      recommendation_verification: 'NOT_SUPPORTED',
      summary:
        'PM25 episode with east wind but higher speeds. Open burning hypothesized but field investigation found predominantly vehicular sources.',
      matching_dimensions: ['wind_sector', 'pm25_severity_band'],
      differing_dimensions: ['wind_speed_band', 'eligible_domains', 'investigation_corridor'],
    },
  ],
  limitations: [
    'This analysis is based on 12 previously verified investigations — a small sample that may not represent all future conditions.',
    'Similarity matching uses 9 environmental dimensions with fixed weights; real-world conditions may differ in unmeasured ways.',
    'Historical verification outcomes reflect the judgment of individual verifiers and may contain bias.',
    'This provides accountability context, NOT a prediction of what will happen or what the AI recommends.',
    'Conditions not well-represented in the historical database may produce misleading similarity scores.',
    'The similarity algorithm is deterministic and rule-based — it does not learn or improve over time.',
  ],
  evidence_status: 'MODERATE',
  historical_context_message:
    'Similar previously verified investigations in the east wind sector with episode-level PM25 showed that investigation recommendations were useful in about 79% of cases (8 of 12). Open burning and traffic emissions were the most commonly confirmed sources in this pattern.',
  disclaimer:
    'This context is derived from deterministic comparison with previously verified investigations. It does NOT represent the AI\'s opinion, prediction, or recommendation. It is provided solely for accountability and transparency.',
};

const DEMO_INVESTIGATION = {
  evidence: {},
  analysis: {
    analysis_status: 'complete',
    event_summary:
      'An active pollution episode is underway in Lahore with PM2.5 at elevated levels. Wind is from the East sector with historical directional enrichment of 1.44x. Weather conditions are compatible with multiple investigation domains including open burning, traffic emissions, and industrial activity.',
    severity_assessment:
      'Episode state with rising trajectory indicates active pollution accumulation. Historical data shows 90.8% of episodes peak within 6 hours. Weather conditions (temperature < 18°C, moderate humidity) are consistent with winter episode patterns.',
    observed_facts: [
      {
        statement:
          'PM2.5 levels are in the episode range as determined by the rule-based episode detection system.',
        evidence_references: ['event_detection.data.state', 'event_detection.data.current_pm25'],
      },
      {
        statement:
          'Wind is currently arriving from the East sector at low speed.',
        evidence_references: ['directional_analysis.current_wind', 'directional_analysis.historical.strongest_sector'],
      },
      {
        statement:
          'The East sector shows 1.44x enrichment with historical pollution episodes based on 972 episode-hours of evidence.',
        evidence_references: ['directional_analysis.historical.strongest_enrichment', 'directional_analysis.historical.evidence_count'],
      },
    ],
    model_inferences: [
      {
        statement:
          'The directional enrichment in the East sector represents a statistical association between wind direction and historical episode occurrence, not a confirmed source.',
        confidence: 0.70,
        supporting_evidence: ['directional_analysis.historical.strongest_enrichment', 'directional_analysis.interpretation'],
      },
      {
        statement:
          'Historical analog matching found episodes with similar meteorological conditions, suggesting a recurring pattern.',
        confidence: 0.65,
        supporting_evidence: ['historical_analogs.matches', 'historical_analogs.total_episodes_searched'],
      },
    ],
    investigation_hypotheses: [
      {
        factor: 'East sector industrial or agricultural emissions',
        confidence: 0.65,
        reasoning:
          'Wind from the East sector with 1.44x historical enrichment suggests this corridor has higher episode association. Winter conditions (temperature < 18°C, low wind speed) allow pollutant accumulation.',
        supporting_evidence: ['directional_analysis.historical.strongest_enrichment', 'investigation_domains'],
        verification_needed:
          'Field inspection of industrial facilities and agricultural sites in the East corridor. Satellite imagery review for active burning signatures.',
      },
      {
        factor: 'Traffic emission accumulation under calm conditions',
        confidence: 0.55,
        reasoning:
          'Low wind speed (< 6 m/s) and high humidity (> 70%) create conditions where vehicle exhaust accumulates rather than disperses.',
        supporting_evidence: ['investigation_domains', 'weather_context.variables'],
        verification_needed:
          'Traffic count data for the episode period. Comparison with non-episode traffic patterns.',
      },
      {
        factor: 'Regional transport from upwind agricultural burning',
        confidence: 0.50,
        reasoning:
          'Historical episodes show similar meteorological patterns during the winter burning season. The East sector enrichment may partially reflect regional agricultural residue transport.',
        supporting_evidence: ['historical_analogs.matches', 'directional_analysis.historical.season'],
        verification_needed:
          'Fire detection satellite data (VIIRS/MODIS) for the broader region. Cross-reference with Punjab agricultural calendar.',
      },
    ],
    investigation_priority: {
      area: 'East sector corridor',
      priority: 'HIGH',
      rationale:
        'Highest directional enrichment (1.44x) with substantial evidence (972 episode-hours). Weather conditions favor accumulation.',
      confidence: 0.70,
    },
    likely_exposure_direction: {
      description:
        'Pollutant exposure likely concentrated in areas downwind of the East sector, based on current wind direction and historical enrichment patterns.',
      confidence: 0.65,
      limitations: [
        'Directional analysis shows association, not confirmed source',
        'Calm wind conditions may create localized accumulation patterns not captured by sector-level analysis',
      ],
    },
    recommended_actions: [
      {
        priority: 1,
        action: 'Deploy field inspection team to East sector corridor for visual assessment of industrial and agricultural activity',
        rationale: 'East sector shows highest historical enrichment with current wind conditions matching episode pattern',
        verification_goal: 'Confirm or rule out active emission sources in the corridor',
      },
      {
        priority: 2,
        action: 'Request satellite fire detection data (VIIRS/MODIS) for Lahore and upwind regions',
        rationale: 'Determine if open burning signatures are present in the region during this episode',
        verification_goal: 'Establish whether agricultural or waste burning contributes to current episode',
      },
      {
        priority: 3,
        action: 'Review traffic monitoring data for correlation with episode timing and location',
        rationale: 'Traffic emissions domain shows weather-compatible conditions (calm wind, high humidity)',
        verification_goal: 'Determine if traffic patterns correlate with episode intensification periods',
      },
    ],
    uncertainties: [
      'The source compass enrichment shows statistical association between wind direction and episodes, but does not confirm a specific emission source in the East sector.',
      'Historical analog matching uses meteorological similarity and does not account for changes in emission sources or regulatory conditions since the analog episodes occurred.',
      'Data freshness may affect the accuracy of current condition assessment — check data_quality.freshness_state for current status.',
      'The investigation domains are evaluated against weather triggers only and do not incorporate real-time emission inventory data.',
    ],
    data_gaps: [
      'No satellite fire detection data available in the current evidence package to confirm or rule out open burning.',
      'No real-time traffic volume data to assess traffic emission contribution during this episode.',
    ],
  },
  analysis_metadata: {
    mode: 'demo',
    provider: 'fixture',
    timestamp: new Date().toISOString(),
    is_fallback: false,
  },
};

/* ── Demo Analytics Data ─────────────────────────────────── */

const DEMO_ACCURACY_SUMMARY = {
  total_predictions: 1247,
  by_horizon: [
    { horizon: 1, total_predictions: 357, accuracy_mae: 12.3, accuracy_rmse: 18.7, avg_error: -1.24, max_error: 38.6, verified_count: 312, pending_count: 45 },
    { horizon: 3, total_predictions: 355, accuracy_mae: 18.9, accuracy_rmse: 27.4, avg_error: 2.11, max_error: 52.3, verified_count: 287, pending_count: 68 },
    { horizon: 6, total_predictions: 343, accuracy_mae: 28.1, accuracy_rmse: 39.2, avg_error: -3.47, max_error: 71.8, verified_count: 254, pending_count: 89 },
    { horizon: 12, total_predictions: 310, accuracy_mae: 42.6, accuracy_rmse: 58.3, avg_error: 5.82, max_error: 96.4, verified_count: 198, pending_count: 112 },
    { horizon: 24, total_predictions: 277, accuracy_mae: 61.4, accuracy_rmse: 82.1, avg_error: -7.35, max_error: 128.7, verified_count: 145, pending_count: 132 },
  ],
};

const DEMO_HORIZON_COMPARISON = {
  count: 5,
  horizons: [
    {
      horizon: 1,
      total_predictions: 357,
      verified_count: 312,
      accuracy_mae: 12.3,
      accuracy_rmse: 18.7,
      bias_mean: -1.2,
      within_25pct: 78.5,
      model_name: 'XGBoost v2.3',
      validation_mae: 11.8,
      live_mae: 12.3,
      status: 'deployed',
    },
    {
      horizon: 3,
      total_predictions: 355,
      verified_count: 287,
      accuracy_mae: 18.9,
      accuracy_rmse: 27.4,
      bias_mean: 2.1,
      within_25pct: 62.3,
      model_name: 'XGBoost v2.3',
      validation_mae: 17.4,
      live_mae: 18.9,
      status: 'deployed',
    },
    {
      horizon: 6,
      total_predictions: 343,
      verified_count: 254,
      accuracy_mae: 28.1,
      accuracy_rmse: 39.2,
      bias_mean: -3.5,
      within_25pct: 48.8,
      model_name: 'Random Forest v1.8',
      validation_mae: 25.6,
      live_mae: 28.1,
      status: 'deployed',
    },
    {
      horizon: 12,
      total_predictions: 310,
      verified_count: 198,
      accuracy_mae: 42.6,
      accuracy_rmse: 58.3,
      bias_mean: 5.8,
      within_25pct: 33.3,
      model_name: 'XGBoost v2.3',
      validation_mae: 38.9,
      live_mae: 42.6,
      status: 'deployed',
    },
    {
      horizon: 24,
      total_predictions: 277,
      verified_count: 145,
      accuracy_mae: 61.4,
      accuracy_rmse: 82.1,
      bias_mean: -8.2,
      within_25pct: 21.4,
      model_name: 'Gradient Boost v1.5',
      validation_mae: 55.2,
      live_mae: 61.4,
      status: 'candidate',
    },
  ],
};

/* ── Prediction Receipt Demo Data ──────────────────────────── */

/**
 * DEMO_PREDICTION_RECEIPT — Deterministic prediction receipt.
 * Every value is fixed. No randomness. No API dependency.
 * Shaped to demonstrate the full Predict → Verify → Learn loop.
 */
const DEMO_PREDICTION_RECEIPT = {
  receipt_id: 'LP-000184',
  prediction: {
    prediction_id: 'pred-demo-6h-001',
    predicted_pm25: 165,
    unit: 'ug/m3',
    horizon_hours: 6,
    prediction_time: '2026-08-28T14:00:00Z',
    target_time: '2026-08-28T20:00:00Z',
    model_version: 'lahore-pm25-v3.2',
    algorithm: 'HistGradientBoosting',
    confidence: 0.82,
    data_timestamp: '2026-08-28T13:42:00Z',
    freshness_hours: 0.3,
    feature_count: 47,
    warnings: [],
  },
  observation: {
    observed_pm25: 181,
    observed_at: '2026-08-28T20:00:00Z',
    station_id: 'us-embassy',
    station_name: 'US Embassy Monitoring Station',
    source: 'Open-Meteo (ECMWF IFS 9km)',
    quality_status: 'verified',
  },
  verification: {
    absolute_error: 16,
    percentage_error: 9.7,
    mape: 9.7,
    status: 'VERIFIED',
    verified_at: '2026-08-28T20:05:00Z',
    within_tolerance: true,
    tolerance_threshold: 20,
  },
  calibration: {
    confidence_level: 82,
    actual_error: 9.7,
    assessment: 'GOOD',
    explanation: 'Model expressed 82% confidence. Actual error was 9.7% — within the expected range for this confidence level.',
  },
  trust_snapshot: {
    total_evaluated: 1247,
    within_tolerance_pct: 78,
    confidence_calibration_score: 0.84,
    mean_absolute_error: 28.1,
    best_horizon: '1h',
    worst_horizon: '24h',
  },
  disclaimer: 'This receipt was generated from demonstration data. All values are deterministic and reproducible.',
};

/**
 * DEMO_MODEL_MISTAKES — Largest verified forecast errors.
 * Clearly labeled as demonstration data.
 */
const DEMO_MODEL_MISTAKES = [
  {
    rank: 1,
    prediction_id: 'pred-worst-001',
    predicted: 142,
    actual: 201,
    error_pct: 41.1,
    error_abs: 59,
    horizon: 24,
    confidence: 89,
    calibration: 'OVERCONFIDENT',
    model_version: 'lahore-pm25-v3.1',
    prediction_time: '2026-08-15T08:00:00Z',
    target_time: '2026-08-15T08:00:00Z',
    root_cause: 'Rapid accumulation event underestimated by historical patterns',
    explanation: 'Model expressed high confidence but substantially underestimated the observed concentration during a rapid accumulation event.',
  },
  {
    rank: 2,
    prediction_id: 'pred-worst-002',
    predicted: 210,
    actual: 168,
    error_pct: 25.0,
    error_abs: 42,
    horizon: 12,
    confidence: 78,
    calibration: 'OVERCONFIDENT',
    model_version: 'lahore-pm25-v3.2',
    prediction_time: '2026-08-20T10:00:00Z',
    target_time: '2026-08-20T22:00:00Z',
    root_cause: 'Wind-shift event dispersed pollution faster than expected',
    explanation: 'Model overestimated the peak during a wind-shift event that dispersed pollution faster than historical patterns suggested.',
  },
  {
    rank: 3,
    prediction_id: 'pred-worst-003',
    predicted: 95,
    actual: 131,
    error_pct: 37.9,
    error_abs: 36,
    horizon: 6,
    confidence: 71,
    calibration: 'UNDERESTIMATED',
    model_version: 'lahore-pm25-v3.2',
    prediction_time: '2026-08-22T16:00:00Z',
    target_time: '2026-08-22T22:00:00Z',
    root_cause: 'Regional transport event not captured by local features',
    explanation: 'An unexpected regional transport event brought additional pollution that was not captured by local weather features.',
  },
];

/**
 * DEMO_MODEL_SUCCESSES — Most accurate verified predictions.
 */
const DEMO_MODEL_SUCCESSES = [
  {
    rank: 1,
    predicted: 168,
    actual: 172,
    error_pct: 2.3,
    error_abs: 4,
    horizon: 1,
    confidence: 91,
    calibration: 'HIGH-CONFIDENCE / VERIFIED',
    model_version: 'lahore-pm25-v3.2',
    target_time: '2026-08-28T15:00:00Z',
  },
  {
    rank: 2,
    predicted: 155,
    actual: 152,
    error_pct: 2.0,
    error_abs: 3,
    horizon: 3,
    confidence: 85,
    calibration: 'HIGH-CONFIDENCE / VERIFIED',
    model_version: 'lahore-pm25-v3.2',
    target_time: '2026-08-27T20:00:00Z',
  },
  {
    rank: 3,
    predicted: 189,
    actual: 195,
    error_pct: 3.1,
    error_abs: 6,
    horizon: 6,
    confidence: 79,
    calibration: 'MODERATE-CONFIDENCE / VERIFIED',
    model_version: 'lahore-pm25-v3.2',
    target_time: '2026-08-26T22:00:00Z',
  },
];

/**
 * DEMO_WHY_TRUST — Evidence-based trust panel.
 */
const DEMO_WHY_TRUST = {
  total_evaluated: 1247,
  within_tolerance_pct: 78,
  tolerance_description: 'within ±20% of observed PM2.5',
  confidence_tracked: true,
  forecasts_independently_verified: true,
  errors_visible: true,
  insufficient_data: false,
};

/**
 * DEMO_CONFIDENCE_CALIBRATION_TABLE — Per-horizon calibration data.
 */
const DEMO_CONFIDENCE_CALIBRATION_TABLE = [
  { horizon: 1, avg_confidence: 91, avg_error: 12.3, assessment: 'GOOD', predictions: 357 },
  { horizon: 3, avg_confidence: 85, avg_error: 18.9, assessment: 'GOOD', predictions: 355 },
  { horizon: 6, avg_confidence: 79, avg_error: 28.1, assessment: 'ACCEPTABLE', predictions: 343 },
  { horizon: 12, avg_confidence: 72, avg_error: 42.6, assessment: 'OVERCONFIDENT', predictions: 310 },
  { horizon: 24, avg_confidence: 65, avg_error: 61.4, assessment: 'OVERCONFIDENT', predictions: 277 },
];

/**
 * DEMO_ACCOUNTABILITY_TIMELINE — Prediction accountability records for demo.
 * Consistent with the single coherent scenario: 85→110→135→150→165→172→181
 * PM2.5 progression across the 7 demo steps.
 */
const DEMO_ACCOUNTABILITY_TIMELINE = {
  count: 6,
  horizon_filter: null,
  summary: {
    total_predictions: 1247,
    pending: 189,
    verified: 891,
    awaiting_verification: 167,
    verification_rate: 71.4,
  },
  timeline: [
    {
      prediction_id: 'pred-demo-1h-001',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'Ridge Regression',
      horizon: 1,
      prediction_time: '2026-08-28T19:00:00Z',
      target_time: '2026-08-28T20:00:00Z',
      predicted: 172,
      actual: 181,
      error: 9,
      status: 'verified',
      data_timestamp: '2026-08-28T18:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
    {
      prediction_id: 'pred-demo-3h-001',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'HistGradientBoosting',
      horizon: 3,
      prediction_time: '2026-08-28T17:00:00Z',
      target_time: '2026-08-28T20:00:00Z',
      predicted: 198,
      actual: 181,
      error: -17,
      status: 'verified',
      data_timestamp: '2026-08-28T16:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
    {
      prediction_id: 'pred-demo-6h-001',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'HistGradientBoosting',
      horizon: 6,
      prediction_time: '2026-08-28T14:00:00Z',
      target_time: '2026-08-28T20:00:00Z',
      predicted: 165,
      actual: 181,
      error: 16,
      status: 'verified',
      data_timestamp: '2026-08-28T13:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
    {
      prediction_id: 'pred-demo-12h-001',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'HistGradientBoosting',
      horizon: 12,
      prediction_time: '2026-08-28T08:00:00Z',
      target_time: '2026-08-28T20:00:00Z',
      predicted: 142,
      actual: 181,
      error: 39,
      status: 'verified',
      data_timestamp: '2026-08-28T07:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
    {
      prediction_id: 'pred-demo-24h-001',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'Ridge Regression',
      horizon: 24,
      prediction_time: '2026-08-27T20:00:00Z',
      target_time: '2026-08-28T20:00:00Z',
      predicted: 128,
      actual: 181,
      error: 53,
      status: 'verified',
      data_timestamp: '2026-08-27T19:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
    {
      prediction_id: 'pred-demo-1h-002',
      model_version: 'lahore-pm25-v3.2',
      algorithm: 'Ridge Regression',
      horizon: 1,
      prediction_time: '2026-08-29T08:00:00Z',
      target_time: '2026-08-29T09:00:00Z',
      predicted: 156,
      actual: null,
      error: null,
      status: 'pending',
      data_timestamp: '2026-08-29T07:42:00Z',
      feature_count: 47,
      data_freshness_hours: 0.3,
    },
  ],
};

/* ── Demo Context ────────────────────────────────────────── */

const DemoDataContext = createContext(null);

/** Check if ?demo=true is in the URL or was previously activated. */
function isDemoUrl() {
  if (typeof window === 'undefined') return false;
  const urlParam = new URLSearchParams(window.location.search).get('demo') === 'true';
  if (urlParam) {
    // Persist so demo survives post-login redirect (which drops query params)
    try { sessionStorage.setItem('lahore_plus_demo_mode', '1'); } catch {}
    return true;
  }
  // Check persisted flag (set when ?demo=true was first encountered)
  try { return sessionStorage.getItem('lahore_plus_demo_mode') === '1'; } catch {}
  return false;
}

/**
 * Parse a valid step number from the URL ?step= param.
 * Returns null if missing, invalid, or out of range.
 */
function parseStepFromUrl() {
  if (typeof window === 'undefined') return null;
  try {
    const params = new URLSearchParams(window.location.search);
    const raw = params.get('step');
    if (raw === null || raw === '') return null;
    const step = parseInt(raw, 10);
    return (step >= 1 && step <= TOTAL_STEPS) ? step : null;
  } catch {
    return null;
  }
}

/**
 * Write the current step to the URL without creating a history entry.
 * Keeps URL as the source of truth for deep linking.
 */
function syncStepToUrl(step) {
  if (typeof window === 'undefined') return;
  try {
    const url = new URL(window.location.href);
    url.searchParams.set('step', String(step));
    window.history.replaceState(window.history.state, '', url.toString());
  } catch {
    // ignore — URL manipulation may fail in restricted contexts
  }
}

/**
 * Write a step to sessionStorage (silently ignored if unavailable).
 */
function persistStepToSession(step) {
  try { sessionStorage.setItem('lahore_plus_demo_step', String(step)); } catch {}
}

/**
 * Remove all demo state from sessionStorage.
 */
function clearDemoSession() {
  try {
    sessionStorage.removeItem('lahore_plus_demo_step');
    sessionStorage.removeItem('lahore_plus_demo_mode');
  } catch {
    // ignore
  }
}

/**
 * DemoModeProvider — wraps children and provides demo data
 * when ?demo=true is in the URL.
 *
 * Deterministic state precedence:
 *   1. URL ?step=N (highest — enables deep linking)
 *   2. sessionStorage lahore_plus_demo_step (survives refresh)
 *   3. Default to Step 1
 *
 * On step change → URL and sessionStorage are both updated.
 * On reset → sessionStorage cleared, step set to 1, URL updated.
 */

/**
 * DEMO_REPLAY_VERIFICATION — Verification badges for replay episodes.
 * Maps date → verification summary so ReplayView can show verified/total counts.
 */
const DEMO_REPLAY_VERIFICATION = {
  '2024-11-13': { verified: 18, total: 24, meanError: 14.2, trustRating: 'Moderate' },
  '2024-11-14': { verified: 20, total: 24, meanError: 11.8, trustRating: 'Good' },
  '2024-11-15': { verified: 22, total: 24, meanError: 9.5, trustRating: 'Strong' },
  '2024-11-20': { verified: 16, total: 24, meanError: 18.7, trustRating: 'Moderate' },
  '2024-12-01': { verified: 21, total: 24, meanError: 10.3, trustRating: 'Good' },
  '2024-12-10': { verified: 19, total: 24, meanError: 13.1, trustRating: 'Moderate' },
  '2025-01-05': { verified: 23, total: 24, meanError: 8.9, trustRating: 'Strong' },
  '2025-01-18': { verified: 17, total: 24, meanError: 16.4, trustRating: 'Moderate' },
  '2025-02-01': { verified: 20, total: 24, meanError: 12.0, trustRating: 'Good' },
  '2025-02-14': { verified: 22, total: 24, meanError: 9.1, trustRating: 'Strong' },
  '2025-03-01': { verified: 18, total: 24, meanError: 15.3, trustRating: 'Moderate' },
  '2025-03-15': { verified: 21, total: 24, meanError: 10.7, trustRating: 'Good' },
};

/**
 * DEMO_AUDIT_TRAIL — 8 event audit log for this prediction lifecycle.
 * Timestamps are deterministic. Clearly labeled as demonstration data.
 */
const DEMO_AUDIT_TRAIL = [
  { id: 'audit-001', timestamp: '2026-08-28T13:42:00Z', action: 'Data Ingested', actor: 'System', detail: '47 features collected from monitoring station, meteorological API, and historical database', icon: 'database' },
  { id: 'audit-002', timestamp: '2026-08-28T13:42:12Z', action: 'Evidence Assembled', actor: 'System', detail: 'Wind pattern, source compass, and historical analogs combined into evidence context', icon: 'layers' },
  { id: 'audit-003', timestamp: '2026-08-28T13:42:18Z', action: 'Investigation Brief', actor: 'AI', detail: '3 constrained hypotheses generated. Best match: industrial emissions in East sector (confidence 67%)', icon: 'brain' },
  { id: 'audit-004', timestamp: '2026-08-28T13:42:24Z', action: 'Prediction Made', actor: 'AI', detail: 'PM2.5 forecast: 165 µg/m³ at 6h horizon. Model version: lahore-pm25-v3.2 (HistGradientBoosting)', icon: 'trending-up' },
  { id: 'audit-005', timestamp: '2026-08-28T13:42:30Z', action: 'Alert Generated', actor: 'System', detail: 'Critical threshold (150 µg/m³) exceeded. Decision support alert issued to authorized personnel', icon: 'alert-triangle' },
  { id: 'audit-006', timestamp: '2026-08-28T20:05:00Z', action: 'Observation Verified', actor: 'System', detail: 'Observed PM2.5: 181 µg/m³. Absolute error: 16 µg/m³ (9.7%). Within tolerance (≤20%)', icon: 'check-circle' },
  { id: 'audit-007', timestamp: '2026-08-28T20:05:12Z', action: 'Investigation Reviewed', actor: 'Officer', detail: 'Investigator outcome recorded: industrial emissions confirmed. Investigation recommendation: Useful', icon: 'user-check' },
  { id: 'audit-008', timestamp: '2026-08-28T20:06:00Z', action: 'Receipt Finalized', actor: 'System', detail: 'Prediction receipt LP-000184 generated. Confidence calibration: GOOD. Record permanently stored', icon: 'file-text' },
];

/**
 * DEMO_DECISION_EVIDENCE_CHAIN — 5 sequential steps answering
 * "Why do we trust this alert?" References data from existing fixtures.
 */
const DEMO_DECISION_EVIDENCE_CHAIN = [
  { id: 'dec-step-1', title: 'Data Foundation', icon: 'database', status: 'complete', data: { label: '47 features ingested', source: 'Monitoring station + ECMWF meteorological model', freshness: '18 minutes before prediction', detail: 'Air quality sensors, wind speed/direction, temperature, humidity, pressure, and historical baselines from 972 comparable episode-hours' } },
  { id: 'dec-step-2', title: 'AI Prediction', icon: 'brain', status: 'complete', data: { label: '165 µg/m³ predicted at 6h horizon', source: 'HistGradientBoosting ensemble (v3.2)', confidence: '82%', detail: 'Algorithm trained on verified historical episodes. Confidence calibrated against 1,247 prior predictions. Model does not know the actual outcome when making this prediction' } },
  { id: 'dec-step-3', title: 'Investigation Brief', icon: 'search', status: 'complete', data: { label: '3 constrained hypotheses', source: 'Evidence chain + historical analog matching', bestMatch: 'Industrial emissions (67% match)', detail: 'Hypotheses bounded by physical plausibility. No single-cause claim. 3 data gaps flagged for human review. Uncertainty explicitly reported' } },
  { id: 'dec-step-4', title: 'Verification', icon: 'check-circle', status: 'complete', data: { label: '9.7% error (within tolerance)', source: 'Observed 181 µg/m³ vs. predicted 165 µg/m³', calibration: 'GOOD — confidence matched accuracy', detail: 'Prediction was conservative (underestimated). Error is within the 20% tolerance for this confidence level. This means the model was honest about its uncertainty' } },
  { id: 'dec-step-5', title: 'Accountability', icon: 'shield', status: 'complete', data: { label: 'Receipt LP-000184 finalized', source: 'Prediction verified, investigation reviewed, record stored', permanent: 'Cannot be edited after the fact', detail: 'Full audit trail from data ingestion to verification is preserved. Every step has timestamp, actor, and detail. Available for independent review at any time' } },
];

export function DemoModeProvider({ children }) {
  const [isDemo, setIsDemo] = useState(isDemoUrl);

  // Deterministic initialization: URL > sessionStorage > default
  const [demoStep, setDemoStepRaw] = useState(() => {
    const urlStep = parseStepFromUrl();
    if (urlStep !== null) {
      persistStepToSession(urlStep);
      return urlStep;
    }
    try {
      const saved = sessionStorage.getItem('lahore_plus_demo_step');
      const step = saved ? parseInt(saved, 10) : 1;
      return (step >= 1 && step <= TOTAL_STEPS) ? step : 1;
    } catch {
      return 1;
    }
  });

  useEffect(() => {
    const check = () => setIsDemo(isDemoUrl());
    window.addEventListener('popstate', check);
    return () => window.removeEventListener('popstate', check);
  }, []);

  // Wrapper: every step change syncs to both URL and sessionStorage
  const setDemoStep = useCallback((stepOrFn) => {
    setDemoStepRaw((prev) => {
      const next = typeof stepOrFn === 'function' ? stepOrFn(prev) : stepOrFn;
      // Clamp to valid range (1–TOTAL_STEPS)
      const safe = Math.max(1, Math.min(TOTAL_STEPS, next));
      persistStepToSession(safe);
      syncStepToUrl(safe);
      return safe;
    });
  }, []);

  const resetDemo = useCallback(() => {
    clearDemoSession();
    setDemoStepRaw(1);
    syncStepToUrl(1);
  }, []);

  if (!isDemo) return children;

  return (
    <DemoDataContext.Provider value={{
      episodeNormal: DEMO_EPISODE_NORMAL,
      episode: DEMO_EPISODE,
      forecasts: DEMO_FORECASTS,
      forecastStatus: DEMO_FORECAST_STATUS,
      analogs: DEMO_ANALOGS,
      alertHistory: DEMO_ALERT_HISTORY,
      reports: DEMO_REPORTS,
      favorites: DEMO_FAVORITES,
      stations: DEMO_STATIONS,
      investigationAnalysis: DEMO_INVESTIGATION,
      exposureGeometry: DEMO_EXPOSURE,
      verification: DEMO_VERIFICATION,
      verificationPending: DEMO_VERIFICATION_PENDING,
      verificationCompleted: DEMO_VERIFICATION_COMPLETED,
      verificationStats: DEMO_VERIFICATION_STATS,
      investigationLearning: DEMO_INVESTIGATION_LEARNING,
      accuracySummary: DEMO_ACCURACY_SUMMARY,
      horizonComparison: DEMO_HORIZON_COMPARISON,
      predictionReceipt: DEMO_PREDICTION_RECEIPT,
      modelMistakes: DEMO_MODEL_MISTAKES,
      modelSuccesses: DEMO_MODEL_SUCCESSES,
      whyTrust: DEMO_WHY_TRUST,
      confidenceCalibrationTable: DEMO_CONFIDENCE_CALIBRATION_TABLE,
      accountabilityTimeline: DEMO_ACCOUNTABILITY_TIMELINE,
      replayVerification: DEMO_REPLAY_VERIFICATION,
      auditTrail: DEMO_AUDIT_TRAIL,
      evidenceChain: DEMO_DECISION_EVIDENCE_CHAIN,
      /* Demo step control */
      demoStep,
      setDemoStep,
      resetDemo,
    }}>
      {children}
    </DemoDataContext.Provider>
  );
}

/**
 * Hook to access demo data. Returns null when not in demo mode.
 */
export function useDemoData() {
  return useContext(DemoDataContext);
}

/* ── Exported fixture data (for direct use) ──────────────── */

export { DEMO_EPISODE, DEMO_FORECASTS, DEMO_FORECAST_STATUS, DEMO_ANALOGS, DEMO_ALERT_HISTORY, DEMO_REPORTS, DEMO_FAVORITES, DEMO_STATIONS, DEMO_INVESTIGATION, DEMO_EXPOSURE, DEMO_VERIFICATION, DEMO_VERIFICATION_PENDING, DEMO_VERIFICATION_COMPLETED, DEMO_VERIFICATION_STATS, DEMO_INVESTIGATION_LEARNING, DEMO_PREDICTION_RECEIPT, DEMO_MODEL_MISTAKES, DEMO_MODEL_SUCCESSES, DEMO_WHY_TRUST, DEMO_CONFIDENCE_CALIBRATION_TABLE, DEMO_AUDIT_TRAIL, DEMO_DECISION_EVIDENCE_CHAIN };
export { isDemoUrl };
export { parseStepFromUrl, syncStepToUrl, persistStepToSession, clearDemoSession };
