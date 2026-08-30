# Lahore Pulse AI — Hackathon Presentation Deck Specification

**Date:** 2026-08-24
**Duration:** 3 minutes (180 seconds)
**Audience:** Smart City Hackathon Lahore judges
**Format:** 8 slides, spoken narration, live demo interleaved
**Core differentiator:** Response Orchestrator (intelligence → evidence → investigation signals → simulated workflow → review → verification)

---

## Claims That MUST NOT Be Made

These are hard prohibitions. If any of these appear in slides, narration, or Q&A answers, the presentation is dishonest.

| Forbidden Claim | Why |
|----------------|-----|
| "We detect pollution sources" | The system shows investigation signals, not confirmed sources |
| "We notify the government" | The Response Orchestrator is a simulation, not a live dispatch system |
| "This is real-time" | CAMS reanalysis data has ~3–4 hour latency |
| "AI identifies the cause" | Domain evaluation is rule-based threshold matching, not ML source attribution |
| "We guarantee accuracy" | Forecast confidence varies; 24h is "Lower" — we say so |
| "This replaces Punjab's systems" | This is an intelligence layer that sits alongside existing monitoring |
| "We provide health advice" | No health recommendations are made; only PM2.5 levels and severity labels |
| "Automatic dispatch" | The workflow is manual simulation only; no department is contacted |
| "Confirmed emission source" | Every domain drawer says "investigation signal, not a confirmed source attribution" |
| "Confidence percentage" | We use labels (High / Moderate / Lower), not numeric probabilities |

---

## Timing Budget

| Slide | Title | Seconds | Cumulative |
|-------|-------|---------|------------|
| 1 | The Problem | 20s | 0:20 |
| 2 | What We Built | 25s | 0:45 |
| 3 | Episode Intelligence | 20s | 1:05 |
| 4 | Response Orchestrator | 25s | 1:30 |
| 5 | Multi-Horizon Forecast | 20s | 1:50 |
| 6 | Prediction Accountability | 20s | 2:10 |
| 7 | Historical Replay | 15s | 2:25 |
| 8 | Closing | 25s | 2:50 |
| | **Buffer** | **10s** | **3:00** |

---

## SLIDE 1 — The Problem

**On-slide text:**

> **Lahore's air is a data problem.**
>
> PM₂.₅ reaches 24× the WHO safe limit during winter smog.
> Decision-makers have no predictive intelligence layer.
> Every existing platform shows current air quality.
> None answers: *What happens next — and was our forecast right?*

**Recommended visual:** Full-bleed photo of Lahore smog (or a simple high-contrast text slide with the 4 bullet points). No logo yet.

**Live screen / screenshot:** None — this is the hook slide. Stay on this slide.

**Presenter narration (20s):**

> "Lahore experiences some of the worst air on Earth. During winter smog, PM₂.₅ hits twenty-four times the WHO safe limit. Every air quality platform on the market shows you what's happening right now. None of them tell you what's coming next — or whether their own forecast was right. That's the problem we're solving."

---

## SLIDE 2 — What We Built

**On-slide text:**

> **Lahore Pulse AI**
> Predictive city-intelligence layer for Lahore
>
> — Ingests 1.31M+ real observations from Copernicus (CAMS)
> — Forecasts PM₂.₅ at 1, 3, 6, 12, and 24 hours
> — Detects pollution episodes with rule-based intelligence
> — Generates investigation signals through the Response Orchestrator
> — Tracks whether every forecast was right or wrong
> — No black boxes. Every model, metric, and confidence level is visible.

**Recommended visual:** Architecture diagram — three layers: Data (CAMS → ingestion) → Intelligence (Episode + Forecast + Weather) → Response (Orchestrator → Workflow). Arrows flow downward.

**Live screen / screenshot:** None — diagram slide.

**Presenter narration (25s):**

> "Lahore Pulse AI is not another AQI dashboard. It's a predictive intelligence layer. We ingest over 1.3 million real environmental observations from the Copernicus Atmosphere Monitoring Service. Five independent models forecast PM₂.₅ one to twenty-four hours ahead. When conditions escalate, our Response Orchestrator generates structured investigation signals — not confirmed sources, investigation signals — and walks operators through a simulated response workflow. Every model name, every accuracy metric, every confidence label is visible. No black boxes."

---

## SLIDE 3 — Episode Intelligence

**On-slide text:**

> **Episode Intelligence**
> When does bad air become a sustained episode?
>
> — Rule-based detection (not ML): PM₂.₅ > 120 μg/m³ with ≥30 increase over 6h, sustained ≥3h
> — 4 weather-association domains evaluated against live conditions
> — Each domain shows its official regulatory basis (Punjab EPA, Transport Dept)
> — Caveat always visible: "statistical association, not causation"

