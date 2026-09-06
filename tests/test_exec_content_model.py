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


# ---------------------------------------------------------------------------
# Phase 146 D-08/D-09 (DISC-07): undetermined-host disclosure
# ---------------------------------------------------------------------------


def test_exec_content_undetermined_defaults():
    """ExecContent constructed without the new kwargs defaults to zero/empty.

    Phase 146 D-08: every pre-existing ExecContent(...) construction in the test
    suite must keep working unmodified.
    """
    result = build_exec_content(
        score_raw=_make_score_raw(),
        findings=[],
        roadmap_items=[],
    )
    assert result.undetermined_hosts_count == 0
    assert result.undetermined_hosts_breakdown == {}


def test_exec_content_manual_construction_defaults():
    """A directly-constructed ExecContent (bypassing build_exec_content) also defaults safely."""
    result = ExecContent(
        narrative_lead="lead",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=0,
        score_band="FAIR",
        subscores={},
        raw_sum=0,
        sev_counts={},
    )
    assert result.undetermined_hosts_count == 0
    assert result.undetermined_hosts_breakdown == {}


def test_compute_undetermined_hosts_mixed_list():
    """Phase 146 D-08/D-09 / Pitfall-3: only port==0 discovery-stage rows count.

    (a) port=0, liveness_skip -> counted
    (b) port=0, discovery_exception -> counted
    (c) port=443, discovery_exception -> excluded (live host with a scan error, not undetermined)
    (d) port=0, missing_extra -> excluded (not a discovery-stage category)
    (e) normal scanned endpoint, no scan_error_category -> excluded
    """
    from types import SimpleNamespace

    from quirk.reports.writer import _compute_undetermined_hosts

    endpoints = [
        SimpleNamespace(port=0, scan_error_category="liveness_skip"),
        SimpleNamespace(port=0, scan_error_category="discovery_exception"),
        SimpleNamespace(port=443, scan_error_category="discovery_exception"),
        SimpleNamespace(port=0, scan_error_category="missing_extra"),
        SimpleNamespace(port=443),
    ]
    count, breakdown = _compute_undetermined_hosts(endpoints)
    assert count == 2
    assert breakdown == {"discovery_exception": 1, "liveness_skip": 1}


def test_compute_undetermined_hosts_excludes_generic_wrapped_phase_exception():
    """CR-01 regression: _wrapped_phase()'s generic "exception" category (used by every
    non-discovery scanner stage — TLS, SSH, JWT, container, ...) must NEVER be counted as
    an undetermined host, even at port=0, since its host field is a scanner label
    (e.g. "tls_scanner"), not a target host.
    """
    from types import SimpleNamespace

    from quirk.reports.writer import _compute_undetermined_hosts

    endpoints = [
        SimpleNamespace(host="tls_scanner", port=0, scan_error_category="exception"),
        SimpleNamespace(host="discovery-batch-3", port=0, scan_error_category="discovery_exception"),
    ]
    count, breakdown = _compute_undetermined_hosts(endpoints)
    assert count == 1
    assert breakdown == {"discovery_exception": 1, "liveness_skip": 0}


def test_compute_undetermined_hosts_empty_and_none():
    """Empty/None input returns zero count and a fully-keyed zero breakdown."""
    from quirk.reports.writer import _compute_undetermined_hosts

    assert _compute_undetermined_hosts(None) == (0, {"discovery_exception": 0, "liveness_skip": 0})
    assert _compute_undetermined_hosts([]) == (0, {"discovery_exception": 0, "liveness_skip": 0})


# ---------------------------------------------------------------------------
# Phase 184.4-06 — rating_cap_reason presence/absence/missing-key contract
# (D-09, D-10). See quirk/reports/executive.py (CLI markdown, both branches)
# and quirk/reports/writer.py (compat score dict threaded to DOCX/scorecard/
# intelligence.json/terminal summary).
# ---------------------------------------------------------------------------


def _cli_cfg():
    from types import SimpleNamespace

    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="t", report_owner="o", data_classification="c", timezone="UTC"
        ),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides={}),
    )


def _cli_endpoints():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    return [
        SimpleNamespace(
            host=f"10.0.0.{i}",
            port=443,
            protocol="TLS",
            scanned_at=datetime.now(timezone.utc),
            scan_error=None,
        )
        for i in range(1, 5)
    ]


