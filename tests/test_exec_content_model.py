"""Phase 98 D-02/D-03/D-04/D-05 / EXEC-02, EXEC-03, TRANS-01 — ExecContent unit tests.

Covers build_exec_content() shape, top-risks population from ALGO_IMPACT_MAP,
within-bucket roadmap priority ordering, and six-pillar subscores pass-through.

Fixtures use CANONICAL score_raw key shape ("score", "rating", "subscores",
"drivers") — NOT the writer.py compat wrapper ("total"). See RESEARCH Pitfall 1.
"""
from __future__ import annotations

import pytest

from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    ExecContent,
    RiskItem,
    RoadmapItem,
    build_exec_content,
)

# ---------------------------------------------------------------------------
# Canonical score_raw fixture (key "score", not "total" — Pitfall 1)
# ---------------------------------------------------------------------------

_SIX_PILLAR_KEYS = (
    "hygiene",
    "modern_tls",
    "identity_trust",
    "agility_signals",
    "data_at_rest",
    "data_in_motion",
)


def _make_score_raw(score: int = 67, rating: str = "FAIR") -> dict:
    """CANONICAL score_raw shape from compute_readiness_score().

    Uses key 'score' (not 'total' — writer.py compat wrapper uses 'total').
    FAIR rating has no CRITICAL restriction, so the congruence guard is silent.
    """
    return {
        "score": score,
        "rating": rating,
        "subscores": {
            "hygiene": 20,
            "modern_tls": 18,
            "identity_trust": 25,
            "agility_signals": 15,
            "data_at_rest": 22,
            "data_in_motion": 21,
        },
        "drivers": [
            "Plaintext HTTP exposure (-12)",
            "RSA-only certificate posture (-8)",
        ],
    }


def _make_rsa_finding(severity: str = "CRITICAL") -> dict:
    """Finding that triggers an ALGO_IMPACT_MAP RSA entry."""
    return {
        "title": "RSA-2048 certificate — quantum-vulnerable",
        "description": "Endpoint uses RSA-2048 which is vulnerable to Shor's algorithm.",
        "severity": severity,
        "category": "RSA",
    }


def _make_weak_hash_finding(severity: str = "HIGH") -> dict:
    """Finding that triggers an ALGO_IMPACT_MAP WEAK_HASH/SHA-1 entry."""
    return {
        "title": "SHA-1 digest in use",
        "description": "SHA-1 is cryptographically weak.",
        "severity": severity,
        "category": "WEAK_HASH",
    }


# ---------------------------------------------------------------------------
# Tests — exact VALIDATION.md node IDs
# ---------------------------------------------------------------------------


def test_top_risks_populated():
    """EXEC-02: build_exec_content with RSA/CRITICAL finding yields >=1 RiskItem
    whose impact_sentence comes from ALGO_IMPACT_MAP.

    Requirement: EXEC-02 — D-02 static map produces top-risks business framing.
    Node ID: test_exec_content_model.py::test_top_risks_populated
    """
    score_raw = _make_score_raw(rating="FAIR")  # FAIR: guard allows CRITICAL
    findings = [_make_rsa_finding(severity="CRITICAL")]
    roadmap_items: list = []

    result = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=roadmap_items,
    )

    assert isinstance(result, ExecContent), (
        "build_exec_content must return an ExecContent instance. EXEC-02."
    )
    assert len(result.top_risks) >= 1, (
        "top_risks must contain at least one RiskItem when RSA/CRITICAL finding present. "
        "EXEC-02 / D-02: top-risks from ALGO_IMPACT_MAP."
    )

    risk = result.top_risks[0]
    assert isinstance(risk, RiskItem), (
        "top_risks items must be RiskItem instances. EXEC-02."
    )

    # The impact_sentence must come from ALGO_IMPACT_MAP (not per-finding prose)
    _, expected_sentence, _ = ALGO_IMPACT_MAP["RSA"]
    assert risk.impact_sentence == expected_sentence, (
        f"impact_sentence '{risk.impact_sentence}' does not match ALGO_IMPACT_MAP RSA entry. "
        "EXEC-02 / D-02: sentences come from the static map, not per-finding text."
    )


def test_roadmap_priority_ordering():
    """EXEC-03: within a single bucket, roadmap_items are ordered high-impact/low-effort first.

    Requirement: EXEC-03 — D-04 impact×effort priority ordering within NOW/NEXT/LATER buckets.
    Node ID: test_exec_content_model.py::test_roadmap_priority_ordering
    """
    score_raw = _make_score_raw(rating="FAIR")
    findings: list = []

    # Three items in the same NOW bucket with intentionally mixed effort/impact.
    # "certificate" → LOW effort, HIGH impact → highest priority (3 * (4-1) = 9)
    # "kms"         → HIGH effort, HIGH impact → lower priority  (3 * (4-3) = 3)
    # "audit"       → MEDIUM effort, MEDIUM impact → mid priority (2 * (4-2) = 4)
    roadmap_items = [
        {
            "phase": "NOW",
            "title": "Rotate KMS keys",
            "why": "Legacy KMS keys at risk.",
            "owner_placeholder": "SecEng",
            "timeframe": "1 month",
            "_priority": 10,
        },
        {
            "phase": "NOW",
            "title": "Crypto audit sweep",
            "why": "Baseline inventory needed.",
            "owner_placeholder": "SecEng",
            "timeframe": "2 weeks",
            "_priority": 20,
        },
        {
            "phase": "NOW",
            "title": "Replace expired certificate",
            "why": "Certificate is expired.",
            "owner_placeholder": "Ops",
            "timeframe": "1 week",
            "_priority": 30,
        },
    ]

    result = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=roadmap_items,
    )

    now_items = [r for r in result.roadmap_items if r.phase == "NOW"]
    assert len(now_items) == 3, (
        "Expected 3 NOW-bucket items in result. EXEC-03."
    )

    # The certificate item (LOW effort, HIGH impact) must sort first
    assert now_items[0].title == "Replace expired certificate", (
        f"Expected 'Replace expired certificate' first (LOW EFFORT / HIGH IMPACT), "
        f"got '{now_items[0].title}'. "
        "EXEC-03 / D-04: high-impact/low-effort items must sort first within a bucket."
    )

    # Verify priority_score is set and ordered descending
    scores = [item.priority_score for item in now_items]
    assert scores == sorted(scores, reverse=True), (
        f"NOW-bucket priority_scores {scores} are not in descending order. "
        "EXEC-03 / D-04: within-bucket ordering must be highest priority_score first."
    )

    # Each item must carry effort and impact fields
    for item in now_items:
        assert item.effort in ("LOW", "MEDIUM", "HIGH"), (
            f"RoadmapItem.effort must be LOW/MEDIUM/HIGH, got '{item.effort}'. "
            "EXEC-03 / D-05."
        )
        assert item.impact in ("HIGH", "MEDIUM", "LOW"), (
            f"RoadmapItem.impact must be HIGH/MEDIUM/LOW, got '{item.impact}'. "
            "EXEC-03 / D-05."
        )


