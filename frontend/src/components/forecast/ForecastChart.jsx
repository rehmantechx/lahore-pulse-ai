/**
 * ForecastChart — Time-series visualization of current + forecast values.
 *
 * Uses Recharts. Clearly distinguishes OBSERVED from FORECAST.
 * No fake uncertainty bands.
 */

import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { HORIZONS, HORIZON_META } from '../../constants';
import { formatTime } from '../../utils/format';

/**
 * @param {object} props
 * @param {object} props.forecasts - { "1": {...}, "3": {...}, ... }
 * @param {object|null} props.currentObservation - Current PM2.5 observation if available
 */
export default function ForecastChart({ forecasts, currentObservation }) {
  const chartData = useMemo(() => {
    if (!forecasts) return [];

    // Build a unified timeline
    // Start point: current time with observed value (if available)
    const now = new Date();
    const data = [];

    // Current observation point
    if (currentObservation?.predicted_pm25 !== undefined) {
      data.push({
        time: 'Now',
        observed: currentObservation.predicted_pm25,
        forecast: null,
        horizon: 0,
        timestamp: now.toISOString(),
      });
    }

    // Forecast points
    HORIZONS.forEach(h => {
      const f = forecasts[String(h)];
      if (f?.predicted_pm25 !== null && f?.predicted_pm25 !== undefined) {
        const meta = HORIZON_META[h];
        data.push({
          time: `+${meta.shortLabel}`,
          observed: null,
          forecast: f.predicted_pm25,
          horizon: h,
          timestamp: f.timing?.target_time,
          algorithm: f.model?.algorithm,
        });
      }
    });

    return data;
  }, [forecasts, currentObservation]);

  if (chartData.length === 0) {
    return (
      <div style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--slate-400)', fontSize: 'var(--text-sm)' }}>
        No forecast data available for chart visualization.
      </div>
    );
  }

  const observedValue = chartData.find(d => d.observed !== null)?.observed;
  const values = chartData.map(d => d.observed ?? d.forecast).filter(v => v !== null);
  const yMin = Math.max(0, Math.min(...values) - 5);
  const yMax = Math.max(...values) + 5;

  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--slate-200)" />

          <XAxis
            dataKey="time"
            tick={{ fontSize: 12, fill: 'var(--slate-500)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--slate-200)' }}
          />

          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 12, fill: 'var(--slate-500)' }}
            tickLine={false}
            axisLine={false}
            label={{
              value: 'Air Quality',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: 'var(--slate-400)' },
              offset: -5,
            }}
          />

          <Tooltip
            contentStyle={{
              background: 'white',
              border: '1px solid var(--slate-200)',
              borderRadius: 4,
              fontSize: 13,
              padding: '8px 12px',
            }}
            formatter={(value, name) => [
              `${value.toFixed(1)} μg/m³`,
              name === 'observed' ? 'Observed' : 'Forecast',
            ]}
          />

          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
            formatter={(value) => value === 'observed' ? 'Observed (current)' : 'Forecast'}
          />

          {/* Observed line — solid */}
          <Line
            type="monotone"
            dataKey="observed"
            stroke="var(--slate-800)"
            strokeWidth={2}
            dot={{ r: 4, fill: 'var(--slate-800)' }}
            connectNulls={false}
            name="observed"
          />

          {/* Forecast line — dashed */}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="var(--blue-600)"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={{ r: 4, fill: 'var(--blue-600)', strokeWidth: 0 }}
            connectNulls={false}
            name="forecast"
          />

          {/* Reference line at current value */}
          {observedValue !== undefined && (
            <ReferenceLine
              y={observedValue}
              stroke="var(--slate-400)"
              strokeDasharray="2 4"
              label={{
                value: `${observedValue.toFixed(1)} (current)`,
                position: 'right',
                style: { fontSize: 11, fill: 'var(--slate-400)' },
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