def _capped_score_raw() -> dict:
    return {
        "score": 89,
        "rating": "FAIR",
        "rating_cap_reason": (
            "Band capped at FAIR: 1 CRITICAL finding(s) open (score 89/100)."
        ),
        "subscores": {k: 25 for k in _SIX_PILLAR_KEYS},
        "drivers": [],
    }


def test_cli_markdown_compat_branch_renders_cap_reason_when_capped():
    """WR-05 compat path (exec_content=None): capped score dict -> cap-reason text present,
    ADJACENT to the Rollup line (D-09's literal requirement, not just present anywhere).

    Index-based adjacency, not a substring-order heuristic: this repo has a documented
    standing weakness where render tests assert presence, not order/appearance
    (feedback_report_render_tests_presence_not_appearance) — a future refactor that
    moved the cap-reason line to the bottom of the document would still pass a bare
    `in md` check. Split into lines and assert the line immediately following the one
    starting with `**Rollup:**` starts with `**Cap reason:**`.
    """
    from unittest.mock import patch

    from quirk.reports.executive import build_exec_markdown

    score_raw = _capped_score_raw()
    with patch(
        "quirk.reports.executive.compute_readiness_score", return_value=score_raw
    ):
        md = build_exec_markdown(_cli_cfg(), _cli_endpoints(), [], exec_content=None)
    assert "Band capped at FAIR" in md

    lines = md.split("\n")
    rollup_idx = next(i for i, ln in enumerate(lines) if ln.startswith("**Rollup:**"))
    assert lines[rollup_idx + 1].startswith("**Cap reason:**"), (
        "Cap reason line must be immediately adjacent to the Rollup line (D-09), "
        f"got: {lines[rollup_idx + 1]!r}"
    )


def test_cli_markdown_compat_branch_absent_when_uncapped():
    """WR-05 compat path: rating_cap_reason is None -> no cap-reason text at all."""
    from unittest.mock import patch

    from quirk.reports.executive import build_exec_markdown

    score_raw = {**_capped_score_raw(), "rating": "EXCELLENT", "rating_cap_reason": None}
    with patch(
        "quirk.reports.executive.compute_readiness_score", return_value=score_raw
    ):
        md = build_exec_markdown(_cli_cfg(), _cli_endpoints(), [], exec_content=None)
    assert "Cap reason" not in md
    assert "Band capped" not in md


def test_cli_markdown_compat_branch_missing_key_does_not_raise():
    """Pre-184.4 shaped score dict with NO rating_cap_reason key at all.

    This is the backward-compatibility case a `[...]`-style direct key read
    would break (KeyError) — only the `.get()` idiom in executive.py protects
    it. Must render cleanly with no cap-reason text.
    """
    from unittest.mock import patch

    from quirk.reports.executive import build_exec_markdown

    score_raw = _capped_score_raw()
    score_raw["rating"] = "FAIR"
    del score_raw["rating_cap_reason"]
    assert "rating_cap_reason" not in score_raw

    with patch(
        "quirk.reports.executive.compute_readiness_score", return_value=score_raw
    ):
        md = build_exec_markdown(_cli_cfg(), _cli_endpoints(), [], exec_content=None)
    assert "Cap reason" not in md
    assert "Band capped" not in md


def test_cli_markdown_exec_content_branch_renders_cap_reason_when_capped():
    """Primary exec_content path: capped score dict -> cap-reason text present,
    ADJACENT to the Rollup line (D-09's literal requirement — see docstring on the
    compat-branch twin of this test for the full rationale and index-based method).
    """
    from unittest.mock import patch

    from quirk.reports.executive import build_exec_markdown

    score_raw = _capped_score_raw()
    crit = {
        "severity": "CRITICAL",
        "host": "10.0.0.9",
        "port": 443,
        "title": "Quantum-vulnerable key exchange",
        "category": "tls",
        "description": "d",
        "recommendation": "r",
        "compliance": [],
    }
    exec_content = build_exec_content(score_raw, [crit], [])
    with patch(
        "quirk.reports.executive.compute_readiness_score", return_value=score_raw
    ):
        md = build_exec_markdown(
            _cli_cfg(), _cli_endpoints(), [crit], exec_content=exec_content
        )
    assert "Band capped at FAIR" in md

    lines = md.split("\n")
    rollup_idx = next(i for i, ln in enumerate(lines) if ln.startswith("**Rollup:**"))
    assert lines[rollup_idx + 1].startswith("**Cap reason:**"), (
        "Cap reason line must be immediately adjacent to the Rollup line (D-09), "
        f"got: {lines[rollup_idx + 1]!r}"
    )


