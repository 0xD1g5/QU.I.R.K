"""Phase 201 (LIFT-01/LIFT-02) — behavioral spec for the score-lift
computation, pinned failing-first: ``quirk/intelligence/score_lift.py`` does
not exist yet (this whole file is RED until Plan 201-02 lands it — see
201-01-SUMMARY.md for the recorded collection-error transcript).

Every expected lift/projection value in this file is derived INDEPENDENTLY,
inside the test, by hand-applying the evidence mutation from
201-RESEARCH.md's Evidence-Delta Map and calling the existing, unmodified
``compute_readiness_score`` — never by calling the module under test twice to
manufacture its own expected value. The two exceptions are the non-additivity
test and the determinism test, which are inherently about the RELATIONSHIP
between the module's own two outputs (``compute_item_lifts`` vs
``compute_projected_score``; two identical calls), not about pinning a
specific number.

Mirrors ``tests/test_intelligence_roadmap.py``'s fixture-dict-in, dict-out,
deterministic pure-function testing style — including its exact 6-key
``set(item.keys())`` assertion (roadmap.py:52-56), re-asserted here after
calling ``compute_item_lifts`` to prove lift attachment happens OUTSIDE
``build_phased_roadmap`` (roadmap.py stays byte-unchanged, per this plan's
hard constraint).
"""
from __future__ import annotations

import copy

from quirk.intelligence.remediation import slug_for_title
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.intelligence.score_lift import (
    compute_item_lifts,
    compute_projected_score,
)
from quirk.intelligence.scoring import compute_readiness_score

# The 9 modelable slugs (201-RESEARCH §Evidence-Delta Map) — the only slugs
# `compute_item_lifts` may ever emit as a key.
_MODELABLE_SLUGS = frozenset(
    {
        "plaintext-http-exposure",
        "high-impact-findings",
        "expired-certificates",
        "scan-reliability",
        "unknown-open-services",
        "near-expiry-certificates",
        "self-signed-certificates",
        "legacy-tls-versions",
        "ecdsa-adoption-planning",
    }
)

# The 5 honest-absence slugs — never modelable, must never appear as a key
# even when the roadmap item is present (201-RESEARCH §Evidence-Delta Map).
_ABSENT_SLUGS = frozenset(
    {
        "tls-enum-coverage",
        "mtls-lifecycle-operations",
        "assign-owners-and-slas",
        "automate-evidence-refresh",
        "crypto-governance-review",
    }
)


def _evidence() -> dict:
    """A healthy-but-flawed scan triggering several modelable items at once,
    plus two non-modelable items (tls-enum-coverage, and the always-forced
    crypto-governance-review baseline) — enough surface to pin per-item
    lifts, realness, aggregate equality, and determinism without saturating
    any subscore's 25-point clamp (see `_clamp_binding_evidence` for the
    deliberately-saturating fixture).
    """
    return {
        "totals": {"endpoints": 10, "findings": 8},
        "protocol_counts": {
            "TLS": 6,
            "HTTP": 2,
            "SSH": 1,
            "UNKNOWN": 1,
            "KERBEROS": 1,
            "POSTGRESQL": 1,
            "SMTPS": 1,
        },
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 0,
        "certificate_observations": {
            "expired_count": 2,
            "expiring_count": 1,
            "self_signed_count": 1,
            "certs_observed": 8,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.1},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
        "tls_enum_coverage_ratio": 0.5,
    }


