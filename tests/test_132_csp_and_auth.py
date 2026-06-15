"""Phase 132 Wave 0 RED tests — CSP header assertion (AUDIT-14 / D-04/05).

These tests MUST fail before Wave 1 implementation because the
Content-Security-Policy header is not yet present in _STATIC_HEADERS.

Wave 1 fix: add "Content-Security-Policy": "script-src 'self'; object-src 'none'"
to quirk/dashboard/api/middleware/security_headers.py::_STATIC_HEADERS.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from quirk.dashboard.api.app import create_app


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _client():
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# RED: Content-Security-Policy header
# ---------------------------------------------------------------------------


def test_csp_header_present():
    """Content-Security-Policy header must be present on all API responses (AUDIT-14 / D-04/05).

    RED: This test fails until Wave 1 adds the CSP entry to _STATIC_HEADERS.
    """
    resp = _client().get("/api/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
