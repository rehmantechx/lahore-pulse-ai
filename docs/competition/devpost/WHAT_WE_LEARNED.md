# What We Learned — Lahore Pulse AI

## Technical Learnings

### 1. Feature Engineering > Model Complexity
We discovered that well-engineered features (PM2.5 lags, rolling statistics, temporal encodings) matter more than model complexity. Ridge Regression with 41 hand-crafted features outperformed more complex models on the 1-hour horizon.

**Key insight:** 41 features capturing temporal patterns and historical PM2.5 behavior provide strong predictive power without overfitting.

### 2. Walk-Forward Validation is Essential
Standard train/test splits can be misleading for time-series data. Walk-forward validation (training on historical data, testing on future data) revealed the true performance degradation at longer horizons.

**Key insight:** The gap between validation R² (0.975) and walk-forward R² (0.966) for 1-hour predictions shows mild overfitting that standard splits would miss.

### 3. Algorithm Selection Should Be Per-Horizon
No single algorithm performs best across all time horizons. Ridge Regression excels at 1h and 24h, while HistGradientBoosting performs best at 3h, 6h, and 12h.

**Key insight:** Matching algorithm to horizon through systematic comparison yields better results than using one "best" model everywhere.

### 4. Honest Uncertainty Builds Trust
Labeling 24-hour predictions as "lower confidence" (R²=0.703) instead of claiming high accuracy actually increased user trust during testing. People appreciated knowing when predictions were less reliable.

**Key insight:** Transparency about limitations is a feature, not a weakness.

### 5. SQLite is Surprisingly Capable
A 672MB SQLite database with 1.31M records handles all our queries in under 200ms with proper indexing. It's sufficient for a demo and even small-scale production.

**Key insight:** Don't reach for PostgreSQL until you actually need its features.

---

## Design Learnings

### 6. Constraints Drive Creativity
The "no purple, no neon, no glassmorphism" constraint forced us to create a clean, professional design system. The result looks more like a real enterprise product than a typical hackathon prototype.

**Key insight:** Design constraints are gifts, not limitations.

### 7. Three Pages is Enough
Dashboard (public), Citizen (health guidance), and Government (policy support) cover the main use cases without overwhelming users. Each page has a clear purpose and audience.

**Key insight:** Focused pages with clear audiences are better than one complex page trying to serve everyone.

---

## Process Learnings

### 8. Phases Prevent Scope Creep
Breaking the project into 9 phases with clear deliverables prevented feature creep. Each phase had a defined scope, test criteria, and completion report.

**Key insight:** Structured development phases work better than ad-hoc feature additions.

### 9. Tests Are Documentation
676 tests serve as executable documentation of expected behavior. When something broke, tests caught it immediately. When onboarding new context, tests showed what mattered.

**Key insight:** Tests aren't just quality assurance — they're living documentation.

### 10. Data Provenance Matters
Tracking every observation back to its source (CAMS), collection time, and quality status built confidence in the system's outputs. Judges and users could verify data authenticity.

**Key insight:** In an era of AI hype, provenance is a competitive advantage.

---

## What We'd Do Differently

1. **Add baseline comparison metrics** — Persistence/naive model comparison would strengthen claims
2. **Implement OpenAQ earlier** — Ground-level validation would improve credibility
3. **Start with data exploration** — Feature engineering took longer than expected
4. **Add authentication earlier** — Open API was fine for demo but needed for production
5. **Use PostgreSQL from the start** — SQLite works but limits scalability
