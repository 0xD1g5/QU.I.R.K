"""Bearer token auth dependency for the dashboard API — Phase 58 / CR-03 / HARDEN-API-01."""
from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


def _get_configured_token() -> str:
    """Priority: QUIRK_API_TOKEN env var -> security.api_token YAML field -> ''.

    Returns empty string when auth is disabled (D-02).
    Env var wins when both are set (D-01).
    """
    if val := os.environ.get("QUIRK_API_TOKEN"):
        return val
    # YAML fallback: import lazily to avoid circular import with app factory
    try:
        from quirk.config import load_config
        cfg = load_config()
        return cfg.security.api_token or ""
    except Exception:
        return ""


_bearer = HTTPBearer(auto_error=False)


def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    """FastAPI Depends() — enforces bearer token when QUIRK_API_TOKEN is configured.

    Raises HTTPException 401 when auth is enabled and token is missing/wrong (D-04).
    Passthrough when auth is disabled — empty configured token (D-02).
    Never reaches business logic on 401 (D-04).
    """
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not hmac.compare_digest(credentials.credentials, configured):  # D-03
        raise HTTPException(status_code=401, detail="Authentication required")
