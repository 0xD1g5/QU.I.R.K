"""Phase 201 Plan 05 (LIFT-01/02/03/05) — CLI markdown/scorecard/JSON lift surfaces.

Covers the 7 behavior bullets from 201-05-PLAN.md:
  1. roadmap-{stamp}.md shows `(+N pts)` for modelable items, nothing for
     unmodelable items.
  2. roadmap-{stamp}.md shows the projected-score line + verbatim disclaimer
     directly after the heading, and shows neither when there is no
     projection.
  3. The scorecard's top-3 NOW actions carry the same `(+N pts)` parenthetical
     (RESEARCH Open Question 1, resolved ADOPTED).
  4. intelligence-{stamp}.json's `"score"` allowlist gains no `projected`/
     `lift` key; `"roadmap"` items carry `score_lift`.
  5. `ExecContent.projected_score` and each `RoadmapItem.score_lift` are
     populated on the object handed to the renderers.
  6. An unassessed scan (score None) produces no parenthetical, no projected
     line, and no disclaimer anywhere.
  7. A raising lift computation still produces a complete report with no
     lift text.

Uses the same mock-the-seams pattern as tests/test_reports_writer.py:
build_evidence_summary/compute_confidence/build_phased_roadmap are stubbed;
compute_readiness_score is stubbed to pass through to the REAL scorer (so
quirk.intelligence.score_lift's own internal compute_readiness_score calls —
imported directly from quirk.intelligence.scoring, not through writer.py's
namespace — produce real, non-fabricated deltas).
"""
from __future__ import annotations

import glob
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.intelligence.scoring import compute_readiness_score as _real_compute_readiness_score

# Locked copy (UI-SPEC Copywriting Contract) — verbatim, character for character.
_DISCLAIMER = "Advisory — this projection is a simulation and does not affect the readiness score."


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 201 Plan 05 Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _modelable_evidence(endpoints, findings):
    """A healthy-but-flawed scan triggering real modelable lifts (mirrors
    tests/test_score_lift.py's `_evidence()` fixture) — plaintext HTTP
    exposure and an expired certificate both resolve to a positive delta.
    """
    return {
        "totals": {"endpoints": 10, "findings": 8},
        "protocol_counts": {
            "TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1,
            "KERBEROS": 1, "POSTGRESQL": 1, "SMTPS": 1,
        },
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 0,
        "certificate_observations": {
            "expired_count": 2, "expiring_count": 1,
            "self_signed_count": 1, "certs_observed": 8,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.1},
        "finding_severity_counts": {
            "CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 1, "INFO": 1,
        },
        "tls_enum_coverage_ratio": 0.5,
    }


def _unassessed_evidence(endpoints, findings):
    """Zero endpoints — every `_*_assessed()` predicate in scoring.py is
    False, so compute_readiness_score returns score: None (SCORE-06)."""
    return {"totals": {"endpoints": 0, "findings": 0}}


def _passthrough_score(evidence, **kwargs):
    """Stub for `quirk.reports.writer.compute_readiness_score` that calls the
    REAL scorer — this is what makes score_lift.py's own internal
    (unmocked, directly-imported) calls to the real scorer meaningful."""
    return _real_compute_readiness_score(evidence, **kwargs)


def _stub_confidence(evidence):
    return {"confidence_score": 70, "factor_breakdown": {}}


def _roadmap_with_modelable_and_unmodelable_items(evidence, score):
    """One modelable NOW item per resolvable slug used by `_modelable_evidence`,
    plus one deliberately unmodelable LATER item (no evidence-delta mutator
    exists for it — RESEARCH's 5 honest-absence kinds)."""
    return {
        "items": [
            {
                "phase": "NOW",
                "title": "Remove plaintext HTTP exposure",
                "why": "Plaintext HTTP observed on 2 endpoint(s).",
                "owner_placeholder": "Security Owner",
                "timeframe": "0-30 days",
                "dependencies": [],
            },
            {
                "phase": "NOW",
                "title": "Replace expired certificates",
                "why": "2 expired certificate(s) observed.",
                "owner_placeholder": "Security Owner",
                "timeframe": "0-30 days",
                "dependencies": [],
            },
            {
                "phase": "LATER",
                "title": "Establish crypto governance review",
                "why": "Baseline governance recommendation.",
                "owner_placeholder": "Security Owner",
                "timeframe": "90+ days",
                "dependencies": [],
            },
        ]
    }


