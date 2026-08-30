# Lahore Pulse AI — 3-Minute Hackathon Demo Script

**Product status: FROZEN.** Do not modify code, add features, or change the UI.  
**Duration:** 3 minutes  
**Audience:** Smart City Hackathon Lahore judges  
**Format:** Live demo with narration  

---

## Pre-Demo Setup (5 minutes before)

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Health check
bash scripts/health-check.sh
```

Open browser to `http://localhost:5173` — let dashboard fully load before starting.

---

## SECTION 1: 3-MINUTE SCRIPT WITH TIMESTAMPS

### 0:00–0:20 — Hook

> Lahore breathes some of the worst air on Earth. During a November smog episode, PM2.5 hit 365 micrograms per cubic meter — twenty-four times the WHO safe limit. Today we're showing you a system that gives decision-makers a one-to-twenty-four-hour heads-up before those episodes escalate.

**Screen:** Browser is already on `localhost:5173` — the Dashboard is loaded. No navigation needed yet.

---

### 0:20–0:50 — Dashboard Walkthrough

**Action:** Scroll down slightly to center the Forecast Trajectory section.

> This is the live dashboard. Right now Lahore sits at 77 micrograms per cubic meter — unhealthy for everyone. The forecast trajectory shows where we expect air quality to head over the next 24 hours: a dip to 44 by 12 hours, then back up to 68 at the 24-hour mark. Each horizon uses a different model optimised for that timeframe.

**Action:** Point to the trust indicators.

> And every forecast comes with a trust snapshot — data freshness, historical reliability, and a verification counter. Right now 1,966 predictions are being tracked. This is not a black box.

---

### 0:50–1:15 — Episode Intelligence

**Action:** Scroll down to the Episode Intelligence card.

> Our episode intelligence section uses rule-based detection — not machine learning — to flag when pollution is building into a sustained episode. Today: no active episode. But look at the weather context — two of four factors match conditions historically associated with episodes. We say "associated with," not "caused by." That's an important distinction.

**Action:** Point to the text that says "statistical association, not causation."

> Every weather comparison carries that caveat. We don't make causal claims. We show investigation signals, not confirmed emission sources.

---

### 1:15–1:40 — Response Signals

**Action:** Scroll to the Response Signals section.

> When an episode is active, response signals break down which investigation domains are relevant — traffic patterns, industrial activity, transboundary events, meteorological conditions. These are signals for human investigators, not automated alerts. Right now there's no active episode, so this section correctly shows "not applicable."

---

### 1:40–2:10 — Historical Replay

**Action:** Click "Replay" in the navigation bar.

> Now let's look at history. This is every pollution episode the system has detected — 20 episodes sorted by peak severity.

**Action:** Click on "Nov 13, 2024" — the top episode (peak 365 μg/m³).

> November 13th, 2024. Peak of 365 micrograms per cubic meter. Let's replay it hour by hour.

**Action:** Click the Play button. Let it run for about 10 seconds through the first several hours.

> Watch the chart build. Every data point is a real observation from our database — 72 hours of hourly PM2.5 readings. The red lines are our episode and severe thresholds. You can see this day stayed above the severe line for the entire 24-hour period.

**Action:** Pause playback.

> This is Level 1 replay — historical observations only. No model predictions overlaid. What you see is what was actually measured.

---

### 2:10–2:35 — Prediction Accountability

**Action:** Navigate back to Dashboard. Scroll to the Prediction Accountability section. Click to expand it.

> Prediction accountability is baked in: predict, observe, verify, learn. Every forecast the system makes gets compared against what actually happened. That's how we build a track record — and that's how users decide whether to trust the system.

**Action:** Point to the verification track count (1,966 predictions tracked).

> Nearly two thousand predictions are already in the verification pipeline.

---

### 2:35–2:50 — Government View

**Action:** Click "Government" in the navigation bar.

