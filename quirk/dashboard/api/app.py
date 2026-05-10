"""FastAPI application factory for QU.I.R.K. dashboard.

Key design:
- API routes registered first (prefix /api).
- Root-level static files (favicon.*) served explicitly before the SPA catch-all.
- /assets StaticFiles mount for Vite build output.
- SPA catch-all last — serves index.html for ANY path not already matched.
  This allows React Router to handle /findings, /cbom, etc. on hard reload.
"""
from __future__ import annotations

import mimetypes
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from quirk.config import get_cors_origins
from quirk.dashboard.api.middleware.rate_limit import RateLimitMiddleware
from quirk.dashboard.api.routes import health, pdf, qramm, scan, schedules, trends

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# Root-level static files that must be served before the SPA catch-all.
# The SPA catch-all would otherwise intercept /favicon.ico etc. and return index.html.
_ROOT_STATIC_FILES = ("favicon.ico", "favicon.svg", "favicon.png", "robots.txt", "manifest.json")


def _index_html() -> str:
    return os.path.join(_STATIC_DIR, "index.html")


def create_app() -> FastAPI:
    application = FastAPI(
        title="QU.I.R.K. Dashboard API",
        description="Local dashboard API for quantum-readiness scan results",
        version="1.0.0",
    )

    # -------------------------------------------------------------------------
    # Middleware — Phase 58 / HARDEN-API-02, HARDEN-API-03
    # FastAPI applies add_middleware in REVERSE registration order.
    # Execution order: CORS (outermost) -> RateLimit -> route dispatch.
    # Auth + CSRF are Depends()-injected at router level (Plan 03).
    # CORS origins are configurable via QUIRK_CORS_ORIGINS env var or
    # security.cors_origins YAML field (defaults: 127.0.0.1 + localhost).
    # -------------------------------------------------------------------------
    application.add_middleware(
        RateLimitMiddleware,  # registered first = innermost (runs after CORS)
    )
    application.add_middleware(
        CORSMiddleware,  # registered last = outermost (runs first on every request)
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. API routes
    application.include_router(health.router, prefix="/api")
    application.include_router(pdf.router, prefix="/api")
    application.include_router(scan.router, prefix="/api")
    application.include_router(trends.router, prefix="/api")
    application.include_router(qramm.router, prefix="/api")
    application.include_router(schedules.router, prefix="/api")

    # 2. Root-level static files — registered before the SPA catch-all so the
    #    wildcard route does not intercept favicon.ico / favicon.svg / favicon.png.
    for _filename in _ROOT_STATIC_FILES:
        _filepath = os.path.join(_STATIC_DIR, _filename)
        if os.path.isfile(_filepath):
            _mime = mimetypes.guess_type(_filename)[0] or "application/octet-stream"

            def _make_handler(fp: str, mt: str):
                async def _handler() -> FileResponse:
                    return FileResponse(fp, media_type=mt)
                return _handler

            application.get(f"/{_filename}")(_make_handler(_filepath, _mime))

    # 3. /assets static mount (CSS, JS, fonts from Vite build)
    assets_dir = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        application.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    # 4. SPA catch-all — MUST be registered last
    @application.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve index.html for all non-API paths (SPA client-side routing)."""
        index = _index_html()
        if os.path.exists(index):
            return FileResponse(index)
        # During development before first `npm run build`, return a minimal placeholder
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>QU.I.R.K. Dashboard</h1>"
                    "<p>Run <code>npm run build</code> in src/dashboard/ to build the frontend.</p>"
                    "</body></html>",
            status_code=200,
        )

    return application


app = create_app()
