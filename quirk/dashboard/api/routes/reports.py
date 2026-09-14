"""GET /api/reports/latest/* — read-only serving of the report artifacts
`write_reports()` already wrote to `cfg.output.directory` (Phase 209, DELIV-01).

This module introduces NO rendering path and never imports from
`quirk.reports.writer` — every artifact it serves already exists on disk by
the time a request reaches here. It re-derives availability independently
(existence checks + `importlib.util.find_spec`) rather than importing writer
internals, consistent with the phase boundary: `write_reports()` and
everything it calls are SHARED with the CLI path, and this module must never
change naming, stamping, or emission to make serving easier.

D-06 history constraint (recorded verbatim so a future reader does not have
to rediscover it): the fixed `ReportFormat` enum below is correct ONLY while
scope is latest-scan-only (D-02: the report stamp is render time, not
`scan_run_id`, and nothing on disk associates them). Any future per-scan
history feature would need a filename or scan-id path parameter, which would
reintroduce a validated (not structurally-closed) path component — that is a
new containment decision, not a trivial extension of D-04, and must revisit
D-04 explicitly rather than inheriting this module's guarantees by
assumption.

Naming hazard (209-PATTERNS.md): `quirk.reports` (the writer package,
`quirk/reports/writer.py`) and `quirk.dashboard.api.routes.reports` (this
module) share a tail name. Grep-based "find the reports module" searches will
hit both — always qualify by full path.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import ReportFormatAvailability, ReportManifestResponse

logger = logging.getLogger(__name__)


class _LiteralPathNotFoundRoute(APIRoute):
    """Converts a 422 raised by an invalid `ReportFormat` path segment into a
    404.

    D-04's containment guard treats enum membership as the routing rule
    itself — an unlisted `{fmt}` value is a routing MISS, not a malformed
    request body/query, so it must read as 404 to a client, not 422. FastAPI
    validates `Literal[...]`-typed path parameters via Pydantic AFTER the
    route already matched the URL pattern, raising `RequestValidationError`
    (-> 422) rather than failing the match itself — this route class is the
    mechanical fix for that gap, scoped to this router only.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except RequestValidationError:
                raise StarletteHTTPException(status_code=404, detail="Not Found")

        return custom_route_handler


# NO require_csrf: both endpoints below are read-only GETs. pdf.py pairs
# require_csrf only because its endpoint is a state-mutating POST.
router = APIRouter(dependencies=[Depends(require_auth)], route_class=_LiteralPathNotFoundRoute)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

REPORT_FORMATS: tuple[str, ...] = ("html", "pdf", "docx", "cbom-json", "cbom-xml")

ReportFormat = Literal["html", "pdf", "docx", "cbom-json", "cbom-xml"]

# Enum -> filename template (server-resolved only; the client never supplies
# a filename or path fragment — D-04/D-05).
_FORMAT_FILENAME_TEMPLATES: dict[str, str] = {
    "html": "report-{stamp}.html",
    "pdf": "report-{stamp}.pdf",
    "docx": "report-{stamp}.docx",
    "cbom-json": "cbom-{stamp}.cdx.json",
    "cbom-xml": "cbom-{stamp}.cdx.xml",
}

_FORMAT_MEDIA_TYPES: dict[str, str] = {
    "html": "text/html",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "cbom-json": "application/json",
    "cbom-xml": "application/xml",
}

# D-09 verbatim reason strings (209-UI-SPEC.md Copywriting Contract). Named
# module constants so this is the one source of truth other plans/tests cite.
REASON_NO_SCAN = "No scan has run yet."
REASON_DOCX_EXTRA_MISSING = "DOCX requires the optional extra: pip install quirk[docx]"
REASON_RENDER_FAILED = "This format failed to render for the latest scan. Check server logs."


# ---------------------------------------------------------------------------
# Config resolution (house idiom — copied from exposure_map.py:45-53)
# ---------------------------------------------------------------------------


def _output_directory() -> Optional[Path]:
    """Resolve `cfg.output.directory` from `QUIRK_CONFIG_PATH`, or None.

    Mirrors the lazy-import + QUIRK_CONFIG_PATH + broad-except idiom
    `exposure_map.py`/`jobs.py` already use. Fails to None on ANY error —
    an unreadable config must degrade to a safe "no artifacts" manifest,
    never a 500 and never a wrong directory.
    """
    try:
        from quirk.config import load_config  # lazy import — avoids cycles

        cfg_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
        cfg = load_config(cfg_path)
        return Path(cfg.output.directory)
    except Exception:
        logger.debug("output.directory unreadable; reports unavailable", exc_info=True)
        return None


def _docx_extra_available() -> bool:
    """Whether the `python-docx` optional extra is installed.

    Evaluated per call (NOT cached at import time) so tests can monkeypatch
    `importlib.util.find_spec`. No reusable helper exists elsewhere in this
    codebase — `docx_renderer.py`'s ImportError catch is function-scoped.
    """
    try:
        return importlib.util.find_spec("docx") is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Stamp-group selection (D-01 + D-03 fallback)
# ---------------------------------------------------------------------------


