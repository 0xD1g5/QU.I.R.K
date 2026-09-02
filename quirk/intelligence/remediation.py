"""Phase 179: remediation item identity, state vocabulary, and progress reads.

Phase boundary (one sentence, per plan): this module models and persists
identity and state; it does NOT compute closure (Phase 180's two-sided
condition — detected by a previous scan AND verified absent by the current
one) and does NOT surface anything (Phase 181's CBOM/VEX/report/dashboard
work).
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
# ---------------------------------------------------------------------------
ITEM_STATES: Tuple[str, ...] = ("open", "closed", "not_observed")
DEFAULT_ITEM_STATE = "not_observed"


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
