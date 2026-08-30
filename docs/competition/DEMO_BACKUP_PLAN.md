# Demo Backup Plan — Lahore Pulse AI

**Purpose:** Contingency plans if live demo fails during competition presentation  

---

## Failure Scenario 1: Backend Won't Start

**Symptoms:** uvicorn fails to bind, import errors, database locked

**Backup:**
1. Check port availability: `netstat -ano | findstr :8000`
2. Kill conflicting process if needed
3. If database locked: `cp backend/data/lahore_pulse.db backend/data/lahore_pulse_backup.db` and update config
4. If all else fails: restart machine, run health-check.sh

**Fallback:** Use pre-recorded screenshots from `docs/competition/screenshots/`

---

## Failure Scenario 2: Frontend Build Fails

**Symptoms:** npm run dev fails, port 5173 occupied

**Backup:**
1. Clear cache: `rm -rf frontend/node_modules/.vite`
2. Reinstall: `cd frontend && npm install`
3. Try different port: `cd frontend && npm run dev -- --port 3000`
4. If build fails: `cd frontend && npm run build && npx serve dist`

**Fallback:** Show production build via `npx serve frontend/dist`

---

## Failure Scenario 3: No Network (Offline Mode)

**Symptoms:** Cannot fetch new data from CAMS

**Backup:**
- The system works entirely offline with existing 1.31M records
- Predictions are generated from cached observations
- All historical data is in the SQLite database
- Map tiles may not load — use screenshots instead

**Fallback:** Show pre-loaded data in browser, reference screenshots

---

## Failure Scenario 4: Database Corruption

**Symptoms:** SQLite errors, missing data

**Backup:**
1. Restore from backup: `cp backend/data/lahore_pulse_backup.db backend/data/lahore_pulse.db`
2. If no backup: recreate with `cd backend && python -m app.infrastructure.database`

**Fallback:** Show API responses from curl/Postman with pre-recorded data

---

## Failure Scenario 5: Model Loading Fails

**Symptoms:** "No model found for horizon" errors

**Backup:**
1. Check model registry: `cat backend/data/models/model_registry.json`
2. Verify artifacts exist: `ls backend/data/models/horizon_*/`
3. Restart backend to re-register models

**Fallback:** Show model metadata files and explain the system architecture

---

## Failure Scenario 6: Demo Video Won't Play

**Symptoms:** Video file corrupted, wrong format

**Backup:**
1. Have video in multiple formats (MP4, WebM)
2. Upload to YouTube as private backup
3. Have screenshots ready to show instead

**Fallback:** Walk through screenshots with narration

---

## Emergency Contacts

- **Backend issues:** Check `backend/README.md` for setup instructions
- **Frontend issues:** Check `frontend/README.md` for setup instructions
- **Model issues:** Check `backend/data/models/model_registry.json`

---

## Key Files for Offline Demo

| File | Purpose |
|------|---------|
| `backend/data/lahore_pulse.db` | Full database (672MB) |
| `backend/data/models/` | All model artifacts (5 horizons) |
| `frontend/dist/` | Production build |
| `docs/competition/screenshots/` | Pre-captured screenshots |
| `docs/competition/DEMO_SCRIPT.md` | Narration script |

---

## Quick Recovery Commands

```bash
# Full system restart
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .
cd frontend && npm run dev

# Run health check
bash scripts/health-check.sh

# Run all tests (confidence check)
cd backend && python -m pytest tests/ -v --no-header -q --no-file-parallelism
cd frontend && npx vitest run --pool=forks

# Production build
cd frontend && npm run build
```