def _unassessed_roadmap(evidence, score):
    return {
        "items": [
            {
                "phase": "NOW",
                "title": "Remove plaintext HTTP exposure",
                "why": "Not assessed.",
                "owner_placeholder": "Security Owner",
                "timeframe": "0-30 days",
                "dependencies": [],
            },
        ]
    }


def _write_reports_with_stubs(cfg, *, evidence_fn, roadmap_fn):
    from quirk.reports.writer import write_reports

    with patch("quirk.reports.writer.build_evidence_summary", side_effect=evidence_fn), \
         patch("quirk.reports.writer.compute_readiness_score", side_effect=_passthrough_score), \
         patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence), \
         patch("quirk.reports.writer.build_phased_roadmap", side_effect=roadmap_fn):
        write_reports(cfg, endpoints=[], findings=[])


def _read_single(pattern):
    files = glob.glob(pattern)
    assert files, f"no file matched {pattern}"
    with open(files[0], "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Behavior 1 + 2: roadmap-{stamp}.md — parenthetical, absence, projected line
# ---------------------------------------------------------------------------

def test_roadmap_markdown_shows_lift_parenthetical_and_absence_for_unmodelable(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_modelable_evidence,
        roadmap_fn=_roadmap_with_modelable_and_unmodelable_items,
    )
    roadmap_md = _read_single(os.path.join(str(tmp_path), "roadmap-*.md"))

    assert "Remove plaintext HTTP exposure" in roadmap_md
    assert "Replace expired certificates" in roadmap_md
    # Both modelable items carry a real (+N pts) parenthetical.
    plaintext_line = next(
        line for line in roadmap_md.splitlines() if "Remove plaintext HTTP exposure" in line
    )
    expired_line = next(
        line for line in roadmap_md.splitlines() if "Replace expired certificates" in line
    )
    assert " pts)" in plaintext_line, roadmap_md
    assert " pts)" in expired_line, roadmap_md

    # The unmodelable LATER item shows no parenthetical at all — absence
    # means "no `pts)` on that line", not "(+0 pts)" (SCORE-06 house style).
    governance_line = next(
        line for line in roadmap_md.splitlines() if "Establish crypto governance review" in line
    )
    assert "pts)" not in governance_line, governance_line


def test_roadmap_markdown_shows_projected_line_and_verbatim_disclaimer(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_modelable_evidence,
        roadmap_fn=_roadmap_with_modelable_and_unmodelable_items,
    )
    roadmap_md = _read_single(os.path.join(str(tmp_path), "roadmap-*.md"))

    assert "# Quantum Crypto Transition Roadmap" in roadmap_md
    lines = roadmap_md.splitlines()
    heading_idx = lines.index("# Quantum Crypto Transition Roadmap")
    following = "\n".join(lines[heading_idx + 1:heading_idx + 6])
    assert "Projected score if all items resolved:" in following
    # Full-string equality against the locked copy — not a substring match.
    assert _DISCLAIMER in lines
    disclaimer_idx = lines.index(_DISCLAIMER)
    assert disclaimer_idx > heading_idx
    assert disclaimer_idx < lines.index("## NOW")


def test_roadmap_markdown_shows_neither_line_when_no_projection(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_unassessed_evidence,
        roadmap_fn=_unassessed_roadmap,
    )
    roadmap_md = _read_single(os.path.join(str(tmp_path), "roadmap-*.md"))

    assert "Projected score if all items resolved:" not in roadmap_md
    assert _DISCLAIMER not in roadmap_md


# ---------------------------------------------------------------------------
# Behavior 3: scorecard top-3 NOW actions (RESEARCH Open Question 1 — ADOPTED)
# ---------------------------------------------------------------------------

def test_scorecard_top3_now_actions_carry_lift_parenthetical(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_modelable_evidence,
        roadmap_fn=_roadmap_with_modelable_and_unmodelable_items,
    )
    scorecard_md = _read_single(os.path.join(str(tmp_path), "scorecard-*.md"))

    idx = scorecard_md.find("Next 30")
    assert idx != -1
    section = scorecard_md[idx:]
    plaintext_line = next(
        line for line in section.splitlines() if "Remove plaintext HTTP exposure" in line
    )
    assert " pts)" in plaintext_line, section


# ---------------------------------------------------------------------------
# Behavior 4: intelligence-{stamp}.json — "score" allowlist untouched,
# "roadmap" items carry score_lift
# ---------------------------------------------------------------------------

def test_intelligence_json_score_block_has_no_projected_or_lift_key(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_modelable_evidence,
        roadmap_fn=_roadmap_with_modelable_and_unmodelable_items,
    )
    intel_json = _read_single(os.path.join(str(tmp_path), "intelligence-*.json"))
    data = json.loads(intel_json)

    score_keys = [k.lower() for k in data["score"].keys()]
    assert not any("projected" in k or "lift" in k for k in score_keys), data["score"]

    roadmap_items = data["roadmap"]["items"]
    lifted = [i for i in roadmap_items if "score_lift" in i]
    assert lifted, roadmap_items
    for item in roadmap_items:
        if item["title"] == "Establish crypto governance review":
            assert "score_lift" not in item, item


# ---------------------------------------------------------------------------
# Behavior 5: ExecContent.projected_score / RoadmapItem.score_lift populated
# ---------------------------------------------------------------------------

def test_exec_content_receives_projected_score_and_roadmap_item_lifts():
    from quirk.reports.content_model import build_exec_content
    from quirk.intelligence.score_lift import compute_item_lifts, compute_projected_score

    evidence = _modelable_evidence(None, None)
    score_raw = _real_compute_readiness_score(evidence, profile="balanced", weights=None)
    roadmap_raw = _roadmap_with_modelable_and_unmodelable_items(evidence, score_raw)
    items = roadmap_raw["items"]

    lifts = compute_item_lifts(evidence, items, profile="balanced", weights=None)
    projected = compute_projected_score(evidence, items, profile="balanced", weights=None)
    from quirk.intelligence.remediation import slug_for_title
    for item in items:
        slug = slug_for_title(item["title"])
        if slug is not None and slug in lifts:
            item["score_lift"] = lifts[slug]

    exec_content = build_exec_content(
        score_raw=score_raw,
        findings=[],
        roadmap_items=items,
        projected_score=projected,
    )
    assert exec_content.projected_score == projected
    assert exec_content.projected_score is not None

    by_title = {r.title: r for r in exec_content.roadmap_items}
    assert by_title["Remove plaintext HTTP exposure"].score_lift is not None
    assert by_title["Establish crypto governance review"].score_lift is None


# ---------------------------------------------------------------------------
# Behavior 6: unassessed scan -> no parenthetical/projected/disclaimer anywhere
# ---------------------------------------------------------------------------

def test_unassessed_scan_produces_no_lift_text_anywhere(tmp_path):
    cfg = _make_cfg(tmp_path)
    _write_reports_with_stubs(
        cfg,
        evidence_fn=_unassessed_evidence,
        roadmap_fn=_unassessed_roadmap,
    )
    roadmap_md = _read_single(os.path.join(str(tmp_path), "roadmap-*.md"))
    scorecard_md = _read_single(os.path.join(str(tmp_path), "scorecard-*.md"))

    for text in (roadmap_md, scorecard_md):
        assert "pts)" not in text
        assert "Projected score if all items resolved:" not in text
        assert _DISCLAIMER not in text


# ---------------------------------------------------------------------------
# Behavior 7: a raising lift computation still yields a complete report
# ---------------------------------------------------------------------------

def test_lift_computation_exception_degrades_to_complete_report_with_no_lift_text(tmp_path):
    cfg = _make_cfg(tmp_path)

    def _raise_lifts(*args, **kwargs):
        raise RuntimeError("boom")

    def _raise_projected(*args, **kwargs):
        raise RuntimeError("boom")

    from quirk.reports.writer import write_reports

    with patch("quirk.reports.writer.build_evidence_summary", side_effect=_modelable_evidence), \
         patch("quirk.reports.writer.compute_readiness_score", side_effect=_passthrough_score), \
         patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence), \
         patch("quirk.reports.writer.build_phased_roadmap", side_effect=_roadmap_with_modelable_and_unmodelable_items), \
         patch("quirk.reports.writer.compute_item_lifts", side_effect=_raise_lifts), \
         patch("quirk.reports.writer.compute_projected_score", side_effect=_raise_projected):
        write_reports(cfg, endpoints=[], findings=[])

    roadmap_md = _read_single(os.path.join(str(tmp_path), "roadmap-*.md"))
    scorecard_md = _read_single(os.path.join(str(tmp_path), "scorecard-*.md"))
    intel_json = _read_single(os.path.join(str(tmp_path), "intelligence-*.json"))

    # The report completed — the roadmap items are still present.
    assert "Remove plaintext HTTP exposure" in roadmap_md
    for text in (roadmap_md, scorecard_md):
        assert "pts)" not in text
        assert "Projected score if all items resolved:" not in text
        assert _DISCLAIMER not in text

    data = json.loads(intel_json)
    for item in data["roadmap"]["items"]:
        assert "score_lift" not in item
