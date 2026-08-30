/**
 * Lahore Pulse AI — useReplay hook.
 *
 * Manages historical episode replay state: episode list selection,
 * observation data fetching, playback animation, and episode
 * state detection at each time step.
 *
 * All data is real — no fabrication. Episode detection uses the
 * same thresholds as the backend (app/modeling/serving/episode.py).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getReplayObservations, listEpisodes } from '../services/api';
import { useDemoData } from '../demo';

// ── Episode Detection Thresholds (from backend/episode.py) ────

const EPISODE_PM25_THRESHOLD = 120.0;
const EPISODE_DELTA_THRESHOLD = 30.0;
const EPISODE_SEVERE_THRESHOLD = 150.0;
const IMPROVING_THRESHOLD = 100.0;

// ── Playback defaults ─────────────────────────────────────────

const DEFAULT_PLAYBACK_SPEED_MS = 500; // 0.5s per hour step

/**
 * Detect episode state from a series of (hour, pm25) readings.
 * Mirrors backend detect_episode_state() logic.
 *
 * @param {Array} readings - Array of { hour, avg_value } sorted by time
 * @param {number} currentIndex - Current position in the series
 * @returns {{ state: string, label: string }}
 */
function detectEpisodeState(readings, currentIndex) {
  if (currentIndex < 0) return { state: 'normal', label: 'Normal' };

  const current = readings[currentIndex];
  const currentPM25 = current.avg_value;

  // Look back up to 6 hours for delta calculation
  const lookback = Math.max(0, currentIndex - 6);
  const older = readings[lookback];
  const delta = older ? currentPM25 - older.avg_value : 0;

  // Sustained severe: last 3 readings all above severe threshold
  const recentStart = Math.max(0, currentIndex - 2);
  const recentReadings = readings.slice(recentStart, currentIndex + 1);
  const severeCount = recentReadings.filter(r => r.avg_value > EPISODE_SEVERE_THRESHOLD).length;
  const isSustainedSevere = currentPM25 > EPISODE_SEVERE_THRESHOLD && severeCount >= 3;

  // Rapid rise: above threshold AND significant delta
  const isRapidRise =
    currentPM25 > EPISODE_PM25_THRESHOLD && delta >= EPISODE_DELTA_THRESHOLD;

  if (isSustainedSevere) {
    return { state: 'episode', label: 'SEVERE EPISODE' };
  }
  if (isRapidRise) {
    return { state: 'episode', label: 'EPISODE DETECTED' };
  }

  // Check if improving
  if (currentPM25 < IMPROVING_THRESHOLD) {
    const wasInEpisode = readings
      .slice(Math.max(0, currentIndex - 12), currentIndex)
      .some(r => r.avg_value > EPISODE_PM25_THRESHOLD);
    if (wasInEpisode) {
      return { state: 'improving', label: 'IMPROVING' };
    }
  }

  // Above episode threshold but not rapid rise or sustained
  if (currentPM25 > EPISODE_PM25_THRESHOLD) {
    return { state: 'elevated', label: 'ELEVATED' };
  }

  return { state: 'normal', label: 'Normal' };
}

/**
 * Get the AQI color level for a PM2.5 value.
 */
function getPM25Level(pm25) {
  if (pm25 <= 12) return { label: 'Good', color: '#16a34a' };
  if (pm25 <= 25) return { label: 'Fair', color: '#65a30d' };
  if (pm25 <= 45) return { label: 'Moderate', color: '#ca8a04' };
  if (pm25 <= 65) return { label: 'Unhealthy for Sensitive Groups', color: '#ea580c' };
  if (pm25 <= 90) return { label: 'Unhealthy', color: '#dc2626' };
  if (pm25 <= 150) return { label: 'Very Unhealthy', color: '#b91c1c' };
  return { label: 'Hazardous', color: '#7f1d1d' };
}

// ── Demo fixtures (when ?demo=true, no backend calls needed) ────

const DEMO_EPISODES = [
  { id: 'demo-ep-1', date: '2024-11-13', station: 'All', state: 'episode', pm25_max: 178.4, peak_pm25: 178.4, avg_pm25: 108.2, readings_count: 24 },
  { id: 'demo-ep-2', date: '2024-11-14', station: 'All', state: 'episode', pm25_max: 162.1, peak_pm25: 162.1, avg_pm25: 95.7, readings_count: 24 },
  { id: 'demo-ep-3', date: '2024-11-15', station: 'All', state: 'episode', pm25_max: 155.8, peak_pm25: 155.8, avg_pm25: 91.3, readings_count: 24 },
  { id: 'demo-ep-4', date: '2024-11-20', station: 'All', state: 'episode', pm25_max: 191.2, peak_pm25: 191.2, avg_pm25: 118.5, readings_count: 24 },
  { id: 'demo-ep-5', date: '2024-12-01', station: 'All', state: 'episode', pm25_max: 148.5, peak_pm25: 148.5, avg_pm25: 88.6, readings_count: 24 },
  { id: 'demo-ep-6', date: '2024-12-10', station: 'All', state: 'episode', pm25_max: 167.3, peak_pm25: 167.3, avg_pm25: 102.1, readings_count: 24 },
];

/**
 * Generate deterministic demo observations for a given episode date.
 * Produces a 24-hour PM2.5 series with a realistic episode arc.
 * Returns { date, hour, avg_value } format matching backend schema.
 */
