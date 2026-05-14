"""CSRF header check dependency for the dashboard API — Phase 58 / CR-03 / HARDEN-API-01.

Uses the custom-request-header CSRF pattern (D-07):
  - All POST/PUT/DELETE/PATCH require header X-Quirk-Request: 1
  - Missing header → 403 (distinguishes from 401 auth failure)
  - GET/HEAD/OPTIONS pass through unconditionally
"""
from __future__ import annotations

from fastapi import HTTPException, Request

CSRF_HEADER = "X-Quirk-Request"
_MUTATING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


def require_csrf(request: Request) -> None:
    """FastAPI Depends() — requires X-Quirk-Request: 1 on mutating requests (D-07).

    Missing header on a mutating request → 403 Forbidden.
    Body: {"detail": "Missing CSRF header: X-Quirk-Request"}
    """
    if request.method in _MUTATING_METHODS:
        if request.headers.get(CSRF_HEADER) != "1":
            raise HTTPException(
                status_code=403,
                detail=f"Missing CSRF header: {CSRF_HEADER}",
            )
