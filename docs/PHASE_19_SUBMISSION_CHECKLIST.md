# Hackathon Submission Checklist — Lahore Pulse AI

**Competition:** Smart City Hackathon Lahore 2026  
**Track:** Theme 2 — City Intelligence  
**Problem Statement:** "Predicting Problems Before They Happen, Not After"  
**Status:** Ready for submission

---

## Pre-Submission

- [ ] Backend starts cleanly: `curl http://127.0.0.1:8002/api/v1/health` returns `{"status":"healthy"}`
- [ ] Frontend starts cleanly: `http://127.0.0.1:5173/` shows landing page
- [ ] Login works: Officer demo account → `/government`
- [ ] Data loads: PM2.5 value visible, "Fresh" status, forecast values present
- [ ] Demo mode loads: `/government?demo=true&step=1` shows Step 1
- [ ] Demo walkthrough tested: Steps 1→6 all render correctly
- [ ] All 1,619 tests still pass (run `npx vitest run` + `pytest`)

## Submission Materials

### Required

- [ ] Project title: "Lahore Pulse AI"
- [ ] One-line pitch written
- [ ] Short description (50 words) written
- [ ] Full project description (400–700 words) written
- [ ] Technology stack documented
- [ ] README.md present and accurate

### Screenshots (7 required)

- [ ] S1: Command Center Overview (`/government`)
- [ ] S2: Forecast Trajectory (`/government/forecasts`)
- [ ] S3: Active Incidents (`/government/incidents`)
- [ ] S4: Investigation Detail (click severe incident)
- [ ] S5: Demo Mode (`/government?demo=true&step=3`)
- [ ] S6: Episode Intelligence (`/alerts`)
- [ ] S7: Landing Page (`/`)

### Demo

- [ ] Demo script reviewed and rehearsed (3–5 minutes)
- [ ] Demo recovery procedure printed/saved
- [ ] Demo mode Step 1→6 walkthrough tested
- [ ] Timing verified (target: 3 min 30 sec)

### Presentation (if required)

- [ ] Deck slides created from `docs/competition/HACKATHON_DECK_SPEC.md`
- [ ] 8 slides, 3-minute narration
- [ ] Live demo interleaved with slides

### Video (if required)

- [ ] Video recorded per `docs/competition/VIDEO_PLAN.md`
- [ ] 3–5 minutes duration
- [ ] Screen recording with narration

## Repository

- [ ] No temp files in repo (Phase 18 scripts cleaned up)
- [ ] `.gitignore` updated: `node_modules/`, `backend/data/`, `*.db`, `*.joblib`
- [ ] README.md test counts updated: 1,619 tests (995 BE + 624 FE)
- [ ] README.md observation count updated: 1.35M
- [ ] No secrets in code (verified in Phase 18 Step 9)

## Devpost / Submission Platform

- [ ] Team info filled in `docs/competition/devpost/TEAM_INFO.md`
- [ ] GitHub repository URL ready
- [ ] Live demo URL documented (localhost:5173)
- [ ] All devpost files present:
  - [ ] PROJECT_DESCRIPTION.md
  - [ ] README.md
  - [ ] TECHNOLOGY栈.md
  - [ ] CHALLENGES.md
  - [ ] ACCOMPLISHMENTS.md
  - [ ] WHAT_WE_LEARNED.md
  - [ ] WHAT_NEXT.md
  - [ ] TEAM_INFO.md

## Final

- [ ] Submission form reviewed
- [ ] Final submission proofread
- [ ] All links tested
- [ ] Screenshots uploaded
- [ ] Video attached (if required)
- [ ] **SUBMITTED**