> The government view consolidates everything into operational intelligence — the same data, restructured for a decision-maker who needs a single-screen briefing. Current reading, forecast trajectory, trust snapshot, data freshness, and a six-hour trend indicator — all in one view.

---

### 2:50–3:00 — Closing

> Lahore Pulse AI doesn't pretend to solve air pollution. What it does is give the people who can act a reliable, honest, accountable signal — backed by 1.3 million real observations and five forecasting models — so they can act hours earlier than they could before. Thank you.

---

## SECTION 2: EXACT SCREEN ACTIONS

| Time | Action | Notes |
|------|--------|-------|
| 0:00 | Browser is on Dashboard (`localhost:5173/`) | Pre-load before starting |
| 0:22 | Scroll down to center Forecast Trajectory | Smooth scroll, don't jump |
| 0:35 | Point/hover over Trust Snapshot section | Three cards: Data Quality, Reliability, Verification |
| 0:50 | Scroll down to Episode Intelligence card | Shows "No Episode" + weather context |
| 1:05 | Point to "statistical association, not causation" text | Bold statement in the weather section |
| 1:15 | Scroll to Response Signals | Shows "not applicable" in no-episode state |
| 1:40 | Click "Replay" link in navbar | Top nav bar, 4th item |
| 1:43 | Wait for episode list to load | ~1-2 seconds |
| 1:45 | Click "Nov 13, 2024" episode | First item, peak 365 |
| 1:48 | Wait for chart to render | ~1 second |
| 1:50 | Click Play button (▶) | Below the chart |
| 2:00 | Let playback run ~10 seconds | Chart fills, state card updates |
| 2:05 | Click Pause button (⏸) | Freezes the playback |
| 2:10 | Click "Dashboard" link in navbar | Navigate back |
| 2:13 | Wait for dashboard to load | ~2 seconds |
| 2:15 | Scroll to Prediction Accountability section | Click to expand if collapsed |
| 2:25 | Point to "1,966 predictions tracked" | Trust Snapshot verification track |
| 2:35 | Click "Government" link in navbar | Third item in nav |
| 2:38 | Wait for government page to load | ~2-3 seconds |
| 2:40 | Scroll to show full Operational Intelligence view | All sections visible |
| 2:50 | Pause on government view for closing statement | Don't navigate away |

---

## SECTION 3: EXACT SPOKEN WORDS

**(Natural, conversational delivery. Read from memory — do not read verbatim from screen.)**

---

**[0:00] HOOK**

"Lahore breathes some of the worst air on Earth. During a November smog episode, PM2.5 hit 365 micrograms per cubic meter — twenty-four times the WHO safe limit. Today we're showing you a system that gives decision-makers a one-to-twenty-four-hour heads-up before those episodes escalate."

---

**[0:20] DASHBOARD**

"This is the live dashboard. Right now Lahore sits at 77 micrograms per cubic meter — unhealthy for everyone." *(gesture at the large number)*

"The forecast trajectory shows where we expect air quality to head over the next 24 hours: a dip to 44 by 12 hours, then back up to 68 at the 24-hour mark." *(trace the trajectory arc with your hand)*

"Each horizon uses a different model optimised for that timeframe." *(brief gesture at the six cards)*

"And every forecast comes with a trust snapshot — data freshness, historical reliability, and a verification counter." *(point to the three cards)*

"Right now 1,966 predictions are being tracked. This is not a black box."

---

**[0:50] EPISODE INTELLIGENCE**

*(scroll to the Episode Intelligence card)*

"Our episode intelligence section uses rule-based detection — not machine learning — to flag when pollution is building into a sustained episode."

"Today: no active episode." *(point to "No Episode" badge)*

"But look at the weather context — two of four factors match conditions historically associated with episodes." *(point to the weather grid)*

"We say 'associated with,' not 'caused by.' That's an important distinction." *(point to the caveat text)*

"Every weather comparison carries that caveat. We don't make causal claims. We show investigation signals, not confirmed emission sources."

---

**[1:15] RESPONSE SIGNALS**

