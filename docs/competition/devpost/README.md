# Lahore Pulse AI — Devpost Submission

**Competition:** Smart City Hackathon Lahore  
**Theme:** City Intelligence  
**Problem Statement:** 2 — "Predicting Problems Before They Happen, Not After"  
**Track:** Theme 2 — City Intelligence  

---

## One-Liner

A predictive city-intelligence platform that forecasts PM2.5 air quality concentrations 1–24 hours ahead for Lahore using open environmental data and validated statistical models.

---

## The Problem

Lahore faces severe air quality challenges, particularly during winter smog seasons. Citizens and policymakers lack advance warning of upcoming PM2.5 spikes, making it impossible to take preventive action. Current approaches are reactive — people learn about bad air quality after it has already affected their health.

---

## Our Solution

Lahore Pulse AI provides **advance warning** for PM2.5 air quality events:

1. **Ingests real environmental data** from the Copernicus Atmosphere Monitoring Service (CAMS) — 1.31M+ historical observations
2. **Trains validated statistical models** across 5 time horizons (1h, 3h, 6h, 12h, 24h)
3. **Generates explainable predictions** with explicit confidence labels
4. **Provides actionable guidance** for citizens (health recommendations) and government (policy decisions)

---

## Key Features

- **Multi-Horizon Forecasting:** Five different time horizons, each with an optimized algorithm
- **Prediction Accountability:** Every forecast is verified against actual observations — Predict → Verify → Learn
- **Forecast Trust Transparency:** Four independent, verifiable trust signals (data freshness, model availability, accuracy, confidence)
- **Horizon Intelligence:** Different models for different horizons, with algorithm rationale explained
- **Explainable AI:** Every prediction shows the algorithm, metrics, and confidence level
- **Interactive Map:** Leaflet map with monitoring stations and PM2.5 readings
- **Historical Trends:** Time-series charts with WHO guideline reference lines
- **Accuracy Tracking:** Real-time verification of predictions against actual observations
- **Model Transparency:** Full visibility into how models work and their limitations

---

## How It Works

```
CAMS Data → Feature Engineering → Model Selection → Prediction → Explanation → User Interface
   │              │                    │                │              │              │
1.31M obs    41 features         5 algorithms     PM2.5 \u00b5g/m3   Actual    Improved
  2023-25     per prediction      per horizon      \u00b1 uncertainty  obs       accuracy
                                                         |           |
                                                    Confidence   Verified
                                                    labels       vs actual
                                                         |           |
                                                    Dashboard   Accountability
                                                    + Trust     timeline
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Database | SQLite (1.31M records) |
| ML Models | scikit-learn (Ridge, HistGradientBoosting) |
| Frontend | React 19, Vite, Leaflet, Recharts |
| Data Source | Copernicus Atmosphere Monitoring Service (CAMS) |
| Testing | pytest (590 tests), Vitest (106 tests) |

---

## Model Performance

| Horizon | Algorithm | MAE (µg/m³) | R² | Confidence |
|---------|-----------|-------------|-----|------------|
| 1h | Ridge Regression | 4.50 | 0.975 | High |
| 3h | HistGradientBoosting | 10.61 | 0.900 | High |
| 6h | HistGradientBoosting | 14.45 | 0.823 | Moderate |
| 12h | HistGradientBoosting | 16.34 | 0.765 | Moderate |
| 24h | Ridge Regression | 17.97 | 0.703 | Lower |

---

## What Makes Us Different

### 1. Prediction Accountability (Predict → Verify → Learn)

Every prediction is recorded with its target time. When the target time passes
and an observation becomes available, the system compares predicted vs actual.
**No consumer-facing AQ platform in the world does this transparently.**

- Past predictions are stored, verified against observations, and their
  accuracy is publicly reported
- Users can see exactly how well the system has performed — not just what
  it claims
- The system continuously improves through this feedback loop

### 2. Forecast Trust Transparency

Four independent trust signals are computed and displayed:
1. **Data freshness** — How recent is the input data? (FRESH/DEGRADED/STALE/UNAVAILABLE)
2. **Model availability** — Are the forecasting models loaded and ready?
3. **Historical accuracy** — How well did past predictions perform?
4. **Horizon confidence** — How reliable is this forecast horizon?

Each signal is independently verifiable — not a proprietary black-box score.

### 3. Horizon Intelligence

Different forecast horizons use different validated models because prediction
difficulty changes with time:
- **1h** uses Ridge Regression (nearly linear short-term dynamics)
- **3h/6h/12h** use HistGradientBoosting (non-linear weather interactions)
- **24h** reverts to Ridge (seasonal baseline, more robust to noise)

Algorithm selection was determined through systematic backtesting on held-out
Lahore data from 2023–2025.

### Additional Differentiators

- **Real data, no fabrication** — 1.31M observations from CAMS, never fake sensor readings
- **Honest uncertainty** — We label 24h predictions as "lower confidence" instead of hiding it
- **Explainability built-in** — Model Transparency shows algorithm, metrics, and feature importance
- **Competition-appropriate design** — Professional UI without AI-themed decoration or false promises

---

## What We Learned

- Ridge Regression outperforms complex models for short-term (1h) PM2.5 forecasting
- Feature engineering (lags, rolling stats, temporal encodings) matters more than model complexity
- Honest uncertainty communication builds more trust than false confidence
- Open environmental data (CAMS) is sufficient for city-scale air quality forecasting

---

## What's Next

1. **OpenAQ integration** — Add ground-level sensor data for validation
2. **Multi-city support** — Extend to other Pakistani cities (Faisalabad, Peshawar)
3. **Real-time feeds** — Integrate live IoT sensor networks when available
4. **Mobile app** — Citizen-facing notifications for air quality alerts
5. **Policy dashboard** — Enhanced government tools for intervention planning

---

## Running the Project

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && python -m pytest tests/ -v --no-header -q --no-file-parallelism
cd frontend && npx vitest run --pool=forks

# Health check
bash scripts/health-check.sh
```

---

## Team

- **Lahore Pulse AI Team** — Smart City Hackathon Lahore 2026

---

## License

Built for the Smart City Hackathon Lahore. Uses open data (CAMS) and open-source tools.
