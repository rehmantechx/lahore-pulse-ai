"""Modeling package — Historical dataset, feature engineering, and leakage prevention.

This package builds the data preparation layer for PM2.5 forecasting.
It does NOT train models or implement ML algorithms (that is Phase 3).

Architecture:
    config     — Dataset, feature, and target configuration
    targets    — Target variable construction (PM2.5 at t+h)
    features   — Feature engineering (lags, rolling, weather, time)
    alignment  — Temporal alignment to hourly UTC grid
    quality    — Data quality assessment and missing-data handling
    splits     — Chronological train/validation/test splitting
    leakage    — Automated data-leakage detection
    collector  — Real data collection from Open-Meteo APIs
    dataset    — End-to-end dataset generation orchestrator
    report     — Quality report generation (Markdown + JSON)

Key constraints:
    - Every data point is REAL — no synthetic, generated, or placeholder data
    - Feature engineering is strictly causal (uses only past observations)
    - All timestamps are UTC with hourly granularity
    - Dataset versioning is deterministic (same inputs → same outputs)
"""
