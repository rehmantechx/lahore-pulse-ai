# Lahore Pulse AI — Backend

## Overview

FastAPI backend providing the API layer for the Lahore Pulse AI air quality intelligence platform. Features ML-powered PM2.5 forecasting, episode intelligence, investigation evidence assembly, and prediction accountability.

## Quick Start

```bash
# Install dependencies (Python 3.13+)
pip install -r requirements.txt

# Run the server (port 8002)
uvicorn app.main:app --port 8002

# Run tests (995 tests)
pytest tests/ -q
```

## API Endpoints (16 route groups, 70+ endpoints)

| Route Group | Prefix | Description |
|-------------|--------|-------------|
| Auth | `/api/v1/auth` | HMAC-SHA256 login, token management |
| Health | `/api/v1/health` | Health check and readiness |
| DataSources | `/api/v1/data-sources` | External data source status |
| Ingestion | `/api/v1/ingestion` | Data refresh and status |
| Observations | `/api/v1/observations` | Air quality observations (1.35M rows) |
| Stations | `/api/v1/stations` | Monitoring stations |
| Forecast | `/api/v1/forecast` | ML predictions (1h/3h/6h/12h/24h horizons) |
| Accuracy | `/api/v1/accuracy` | Model performance tracking |
| Episode | `/api/v1/episode` | Pollution event detection |
| Alerts | `/api/v1/alerts` | Alert history and preferences |
| Reports | `/api/v1/reports` | Report generation and history |
| Favorites | `/api/v1/favorites` | My Lahore favorites |
| Replay | `/api/v1/replay` | Historical event replay |
| Investigation | `/api/v1/investigation` | Evidence assembly and AI reasoning |
| Verification | `/api/v1/verification` | Prediction verification learning loop |

Full interactive API docs at `http://localhost:8002/docs`.

## Architecture (Hexagonal)

```
API Layer (app/api/v1/) — FastAPI routers
    ↓
Application Layer (app/application/services/) — Business logic
    ↓
Domain Layer (app/domain/) — Models and contracts
    ↓
Infrastructure Layer (app/infrastructure/) — Database, providers
    ↓
Modeling Layer (app/modeling/) — ML pipeline, features, serving
```

## ML Models

5 trained models covering PM2.5 forecasting at different horizons:

| Horizon | Algorithm | Validation R² |
|---------|-----------|---------------|
| 1h | Ridge | 0.975 |
| 3h | HistGradientBoosting | 0.900 |
| 6h | HistGradientBoosting | 0.823 |
| 12h | HistGradientBoosting | 0.765 |
| 24h | Ridge | 0.703 |

Models use 41 engineered features and are stored as `.joblib` files in `data/models/`.

## Database

SQLite at `data/lahore_pulse.db` (~941 MB, 1.35M observations, 2017–2026). Populated via `collect_real_data.py`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LPA_AUTH_SECRET` | Built-in fallback | HMAC secret for token signing |
| `LPA_DATABASE_URL` | `sqlite:///data/lahore_pulse.db` | Database connection |

## Configuration

Configuration is managed via environment variables with the `LPA_` prefix.

See `.env.example` for available options.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_health.py
```

## Code Quality

```bash
ruff check app/ tests/       # Lint
ruff format app/ tests/      # Format
mypy app/                    # Type check
```
