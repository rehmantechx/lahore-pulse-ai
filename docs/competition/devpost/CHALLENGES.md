# Challenges We Faced — Lahore Pulse AI

## Challenge 1: Data Source Reliability

**Problem:** Initial plan was to use OpenAQ for ground-level sensor data, but OpenAQ's Lahore coverage was sparse and inconsistent.

**Solution:** Pivoted to Copernicus Atmosphere Monitoring Service (CAMS) reanalysis data, which provides consistent hourly PM2.5 estimates for the Lahore region. Built a robust data pipeline that handles API failures gracefully.

**Impact:** Secured 1.31M+ reliable observations spanning 2023–2025, forming a solid foundation for model training.

---

## Challenge 2: Model Selection Without Overfitting

**Problem:** With 41 features and limited domain-specific training data, complex models (neural networks, deep learning) showed signs of overfitting during walk-forward validation.

**Solution:** Systematically compared Ridge Regression, Random Forest, and HistGradientBoosting across all 5 horizons. Found that Ridge Regression excels at short-term (1h, 24h) while HistGradientBoosting performs best at medium-term (3h, 6h, 12h). Selected per-horizon optimal algorithms based on validation metrics, not model complexity.

**Impact:** Achieved R² = 0.975 for 1-hour predictions without overfitting, with honest degradation to R² = 0.703 for 24-hour predictions.

---

## Challenge 3: Honest Uncertainty Communication

**Problem:** Most hackathon projects overstate their accuracy. We needed to communicate that 24-hour predictions are inherently less reliable than 1-hour predictions without undermining confidence in the system.

**Solution:** Designed a confidence labeling system (high, moderate, lower) tied directly to validation metrics. Built ModelTransparency and TechnicalDetail UI components that show exact algorithm names, MAE values, and R² scores. Users see "lower confidence" for 24h predictions — we don't hide this.

**Impact:** Built a system that earns trust through honesty rather than false certainty.

---

## Challenge 4: Competition Design Constraints

**Problem:** The competition required a professional, enterprise-grade UI. Early prototypes used purple gradients and neon effects, which violated the design constraints.

**Solution:** Established hard design rules: no purple gradients, no neon, no glowing, no glassmorphism, no AI-themed decoration. Created a clean, professional design system using standard colors and typography. Applied these rules consistently across all 3 pages.

**Impact:** Professional UI that looks like a real enterprise product, not a hackathon prototype.

---

## Challenge 5: Windows Development Environment

**Problem:** The team develops on Windows, which has different path handling, process management, and tool compatibility than Linux/macOS.

**Solution:** Created Windows-specific commands for uvicorn (`--app-dir`), Vite (`Push-Location`), and Vitest (`--no-file-parallelism`). Documented all Windows-specific setup steps.

**Impact:** Full development and testing capability on Windows without requiring WSL or Docker.

---

## Challenge 6: Database Size and Performance

**Problem:** 1.31M observations resulted in a 672MB SQLite database, which could cause slow queries during demo.

**Solution:** Optimized SQL queries with proper indexes, used window functions (ROW_NUMBER) for efficient latest-per-station queries, and implemented data caching in the API layer.

**Impact:** All API endpoints respond in under 200ms, even with the full dataset loaded.

---

## Challenge 7: Auto-Refresh Without Blocking

**Problem:** The data pipeline needs to refresh every 30 minutes, but a naive implementation would block the API during refresh.

**Solution:** Implemented asyncio background task using FastAPI's lifespan context manager. The refresh runs in a separate coroutine, allowing the API to continue serving requests during data updates.

**Impact:** Seamless background data refresh with zero API downtime.

---

## What We'd Do Differently

1. **Start with data exploration earlier** — Feature engineering took longer than expected
2. **Add baseline comparison metrics** — Persistence/naive model comparison would strengthen claims
3. **Implement OpenAQ integration** — Ground-level validation would improve credibility
4. **Add authentication** — Current API is open for demo but needs auth for production
5. **Use PostgreSQL** — SQLite works for demo but wouldn't scale to multi-city deployment
