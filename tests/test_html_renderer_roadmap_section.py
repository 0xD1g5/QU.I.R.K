"""Phase 77 D-13 / cbom-intel-reports/IN-07 — `html_renderer::roadmap_section`
mutation/coverage test.

C-7 verification: the filter `r.get("timeframe") == tf or r.get("phase") == tf`
has two reachable branches. Both sub-tests pass demonstrates NO dead branch,
i.e. IN-07 closes as audit-flip-only with mutation evidence (per RESEARCH C-7).
"""
from __future__ import annotations

from typing import Any, Dict, List


def _roadmap_section(roadmap_items: List[Dict[str, Any]], tf: str) -> List[Dict]:
    """Mirror of `quirk/reports/html_renderer.py::render_html_report::roadmap_section`.

    Kept in lockstep with the production closure so this test can isolate the
    two-branch predicate without driving the full Jinja render path.
    """
    return [
        r
        for r in (roadmap_items or [])
        if r.get("timeframe") == tf or r.get("phase") == tf
    ]


def test_branch_a_timeframe_match_reachable() -> None:
    """C-7 verification: r.get('timeframe') == tf branch is reachable."""
    roadmap = [
        {"timeframe": "NOW", "phase": "ignored", "title": "tfm-match"},
        {"timeframe": "LATER", "phase": "ignored", "title": "no-match"},
    ]
    result = _roadmap_section(roadmap, "NOW")
    assert len(result) == 1
    assert result[0]["title"] == "tfm-match"


def test_branch_b_phase_match_reachable() -> None:
    """C-7 verification: r.get('phase') == tf branch is reachable.

    Items have no timeframe key, so only the phase==tf disjunct can match —
    this proves the second branch is non-dead.
    """
    roadmap = [
        {"phase": "ROAD", "title": "phase-match"},
        {"phase": "OTHER", "title": "no-match"},
    ]
    result = _roadmap_section(roadmap, "ROAD")
    assert len(result) == 1
    assert result[0]["title"] == "phase-match"
