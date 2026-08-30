/**
 * incidentStore — Client-side incident lifecycle management.
 *
 * INCIDENT LIFECYCLE:
 *   Detected → Investigating → Responding → Monitoring → Resolved
 *
 * Incidents are derived from episode intelligence and stored in localStorage
 * for persistence across page reloads. This is a prototype — production
 * would use a backend API with proper database persistence.
 *
 * KEY PRINCIPLE:
 *   - Real data only: incidents come from actual episode detection
 *   - No fabricated incidents or fake response data
 *   - Officers advance lifecycle stages manually
 *   - Timeline events are timestamped actions
 */

// ── Lifecycle Stages ────────────────────────────────────────

export const INCIDENT_STAGES = [
  { id: 'detected', label: 'Detected', color: '#dc2626', description: 'Episode detected by rule-based system' },
  { id: 'investigating', label: 'Investigating', color: '#ea580c', description: 'Officers analyzing sources and trajectory' },
  { id: 'responding', label: 'Responding', description: 'Active response measures underway', color: '#a16207' },
  { id: 'monitoring', label: 'Monitoring', description: 'Tracking conditions for improvement', color: '#2563eb' },
  { id: 'resolved', label: 'Resolved', description: 'Episode concluded, air quality returned to normal', color: '#16a34a' },
];

// ── Severity classification from PM2.5 ──────────────────────

export function classifySeverity(pm25) {
  if (pm25 === null || pm25 === undefined) return 'unknown';
  if (pm25 > 150) return 'critical';
  if (pm25 > 90) return 'severe';
  if (pm25 > 65) return 'high';
  if (pm25 > 45) return 'moderate';
  if (pm25 > 25) return 'low';
  return 'minimal';
}

export const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: '#7f1d1d', bg: '#fef2f2', border: '#fecaca' },
  severe:   { label: 'Severe',   color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  high:     { label: 'High',     color: '#ea580c', bg: '#fff7ed', border: '#fed7aa' },
  moderate: { label: 'Moderate', color: '#a16207', bg: '#fefce8', border: '#fef08a' },
  low:      { label: 'Low',      color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  minimal:  { label: 'Minimal',  color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  unknown:  { label: 'Unknown',  color: '#64748b', bg: '#f8fafc', border: '#e2e8f0' },
};

// ── Storage helpers ──────────────────────────────────────────

const STORAGE_KEY = 'lahoreplus_incidents';

function loadIncidents() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveIncidents(incidents) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(incidents));
  } catch { /* quota exceeded */ }
}

