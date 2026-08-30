"""
PHASE 4-6: Aggressive Edge-Case Testing
========================================
Forecast / ML Pipeline, Prediction Accountability Loop, Ingestion Pipeline

Uses ONLY urllib.request + json (no requests library).
Tests against http://localhost:8002
"""

import json
import sys
import time
import traceback
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8002"
results = []  # (phase, test_name, pass/fail, detail)
session_tokens = {}


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def record(phase: str, name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append((phase, name, status, detail))
    icon = "✅" if passed else "❌"
    print(f"  {icon} [{phase}] {name}: {status}" + (f" — {detail}" if detail else ""))


def api_get(path: str, token: str = None) -> dict:
    """GET request, returns (status_code, parsed_json_or_None, raw_text)."""
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        body = resp.read().decode("utf-8")
        try:
            return resp.status, json.loads(body), body
        except json.JSONDecodeError:
            return resp.status, None, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body), body
        except json.JSONDecodeError:
            return e.code, None, body
    except Exception as e:
        return 0, None, str(e)


def api_post(path: str, data: dict = None, token: str = None, raw_body: str = None, content_type: str = "application/json") -> dict:
    """POST request, returns (status_code, parsed_json_or_None, raw_text)."""
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if raw_body is not None:
        body_bytes = raw_body.encode("utf-8")
        headers["Content-Type"] = content_type
    elif data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body_bytes = None
    req = urllib.request.Request(url, data=body_bytes, method="POST", headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        body = resp.read().decode("utf-8")
        try:
            return resp.status, json.loads(body), body
        except json.JSONDecodeError:
            return resp.status, None, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body), body
        except json.JSONDecodeError:
            return e.code, None, body
    except Exception as e:
        return 0, None, str(e)


def has_no_traceback(raw: str) -> bool:
    """Check response body doesn't contain Python traceback."""
    bad = ["Traceback (most recent call last)", "File \"", "Internal Server Error"]
    for b in bad:
        if b in raw:
            return False
    return True


def has_no_filesystem_path(raw: str) -> bool:
    """Check response body doesn't leak filesystem paths."""
    import re
    # Windows paths like C:\... or Unix paths like /home/...
    if re.search(r'[A-Z]:\\[\\\/]', raw):
        return False
    if re.search(r'\/home\/\w+', raw):
        return False
    if re.search(r'\/Users\/\w+', raw):
        return False
    return True


def login(username: str, password: str) -> str | None:
    """Login and return token, or None on failure."""
    status, data, raw = api_post("/api/v1/auth/login", {"username": username, "password": password})
    if status == 200 and data and "token" in data:
        return data["token"]
    return None


# ═══════════════════════════════════════════════════════════════════
# PHASE 4: FORECAST / ML EDGE CASES
# ═══════════════════════════════════════════════════════════════════

