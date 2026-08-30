"""
PHASE 12 & 13: Network Failure + Security Edge-Case Tests
Lahore Pulse AI — Comprehensive Robustness Audit
Uses ONLY urllib.request + json (no third-party deps)
"""

import json
import socket
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO

BASE = "http://localhost:8002"
DEAD_PORT = "http://localhost:8999"

results = []          # (phase, test_name, status, detail)
SECRETS_PATTERNS = [
    "password", "secret", "api_key", "token",
    "/Users/", "/home/", "C:\\Users\\", ".env", ".db", ".sqlite",
]
# Legitimate tokens returned by /auth/login contain "token" in the
# JSON response body — we must not flag those.  We'll track the
# known-good token strings and exclude them from the secrets scan.


# ── Helpers ──────────────────────────────────────────────────────

def _record(phase, name, status, detail=""):
    results.append((phase, name, status, detail))
    tag = "PASS" if status else "FAIL"
    print(f"  [{tag}] {name}" + (f"  → {detail}" if detail else ""))


def _req(method, path, data=None, headers=None, raw_body=None,
         content_type="application/json", expect_json=True):
    """Send request, return (status_code, response_dict_or_str, response_headers)."""
    url = f"{BASE}{path}"
    h = headers.copy() if headers else {}
    if data is not None:
        body = raw_body if raw_body is not None else json.dumps(data).encode()
        h.setdefault("Content-Type", content_type)
        h.setdefault("Content-Length", str(len(body)))
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        hdrs = dict(resp.headers)
        status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        hdrs = dict(e.headers)
        status = e.code
    except Exception as e:
        return (None, str(e), {})

    # Try JSON parse
    if expect_json:
        try:
            return (status, json.loads(raw.decode("utf-8", errors="replace")), hdrs)
        except (json.JSONDecodeError, ValueError):
            return (status, raw.decode("utf-8", errors="replace"), hdrs)
    else:
        return (status, raw.decode("utf-8", errors="replace"), hdrs)


def _get_citizen_token():
    """Get a valid citizen token for authenticated tests."""
    status, body, _ = _req("POST", "/api/v1/auth/login",
                           {"username": "citizen", "password": "citizen123"})
    if status == 200 and isinstance(body, dict) and "token" in body:
        return body["token"]
    print(f"  [WARN] Could not obtain citizen token: {status} {body}")
    return None


def _get_officer_token():
    """Get a valid officer token."""
    status, body, _ = _req("POST", "/api/v1/auth/login",
                           {"username": "officer", "password": "officer123"})
    if status == 200 and isinstance(body, dict) and "token" in body:
        return body["token"]
    return None


# ══════════════════════════════════════════════════════════════════
#  PHASE 12 — NETWORK FAILURE TESTS
# ══════════════════════════════════════════════════════════════════

