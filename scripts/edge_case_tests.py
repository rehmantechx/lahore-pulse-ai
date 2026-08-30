#!/usr/bin/env python3
"""Comprehensive edge-case test suite for Lahore Pulse AI backend.

Tests API edge cases, auth edge cases, and database edge cases.
Uses only urllib.request + json (no third-party dependencies).
"""

from __future__ import annotations

import json
import sys
import traceback as tb
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://localhost:8002/api/v1"

# ── helpers ──────────────────────────────────────────────────────

PASS = 0
FAIL = 0
RESULTS: list[str] = []


def _result(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    line = f"[{tag}] {name}" + (f" — {detail}" if detail else "")
    RESULTS.append(line)
    print(line)


def _req(
    method: str,
    url: str,
    data: dict | None = None,
    headers: dict | None = None,
    raw_body: str | None = None,
    content_type: str = "application/json",
) -> tuple[int, str]:
    """Make an HTTP request and return (status_code, body_text)."""
    hdrs = dict(headers) if headers else {}
    if data is not None and raw_body is None:
        body = json.dumps(data).encode()
        hdrs.setdefault("Content-Type", content_type)
    elif raw_body is not None:
        body = raw_body.encode("utf-8")
        if content_type:
            hdrs["Content-Type"] = content_type
    else:
        body = None

    req = Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urlopen(req, timeout=15)
        return resp.status, resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except URLError as e:
        return 0, str(e.reason)
    except Exception as e:
        return 0, str(e)


def _safe_json(text: str):
    """Parse JSON safely; returns (parsed, None) or (None, error_string)."""
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


def _check_safety(name: str, status: int, body: str) -> bool:
    """Verify no tracebacks / filesystem paths / DB paths leak. Returns True if clean."""
    violations = []
    lower = body.lower()
    # Filesystem path indicators (Windows + Unix)
    for pat in ["c:\\\\", "c:/", "/home/", "/usr/", "backtrace", "traceback", "exception"]:
        if pat in lower:
            violations.append(f"found '{pat}'")
    # Database file path
    if "lahore_pulse.db" in lower:
        violations.append("found DB path lahore_pulse.db")
    if violations:
        _result(name, False, f"body leak: {'; '.join(violations)}")
        return False
    return True


def _get_token(username: str, password: str) -> str | None:
    """Login and return token, or None on failure."""
    status, body = _req("POST", f"{BASE}/auth/login", {"username": username, "password": password})
    if status == 200:
        parsed, err = _safe_json(body)
        if parsed and "token" in parsed:
            return parsed["token"]
    return None


# ═══════════════════════════════════════════════════════════════════
# PHASE 1: API EDGE CASES
# ═══════════════════════════════════════════════════════════════════

def phase1_auth_tests():
    print("\n" + "=" * 60)
    print("PHASE 1a: AUTH ENDPOINT EDGE CASES")
    print("=" * 60)

    url = f"{BASE}/auth/login"

    # 1. Valid credentials
    s, b = _req("POST", url, {"username": "citizen", "password": "citizen123"})
    parsed, _ = _safe_json(b)
    has_token = "token" in (parsed or {})
    _result(
        "auth: valid creds (citizen/citizen123)",
        s == 200 and parsed is not None and has_token,
        f"status={s}, has_token={has_token}"
    )
    _check_safety("auth: valid creds safety", s, b)

    # 2. Invalid credentials
    s, b = _req("POST", url, {"username": "citizen", "password": "wrongpass"})
    _result(
        "auth: invalid creds",
        s == 401 or s == 400,
        f"status={s}"
    )

    # 3. Empty username
    s, b = _req("POST", url, {"username": "", "password": "citizen123"})
    _result(
        "auth: empty username",
        s in (400, 401, 422),
        f"status={s}"
    )

    # 4. Empty password
    s, b = _req("POST", url, {"username": "citizen", "password": ""})
    _result(
        "auth: empty password",
        s in (400, 401, 422),
        f"status={s}"
    )

    # 5. Null fields
    s, b = _req("POST", url, {"username": None, "password": None})
    _result(
        "auth: null fields",
        s in (400, 401, 422),
        f"status={s}"
    )

    # 6. Whitespace strings
    s, b = _req("POST", url, {"username": "   ", "password": "   "})
    _result(
        "auth: whitespace strings",
        s in (400, 401, 422),
        f"status={s}"
    )

    # 7. Extremely long username (1000 chars)
    long_name = "a" * 1000
    s, b = _req("POST", url, {"username": long_name, "password": "citizen123"})
    _result(
        "auth: 1000-char username",
        s in (400, 401, 422),
        f"status={s}"
    )

    # 8. Malformed JSON body
    s, b = _req("POST", url, raw_body="{bad json", content_type="application/json")
    _result(
        "auth: malformed JSON body",
        s in (400, 422),
        f"status={s}"
    )

    # 9. Wrong Content-Type
    s, b = _req("POST", url, data={"username": "citizen", "password": "citizen123"},
                content_type="text/plain")
    _result(
        "auth: wrong content-type (text/plain)",
        s in (400, 415, 422),
        f"status={s}"
    )

    # 10. SQL injection
    s, b = _req("POST", url, {"username": "' OR 1=1--", "password": "anything"})
    parsed, _ = _safe_json(b)
    # Must NOT succeed — should return 401
    _result(
        "auth: SQL injection (' OR 1=1--)",
        s in (400, 401, 422),
        f"status={s}"
    )
    _check_safety("auth: SQL injection safety", s, b)

    # 11. XSS
    s, b = _req("POST", url, {"username": "<script>alert(1)</script>", "password": "x"})
    _result(
        "auth: XSS in username",
        s in (400, 401, 422),
        f"status={s}"
    )
    _check_safety("auth: XSS safety", s, b)


def phase1_forecast_tests(token: str):
    print("\n" + "=" * 60)
    print("PHASE 1b: FORECAST ENDPOINT EDGE CASES")
    print("=" * 60)
    auth = {"Authorization": f"Bearer {token}"}

    valid_horizons = [1, 3, 6, 12, 24]
    for h in valid_horizons:
        s, b = _req("GET", f"{BASE}/forecast?horizon={h}", headers=auth)
        parsed, _ = _safe_json(b)
        ok = s == 200 and parsed is not None
        _result(
            f"forecast: horizon={h} (valid)",
            ok,
            f"status={s}, has_forecast={'forecast' in (parsed or {})}"
        )
        _check_safety(f"forecast: horizon={h} safety", s, b)

    # Invalid horizons
    bad_horizons = [
        (999, "huge horizon 999"),
        (-1, "negative horizon -1"),
        (0, "zero horizon 0"),
    ]
    for h, label in bad_horizons:
        s, b = _req("GET", f"{BASE}/forecast?horizon={h}", headers=auth)
        _result(
            f"forecast: {label}",
            s in (400, 422),
            f"status={s}"
        )
        _check_safety(f"forecast: {label} safety", s, b)

    # String horizon
    s, b = _req("GET", f"{BASE}/forecast?horizon=abc", headers=auth)
    _result(
        "forecast: string horizon 'abc'",
        s in (400, 422),
        f"status={s}"
    )

    # Empty horizon
    s, b = _req("GET", f"{BASE}/forecast?horizon=", headers=auth)
    _result(
        "forecast: empty horizon",
        s in (400, 422),
        f"status={s}"
    )

    # Very huge horizon
    s, b = _req("GET", f"{BASE}/forecast?horizon=999999", headers=auth)
    _result(
        "forecast: huge horizon 999999",
        s in (400, 422),
        f"status={s}"
    )

    # Missing horizon
    s, b = _req("GET", f"{BASE}/forecast", headers=auth)
    _result(
        "forecast: missing horizon param",
        s in (400, 422),
        f"status={s}"
    )

    # Verify no 500 errors in any forecast response
    for h in valid_horizons + [999, -1, 0]:
        s, b = _req("GET", f"{BASE}/forecast?horizon={h}", headers=auth)
        _result(
            f"forecast: no 500 for horizon={h}",
            s != 500,
            f"status={s}"
        )


def phase1_observations_tests():
    print("\n" + "=" * 60)
    print("PHASE 1c: OBSERVATIONS ENDPOINT EDGE CASES")
    print("=" * 60)

    # No params
    s, b = _req("GET", f"{BASE}/observations")
    parsed, _ = _safe_json(b)
    _result(
        "observations: no params",
        s == 200 and parsed is not None,
        f"status={s}"
    )
    _check_safety("observations: no params safety", s, b)

    # Nonexistent station
    s, b = _req("GET", f"{BASE}/observations?station_id=nonexistent_xyz")
    parsed, _ = _safe_json(b)
    _result(
        "observations: nonexistent station_id",
        s == 200 and parsed is not None,
        f"status={s}"
    )

    # Valid date range (historical)
    s, b = _req("GET", f"{BASE}/observations?start_date=2017-01-01&end_date=2017-01-02")
    parsed, _ = _safe_json(b)
    _result(
        "observations: valid range 2017-01-01 to 2017-01-02",
        s == 200 and parsed is not None,
        f"status={s}"
    )

    # Future dates
    s, b = _req("GET", f"{BASE}/observations?start_date=2099-01-01&end_date=2099-12-31")
    parsed, _ = _safe_json(b)
    _result(
        "observations: future dates 2099",
        s == 200 and parsed is not None,
        f"status={s}, total={parsed.get('total', '?') if parsed else '?'}"
    )

    # Invalid date format
    s, b = _req("GET", f"{BASE}/observations?start_date=invalid-date")
    parsed, _ = _safe_json(b)
    # Should either return 200 with empty data or 400/422
    _result(
        "observations: invalid date format",
        s in (200, 400, 422),
        f"status={s}"
    )
    _check_safety("observations: invalid date safety", s, b)

    # limit=0 → should be rejected (ge=1)
    s, b = _req("GET", f"{BASE}/observations?limit=0")
    _result(
        "observations: limit=0",
        s in (400, 422),
        f"status={s}"
    )

    # limit=-1 → should be rejected (ge=1)
    s, b = _req("GET", f"{BASE}/observations?limit=-1")
    _result(
        "observations: limit=-1",
        s in (400, 422),
        f"status={s}"
    )

    # limit=10000 → should be rejected (le=500)
    s, b = _req("GET", f"{BASE}/observations?limit=10000")
    _result(
        "observations: limit=10000",
        s in (400, 422),
        f"status={s}"
    )

    # offset=999999 (beyond data)
    s, b = _req("GET", f"{BASE}/observations?offset=999999")
    parsed, _ = _safe_json(b)
    _result(
        "observations: offset=999999",
        s == 200 and parsed is not None,
        f"status={s}"
    )


def phase1_health_tests():
    print("\n" + "=" * 60)
    print("PHASE 1d: HEALTH ENDPOINT")
    print("=" * 60)

    s, b = _req("GET", f"{BASE}/health")
    parsed, _ = _safe_json(b)
    _result(
        "health: basic check",
        s == 200 and parsed is not None,
        f"status={s}"
    )
    _check_safety("health: no filesystem paths", s, b)


def phase1_accuracy_tests(citizen_token: str, officer_token: str):
    print("\n" + "=" * 60)
    print("PHASE 1e: ACCURACY ENDPOINT RBAC")
    print("=" * 60)

    # No token → 401
    s, b = _req("GET", f"{BASE}/accuracy/summary")
    _result(
        "accuracy: no token → 401",
        s == 401,
        f"status={s}"
    )

    # Citizen token → should be 403
    auth_citizen = {"Authorization": f"Bearer {citizen_token}"}
    s, b = _req("GET", f"{BASE}/accuracy/summary", headers=auth_citizen)
    _result(
        "accuracy: citizen token → 403",
        s == 403,
        f"status={s}"
    )

    # Officer token → should be 200
    auth_officer = {"Authorization": f"Bearer {officer_token}"}
    s, b = _req("GET", f"{BASE}/accuracy/summary", headers=auth_officer)
    parsed, _ = _safe_json(b)
    _result(
        "accuracy: officer token → 200",
        s == 200,
        f"status={s}"
    )
    _check_safety("accuracy: officer response safety", s, b)


# ═══════════════════════════════════════════════════════════════════
# PHASE 2: AUTH EDGE CASES
# ═══════════════════════════════════════════════════════════════════

def phase2_auth_edge_cases(citizen_token: str, officer_token: str):
    print("\n" + "=" * 60)
    print("PHASE 2: AUTH EDGE CASES")
    print("=" * 60)

    # Citizen → government endpoint → expect 403
    auth_citizen = {"Authorization": f"Bearer {citizen_token}"}
    s, b = _req("GET", f"{BASE}/accuracy/summary", headers=auth_citizen)
    _result(
        "auth-edge: citizen → accuracy/summary → 403",
        s == 403,
        f"status={s}"
    )

    # Officer → accuracy/summary → expect 200
    auth_officer = {"Authorization": f"Bearer {officer_token}"}
    s, b = _req("GET", f"{BASE}/accuracy/summary", headers=auth_officer)
    _result(
        "auth-edge: officer → accuracy/summary → 200",
        s == 200,
        f"status={s}"
    )

    # No token → 401
    s, b = _req("GET", f"{BASE}/accuracy/summary")
    _result(
        "auth-edge: no token → 401",
        s == 401,
        f"status={s}"
    )

    # Tampered token
    s, b = _req("GET", f"{BASE}/accuracy/summary",
                headers={"Authorization": "Bearer abcdef123456789"})
    _result(
        "auth-edge: tampered token → 401",
        s == 401,
        f"status={s}"
    )

    # Empty Bearer
    s, b = _req("GET", f"{BASE}/accuracy/summary",
                headers={"Authorization": "Bearer "})
    _result(
        "auth-edge: empty Bearer → 401",
        s == 401,
        f"status={s}"
    )

    # Malformed header: just "Bearer" without value
    s, b = _req("GET", f"{BASE}/accuracy/summary",
                headers={"Authorization": "Bearer"})
    _result(
        "auth-edge: bare 'Bearer' header → 401",
        s == 401,
        f"status={s}"
    )


# ═══════════════════════════════════════════════════════════════════
# PHASE 3: DATABASE EDGE CASES
# ═══════════════════════════════════════════════════════════════════

def phase3_database_edge_cases():
    print("\n" + "=" * 60)
    print("PHASE 3: DATABASE EDGE CASES")
    print("=" * 60)

    # Start date far in the past (before any data exists)
    s, b = _req("GET", f"{BASE}/observations?start_date=1900-01-01&end_date=1900-12-31")
    parsed, _ = _safe_json(b)
    _result(
        "db: start_date=1900-01-01 (before data)",
        s == 200 and parsed is not None,
        f"status={s}, total={parsed.get('total', '?') if parsed else '?'}"
    )

    # End date far in the future
    s, b = _req("GET", f"{BASE}/observations?start_date=2200-01-01&end_date=2200-12-31")
    parsed, _ = _safe_json(b)
    _result(
        "db: end_date=2200 (far future)",
        s == 200 and parsed is not None,
        f"status={s}, total={parsed.get('total', '?') if parsed else '?'}"
    )

    # Inverted range (start > end)
    s, b = _req("GET", f"{BASE}/observations?start_date=2025-12-31&end_date=2025-01-01")
    parsed, _ = _safe_json(b)
    _result(
        "db: inverted date range (start > end)",
        s == 200 and parsed is not None,
        f"status={s}, total={parsed.get('total', '?') if parsed else '?'}"
    )

    # limit=1
    s, b = _req("GET", f"{BASE}/observations?limit=1")
    parsed, _ = _safe_json(b)
    _result(
        "db: limit=1",
        s == 200 and parsed is not None,
        f"status={s}, returned={len(parsed.get('observations', [])) if parsed else '?'}"
    )

    # Very large offset beyond data
    s, b = _req("GET", f"{BASE}/observations?offset=999999")
    parsed, _ = _safe_json(b)
    _result(
        "db: offset=999999 (beyond data)",
        s == 200 and parsed is not None,
        f"status={s}, total={parsed.get('total', '?') if parsed else '?'}"
    )

    # Health endpoint (predictable database check)
    s, b = _req("GET", f"{BASE}/health")
    parsed, _ = _safe_json(b)
    _result(
        "db: health endpoint with DB check",
        s == 200 and parsed is not None,
        f"status={s}, status_field={parsed.get('status', '?') if parsed else '?'}"
    )
    _check_safety("db: health endpoint safety (no DB path leak)", s, b)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    global PASS, FAIL
    print("=" * 60)
    print("LAHORE PULSE AI — AGGRESSIVE EDGE-CASE TEST SUITE")
    print("=" * 60)

    # ── Pre-flight: get tokens ───────────────────────────────────
    print("\nObtaining auth tokens...")
    citizen_token = _get_token("citizen", "citizen123")
    officer_token = _get_token("officer", "officer123")

    if not citizen_token:
        _result("PRE-FLIGHT: citizen login", False, "Could not obtain citizen token")
        print("\nFATAL: Cannot proceed without citizen token. Is the server running?")
        _print_summary()
        return

    _result("PRE-FLIGHT: citizen login", True)
    if officer_token:
        _result("PRE-FLIGHT: officer login", True)
    else:
        _result("PRE-FLIGHT: officer login", False, "Could not obtain officer token — officer tests will be skipped")

    # ── Phase 1 ──────────────────────────────────────────────────
    phase1_auth_tests()
    phase1_forecast_tests(citizen_token)
    phase1_observations_tests()
    phase1_health_tests()

    if officer_token:
        phase1_accuracy_tests(citizen_token, officer_token)
    else:
        print("\n  [SKIP] Phase 1e: accuracy RBAC tests (no officer token)")

    # ── Phase 2 ──────────────────────────────────────────────────
    if citizen_token and officer_token:
        phase2_auth_edge_cases(citizen_token, officer_token)
    else:
        print("\n  [SKIP] Phase 2: auth edge cases (missing tokens)")

    # ── Phase 3 ──────────────────────────────────────────────────
    phase3_database_edge_cases()

    # ── Summary ──────────────────────────────────────────────────
    _print_summary()


def _print_summary():
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    total = PASS + FAIL
    print(f"  Total tests : {total}")
    print(f"  PASS        : {PASS}")
    print(f"  FAIL        : {FAIL}")
    print(f"  Pass rate   : {(PASS/total*100) if total else 0:.1f}%")
    print("=" * 60)
    if FAIL:
        print("\nFailed tests:")
        for r in RESULTS:
            if r.startswith("[FAIL]"):
                print(f"  {r}")
    print()
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