def test_subscores_all_keys_present():
    """TRANS-01: ExecContent.subscores contains all six pillar keys.

    Requirement: TRANS-01 — six-pillar subscore decomposition exposed via ExecContent.
    Node ID: test_exec_content_model.py::test_subscores_all_keys_present
    """
    score_raw = _make_score_raw(rating="FAIR")
    findings: list = []
    roadmap_items: list = []

    result = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=roadmap_items,
    )

    for key in _SIX_PILLAR_KEYS:
        assert key in result.subscores, (
            f"ExecContent.subscores missing pillar key '{key}'. "
            "TRANS-01: all six subscore pillars must be present in ExecContent."
        )

    assert result.score_total == 67, (
        f"ExecContent.score_total expected 67 (from score_raw['score']), got {result.score_total}. "
        "TRANS-01 / Pitfall 1: must use canonical 'score' key, not 'total'."
    )

    assert result.raw_sum == sum(
        score_raw["subscores"].values()
    ), (
        f"ExecContent.raw_sum expected {sum(score_raw['subscores'].values())}, "
        f"got {result.raw_sum}. TRANS-01."
    )


def test_empty_subscores_edge_case():
    """TRANS-01 / Pitfall 3: empty subscores dict yields raw_sum = 0 without error."""
    score_raw = {
        "score": 0,
        "rating": "POOR",
        "subscores": {},
        "drivers": [],
    }
    result = build_exec_content(
        score_raw=score_raw,
        findings=[],
        roadmap_items=[],
    )
    assert result.raw_sum == 0, (
        "raw_sum must be 0 for empty subscores (no ZeroDivisionError or AttributeError). "
        "TRANS-01 / Pitfall 3 edge case."
    )
    assert result.subscores == {}, (
        "ExecContent.subscores must be empty dict when score_raw subscores are empty."
    )


def test_sev_counts_computed_once():
    """TRANS-03 / D-06: sev_counts is computed once and present in ExecContent."""
    score_raw = _make_score_raw(rating="POOR")  # POOR: no CRITICAL restriction
    findings = [
        _make_rsa_finding(severity="HIGH"),
        _make_weak_hash_finding(severity="MEDIUM"),
        {"title": "Low-severity info", "severity": "LOW"},
    ]
    result = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=[],
    )
    assert result.sev_counts.get("HIGH", 0) == 1, (
        "sev_counts['HIGH'] must be 1 for one HIGH finding. TRANS-03 / D-06."
    )
    assert result.sev_counts.get("MEDIUM", 0) == 1, (
        "sev_counts['MEDIUM'] must be 1 for one MEDIUM finding. TRANS-03 / D-06."
    )
    assert result.sev_counts.get("LOW", 0) == 1, (
        "sev_counts['LOW'] must be 1 for one LOW finding. TRANS-03 / D-06."
    )


def test_narrative_lead_band_collapse():
    """EXEC-01 / D-01: narrative lead uses the correct 5->4 band collapse.

    EXCELLENT and GOOD share the same lead; MODERATE -> FAIR lead;
    FAIR -> POOR lead; POOR -> CRITICAL lead. (RESEARCH Pattern 4.)
    """
    from quirk.reports.content_model import _NARRATIVE_LEADS

    excellent_result = build_exec_content(
        score_raw={"score": 90, "rating": "EXCELLENT", "subscores": {}, "drivers": []},
        findings=[],
        roadmap_items=[],
    )
    good_result = build_exec_content(
        score_raw={"score": 75, "rating": "GOOD", "subscores": {}, "drivers": []},
        findings=[],
        roadmap_items=[],
    )
    assert excellent_result.narrative_lead == good_result.narrative_lead, (
        "EXCELLENT and GOOD bands must map to the same narrative lead (5->4 collapse). "
        "EXEC-01 / RESEARCH Pattern 4."
    )
    assert good_result.narrative_lead == _NARRATIVE_LEADS["GOOD"], (
        "GOOD band narrative lead must match _NARRATIVE_LEADS['GOOD']. EXEC-01."
    )

    moderate_result = build_exec_content(
        score_raw={"score": 60, "rating": "MODERATE", "subscores": {}, "drivers": []},
        findings=[],
        roadmap_items=[],
    )
    assert moderate_result.narrative_lead == _NARRATIVE_LEADS["MODERATE"], (
        "MODERATE band must use its own narrative lead. EXEC-01 / RESEARCH Pattern 4."
    )