def phase12():
    print("\n" + "=" * 70)
    print("PHASE 12: NETWORK FAILURE TESTS")
    print("=" * 70)

    # ── 12-A: Backend down simulation ────────────────────────────
    print("\n── 12-A: Backend-down simulation ──")

    # A1: Connection refused on dead port
    try:
        req = urllib.request.Request(f"{DEAD_PORT}/api/v1/health")
        urllib.request.urlopen(req, timeout=3)
        _record("12A", "Dead-port connection refused", False, "No error raised")
    except (urllib.error.URLError, ConnectionError, socket.error, OSError) as e:
        _record("12A", "Dead-port connection refused", True, type(e).__name__)
    except Exception as e:
        _record("12A", "Dead-port connection refused", False, f"Unexpected: {e}")

    # A2: Invalid endpoint on live server → 404
    status, body, _ = _req("GET", "/api/v1/this-endpoint-does-not-exist-xyz")
    _record("12A", "Invalid endpoint returns 404", status == 404,
            f"status={status}")

    # ── 12-B: HTTP error code tests ──────────────────────────────
    print("\n── 12-B: HTTP error codes ──")

    # B1: GET /api/v1/nonexistent → 404
    status, body, _ = _req("GET", "/api/v1/nonexistent")
    _record("12B", "GET /nonexistent → 404", status == 404, f"status={status}")

    # B2: POST /auth/login with empty body → 422
    status, body, _ = _req("POST", "/api/v1/auth/login", raw_body=b"{}")
    _record("12B", "POST /auth/login empty body → 422",
            status == 422, f"status={status}")

    # B3: GET /accuracy/summary with no token → 401
    status, body, _ = _req("GET", "/api/v1/accuracy/summary")
    _record("12B", "GET /accuracy/summary no token → 401",
            status == 401, f"status={status}")

    # B4: GET /forecast?horizon=abc → 422
    status, body, _ = _req("GET", "/api/v1/forecast?horizon=abc")
    _record("12B", "GET /forecast?horizon=abc → 422",
            status == 422, f"status={status}")

    # ── 12-C: Malformed requests ─────────────────────────────────
    print("\n── 12-C: Malformed requests ──")

    # C1: POST with empty JSON body
    status, body, _ = _req("POST", "/api/v1/auth/login", raw_body=b"{}")
    is_json = isinstance(body, (dict, list))
    no_trace = isinstance(body, str) and "Traceback" not in body and "<html" not in body.lower()
    _record("12C", "Empty JSON body {}", status is not None and (is_json or no_trace),
            f"status={status}, json={is_json}")

    # C2: POST with malformed JSON
    status, body, _ = _req("POST", "/api/v1/auth/login", raw_body=b"{broken")
    is_json = isinstance(body, (dict, list))
    no_trace = isinstance(body, str) and "Traceback" not in body and "<html" not in body.lower()
    _record("12C", "Malformed JSON {broken", status is not None and (is_json or no_trace),
            f"status={status}, json={is_json}")

    # C3: POST with wrong content-type
    status, body, _ = _req("POST", "/api/v1/auth/login",
                           raw_body=b'{"username":"citizen","password":"citizen123"}',
                           content_type="text/plain")
    is_json = isinstance(body, (dict, list))
    no_trace = isinstance(body, str) and "Traceback" not in body and "<html" not in body.lower()
    _record("12C", "Wrong content-type (text/plain)", status is not None and (is_json or no_trace),
            f"status={status}")

    # C4: POST with extremely large body (10 MB of zeros)
    large_body = b"\x00" * (10 * 1024 * 1024)
    status, body, _ = _req("POST", "/api/v1/auth/login", raw_body=large_body,
                           content_type="application/json")
    is_json = isinstance(body, (dict, list))
    no_trace = isinstance(body, str) and "Traceback" not in body and "<html" not in body.lower()
    _record("12C", "10 MB body", status is not None and (is_json or no_trace),
            f"status={status}")

    # ── 12-D: Verify NO tracebacks / HTML error pages ────────────
    print("\n── 12-D: Error response format validation ──")
    problematic_statuses = []
    for phase, name, passed, detail in results:
        if "12" in phase and not passed:
            problematic_statuses.append((name, detail))
    if not problematic_statuses:
        _record("12D", "All Phase-12 error responses clean", True)
    else:
        for n, d in problematic_statuses:
            _record("12D", f"Problematic: {n}", False, d)


# ══════════════════════════════════════════════════════════════════
#  PHASE 13 — SECURITY EDGE CASES
# ══════════════════════════════════════════════════════════════════

