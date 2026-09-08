"""Phase 188 SCORE-06 — exclude-and-rescale coverage-disclosure regression suite.

Covers three behaviors compute_readiness_score() must exhibit after the exclude-and-rescale
rewrite (quirk/intelligence/scoring.py, Phase 188 plan 188-01):

1. Per-category exclusion: a category with zero assessable evidence is excluded from the
   headline (subscore None, not counted in domains_assessed) rather than defaulting to 25.
2. ROADMAP success criterion 1: a chaos-lab-shaped partial-coverage fixture that previously
   overstated readiness by fabricating full 25/25 credit for domains it never assessed can no
   longer reach 96/100 on the strength of those unassessed domains.
3. Zero-assessed edge case: a scan that assessed nothing emits an explicit "not computed" state
   (score=None, rating="NOT_ASSESSED") — never a fabricated 0 or 100, never a ZeroDivisionError.

Architectural note on the per-category parametrization (read before extending this file):
hygiene, modern_tls, and agility_signals all share the IDENTICAL assessed-predicate
(`_endpoints_assessed`, i.e. `totals.endpoints > 0`) — this is not an implementation gap, it is
how scoring.py's own ratios are built (all three read the same `denom` variable derived from
endpoints; see quirk/intelligence/scoring.py's per-category impact lists). Because the three
share one boolean, it is structurally impossible to construct evidence that excludes exactly one
of them while leaving the other two (and everything else) assessed — excluding one always
excludes all three simultaneously. This file therefore parametrizes independent single-category
exclusion over the three categories that DO have independent predicates (identity_trust,
data_at_rest, data_in_motion — each reads its own protocol_counts/cert_obs signal) and covers the
shared endpoint-wide group with a single dedicated test asserting all three exclude together.
"""
from __future__ import annotations

import pytest

from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# 1. Per-category exclusion — independently-controllable categories
# ---------------------------------------------------------------------------

# Baseline: all six categories assessed via one representative protocol_counts
# literal per independent predicate (KERBEROS for identity_trust, POSTGRESQL for
# data_at_rest, KAFKA-PLAIN for data_in_motion) plus endpoints > 0 for the
# endpoint-wide group. Every counter defaults to 0 (no findings), so every
# subscore is a clean 25.
_FULL_COVERAGE_PROTOCOL_COUNTS = {"KERBEROS": 1, "POSTGRESQL": 1, "KAFKA-PLAIN": 1}


def _full_coverage_evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 0},
        "protocol_counts": dict(_FULL_COVERAGE_PROTOCOL_COUNTS),
    }


@pytest.mark.parametrize("excluded_category,excluded_protocol_key", [
    ("identity_trust", "KERBEROS"),
    ("data_at_rest", "POSTGRESQL"),
    ("data_in_motion", "KAFKA-PLAIN"),
])
def test_single_category_exclusion_rescales_over_five(excluded_category, excluded_protocol_key):
    """Excluding exactly one independently-controllable category's assessed-signal yields
    that category absent from the assessed set (subscore None), domains_assessed == 5, and
    score_divisor == 1.25 -- the other five categories are unaffected.
    """
    evidence = _full_coverage_evidence()
    evidence["protocol_counts"] = {
        k: v for k, v in _FULL_COVERAGE_PROTOCOL_COUNTS.items() if k != excluded_protocol_key
    }

    result = compute_readiness_score(evidence)

    assert result["domains_assessed"] == 5, (
        f"Expected 5 domains assessed with {excluded_category} excluded, "
        f"got {result['domains_assessed']} (subscores={result['subscores']})"
    )
    assert result["domains_total"] == 6
    assert result["score_divisor"] == 1.25
    assert result["subscores"][excluded_category] is None, (
        f"{excluded_category} must be None (unassessed), got "
        f"{result['subscores'][excluded_category]}"
    )
    for category, value in result["subscores"].items():
        if category == excluded_category:
            continue
        assert value == 25, (
            f"{category} must remain a clean 25/25 when only {excluded_category} is "
            f"excluded, got {value}. Cross-category exclusion leaked."
        )
    # Full coverage (all 6 clean) would be 100; excluding one clean domain must not
    # change the headline, since the remaining 5 are still all clean 25s.
    assert result["score"] == 100


