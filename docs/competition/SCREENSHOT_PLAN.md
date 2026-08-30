# Screenshot Plan — Lahore Pulse AI

**Purpose:** Plan for capturing competition screenshots  
**Status:** Plan ready — screenshots need to be captured manually  

---

## Required Screenshots

### 1. Dashboard Page (3 screenshots)

| # | Focus | Description | Notes |
|---|-------|-------------|-------|
| S1 | Full page | Complete Dashboard with forecast cards, map, and charts | Show all 5 horizon cards |
| S2 | Forecast cards | Close-up of forecast cards showing algorithm names and confidence | Expand technical details |
| S3 | Historical chart | Trend chart with WHO guideline reference line | Show 24h time window |

### 2. Citizen Page (2 screenshots)

| # | Focus | Description | Notes |
|---|-------|-------------|-------|
| S4 | Health guidance | PM2.5 level cards with health recommendations | Show different severity levels |
| S5 | Full page | Complete Citizen page with forecast + guidance | Show user-friendly layout |

### 3. Government Page (2 screenshots)

| # | Focus | Description | Notes |
|---|-------|-------------|-------|
| S6 | Data tables | Policy decision support tables with predictions | Show multi-horizon comparison |
| S7 | Full page | Complete Government page with map + accuracy tracker | Show station overlay |

### 4. Technical Screenshots (2 screenshots)

| # | Focus | Description | Notes |
|---|-------|-------------|-------|
| S8 | Model transparency | ModelTransparency component showing algorithm + metrics | Expand all sections |
| S9 | API docs | Swagger/OpenAPI documentation page | Show endpoint list |

### 5. Architecture (1 screenshot)

| # | Focus | Description | Notes |
|---|-------|-------------|-------|
| S10 | README diagram | Architecture diagram from README.md | Clean, readable version |

---

## Capture Instructions

### Setup
1. Start backend: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser to `http://localhost:5173`
4. Set browser window to 1920×1080 resolution

### Capture Process
1. Navigate to each page
2. Wait for data to load (check network tab)
3. Expand all technical details sections
4. Capture screenshots using browser dev tools or Snipping Tool
5. Save to `docs/competition/screenshots/`

### File Naming
```
docs/competition/screenshots/
├── S01_dashboard_full.png
├── S02_forecast_cards.png
├── S03_historical_chart.png
├── S04_citizen_health.png
├── S05_citizen_full.png
├── S06_government_tables.png
├── S07_government_full.png
├── S08_model_transparency.png
├── S09_api_docs.png
└── S10_architecture.png
```

---

## Quality Checklist

- [ ] All screenshots are 1920×1080 or similar high resolution
- [ ] Text is readable (not blurry or compressed)
- [ ] No personal information visible
- [ ] No browser bookmarks or extensions visible
- [ ] Clean browser UI (no dev tools panels)
- [ ] Data is loaded (not empty states)
- [ ] Technical details are expanded where needed

---

## Usage

| Material | Screenshots Used |
|----------|-----------------|
| Devpost submission | S1, S4, S8, S10 |
| Presentation slides | S1, S2, S3, S4, S6, S8 |
| Documentation | S9, S10 |
| README | S10 |
