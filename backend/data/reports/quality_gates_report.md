# Quality Gate Report

**Generated:** 2026-08-15T16:03:37.153179+00:00
## ❌ Verdict: NOT_MODEL_READY

The dataset does NOT pass all quality gates.

**Blocking failures:**
  - `TARGET_AVAILABILITY`

**Summary:** 9/10 passed, 1 failed, 0 warnings

## Gate Results

| Gate | Status | Severity | Message |
|------|--------|----------|---------|
| DATA_SUFFICIENCY | ✅ PASS | error | Total: 1,308,659 (min 100,000), min per param: 35,315 (min 10,000) |
| TEMPORAL_COVERAGE | ✅ PASS | error | Coverage: 84,335 hours (min 8,760) |
| TARGET_AVAILABILITY | ❌ FAIL | error | PM2.5 coverage: 41.92% (min 80%) |
| MISSINGNESS | ✅ PASS | error | Missingness: 18.33% (max 30%) |
| TEMPORAL_CONTINUITY | ✅ PASS | error | Longest gap: 3h (max 72h) |
| DUPLICATE_INTEGRITY | ✅ PASS | error | Duplicates found: 0 |
| PROVENANCE_COMPLETENESS | ✅ PASS | error | Provenance coverage: 100.00% |
| PARAMETER_COMPLETENESS | ✅ PASS | error | Parameters: 19 total (13 weather, 6 AQ) |
| VALUE_VALIDITY | ✅ PASS | error | Invalid values: 0 |
| SEASONAL_REPRESENTATION | ✅ PASS | error | Seasons covered: 5 (min 2) |
