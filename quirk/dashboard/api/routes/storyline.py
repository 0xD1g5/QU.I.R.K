"""GET /api/findings/{finding_id}/storyline — Phase 202 / Plan 03 (STORY-01).

Auth-gated (T-202-07), matching the identical router construction
`connectors.py` (Phase 193) already uses. Returns the narrative section of
one finding's storyline, assembled server-side from the existing Phase-99
`ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG` catalogs (D-05) — no fourth
narrative generator, no new catalog content written here or anywhere in the
dashboard layer.

D-06: `FindingItem.id` IS `CryptoEndpoint.id`, reused across every finding
`findings_for_endpoint` derives from that one endpoint row — so `id` alone
would silently return the wrong finding's storyline. `title` is therefore a
REQUIRED query parameter and the (id, title) pair is the real lookup key,
resolved via `finding_by_id_and_title`.

D-07: a finding whose text carries no catalog keyword returns `narrative`,
`quantum_impact`, and `remediation_guidance` all `None` with a 200 — this is
the COMMON case (most TLS finding classes carry no algorithm keyword), not
an error.

Phase 202 / Plan 05 (STORY-02, D-06/D-08/D-09) fills in the six
`theme_*`/`finding_position` fields via the fingerprint join described in
`_theme_attribution_for_finding` below: `canonical_cli_title()` (202-01) ->
`TicketingChannel.compute_fingerprint` -> `RemediationItemFingerprint` rows
-> D-08 tie-break -> `item_progress()` / `lift_context_for_scan()`. The join
is READ-ONLY — no row is ever added or persisted here — and degrades to honest
`None` (never a 500) when the fingerprint table is absent or empty.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.finding_title_bridge import canonical_cli_title
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.routes.scan import finding_by_id_and_title, lift_context_for_scan
from quirk.dashboard.api.schemas import FindingStoryline
from quirk.intelligence.remediation import REMEDIATION_KIND_SLUGS, item_progress
from quirk.models import RemediationItemFingerprint
from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG, _classify_finding
from quirk.ticketing.base import TicketingChannel

# D-08: the severity catch-all slug — never preferred over a specific
# title-based theme when both match the same finding (see
# _theme_attribution_for_finding). D-09 governs the opposite case: when this
# IS the finding's only matching slug, it is the finding's real theme and it
# renders.
_CATCHALL_SLUG = "high-impact-findings"

# slug -> display title, the reverse of REMEDIATION_KIND_SLUGS (interfaces
# item 5: "Do NOT synthesize a title from the slug"). Built once at import
# time from the single source of truth in quirk/intelligence/remediation.py.
_TITLE_FOR_SLUG: Dict[str, str] = {slug: title for title, slug in REMEDIATION_KIND_SLUGS.items()}

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])

# T-202-08: fixed detail strings only. Never the exception's own message,
# never the submitted title, never a filesystem path — the connectors.py:38-44
# (T-193-15) precedent this whole pattern is copied from.
_DETAIL_NO_SUCH_ENDPOINT = "Finding not found"
_DETAIL_NO_SUCH_TITLE = "Finding not found for the given title"
_DETAIL_INTERNAL_ERROR = "Storyline lookup failed"


def _theme_attribution_for_finding(db: Session, ep: Any, finding: Any) -> Dict[str, Any]:
    """The D-08/D-09 theme join, per <interfaces> in 202-05-PLAN.md.

    Read-only. Returns a dict of the six theme_*/finding_position fields,
    all `None` on any absence branch (A1: no CLI title, no fingerprint
    match, or no theme; A2: no modelable lift; A3: item_progress total is
    0) or on ANY internal failure (missing/empty
    `remediation_item_fingerprints` table, including a pre-Phase-179 DB
    raising `OperationalError: no such table`) — the whole block is wrapped
    in the same advisory try/except posture `_derive_roadmap` uses, so a
    fingerprint-join failure never turns a 200 into a 500 and never blanks
    the narrative section assembled independently by the caller.

    `finding_position` is ALWAYS None (UI-SPEC Assumption A4): `ORDER BY
    finding_fingerprint` is a real, deterministic, re-scan-stable ordering,
    but a hash-lexicographic "1 of 8" tells an operator nothing about
    sequence, severity, or priority and invites reading a meaningless
    ordinal as a rank. The blocker is semantic meaninglessness, not
    technical impossibility — nothing is computed here and then discarded;
    computing it and shipping it as null would still be it "wiring up the
    value" the UI-SPEC deliberately declined. What would change this
    decision: the constituent rows gaining a genuine severity, priority, or
    first-seen ordering key.
    """
    result: Dict[str, Any] = {
        "theme_slug": None,
        "theme_title": None,
        "theme_score_lift": None,
        "theme_finding_count": None,
        "theme_closed_count": None,
        "finding_position": None,  # UI-SPEC A4 — see docstring; never computed, always null.
    }

    try:
        cli_title = canonical_cli_title(finding.title)
        if cli_title is None:
            return result  # A1 — unbridged or unrecognised dashboard title.

        fingerprint = TicketingChannel.compute_fingerprint(
            {"host": ep.host, "port": ep.port, "title": cli_title}
        )

        rows = (
            db.query(RemediationItemFingerprint)
            .filter(
                RemediationItemFingerprint.scan_run_id == ep.scan_run_id,
                RemediationItemFingerprint.finding_fingerprint == fingerprint,
            )
            .all()
        )
        slugs = sorted({row.slug for row in rows if row.slug})

        if not slugs:
            return result  # A1 — genuinely no theme (e.g. untrusted-CA class).

        if len(slugs) == 1:
            slug = slugs[0]
            # D-09: whether or not it is the catch-all, a SINGLE matching
            # slug is this finding's real theme and it renders. The
            # catch-all-only branch (undersized-RSA class) is exactly this
            # path with slug == _CATCHALL_SLUG.
        else:
            # D-08: 2+ slugs — drop the severity catch-all, keep the
            # specific theme(s). SQLite row order is not a stable API
            # contract, so the remaining set is sorted before selection.
            specific = [s for s in slugs if s != _CATCHALL_SLUG]
            if not specific:
                # All matched slugs were the catch-all (not possible given
                # set semantics above, but fenced for completeness).
                slug = _CATCHALL_SLUG
            elif len(specific) == 1:
                slug = specific[0]
            else:
                # Not observed in live data (28/28 multi-theme cases pair
                # the catch-all with exactly one specific slug) — pick
                # deterministically and log loudly, per <interfaces> item 4.
                slug = specific[0]
                logger.warning(
                    "Finding fingerprint %s matched multiple SPECIFIC slugs %s "
                    "(deterministically chose %r) — D-08's tie-break assumes "
                    "at most one specific slug per fingerprint; this is the "
                    "documented trigger to revisit D-08.",
                    fingerprint,
                    specific,
                    slug,
                )

        result["theme_slug"] = slug
        result["theme_title"] = _TITLE_FOR_SLUG.get(slug)

        closed_count, total_count = item_progress(db, scan_run_id=ep.scan_run_id, slug=slug)
        if total_count > 0:
            # Never write 0 for a genuinely-zero total (A3's territory) —
            # `0 of 0` / `1 of 0` / `1 of null` are all UI-SPEC-forbidden.
            result["theme_finding_count"] = total_count
            result["theme_closed_count"] = closed_count

        lifts_by_slug = lift_context_for_scan(db, ep.scan_run_id)
        result["theme_score_lift"] = lifts_by_slug.get(slug)  # A2 if absent — never substitute 0.

        return result
    except Exception:
        logger.exception(
            "Theme attribution join failed for finding_id=%s (advisory-only, "
            "degrading to honest absence)",
            ep.id if ep is not None else None,
        )
        return {
            "theme_slug": None,
            "theme_title": None,
            "theme_score_lift": None,
            "theme_finding_count": None,
            "theme_closed_count": None,
            "finding_position": None,
        }


@router.get(
    "/findings/{finding_id}/storyline",
    response_model=FindingStoryline,
)
def get_finding_storyline(
    finding_id: int,
    title: str = Query(..., min_length=1, max_length=512),
    db: Session = Depends(get_db),
) -> FindingStoryline:
    """Return one finding's catalog-sourced storyline, keyed by (id, title).

    FastAPI's own `int` path coercion yields 422 on a non-numeric
    `finding_id`; the required `Query(...)` yields 422 on an omitted
    `title`. Neither is hand-validated here — no custom validator that
    would risk echoing the value back into an error message.
    """
    try:
        ep, finding = finding_by_id_and_title(db, finding_id, title)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all, see T-202-08
        logger.exception("Storyline lookup failed for finding_id=%s", finding_id)
        raise HTTPException(status_code=500, detail=_DETAIL_INTERNAL_ERROR) from exc

    if ep is None:
        # No such CryptoEndpoint.id at all.
        raise HTTPException(status_code=404, detail=_DETAIL_NO_SUCH_ENDPOINT)
    if finding is None:
        # Endpoint exists, but no finding on it matches the given title —
        # a DIFFERENT fixed detail, distinguishable in logs/tests, still
        # containing neither the submitted title nor a path (T-202-09).
        raise HTTPException(status_code=404, detail=_DETAIL_NO_SUCH_TITLE)

    try:
        narrative: Optional[str] = None
        quantum_impact: Optional[str] = None
        remediation_guidance: Optional[str] = None

        # _classify_finding reads severity/title/description/category/
        # check_id (quirk/reports/content_model.py:690-710). FindingItem has
        # no `category` or `check_id` counterpart, so only the three fields
        # it actually carries are supplied.
        classify_input: Dict[str, Any] = {
            "severity": finding.severity,
            "title": finding.title,
            "description": finding.description or "",
        }
        crypto_class = _classify_finding(classify_input)

        if crypto_class is not None:
            # ALGO_IMPACT_MAP[key] is a 3-tuple:
            # (risk_label, impact_sentence, quantum_risk_sentence)
            # (quirk/reports/content_model.py:230-232).
            #
            # narrative: composed the same way the executive report composes
            # risk_label + impact_sentence — mirrors the markdown join at
            # quirk/reports/executive.py:432
            # (f"- **{risk.risk_label}** — {risk.impact_sentence}"), minus
            # the markdown emphasis since this is a plain-text API field.
            #
            # quantum_impact: index [2] verbatim — the same composition
            # findings_evaluator._build_finding uses for its own
            # `quantum_risk` field (quirk/engine/findings_evaluator.py:122-125).
            #
            # remediation_guidance: REMEDIATION_CATALOG[key] verbatim — the
            # same composition findings_evaluator._build_finding uses for its
            # own `recommendation` field when a catalog entry exists
            # (quirk/engine/findings_evaluator.py:115-116). No fallback
            # boilerplate (NIST_IR_8547_DEPRECATION) is appended here: that
            # branch only fires in _build_finding when there is NO catalog
            # match, which is exactly the case this route leaves as honest
            # `None` per D-07 rather than authoring new text.
            if crypto_class in ALGO_IMPACT_MAP:
                risk_label, impact_sentence, quantum_risk_sentence = ALGO_IMPACT_MAP[crypto_class]
                narrative = f"{risk_label} — {impact_sentence}"
                quantum_impact = quantum_risk_sentence
            if crypto_class in REMEDIATION_CATALOG:
                remediation_guidance = REMEDIATION_CATALOG[crypto_class]

        # 202-05 (STORY-02, D-06/D-08/D-09): the theme-attribution join is
        # independent of the narrative assembly above — its own advisory
        # try/except means a fingerprint-join failure degrades ONLY the six
        # theme_*/finding_position fields to None, never the narrative
        # fields already computed (UI-SPEC S6: the two data paths must not
        # take each other down).
        theme_fields = _theme_attribution_for_finding(db, ep, finding)

        return FindingStoryline(
            finding_id=finding_id,
            narrative=narrative,
            quantum_impact=quantum_impact,
            remediation_guidance=remediation_guidance,
            **theme_fields,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all, see T-202-08
        logger.exception("Storyline narrative assembly failed for finding_id=%s", finding_id)
        raise HTTPException(status_code=500, detail=_DETAIL_INTERNAL_ERROR) from exc