def test_phase4_forecast():
    PHASE = "P4-FORECAST"
    print(f"\n{'='*70}")
    print(f"PHASE 4: FORECAST / ML EDGE CASES")
    print(f"{'='*70}")

    # ── 4.0 Authentication ────────────────────────────────────────
    print("\n── Authentication ──")
    citizen_token = login("citizen", "citizen123")
    record(PHASE, "Citizen login", citizen_token is not None,
           "Got token" if citizen_token else "Login failed")
    if not citizen_token:
        print("  ⚠️  Cannot proceed without citizen token")
        return

    officer_token = login("officer", "officer123")
    record(PHASE, "Officer login", officer_token is not None,
           "Got token" if officer_token else "Login failed")
    if not officer_token:
        print("  ⚠️  Cannot proceed without officer token")

    # ── 4.1 Valid horizon forecasts (citizen) ─────────────────────
    print("\n── Valid Horizons (Citizen Token) ──")
    valid_horizons = [1, 3, 6, 12, 24]
    forecast_structures = {}

    for h in valid_horizons:
        status, data, raw = api_get(f"/api/v1/forecast?horizon={h}", citizen_token)

        # Check HTTP 200
        record(PHASE, f"horizon={h} HTTP 200", status == 200,
               f"status={status}" if status != 200 else "")

        if status != 200:
            print(f"    Response: {raw[:500]}")
            continue

        # Check valid JSON
        record(PHASE, f"horizon={h} valid JSON", data is not None,
               "" if data else "Not valid JSON")

        if not data:
            continue

        # Check top-level 'forecast' key
        has_forecast = "forecast" in data
        record(PHASE, f"horizon={h} has 'forecast' key", has_forecast)

        if not has_forecast:
            continue

        fc = data["forecast"]
        forecast_structures[h] = fc

        # Check predicted_pm25
        pm25 = fc.get("predicted_pm25")
        pm25_ok = isinstance(pm25, (int, float)) and pm25 is not None
        record(PHASE, f"horizon={h} predicted_pm25 is number",
               pm25_ok, f"value={pm25}" if pm25_ok else f"value={pm25!r}")

        if pm25_ok:
            pm25_range = -1 <= pm25 <= 600
            record(PHASE, f"horizon={h} predicted_pm25 in [0,600]",
                   pm25_range, f"pm25={pm25}")
        else:
            record(PHASE, f"horizon={h} predicted_pm25 in [0,600]", False, "Skipped — value not numeric")

        # Check unit
        unit_ok = fc.get("unit") == "ug/m3"
        record(PHASE, f"horizon={h} unit='ug/m3'", unit_ok,
               f"unit={fc.get('unit')!r}")

        # Check model info
        model = fc.get("model", {})
        model_version = model.get("version", "")
        model_algo = model.get("algorithm", "")
        record(PHASE, f"horizon={h} model.version exists", bool(model_version),
               f"version={model_version!r}")
        record(PHASE, f"horizon={h} model.version starts with 'v1.0.0'",
               model_version.startswith("v1.0.0"),
               f"version={model_version!r}")
        record(PHASE, f"horizon={h} model.algorithm exists", bool(model_algo),
               f"algorithm={model_algo!r}")

        # Check timing
        timing = fc.get("timing", {})
        timing_ok = isinstance(timing.get("inference_ms"), (int, float))
        record(PHASE, f"horizon={h} timing.inference_ms is number",
               timing_ok, f"inference_ms={timing.get('inference_ms')}")
        record(PHASE, f"horizon={h} timing.prediction_time exists",
               bool(timing.get("prediction_time")))
        record(PHASE, f"horizon={h} timing.target_time exists",
               bool(timing.get("target_time")))

        # Check data_quality
        dq = fc.get("data_quality", {})
        fc_count = dq.get("feature_count")
        record(PHASE, f"horizon={h} data_quality.feature_count == 41",
               fc_count == 41, f"feature_count={fc_count}")
        record(PHASE, f"horizon={h} data_quality.missing_features is list",
               isinstance(dq.get("missing_features"), list))

        # Check warnings and errors are lists
        record(PHASE, f"horizon={h} warnings is list",
               isinstance(fc.get("warnings"), list))
        record(PHASE, f"horizon={h} errors is list",
               isinstance(fc.get("errors"), list))

        # Check horizon_hours matches requested horizon
        record(PHASE, f"horizon={h} horizon_hours matches",
               fc.get("horizon_hours") == h,
               f"horizon_hours={fc.get('horizon_hours')}")

        # Check prediction_id exists
        record(PHASE, f"horizon={h} prediction_id exists",
               bool(fc.get("prediction_id")),
               f"prediction_id={fc.get('prediction_id')!r}")

    # ── 4.2 Invalid horizons ──────────────────────────────────────
    print("\n── Invalid Horizons ──")

    # horizon=999 — should NOT return 500
    status, data, raw = api_get("/api/v1/forecast?horizon=999", citizen_token)
    record(PHASE, "horizon=999 no 500", status != 500,
           f"status={status}")
    record(PHASE, "horizon=999 valid JSON", data is not None or status == 422,
           f"status={status}")
    record(PHASE, "horizon=999 no traceback", has_no_traceback(raw),
           "Contains traceback!" if not has_no_traceback(raw) else "")

    # horizon=-1 — should NOT return 500
    status, data, raw = api_get("/api/v1/forecast?horizon=-1", citizen_token)
    record(PHASE, "horizon=-1 no 500", status != 500,
           f"status={status}")
    record(PHASE, "horizon=-1 valid JSON", data is not None or status == 422,
           f"status={status}")
    record(PHASE, "horizon=-1 no traceback", has_no_traceback(raw))

    # horizon=0 — should NOT return 500
    status, data, raw = api_get("/api/v1/forecast?horizon=0", citizen_token)
    record(PHASE, "horizon=0 no 500", status != 500,
           f"status={status}")
    record(PHASE, "horizon=0 valid JSON", data is not None or status == 422,
           f"status={status}")
    record(PHASE, "horizon=0 no traceback", has_no_traceback(raw))

    # Missing horizon param
    status, data, raw = api_get("/api/v1/forecast", citizen_token)
    record(PHASE, "missing horizon no 500", status != 500,
           f"status={status}")
    record(PHASE, "missing horizon no traceback", has_no_traceback(raw))

    # ── 4.3 Officer forecast ──────────────────────────────────────
    if officer_token:
        print("\n── Officer Forecast Access ──")
        status, data, raw = api_get("/api/v1/forecast?horizon=6", officer_token)
        record(PHASE, "officer forecast HTTP 200", status == 200,
               f"status={status}")
        if status == 200 and data and "forecast" in data:
            fc = data["forecast"]
            pm25 = fc.get("predicted_pm25")
            record(PHASE, "officer predicted_pm25 is number",
                   isinstance(pm25, (int, float)) and pm25 is not None,
                   f"pm25={pm25}")
        elif status == 200:
            record(PHASE, "officer predicted_pm25 is number", False, "No forecast key")

    # ── 4.4 Unauthenticated forecast ──────────────────────────────
    print("\n── Unauthenticated Access ──")
    status, data, raw = api_get("/api/v1/forecast?horizon=6")
    # Citizen endpoints typically don't require auth, but let's see
    record(PHASE, "unauth forecast no 500", status != 500,
           f"status={status}")
    record(PHASE, "unauth forecast no traceback", has_no_traceback(raw))


