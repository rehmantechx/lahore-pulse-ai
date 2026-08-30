# Project Description — Lahore Pulse AI

## Short Description (50 words)

Lahore Pulse AI is a predictive city-intelligence platform that forecasts PM2.5 air quality concentrations 1–24 hours ahead for Lahore using 1.31M real observations from the Copernicus Atmosphere Monitoring Service and validated statistical models with explainable predictions and honest uncertainty.

---

## Long Description (300 words)

### The Problem

Lahore faces severe air quality challenges, particularly during winter smog seasons when PM2.5 concentrations frequently exceed WHO guidelines by 5–10x. Citizens lack advance warning of upcoming pollution events, making it impossible to take preventive health measures. Policymakers lack data-driven tools for timely interventions. Current approaches are reactive — people learn about bad air quality after it has already affected their health.

### Our Solution

Lahore Pulse AI provides advance warning for PM2.5 air quality events through a predictive city-intelligence platform. The system:

1. **Ingests real environmental data** from the Copernicus Atmosphere Monitoring Service (CAMS), maintaining a database of 1.31 million hourly PM2.5 observations spanning 2023–2025 for Lahore.

2. **Engineers 41 predictive features** including PM2.5 lags (1h–24h), rolling statistics (mean, std, min, max over multiple windows), meteorological variables (temperature, humidity, wind, pressure), and temporal encodings (hour, day, season).

3. **Trains validated statistical models** across five time horizons: 1-hour (Ridge Regression, R²=0.975), 3-hour (HistGradientBoosting, R²=0.900), 6-hour (R²=0.823), 12-hour (R²=0.765), and 24-hour (Ridge Regression, R²=0.703). Each horizon uses the algorithm that performed best in walk-forward validation.

4. **Generates explainable predictions** with explicit confidence labels. The system shows exactly which algorithm produced each prediction, its validation metrics, and communicates that 24-hour predictions have greater uncertainty than 1-hour predictions.

5. **Provides actionable guidance** through three user-facing pages: a public Dashboard for general awareness, a Citizen page with health recommendations based on PM2.5 levels, and a Government page for policy decision support.

### What Makes Us Different

1. **Prediction Accountability (Predict → Verify → Learn):** Every forecast is recorded and later verified against actual observations. Past predictions are publicly visible with their accuracy — no consumer-facing AQ platform does this transparently.

2. **Forecast Trust Transparency:** Four independent, verifiable trust signals (data freshness, model availability, historical accuracy, horizon confidence) replace opaque confidence numbers. Users can verify each signal independently.

3. **Horizon Intelligence:** Different forecast horizons use different validated models — Ridge Regression for near-linear 1h/24h, HistGradientBoosting for non-linear 3h/6h/12h — determined through systematic backtesting on Lahore data.

4. **Real data only:** 1.31M real CAMS observations, never fabricated sensor readings, predictions, or confidence values

5. **Honest uncertainty:** 24-hour predictions labeled "lower confidence" — we don't hide limitations

### Technical Foundation

Built with FastAPI (Python 3.11), React 19, SQLite, scikit-learn, Leaflet maps, and Recharts visualizations. Full test suite with 590 backend tests and 106 frontend tests. 24+ API endpoints with 3 accountability/trust endpoints. Clean layered architecture documented in Architecture Decision Records.