def test_cli_markdown_exec_content_branch_absent_when_uncapped():
    """Primary exec_content path: rating_cap_reason is None -> no cap-reason text."""
    from unittest.mock import patch

    from quirk.reports.executive import build_exec_markdown

    score_raw = {**_capped_score_raw(), "rating": "EXCELLENT", "rating_cap_reason": None}
    exec_content = build_exec_content(score_raw, [], [])
    with patch(
        "quirk.reports.executive.compute_readiness_score", return_value=score_raw
    ):
        md = build_exec_markdown(
            _cli_cfg(), _cli_endpoints(), [], exec_content=exec_content
        )
    assert "Cap reason" not in md
    assert "Band capped" not in md


def test_writer_compat_dict_carries_rating_cap_reason_through():
    """The writer.py compat score dict must carry rating_cap_reason from score_raw
    through to every consumer that reads it (D-09/D-10) — proven here via
    `_scorecard_markdown`, one of those consumers, matching the exact compat
    dict shape `write_reports` builds (`total`/`subscores`/`drivers`/
    `rating_cap_reason`).
    """
    from types import SimpleNamespace

    from quirk.reports.writer import _scorecard_markdown

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(report_owner="o", data_classification="c")
    )
    conf = {"confidence": 80}

    capped_compat = {
        "total": 89,
        "subscores": {},
        "drivers": [],
        "rating_cap_reason": "Band capped at FAIR: 1 CRITICAL finding(s) open (score 89/100).",
    }
    uncapped_compat = {**capped_compat, "rating_cap_reason": None}

    capped_md = _scorecard_markdown(cfg, capped_compat, conf, [], [])
    uncapped_md = _scorecard_markdown(cfg, uncapped_compat, conf, [], [])

    assert "Band capped at FAIR" in capped_md
    assert "Cap reason" not in uncapped_md


# ---------------------------------------------------------------------------
# Phase 184.4 WR-01 — rating_cap_reason lives on the shared ExecContent model.
#
# Before this fix, rating_cap_reason was the ONE score-derived value that
# bypassed ExecContent: six renderer call sites each re-fetched it with their
# own `.get("rating_cap_reason")` off three different dicts (score_raw, the
# writer.py compat `score` dict, and a bespoke render_docx_report keyword).
# writer.py's own comment named that hazard but the chosen mitigation was to
# document the trap rather than close it, violating content_model.py's stated
# D-03 contract ("neither re-derives content from raw inputs").
#
# These tests lock the closure: ONE derivation in build_exec_content(), with
# every renderer reading exec_content.rating_cap_reason.
# ---------------------------------------------------------------------------


def test_exec_content_carries_rating_cap_reason_from_score_raw():
    """build_exec_content() populates the field from score_raw."""
    from quirk.reports.content_model import build_exec_content

    score_raw = _capped_score_raw()
    exec_content = build_exec_content(
        score_raw=score_raw, findings=[], roadmap_items=[]
    )

    assert exec_content.rating_cap_reason == score_raw["rating_cap_reason"]


def test_exec_content_rating_cap_reason_is_none_when_uncapped():
    """An explicitly-None cap reason stays None — the uncapped signal."""
    from quirk.reports.content_model import build_exec_content

    score_raw = {**_capped_score_raw(), "rating_cap_reason": None}
    exec_content = build_exec_content(
        score_raw=score_raw, findings=[], roadmap_items=[]
    )

    assert exec_content.rating_cap_reason is None


def test_exec_content_rating_cap_reason_defaults_when_key_absent():
    """A pre-184.4-shaped score dict (no rating_cap_reason key at all) must
    yield None rather than raising — absence and None both mean 'not capped'."""
    from quirk.reports.content_model import build_exec_content

    score_raw = _capped_score_raw()
    del score_raw["rating_cap_reason"]
    assert "rating_cap_reason" not in score_raw

    exec_content = build_exec_content(
        score_raw=score_raw, findings=[], roadmap_items=[]
    )
    assert exec_content.rating_cap_reason is None


