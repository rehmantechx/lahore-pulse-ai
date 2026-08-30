/**
 * ForecastTimeline — All 5 forecast horizons in a card grid.
 *
 * The user can see how the forecast evolves over time.
 * Each card shows the horizon, predicted value, severity, and reliability.
 */

import { HORIZONS } from '../../constants';
import ForecastCard from './ForecastCard';

/**
 * @param {object} props
 * @param {object} props.forecasts - { "1": {...}, "3": {...}, ... } from API
 * @param {number|null} props.selectedHorizon - Currently selected horizon
 * @param {Function} props.onSelectHorizon - Callback when a horizon is selected
 */
export default function ForecastTimeline({ forecasts, selectedHorizon, onSelectHorizon }) {
  return (
    <div className="forecast-cards" role="group" aria-label="Forecast horizons">
      {HORIZONS.map(h => (
        <ForecastCard
          key={h}
          horizon={h}
          forecast={forecasts?.[String(h)] || null}
          isSelected={selectedHorizon === h}
          onSelect={onSelectHorizon}
        />
      ))}
    </div>
  );
}