function generateDemoObservations(episodeDate) {
  const readings = [];
  // Seed a simple arc: normal → rise → peak → decline
  const arc = [
    45, 52, 58, 63, 72, 85, 98, 112, 125, 138,
    152, 165, 178, 181, 172, 158, 142, 128, 115, 102,
    88, 75, 62, 50,
  ];
  for (let h = 0; h < 24; h++) {
    readings.push({
      date: episodeDate,
      hour: h,
      avg_value: arc[h],
    });
  }
  return readings;
}

/**
 * Hook for historical episode replay.
 */
export function useReplay() {
  // ── Demo mode: return fixtures, skip all API calls ──
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // ── URL params (for deep-linking from analog replay) ──
  const [searchParams] = useSearchParams();
  const dateParam = searchParams.get('date'); // e.g. "2024-11-13"

  // ── Episode list ──
  const [episodes, setEpisodes] = useState(isDemo ? DEMO_EPISODES : []);
  const [loadingEpisodes, setLoadingEpisodes] = useState(!isDemo);
  const [episodeError, setEpisodeError] = useState(null);

  // ── Selected episode ──
  const [selectedEpisode, setSelectedEpisode] = useState(null);

  // ── Observation data ──
  const [observations, setObservations] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loadingObs, setLoadingObs] = useState(false);
  const [obsError, setObsError] = useState(null);

  // ── Playback state ──
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(DEFAULT_PLAYBACK_SPEED_MS);
  const timerRef = useRef(null);
  const mountedRef = useRef(true);

  // ── Fetch episode list on mount (skipped in demo mode) ──
  useEffect(() => {
    if (isDemo) return; // Demo mode: episodes already set from fixtures
    mountedRef.current = true;
    (async () => {
      try {
        setLoadingEpisodes(true);
        const result = await listEpisodes({ limit: 20 }, { timeout: 15000 });
        if (!mountedRef.current) return;
        setEpisodes(result.episodes || []);
        setEpisodeError(null);
      } catch (err) {
        if (!mountedRef.current) return;
        setEpisodeError(err);
      } finally {
        if (mountedRef.current) setLoadingEpisodes(false);
      }
    })();
    return () => { mountedRef.current = false; };
  }, []);

  // ── Fetch observations when episode is selected ──
  const selectEpisode = useCallback(async (episode) => {
    setSelectedEpisode(episode);
    setCurrentIndex(0);
    setIsPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);

    // Demo mode: generate deterministic observations, no API call
    if (isDemo) {
      setObservations(generateDemoObservations(episode.date));
      setMeta({ station: 'All', startDate: episode.date, endDate: episode.date });
      setLoadingObs(false);
      setObsError(null);
      return;
    }

    try {
      setLoadingObs(true);
      setObsError(null);
      // Fetch 3 days: day before, the day, and day after (for context)
      const startDate = new Date(episode.date + 'T00:00:00Z');
      const endDate = new Date(startDate);
      endDate.setUTCDate(endDate.getUTCDate() + 2);

      const startStr = startDate.toISOString().split('T')[0];
      const endStr = endDate.toISOString().split('T')[0];

      const result = await getReplayObservations({
        startDate: startStr,
        endDate: endStr,
      }, { timeout: 20000 });

      if (!mountedRef.current) return;
      setObservations(result.observations || []);
      setMeta(result.meta || null);
      setObsError(null);
    } catch (err) {
      if (!mountedRef.current) return;
      setObsError(err);
    } finally {
      if (mountedRef.current) setLoadingObs(false);
    }
  }, []);

  // ── Auto-select episode from ?date= URL param (for analog replay links) ──
  useEffect(() => {
    if (!dateParam || episodes.length === 0 || selectedEpisode) return;
    const match = episodes.find(ep => ep.date === dateParam);
    if (match) {
      selectEpisode(match);
    }
  }, [dateParam, episodes, selectedEpisode, selectEpisode]);

  // ── Playback controls ──
  const play = useCallback(() => {
    if (observations.length === 0) return;
    setIsPlaying(true);
  }, [observations.length]);

  const pause = useCallback(() => {
    setIsPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const reset = useCallback(() => {
    setIsPlaying(false);
    setCurrentIndex(0);
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const goToIndex = useCallback((index) => {
    setCurrentIndex(Math.max(0, Math.min(index, observations.length - 1)));
  }, [observations.length]);

  const stepForward = useCallback(() => {
    setCurrentIndex(prev => Math.min(prev + 1, observations.length - 1));
  }, [observations.length]);

  const stepBackward = useCallback(() => {
    setCurrentIndex(prev => Math.max(prev - 1, 0));
  }, []);

  // ── Playback timer ──
  useEffect(() => {
    if (!isPlaying) return;

    timerRef.current = setInterval(() => {
      setCurrentIndex(prev => {
        if (prev >= observations.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, playbackSpeed);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, playbackSpeed, observations.length]);

  // ── Derived state ──
  const currentReading = observations[currentIndex] || null;
  const episodeState = currentReading
    ? detectEpisodeState(observations, currentIndex)
    : null;
  const pm25Level = currentReading
    ? getPM25Level(currentReading.avg_value)
    : null;
  const progress = observations.length > 0
    ? (currentIndex / (observations.length - 1)) * 100
    : 0;

  return {
    // Episode list
    episodes,
    loadingEpisodes,
    episodeError,
    selectEpisode,
    selectedEpisode,

    // Observations
    observations,
    meta,
    loadingObs,
    obsError,

    // Playback
    currentIndex,
    currentReading,
    isPlaying,
    playbackSpeed,
    setPlaybackSpeed,
    progress,
    play,
    pause,
    reset,
    goToIndex,
    stepForward,
    stepBackward,

    // Derived
    episodeState,
    pm25Level,

    // Utilities (exported for components)
    detectEpisodeState,
    getPM25Level,
  };
}