def _clamp_binding_evidence() -> dict:
    """Same shape as `_evidence`, but with hygiene-subscore penalties
    (plaintext HTTP + HTTP-on-TLS-port ratios, against only 2 endpoints)
    deliberately exceeding the 25-point clamp headroom, verified below by
    `test_clamp_binding_fixture_actually_binds`.

    Unclamped hygiene penalty at these values:
        plaintext_ratio(2/2=1.0)*18 + http_on_tls_ratio(2/2=1.0)*16
            + scan_error_rate(0.5)*6
        = 18 + 16 + 3 = 37 > 25 (score_cap) -> hygiene clamps to 0.

    Live scratch run recorded during execution (201-01-SUMMARY.md) confirmed:
    base score=33 (hygiene=0, clamped from an unclamped -12), and resolving
    each of the 9 modelable items in isolation and summing their lifts
    (=70) strictly exceeds the one true aggregate rescore's lift (=67) —
    the non-additivity this fixture exists to prove.
    """
    return {
        "totals": {"endpoints": 2, "findings": 5},
        "protocol_counts": {"KERBEROS": 1, "UNKNOWN": 1},
        "plaintext_http_count": 2,
        "http_on_tls_port_count": 2,
        "mtls_present_count": 0,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 1,
            "self_signed_count": 1,
            "certs_observed": 3,
        },
        "cert_key_type_counts": {"RSA": 3, "ECDSA": 0},
        "scan_error": {"rate": 0.5},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
    }


def _absence_evidence() -> dict:
    """A fixture deliberately shaped to force ALL 5 honest-absence slugs
    into the roadmap's item list at once (mtls_present_count>0,
    tls_enum_coverage_ratio<0.85, and few enough modelable triggers that the
    `assign-owners-and-slas` / `automate-evidence-refresh` baseline-filler
    loop in `build_phased_roadmap` still fires before `min_items` is
    satisfied). Live scratch run recorded in 201-01-SUMMARY.md confirms this
    fixture's `items` list is EXACTLY the 5 absence slugs, in this order:
    assign-owners-and-slas, tls-enum-coverage, automate-evidence-refresh,
    mtls-lifecycle-operations, crypto-governance-review.
    """
    return {
        "totals": {"endpoints": 5, "findings": 2},
        "protocol_counts": {"KERBEROS": 1},
        "mtls_present_count": 1,
        "tls_enum_coverage_ratio": 0.5,
        "certificate_observations": {"certs_observed": 3},
        "cert_key_type_counts": {"RSA": 0, "ECDSA": 0},
    }


def _unassessed_evidence() -> dict:
    """Zero endpoints, no certs_observed, no protocol keys — every
    `_*_assessed()` predicate in scoring.py is False, so
    `compute_readiness_score` returns `score: None` / `rating:
    "NOT_ASSESSED"` (SCORE-06 honest absence)."""
    return {"totals": {"endpoints": 0, "findings": 0}}


def _items(evidence: dict) -> list:
    return build_phased_roadmap(evidence, compute_readiness_score(evidence))["items"]


# ---------------------------------------------------------------------------
# Fixture sanity checks (not behavior pins) — prove the fixtures actually
# exercise what the docstrings above claim, so a future scoring.py change
# that silently stops binding the clamp can't leave this suite vacuously
# green.
# ---------------------------------------------------------------------------


def test_clamp_binding_fixture_actually_binds() -> None:
    evidence = _clamp_binding_evidence()
    denom = max(0, evidence["totals"]["endpoints"]) or 1
    plaintext_ratio = evidence["plaintext_http_count"] / denom
    http_on_tls_ratio = evidence["http_on_tls_port_count"] / denom
    scan_error_rate = evidence["scan_error"]["rate"]
    unclamped_hygiene_penalty = (
        plaintext_ratio * 18.0 + http_on_tls_ratio * 16.0 + scan_error_rate * 6.0
    )
    assert unclamped_hygiene_penalty > 25.0, (
        "clamp-binding fixture does not actually exceed the 25-point hygiene "
        f"headroom: unclamped penalty={unclamped_hygiene_penalty}"
    )
    base = compute_readiness_score(evidence)
    assert base["subscores"]["hygiene"] == 0, (
        "clamp-binding fixture's hygiene subscore did not clamp to 0 as expected: "
        f"{base['subscores']}"
    )


