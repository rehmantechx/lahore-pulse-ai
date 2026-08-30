# The Solution: Lahore+

## What Lahore+ Does

Lahore+ is an **environmental intelligence system** that converts air quality monitoring data into actionable investigation recommendations for government response officers.

It is **not** another AQI dashboard. It does not just show numbers. It answers a specific operational question:

> **"Given this pollution event, where should we investigate first, and why?"**

## How It Works — Step by Step

### 1. Detect Abnormal Events (Deterministic)
The system continuously monitors PM2.5 readings from Lahore's air quality stations. When readings deviate from normal patterns for a given station and time of day, it classifies the event as an **episode** — a period of abnormal pollution that warrants investigation.

This classification is **deterministic** — it follows explicit rules, not AI inference.

### 2. Assemble Environmental Context
For each detected episode, the system gathers:
- **Wind data**: speed and direction from nearby weather stations
- **Historical patterns**: what happened during similar past episodes
- **Geographic context**: station locations, neighborhood boundaries, nearby landmarks

This data is assembled from real public sources and is **directly observed**.

### 3. Generate Investigation Hypotheses (AI — Constrained)
An AI model generates **constrained investigation hypotheses** based on the assembled evidence:
- Directional estimates (NW, SE, etc. — not precise addresses)
- Confidence levels (High / Medium / Low)
- Evidence chains explaining what the AI observed and what it inferred

The AI is **explicitly constrained** — it cannot claim to identify specific polluters, and its hypotheses are clearly labeled as AI-generated, not facts.

### 4. Predict Exposure Geometry
Using wind direction, speed, and station geometry, the system predicts the **approximate area** where pollution exposure is most likely. This is shown as a directional wedge on the map — not a precise boundary.

### 5. Recommend Investigation Priority
The system generates a ranked list of investigation areas with:
- Priority level (High / Medium / Low)
- Confidence percentage
- One-paragraph reasoning
- Evidence summary

Officers review these recommendations and decide where to deploy.

### 6. Record Human Verification
When officers return from field investigation, they report what they actually found. The system records:
- Whether the investigation was useful
- Whether they found an active pollution source
- What they observed on the ground

This creates an **accountability loop** — the system's recommendations are compared against reality.

### 7. Learn Over Time
The system tracks whether past investigation recommendations were useful. Over time, this builds an evidence base showing:
- How often the system's recommendations are helpful
- What types of pollution sources are most common
- Which investigation areas have recurring problems

## Key Design Principles

- **Transparency**: Every output is labeled with its data source — observed, deterministic, AI-generated, or human-verified
- **Non-overclaiming**: The system never claims to know the source of pollution. It generates hypotheses for humans to investigate.
- **Accountability**: Human officers confirm or reject every recommendation. The system learns from both successes and failures.
- **Decision support, not decision making**: The system recommends. Humans decide.
