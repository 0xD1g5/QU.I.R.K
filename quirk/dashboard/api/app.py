"""FastAPI application factory for QU.I.R.K. dashboard.

Key design:
- API routes registered first (prefix /api).
- /assets StaticFiles mount second.
- SPA catch-all last — serves index.html for ANY path not already matched.
  This allows React Router to handle /findings, /cbom, etc. on hard reload.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from quirk.dashboard.api.routes import health, pdf

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


def _index_html() -> str:
    return os.path.join(_STATIC_DIR, "index.html")


def create_app() -> FastAPI:
    application = FastAPI(
        title="QU.I.R.K. Dashboard API",
        description="Local dashboard API for quantum-readiness scan results",
        version="1.0.0",
    )

    # 1. API routes
    application.include_router(health.router, prefix="/api")
    application.include_router(pdf.router, prefix="/api")

    # 2. /assets static mount (CSS, JS, fonts from Vite build)
    assets_dir = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        application.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    # 3. SPA catch-all — MUST be registered last
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
