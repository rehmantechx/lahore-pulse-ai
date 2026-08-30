"""Security Headers Middleware.

Adds standard security headers to all HTTP responses.
Implements OWASP-recommended headers for web application security.

Headers set:
    X-Content-Type-Options: nosniff — Prevents MIME type sniffing
    X-Frame-Options: DENY — Prevents clickjacking
    X-XSS-Protection: 1; mode=block — Legacy XSS protection
    Referrer-Policy: strict-origin-when-cross-origin — Controls referrer info
    Content-Security-Policy: Basic policy — Prevents XSS/injection
    Strict-Transport-Security: HSTS for production
    Permissions-Policy: Restricts browser features
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking — no framing allowed
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Basic Content Security Policy
        # Allows inline scripts/styles (required by Vite dev), restricts sources
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' http://localhost:8000 http://localhost:8001 http://localhost:5173",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # HSTS — only in production (enforced HTTPS)
        # In dev, skip to avoid cert issues on localhost
        host = request.headers.get("host", "")
        if "localhost" not in host and "127.0.0.1" not in host:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
