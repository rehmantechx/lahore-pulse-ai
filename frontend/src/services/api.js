/**
 * Lahore Pulse AI — API Client.
 *
 * Centralized HTTP client for all backend communication.
 * All API endpoints, error handling, timeout, and response
 * validation live here. Components never call fetch() directly.
 *
 * Backend is the source of truth for all data schemas.
 */

const DEFAULT_TIMEOUT_MS = 15000;
const API_BASE = '/api/v1';

// ── Error Classes ──────────────────────────────────────────────

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export class NetworkError extends Error {
  constructor(message, originalError) {
    super(message);
    this.name = 'NetworkError';
    this.originalError = originalError;
  }
}

export class TimeoutError extends Error {
  constructor(timeoutMs) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

// ── Auth Token Reader ──────────────────────────────────────────

/**
 * Read the authentication token from localStorage.
 *
 * Uses the same key as AuthContext (lahore_plus_auth).
 * Returns null if no saved session exists or token cannot be read.
 *
 * @returns {string|null} Bearer token or null for unauthenticated users
 */
function _readAuthToken() {
  try {
    const saved = localStorage.getItem('lahore_plus_auth');
    if (!saved) return null;
    const parsed = JSON.parse(saved);
    return parsed.token || null;
  } catch {
    return null;
  }
}

// ── Core Fetch Wrapper ─────────────────────────────────────────

/**
 * Execute an API request with timeout, error parsing, and
 * response validation.
 *
 * Automatically attaches Authorization: Bearer <token> header
 * when a valid session exists in localStorage. Public endpoints
 * work regardless of auth state.
 *
 * @param {string} path - API path (e.g., '/forecast/all')
 * @param {object} options - fetch options + timeout
 * @returns {Promise<object>} Parsed JSON response
 */
async function apiFetch(path, options = {}) {
  const { timeout = DEFAULT_TIMEOUT_MS, signal: externalSignal, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Combine external signal if provided
  if (externalSignal) {
    externalSignal.addEventListener('abort', () => controller.abort());
  }

  // Read auth token from localStorage (same key as AuthContext)
  const token = _readAuthToken();

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        // Inject auth token if user has an active session
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      // 401 Unauthorized: clear stale token so ProtectedRoute redirects to login
      if (response.status === 401) {
        try { localStorage.removeItem('lahore_plus_auth'); } catch { /* ignore */ }
      }

      let errorBody;
      try {
        errorBody = await response.json();
      } catch {
        errorBody = { error: { code: 'UNKNOWN', message: response.statusText } };
      }

      const error = errorBody.error || {};
      throw new ApiError(
        response.status,
        error.code || 'UNKNOWN',
        error.message || `HTTP ${response.status}`,
        error.details || null,
      );
    }

    const data = await response.json();
    return data;
  } catch (err) {
    clearTimeout(timeoutId);

    if (err instanceof ApiError) throw err;

    if (err.name === 'AbortError') {
      if (controller.signal.aborted) {
        throw new TimeoutError(timeout);
      }
      throw err;
    }

    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new NetworkError('Cannot connect to the backend server. Please check your connection.', err);
    }

    throw new NetworkError(`Network error: ${err.message}`, err);
  }
}

// ── API Methods ────────────────────────────────────────────────

/**
 * Get basic health status.
 * @returns {Promise<object>} { status, service, version, timestamp }
 */
export async function getHealth(options) {
  return apiFetch('/health', options);
}

/**
 * Get detailed readiness status.
 * @returns {Promise<object>} { status, service, version, components }
 */
export async function getReadiness(options) {
  return apiFetch('/readiness', options);
}

/**
 * Get a single-horizon PM2.5 forecast.
 * @param {number} horizon - Forecast horizon in hours (1, 3, 6, 12, 24)
 * @returns {Promise<object>} { forecast: PredictionResult }
 */
export async function getForecast(horizon, options) {
  return apiFetch(`/forecast?horizon=${horizon}`, options);
}

/**
 * Get forecasts for all supported horizons.
 * @returns {Promise<object>} { forecasts: { "1": {...}, "3": {...}, ... }, errors: [...], horizon_count }
 */
export async function getAllForecasts(options) {
  return apiFetch('/forecast/all', options);
}

/**
 * Get forecast service status.
 * @returns {Promise<object>} { ready, model_store, db_path, supported_horizons }
 */
