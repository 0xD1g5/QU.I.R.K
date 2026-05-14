"""POST /api/export/pdf — generates a PDF from the /print route using Playwright headless.

Design:
- Requires `playwright install chromium` (one-time ~150MB, user runs manually).
- On success: returns PDF bytes as application/pdf response.
- On missing chromium: returns HTTP 503 with actionable error message.
- Playwright navigates to http://127.0.0.1:{port}/print on the same server.
  Port is read from the QUIRK_SERVE_PORT environment variable (set by server.py),
  defaulting to 8512.
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from quirk.errors import format_error

from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])

# Module-level import allows test mocking via patch("quirk.dashboard.api.routes.pdf.sync_playwright")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]


@router.post("/export/pdf")
def export_pdf() -> Response:
    """POST /api/export/pdf — renders the /print route with Playwright and returns a PDF.

    Returns:
        200: PDF binary (application/pdf)
        503: JSON error when Playwright chromium is not installed
    """
    if sync_playwright is None:
        return Response(
            content=json.dumps({"detail": format_error("DASHBOARD-012")}).encode(),
            status_code=503,
            media_type="application/json",
        )

    try:
        port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
    except ValueError:
        return Response(
            content=json.dumps({"detail": "QUIRK_SERVE_PORT is not a valid integer."}).encode(),
            status_code=500,
            media_type="application/json",
        )

    # D-11 / CR-02: port range clamp — reject values outside safe ephemeral range
    if not (1024 <= port <= 65535):
        return Response(
            content=json.dumps(
                {"detail": "QUIRK_SERVE_PORT is out of allowed range (1024–65535)."}
            ).encode(),
            status_code=500,
            media_type="application/json",
        )

    print_url = f"http://127.0.0.1:{port}/print"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()

                # D-12 / CR-02: abort navigations that resolve to non-loopback hosts.
                _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

                def _abort_non_loopback(route):
                    from urllib.parse import urlparse
                    host = urlparse(route.request.url).hostname or ""
                    if host not in _LOOPBACK_HOSTS:
                        route.abort()
                    else:
                        route.continue_()

                page.route("**/*", _abort_non_loopback)

                page.goto(print_url, wait_until="networkidle", timeout=30_000)
                page.wait_for_selector('body[data-ready="true"]', timeout=15_000)

                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "16mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
                )
            finally:
                browser.close()

        return Response(
            content=pdf_bytes,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=quirk-report.pdf"},
        )

    except Exception as exc:
        msg = str(exc)
        if "chromium" in msg.lower() or "executable" in msg.lower() or "no such file" in msg.lower():
            detail = f"PDF export failed. Ensure Playwright is installed: playwright install chromium. Error: {msg}"
            return Response(
                content=json.dumps({"detail": detail}).encode(),
                status_code=503,
                media_type="application/json",
            )
        return Response(
            content=json.dumps({"detail": f"PDF export failed: {msg}"}).encode(),
            status_code=500,
            media_type="application/json",
        )
