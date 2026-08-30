# Demo Script: 2-Minute Guided Walkthrough

## Pre-Demo Setup

1. Open `http://localhost:5173/?demo=true`
2. The demo controller appears on the right side of the screen
3. Click "Overview" in the government nav (the only enabled link in demo mode)
4. The system is pre-loaded with realistic Lahore data

---

## Step 1: The Problem (0–15s)

**Click "Next"** → Step 1: Monitoring

> "Lahore is one of the most polluted cities in the world. PM2.5 regularly hits 10× the WHO limit. The city has monitoring stations — but the gap isn't measurement. The gap is response."

**Point to**: Command strip showing live station data. The system is monitoring normally.

**Key message**: The data exists. The question is: what do we do with it?

---

## Step 2: Event Detected (15–35s)

**Click "Next"** → Step 2: Event Detected

> "At 3:15 PM, the system detects an abnormal pollution episode at the Kot Lakhpat station. PM2.5 has spiked to 185 µg/m³ — that's 12× the WHO guideline."

**Point to**: Incident status showing the episode state. The system classified this as a "Severe" episode using deterministic rules — not AI.

**Key message**: Detection is automatic and deterministic. No AI involved yet.

---

## Step 3: AI Investigation (35–55s)

**Click "Next"** → Step 3: Investigation

> "Here's where AI enters the picture — but with strict constraints. The AI doesn't say 'this factory is polluting.' It says: based on wind data and historical patterns, investigate the northeast quadrant first. High confidence, 85%."

**Point to**: Decision Trace showing the 4-layer evidence chain. AI Hypothesis badge is amber. Investigation recommendations with confidence levels.

**Key message**: The AI is constrained. It generates hypotheses, not conclusions. Every output is labeled by its data layer.

---

## Step 4: Exposure Map (55–80s)

**Click "Next"** → Step 4: Exposure

> "The system predicts the approximate exposure direction using wind data and station geometry. This is a directional estimate — not a precise boundary. The red zone is where investigation is most urgent."

**Point to**: Leaflet map showing the exposure wedge, station markers, and investigation area.

**Key message**: The map helps officers decide where to go first. It's approximate, and it says so.

---

## Step 5: Human Verification (80–105s)

**Click "Next"** → Step 5: Verification

> "This is the critical step. A field officer goes to the recommended area and reports what they found. They found an active construction site with no dust suppression. The system now knows: this recommendation was useful."

**Point to**: Verification panel showing officer report, "Useful: Yes" badge, and the accountability record.

**Key message**: The system doesn't just recommend — it tracks whether the recommendation was helpful. This is the accountability loop.

---

## Step 6: Historical Learning (105–120s)

**Click "Next"** → Step 6: Accountability

> "Over time, the system builds a track record. 67% of investigation recommendations were found useful. It remembers what was found at each location and learns which areas have recurring problems. Each episode makes the next one better."

**Point to**: Investigation learning panel showing historical verification stats and past outcomes.

**Key message**: The system improves with use. This is not a static dashboard — it's a learning system.

---

## Closing Statement

> "Lahore+ doesn't claim to know what causes pollution. It doesn't identify polluters. It helps humans investigate faster with clearer evidence. Every AI output is labeled, confidence-rated, and tracked. The system admits what it cannot know — and that's what makes it trustworthy."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Demo controller doesn't appear | Ensure URL has `?demo=true` |
| Pages show "No Data Available" | Demo mode should auto-inject fixtures — check console |
| Map tiles not loading | Normal — tiles require internet connection |
| Can't navigate to other pages | Demo mode restricts navigation to Overview only — this is by design |

---

## Judges' Cheat Sheet

| Question | Answer |
|----------|--------|
| "Is this real data?" | Real data from OpenAQ and Pakistan Meteorological Department, loaded into a local SQLite database |
| "How accurate is the AI?" | We don't claim accuracy percentages. We track usefulness through human verification. Currently 67% of recommendations are found useful. |
| "What if the AI is wrong?" | The verification loop catches it. Officers report what they actually found. Wrong recommendations are recorded and the system learns. |
| "Can it identify polluters?" | No. It generates directional investigation hypotheses, not source attribution. This is intentional. |
| "How is this different from a dashboard?" | Dashboards show data. Lahore+ makes recommendations and tracks whether they were useful. |
| "What data does it use?" | Publicly available monitoring station data (OpenAQ) and weather data. No private or proprietary data. |