*(scroll to Response Signals)*

"When an episode is active, response signals break down which investigation domains are relevant — traffic patterns, industrial activity, transboundary events, meteorological conditions."

"These are signals for human investigators, not automated alerts."

"Right now there's no active episode, so this section correctly shows 'not applicable.'"

---

**[1:40] HISTORICAL REPLAY**

*(click "Replay" in the navigation bar)*

"Now let's look at history. This is every pollution episode the system has detected — 20 episodes sorted by peak severity."

*(click "Nov 13, 2024" — the top item)*

"November 13th, 2024. Peak of 365 micrograms per cubic meter. Let's replay it hour by hour."

*(click Play button, let it run ~10 seconds)*

"Watch the chart build. Every data point is a real observation from our database — 72 hours of hourly PM2.5 readings."

*(point to the horizontal threshold lines on the chart)*

"The red lines are our episode and severe thresholds. You can see this day stayed above the severe line for the entire 24-hour period."

*(pause playback)*

"This is Level 1 replay — historical observations only. No model predictions overlaid. What you see is what was actually measured."

---

**[2:10] PREDICTION ACCOUNTABILITY**

*(navigate back to Dashboard, scroll to Prediction Accountability, click to expand)*

"Prediction accountability is baked in: predict, observe, verify, learn." *(point to the four-step label)*

"Every forecast the system makes gets compared against what actually happened. That's how we build a track record — and that's how users decide whether to trust the system."

*(point to verification count)*

"Nearly two thousand predictions are already in the verification pipeline."

---

**[2:35] GOVERNMENT VIEW**

*(click "Government" in the navigation bar)*

"The government view consolidates everything into operational intelligence — the same data, restructured for a decision-maker who needs a single-screen briefing."

*(scroll to show all sections)*

"Current reading, forecast trajectory, trust snapshot, data freshness, and a six-hour trend indicator — all in one view."

---

**[2:50] CLOSING**

"Lahore Pulse AI doesn't pretend to solve air pollution. What it does is give the people who can act a reliable, honest, accountable signal — backed by 1.3 million real observations and five forecasting models — so they can act hours earlier than they could before. Thank you."

---

## SECTION 4: BACKUP SCRIPTS

### Backup A: If Current State Shows "Episode Active" Instead of "No Episode"

If the demo day happens to fall during a real pollution episode, **use it** — it's even more compelling.

**Replace the Episode Intelligence section (0:50–1:15) with:**

> "Right now we're in an active episode. Current PM2.5 is [X] micrograms per cubic meter, and the system is flagging investigation signals across [N] domains." *(scroll through response signals)*

> "These are signals for human investigators — not confirmed emission sources. The system is saying 'look here,' not 'this is the cause.'"

**Keep everything else the same.** The dashboard, forecast, replay, and government views all work regardless of episode state.

---

### Backup B: If Data Is Slow to Load (>5 seconds)

If the dashboard takes too long to load (cold start, slow network):

**Replace the Dashboard section (0:20–0:50) with:**

> "While the dashboard loads — this is a cold start, the backend is warming up its models — let me explain what you're about to see."

*(fill time by explaining the data pipeline: 1.3 million observations from Copernicus, 45 km resolution grid point at 31.52, 74.36)*

> "Once it loads, you'll see a live forecast trajectory and real-time episode detection."

*(when it loads)*

> "There we go. Live data."

---

### Backup C: If Replay Page Is Slow to Load

If the episode list takes more than 3 seconds:

**Replace the Replay opening (1:40–1:45) with:**

> "The system has catalogued 371 historical episodes. Let me show you the most severe one."

*(keep talking about the data while it loads: average episode duration 5.8 hours, 90.8% of peaks occur within the first 6 hours)*

> "There — 20 episodes, sorted by peak severity. November 13th at the top."

---

### Backup D: If Government Page Is Slow

If the government page takes more than 3 seconds:

**Replace the Government section (2:35–2:50) with:**