**Recommended visual:** Screenshot of the Episode Intelligence card in `episode` state — red pill header, trajectory note, 4 weather variables with match/mismatch indicators.

**Live screen / screenshot:** **EPISODE state** — `ResponseOrchestrator` shows "POLLUTION INCIDENT ACTIVE" with weather context. Use the browser fixture-injected EPISODE state (PM₂.₅ = 145.0 μg/m³).

**Presenter narration (20s):**

> "When pollution is building into a sustained event, our Episode Intelligence section flags it — using rule-based detection, not machine learning. PM₂.₅ above 120 with a 30-point rise over 6 hours, sustained for 3 hours. It then evaluates four weather-association domains — open burning, traffic, dust, industrial — and shows which environmental factors currently match historical episode patterns. Every comparison carries the caveat: statistical association, not causation."

---

## SLIDE 4 — Response Orchestrator (CORE DIFFERENTIATOR)

**On-slide text:**

> **Response Orchestrator**
> From detection → evidence → investigation signals → simulated response workflow
>
> — 4 investigation domains evaluated with deterministic thresholds
> — 5-step workflow: Detected → Investigate → Acknowledge → Review → Closed
> — Target response windows from Punjab AQI Emergency Response Protocol
> — Every signal carries: *"This is an investigation signal, not a confirmed source attribution."*
> — Every render shows: *"Response workflow simulation. Not live government dispatch."*

**Recommended visual:** Screenshot of the full Response Orchestrator in EPISODE state — red header, 4 domain INVESTIGATE badges, 5-step pipeline, SLA windows, disclaimer at bottom. This is the hero screenshot of the entire presentation.

**Live screen / screenshot:** **EPISODE state via browser** — show the full Response Orchestrator section: header → PM₂.₅ value → trajectory → "Why was this flagged?" drawer → 4 domain signals (INVESTIGATE/LOW badges) → 5-step workflow pipeline → SLA windows → disclaimer. Click "Start Response Workflow" and advance through 2–3 steps during narration.

**Presenter narration (25s):**

> "This is our core differentiator. The Response Orchestrator takes the detected episode and does three things. First: it evaluates four investigation domains — open burning, traffic, dust, industrial — against current weather data using deterministic thresholds. Not machine learning. Second: it generates a structured five-step workflow — detected, investigate, acknowledge, review, closed — with target response windows sourced from Punjab's published emergency response protocol. Third — and this is critical — every single signal carries the explicit caveat: this is an investigation signal, not a confirmed source attribution. The workflow is a simulation, not a live dispatch. We show operators what to investigate, not what to conclude."

---

## SLIDE 5 — Multi-Horizon Forecast

**On-slide text:**

> **Five forecast horizons. Different algorithms for different timeframes.**
>
> | Horizon | Algorithm | Confidence |
> |---------|-----------|------------|
> | 1 hour | Ridge Regression | High |
> | 3 hours | HistGradientBoosting | High |
> | 6 hours | HistGradientBoosting | Moderate |
> | 12 hours | HistGradientBoosting | Moderate |
> | 24 hours | Ridge Regression | Lower |
>
> Algorithm names, metrics, and confidence labels — all visible in the UI.

**Recommended visual:** Screenshot of the Forecast Trajectory section — 6-point compact chart with horizon cards below. Show the algorithm name and confidence label for each card.

**Live screen / screenshot:** **Dashboard — Forecast Trajectory section** — scroll to the forecast cards. Point to the algorithm name printed on each card (e.g., "Ridge", "HistGradientBoosting"). Point to the confidence labels ("High", "Moderate", "Lower").

**Presenter narration (20s):**

> "We forecast PM₂.₅ at five time horizons. Short-term predictions — one and three hours — use Ridge Regression and Histogram Gradient Boosting respectively. Longer horizons switch algorithms because prediction difficulty changes with time. Every card shows the algorithm name and a confidence label tied to actual validation performance. The 24-hour horizon is labeled 'Lower' — we don't hide uncertainty, we show it."

---

## SLIDE 6 — Prediction Accountability

**On-slide text:**

> **Prediction Accountability**
> Was the forecast right? We track every one.
>
> — Every prediction is stored with its target time
> — When the target time passes, the system compares predicted vs. actual
> — Accuracy dashboard shows verified predictions over time
> — No AQ platform in the world does this for consumer-facing forecasts

**Recommended visual:** Screenshot of the Prediction Accountability component — the table showing prediction time, target time, predicted value, actual value, and verification status (verified / pending).

**Live screen / screenshot:** **Dashboard — Prediction Accountability section** (below fold). Show the accountability table with verified predictions. Point to the "Verified" / "Pending" status columns.

