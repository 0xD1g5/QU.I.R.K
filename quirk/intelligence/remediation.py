"""Phase 179: remediation item identity, state vocabulary, and progress reads.

Phase boundary (one sentence, per plan): this module models and persists
identity and state; it does NOT compute closure (Phase 180's two-sided
condition — detected by a previous scan AND verified absent by the current
one) and does NOT surface anything (Phase 181's CBOM/VEX/report/dashboard
work).

Phase 180 Plan 03: this module now also owns the four-member state
vocabulary Phase 180 writes into (`resurfaced` added alongside
`open`/`closed`/`not_observed`), the `OPEN_LIKE_STATES` counted-as-open
grouping, and the `CLOSURE_EVENT_TYPES` write-site allowlist for
`RemediationClosureEvent.event_type`. It still does not compute closure or
resurface transitions itself — that decision lives in
`quirk/intelligence/closure.py` (Plans 04/05).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

REMEDIATION_MODEL_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# The closed candidate set: every title `build_phased_roadmap` can emit,
# mapped to a stable, kind-derived slug. This is the ONLY place a slug is
# defined — never derive a slug from title at a call site. D-01 rejects
# title-derived IDs outright: the whole point is that rewording a title must
# not re-key history. Verified by full-file read of
# quirk/intelligence/roadmap.py, 2026-09-02.
# ---------------------------------------------------------------------------
REMEDIATION_KIND_SLUGS: Dict[str, str] = {
    # title                                                  slug                            phase  priority
    "Remove plaintext HTTP exposure": "plaintext-http-exposure",                            # NOW    10
    "Triage high-impact findings": "high-impact-findings",                                  # NOW    20
    "Replace expired certificates": "expired-certificates",                                 # NOW    30
    "Stabilize scan reliability": "scan-reliability",                                       # NOW    40
    "Classify unknown open services": "unknown-open-services",                              # NEXT   50
    "Renew near-expiry certificates": "near-expiry-certificates",                           # NEXT   60
    "Migrate self-signed certificates to managed PKI": "self-signed-certificates",           # NEXT   70
    "Disable legacy TLS versions": "legacy-tls-versions",                                   # NEXT   80
    "Increase TLS enumeration coverage": "tls-enum-coverage",                               # NEXT   90
    "Plan ECDSA adoption": "ecdsa-adoption-planning",                                       # LATER  100
    "Standardize mTLS lifecycle operations": "mtls-lifecycle-operations",                   # LATER  110
    "Assign remediation owners and SLAs": "assign-owners-and-slas",                         # NOW    900
    "Automate evidence refresh cadence": "automate-evidence-refresh",                       # NEXT   910
    "Establish crypto governance review": "crypto-governance-review",                       # LATER  920
}

# The 3 zero-endpoint fallback titles (quirk/intelligence/roadmap.py lines
# ~419-460). EXCLUDED from remediation_items and given NO slug: they fire
# only in the `endpoints == 0` branch and by construction have zero
# constituent findings, so a row for them would be indistinguishable from
# not_observed and would misrepresent onboarding work as remediation
# posture. Listed here, separately, so the closed-set guard can prove they
# were considered and rejected — not forgotten.
REMEDIATION_EXCLUDED_TITLES: frozenset = frozenset(
    {
        "Collect initial asset scope",
        "Run baseline discovery and fingerprinting",
        "Establish recurring readiness reporting",
    }
)

# ---------------------------------------------------------------------------
# Constituency: what kind of evidence constitutes each remediation item.
# Three kinds, exactly:
#   "fingerprint"   — constituted by findings matched on normalised title
#   "severity"      — constituted by every finding at HIGH/CRITICAL severity,
#                      whatever its title
#   "evidence_only" — no finding constitutes it; driven by a scan-level
#                      counter, so per-fingerprint progress is structurally
#                      unavailable and Phase 180 must leave it not_observed.
#                      This is an honest declaration of a limitation, NOT a
#                      TODO — do not apply it to any fingerprint-backed item
#                      because wiring join rows is fiddly.
# ---------------------------------------------------------------------------
REMEDIATION_CONSTITUENCY: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "plaintext-http-exposure": (
        "fingerprint",
        (
            "Plaintext HTTP service detected",
            "HTTP on TLS-designated port",
            "Plaintext AMQP listener detected",
            "Plaintext Kafka listener detected",
            "Plaintext Redis listener (no auth)",
        ),
    ),
    "expired-certificates": ("fingerprint", ("TLS certificate expired",)),
    "near-expiry-certificates": (
        "fingerprint",
        ("TLS certificate expiring within 30 days",),
    ),
    "self-signed-certificates": ("fingerprint", ("TLS certificate is self-signed",)),
    "legacy-tls-versions": (
        "fingerprint",
        (
            "Legacy TLS versions allowed (TLS 1.0/1.1)",
            "Legacy TLS cipher suites accepted",
        ),
    ),
    "unknown-open-services": ("fingerprint", ("Unknown open service",)),
    "high-impact-findings": ("severity", ()),
    "scan-reliability": ("evidence_only", ()),
    "tls-enum-coverage": ("evidence_only", ()),
    "ecdsa-adoption-planning": ("evidence_only", ()),
    "mtls-lifecycle-operations": ("evidence_only", ()),
    "assign-owners-and-slas": ("evidence_only", ()),
    "automate-evidence-refresh": ("evidence_only", ()),
    "crypto-governance-review": ("evidence_only", ()),
}

# ---------------------------------------------------------------------------
# State vocabulary. D-12: an unmatched item defaults to not_observed, NEVER
# closed — absence must never imply remediation.
#
# Phase 180 Plan 03 (CLOSE-02) — D-20: `resurfaced` is APPENDED as a fourth
# member, not inserted alphabetically, so every pre-existing member keeps its
# existing tuple index (a consumer that wrongly indexes the tuple keeps
# working) while the exact-tuple drift guard in
# tests/test_remediation_item_model.py still pins the literal value.
#
# `resurfaced` means a previously-`closed` item was detected again by a
# later scan. It is COUNTED AS OPEN via `OPEN_LIKE_STATES` (D-21) and
# REPORTED SEPARATELY — folding it silently into `open` would lose the
# signal that remediation regressed, which is precisely the fact a client
# attestation needs. A scope-signature mismatch can never produce
# `resurfaced` either — the same hard refusal that governs closure:
# comparing incomparable scans yields `not_observed` in both directions.
#
# The transition itself (deciding an item is newly `closed`, newly
# `resurfaced`, or `reclosed` after a resurface) is NEVER decided here — that
# is `quirk/intelligence/closure.py`'s job (Plans 04/05). This module only
# owns the vocabulary those decisions are written into.
# ---------------------------------------------------------------------------
ITEM_STATES: Tuple[str, ...] = ("open", "closed", "not_observed", "resurfaced")
DEFAULT_ITEM_STATE = "not_observed"
RESURFACED_STATE = "resurfaced"

# D-21: a named constant, not an inline `in ("open", "resurfaced")` at each
# call site — a future counter that forgets `resurfaced` under-reports open
# work visibly (import error / grep hit) rather than silently.
OPEN_LIKE_STATES: Tuple[str, ...] = ("open", "resurfaced")

# D-22: the event-type allowlist for RemediationClosureEvent.event_type
# lives here (the writer module), never in quirk/models.py — mirrors
# HardwareDriftEvent's T-155-03 precedent exactly. Validated at the write
# site (Plan 04/05), never stored as free text.
CLOSURE_EVENT_TYPES: Tuple[str, ...] = ("closed", "resurfaced", "reclosed")


def slug_for_title(title: str) -> Optional[str]:
    """Exact-match lookup against REMEDIATION_KIND_SLUGS.

    Returns None for excluded and unknown titles. No fuzzy matching, no
    normalisation fallback: an unmapped title must be visibly unmapped, not
    silently coerced.
    """
    return REMEDIATION_KIND_SLUGS.get(title)


def item_progress(session, *, scan_run_id: str, slug: str) -> Tuple[int, int]:
    """Return (closed_count, total_count) of constituent fingerprint rows.

    This READS persisted state, it does not DECIDE it. In Phase 179 no code
    path ever writes "closed"; Phase 180 owns that transition. The function
    exists now so that "6 of 8 verified closed" is provably expressible
    against the schema.
    """
    from quirk.models import RemediationItemFingerprint

    rows = (
        session.query(RemediationItemFingerprint)
        .filter(
            RemediationItemFingerprint.scan_run_id == scan_run_id,
            RemediationItemFingerprint.slug == slug,
        )
        .all()
    )
    total_count = len(rows)
    closed_count = sum(1 for row in rows if row.state == "closed")
    return (closed_count, total_count)