def _select_stamp(outdir: Path) -> tuple[Optional[str], Optional[str]]:
    """Select the stamp group to serve, returning (stamp, scan_time).

    D-01: prefer the newest `run-stats-{stamp}.json` group — it carries the
    real scan time and guarantees a coherent artifact set from one real run
    (never a mix of formats from two different runs).

    D-03 fallback: when no run-stats file exists, fall back to the newest
    complete stamp group and report scan time as explicitly unknown, never
    invented. `report-{stamp}.html` is the completeness signal because
    writer.py writes it unconditionally (writer.py:903-914) while
    pdf/docx/cbom are each independently skippable.
    """
    try:
        run_stats_files = sorted(glob.glob(str(outdir / "run-stats-*.json")))
    except Exception:
        run_stats_files = []

    if run_stats_files:
        newest = run_stats_files[-1]
        stamp = Path(newest).stem[len("run-stats-"):]
        scan_time: Optional[str] = None
        try:
            payload = json.loads(Path(newest).read_text())
            scan_time = payload.get("ended_utc")
        except Exception:
            logger.debug("run-stats file unreadable; scan_time unknown", exc_info=True)
        return stamp, scan_time

    try:
        html_files = sorted(glob.glob(str(outdir / "report-*.html")))
    except Exception:
        html_files = []

    if html_files:
        newest_html = html_files[-1]
        stamp = Path(newest_html).stem[len("report-"):]
        return stamp, None

    return None, None


def _format_availability(
    outdir: Path, stamp: Optional[str], fmt: str
) -> tuple[bool, Optional[str]]:
    """D-09 three-way distinction: no scan / extra missing / render failed."""
    if stamp is None:
        return False, REASON_NO_SCAN

    path = _resolve_artifact_path(outdir, stamp, fmt)
    if path.is_file():
        return True, None

    if fmt == "docx" and not _docx_extra_available():
        return False, REASON_DOCX_EXTRA_MISSING

    return False, REASON_RENDER_FAILED


def _resolve_artifact_path(outdir: Path, stamp: str, fmt: str) -> Path:
    """Join ONLY a server-resolved filename template onto `outdir`.

    The client never supplies `fmt` as anything other than one of the 5
    Literal members (Starlette 404s anything else before the handler runs),
    and even so this function never joins the raw `fmt` value itself — only
    the filename string looked up from `_FORMAT_FILENAME_TEMPLATES` (D-04).
    """
    filename = _FORMAT_FILENAME_TEMPLATES[fmt].format(stamp=stamp)
    return outdir / filename


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/reports/latest/manifest", response_model=ReportManifestResponse)
def get_report_manifest() -> ReportManifestResponse:
    """GET /api/reports/latest/manifest — every format with available+reason.

    Auth: inherited from router-level require_auth (do NOT add per-route).

    Never returns an empty `formats` dict, never 404s, never 500s (D-10) — an
    unreadable config or missing output directory degrades to a manifest
    where every format is unavailable with REASON_NO_SCAN, exactly the
    fail-to-safe-empty-value discipline exposure_map.py's crown-jewel loader
    uses.
    """
    try:
        outdir = _output_directory()
        if outdir is None or not outdir.is_dir():
            return ReportManifestResponse(
                scan_time=None,
                stamp=None,
                formats={
                    fmt: ReportFormatAvailability(available=False, reason=REASON_NO_SCAN)
                    for fmt in REPORT_FORMATS
                },
            )

        stamp, scan_time = _select_stamp(outdir)
        formats = {}
        for fmt in REPORT_FORMATS:
            available, reason = _format_availability(outdir, stamp, fmt)
            formats[fmt] = ReportFormatAvailability(available=available, reason=reason)

        return ReportManifestResponse(scan_time=scan_time, stamp=stamp, formats=formats)
    except Exception:
        logger.exception("report manifest derivation failed; surfacing as unavailable")
        return ReportManifestResponse(
            scan_time=None,
            stamp=None,
            formats={
                fmt: ReportFormatAvailability(available=False, reason=REASON_NO_SCAN)
                for fmt in REPORT_FORMATS
            },
        )


# IMPORTANT route ordering: /reports/latest/manifest is declared BEFORE
# /reports/latest/{fmt}. Not strictly necessary given the Literal constraint
# excludes "manifest", but the explicit ordering makes the intent legible and
# survives a future enum change.


@router.get("/reports/latest/{fmt:path}")
def download_report(fmt: ReportFormat) -> FileResponse:
    """GET /api/reports/latest/{fmt} — stream an on-disk artifact.

    `fmt` is `Literal`-typed, and the route uses Starlette's `:path`
    converter so the CAPTURED segment can contain `/` — this is what lets a
    single route intercept both a single unlisted string ("nonexistent")
    AND a multi-segment traversal payload ("../../../etc/passwd") with the
    exact same enum-membership check, rather than falling through to
    `app.py`'s SPA catch-all (which would otherwise return 200 with
    `index.html` for anything this router doesn't structurally claim).
    `_LiteralPathNotFoundRoute` (module-level, applied to this whole router)
    converts FastAPI's default 422-on-Literal-mismatch into an honest 404,
    since an unlisted `fmt` is a routing miss (D-04's enum IS the routing
    rule), not a malformed request. TRIPWIRE: if a future refactor replaces
    the `ReportFormat` annotation with a bare `str`, the containment
    property is lost; `tests/test_reports_download_route.py -k containment`
    is what catches that regression.

    Auth: inherited from router-level require_auth (do NOT add per-route).
    """
    outdir = _output_directory()
    if outdir is None or not outdir.is_dir():
        raise HTTPException(status_code=404, detail="No report artifacts are available yet.")

    stamp, _scan_time = _select_stamp(outdir)
    if stamp is None:
        raise HTTPException(status_code=404, detail="No report artifacts are available yet.")

    path = _resolve_artifact_path(outdir, stamp, fmt)
    if not path.is_file():
        raise HTTPException(
            status_code=404, detail=f"The {fmt} report is not available for the latest scan."
        )

    return FileResponse(path, media_type=_FORMAT_MEDIA_TYPES[fmt], filename=path.name)
