"""Phase 179 Plan 03: write remediation identity and membership at scan time.

This module writes remediation ITEM rows and their constituent FINGERPRINT
join rows, explicitly, once per scan. It does NOT compute closure (Phase
180's two-sided condition — detected by a previous scan AND verified absent
by the current one) and it does NOT surface anything (Phase 181's CBOM/VEX/
report/dashboard work). It deliberately never imports the quantum-readiness
weighting module anywhere (ADVISORY-01) — ``build_phased_roadmap`` is called
with its second, driver-decoration-only argument passed as an EMPTY mapping
(``{}``), which structurally removes that module from this path rather than
merely avoiding it by convention. See
``tests/test_remediation_advisory_guard.py`` for the falsifiable AST proof.
This docstring itself avoids naming that module so a plain-text search of
this file for its name finds nothing to find.

The concrete defect this fixes: today ``_add_candidate``
(``quirk/intelligence/roadmap.py``) merges candidates into an in-memory dict
keyed by TITLE and persists nothing. With 8 plaintext-HTTP endpoints: fixing
1 closes nothing (there is nowhere for the closed state to live), fixing the 8th
makes the item silently vanish with no closure record, and rewording the
title re-keys its entire history. Writing membership EXPLICITLY at scan
time — never recomputing it at read time from evidence counters, which IS
the current defect — is what makes "6 of 8 verified closed" a queryable
fact instead of a boolean guess.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from quirk.compliance import FINGERPRINT_TITLE_ALIASES, normalize_finding_title
from quirk.db import get_session
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.remediation import (
    DEFAULT_ITEM_STATE,
    REMEDIATION_CONSTITUENCY,
    slug_for_title,
)
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.models import RemediationItem, RemediationItemFingerprint
from quirk.ticketing.base import TicketingChannel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# `build_phased_roadmap`'s returned item dict does NOT include the numeric
# `priority` used to break ties in `_add_candidate` — it is stripped before
# the function returns (see quirk/intelligence/roadmap.py's `final_items`
# construction). This table mirrors the `priority=` values already declared,
# per-slug, as inline comments next to REMEDIATION_KIND_SLUGS in
# quirk/intelligence/remediation.py. It is duplicated data, not derived,
# because remediation.py (Plan 01's output) intentionally exposes only a
# flat title->slug map and this plan does not modify that file. If Plan 01's
# comment values ever change, this table must change with them —
# `tests/test_remediation_persist.py` pins every value against a fresh read
# of the source comments.
# ---------------------------------------------------------------------------
_SLUG_PRIORITY: Dict[str, int] = {
    "plaintext-http-exposure": 10,
    "high-impact-findings": 20,
    "expired-certificates": 30,
    "scan-reliability": 40,
    "unknown-open-services": 50,
    "near-expiry-certificates": 60,
    "self-signed-certificates": 70,
    "legacy-tls-versions": 80,
    "tls-enum-coverage": 90,
    "ecdsa-adoption-planning": 100,
    "mtls-lifecycle-operations": 110,
    "assign-owners-and-slas": 900,
    "automate-evidence-refresh": 910,
    "crypto-governance-review": 920,
}

_HIGH_IMPACT_SEVERITIES = frozenset({"HIGH", "CRITICAL"})


def _normalized(title: str) -> str:
    return normalize_finding_title(str(title or ""), FINGERPRINT_TITLE_ALIASES)


def _select_constituent_findings(
    kind: str,
    constituency_titles: Sequence[str],
    findings: Sequence[Mapping[str, Any]],
) -> List[Mapping[str, Any]]:
    """Return the findings that constitute one item, by its constituency kind.

    fingerprint  -> findings whose normalised title matches a normalised
                    constituency title.
    severity     -> findings at HIGH or CRITICAL severity, whatever the title.
    evidence_only -> nothing constitutes it; no finding backs it.
    """
    if kind == "fingerprint":
        wanted = {_normalized(t) for t in constituency_titles}
        return [f for f in findings if _normalized(f.get("title")) in wanted]
    if kind == "severity":
        return [
            f for f in findings
            if str(f.get("severity") or "").upper() in _HIGH_IMPACT_SEVERITIES
        ]
    # "evidence_only" — deliberately zero constituents (see remediation.py).
    return []


def _earliest_scan_run_id_for_slug(session, slug: str, fallback: str) -> str:
    existing = (
        session.query(RemediationItem)
        .filter(RemediationItem.slug == slug)
        .order_by(RemediationItem.created_at.asc().nullslast())
        .first()
    )
    if existing is not None and existing.scan_run_id:
        return existing.scan_run_id
    return fallback


def _upsert_item(
    session,
    *,
    slug: str,
    scan_run_id: str,
    title: str,
    phase: str,
    priority: Optional[int],
    constituency: str,
) -> RemediationItem:
    row = (
        session.query(RemediationItem)
        .filter(
            RemediationItem.slug == slug,
            RemediationItem.scan_run_id == scan_run_id,
        )
        .first()
    )
    if row is not None:
        # Idempotent re-run of the SAME scan_run_id: refresh display fields
        # only. Never touch state, first_seen_scan_run_id, or created_at —
        # those are identity/history facts, not display facts.
        row.title = title
        row.phase = phase
        row.priority = priority
        row.constituency = constituency
        return row

    first_seen = _earliest_scan_run_id_for_slug(session, slug, scan_run_id)
    row = RemediationItem(
        slug=slug,
        scan_run_id=scan_run_id,
        title=title,
        phase=phase,
        priority=priority,
        constituency=constituency,
        state=DEFAULT_ITEM_STATE,  # D-12: never write the closed state here.
        first_seen_scan_run_id=first_seen,
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()  # assign row.id before writing join rows
    return row


def _existing_fingerprints(session, *, scan_run_id: str, slug: str) -> set:
    rows = (
        session.query(RemediationItemFingerprint.finding_fingerprint)
        .filter(
            RemediationItemFingerprint.scan_run_id == scan_run_id,
            RemediationItemFingerprint.slug == slug,
        )
        .all()
    )
    return {r[0] for r in rows}


def persist_remediation_snapshot(
    db_path: str,
    scan_run_id: Optional[str],
    endpoints: Iterable[Any],
    findings: Optional[Iterable[Mapping[str, Any]]],
) -> Dict[str, int]:
    """Write remediation items and their constituent fingerprints for one scan.

    Returns a counters dict for the caller to log:
      {"items": N written/updated, "fingerprints": M join rows written,
       "skipped_findings": K roadmap candidates with no resolvable slug}.

    This function must NEVER be able to fail a scan: remediation persistence
    is advisory bookkeeping layered on top of endpoint data that has already
    been produced and persisted. Any exception here is caught, logged, and
    reported back as zeroed counters.
    """
    counters = {"items": 0, "fingerprints": 0, "skipped_findings": 0}

    if not scan_run_id or not db_path:
        logger.warning(
            "remediation_persist: skipped — missing scan_run_id or db_path"
        )
        return counters

    try:
        endpoint_list = list(endpoints)
        finding_list = list(findings) if findings is not None else []

        evidence = build_evidence_summary(endpoint_list, finding_list)
        # ADVISORY-01: empty second-argument mapping — this call never
        # transits the quantum-readiness weighting module. That argument
        # only decorates the human-readable `why` text; it has zero effect
        # on which titles are emitted.
        roadmap = build_phased_roadmap(evidence, {})

        with get_session(db_path) as session:
            for item in roadmap.get("items", []):
                title = item.get("title", "")
                slug = slug_for_title(title)
                if slug is None:
                    # Either one of the 3 endpoints==0 fallback titles
                    # (deliberately excluded, see REMEDIATION_EXCLUDED_TITLES)
                    # or a genuinely unmapped title — either way this is a
                    # silent-drift hazard worth a single warning line, but
                    # never an unmapped item and never a raise.
                    counters["skipped_findings"] += 1
                    logger.warning(
                        "remediation_persist: no slug for roadmap title %r "
                        "— skipping (excluded fallback title or unmapped)",
                        title,
                    )
                    continue

                kind, constituency_titles = REMEDIATION_CONSTITUENCY.get(
                    slug, ("evidence_only", ())
                )
                row = _upsert_item(
                    session,
                    slug=slug,
                    scan_run_id=scan_run_id,
                    title=title,
                    phase=item.get("phase"),
                    priority=_SLUG_PRIORITY.get(slug),
                    constituency=kind,
                )
                counters["items"] += 1

                constituents = _select_constituent_findings(
                    kind, constituency_titles, finding_list
                )
                if not constituents:
                    continue

                seen_fps = _existing_fingerprints(
                    session, scan_run_id=scan_run_id, slug=slug
                )
                for finding in constituents:
                    fp = TicketingChannel.compute_fingerprint(dict(finding))
                    if fp in seen_fps:
                        continue
                    seen_fps.add(fp)
                    session.add(
                        RemediationItemFingerprint(
                            remediation_item_id=row.id,
                            slug=slug,
                            scan_run_id=scan_run_id,
                            finding_fingerprint=fp,
                            host=finding.get("host"),
                            port=finding.get("port"),
                            finding_title=finding.get("title"),
                            state=DEFAULT_ITEM_STATE,  # D-12: never write the closed state here.
                            observed_at=datetime.now(timezone.utc),
                        )
                    )
                    counters["fingerprints"] += 1
        return counters
    except Exception as exc:  # noqa: BLE001 — must never fail a scan
        logger.error("remediation_persist: failed, continuing scan: %r", exc)
        return {"items": 0, "fingerprints": 0, "skipped_findings": 0}
