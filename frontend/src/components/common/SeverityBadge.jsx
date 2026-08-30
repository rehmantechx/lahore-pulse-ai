/**
 * SeverityBadge — Renders a PM2.5 severity level with color, icon, and label.
 *
 * Every severity state includes text, icon, and accessible label.
 * Colors match across map, cards, tables, and legends.
 */

import { getPM25Level } from '../../utils/format';

/**
 * @param {object} props
 * @param {number|null} props.value - PM2.5 value in μg/m³
 * @param {boolean} [props.showValue] - Also show the numeric value
 * @param {string} [props.size] - 'sm' for compact display
 */
export default function SeverityBadge({ value, showValue = false, size = 'default' }) {
  const safeValue = value != null && !isNaN(value) ? value : null;
  const level = getPM25Level(safeValue);

  return (
    <span
      className={`severity-badge ${size === 'sm' ? 'badge--sm' : ''}`}
      style={{
        backgroundColor: level.bg,
        color: level.textColor,
        border: `1px solid ${level.color}22`,
      }}
      role="status"
      aria-label={`Air quality: ${level.label}${safeValue != null ? `, PM2.5 ${safeValue.toFixed(1)} micrograms per cubic meter` : ''}`}
    >
      <span className="severity-badge__icon" aria-hidden="true">{level.icon}</span>
      {showValue && safeValue != null && (
        <span style={{ fontWeight: 600, marginRight: 4 }}>{safeValue.toFixed(1)}</span>
      )}
      <span>{level.label}</span>
    </span>
  );
}
