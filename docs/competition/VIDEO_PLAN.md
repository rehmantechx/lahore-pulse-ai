# Video Plan — Lahore Pulse AI

**Purpose:** Plan for competition demo video  
**Target Duration:** 3–5 minutes  
**Format:** Screen recording with narration  

---

## Video Structure

### Section 1: Opening (0:00–0:30)

**Visual:** Dashboard page, full view  
**Narration:**
> "Lahore Pulse AI is a predictive city-intelligence platform that forecasts PM2.5 air quality concentrations 1 to 24 hours ahead for Lahore, Pakistan. It uses real environmental data from the Copernicus Atmosphere Monitoring Service and validated statistical models."

**Action:** Show the Dashboard with all forecast cards visible

---

### Section 2: Data Pipeline (0:30–1:00)

**Visual:** Scroll to Data Collection section  
**Narration:**
> "The system ingests real data — over 1.3 million hourly PM2.5 observations spanning 2023 to 2025. The data pipeline runs automatically, refreshing every 30 minutes. Every observation is traceable to its source."

**Action:** Point to data source indicator, show observation count

---

### Section 3: Multi-Horizon Forecasting (1:00–2:00)

**Visual:** Forecast cards with technical details expanded  
**Narration:**
> "We forecast at five time horizons: 1 hour, 3 hours, 6 hours, 12 hours, and 24 hours. Each uses a different algorithm optimized for that timeframe. The 1-hour model uses Ridge Regression with an R-squared of 0.975. The 24-hour model has greater uncertainty — we label it 'lower confidence' instead of hiding this."

**Action:** Click "Show technical details" on each card, point to algorithm names and confidence labels

---

### Section 4: Explainability (2:00–2:45)

**Visual:** Model Transparency section expanded  
**Narration:**
> "Every prediction is explainable. The Model Transparency section shows exactly which algorithm was used, its validation metrics, and feature importance. Users can see how predictions are generated — no black box."

**Action:** Expand ModelTransparency, show algorithm, MAE, R², feature importance

---

### Section 5: Interactive Map (2:45–3:15)

**Visual:** Leaflet map with station markers  
**Narration:**
> "The map shows monitoring stations across Lahore with their latest PM2.5 readings. Citizens can see air quality in their area and make informed decisions about outdoor activities."

**Action:** Hover over station markers, show PM2.5 values

---

### Section 6: Closing (3:15–3:30)

**Visual:** Return to Dashboard overview  
**Narration:**
> "Lahore Pulse AI demonstrates that honest, explainable predictive city intelligence is achievable with open data and proven statistical methods. We show real uncertainty, not false confidence. Thank you."

**Action:** Show full Dashboard, fade out

---

## Recording Setup

### Tools
- **Screen recording:** OBS Studio (free) or Windows Game Bar (Win+G)
- **Audio:** Built-in microphone or external USB mic
- **Resolution:** 1920×1080 (Full HD)
- **Frame rate:** 30 fps

### Preparation
1. Start backend and frontend
2. Close unnecessary applications
3. Hide browser bookmarks bar
4. Set browser to full-screen mode (F11)
5. Test audio levels
6. Do a practice run

### Recording Process
1. Open Dashboard page
2. Start recording
3. Follow the script above
4. Pause between sections if needed
5. Stop recording
6. Review and re-record if needed

---

## Post-Production

### Editing
- Trim unnecessary pauses
- Add subtle zoom on key elements (forecast cards, model transparency)
- Add text overlays for key metrics (R² = 0.975)
- Add background music (optional, keep subtle)

### Export Settings
- Format: MP4 (H.264)
- Resolution: 1920×1080
- Frame rate: 30 fps
- Bitrate: 5–10 Mbps
- Audio: AAC, 128 kbps

### File Naming
```
docs/competition/video/
├── lahore_pulse_ai_demo.mp4
├── lahore_pulse_ai_demo_raw.mp4
└── lahore_pulse_ai_demo_subtitles.srt
```

---

## Subtitles

Create SRT subtitle file for accessibility:

```srt
1
00:00:00,000 --> 00:00:05,000
Lahore Pulse AI is a predictive city-intelligence platform

2
00:00:05,000 --> 00:00:10,000
that forecasts PM2.5 air quality concentrations

3
00:00:10,000 --> 00:00:15,000
1 to 24 hours ahead for Lahore, Pakistan
```

---

## Quality Checklist

- [ ] Video is 3–5 minutes long
- [ ] Audio is clear and audible
- [ ] Screen is 1920×1080 resolution
- [ ] All UI elements are readable
- [ ] No personal information visible
- [ ] No browser bookmarks or extensions
- [ ] Data is loaded (not empty states)
- [ ] Subtitles are accurate
- [ ] File size is reasonable (<100MB)

---

## Upload

| Platform | Privacy | Notes |
|----------|---------|-------|
| YouTube | Unlisted | Share link with judges |
| Google Drive | Link sharing | Backup option |
| Devpost | Direct upload | If supported |
