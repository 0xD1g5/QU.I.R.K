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
    (plaintext HTTP + HTTP-on-TLS-port counts) deliberately exceeding the
    25-point clamp headroom, verified below by
    `test_clamp_binding_fixture_actually_binds`.

    Phase 234 (scoring 4.0): penalties follow the absolute-count curve
    `min(1, count / 40) ** 0.5`, so the clamp only binds when the counts reach
    N_REF = 40. Unclamped hygiene penalty at these values:
        curve(40)*18 + curve(40)*16 + curve(20)*6
        = 18 + 16 + 4.24 = 38.24 > 25 (score_cap) -> hygiene clamps to 0.
    (3.0 used the share of 2 endpoints: 2/2 * 18 + 2/2 * 16 + 0.5 * 6 = 37.)

    Live scratch run recorded during execution (201-01-SUMMARY.md) confirmed:
    base score=33 (hygiene=0, clamped from an unclamped -12), and resolving
    each of the 9 modelable items in isolation and summing their lifts
    (=70) strictly exceeds the one true aggregate rescore's lift (=67) —
    the non-additivity this fixture exists to prove.
    """
    return {
        "totals": {"endpoints": 40, "findings": 5},
        "protocol_counts": {"KERBEROS": 1, "UNKNOWN": 1},
        "plaintext_http_count": 40,
        "http_on_tls_port_count": 40,
        "mtls_present_count": 0,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 1,
            "self_signed_count": 1,
            "certs_observed": 3,
        },
        "cert_key_type_counts": {"RSA": 3, "ECDSA": 0},
        "scan_error": {"rate": 0.5, "count": 20},
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
        # Phase 234 O-4: every observed certificate carries a PQC key, so the
        # retargeted PQC/hybrid certificate item (which now also fires on
        # certificates with undetermined key types) stays out of this fixture.
        "cert_key_type_counts": {"RSA": 0, "ECDSA": 0, "PQC": 3},
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


def _count_curve(count: int) -> float:
    """Independent restatement of the scoring-4.0 absolute-count curve
    (N_REF = 40, exponent 0.5), written here rather than imported so the
    fixture check does not lean on the module it guards."""
    if count <= 0:
        return 0.0
    return min(1.0, count / 40) ** 0.5


def test_clamp_binding_fixture_actually_binds() -> None:
    evidence = _clamp_binding_evidence()
    unclamped_hygiene_penalty = (
        _count_curve(evidence["plaintext_http_count"]) * 18.0
        + _count_curve(evidence["http_on_tls_port_count"]) * 16.0
        + _count_curve(evidence["scan_error"]["count"]) * 6.0
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
    # Phase 234 D-03: scoring 4.0 reads scan_error.count, so both are zeroed.
    "scan-reliability": lambda e: (
        e["scan_error"].__setitem__("rate", 0.0),
        e["scan_error"].__setitem__("count", 0),
    ),
    "unknown-open-services": lambda e: e["protocol_counts"].__setitem__("UNKNOWN", 0),
    "near-expiry-certificates": lambda e: e["certificate_observations"].__setitem__(
        "expiring_count", 0
    ),
    "self-signed-certificates": lambda e: e["certificate_observations"].__setitem__(
        "self_signed_count", 0
    ),
    "legacy-tls-versions": lambda e: e["finding_severity_counts"].__setitem__("LOW", 0),
    # Phase 234 O-4: the slug now names PQC/hybrid certificate adoption; the
    # independent model is "all classical certificate keys migrated".
    "ecdsa-adoption-planning": lambda e: _migrate_all_cert_keys_to_pqc(e),
}


def _migrate_all_cert_keys_to_pqc(evidence: dict) -> None:
    """Independent mirror of the O-4 resolver: RSA = ECDSA = 0 and
    PQC = max(1, RSA + ECDSA, certs_observed)."""
    keys = evidence.setdefault("cert_key_type_counts", {})
    classical = int(keys.get("RSA", 0)) + int(keys.get("ECDSA", 0))
    observed = int(evidence.get("certificate_observations", {}).get("certs_observed", 0))
    keys["RSA"] = 0
    keys["ECDSA"] = 0
    keys["PQC"] = max(1, classical, observed)


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


def test_pqc_certificate_adoption_lift_is_positive_on_r2() -> None:
    """Phase 234 O-4: on the R2 calibration rung (40 RSA certificates, no PQC)
    the retargeted item projects a real, strictly positive lift. Under the
    pre-234 resolver (add one ECDSA key) the 4.0 lift was 0: ECDSA is a
    classical key and takes the same penalty as RSA."""
    from tests.test_score_properties import _r2_well_run_no_pqc

    evidence = _r2_well_run_no_pqc()
    base = compute_readiness_score(evidence)["score"]
    resolved = copy.deepcopy(evidence)
    _migrate_all_cert_keys_to_pqc(resolved)
    expected_lift = compute_readiness_score(resolved)["score"] - base
    assert expected_lift > 0, f"migrate-all-to-PQC lift on R2 is {expected_lift}"

    items = _items(evidence)
    assert "ecdsa-adoption-planning" in {slug_for_title(i["title"]) for i in items}
    lifts = compute_item_lifts(evidence, items)
    assert lifts.get("ecdsa-adoption-planning") == expected_lift


def test_scan_reliability_lift_follows_the_count_input() -> None:
    """Phase 234 D-03: the scorer reads scan_error.count, so the "Increase scan
    coverage" lift must be positive when only the count is populated."""
    evidence = _evidence()
    # The count is what the 4.0 scorer reads and what triggers the roadmap item
    # (Phase 234 review D-31); the rate only feeds the why text.
    evidence["scan_error"] = {"rate": 0.4, "count": 4}
    items = _items(evidence)
    assert "scan-reliability" in {slug_for_title(i["title"]) for i in items}
    base = compute_readiness_score(evidence)["score"]
    resolved = copy.deepcopy(evidence)
    resolved["scan_error"]["rate"] = 0.0
    resolved["scan_error"]["count"] = 0
    expected_lift = compute_readiness_score(resolved)["score"] - base
    assert expected_lift > 0
    assert compute_item_lifts(evidence, items).get("scan-reliability") == expected_lift