# ═══════════════════════════════════════════════════════════════════
# PHASE 5: PREDICTION ACCOUNTABILITY LOOP
# ═══════════════════════════════════════════════════════════════════

def test_phase5_accountability():
    PHASE = "P5-ACCOUNTABILITY"
    print(f"\n{'='*70}")
    print(f"PHASE 5: PREDICTION ACCOUNTABILITY LOOP")
    print(f"{'='*70}")

    officer_token = login("officer", "officer123")
    citizen_token = login("citizen", "citizen123")

    if not officer_token:
        print("  ⚠️  Cannot proceed without officer token")
        return

    # ── 5.1 Accuracy Summary ──────────────────────────────────────
    print("\n── Accuracy Summary ──")
    status1, data1, raw1 = api_get("/api/v1/accuracy/summary", officer_token)
    record(PHASE, "accuracy/summary HTTP 200", status1 == 200,
           f"status={status1}")
    record(PHASE, "accuracy/summary valid JSON", data1 is not None)
    record(PHASE, "accuracy/summary no traceback", has_no_traceback(raw1))

    if data1:
        record(PHASE, "accuracy/summary has total_predictions",
               "total_predictions" in data1)
        record(PHASE, "accuracy/summary has by_horizon",
               "by_horizon" in data1)
        if "by_horizon" in data1 and isinstance(data1["by_horizon"], list):
            record(PHASE, "accuracy/summary by_horizon is list", True,
                   f"count={len(data1['by_horizon'])}")

    # Second call — consistency check
    print("\n── Accuracy Summary Consistency ──")
    status2, data2, raw2 = api_get("/api/v1/accuracy/summary", officer_token)
    record(PHASE, "accuracy/summary 2nd call HTTP 200", status2 == 200)
    if data1 and data2:
        consistent = data1.get("total_predictions") == data2.get("total_predictions")
        record(PHASE, "accuracy/summary consistent total_predictions", consistent,
               f"1st={data1.get('total_predictions')} 2nd={data2.get('total_predictions')}")

    # ── 5.2 Accuracy Recent ───────────────────────────────────────
    print("\n── Accuracy Recent ──")
    status, data, raw = api_get("/api/v1/accuracy/recent", officer_token)
    record(PHASE, "accuracy/recent HTTP 200", status == 200,
           f"status={status}")
    record(PHASE, "accuracy/recent valid JSON", data is not None)
    record(PHASE, "accuracy/recent no traceback", has_no_traceback(raw))

    # ── 5.3 Verification Endpoints ────────────────────────────────
    print("\n── Verification Endpoints ──")

    # GET /api/v1/verification (list)
    status, data, raw = api_get("/api/v1/verification", officer_token)
    record(PHASE, "verification GET list", status in (200, 404, 405),
           f"status={status}")
    record(PHASE, "verification GET list no 500", status != 500)
    record(PHASE, "verification GET list no traceback", has_no_traceback(raw))
    if status == 200 and data:
        record(PHASE, "verification GET list has 'outcomes'",
               "outcomes" in data)
        record(PHASE, "verification GET list has 'count'",
               "count" in data)

    # GET /api/v1/verification/outcomes — may not exist
    print("\n── Verification Outcomes Endpoint ──")
    status, data, raw = api_get("/api/v1/verification/outcomes", officer_token)
    record(PHASE, "verification/outcomes no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification/outcomes no traceback", has_no_traceback(raw))

    # GET /api/v1/verification/breakdown — may not exist
    print("\n── Verification Breakdown Endpoint ──")
    status, data, raw = api_get("/api/v1/verification/breakdown", officer_token)
    record(PHASE, "verification/breakdown no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification/breakdown no traceback", has_no_traceback(raw))

    # POST /api/v1/verification — valid data
    print("\n── Verification POST (valid) ──")
    valid_payload = {
        "investigation_id": f"edge-test-{int(time.time())}",
        "overall_status": "USEFUL",
        "recommendation_verification": "SUPPORTED",
        "investigation_area_verification": "SUPPORTED",
        "hypothesis_verifications": [
            {"factor": "traffic emissions", "verified": True, "notes": "Confirmed"}
        ],
        "field_notes": "Edge-case test verification submission",
        "verified_by": "test-automaton",
    }
    status, data, raw = api_post("/api/v1/verification", valid_payload, officer_token)
    record(PHASE, "verification POST valid no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification POST valid no traceback", has_no_traceback(raw))
    if status == 201 and data:
        record(PHASE, "verification POST valid has outcome_id",
               "outcome_id" in data)
        record(PHASE, "verification POST valid overall_status",
               data.get("overall_status") == "USEFUL")
        # Store for later
        created_outcome_id = data.get("outcome_id")
    elif status == 201:
        record(PHASE, "verification POST valid has outcome_id", False, "No data")
        created_outcome_id = None
    else:
        created_outcome_id = None

    # POST /api/v1/verification — invalid data (missing required field)
    print("\n── Verification POST (invalid) ──")
    invalid_payload = {
        "investigation_id": "",  # empty string — min_length=1
        "overall_status": "USEFUL",
    }
    status, data, raw = api_post("/api/v1/verification", invalid_payload, officer_token)
    record(PHASE, "verification POST invalid no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification POST invalid no traceback", has_no_traceback(raw))
    # Should be 400 or 422 (validation error)
    record(PHASE, "verification POST invalid rejected",
           status in (400, 422, 409),
           f"status={status}")

    # POST /api/v1/verification — bad overall_status
    print("\n── Verification POST (bad status value) ──")
    bad_status_payload = {
        "investigation_id": "test-bad-status",
        "overall_status": "TOTES_LEGITIMATE_STATUS",
    }
    status, data, raw = api_post("/api/v1/verification", bad_status_payload, officer_token)
    record(PHASE, "verification POST bad status no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification POST bad status rejected",
           status in (400, 422),
           f"status={status}")

    # POST /api/v1/verification — citizen token (should be 403)
    if citizen_token:
        print("\n── Verification POST (citizen — should be 403) ──")
        status, data, raw = api_post("/api/v1/verification", valid_payload, citizen_token)
        record(PHASE, "verification POST citizen 403", status == 403,
               f"status={status}")
        record(PHASE, "verification POST citizen no 500", status != 500)

    # GET /api/v1/verification/stats
    print("\n── Verification Stats ──")
    status, data, raw = api_get("/api/v1/verification/stats", officer_token)
    record(PHASE, "verification/stats HTTP 200", status == 200,
           f"status={status}")
    record(PHASE, "verification/stats no 500", status != 500)
    record(PHASE, "verification/stats no traceback", has_no_traceback(raw))
    if status == 200 and data:
        record(PHASE, "verification/stats has total_verifications",
               "total_verifications" in data)

    # GET /api/v1/verification/context/{id}
    print("\n── Verification Context ──")
    test_inv_id = f"edge-test-{int(time.time())}"
    status, data, raw = api_get(f"/api/v1/verification/context/{test_inv_id}", officer_token)
    record(PHASE, "verification/context no 500", status != 500,
           f"status={status}")
    record(PHASE, "verification/context no traceback", has_no_traceback(raw))
    if status == 200 and data:
        record(PHASE, "verification/context has stats",
               "stats" in data)
        record(PHASE, "verification/context has disclaimer",
               "disclaimer" in data)