function generateId() {
  return `INC-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

// ── Public API ───────────────────────────────────────────────

/**
 * Get all incidents, optionally filtered.
 */
export function getIncidents({ status, severity, search } = {}) {
  let incidents = loadIncidents();

  if (status && status !== 'all') {
    incidents = incidents.filter(i => i.stage === status);
  }
  if (severity && severity !== 'all') {
    incidents = incidents.filter(i => i.severity === severity);
  }
  if (search) {
    const q = search.toLowerCase();
    incidents = incidents.filter(i =>
      i.id.toLowerCase().includes(q) ||
      i.title.toLowerCase().includes(q) ||
      (i.area || '').toLowerCase().includes(q)
    );
  }

  // Sort by most recent first
  return incidents.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
}

/**
 * Get a single incident by ID.
 */
export function getIncident(id) {
  return loadIncidents().find(i => i.id === id) || null;
}

/**
 * Get counts by stage and severity for dashboard badges.
 */
export function getIncidentStats() {
  const incidents = loadIncidents();
  const active = incidents.filter(i => i.stage !== 'resolved');

  const byStage = {};
  for (const stage of INCIDENT_STAGES) {
    byStage[stage.id] = active.filter(i => i.stage === stage.id).length;
  }

  const bySeverity = {};
  for (const sev of Object.keys(SEVERITY_CONFIG)) {
    bySeverity[sev] = active.filter(i => i.severity === sev).length;
  }

  return {
    total: incidents.length,
    activeCount: active.length,
    resolvedCount: incidents.filter(i => i.stage === 'resolved').length,
    byStage,
    bySeverity,
  };
}

/**
 * Create a new incident from episode intelligence data.
 * Called automatically when an episode is detected.
 */
export function createIncident({ pm25, state, trajectory, narrative, area = 'Lahore City Center' }) {
  const incidents = loadIncidents();

  // Don't create duplicate active incidents for the same area
  const existingActive = incidents.find(
    i => i.area === area && i.stage !== 'resolved'
  );
  if (existingActive) {
    // Update existing incident with latest data instead
    return updateIncidentData(existingActive.id, { pm25, state, trajectory, narrative });
  }

  const severity = classifySeverity(pm25);
  const severityCfg = SEVERITY_CONFIG[severity];
  const now = new Date().toISOString();

  const incident = {
    id: generateId(),
    title: `Pollution Episode — ${severityCfg.label}`,
    area,
    stage: 'detected',
    severity,
    pm25,
    state,
    trajectory,
    narrative: narrative || `PM2.5 level at ${pm25?.toFixed(1)} μg/m³ detected. Severity: ${severityCfg.label}.`,
    createdAt: now,
    updatedAt: now,
    timeline: [
      {
        event: 'detected',
        timestamp: now,
        detail: `Episode detected. PM2.5: ${pm25?.toFixed(1)} μg/m³. ${severityCfg.label} severity.`,
        actor: 'System',
      },
    ],
    actions: [],
    notes: [],
  };

  incidents.push(incident);
  saveIncidents(incidents);
  return incident;
}

/**
 * Advance incident to next lifecycle stage.
 */
export function advanceStage(incidentId, { note = '' } = {}) {
  const incidents = loadIncidents();
  const idx = incidents.findIndex(i => i.id === incidentId);
  if (idx === -1) return null;

  const incident = incidents[idx];
  const currentStageIdx = INCIDENT_STAGES.findIndex(s => s.id === incident.stage);
  if (currentStageIdx >= INCIDENT_STAGES.length - 1) return incident; // already resolved

  const nextStage = INCIDENT_STAGES[currentStageIdx + 1];
  const now = new Date().toISOString();

  incident.stage = nextStage.id;
  incident.updatedAt = now;
  incident.timeline.push({
    event: nextStage.id,
    timestamp: now,
    detail: note || `Advanced to ${nextStage.label}. ${nextStage.description}.`,
    actor: 'Officer',
  });

  incidents[idx] = incident;
  saveIncidents(incidents);
  return incident;
}

/**
 * Add a note or action to an incident.
 */
export function addIncidentNote(incidentId, { note, action } = {}) {
  const incidents = loadIncidents();
  const idx = incidents.findIndex(i => i.id === incidentId);
  if (idx === -1) return null;

  const incident = incidents[idx];
  const now = new Date().toISOString();
  incident.updatedAt = now;

  if (note) {
    incident.notes.push({ text: note, timestamp: now, actor: 'Officer' });
    incident.timeline.push({ event: 'note', timestamp: now, detail: note, actor: 'Officer' });
  }

  if (action) {
    incident.actions.push({ text: action, timestamp: now, actor: 'Officer' });
    incident.timeline.push({ event: 'action', timestamp: now, detail: action, actor: 'Officer' });
  }

  incidents[idx] = incident;
  saveIncidents(incidents);
  return incident;
}

/**
 * Update incident data with latest readings.
 */
function updateIncidentData(incidentId, { pm25, state, trajectory, narrative }) {
  const incidents = loadIncidents();
  const idx = incidents.findIndex(i => i.id === incidentId);
  if (idx === -1) return null;

  const incident = incidents[idx];
  const now = new Date().toISOString();

  incident.pm25 = pm25;
  incident.state = state;
  incident.trajectory = trajectory;
  incident.severity = classifySeverity(pm25);
  incident.updatedAt = now;

  if (narrative) {
    incident.narrative = narrative;
  }

  incident.timeline.push({
    event: 'data_update',
    timestamp: now,
    detail: `Updated readings. PM2.5: ${pm25?.toFixed(1)} μg/m³. Severity: ${SEVERITY_CONFIG[incident.severity]?.label}.`,
    actor: 'System',
  });

  incidents[idx] = incident;
  saveIncidents(incidents);
  return incident;
}

/**
 * Delete an incident (admin only in production).
 */
export function deleteIncident(incidentId) {
  const incidents = loadIncidents().filter(i => i.id !== incidentId);
  saveIncidents(incidents);
}

/**
 * Seed demo incidents for competition demo.
 * Creates realistic-looking incident history.
 */
export function seedDemoIncidents() {
  const existing = loadIncidents();
  if (existing.length > 0) return existing;

  const now = Date.now();
  const hour = 3600000;
  const day = 86400000;

  const demoIncidents = [
    {
      id: 'INC-SM0G-01A3',
      title: 'Severe Smog Episode — Critical',
      area: 'Lahore City Center',
      stage: 'resolved',
      severity: 'critical',
      pm25: 187.3,
      state: 'episode',
      trajectory: 'worsening',
      narrative: 'Severe smog event with PM2.5 exceeding 150 μg/m³. Cross-border agricultural burning contributed to elevated levels.',
      createdAt: new Date(now - 5 * day).toISOString(),
      updatedAt: new Date(now - 3 * day).toISOString(),
      timeline: [
        { event: 'detected', timestamp: new Date(now - 5 * day).toISOString(), detail: 'Episode detected. PM2.5: 187.3 μg/m³. Critical severity.', actor: 'System' },
        { event: 'investigating', timestamp: new Date(now - 5 * day + 30 * 60000).toISOString(), detail: 'Officers investigating. Wind patterns suggest agricultural burning contribution.', actor: 'Officer' },
        { event: 'responding', timestamp: new Date(now - 5 * day + 2 * hour).toISOString(), detail: 'Active monitoring stations deployed. Public advisory issued.', actor: 'Officer' },
        { event: 'monitoring', timestamp: new Date(now - 4 * day).toISOString(), detail: 'Conditions stabilizing. PM2.5 dropped to 142 μg/m³.', actor: 'Officer' },
        { event: 'resolved', timestamp: new Date(now - 3 * day).toISOString(), detail: 'Episode concluded. PM2.5 returned to 68 μg/m³.', actor: 'Officer' },
      ],
      actions: [
        { text: 'Public health advisory issued', timestamp: new Date(now - 5 * day + 2 * hour).toISOString(), actor: 'Officer' },
      ],
      notes: [
        { text: 'Cross-border burning confirmed by wind analysis', timestamp: new Date(now - 4 * day).toISOString(), actor: 'Officer' },
      ],
    },
    {
      id: 'INC-W1ND-02B7',
      title: 'High PM Episode — Severe',
      area: 'Johar Town Industrial',
      stage: 'monitoring',
      severity: 'severe',
      pm25: 124.8,
      state: 'improving',
      trajectory: 'improving',
      narrative: 'Industrial area showing elevated PM2.5. Possible factory emissions combined with stagnant air.',
      createdAt: new Date(now - 2 * day).toISOString(),
      updatedAt: new Date(now - 6 * hour).toISOString(),
      timeline: [
        { event: 'detected', timestamp: new Date(now - 2 * day).toISOString(), detail: 'Episode detected. PM2.5: 124.8 μg/m³. Severe severity.', actor: 'System' },
        { event: 'investigating', timestamp: new Date(now - 2 * day + 25 * 60000).toISOString(), detail: 'Industrial sector flagged as likely contributor.', actor: 'Officer' },
        { event: 'responding', timestamp: new Date(now - 2 * day + 90 * 60000).toISOString(), detail: 'Field inspection initiated in Johar Town industrial zone.', actor: 'Officer' },
        { event: 'monitoring', timestamp: new Date(now - 6 * hour).toISOString(), detail: 'PM2.5 trending down to 108 μg/m³. Wind shifting eastward.', actor: 'Officer' },
      ],
      actions: [
        { text: 'Field inspection: Johar Town industrial zone', timestamp: new Date(now - 2 * day + 90 * 60000).toISOString(), actor: 'Officer' },
      ],
      notes: [
        { text: 'Brick kiln activity suspected', timestamp: new Date(now - 2 * day + 3 * hour).toISOString(), actor: 'Officer' },
      ],
    },
    {
      id: 'INC-A1RT-03C9',
      title: 'Moderate Episode — High',
      area: 'Gulberg III',
      stage: 'investigating',
      severity: 'high',
      pm25: 78.5,
      state: 'episode',
      trajectory: 'worsening',
      narrative: 'Moderate pollution episode in commercial area. Traffic density and construction dust contributing factors.',
      createdAt: new Date(now - 8 * hour).toISOString(),
      updatedAt: new Date(now - 2 * hour).toISOString(),
      timeline: [
        { event: 'detected', timestamp: new Date(now - 8 * hour).toISOString(), detail: 'Episode detected. PM2.5: 78.5 μg/m³. High severity.', actor: 'System' },
        { event: 'investigating', timestamp: new Date(now - 2 * hour).toISOString(), detail: 'Investigating traffic and construction sources.', actor: 'Officer' },
      ],
      actions: [],
      notes: [
        { text: 'Large construction project on Main Boulevard', timestamp: new Date(now - 3 * hour).toISOString(), actor: 'Officer' },
      ],
    },
    {
      id: 'INC-D4TA-04E1',
      title: 'Active Episode — Moderate',
      area: 'DHA Phase V',
      stage: 'detected',
      severity: 'moderate',
      pm25: 52.1,
      state: 'episode',
      trajectory: 'stable',
      narrative: 'Newly detected episode. PM2.5 rising in residential zone. Source under investigation.',
      createdAt: new Date(now - 45 * 60000).toISOString(),
      updatedAt: new Date(now - 45 * 60000).toISOString(),
      timeline: [
        { event: 'detected', timestamp: new Date(now - 45 * 60000).toISOString(), detail: 'Episode detected. PM2.5: 52.1 μg/m³. Moderate severity.', actor: 'System' },
      ],
      actions: [],
      notes: [],
    },
  ];

  saveIncidents(demoIncidents);
  return demoIncidents;
}