def test_endpoint_wide_group_excludes_together():
    """hygiene, modern_tls, and agility_signals share the identical `_endpoints_assessed`
    predicate (totals.endpoints > 0) -- excluding it excludes all three simultaneously, never
    just one. With endpoints == 0 but the three independent predicates still satisfied
    (identity/dar/motion protocol_counts present), domains_assessed == 3 and score_divisor
    == 0.75.
    """
    evidence = {
        "totals": {"endpoints": 0, "findings": 0},
        "protocol_counts": dict(_FULL_COVERAGE_PROTOCOL_COUNTS),
    }

    result = compute_readiness_score(evidence)

    assert result["domains_assessed"] == 3
    assert result["domains_total"] == 6
    assert result["score_divisor"] == 0.75
    for category in ("hygiene", "modern_tls", "agility_signals"):
        assert result["subscores"][category] is None, (
            f"{category} must be excluded when endpoints == 0, got "
            f"{result['subscores'][category]}"
        )
    for category in ("identity_trust", "data_at_rest", "data_in_motion"):
        assert result["subscores"][category] == 25, (
            f"{category} must remain assessed (clean 25) when only the endpoint-wide "
            f"group is excluded, got {result['subscores'][category]}"
        )
    assert result["score"] == 100


# ---------------------------------------------------------------------------
# 2. ROADMAP success criterion 1 — partial coverage cannot reach 96/100
# ---------------------------------------------------------------------------

def _partial_coverage_endpoints() -> list:
    """15 clean TLS endpoints (ECDSA, modern TLS1.3) + 5 plaintext HTTP endpoints, zero
    DAR/motion protocol endpoints, zero identity signals (no cert data, no KERBEROS/SAML/
    DNSSEC). Mirrors a chaos-lab-shaped partial scan: TLS/hygiene/agility were assessed,
    but the DB/storage/K8s/vault (data_at_rest) and email/broker (data_in_motion) and
    identity (identity_trust) domains were never reached by this particular scan profile.
    """
    endpoints = [
        CryptoEndpoint(
            host=f"clean{i}.example.com", port=443, protocol="TLS",
            tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
            cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        )
        for i in range(15)
    ]
    endpoints += [
        CryptoEndpoint(host=f"http{i}.example.com", port=80, protocol="HTTP")
        for i in range(5)
    ]
    return endpoints


def _partial_coverage_findings() -> list:
    return [
        {
            "title": "Plaintext HTTP service detected",
            "severity": "MEDIUM",
            "category": "tls",
            "description": f"Plaintext HTTP service detected on http{i}.example.com:80",
            "host": f"http{i}.example.com",
            "port": 80,
            "recommendation": "Redirect to HTTPS.",
            "compliance": [],
        }
        for i in range(5)
    ]


