# Lahore Pulse AI

**Predictive City-Intelligence Platform for Lahore**

---

## Problem

This project addresses **Problem Statement 2** of the **Smart City Hackathon Lahore**:

> *"Predicting Problems Before They Happen, Not After."*

Lahore Pulse AI provides advance warning for recurring urban environmental problems — starting with air quality, heat, and flood prediction — using open historical and recent environmental data.

## Vision

A serious, enterprise-grade city-intelligence platform that:

- Ingests real environmental data from verified open sources
- Applies explainable predictive models
- Produces actionable risk assessments with explicit uncertainty
- Traces every output back to its data provenance
- Builds government accountability through prediction receipts and verification

## Demo

Try the guided walkthrough:

```bash
# Start the backend
cd backend
python -m uvicorn app.main:app --port 8002

# Start the frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173/government?demo=true** — a 7-step deterministic walkthrough through a complete pollution investigation story, from detection to accountability. No backend calls are needed in demo mode.

### Demo Credentials

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Officer | `officer` | `officer123` | Government Command Center |
| Admin | `admin` | `admin123` | Full access |
| Citizen | `citizen` | `citizen123` | Public dashboard |

## Architecture

```
              Lahore Pulse AI
                     │
              ┌──────▼──────┐
              │   Frontend  │  React 19 + Vite
              │  (Port 5173)│  Government Command Center
              └──────┬──────┘  Citizen Dashboard
                     │         Episode Replay
              ┌──────▼──────┐
              │   Backend   │  FastAPI + Python
              │  (Port 8002)│  SQLite Database
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
  Data Ingestion  ML Forecast  Serving
  (Open-Meteo)    (Phase 4-5)  (Episodes)
```

### Key Components

| Layer | Technology | Responsibility |
|-------|-----------|---------------|
| **Frontend** | React 19, Vite 8, Recharts, Leaflet | Government UI, citizen dashboard, demo walkthrough |
| **API** | FastAPI, Pydantic | REST endpoints, auth (HMAC-SHA256), CORS |
| **Application** | Service layer | Ingestion orchestration, forecast serving, episode detection |
| **ML** | HistGradientBoosting, scikit-learn | PM2.5 forecasting with calibrated confidence |
| **Storage** | SQLite, SQLAlchemy | Observations, forecasts, episodes, predictions |

## Engineering Principles

- **Real data only** — Never fabricate sensor readings, predictions, or confidence values
- **Explainability** — Every prediction traces from input → model → output
- **Provenance** — Every observation is traceable to its source and retrieval time
- **Explicit uncertainty** — Insufficient data produces low confidence, not false certainty
- **Accountability** — Every prediction becomes a receipt that is verified against reality
- **Graceful failure** — One unavailable provider does not destroy unrelated functionality

## Development

### Prerequisites

- Python 3.13+
- Node.js 18+
- pip / npm

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd lahore-pulse-ai

# Backend setup (venv at project root)
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r backend/requirements.txt

# Frontend setup
cd frontend
npm install
```

### Running

```bash
# Backend (terminal 1) — from project root
cd backend
python -m uvicorn app.main:app --port 8002

# Frontend (terminal 2)
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8002
- API Docs: http://localhost:8002/docs
- Demo Mode: http://localhost:5173/government?demo=true

### Running Tests

```bash
# Backend (995 tests)
cd backend
python -m pytest tests/ -q

# Frontend (756 tests)
cd frontend
npx vitest run
```

## Project Structure

```
lahore-pulse-ai/
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP endpoints (auth, forecasts, episodes)
│   │   ├── application/      # Service layer (ingestion, serving)
│   │   ├── core/             # Configuration, logging, errors
│   │   ├── domain/           # Models, contracts, business rules
│   │   ├── infrastructure/   # Providers (Open-Meteo, OpenAQ)
│   │   ├── modeling/         # ML pipeline (features, training, serving)
│   │   └── middleware/       # Error handling, request logging
│   ├── data/
│   │   ├── models/           # Trained ML model artifacts (.joblib)
│   │   └── reports/          # Benchmark results, quality gates
│   ├── tests/                # Backend test suite (995 tests)
│   └── pyproject.toml        # Tool configuration
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Route pages (Command Center, Replay, Analytics)
│   │   ├── hooks/            # Data fetching hooks (useReplay, useForecast, etc.)
│   │   ├── demo/             # Demo mode fixtures and state machine
│   │   ├── contexts/         # Auth context, demo mode provider
│   │   ├── styles/           # CSS (Lahore+ design system)
│   │   └── test/             # Test setup and integration tests
│   ├── src/**/__tests__/     # Component unit tests
│   └── vite.config.js        # Vite + Vitest configuration
├── docs/                     # Architecture, decisions, research
├── scripts/                  # Health check scripts
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Demo Walkthrough

The guided demo (`?demo=true`) tells a complete pollution investigation story in 7 steps:

1. **Normal Conditions** — Baseline air quality monitoring
2. **Event Detected** — Anomaly triggers investigation
3. **Investigation Active** — AI generates constrained hypotheses
4. **Exposure Active** — Population exposure mapping
5. **Verification Complete** — Prediction accuracy verified against reality
6. **Prediction Receipt** — Formal accountability record issued
7. **Accountability Visible** — Full audit trail preserved

Each step progressively reveals government decision-making layers, from data ingestion to human accountability.

## License

 TBD

---

*Built for the Smart City Hackathon Lahore — Theme 2*