def test_absence_fixture_yields_exactly_the_five_absent_slugs() -> None:
    evidence = _absence_evidence()
    items = _items(evidence)
    slugs = {slug_for_title(it["title"]) for it in items}
    assert slugs == _ABSENT_SLUGS, (
        f"absence fixture's roadmap items resolved to unexpected slugs: {slugs}"
    )


# ---------------------------------------------------------------------------
# Behavior 1: per-item lift is pinned, independently computed.
# ---------------------------------------------------------------------------


def test_per_item_lift_matches_independent_rescore_for_expired_certificates() -> None:
    evidence = _evidence()
    items = _items(evidence)
    base_score = compute_readiness_score(evidence)["score"]

    resolved = copy.deepcopy(evidence)
    resolved["certificate_observations"]["expired_count"] = 0
    expected_lift = compute_readiness_score(resolved)["score"] - base_score
    assert expected_lift > 0

    lifts = compute_item_lifts(evidence, items)
    assert lifts["expired-certificates"] == expected_lift


# ---------------------------------------------------------------------------
# Behavior 2: realness — changing weights changes the lift (not a static
# heuristic table).
# ---------------------------------------------------------------------------


def test_realness_weights_change_moves_the_lift_for_the_same_slug() -> None:
    evidence = _evidence()
    items = _items(evidence)

    default_lifts = compute_item_lifts(evidence, items)
    custom_weights = {"identity_expired_ratio": 30.0}
    reweighted_lifts = compute_item_lifts(evidence, items, weights=custom_weights)

    assert default_lifts["expired-certificates"] != reweighted_lifts["expired-certificates"]

    # Independently confirm the direction/magnitude via a bare rescore, so
    # this isn't just asserting the module disagrees with itself.
    base_default = compute_readiness_score(evidence)["score"]
    base_reweighted = compute_readiness_score(evidence, weights=custom_weights)["score"]
    resolved = copy.deepcopy(evidence)
    resolved["certificate_observations"]["expired_count"] = 0
    resolved_default = compute_readiness_score(resolved)["score"]
    resolved_reweighted = compute_readiness_score(resolved, weights=custom_weights)["score"]

    assert (resolved_default - base_default) == default_lifts["expired-certificates"]
    assert (resolved_reweighted - base_reweighted) == reweighted_lifts["expired-certificates"]


# ---------------------------------------------------------------------------
# Behavior 3: honest absence — unmodelable slugs never appear; no key is
# ever <= 0.
# ---------------------------------------------------------------------------


def test_unmodelable_slugs_never_appear_as_keys() -> None:
    evidence = _absence_evidence()
    items = _items(evidence)
    lifts = compute_item_lifts(evidence, items)
    for slug in _ABSENT_SLUGS:
        assert slug not in lifts, f"unmodelable slug {slug!r} leaked into lifts: {lifts}"


def test_no_lift_key_is_ever_zero_or_negative_and_key_set_is_a_modelable_subset() -> None:
    for evidence in (_evidence(), _clamp_binding_evidence(), _absence_evidence()):
        items = _items(evidence)
        lifts = compute_item_lifts(evidence, items)
        assert set(lifts.keys()) <= _MODELABLE_SLUGS
        for slug, value in lifts.items():
            assert isinstance(value, int), f"{slug} lift is not an int: {value!r}"
            assert value > 0, f"{slug} lift is not strictly positive: {value!r}"


# ---------------------------------------------------------------------------
# Behavior 4: aggregate projection is its own independent single rescore.
# ---------------------------------------------------------------------------