def test_exec_content_construction_without_rating_cap_reason_still_works():
    """The field is defaulted, so every pre-existing ExecContent(...) keyword
    construction in the suite keeps working unmodified."""
    from quirk.reports.content_model import ExecContent

    result = ExecContent(
        narrative_lead="lead",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=0,
        score_band="FAIR",
        subscores={},
        raw_sum=0,
        sev_counts={},
    )
    assert result.rating_cap_reason is None


def test_render_docx_report_no_longer_takes_a_bespoke_cap_reason_kwarg():
    """WR-01: the `rating_cap_reason` keyword parameter is GONE from
    render_docx_report — the DOCX surface reads exec_content like every other
    score-derived value. Asserted against the real signature so re-adding the
    bespoke parameter (recreating the six-call-site divergence) fails here."""
    import inspect

    from quirk.reports.docx_renderer import render_docx_report

    params = inspect.signature(render_docx_report).parameters
    assert "rating_cap_reason" not in params, (
        "render_docx_report grew a bespoke rating_cap_reason parameter again; "
        "it must read exec_content.rating_cap_reason instead (184.4 WR-01)."
    )
    # exec_content is the seam it must use, so it had better still be there.
    assert "exec_content" in params


def test_docx_renders_cap_reason_sourced_from_exec_content():
    """End-to-end for the DOCX surface: with NO cap-reason keyword available,
    a capped exec_content must still produce the cap-reason paragraph, and an
    uncapped one must produce none."""
    docx = pytest.importorskip("docx")  # noqa: F841

    import tempfile
    from pathlib import Path

    from quirk.reports.content_model import build_exec_content
    from quirk.reports.docx_renderer import render_docx_report

    capped = build_exec_content(
        score_raw=_capped_score_raw(), findings=[], roadmap_items=[]
    )
    uncapped = build_exec_content(
        score_raw={**_capped_score_raw(), "rating_cap_reason": None},
        findings=[],
        roadmap_items=[],
    )

    with tempfile.TemporaryDirectory() as tmp:
        capped_path = str(Path(tmp) / "capped.docx")
        uncapped_path = str(Path(tmp) / "uncapped.docx")

        assert render_docx_report(
            path=capped_path, cfg=_cli_cfg(), findings=[], exec_content=capped
        )
        assert render_docx_report(
            path=uncapped_path, cfg=_cli_cfg(), findings=[], exec_content=uncapped
        )

        from docx import Document

        capped_text = "\n".join(p.text for p in Document(capped_path).paragraphs)
        uncapped_text = "\n".join(p.text for p in Document(uncapped_path).paragraphs)

    assert "Band capped at FAIR" in capped_text, (
        "the DOCX cap-reason paragraph vanished once the bespoke keyword was "
        f"removed — exec_content sourcing is broken. Got: {capped_text!r}"
    )
    assert "Cap reason" not in uncapped_text


def test_only_one_place_reads_rating_cap_reason_off_score_raw():
    """The WR-01 invariant as a source gate: `score_raw`-rooted reads of
    rating_cap_reason must be confined to build_exec_content() (the single
    derivation) plus executive.py's legacy exec_content-is-None branch, which
    has no shared model available and is unreachable from the shipped pipeline
    (writer.py always passes exec_content).

    Scanned from the source tree at run time rather than asserted from a
    written list, so a NEW renderer re-deriving the key off score_raw fails
    here instead of quietly recreating the divergence WR-01 closed.
    """
    from pathlib import Path

    reports_dir = Path(__file__).resolve().parent.parent / "quirk" / "reports"
    needle = 'score_raw.get("rating_cap_reason")'

    offenders = {}
    for path in sorted(reports_dir.rglob("*.py")):
        # Count only real reads, not the prose in comments/docstrings that
        # explains why this gate exists.
        hits = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if needle in line and not line.strip().startswith("#")
        ]
        if hits:
            offenders[path.name] = hits

    assert set(offenders) <= {"content_model.py", "executive.py"}, (
        "a renderer re-derives rating_cap_reason from score_raw instead of "
        f"reading exec_content.rating_cap_reason: {offenders!r}"
    )
    # Guard against the scan going vacuous (e.g. the needle string changing).
    assert "content_model.py" in offenders, (
        "the single authoritative read in build_exec_content() was not found "
        "— this gate is scanning for the wrong pattern and would pass "
        "vacuously."
    )
    assert len(offenders["content_model.py"]) == 1, (
        f"expected exactly ONE score_raw read of the key: {offenders!r}"
    )


