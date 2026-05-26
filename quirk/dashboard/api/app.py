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
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from quirk.config import get_cors_origins
from quirk.dashboard.api.deps import _default_db_path
from quirk.dashboard.api.middleware.rate_limit import RateLimitMiddleware
from quirk.dashboard.api.routes import health, jobs, merge, pdf, qramm, scan, schedules, sensor, trends

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# Root-level static files that must be served before the SPA catch-all.
# The SPA catch-all would otherwise intercept /favicon.ico etc. and return index.html.
_ROOT_STATIC_FILES = ("favicon.ico", "favicon.svg", "favicon.png", "robots.txt", "manifest.json")


def _index_html() -> str:
    return os.path.join(_STATIC_DIR, "index.html")


def _recover_stale_jobs(db_path: str) -> None:
    """Phase 65 D-12: flip orphaned `running` scan_jobs rows to `failed` on startup.

    Wrapped in try/except so a missing table on first-ever boot (before init_db
    has run) does not crash API startup.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.models import ScanJob

        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session() as db:
            stale_rows = db.query(ScanJob).filter(ScanJob.status == "running").all()
            for row in stale_rows:
                row.status = "failed"
                row.error_message = "API restarted — job lost"
                row.completed_at = now
            if stale_rows:
                db.commit()
    except Exception:
        # Best-effort: never crash API startup on stale-job sweep failure
        pass


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Phase 65 D-12: sweep stale `running` scan_jobs to `failed` on startup."""
    db_path = application.state.db_path
    _recover_stale_jobs(db_path)
    yield
    # No teardown


def create_app(db_path: str | None = None) -> FastAPI:
    if db_path is None:
        db_path = _default_db_path()
    application = FastAPI(
        title="QU.I.R.K. Dashboard API",
        description="Local dashboard API for quantum-readiness scan results",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.db_path = db_path

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
    application.include_router(jobs.read_router, prefix="/api")
    application.include_router(jobs.write_router, prefix="/api")
    application.include_router(merge.router, prefix="/api")
    application.include_router(sensor.router, prefix="/api")

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
