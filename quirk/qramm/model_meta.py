"""QRAMM model staleness metadata — Phase 51.

Mirrors quirk/compliance/__init__.py staleness pattern (Phase 49 COMPLY-08).
STALENESS_THRESHOLD_DAYS is 90 (shorter than compliance's 365) because the
CSNP QRAMM toolkit is an active open-source project and the catalog should
be re-verified quarterly.

Source: github.com/csnp/qramm (MIT License).
The CLI surface (quirk qramm status) is Phase 55 (QRAMM-07) — not built here.
"""
from __future__ import annotations

# Per QRAMM-06 — quarterly re-verification cadence for an active open-source model.
# See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
STALENESS_THRESHOLD_DAYS: int = 90

QRAMM_MODEL = {
    "qramm_version": "1.0",
    "last_verified": "2026-05-05",
    "source_url": "https://qramm.org",
    "github_url": "https://github.com/csnp/qramm",
    "license": "MIT",
}