> "The government view is our operational intelligence dashboard. It pulls the same data from the same API but structures it for a different audience."

*(fill with: "Decision-makers don't need raw charts — they need a single-screen briefing with a clear trend indicator and a trust score.")*

> "There it is — current reading, forecast trajectory, trust snapshot, all on one screen."

---

### Backup E: If Entire Frontend Fails (White Screen)

**Do not panic. Switch to terminal demo.**

```bash
# Show the API directly
curl -s http://127.0.0.1:8000/api/v1/episode | python -m json.tool
curl -s "http://127.0.0.1:8000/api/v1/replay/episodes" | python -m json.tool
```

> "Even without the frontend, the backend API is serving real-time episode intelligence and historical replay data. The frontend is one consumer of this API — mobile apps, government dashboards, and alerting systems can all plug in."

---

## SECTION 5: JUDGE Q&A

### Q1: "How is this different from existing air quality monitoring?"

**Answer:** "Existing systems show you what the air quality is right now. We forecast one to twenty-four hours ahead using five different models, each optimised for its timeframe. We also detect when conditions are building into a sustained pollution episode — not just a spike — and we provide a trust snapshot so decision-makers know how much confidence to place in each forecast."

---

### Q2: "Where does the data come from? Is it real?"

**Answer:** "All data comes from the Copernicus Atmosphere Monitoring Service — CAMS. We have 1.3 million hourly PM2.5 observations spanning multiple years. Every observation is traceable to its source and collection time. The database is 749 megabytes of SQLite. Nothing is fabricated."

---

### Q3: "How accurate are the forecasts?"

**Answer:** "Accuracy varies by horizon. The one-hour Ridge regression model has strong historical validation. The 24-hour model is less precise but still provides useful directional guidance. We don't claim a single accuracy number because it depends on the timeframe and conditions. What we do is track every prediction against what actually happened — right now 1,966 predictions are in the verification pipeline."

---

### Q4: "What happens when the weather changes suddenly?"

**Answer:** "The system re-evaluates every 30 minutes when fresh CAMS data arrives. If weather conditions shift, the forecast adjusts. The weather context section shows you which factors match historical episode patterns — but we're explicit that these are statistical associations, not causal relationships. We don't claim the weather 'causes' episodes."

---

### Q5: "Why rule-based detection instead of machine learning for episodes?"

**Answer:** "Because we wanted transparent, auditable detection criteria. A rule says: PM2.5 above 120 and rising by 30 or more over six hours, sustained for three hours. Anyone can inspect those thresholds and understand why an episode was flagged. A machine learning classifier would be harder to explain to a government decision-maker who needs to act on the output."

---

### Q6: "What's the 'Level 1' in 'Level 1 Replay'?"

**Answer:** "Level 1 means we show historical observations only — what the sensors actually measured hour by hour. Level 2 would overlay model predictions from that time period to show what the system would have forecast. Level 3 would add verification data showing what the models got right or wrong. We implemented Level 1 first because it's the foundation — you can't evaluate predictions without first seeing the ground truth."

---

### Q7: "Can this system be deployed in other cities?"

**Answer:** "The architecture is city-agnostic. The CAMS data source covers all of Europe and parts of Asia and Africa. To adapt for a new city, you'd change the grid point coordinates, retrain the models on that city's historical data, and adjust the episode thresholds. The detection rules and the frontend are reusable as-is."

---

### Q8: "What's the response signals section for?"

**Answer:** "When an episode is active, response signals identify investigation domains — things like traffic patterns, industrial activity, transboundary events, and meteorological conditions. These are signals for human investigators, not automated alerts. We're saying 'here's where to look,' not 'this is the confirmed source.' The goal is to help investigators prioritise their time."

---

### Q9: "How do you handle data freshness?"