export async function getForecastStatus(options) {
  return apiFetch('/forecast/status', options);
}

/**
 * Get recent prediction history.
 * @param {object} params - { horizon?: number, limit?: number }
 * @returns {Promise<object>} { predictions: [...], count, summary }
 */
export async function getPredictionHistory(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.horizon) qs.set('horizon', params.horizon);
  if (params.limit) qs.set('limit', params.limit);
  const query = qs.toString();
  return apiFetch(`/forecast/history${query ? '?' + query : ''}`, options);
}

/**
 * List registered data sources.
 * @returns {Promise<object>} { sources: [...], count }
 */
export async function getDataSources(options) {
  return apiFetch('/data-sources', options);
}

/**
 * Get observation statistics.
 * @returns {Promise<object>} { total_observations, by_source, by_parameter, by_quality }
 */
export async function getObservationStats(options) {
  return apiFetch('/observations/stats', options);
}

/**
 * List recent observations with optional filters.
 * @param {object} params - { parameter?, source_id?, limit?, offset? }
 * @returns {Promise<object>} { observations: [...], total, limit, offset }
 */
export async function getObservations(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.parameter) qs.set('parameter', params.parameter);
  if (params.source_id) qs.set('source_id', params.source_id);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset) qs.set('offset', params.offset);
  const query = qs.toString();
  return apiFetch(`/observations${query ? '?' + query : ''}`, options);
}

/**
 * Refresh current data from all available providers.
 * Fetches recent weather, air quality, and real-time station data.
 * @param {object} params - { latitude?, longitude?, forecast_days? }
 * @returns {Promise<object>} { status, providers, summary }
 */
export async function refreshCurrentData(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.latitude) qs.set('latitude', params.latitude);
  if (params.longitude) qs.set('longitude', params.longitude);
  if (params.forecast_days) qs.set('forecast_days', params.forecast_days);
  const query = qs.toString();
  return apiFetch(`/ingestion/refresh${query ? '?' + query : ''}`, {
    method: 'POST',
    ...options,
    timeout: options?.timeout || 60000,
  });
}

/**
 * Get current real weather observations from the database.
 * Data comes from Open-Meteo ingestion pipeline — no synthetic values.
 * @returns {Promise<object>} { weather: { temperature, humidity, wind_speed, ... } }
 */
export async function getCurrentWeather(options) {
  return apiFetch('/weather/current', options);
}

// ── Phase 8: Accuracy & Stations ──────────────────────────────

/**
 * Get aggregated accuracy statistics by forecast horizon.
 * Auto-backfills actuals from observations before computing.
 * @returns {Promise<object>} { total_predictions, by_horizon }
 */
export async function getAccuracySummary(options) {
  return apiFetch('/accuracy/summary', options);
}

/**
 * Get recent verified predictions (actual vs predicted).
 * @param {object} params - { horizon?: number, limit?: number }
 * @returns {Promise<object>} { count, predictions }
 */
export async function getRecentVerified(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.horizon) qs.set('horizon', params.horizon);
  if (params.limit) qs.set('limit', params.limit);
  const query = qs.toString();
  return apiFetch(`/accuracy/recent${query ? '?' + query : ''}`, options);
}

/**
 * List monitoring stations with latest PM2.5 readings.
 * @param {object} params - { source?: string }
 * @returns {Promise<object>} { stations, count }
 */
export async function getStations(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.source) qs.set('source', params.source);
  const query = qs.toString();
  return apiFetch(`/stations${query ? '?' + query : ''}`, options);
}

// ── Phase 10: Competitive Differentiation ─────────────────────

/**
 * Get prediction accountability timeline.
 * Returns past predictions with actuals (verified vs pending).
 * @param {object} params - { horizon?: number, limit?: number }
 * @returns {Promise<object>} { count, summary, timeline }
 */
export async function getAccountabilityTimeline(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.horizon) qs.set('horizon', params.horizon);
  if (params.limit) qs.set('limit', params.limit);
  const query = qs.toString();
  return apiFetch(`/accuracy/accountability${query ? '?' + query : ''}`, options);
}

/**
 * Trigger on-demand verification of pending predictions.
 * @returns {Promise<object>} { status, backfilled, message }
 */
export async function triggerVerification(options) {
  return apiFetch('/accuracy/verify', {
    method: 'POST',
    ...options,
    timeout: options?.timeout || 30000,
  });
}

