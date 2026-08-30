/**
 * GovForecastsPage — Government forecast analysis.
 *
 * Placeholder for Phase 2.
 */

import { useState } from 'react';
import { useForecast } from '../hooks/useForecast';
import ForecastTrajectory from '../components/forecast/ForecastTrajectory';
import ForecastChart from '../components/forecast/ForecastChart';

export default function GovForecastsPage() {
  const { forecasts, loading } = useForecast();
  const [selectedHorizon, setSelectedHorizon] = useState(1);
  const currentForecast = forecasts?.['1'];

  return (
    <div className="page page--wide">
      <h1 className="page__title">Forecasts</h1>
      <p className="page__subtitle">Multi-horizon air quality prediction analysis</p>

      <div className="surface" style={{ marginTop: 'var(--sp-4)', padding: 'var(--sp-4) var(--sp-5)' }}>
        <ForecastTrajectory
          forecasts={forecasts}
          selectedHorizon={selectedHorizon}
          onSelectHorizon={setSelectedHorizon}
        />
      </div>

      <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="surface__header">
          <span className="surface__title">Forecast Chart</span>
          <span className="text-xs text-muted">Solid = Observed · Dashed = Model Prediction</span>
        </div>
        <div className="surface__body">
          <ForecastChart forecasts={forecasts} currentObservation={currentForecast} />
        </div>
      </div>
    </div>
  );
}