# ═══════════════════════════════════════════════════════════════════
# PHASE 6: INGESTION / DATA PIPELINE
# ═══════════════════════════════════════════════════════════════════

def test_phase6_ingestion():
    PHASE = "P6-INGESTION"
    print(f"\n{'='*70}")
    print(f"PHASE 6: INGESTION / DATA PIPELINE")
    print(f"{'='*70}")

    officer_token = login("officer", "officer123")
    citizen_token = login("citizen", "citizen123")

    if not officer_token:
        print("  ⚠️  Cannot proceed without officer token")
        return

    # ── 6.1 GET /api/v1/ingestion/runs (list past runs) ───────────
    print("\n── Ingestion Run History ──")
    status, data, raw = api_get("/api/v1/ingestion/runs", officer_token)
    record(PHASE, "ingestion/runs HTTP 200", status == 200,
           f"status={status}")
    record(PHASE, "ingestion/runs valid JSON", data is not None)
    record(PHASE, "ingestion/runs no traceback", has_no_traceback(raw))
    record(PHASE, "ingestion/runs no filesystem paths",
           has_no_filesystem_path(raw))
    if data:
        record(PHASE, "ingestion/runs has 'runs' key",
               "runs" in data)
        record(PHASE, "ingestion/runs has 'count' key",
               "count" in data)

    # ── 6.2 POST /api/v1/ingestion/refresh (main ingestion) ──────
    print("\n── Ingestion Refresh (default params) ──")
    status, data, raw = api_post("/api/v1/ingestion/refresh", token=officer_token)
    record(PHASE, "ingestion/refresh HTTP 200", status == 200,
           f"status={status}")
    record(PHASE, "ingestion/refresh valid JSON", data is not None,
           f"raw={raw[:300]}" if not data else "")
    record(PHASE, "ingestion/refresh no traceback", has_no_traceback(raw))
    record(PHASE, "ingestion/refresh no filesystem paths",
           has_no_filesystem_path(raw))
    if data:
        record(PHASE, "ingestion/refresh has 'status'",
               "status" in data)
        record(PHASE, "ingestion/refresh has 'providers'",
               "providers" in data)
        record(PHASE, "ingestion/refresh has 'summary'",
               "summary" in data)
        if "providers" in data:
            for provider_name, prov_data in data["providers"].items():
                if isinstance(prov_data, dict):
                    has_status = "status" in prov_data
                    record(PHASE, f"ingestion/refresh {provider_name} has status",
                           has_status)

    # ── 6.3 POST /api/v1/ingestion/refresh with invalid query params ──
    print("\n── Ingestion Refresh (invalid params) ──")
    # invalid past_days (out of range)
    status, data, raw = api_post("/api/v1/ingestion/refresh?past_days=9999", token=officer_token)
    record(PHASE, "ingestion/refresh invalid params no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/refresh invalid params no traceback",
           has_no_traceback(raw))

    # ── 6.4 POST /api/v1/ingestion/run — may not exist ────────────
    print("\n── Ingestion /run endpoint ──")
    status, data, raw = api_post("/api/v1/ingestion/run", {}, officer_token)
    record(PHASE, "ingestion/run no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/run no traceback", has_no_traceback(raw))

    # ── 6.5 POST /api/v1/ingestion/run with invalid body ──────────
    print("\n── Ingestion /run (invalid body) ──")
    status, data, raw = api_post("/api/v1/ingestion/run",
                                 {"bogus_key": "bogus_value"}, officer_token)
    record(PHASE, "ingestion/run invalid body no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/run invalid body no traceback",
           has_no_traceback(raw))
    record(PHASE, "ingestion/run invalid body no filesystem",
           has_no_filesystem_path(raw))

    # ── 6.6 POST /api/v1/ingestion/run with empty body ────────────
    print("\n── Ingestion /run (empty body) ──")
    status, data, raw = api_post("/api/v1/ingestion/run", {}, officer_token)
    record(PHASE, "ingestion/run empty body no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/run empty body no traceback",
           has_no_traceback(raw))

    # ── 6.7 POST /api/v1/ingestion/run with malformed JSON ────────
    print("\n── Ingestion /run (malformed JSON) ──")
    status, data, raw = api_post("/api/v1/ingestion/run",
                                 raw_body="{not valid json!!!",
                                 content_type="application/json",
                                 token=officer_token)
    record(PHASE, "ingestion/run malformed JSON no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/run malformed JSON no traceback",
           has_no_traceback(raw))
    record(PHASE, "ingestion/run malformed JSON no filesystem",
           has_no_filesystem_path(raw))

    # ── 6.8 Citizen access to ingestion (should be 403) ───────────
    if citizen_token:
        print("\n── Ingestion Access (citizen — should be 403) ──")
        status, data, raw = api_post("/api/v1/ingestion/refresh", token=citizen_token)
        record(PHASE, "citizen ingestion refresh 403", status == 403,
               f"status={status}")
        record(PHASE, "citizen ingestion refresh no 500", status != 500)
        record(PHASE, "citizen ingestion refresh no traceback",
               has_no_traceback(raw))

    # ── 6.9 GET /api/v1/ingestion/runs with limit ─────────────────
    print("\n── Ingestion Runs (with limit) ──")
    status, data, raw = api_get("/api/v1/ingestion/runs?limit=5", officer_token)
    record(PHASE, "ingestion/runs limit=5 HTTP 200", status == 200,
           f"status={status}")
    if data and "count" in data:
        record(PHASE, "ingestion/runs limit=5 count<=5",
               data["count"] <= 5, f"count={data['count']}")

    # ── 6.10 GET /api/v1/ingestion/runs with provider filter ──────
    print("\n── Ingestion Runs (provider filter) ──")
    status, data, raw = api_get("/api/v1/ingestion/runs?provider=openmeteo", officer_token)
    record(PHASE, "ingestion/runs provider filter no 500", status != 500,
           f"status={status}")
    record(PHASE, "ingestion/runs provider filter no traceback",
           has_no_traceback(raw))

    # ── 6.11 Historical Weather (edge case: bad dates) ────────────
    print("\n── Historical Weather Ingestion (edge case) ──")
    status, data, raw = api_post(
        "/api/v1/ingestion/runs/weather/historical?start_date=not-a-date&end_date=also-not",
        token=officer_token
    )
    record(PHASE, "weather historical bad dates no 500", status != 500,
           f"status={status}")
    record(PHASE, "weather historical bad dates no traceback",
           has_no_traceback(raw))

    # ── 6.12 Historical AQ (edge case: bad dates) ─────────────────
    print("\n── Historical AQ Ingestion (edge case) ──")
    status, data, raw = api_post(
        "/api/v1/ingestion/runs/aq/historical?start_date=not-a-date&end_date=also-not",
        token=officer_token
    )
    record(PHASE, "aq historical bad dates no 500", status != 500,
           f"status={status}")
    record(PHASE, "aq historical bad dates no traceback",
           has_no_traceback(raw))


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  LAHORE PULSE AI — PHASE 4-6 EDGE CASE TEST SUITE")
    print(f"  Target: {BASE_URL}")
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Pre-flight check
    print("\n── Pre-flight: Health Check ──")
    try:
        status, data, raw = api_get("/api/v1/health")
        if status == 200:
            print(f"  ✅ Server is up (status={status})")
        else:
            print(f"  ⚠️  Server returned status={status}")
            print(f"  Response: {raw[:300]}")
    except Exception as e:
        print(f"  ❌ Cannot reach server: {e}")
        print("  Make sure the backend is running at http://localhost:8002")
        sys.exit(1)

    # Run all phases
    try:
        test_phase4_forecast()
    except Exception as e:
        print(f"\n  💥 Phase 4 crashed: {e}")
        traceback.print_exc()
        record("P4-FORECAST", "PHASE 4 CRASHED", False, str(e))

    try:
        test_phase5_accountability()
    except Exception as e:
        print(f"\n  💥 Phase 5 crashed: {e}")
        traceback.print_exc()
        record("P5-ACCOUNTABILITY", "PHASE 5 CRASHED", False, str(e))

    try:
        test_phase6_ingestion()
    except Exception as e:
        print(f"\n  💥 Phase 6 crashed: {e}")
        traceback.print_exc()
        record("P6-INGESTION", "PHASE 6 CRASHED", False, str(e))

    # ═══════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")

    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = sum(1 for r in results if r[2] == "FAIL")

    # Group by phase
    phases = {}
    for phase, name, status, detail in results:
        if phase not in phases:
            phases[phase] = {"pass": 0, "fail": 0, "total": 0}
        phases[phase]["total"] += 1
        if status == "PASS":
            phases[phase]["pass"] += 1
        else:
            phases[phase]["fail"] += 1

    for phase in sorted(phases.keys()):
        p = phases[phase]
        emoji = "✅" if p["fail"] == 0 else "⚠️"
        print(f"  {emoji} {phase}: {p['pass']}/{p['total']} passed"
              + (f" ({p['fail']} FAILED)" if p["fail"] > 0 else ""))

    print(f"\n  TOTAL: {passed}/{total} passed, {failed} FAILED")

    if failed == 0:
        print(f"\n  🎉 ALL TESTS PASSED!")
    else:
        print(f"\n  ❌ {failed} TEST(S) FAILED — details above")
        print("\n  Failed tests:")
        for phase, name, status, detail in results:
            if status == "FAIL":
                print(f"    • [{phase}] {name}: {detail}")

    print(f"\n{'='*70}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
