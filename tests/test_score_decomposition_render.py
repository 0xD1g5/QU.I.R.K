"""Phase 208 Plan 02 / COV-07 / UAT-88-02: HTML render-output level assertions for
the six-row /25 score-decomposition table and both rollup sentences.

Scope limit (this project's standing render-test convention): these assertions cover
row-label and value **presence** in the rendered HTML, not visual order or appearance.
This project's render tests assert presence, not appearance (see
`tests/test_score_render_parity.py`, `tests/test_html_report.py`), and COV-07's HTML
leg inherits that limit rather than implying visual-fidelity coverage.

Today, prior to this file, only data-layer parity (`test_score_render_parity.py`) and
markdown presence (`test_score_transparency.py`) are covered for the decomposition
table -- UAT-88-02's own GAP text is explicit that neither exercises the rendered HTML
this file now exercises directly.

The PDF leg (UAT-88-03) is OUT OF SCOPE per D-01/D-02 and is deliberately NOT stubbed
here: `.github/workflows/python-ci.yml` installs no headless browser toolchain, so a
browser-driven-render test would never run anywhere and would be cited as coverage
while being permanently skipped -- "a test which can never fail is not a guard."
UAT-88-03 is handed to Phase 207 as a costed decision in plan 208-06.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

from quirk.intelligence.scoring import SCORING_VERSION
from quirk.reports.content_model import build_exec_content, NOT_COMPUTED_STATEMENT
from quirk.reports.html_renderer import render_html_report


def _make_minimal_cfg(outdir: str):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="208-02 Decomposition Render Test Org",
            report_owner="Decomposition Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=outdir),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )


# All six subscores non-None (unlike test_score_render_parity.py's deliberately
# partial fixtures) so every row and both rollup sentences render with real values.
# 20 + 18 + 15 + 15 + 10 + 21 = 99; 99 / 1.5 = 66 exactly, so score == 66 renders the
# uncapped rollup branch (rollup_computed == total_score).
_FULL_SCORE_RAW = {
    "score": 66,
    "rating": "GOOD",
    "subscores": {
        "hygiene": 20,
        "modern_tls": 18,
        "identity_trust": 15,
        "agility_signals": 15,
        "data_at_rest": 10,
        "data_in_motion": 21,
    },
    "drivers": [],
    "domains_assessed": 6,
    "domains_total": 6,
    "score_divisor": 1.5,
    "coverage_disclosure": "6 of 6 domains assessed",
    "scoring_version": SCORING_VERSION,
}


def _render_decomposition_html(tmp_path) -> str:
    """Render the HTML report from `_FULL_SCORE_RAW` and read it back from disk."""
    exec_content = build_exec_content(score_raw=_FULL_SCORE_RAW, findings=[], roadmap_items=[])
    cfg = _make_minimal_cfg(str(tmp_path))

    html_path = os.path.join(str(tmp_path), "decomposition.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=[],
        score={"drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
        exec_content=exec_content,
    )
    with open(html_path, encoding="utf-8") as f:
        return f.read()


def test_decomposition_table_renders_all_six_labels(tmp_path):
    """Covers UAT-88-02 Pass Criteria: the six /25 pillar-subscore rows render in the
    HTML report, each with its label and its literal integer value.

    Asserting only "a table exists" does not red-prove against a single-row deletion
    -- each label is asserted individually, plus the /25 budget-cell count, so a
    one-row deletion (Red-proof 4) fails this specific assertion.
    """
    html = _render_decomposition_html(tmp_path)

    assert "Hygiene" in html, "Missing decomposition row label: Hygiene"
    assert "Modern TLS" in html, "Missing decomposition row label: Modern TLS"
    assert "Identity" in html, "Missing decomposition row label: Identity"
    assert "Agility" in html, "Missing decomposition row label: Agility"
    assert "Data at Rest" in html, "Missing decomposition row label: Data at Rest"
    assert "Data in Motion" in html, "Missing decomposition row label: Data in Motion"

    # Row-count proof: exactly 6 `/25` budget cells in the decomposition table.
    budget_cell_count = html.count("<td>/25</td>")
    assert budget_cell_count == 6, (
        f"Expected exactly 6 '/25' budget cells in the decomposition table, "
        f"found {budget_cell_count}."
    )

    # Each subscore's literal integer value from the fixture appears in the HTML.
    for key, value in _FULL_SCORE_RAW["subscores"].items():
        assert f">{value}<" in html, (
            f"Subscore value for '{key}' ({value}) not found rendered in HTML."
        )


def test_decomposition_rollup_arithmetic_sentence_renders_hand_computed_value(tmp_path):
    """Covers UAT-88-02 Pass Criteria: the Rollup sentence renders the TRUE arithmetic
    (raw_sum / divisor = rollup_computed), hand-computed independently of the fixture
    dict fed into the renderer.

    COV-07 carve-out 1: the expectation below is a literal, hand-typed arithmetic
    expression over integers written out explicitly in THIS test body -- never read
    back out of `_FULL_SCORE_RAW` or `exec_content`. Reading `rollup_computed` back
    out of the same dict fed to the renderer is self-referential and would pass
    regardless of the mutation in Red-proof 5.
    """
    html = _render_decomposition_html(tmp_path)

    # Hand-computed, literal integers -- NOT read from _FULL_SCORE_RAW.
    raw_sum = 20 + 18 + 15 + 15 + 10 + 21  # == 99
    divisor = 1.5
    expected_rollup = round(raw_sum / divisor)  # == 66

    # Format-exact assertion: the template's UNCAPPED branch renders
    # "{raw_sum} &divide; {divisor} = <strong>{rollup_computed} / 100</strong>" (no
    # "capped to" clause) exactly when rollup_computed == total_score. A weaker
    # assertion that only checks "<strong>66</strong>" or "<strong>66 / 100</strong>"
    # appear ANYWHERE in the HTML is self-referentially blind to a wrong-arithmetic
    # mutation: on this fixture total_score == 66 too, so a mutated rollup_computed
    # (e.g. 59) still renders "capped to <strong>66 / 100</strong>" -- the substring
    # "66 / 100" is present regardless of whether the arithmetic is correct. Anchoring
    # on the full "= <strong>...</strong>" prefix (immediately after the "=" sign, not
    # after "capped to") and requiring "capped to" to be ABSENT closes that hole.
    expected_uncapped_sentence = (
        f"{raw_sum} &divide; {divisor} = <strong>{expected_rollup} / 100</strong>"
    )
    assert expected_uncapped_sentence in html, (
        f"Rollup sentence does not match hand-computed uncapped arithmetic: "
        f"expected {expected_uncapped_sentence!r} in rendered HTML."
    )
    assert "capped to" not in html, (
        "Rollup sentence unexpectedly rendered the capped-to branch -- "
        "rollup_computed no longer equals total_score, arithmetic is wrong."
    )


def test_decomposition_domain_count_sentence_renders_assessed_over_total(tmp_path):
    """Covers UAT-88-02 Pass Criteria: the rollup-formula block renders the
    "N of M assessed pillar subscores" sentence with the true domain-assessed count,
    proving the COMPUTED branch (not the not-computed branch) fired.

    This is a SEPARATE assertion from the arithmetic sentence test above and gets its
    own distinct red-proof mutation (`effective_domain_counts`, not
    `rollup_computed_score`) in Task 2.
    """
    html = _render_decomposition_html(tmp_path)

    assert "6 of 6 assessed pillar subscores" in html, (
        "Missing domain-count sentence: '6 of 6 assessed pillar subscores'"
    )
    assert NOT_COMPUTED_STATEMENT not in html, (
        "NOT_COMPUTED_STATEMENT present in HTML -- the not-computed branch fired "
        "instead of the computed rollup-formula branch."
    )
