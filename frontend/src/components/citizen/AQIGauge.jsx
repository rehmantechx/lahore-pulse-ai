/**
 * AQIGauge — Premium circular AQI gauge for citizen-facing pages.
 *
 * Large, prominent visual indicator of current air quality.
 * No technical jargon — uses human-friendly labels.
 * Inspired by IQAir/AirNow gauge patterns.
 *
 * Props:
 *   value: number (PM2.5 μg/m³, used internally only)
 *   size: 'hero' | 'large' | 'medium' (default: 'hero')
 *   loading: boolean
 */

const SIZE_MAP = {
  hero:   { svg: 240, stroke: 14, fontSize: 64, labelSize: 16, subSize: 14 },
  large:  { svg: 200, stroke: 14, fontSize: 56, labelSize: 15, subSize: 13 },
  medium: { svg: 120, stroke: 8,  fontSize: 36, labelSize: 12, subSize: 11 },
};

function getAirQualityInfo(value) {
  if (value == null || isNaN(value)) return { label: 'No Data', color: '#A09A93', level: 0, advice: 'Waiting for sensor data' };
  if (value <= 12)  return { label: 'Excellent', color: '#22C55E', level: 5,  advice: 'Air quality is perfect. Enjoy the outdoors!' };
  if (value <= 25)  return { label: 'Good',      color: '#84CC16', level: 4,  advice: 'Air is clean. Safe for all activities.' };
  if (value <= 35)  return { label: 'Fair',      color: '#EAB308', level: 3,  advice: 'Acceptable for most people. Sensitive groups take care.' };
  if (value <= 55)  return { label: 'Moderate',  color: '#F97316', level: 2.5, advice: 'Consider limiting prolonged outdoor activity.' };
  if (value <= 90)  return { label: 'Poor',      color: '#EF4444', level: 2,  advice: 'Avoid outdoor exercise. Keep windows closed.' };
  if (value <= 150) return { label: 'Very Poor', color: '#DC2626', level: 1.5, advice: 'Stay indoors. Use air purifier if available.' };
  return { label: 'Hazardous', color: '#7F1D1D', level: 1, advice: 'Emergency conditions. Stay inside. Wear N95 if you must go out.' };
}

function getTrafficColor(info) {
  // Map 7-level severity to a smooth arc color
  const colors = ['#22C55E', '#84CC16', '#EAB308', '#F97316', '#EF4444', '#DC2626', '#7F1D1D'];
  const idx = Math.min(Math.max(0, Math.round((5 - info.level) * 1.4)), colors.length - 1);
  return colors[idx];
}

export default function AQIGauge({ value, size = 'hero', loading = false, showAQILabel = false }) {
  const s = SIZE_MAP[size] || SIZE_MAP.hero;
  const info = getAirQualityInfo(value);
  const color = getTrafficColor(info);

  const r = (s.svg - s.stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const maxAQI = 500;
  const pct = value != null ? Math.min(value / maxAQI, 1) : 0;
  const offset = circumference * (1 - pct * 0.75); // 270° arc (3/4 circle)

  const centerLabel = showAQILabel ? 'AQI' : (loading ? 'Loading' : 'Air Quality Level');

  return (
    <div className={`aqi-gauge aqi-gauge--${size}`} style={{ width: s.svg, height: s.svg + (showAQILabel ? 0 : 32) }} role="img" aria-label={`Air quality: ${info.label}`}>
      <svg width={s.svg} height={s.svg} viewBox={`0 0 ${s.svg} ${s.svg}`}>
        {/* Background arc */}
        <circle
          cx={s.svg / 2}
          cy={s.svg / 2}
          r={r}
          fill="none"
          stroke="#E8E5E0"
          strokeWidth={s.stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          transform={`rotate(135, ${s.svg / 2}, ${s.svg / 2})`}
        />
        {/* Value arc */}
        {!loading && value != null && (
          <circle
            cx={s.svg / 2}
            cy={s.svg / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={s.stroke}
            strokeLinecap="round"
            strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
            strokeDashoffset={offset}
            transform={`rotate(135, ${s.svg / 2}, ${s.svg / 2})`}
            style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s ease' }}
          />
        )}
        {/* Center text */}
        <text
          x={s.svg / 2}
          y={s.svg / 2 - (s.fontSize > 40 ? 8 : 4)}
          textAnchor="middle"
          dominantBaseline="central"
          fill={loading ? '#A09A93' : color}
          fontSize={s.fontSize}
          fontWeight="800"
          fontFamily="'Inter', sans-serif"
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {loading ? '...' : (value != null ? Math.round(value) : '—')}
        </text>
        <text
          x={s.svg / 2}
          y={s.svg / 2 + s.fontSize / 2 - 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#A09A93"
          fontSize={s.subSize}
          fontWeight="500"
          fontFamily="'Inter', sans-serif"
        >
          {loading ? 'Loading' : centerLabel}
        </text>
      </svg>
      {/* Label below */}
      <div className="aqi-gauge__label" style={{ color: loading ? '#A09A93' : color, fontSize: s.labelSize }}>
        {loading ? 'Checking sensors...' : info.label}
      </div>
      {size === 'hero' && !loading && (
        <div className="aqi-gauge__advice">{info.advice}</div>
      )}
    </div>
  );
}
