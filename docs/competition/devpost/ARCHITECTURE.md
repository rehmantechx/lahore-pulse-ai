# Architecture — Lahore Pulse AI

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Lahore Pulse AI                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Dashboard   │    │   Citizen    │    │  Government  │      │
│  │   (React)     │    │   (React)    │    │  (React)     │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                    │                    │               │
│         └────────────────────┼────────────────────┘               │
│                              │                                    │
│                    ┌─────────▼─────────┐                         │
│                    │    FastAPI         │                         │
│                    │    REST API        │                         │
│                    │    (21 endpoints)  │                         │
│                    └─────────┬─────────┘                         │
│                              │                                    │
│         ┌────────────────────┼────────────────────┐               │
│         │                    │                    │               │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐      │
│  │  Observations │    │  Predictions │    │   Accuracy   │      │
│  │  Service      │    │  Service     │    │   Tracker    │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                    │                    │               │
│         └────────────────────┼────────────────────┘               │
│                              │                                    │
│                    ┌─────────▼─────────┐                         │
│                    │    SQLite          │                         │
│                    │    Database        │                         │
│                    │    (1.31M records) │                         │
│                    └─────────┬─────────┘                         │
│                              │                                    │
│                    ┌─────────▼─────────┐                         │
│                    │    CAMS            │                         │
│                    │    Data Source      │                         │
│                    │    (CAMS NRT)      │                         │
│                    └───────────────────┘                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Layered Architecture

```
┌─────────────────────────────────────────┐
│              API Layer                   │
│  FastAPI endpoints, request validation  │
├─────────────────────────────────────────┤
│          Application Layer              │
│  Use-case orchestration, services       │
├─────────────────────────────────────────┤
│            Domain Layer                 │
│  Models, contracts, business rules      │
├─────────────────────────────────────────┤
│         Infrastructure Layer            │
│  Database, external APIs, providers     │
└─────────────────────────────────────────┘
```

## Data Flow

```
CAMS API → Data Provider → Observation Store → Feature Engineering → Model Registry
                                                                      │
                                                                      ▼
User Interface ← API Layer ← Prediction Service ← ML Models (5 horizons)
```

## Model Architecture

```
                    Input Features (41)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
     │ PM2.5 Lags  │ │ Weather │ │  Temporal   │
     │ 1h-24h      │ │ T,H,W,P │ │  H,D,M      │
     └──────┬──────┘ └────┬────┘ └──────┬──────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼──────┐
                    │  Feature    │
                    │  Vector     │
                    │  (41-dim)   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │  1h     │      │  3h     │      │  6h     │
    │  Ridge  │      │  HGB    │      │  HGB    │
    │  R²=.975│      │  R²=.900│      │  R²=.823│
    └────┬────┘      └────┬────┘      └────┬────┘
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐
    │  12h    │      │  24h    │
    │  HGB    │      │  Ridge  │
    │  R²=.765│      │  R²=.703│
    └────┬────┘      └────┬────┘
         │                 │
         └────────┬────────┘
                  │
           ┌──────▼──────┐
           │  Predictions │
           │  + Confidence│
           │  Labels      │
           └─────────────┘
```

## Database Schema (Key Tables)

```sql
-- Observations (1.31M records)
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    station_id TEXT,
    observation_type TEXT CHECK(observation_type IN ('pm25', ...)),
    value REAL,
    unit TEXT,
    timestamp DATETIME,
    source TEXT,
    created_at DATETIME
);

-- Predictions
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    horizon INTEGER,
    predicted_value REAL,
    confidence REAL,
    model_version TEXT,
    created_at DATETIME
);

-- Stations
CREATE TABLE stations (
    station_id TEXT PRIMARY KEY,
    name TEXT,
    latitude REAL,
    longitude REAL,
    active BOOLEAN
);

-- Model Registry
CREATE TABLE model_registry (
    model_version TEXT PRIMARY KEY,
    horizon INTEGER,
    algorithm TEXT,
    status TEXT,
    metrics JSON
);
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite for demo | Simple, no setup, 672MB handles 1.31M records |
| Ridge for 1h/24h | Outperforms complex models on these horizons |
| HGB for 3h/6h/12h | Best medium-term performance |
| Walk-forward validation | Prevents temporal data leakage |
| 41 features | Captures temporal patterns without overfitting |
| Confidence labels | Honest uncertainty communication |
| Auto-refresh 30min | Balances freshness with API load |
| No authentication | Demo simplicity; production would add JWT |