/**
 * Get per-horizon model comparison with validation and live metrics.
 * @returns {Promise<object>} { count, horizons }
 */
export async function getHorizonComparison(options) {
  return apiFetch('/accuracy/horizon-comparison', options);
}

/**
 * Get recent PM2.5 observations from ground stations.
 * @param {object} params - { hours?: number }
 * @returns {Promise<object>} { count, hours, observations }
 */
export async function getStationHistory(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.hours) qs.set('hours', params.hours);
  const query = qs.toString();
  return apiFetch(`/stations/history${query ? '?' + query : ''}`, options);
}

// ── Episode Intelligence ───────────────────────────────────────

/**
 * Get episode intelligence: rule-based episode detection,
 * trajectory analysis, weather context, and narrative.
 *
 * This is NOT machine learning -- it is rule-based detection
 * using ML forecasts as one input signal.
 *
 * @returns {Promise<object>} Episode intelligence response
 */
export async function getEpisodeIntelligence(options) {
  return apiFetch('/episode', options);
}

// ── Historical Replay ──────────────────────────────────────────

/**
 * Get hourly observations for replay animation.
 * @param {object} params - { startDate, endDate, parameter? }
 * @returns {Promise<object>} { observations, meta }
 */
export async function getReplayObservations(params, options) {
  const qs = new URLSearchParams();
  qs.set('start_date', params.startDate);
  qs.set('end_date', params.endDate);
  if (params.parameter) qs.set('parameter', params.parameter);
  return apiFetch(`/replay/observations?${qs.toString()}`, options);
}

/**
 * List historical dates where episode detection would trigger.
 * @param {object} params - { minPeak?, limit? }
 * @returns {Promise<object>} { episodes, count }
 */
export async function listEpisodes(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.minPeak) qs.set('min_peak', params.minPeak);
  if (params.limit) qs.set('limit', params.limit);
  const query = qs.toString();
  return apiFetch(`/replay/episodes${query ? '?' + query : ''}`, options);
}

// ── Historical Analog Engine ──────────────────────────────────────

/**
 * Find historical episodes similar to current conditions.
 * @param {object} params - { limit? }
 * @returns {Promise<object>} { current_context, analogs, total_episodes_searched, caveat }
 */
export async function getEpisodeAnalogs(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.limit) qs.set('limit', params.limit);
  const query = qs.toString();
  return apiFetch(`/episode/analogs${query ? '?' + query : ''}`, options);
}

// ── Alerts ─────────────────────────────────────────────────────

/**
 * Get recent alert history.
 * @returns {Promise<Array>} List of alert objects
 */
export async function getAlertHistory(options) {
  return apiFetch('/alerts/history', options);
}

/**
 * Get alert preferences.
 * @returns {Promise<Array>} List of preference objects
 */
export async function getAlertPreferences(options) {
  return apiFetch('/alerts/preferences', options);
}

/**
 * Update alert preferences.
 * @param {Array} preferences - [{ alert_type, enabled }]
 * @returns {Promise<Array>} Updated preferences
 */
export async function updateAlertPreferences(preferences, options) {
  return apiFetch('/alerts/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preferences }),
    ...options,
  });
}

// ── Reports ────────────────────────────────────────────────────

/**
 * List generated reports.
 * @returns {Promise<Array>} List of report objects
 */
export async function getReportHistory(options) {
  return apiFetch('/reports', options);
}

/**
 * Generate a new report.
 * @param {string} reportType - daily | weekly | monthly | episode | snapshot
 * @returns {Promise<object>} Generated report object
 */
export async function generateReport(reportType, options) {
  return apiFetch('/reports/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_type: reportType }),
    ...options,
  });
}

/**
 * Get report details by ID.
 * @param {string} reportId
 * @returns {Promise<object>} Report object
 */
export async function getReport(reportId, options) {
  return apiFetch(`/reports/${reportId}`, options);
}

// ── Investigation AI Analysis ─────────────────────────────────

/**
 * Get AI investigation reasoning analysis.
 * Returns structured analysis: observed facts, model inferences,
 * hypotheses, priorities, uncertainties, and recommended actions.
 *
 * @param {object} params - { demo?: boolean }
 * @returns {Promise<object>} { evidence, analysis, analysis_metadata }
 */