_DELTA_APPLICATIONS = {
    "plaintext-http-exposure": lambda e: (
        e.__setitem__("plaintext_http_count", 0),
        e.__setitem__("http_on_tls_port_count", 0),
    ),
    "high-impact-findings": lambda e: (
        e["finding_severity_counts"].__setitem__("HIGH", 0),
        e["finding_severity_counts"].__setitem__("CRITICAL", 0),
    ),
    "expired-certificates": lambda e: e["certificate_observations"].__setitem__(
        "expired_count", 0
    ),
    "scan-reliability": lambda e: e["scan_error"].__setitem__("rate", 0.0),
    "unknown-open-services": lambda e: e["protocol_counts"].__setitem__("UNKNOWN", 0),
    "near-expiry-certificates": lambda e: e["certificate_observations"].__setitem__(
        "expiring_count", 0
    ),
    "self-signed-certificates": lambda e: e["certificate_observations"].__setitem__(
        "self_signed_count", 0
    ),
    "legacy-tls-versions": lambda e: e["finding_severity_counts"].__setitem__("LOW", 0),
    "ecdsa-adoption-planning": lambda e: e["cert_key_type_counts"].__setitem__("ECDSA", 1),
}


def _independently_resolve_all(evidence: dict, items: list) -> dict:
    """Apply the union of ALL modelable slugs' Evidence-Delta Map mutations
    present in `items`, to ONE deep copy — the same "one all-resolved
    rescore" recipe LIFT-02 requires `compute_projected_score` to follow,
    computed here independently of the module under test.
    """
    resolved = copy.deepcopy(evidence)
    present_slugs = {slug_for_title(it["title"]) for it in items}
    for slug in present_slugs & _MODELABLE_SLUGS:
        _DELTA_APPLICATIONS[slug](resolved)
    return resolved


def test_aggregate_projection_equals_one_independent_rescore() -> None:
    evidence = _evidence()
    items = _items(evidence)

    expected = compute_readiness_score(_independently_resolve_all(evidence, items))["score"]
    projected = compute_projected_score(evidence, items)

    assert projected == expected


# ---------------------------------------------------------------------------
# Behavior 5: non-additivity (LIFT-02's stated reason) — clamp-binding
# fixture proves sum(per-item lifts) > (projected - base) strictly.
# ---------------------------------------------------------------------------


def test_lifts_are_not_additive_on_a_clamp_binding_fixture() -> None:
    evidence = _clamp_binding_evidence()
    items = _items(evidence)

    base = compute_readiness_score(evidence)["score"]
    lifts = compute_item_lifts(evidence, items)
    projected = compute_projected_score(evidence, items)

    assert sum(lifts.values()) > (projected - base)


# ---------------------------------------------------------------------------
# Behavior 6: SCORE-06 — base score None yields {} lifts and None projection.
# ---------------------------------------------------------------------------


def test_unassessed_evidence_yields_empty_lifts_and_none_projection() -> None:
    evidence = _unassessed_evidence()
    assert compute_readiness_score(evidence)["score"] is None

    items = _items(evidence)
    assert compute_item_lifts(evidence, items) == {}
    assert compute_projected_score(evidence, items) is None


# ---------------------------------------------------------------------------
# Behavior 7: determinism.
# ---------------------------------------------------------------------------


def test_output_is_deterministic() -> None:
    evidence = _evidence()
    items = _items(evidence)

    first_lifts = compute_item_lifts(copy.deepcopy(evidence), items)
    second_lifts = compute_item_lifts(copy.deepcopy(evidence), items)
    assert first_lifts == second_lifts

    first_projected = compute_projected_score(copy.deepcopy(evidence), items)
    second_projected = compute_projected_score(copy.deepcopy(evidence), items)
    assert first_projected == second_projected


# ---------------------------------------------------------------------------
# Structural constraint (201-PATTERNS): lift computation happens OUTSIDE
# build_phased_roadmap. roadmap.py stays byte-unchanged; this pins that
# `test_intelligence_roadmap.py:52-56`'s 6-key item shape survives a
# `compute_item_lifts` call untouched.
# ---------------------------------------------------------------------------


def test_build_phased_roadmap_items_are_unchanged_by_lift_computation() -> None:
    evidence = _evidence()
    items = _items(evidence)
    pre_image = copy.deepcopy(items)

    compute_item_lifts(evidence, items)

    assert items == pre_image
    for item in items:
        assert set(item.keys()) == {
            "phase",
            "title",
            "why",
            "owner_placeholder",
            "dependencies",
            "timeframe",
        }