def test_partial_coverage_fixture_cannot_reach_96_via_unassessed_domains():
    """SCORE-06 / ROADMAP success criterion 1: this fixture reproduces the exact
    pre-fix overstatement shape -- 3 of 6 domains actually assessed (hygiene, modern_tls,
    agility_signals), 3 unassessed (identity_trust, data_at_rest, data_in_motion) -- and
    asserts the returned score can no longer reach 96/100 on the strength of the 3
    unassessed domains, AND asserts *why*: the two headline-relevant unassessed domains
    (data_at_rest, data_in_motion) are absent from the assessed set. A future formula
    change that reintroduces the old fixed-divisor overstatement fails this test with a
    readable message, not a silent regression.

    Derivation (verified via build_evidence_summary + compute_readiness_score, not
    guessed): hygiene=20 (5 plaintext HTTP findings out of 20 endpoints,
    -5/20*18=-4.5->-4... exact value read from the real pipeline below, not hand-derived,
    since this test's job is the coverage assertion, not re-deriving hygiene's own
    weighted-impact arithmetic), modern_tls=25, agility_signals=25 (MEDIUM severity findings
    do not feed agility_high_impact_ratio, which only counts HIGH/CRITICAL). domains_assessed
    == 3, score_divisor == 0.75.

    Pre-188 comparison (not asserted, illustrative only): the OLD fixed-divisor formula
    would have summed these three real subscores PLUS three fabricated full-25s for the
    unassessed domains, divided by 1.5 -- sum(20, 25, 25, 25, 25, 25) / 1.5 = 145 / 1.5 =
    96.67 -> 97, at or above the 96 threshold this criterion exists to prevent. The
    exclude-and-rescale formula instead divides only the three REAL subscores by their own
    count: sum(20, 25, 25) / (3 * 25) * 100 = 70 / 75 * 100 = 93.33 -> 93.
    """
    endpoints = _partial_coverage_endpoints()
    findings = _partial_coverage_findings()
    evidence = build_evidence_summary(endpoints, findings)

    result = compute_readiness_score(evidence)

    assert result["domains_assessed"] == 3, (
        f"Fixture precondition failed: expected 3 domains assessed (hygiene, modern_tls, "
        f"agility_signals), got {result['domains_assessed']} (subscores={result['subscores']})"
    )
    assert result["subscores"]["data_at_rest"] is None, (
        "Fixture precondition failed: data_at_rest must be unassessed (no DAR protocol "
        "endpoints in this fixture)."
    )
    assert result["subscores"]["data_in_motion"] is None, (
        "Fixture precondition failed: data_in_motion must be unassessed (no email/broker "
        "protocol endpoints in this fixture)."
    )
    assert result["coverage_disclosure"] == "3 of 6 domains assessed"

    assert result["score"] is not None
    assert result["score"] < 96, (
        f"SCORE-06 REGRESSION: this fixture reached a score of {result['score']}, at or "
        f"above the 96/100 threshold, by way of its 3 unassessed domains "
        f"(identity_trust, data_at_rest, data_in_motion never contributed a fabricated "
        f"25/25). ROADMAP success criterion 1 requires this fixture to score strictly "
        f"below 96. If the formula changed and this now legitimately scores higher, "
        f"update this assertion with a new written derivation -- do not just raise the "
        f"threshold to make the test pass."
    )


# ---------------------------------------------------------------------------
# 3. Zero-assessed edge case — explicit "not computed", never fabricated 0/100
# ---------------------------------------------------------------------------

def test_zero_assessed_domains_emits_not_computed_never_fabricated():
    """A scan (or hand-built evidence dict) with zero endpoints, zero DAR/motion protocol
    counts, and zero identity signals must emit an explicit "not computed" state: score is
    None (asserted with `is None`, not a truthiness check, so 0 and None are never
    conflated), rating is the literal string "NOT_ASSESSED", score_divisor is None, and
    every subscore is None. No ZeroDivisionError.
    """
    result = compute_readiness_score({})

    assert result["score"] is None
    assert result["rating"] == "NOT_ASSESSED"
    assert result["rating_cap_reason"] is None
    assert result["score_divisor"] is None
    assert result["domains_assessed"] == 0
    assert result["domains_total"] == 6
    assert result["coverage_disclosure"] == "0 of 6 domains assessed"
    for category, value in result["subscores"].items():
        assert value is None, f"subscore {category} must be None, got {value}"


def test_zero_assessed_domains_does_not_raise_on_realistic_empty_scan():
    """Companion to the hand-built-dict case above: build_evidence_summary()'s own output
    shape (with all its extra keys) also hits the zero-assessed branch cleanly for a truly
    empty scan (no endpoints, no findings) -- proving the None-safety holds against the
    REAL evidence dict shape, not just a minimal hand-built one.
    """
    evidence = build_evidence_summary([], [])
    result = compute_readiness_score(evidence)

    assert result["score"] is None
    assert result["rating"] == "NOT_ASSESSED"
    assert result["domains_assessed"] == 0


if __name__ == "__main__":
    import unittest

    unittest.main()
