# Technology Stack — Lahore Pulse AI

## Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | Python | 3.11 | Application runtime |
| Web Framework | FastAPI | Latest | REST API with auto-docs |
| ASGI Server | uvicorn | Latest | Production-grade server |
| Data Validation | Pydantic v2 | Latest | Request/response models |
| ML Library | scikit-learn | Latest | Ridge, HistGradientBoosting |
| Database | SQLite | 3.x | 1.31M observation records |
| Scheduler | asyncio | stdlib | Auto-refresh every 30 minutes |
| Testing | pytest | Latest | 570 backend tests |

## Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 19.2.8 | UI components |
| Build Tool | Vite | 8.2.1 | Fast development + production builds |
| Routing | react-router-dom | 7.18.2 | Page navigation (3 pages) |
| Maps | Leaflet | 1.9.4 | Interactive Lahore map |
| Charts | Recharts | 3.10.1 | Historical trend visualization |
| Testing | Vitest | 4.1.10 | 106 frontend tests |
| Linting | ESLint | Latest | Code quality |

## Data

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Primary Source | CAMS (CAMS NRT) | PM2.5 reanalysis data |
| Storage | SQLite | 672MB database, 1.31M records |
| Features | Custom pipeline | 41 engineered features per prediction |

## Architecture

| Pattern | Implementation |
|---------|---------------|
| Layered Architecture | API → Application → Domain → Infrastructure |
| Factory Pattern | `create_app()` for FastAPI initialization |
| Provider Pattern | Abstract data provider interfaces |
| Window Functions | SQL ROW_NUMBER for latest-per-station queries |
| Walk-Forward Validation | Temporal train/test splits for model evaluation |

## Development Tools

| Tool | Purpose |
|------|---------|
| ruff | Python linting + formatting |
| mypy | Static type checking |
| pytest-cov | Test coverage |
| ESLint | JavaScript linting |
| npm | Package management |

## Deployment (Demo)

| Component | Command |
|-----------|---------|
| Backend | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .` |
| Frontend | `cd frontend && npm run dev` |
| Tests | `python -m pytest tests/ -v --no-header -q --no-file-parallelism` |
| Health Check | `bash scripts/health-check.sh` |
