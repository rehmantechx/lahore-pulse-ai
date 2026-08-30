# Documentation Index — Lahore Pulse AI

**Last Updated:** August 2026  

---

## Project Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| README | `README.md` | Project overview, setup, architecture |
| Development Guide | `docs/development/DEVELOPMENT.md` | Development workflow, conventions |
| Architecture Decision Record | `docs/architecture/ADR-001-architecture-foundation.md` | Architecture decisions and rationale |

---

## Phase Reports

| Phase | Location | Summary |
|-------|----------|---------|
| Phase 0.5 | `docs/research/PHASE-0.5-REPORT.md` | Data source research |
| Phase 2 | `docs/PHASE2_REPORT.md` | Data pipeline |
| Phase 2 Data | `docs/PHASE2_FULL_DATA.md` | Detailed data exploration |

---

## Research & Data

| Document | Location | Purpose |
|----------|----------|---------|
| Data Source Research | `docs/research/DATA-SOURCE-RESEARCH.md` | CAMS, OpenAQ evaluation |
| Coverage Report | `backend/data/reports/coverage_report.md` | Data coverage analysis |
| Quality Gates | `backend/data/reports/quality_gates_report.md` | Data quality assessment |
| Phase 2 Data | `docs/PHASE2_FULL_DATA.md` | Detailed data exploration |

---

## Competition Materials

| Document | Location | Purpose |
|----------|----------|---------|
| Final System Status | `docs/competition/FINAL_SYSTEM_STATUS.md` | System readiness overview |
| Competition Scorecard | `docs/competition/COMPETITION_READINESS_SCORECARD.md` | Readiness assessment |
| Demo Workflow | `docs/competition/DEMO_WORKFLOW.md` | Step-by-step demo guide |
| Demo Script | `docs/competition/DEMO_SCRIPT.md` | Narration script with timing |
| Demo Backup Plan | `docs/competition/DEMO_BACKUP_PLAN.md` | Contingency plans |
| Health Check Script | `scripts/health-check.sh` | Quick system verification |
| Screenshot Plan | `docs/competition/SCREENSHOT_PLAN.md` | Screenshot capture guide |
| Video Plan | `docs/competition/VIDEO_PLAN.md` | Demo video production |
| Presentation Content | `docs/competition/PRESENTATION_CONTENT.md` | Slide content + speaker notes |
| Model Explanation | `docs/competition/MODEL_EXPLANATION.md` | ML models explained |
| Limitation Audit | `docs/competition/LIMITATION_AUDIT.md` | Honest limitation assessment |

---

## Devpost Submission

| Document | Location | Purpose |
|----------|----------|---------|
| Devpost README | `docs/competition/devpost/README.md` | Devpost overview |
| Project Description | `docs/competition/devpost/PROJECT_DESCRIPTION.md` | Short + long descriptions |
| Technology Stack | `docs/competition/devpost/TECHNOLOGY_STACK.md` | Tech details |
| Challenges | `docs/competition/devpost/CHALLENGES.md` | Challenges faced |
| Accomplishments | `docs/competition/devpost/ACCOMPLISHMENTS.md` | What we accomplished |
| What We Learned | `docs/competition/devpost/WHAT_WE_LEARNED.md` | Key insights |
| What's Next | `docs/competition/devpost/WHAT_NEXT.md` | Future plans |
| Team Info | `docs/competition/devpost/TEAM_INFO.md` | Team information |
| Architecture | `docs/competition/devpost/ARCHITECTURE.md` | System architecture |

---

## Quick Reference

### Running the System
```bash
# Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .

# Frontend
cd frontend && npm run dev

# Health check
bash scripts/health-check.sh
```

### Running Tests
```bash
# Backend (570 tests)
cd backend && python -m pytest tests/ -v --no-header -q --no-file-parallelism

# Frontend (106 tests)
cd frontend && npx vitest run --pool=forks
```

### Key Endpoints
- Health: `GET /api/v1/health`
- Predictions: `GET /api/v1/predictions/latest`
- Observations: `GET /api/v1/observations/latest`
- Accuracy: `GET /api/v1/accuracy/summary`
- Stations: `GET /api/v1/stations`
- Models: `GET /api/v1/models/registry`

### Key Metrics
- Total observations: 1,310,236
- Model horizons: 5 (1h–24h)
- Best R²: 0.975 (1h)
- Honest R²: 0.703 (24h)
- Backend tests: 570
- Frontend tests: 106
- API endpoints: 21
- Database size: 672MB
