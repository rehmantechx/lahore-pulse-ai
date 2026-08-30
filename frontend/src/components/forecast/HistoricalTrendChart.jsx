/**
 * HistoricalTrendChart — Shows PM2.5 historical observations over time.
 *
 * Displays recent ground-level observations as a time series,
 * helping users see trends and patterns beyond just the forecast window.
 *
 * Uses Recharts LineChart with observed data points.
 * Clearly labeled as historical observations, not predictions.
 */

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { getStationHistory } from '../../services/api';
import { PM25_LEVELS } from '../../constants';
import { formatTime } from '../../utils/format';
import { useDemoData } from '../../demo';

function getSeverityColor(pm25) {
  if (pm25 === null || pm25 === undefined) return '#94a3b8';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.color;
  }
  return '#7f1d1d';
}

export default function HistoricalTrendChart() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(48);

  useEffect(() => {
    if (isDemo) {
      // Generate deterministic demo observations for the past N hours
      const now = new Date();
      const demoPoints = [];
      for (let i = hours; i >= 0; i--) {
        const t = new Date(now.getTime() - i * 3600000);
        const hour = t.getHours();
        // Simulate Lahore diurnal pattern: higher during day (8-20), lower at night
        const base = hour >= 8 && hour <= 20 ? 95 : 55;
        const noise = Math.sin(i * 0.7) * 20 + Math.cos(i * 1.3) * 12;
        const pm25 = Math.max(10, Math.round((base + noise) * 10) / 10);
        demoPoints.push({
          time: t.toISOString().substring(0, 13) + ':00',
          pm25,
        });
      }
      setData(demoPoints);
      setLoading(false);
      return;
    }
    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const result = await getStationHistory({ hours }, { timeout: 35000 });
        if (!cancelled) {
          // Group observations by hour and average them
          const grouped = {};
          for (const obs of (result.observations || [])) {
            const hour = obs.observed_at?.substring(0, 13); // YYYY-MM-DDTHH
            if (!hour) continue;
            if (!grouped[hour]) grouped[hour] = { sum: 0, count: 0 };
            grouped[hour].sum += obs.value;
            grouped[hour].count += 1;
          }

          const chartData = Object.entries(grouped)
            .map(([hour, { sum, count }]) => ({
              time: hour + ':00',
              pm25: Math.round((sum / count) * 10) / 10,
            }))
            .sort((a, b) => a.time.localeCompare(b.time));

          setData(chartData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [hours, isDemo]);

  return (
    <div className="surface" style={{ marginBottom: 'var(--sp-4)' }}>
      <div className="surface__header">
        <span className="surface__title">Historical Observations</span>
        <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
          {[24, 48, 72].map(h => (
            <button
              key={h}
              className={`btn btn--sm ${hours === h ? 'btn--primary' : ''}`}
              onClick={() => setHours(h)}
              style={{ fontSize: 'var(--text-xs)', padding: '2px 8px' }}
            >
              {h}h
            </button>
          ))}
        </div>
      </div>
      <div className="surface__body">
        {loading && (
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
            Loading historical data...
          </div>
        )}

        {error && (
          <div className="info-box info-box--warn">
            Unable to load historical data: {error}
          </div>
        )}

        {!loading && !error && data.length === 0 && (
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-500)', padding: 'var(--sp-3)' }}>
            No historical observations available for the selected time window.
          </div>
        )}

        {!loading && !error && data.length > 0 && (
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)', marginBottom: 'var(--sp-2)' }}>
            PM2.5 observations from ground stations over the past {hours} hours
          </div>
        )}

        {!loading && !error && data.length > 0 && (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(val) => {
                  const d = new Date(val);
                  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}h`;
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                label={{ value: 'Level', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#94a3b8' } }}
              />
              <Tooltip
                labelFormatter={(val) => new Date(val).toLocaleString()}
                formatter={(val) => [`${Math.round(val)}`, 'Air Quality']}
                contentStyle={{
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)',
                  border: '1px solid #e2e8f0',
                  borderRadius: 4,
                }}
              />
              {/* WHO guideline reference line */}
              <ReferenceLine y={25} stroke="#ca8a04" strokeDasharray="6 3" label={{ value: 'WHO 24h', position: 'right', style: { fontSize: 10, fill: '#ca8a04' } }} />
              <Line
                type="monotone"
                dataKey="pm25"
                stroke="#64748b"
                strokeWidth={1.5}
                dot={{ r: 2, fill: '#64748b' }}
                activeDot={{ r: 4, stroke: '#334155', strokeWidth: 2 }}
                name="PM2.5"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