**Presenter narration (20s):**

> "Here's something no consumer air quality platform does: prediction accountability. Every forecast is stored with its target time. When that target time passes and an observation becomes available, the system compares what we predicted against what actually happened. Users can see a running record of verified predictions. We don't just say we're accurate — we prove it, prediction by prediction."

---

## SLIDE 7 — Historical Replay

**On-slide text:**

> **Historical Replay**
> 371 detected episodes. Hour-by-hour. No fabrication.
>
> — Every episode is a real detected event from 2023–2025 CAMS data
> — Hour-by-hour replay of PM₂.₅ trajectory
> — Seasonal patterns and average durations visible
> — Built-in validation: the same detection rules that run live were applied retroactively

**Recommended visual:** Screenshot of the Replay page showing the episode list — 371 episodes with peak values, date ranges, and duration. One episode expanded to show the hour-by-hour chart.

**Live screen / screenshot:** **Replay page** — click "Replay" in the navigation. Show the episode table (Nov 2024 at top with peak 365 μg/m³). Click on one episode to expand the hour-by-hour chart.

**Presenter narration (15s):**

> "Historical Replay gives us 371 detected episodes from 2023 to 2025 — every one a real event, not fabricated. You can replay any episode hour by hour. The same detection rules that run live were applied retroactively, so this is a genuine validation of the system's detection capability."

---

## SLIDE 8 — Closing

**On-slide text:**

> **Lahore Pulse AI**
>
> Intelligence layer around Punjab's existing monitoring systems.
>
> — Real data: 1.31M observations
> — Real models: 5 validated horizons
> — Real accountability: every forecast tracked
> — Real honesty: uncertainty shown, not hidden
>
> *"We don't replace Punjab's systems. We give them an intelligence layer."*

**Recommended visual:** Clean title card with the 4 bullet points. The closing quote at the bottom in a distinct font/weight.

**Live screen / screenshot:** None — closing slide. Return to title/logo.

**Presenter narration (25s):**

> "To close: Lahore Pulse AI is not a replacement for Punjab's existing air quality monitoring. It's an intelligence layer that sits alongside it — giving decision-makers advance warning, structured investigation signals, and transparent accountability for every forecast. Real data, real models, real accountability, and real honesty about what we know and what we don't. Thank you."

---

## Final Closing Sentence

> **"We don't replace Punjab's systems. We give them an intelligence layer."**

This sentence must appear verbatim on Slide 8 and be spoken as the last substantive line before "Thank you."

---

## Appendix: Live Demo Transition Guide

If the presentation includes a brief live demo between Slides 3 and 4 (optional, adds ~30s):

| Step | Action | What to Show |
|------|--------|-------------|
| 1 | Switch to browser on `localhost:5173` | Dashboard in EPISODE state (fixture-injected) |
| 2 | Scroll to Response Orchestrator | Red "POLLUTION INCIDENT ACTIVE" header |
| 3 | Click "Why was this flagged?" | Evidence drawer expands — trend, forecast, data status |
| 4 | Click Open Burning domain | Drawer shows "3 of 3 weather factors match" + official basis |
| 5 | Click "Start Response Workflow" | Step 0 activates — "Pollution incident detected by rule-based episode intelligence" |
| 6 | Click "Advance to: Investigate" | Step 1 — "Investigation task generated for 4 domain(s)" |

**Do NOT** advance past step 2 during the demo — the "acknowledged" and "closed" steps are less visually interesting and waste time.

---

## Appendix: Q&A Prepared Answers

| Judge Question | Answer |
|----------------|--------|
| "Is this real-time?" | "CAMS data has a 3–4 hour latency. We say 'recent observations,' not 'real-time.' The forecasts are forward-looking from the most recent available data." |
| "How accurate are the forecasts?" | "The 1-hour model has an R² of 0.975. The 24-hour model is 0.703. We show confidence labels — High, Moderate, Lower — tied to actual validation. We don't claim certainty we don't have." |
| "Does this detect pollution sources?" | "No. It shows investigation signals — weather conditions that historically correlate with certain pollution types. Every signal says 'not a confirmed source attribution.'" |
| "Will the government use this?" | "This is a prototype intelligence layer. It's designed to sit alongside Punjab's existing monitoring systems, not replace them. The Response Orchestrator is a simulation, not a live dispatch system." |
| "What's different from IQAir or WAQI?" | "Two things: prediction accountability — we track whether every forecast was right — and the Response Orchestrator, which turns episode detection into structured investigation signals with honest caveats. No other platform does either." |
| "Is this just a dashboard?" | "No. A dashboard shows current state. This predicts future state, detects episodes, generates investigation signals, and tracks whether its own predictions were accurate. It's an intelligence layer." |