def phase13():
    print("\n" + "=" * 70)
    print("PHASE 13: SECURITY EDGE CASES")
    print("=" * 70)

    # ── 13-A: Input injection ────────────────────────────────────
    print("\n── 13-A: Input injection tests ──")

    injections = [
        ("SQL injection (single-quote)", "'; DROP TABLE users; --"),
        ("SQL injection (double-quote OR)", 'admin" OR "1"="1'),
        ("XSS payload", "<script>alert('xss')</script>"),
        ("Path traversal in username", "../../../etc/passwd"),
        ("Unicode username", "أحمد"),
        ("Null byte injection", "admin\x00"),
    ]

    for label, payload in injections:
        status, body, _ = _req("POST", "/api/v1/auth/login",
                               {"username": payload, "password": "x"})
        is_json = isinstance(body, (dict, list))
        no_trace = isinstance(body, str) and "Traceback" not in body and "<html" not in body.lower()
        safe = status is not None and (is_json or no_trace)
        # None of these should succeed with 200
        not_200 = status != 200
        _record("13A", f"Injection: {label}", safe and not_200,
                f"status={status}, safe_format={safe}")

    # ── 13-B: Path traversal ─────────────────────────────────────
    print("\n── 13-B: Path traversal attempts ──")

    traversal_paths = [
        "/api/v1/../../../etc/passwd",
        "/api/v1/%2e%2e/%2e%2e/etc/passwd",
        "/api/v1/..%2f..%2f..%2fetc/passwd",
    ]

    for tpath in traversal_paths:
        status, body, _ = _req("GET", tpath, expect_json=False)
        no_file_leak = "root:" not in (body if isinstance(body, str) else "")
        _record("13B", f"Traversal: {tpath}", status is not None and no_file_leak,
                f"status={status}")

    # ── 13-C: Security headers ───────────────────────────────────
    print("\n── 13-C: Security response headers ──")

    status, body, hdrs = _req("GET", "/api/v1/health")

    expected_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": None,  # just check presence
    }

    for hdr, expected_val in expected_headers.items():
        actual = hdrs.get(hdr, hdrs.get(hdr.lower()))
        if expected_val:
            ok = actual == expected_val
            _record("13C", f"Header {hdr}", ok,
                    f"expected={expected_val!r}, got={actual!r}")
        else:
            ok = actual is not None and len(actual) > 0
            _record("13C", f"Header {hdr} present", ok,
                    f"got={actual!r}")

    # ── 13-D: Token verification ─────────────────────────────────
    print("\n── 13-D: Token verification ──")

    token = _get_citizen_token()
    if token:
        _record("13D", "Obtain valid citizen token", True)

        # D1: Valid token works
        status, body, _ = _req("GET", "/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {token}"})
        _record("13D", "Valid token accepted", status == 200, f"status={status}")

        # D2: Modified token fails
        modified = token[:-1] + ("A" if token[-1] != "A" else "B")
        status, body, _ = _req("GET", "/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {modified}"})
        _record("13D", "Modified token rejected", status == 401, f"status={status}")

        # D3: Empty bearer string
        status, body, _ = _req("GET", "/api/v1/auth/me",
                               headers={"Authorization": "Bearer "})
        _record("13D", "Empty bearer string rejected", status == 401, f"status={status}")

        # D4: Expired token format (fake payload with past exp)
        import base64
        fake_header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        fake_payload = base64.urlsafe_b64encode(json.dumps({
            "sub": "citizen", "role": "citizen",
            "exp": int(time.time()) - 86400  # 24 hours ago
        }).encode()).rstrip(b"=")
        expired_token = f"{fake_header.decode()}.{fake_payload.decode()}.fakesig"
        status, body, _ = _req("GET", "/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {expired_token}"})
        _record("13D", "Expired/fake token rejected", status == 401, f"status={status}")
    else:
        _record("13D", "Token acquisition failed — skipping token tests", False)

    # ── 13-E: Secrets leak check ─────────────────────────────────
    print("\n── 13-E: Secrets / sensitive data leak scan ──")

    scan_paths = [
        ("GET", "/api/v1/health", None),
        ("GET", "/api/v1/readiness", None),
        ("GET", "/api/v1/forecast/all", None),
        ("GET", "/api/v1/observations", None),
        ("GET", "/api/v1/data-sources", None),
        ("POST", "/api/v1/auth/login", {"username": "citizen", "password": "citizen123"}),
    ]

    found_leaks = []
    token_value = token if token else ""

    for method, path, data in scan_paths:
        status, body, _ = _req(method, path, data)
        if body is None:
            continue
        body_str = json.dumps(body) if isinstance(body, (dict, list)) else str(body)

        # Remove the actual token from scan (it legitimately contains "token")
        if token_value:
            body_str = body_str.replace(token_value, "[REDACTED]")

        # Remove the password we sent in login request
        body_str = body_str.replace("citizen123", "[REDACTED]")
        body_str = body_str.replace("officer123", "[REDACTED]")

        for pattern in SECRETS_PATTERNS:
            if pattern.lower() in body_str.lower():
                # Check if it's a false-positive from field names like "token" in response schema
                if pattern == "token":
                    # The token field name appears in login response — that's fine
                    # But full token VALUES should not leak
                    continue
                found_leaks.append((path, pattern, body_str[:200]))

    if not found_leaks:
        _record("13E", "No secrets/sensitive data leaked", True)
    else:
        for path, pat, sample in found_leaks:
            _record("13E", f"Leak in {path}: '{pat}'", False, f"sample={sample}")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  PHASE 12 & 13: Network Failure + Security Edge-Case Tests ║")
    print("║  Lahore Pulse AI — Comprehensive Robustness Audit          ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Pre-flight: confirm backend is up
    try:
        req = urllib.request.Request(f"{BASE}/api/v1/health")
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"\n✓ Backend is UP (HTTP {resp.status})")
    except Exception as e:
        print(f"\n✗ Backend NOT reachable at {BASE}: {e}")
        print("  Tests will still run but many will fail.")

    phase12()
    phase13()

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for _, _, s, _ in results if s)
    failed = total - passed

    phase12_total = sum(1 for p, *_ in results if "12" in p)
    phase12_pass  = sum(1 for p, _, s, _ in results if "12" in p and s)
    phase13_total = sum(1 for p, *_ in results if "13" in p)
    phase13_pass  = sum(1 for p, _, s, _ in results if "13" in p and s)

    print(f"\n  Phase 12 (Network Failure):  {phase12_pass}/{phase12_total} passed")
    print(f"  Phase 13 (Security):         {phase13_pass}/{phase13_total} passed")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL:                       {passed}/{total} passed, {failed} failed")

    if failed:
        print(f"\n  FAILED TESTS:")
        for phase, name, _, detail in results:
            if not ("PASS" in ("PASS" if True else "")):
                pass
        for phase, name, status, detail in results:
            if not status:
                print(f"    ✗ [{phase}] {name}  →  {detail}")
    else:
        print(f"\n  🎉 ALL TESTS PASSED!")

    print()
    sys.exit(0 if failed == 0 else 1)