def test_scan_coverage_item_fires_on_the_scored_count_with_a_real_lift() -> None:
    """Phase 234 review D-31 (WR-04): "Increase scan coverage" triggers on
    scan_error.count, the input scoring 4.0 penalises, not on the rate.

    WR-04 reproduction: R3 with 40 scan errors among 250 endpoints (rate
    0.16, below the old 0.2 trigger). The count costs points (hygiene and
    modern_tls), yet the item was absent, so the roadmap offered no
    remediation and the projected score left those points out.
    """
    from tests.test_score_properties import _r3_typical_enterprise

    evidence = _r3_typical_enterprise()
    evidence["totals"]["endpoints"] = 250
    evidence["scan_error"] = {"count": 40, "rate": 0.16}
    clean = copy.deepcopy(evidence)
    clean["scan_error"] = {"count": 0, "rate": 0.0}
    # Non-vacuity: the count really costs points on this estate.
    assert compute_readiness_score(evidence)["score"] < (
        compute_readiness_score(clean)["score"]
    )
    items = _items(evidence)
    assert "scan-reliability" in {slug_for_title(i["title"]) for i in items}
    lift = compute_item_lifts(evidence, items).get("scan-reliability")
    assert lift is not None and lift > 0, f"scan-reliability lift {lift!r}"
    assert lift == (
        compute_readiness_score(clean)["score"]
        - compute_readiness_score(evidence)["score"]
    )
    # The item does not fire when nothing is penalised.
    assert "scan-reliability" not in {
        slug_for_title(i["title"]) for i in _items(clean)
    }


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
    """LIFT-02's stated reason: per-item lifts do NOT sum to the aggregate, so
    `compute_projected_score` must do one all-resolved rescore instead of adding
    the parts up.

    999.115 — the non-additivity still holds and is if anything larger, but its
    DIRECTION flipped, so the assertion moved from `>` to `<`. Measured on this
    fixture: sum(lifts) = 54 against an aggregate delta of 64 (base 20 ->
    projected 84). Phase 234 (scoring 4.0, fixture counts raised to N_REF so
    the clamp still binds): sum(lifts) = 41 against an aggregate delta of 47
    (base 37, ceiling-bound by 1 open HIGH from computed 54 -> projected 84).

    Why it flipped. Two non-linearities act on this fixture and they pull
    opposite ways. The per-subscore 25-point clamp (the one this fixture is
    named for, and the only one that existed when this test was written) makes
    parts SUM HIGH: several items each claim credit for the same clamped
    headroom. 999.115's consequence ceiling adds a second, stronger one pulling
    the other way: the base is ceiling-bound at 20 by `1 open HIGH finding`, and
    no SINGLE item resolves the last HIGH, so no single lift can raise the
    ceiling — but resolving everything does, and the ceiling jumps from the top
    of MODERATE (69) to the PQC ceiling (84). That step belongs to the
    combination, never to any part, so the whole exceeds the sum.

    This is product-visible and deliberate: on a ceiling-bound estate the
    roadmap's per-item numbers now UNDERSTATE the total, and the honest reading
    is "clearing your last HIGH finding lifts the cap". Understating each step
    is the safer direction of the two for a client-facing roadmap.
    """
    evidence = _clamp_binding_evidence()
    items = _items(evidence)

    base = compute_readiness_score(evidence)["score"]
    lifts = compute_item_lifts(evidence, items)
    projected = compute_projected_score(evidence, items)

    # The LIFT-02 contract proper: not additive, in either direction.
    assert sum(lifts.values()) != (projected - base), (
        "LIFT-02 requires the projection to be one all-resolved rescore. If the "
        "parts now sum exactly to the whole, either both non-linearities stopped "
        "binding on this fixture or the projection is summing the parts."
    )
    # Pin the direction too, so a future flip is a visible failure and not a
    # silent change in what the roadmap tells a client. Was `>` before 999.115.
    assert sum(lifts.values()) < (projected - base), (
        f"Expected superadditivity on a ceiling-bound fixture: sum(lifts)="
        f"{sum(lifts.values())} should be BELOW the aggregate delta "
        f"{projected - base} (base={base}, projected={projected}), because "
        "lifting the consequence ceiling requires resolving the last HIGH "
        "finding and so belongs to no individual item."
    )


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
