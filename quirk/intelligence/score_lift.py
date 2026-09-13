"""Phase 201 (LIFT-01/LIFT-02) — real forward-projection score lifts.

READ-ONLY forward projection over synthetic evidence: every value this module
produces comes from re-invoking the production scorer
(``quirk.intelligence.scoring.compute_readiness_score``) against a
``copy.deepcopy`` of the caller's evidence with one or more fields
hand-mutated to model "this remediation item is resolved". Nothing here is a
static heuristic table, and nothing here may ever reach a real score surface
— that boundary is machine-enforced by the ADVISORY-02 firewall
(``tests/test_forward_projection_firewall.py``), including its three
runtime purity legs (evidence deep-equality, DB-session isolation, base-score
invariance). This module must never import ``quirk.db``, any model, or any
persistence/report module.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from quirk.intelligence.remediation import slug_for_title
from quirk.intelligence.scoring import compute_readiness_score

# ---------------------------------------------------------------------------
# Evidence-Delta Map (201-RESEARCH) — the 9 modelable slugs. Each mutator
# takes a mutable evidence dict (always a fresh `copy.deepcopy`, never the
# caller's live mapping) and resolves it in place, mirroring exactly one row
# of the map. Sub-dicts are created defensively so a sparse evidence mapping
# never raises.
# ---------------------------------------------------------------------------


def _ensure(evidence: Dict[str, Any], key: str) -> Dict[str, Any]:
    sub = evidence.get(key)
    if not isinstance(sub, dict):
        sub = {}
        evidence[key] = sub
    return sub


def _resolve_plaintext_http_exposure(evidence: Dict[str, Any]) -> None:
    evidence["plaintext_http_count"] = 0
    evidence["http_on_tls_port_count"] = 0


def _resolve_high_impact_findings(evidence: Dict[str, Any]) -> None:
    sev = _ensure(evidence, "finding_severity_counts")
    # Do NOT decrement totals.findings — the agility ratio denominator is
    # max(findings, 1); zeroing only the HIGH/CRITICAL numerator is the
    # honest model (plan action notes).
    sev["HIGH"] = 0
    sev["CRITICAL"] = 0


def _resolve_expired_certificates(evidence: Dict[str, Any]) -> None:
    cert_obs = _ensure(evidence, "certificate_observations")
    cert_obs["expired_count"] = 0


def _resolve_near_expiry_certificates(evidence: Dict[str, Any]) -> None:
    cert_obs = _ensure(evidence, "certificate_observations")
    cert_obs["expiring_count"] = 0


def _resolve_self_signed_certificates(evidence: Dict[str, Any]) -> None:
    cert_obs = _ensure(evidence, "certificate_observations")
    cert_obs["self_signed_count"] = 0


def _resolve_scan_reliability(evidence: Dict[str, Any]) -> None:
    scan_error = _ensure(evidence, "scan_error")
    scan_error["rate"] = 0.0


def _resolve_unknown_open_services(evidence: Dict[str, Any]) -> None:
    protocol_counts = _ensure(evidence, "protocol_counts")
    protocol_counts["UNKNOWN"] = 0


def _resolve_legacy_tls_versions(evidence: Dict[str, Any]) -> None:
    sev = _ensure(evidence, "finding_severity_counts")
    sev["LOW"] = 0


def _resolve_ecdsa_adoption_planning(evidence: Dict[str, Any]) -> None:
    cert_keys = _ensure(evidence, "cert_key_type_counts")
    # Flip the flat RSA-only penalty to the flat has-ECDSA bonus. Magnitude
    # is count-independent, so 1 suffices; RSA is left untouched.
    cert_keys["ECDSA"] = 1


_DELTAS: Dict[str, Callable[[Dict[str, Any]], None]] = {
    "plaintext-http-exposure": _resolve_plaintext_http_exposure,
    "high-impact-findings": _resolve_high_impact_findings,
    "expired-certificates": _resolve_expired_certificates,
    "near-expiry-certificates": _resolve_near_expiry_certificates,
    "self-signed-certificates": _resolve_self_signed_certificates,
    "scan-reliability": _resolve_scan_reliability,
    "unknown-open-services": _resolve_unknown_open_services,
    "legacy-tls-versions": _resolve_legacy_tls_versions,
    "ecdsa-adoption-planning": _resolve_ecdsa_adoption_planning,
}

# The 5 deliberately-absent kinds: the scorer reads no key their resolution
# would change, so no honest mutation exists. Absence here is the
# deliverable, not a gap — never fall back to a heuristic number for these.
#   tls-enum-coverage          — tls_enum_coverage_ratio is not read by
#                                 compute_readiness_score's subscores at all.
#   mtls-lifecycle-operations  — mtls_present_count only gates whether the
#                                 identity_trust subscore is *assessed*, it
#                                 never adjusts its VALUE once assessed.
#   assign-owners-and-slas     — a baseline-filler roadmap item with no
#                                 scoring evidence key of its own.
#   automate-evidence-refresh  — a baseline-filler roadmap item with no
#                                 scoring evidence key of its own.
#   crypto-governance-review   — an always-forced baseline item with no
#                                 scoring evidence key of its own.


def _slugs_for_items(items: Sequence[Mapping[str, Any]]) -> Sequence[str]:
    slugs = []
    for item in items:
        title = item.get("title")
        if title is None:
            continue
        slug = slug_for_title(title)
        if slug is not None:
            slugs.append(slug)
    return slugs


def compute_item_lifts(
    evidence: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    *,
    profile: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, int]:
    """Per-item lift = an independent rescore delta for each modelable item.

    Each lift is `compute_readiness_score(deepcopy+mutate)["score"] - base`,
    recorded only when strictly positive. Slugs with no delta entry (the 5
    honest-absence kinds, plus the 3 zero-endpoint fallback titles for which
    `slug_for_title` returns None) never appear as keys — never 0, never
    negative, never a heuristic.
    """
    base = compute_readiness_score(evidence, profile=profile, weights=weights)
    base_score = base.get("score")
    if base_score is None:
        return {}

    lifts: Dict[str, int] = {}
    for slug in dict.fromkeys(_slugs_for_items(items)):
        mutator = _DELTAS.get(slug)
        if mutator is None:
            continue
        candidate: Dict[str, Any] = copy.deepcopy(evidence)  # type: ignore[assignment]
        mutator(candidate)
        projected = compute_readiness_score(candidate, profile=profile, weights=weights)
        projected_score = projected.get("score")
        if projected_score is None:
            continue
        delta = projected_score - base_score
        if delta > 0:
            lifts[slug] = int(delta)
    return lifts


def compute_projected_score(
    evidence: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    *,
    profile: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> Optional[int]:
    """Aggregate projection = ONE rescore of a single all-resolved deep copy.

    LIFT-02: this is deliberately a single-rescore shape, never a sum of
    per-item lifts — the 25-point subscore clamp in scoring.py's
    `_apply_weighted_impacts` makes lifts non-additive (resolving several
    items at once can share the same clamp headroom that per-item lifts each
    counted individually), so summing would overstate the achievable gain.
    """
    base = compute_readiness_score(evidence, profile=profile, weights=weights)
    if base.get("score") is None:
        return None

    resolved: Dict[str, Any] = copy.deepcopy(evidence)  # type: ignore[assignment]
    for slug in dict.fromkeys(_slugs_for_items(items)):
        mutator = _DELTAS.get(slug)
        if mutator is not None:
            mutator(resolved)

    projected = compute_readiness_score(resolved, profile=profile, weights=weights)
    return projected.get("score")