# ---------------------------------------------------------------------------
# Phase 184.4 IN-02 — the DOCX surface must name the readiness band itself.
#
# The DOCX was the only one of the six render surfaces that never stated the
# band as its own field. The CLI writes "**Rating:** **{band}**", the HTML
# template writes <div class="score-band">{{ score_band }}</div>, the dashboard
# renders a badge — the DOCX wrote only the raw "raw_sum / 1.5 = score / 100"
# rollup. So an UNCAPPED DOCX report stated no band anywhere, and a CAPPED one
# named it only incidentally, inside the cap-reason sentence
# ("Band capped at FAIR: ...").
#
# That incidental mention is why this needs an UNCAPPED assertion specifically:
# a test that only checked a capped report would have passed before this fix.
# ---------------------------------------------------------------------------


def test_docx_names_the_band_even_when_uncapped():
    """IN-02: an uncapped DOCX report must state its own rating band.

    This is the case that was broken: with no cap, the pre-fix document had no
    occurrence of the band name at all. Asserted against a live python-docx
    round-trip read of the written file, not against the renderer's inputs.
    """
    pytest.importorskip("docx")

    import tempfile
    from pathlib import Path

    from docx import Document

    from quirk.reports.content_model import build_exec_content
    from quirk.reports.docx_renderer import render_docx_report

    # An uncapped, genuinely favourable score — the band must come from the
    # producer's own value, so assert against exec_content.score_band rather
    # than a hardcoded literal that could drift from the band table.
    uncapped = build_exec_content(
        score_raw={
            **_capped_score_raw(),
            "score": 92,
            "rating": "EXCELLENT",
            "rating_cap_reason": None,
        },
        findings=[],
        roadmap_items=[],
    )
    assert uncapped.rating_cap_reason is None, "fixture is not actually uncapped"
    band = uncapped.score_band

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "uncapped.docx")
        assert render_docx_report(
            path=path, cfg=_cli_cfg(), findings=[], exec_content=uncapped
        )
        text = "\n".join(p.text for p in Document(path).paragraphs)

    assert f"Rating: {band}" in text, (
        "an uncapped DOCX report does not name its readiness band anywhere "
        f"(expected a 'Rating: {band}' paragraph). This is IN-02: the DOCX was "
        f"the only surface silent about the band. Got: {text!r}"
    )
    # The band must not arrive via the cap-reason sentence, which is absent here.
    assert "Cap reason" not in text


def test_docx_names_both_the_capped_band_and_the_cap_reason():
    """IN-02 companion: a capped report states the CAPPED band as its own
    Rating field AND still carries the cap-reason sentence.

    The band field must show the post-cap band (what the reader is actually
    being told their posture is), not the pre-cap numeric band — otherwise the
    document would contradict itself, which is the BACK-89 failure mode this
    phase exists to close.
    """
    pytest.importorskip("docx")

    import tempfile
    from pathlib import Path

    from docx import Document

    from quirk.reports.content_model import build_exec_content
    from quirk.reports.docx_renderer import render_docx_report

    capped = build_exec_content(
        score_raw=_capped_score_raw(), findings=[], roadmap_items=[]
    )
    assert capped.rating_cap_reason, "fixture is not actually capped"

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "capped.docx")
        assert render_docx_report(
            path=path, cfg=_cli_cfg(), findings=[], exec_content=capped
        )
        text = "\n".join(p.text for p in Document(path).paragraphs)

    assert f"Rating: {capped.score_band}" in text, (
        f"capped DOCX does not name its band as a field. Got: {text!r}"
    )
    assert "Band capped at FAIR" in text, (
        f"capped DOCX lost its cap-reason sentence. Got: {text!r}"
    )
    # Self-consistency: the score_raw fixture is capped to FAIR, so the Rating
    # field must agree with the band named inside the cap sentence rather than
    # reporting the uncapped band the raw score alone would have produced.
    assert "Rating: FAIR" in text, (
        "the Rating field reports a different band than the cap-reason "
        f"sentence — the document contradicts itself. Got: {text!r}"
    )
