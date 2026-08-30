# Demo Workflow — Lahore Pulse AI

**Purpose:** Step-by-step guide for live demo at Smart City Hackathon Lahore  
**Estimated Duration:** 8–10 minutes  

---

## Pre-Demo Checklist

- [ ] Backend running on `http://localhost:8000`
- [ ] Frontend running on `http://localhost:5173`
- [ ] Database populated (1.31M+ observations)
- [ ] Models loaded (5 horizons)
- [ ] Run `scripts/health-check.sh` to verify
- [ ] Browser open with Dashboard page

---

## Demo Script

### 1. Opening (1 minute)

**Narration:** "Lahore Pulse AI is a predictive city-intelligence platform that forecasts PM2.5 air quality concentrations 1 to 24 hours ahead for Lahore, Pakistan. It uses open environmental data and validated statistical models to provide advance warning for air quality events."

**Action:** Show the Dashboard page. Point to the hero section showing current PM2.5 status.

### 2. Data Pipeline (2 minutes)

**Narration:** "The system ingests real environmental data from the Copernicus Atmosphere Monitoring Service. We have over 1.3 million observation records spanning 2023 to 2025. The data pipeline runs automatically, refreshing every 30 minutes."

**Action:** 
- Scroll down to show the Data Collection section
- Point to the data source indicator
- Mention the auto-refresh mechanism

### 3. Multi-Horizon Forecasting (3 minutes)

**Narration:** "We forecast PM2.5 at five time horizons: 1 hour, 3 hours, 6 hours, 12 hours, and 24 hours ahead. Each horizon uses a different algorithm optimized for that timeframe. The 1-hour model uses Ridge Regression with an R-squared of 0.975, while longer horizons use Histogram Gradient Boosting."

**Action:**
- Show the forecast cards for each horizon
- Click "Show technical details" to reveal algorithm names and metrics
- Point to the confidence labels (high, moderate, lower)
- Show the accuracy tracker section

### 4. Explainability (2 minutes)

**Narration:** "Every prediction is explainable. The Model Transparency section shows exactly which algorithm was used, its validation metrics, and how confidence varies by horizon. We show that 24-hour predictions have greater uncertainty — we don't hide this."

**Action:**
- Expand the Model Transparency section
- Point to the algorithm names, MAE, R² values
- Show the confidence explanation

### 5. Interactive Map (1 minute)

**Narration:** "The map shows monitoring stations across Lahore with their latest PM2.5 readings. Citizens can see air quality in their area."

**Action:**
- Show the Leaflet map with station markers
- Hover over a station to show its PM2.5 value
- Show the WHO guideline reference line on the historical chart

### 6. Closing (30 seconds)

**Narration:** "Lahore Pulse AI demonstrates that honest, explainable predictive city intelligence is achievable with open data and proven statistical methods. We show real uncertainty, not false confidence. Thank you."

---

## Key Talking Points

1. **Real data** — 1.31M observations, never fabricated
2. **Honest uncertainty** — "lower" confidence for 24h predictions
3. **Multi-horizon** — Different algorithms for different timeframes
4. **Explainable** — Every prediction traceable to model + features
5. **Open source** — Built on open data (CAMS) and open tools

---

## Q&A Preparation

**Q: Is this real-time data?**  
A: "The data comes from CAMS reanalysis, which has a 3–4 hour latency. We use 'recent data' rather than claiming real-time. The system refreshes every 30 minutes."

**Q: How accurate are the predictions?**  
A: "The 1-hour model has an R-squared of 0.975, meaning it explains 97.5% of variance. Accuracy decreases for longer horizons — the 24-hour model has R-squared of 0.703. We're transparent about this."

**Q: Why not use deep learning?**  
A: "For this dataset size and problem type, Ridge Regression and Gradient Boosting outperform deep learning. We chose algorithms based on evidence, not hype."

**Q: What about other cities?**  
A: "The architecture is designed to be extensible. Adding another city requires a new data source and retraining. The current scope is Lahore."

**Q: How does this help citizens?**  
A: "The Citizen page provides health guidance based on PM2.5 levels — when to limit outdoor activity, when sensitive groups should take precautions. The Government page supports policy decisions."