export async function getInvestigationAnalysis(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.demo) qs.set('demo', 'true');
  const query = qs.toString();
  return apiFetch(`/investigation/analyze${query ? '?' + query : ''}`, {
    timeout: 45000,
    ...options,
  });
}

/**
 * Get deterministic exposure geometry for the current pollution event.
 *
 * Returns wind-driven geometry: upwind investigation corridor,
 * downwind exposure cone, vulnerable locations (schools/hospitals).
 * Purely deterministic — no AI involved.
 *
 * @param {object} params - { demo?: boolean }
 * @returns {Promise<object>} Exposure geometry response
 */
export async function getExposureGeometry(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.demo) qs.set('demo', 'true');
  const query = qs.toString();
  return apiFetch(`/investigation/exposure${query ? '?' + query : ''}`, {
    timeout: 15000,
    ...options,
  });
}

// ── Favorites (My Lahore) ────────────────────────────────────

/**
 * List saved locations with live AQ data.
 * @returns {Promise<object>} { locations, count }
 */
export async function getFavorites(options) {
  return apiFetch('/favorites', options);
}

/**
 * Add a new saved location.
 * @param {object} data - { station_id?, name, label?, latitude?, longitude?, icon? }
 * @returns {Promise<object>} Created location object
 */
export async function addFavorite(data, options) {
  return apiFetch('/favorites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Update a saved location.
 * @param {string} locationId
 * @param {object} data - { name?, label?, icon?, sort_order? }
 * @returns {Promise<object>} Updated location object
 */
export async function updateFavorite(locationId, data, options) {
  return apiFetch(`/favorites/${locationId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Delete a saved location.
 * @param {string} locationId
 * @returns {Promise<object>} Deletion confirmation
 */
export async function deleteFavorite(locationId, options) {
  return apiFetch(`/favorites/${locationId}`, {
    method: 'DELETE',
    ...options,
  });
}

// ── Investigation Verification (Phase 5 — Learning Loop) ─────

/**
 * Submit a verification outcome for an investigation.
 * @param {object} data - { investigation_id, overall_status, recommendation_verification, ... }
 * @returns {Promise<object>} Created verification outcome
 */
export async function submitVerification(data, options) {
  return apiFetch('/verification', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Update an existing verification outcome.
 * @param {string} outcomeId
 * @param {object} data - { overall_status?, field_notes?, ... }
 * @returns {Promise<object>} Updated verification outcome
 */
export async function updateVerification(outcomeId, data, options) {
  return apiFetch(`/verification/${outcomeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * Get verification context for an investigation.
 * @param {string} investigationId
 * @returns {Promise<object>} { current_outcome, stats, disclaimer }
 */
export async function getVerificationContext(investigationId, options) {
  return apiFetch(`/verification/context/${investigationId}`, options);
}

/**
 * Get aggregated verification statistics.
 * @returns {Promise<object>} VerificationStats
 */
export async function getVerificationStats(options) {
  return apiFetch('/verification/stats', options);
}

/**
 * List all verification outcomes.
 * @param {object} params - { status?, limit?, offset? }
 * @returns {Promise<object>} { outcomes, count, limit, offset }
 */
export async function listVerifications(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.offset) qs.set('offset', String(params.offset));
  const query = qs.toString();
  return apiFetch(`/verification${query ? '?' + query : ''}`, options);
}

/**
 * Delete a verification outcome.
 * @param {string} outcomeId
 * @returns {Promise<void>}
 */
export async function deleteVerification(outcomeId, options) {
  return apiFetch(`/verification/${outcomeId}`, {
    method: 'DELETE',
    ...options,
  });
}

// ── Investigation Learning (Phase 6 — Accountability) ───────

/**
 * Get investigation learning context from verified historical outcomes.
 *
 * Deterministic comparison against previously verified investigations.
 * Returns similarity scores, reliability classification, and limitations.
 * Requires minimum 3 verified cases before showing statistics.
 *
 * @param {object} params - { demo?: boolean }
 * @returns {Promise<object>} Investigation learning response
 */
export async function getInvestigationLearning(params = {}, options) {
  const qs = new URLSearchParams();
  if (params.demo) qs.set('demo', 'true');
  const query = qs.toString();
  return apiFetch(`/investigation/learning${query ? '?' + query : ''}`, {
    timeout: 15000,
    ...options,
  });
}
