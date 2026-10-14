"""D-25 -- score-neutral finding category invariance (SECH-05).

A finding in ``SCORE_NEUTRAL_FINDING_CATEGORIES`` is counted in
``totals.findings`` and ``finding_severity_counts`` but must not feed the
readiness score, the roadmap's high-impact item, or the what-if lifts.
For every other finding set nothing may change.
"""
from __future__ import annotations

import copy

from quirk.intelligence.evidence import (
    SCORE_NEUTRAL_FINDING_CATEGORIES,
    build_evidence_summary,
)
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.intelligence.score_lift import compute_item_lifts
from quirk.intelligence.scoring import compute_readiness_score

_FINDING_SETS = [
    [],
    [{"severity": "HIGH", "host": "h", "port": 1, "title": "Plaintext HTTP service detected"}],
    [
        {"severity": "CRITICAL", "host": "a", "port": 1, "title": "A"},
        {"severity": "LOW", "host": "b", "port": 2, "title": "B"},
        {"severity": "MEDIUM", "host": "c", "port": 3, "title": "C"},
        {"severity": "INFO", "host": "d", "port": 4, "title": "D"},
    ],
]

_NEUTRAL_HIGH = {
    "severity": "HIGH",
    "category": "config_advisory",
    "host": "n",
    "port": 9,
    "title": "Neutral advisory",
}


def _base() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 0},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 0,
        "mtls_present_count": 0,
        "certificate_observations": {
            "expired_count": 1, "expiring_count": 0,
            "self_signed_count": 0, "certs_observed": 6,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.0},
        "tls_enum_coverage_ratio": 1.0,
    }


def _evidence(findings: list) -> dict:
    built = build_evidence_summary(endpoints=[], findings=findings)
    ev = _base()
    ev["totals"]["findings"] = built["totals"]["findings"]
    ev["finding_severity_counts"] = built["finding_severity_counts"]
    if "scored_finding_severity_counts" in built:
        ev["scored_finding_severity_counts"] = built["scored_finding_severity_counts"]
    return ev


def _score_view(score: dict) -> tuple:
    return (score.get("score"), score.get("rating"), score.get("rating_cap_reason"))


def test_category_set_contains_config_advisory() -> None:
    assert "config_advisory" in SCORE_NEUTRAL_FINDING_CATEGORIES


def test_p1_scored_counts_equal_counts_without_neutral_findings() -> None:
    for findings in _FINDING_SETS:
        built = build_evidence_summary(endpoints=[], findings=findings)
        assert built["scored_finding_severity_counts"] == built["finding_severity_counts"]
        ev = _evidence(findings)
        fallback = copy.deepcopy(ev)
        fallback.pop("scored_finding_severity_counts")
        assert compute_readiness_score(ev) == compute_readiness_score(fallback)


def test_p2_neutral_high_is_counted_but_does_not_move_score() -> None:
    for findings in _FINDING_SETS:
        before = build_evidence_summary(endpoints=[], findings=findings)
        after = build_evidence_summary(endpoints=[], findings=findings + [_NEUTRAL_HIGH])
        assert after["finding_severity_counts"]["HIGH"] == before["finding_severity_counts"]["HIGH"] + 1
        assert after["totals"]["findings"] == before["totals"]["findings"] + 1
        assert after["scored_finding_severity_counts"] == before["scored_finding_severity_counts"]
        s_before = compute_readiness_score(_evidence(findings))
        s_after = compute_readiness_score(_evidence(findings + [_NEUTRAL_HIGH]))
        assert _score_view(s_before) == _score_view(s_after)
        assert s_before["score"] is not None


def test_p3_roadmap_and_lifts_ignore_neutral_high() -> None:
    findings = _FINDING_SETS[2]
    ev0, ev1 = _evidence(findings), _evidence(findings + [_NEUTRAL_HIGH])
    r0 = build_phased_roadmap(ev0, compute_readiness_score(ev0))["items"]
    r1 = build_phased_roadmap(ev1, compute_readiness_score(ev1))["items"]
    assert [i["title"] for i in r0] == [i["title"] for i in r1]
    assert compute_item_lifts(ev0, r0) == compute_item_lifts(ev1, r1)

    only_neutral = _evidence([_NEUTRAL_HIGH])
    items = build_phased_roadmap(only_neutral, compute_readiness_score(only_neutral))["items"]
    assert not any("high" in str(i.get("title", "")).lower() and "impact" in str(i.get("title", "")).lower()
                   for i in items)


def test_p4_coverage_gap_still_excluded_from_counts() -> None:
    gap = {"severity": "HIGH", "category": "coverage_gap", "host": "g", "port": 0, "title": "gap"}
    built = build_evidence_summary(endpoints=[], findings=[gap])
    assert built["totals"]["findings"] == 0
    assert built["finding_severity_counts"]["HIGH"] == 0


def test_p5_evidence_without_scored_key_scores_from_legacy_counts() -> None:
    ev = _evidence(_FINDING_SETS[1])
    ev.pop("scored_finding_severity_counts", None)
    with_high = compute_readiness_score(ev)
    ev["finding_severity_counts"] = dict(ev["finding_severity_counts"], HIGH=0)
    assert with_high["score"] != compute_readiness_score(ev)["score"] or \
        with_high["rating_cap_reason"] != compute_readiness_score(ev)["rating_cap_reason"]
