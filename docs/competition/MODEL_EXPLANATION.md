# Model Explanation — Lahore Pulse AI

## Overview

Lahore Pulse AI uses **supervised regression models** to predict PM2.5 air quality concentrations at five time horizons: 1 hour, 3 hours, 6 hours, 12 hours, and 24 hours ahead.

Each horizon uses the algorithm that performed best in walk-forward validation:

| Horizon | Algorithm | Why This Algorithm |
|---------|-----------|-------------------|
| 1h | Ridge Regression | Best short-term performance, fast training |
| 3h | HistGradientBoosting | Captures non-linear patterns at medium range |
| 6h | HistGradientBoosting | Best medium-term balance |
| 12h | HistGradientBoosting | Handles increasing uncertainty |
| 24h | Ridge Regression | More stable than complex models at long range |

---

## How It Works

### Step 1: Data Collection
- Hourly PM2.5 observations from CAMS (Copernicus Atmosphere Monitoring Service)
- 1.31M+ records spanning 2023–2025
- Each observation tagged with source, timestamp, and quality status

### Step 2: Feature Engineering
From raw PM2.5 and weather data, we create **41 features**:

**PM2.5 Lag Features (6):**
- PM2.5 at t-1h, t-2h, t-3h, t-6h, t-12h, t-24h

**Rolling Statistics (16):**
- Mean, std, min, max over 3h, 6h, 12h, 24h windows

**Weather Variables (7):**
- Temperature, humidity, wind speed, wind direction, pressure, precipitation, cloud cover

**Temporal Encodings (5):**
- Hour of day (sin/cos), day of week (sin/cos), month, is_weekend, is_night

**Derived Features (7):**
- Short-term change rate, long-term change rate, PM2.5 stability index

### Step 3: Model Training
- **Walk-forward validation:** Train on historical data, test on future data
- **No data leakage:** Never use future information to predict the past
- **Per-horizon optimization:** Each horizon gets its own best-performing algorithm

### Step 4: Prediction
- Input: Latest 41 features from current observations
- Output: PM2.5 concentration prediction (µg/m³) + confidence label
- Confidence labels: high (R² > 0.9), moderate (R² > 0.75), lower (R² < 0.75)

### Step 5: Verification
- Actual observations compared against predictions
- Accuracy tracking shows real-time verification
- Backfill mechanism matches historical predictions with actuals

---

## Algorithm Details

### Ridge Regression (1h, 24h)

**What it is:** A linear model with L2 regularization that prevents overfitting by penalizing large coefficients.

**Why it works well:**
- Short-term PM2.5 behavior is largely linear (today's value predicts tomorrow's)
- Regularization prevents overfitting to noise
- Fast training (0.3 seconds) and prediction
- Stable at long horizons where complex models overfit

**Limitations:**
- Cannot capture non-linear relationships
- Assumes linear correlation between features and target
- May underperform during sudden pollution events

### HistGradientBoosting (3h, 6h, 12h)

**What it is:** An ensemble of decision trees trained sequentially, where each tree corrects the errors of the previous ones. Uses histogram-based splitting for efficiency.

**Why it works well:**
- Captures non-linear relationships between weather and PM2.5
- Handles missing values gracefully
- Robust to outliers
- Good balance of bias and variance at medium horizons

**Limitations:**
- More complex than Ridge Regression
- Can overfit with insufficient data
- Less interpretable (though feature importance is available)
- Training takes 3–4 seconds vs 0.3 seconds for Ridge

---

## Performance Metrics

| Metric | What It Means | 1h | 3h | 6h | 12h | 24h |
|--------|--------------|-----|-----|-----|------|------|
| MAE | Average prediction error (µg/m³) | 4.50 | 10.61 | 14.45 | 16.34 | 17.97 |
| RMSE | Error with penalty for large errors | 7.40 | 14.77 | 19.67 | 22.71 | 25.54 |
| R² | Variance explained (0–1) | 0.975 | 0.900 | 0.823 | 0.765 | 0.703 |

**Interpretation:**
- **1h R² = 0.975:** The model explains 97.5% of PM2.5 variance — very strong
- **24h R² = 0.703:** The model explains 70.3% of variance — useful but less reliable
- **MAE = 4.50 (1h):** Average error is 4.5 µg/m³ — about 10% of typical PM2.5 range

---

## Feature Importance

The most important features across all horizons:

1. **PM2.5 t-1h** (lag 1 hour) — Most predictive feature for short-term
2. **PM2.5 t-3h** (lag 3 hours) — Strong for medium-term
3. **Rolling mean 6h** — Captures recent trend
4. **Temperature** — Weather drives PM2.5 dispersion
5. **Wind speed** — Affects pollution transport
6. **Hour of day** — Captures diurnal patterns
7. **Humidity** — Affects PM2.5 formation

---

## Why Not Deep Learning?

For this dataset and problem type:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Ridge Regression | Fast, interpretable, stable | Linear only | ✅ Best for 1h, 24h |
| HistGradientBoosting | Non-linear, robust, efficient | Less interpretable | ✅ Best for 3h, 6h, 12h |
| LSTM/GRU | Temporal patterns | Needs more data, overfits | ❌ Not enough data |
| Transformer | Long-range dependencies | Overkill, slow, black box | ❌ Not justified |

**Key insight:** 41 well-engineered features + simple models outperform complex deep learning on this dataset size.

---

## Limitations (Honest Assessment)

1. **Data latency:** CAMS data arrives 3–4 hours late, not real-time
2. **Single source:** Only CAMS; no ground-level sensor validation
3. **No baseline comparison:** No persistence/naive model in stored metrics
4. **Long-horizon degradation:** 24h predictions have meaningful uncertainty
5. **No extreme event modeling:** Sudden pollution spikes may be missed
6. **Station coverage:** Limited to CAMS grid resolution, not street-level