**Answer:** "We check data freshness on every dashboard load. If the most recent observation is less than 2 hours old, we show 'Fresh.' Between 2 and 6 hours, 'Stale.' Above 6 hours, 'Expired' with a warning. The system needs CAMS data every 30 minutes for optimal performance, but it continues operating with older data — the trust snapshot reflects the reduced reliability."

---

### Q10: "What are the limitations you'd acknowledge?"

**Answer:** "Three honest ones: First, the grid resolution is 45 kilometres — that's the CAMS spatial resolution. A reading at one grid point may not represent conditions five kilometres away. Second, the detection is rule-based, so it can't learn new episode patterns without human adjustment of thresholds. Third, we rely entirely on CAMS data — if CAMS goes down, we have no new input until it recovers. We have 1.3 million historical observations as a buffer, but real-time forecasting would pause."

---

## SECTION 6: FINAL ONE-SENTENCE PITCH

> **Lahore Pulse AI is a transparent air quality forecasting system that gives decision-makers one-to-twenty-four-hour advance warning of pollution episodes — backed by 1.3 million real observations, five optimised models, and built-in prediction accountability — so they can act hours earlier than they could before.**

---

## SAFETY RULES — THINGS TO NEVER SAY

| ❌ Never Say | ✅ Say Instead |
|---|---|
| "AI detects episodes" | "Rule-based detection identifies episodes" |
| "Weather causes pollution" | "Weather conditions are statistically associated with episodes" |
| "It will peak at X at Y time" | "The forecast suggests PM2.5 may reach X by Y" |
| "Confirmed emission source" | "Investigation signal" / "Domain to investigate" |
| "Government is notified" | "Decision-makers receive the briefing" |
| "Real-time integration" | "Data refreshes every 30 minutes when CAMS data arrives" |
| "The system learns automatically" | "We track predictions against outcomes for manual review" |
| "95% accuracy" (or any fake %) | "Strong historical validation" / cite actual verification count |
| "Weather causes the episode" | "Statistical association, not causation" |
| "This is Level 3 replay" | "This is Level 1 replay — observations only" |

---

## VERIFIED DATA POINTS (for script accuracy)

All values below were verified against the live application on Aug 24, 2026:

| Metric | Value | Source |
|--------|-------|--------|
| Current PM2.5 | 76.9 μg/m³ (reported as 69 in episode card) | Dashboard |
| Episode State | No Episode | Episode Intelligence |
| Trajectory | Increasing near-term, improving 12h+ | Forecast Trajectory |
| Forecast: Now | 77 μg/m³ (Unhealthy) | Forecast cards |
| Forecast: +12h | 44 μg/m³ (Moderate) | Forecast cards |
| Forecast: +24h | 68 μg/m³ (Unhealthy) | Forecast cards |
| Data freshness | Fresh (0.6h ago, Aug 24 01:00 AM PKT) | Dashboard |
| Weather match | 2 of 4 factors | Episode Intelligence |
| Historical episodes | 371 | Historical Context |
| Avg episode duration | 5.8 hours | Historical Context |
| Peaks within 6h | 90.8% | Historical Context |
| Verification track | 1,966 predictions tracked | Trust Snapshot |
| Nov 13, 2024 peak | 365.1 μg/m³ | Replay |
| Nov 13, 2024 avg | 264.9 μg/m³ | Replay |
| Nov 13, 2024 readings | 72 hourly readings | Replay |
| Grid point | 31.5204, 74.3587 | Episode Intelligence |
| Grid resolution | 45 km (CAMS) | System documentation |
| Total observations | 1.3 million | Database |
| Database size | 749 MB SQLite | System |
| Models loaded | 5 (Ridge 1h/24h, HGB 3h/6h/12h) | Backend |
| Episode threshold | 120 μg/m³ PM2.5 | Detection config |
| Severe threshold | 150 μg/m³ PM2.5 | Detection config |
| Detection method | Rule-based (NOT machine learning) | Episode Intelligence |
| Detection criteria | PM2.5 > 120, Δ ≥ 30 in 6h, sustained ≥ 3h | System |
