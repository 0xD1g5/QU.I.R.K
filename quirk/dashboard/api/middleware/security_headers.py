"""Security response-header middleware — hardening for network-exposed consoles.

Adds a small set of defensive headers to every response. These matter once the
console is reachable beyond loopback (e.g. a cloud-hosted console behind a TLS
reverse proxy): they reduce MIME-sniffing, clickjacking, and referrer-leak
surface for the dashboard SPA and the JSON API.

Design:
* Zero new dependencies — Starlette BaseHTTPMiddleware only.
* HSTS is OFF by default and opt-in via QUIRK_HSTS, because the app speaks
  plain HTTP to its reverse proxy; emitting HSTS only makes sense once TLS is
  actually terminated in front of it. Operators enable it in production via the
  console.env file (see docs/deployment-cloud-console.md).
* Existing headers are never overwritten — a downstream proxy that already sets
  a stricter policy wins.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Static defensive headers applied to every response.
_STATIC_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Lock down powerful browser features the dashboard never uses.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Restrict script execution to same origin; block plugins (AUDIT-14 / D-04/05).
    "Content-Security-Policy": "script-src 'self'; object-src 'none'",
}

# HSTS value used when QUIRK_HSTS is truthy: 1 year + subdomains.
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


def _hsts_enabled() -> bool:
    return os.environ.get("QUIRK_HSTS", "").strip().lower() in {"1", "true", "yes", "on"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach defensive headers to every response without clobbering existing ones."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in _STATIC_HEADERS.items():
            response.headers.setdefault(name, value)
        if _hsts_enabled():
            response.headers.setdefault("Strict-Transport-Security", _HSTS_VALUE)
        return response
