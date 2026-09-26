"""Phase 207 / COV-05 / UAT-88-03: the six-row score-decomposition table and its
rollup arithmetic sentence survive HTML -> PDF rendering as extractable text.

This is the **PDF leg**, one layer downstream of UAT-88-02's HTML leg in
`tests/test_score_decomposition_render.py`. That sibling asserts against the rendered
HTML *source string*; this module asserts against the *extracted text layer* of a real
Chromium-rendered PDF. The two artifacts are different strings even though they come
from the same template -- notably, the PDF text layer carries plain Unicode `÷` with
no HTML markup, where the HTML source carries `&divide;` inside `<strong>` tags. Do not
port assertions between the two files verbatim.

**This test requires a Chromium browser binary.** `render_pdf_report()` degrades
gracefully to `False` when Playwright is not importable or the browser cannot launch
(`quirk/reports/html_renderer.py:1351-1394`), so this module SKIPS cleanly in the
required `Linux Full Suite` CI job, where Chromium is deliberately absent. It executes
for real only in the non-gating Browser E2E job added by Phase 207 Plan 04, per D-01 /
D-02: the browser leg lives in its own job so the documented TRIAGE-149 order-dependent
flake class cannot redden the check every PR must pass.

**A skip here is not a pass.** A skipped run proves nothing about whether the
decomposition table survived the render; it proves only that no browser was present.
Coverage for UAT-88-03 is established by the Browser E2E job's real execution, which is
why the disposition citing this node must carry a `CI-EXEMPT:` declaration (D-10) --
`tests/test_uat_disposition_integrity.py` executes cited nodes inside `Linux Full Suite`
and asserts `skipped == 0`.

No pytest marker is registered for this module on purpose: `Linux Full Suite` runs
`pytest -q -m ""`, an empty marker expression that selects ALL tests and overrides
`pyproject.toml`'s `addopts`, so a marker could not keep this test out of the required
job. The Browser E2E job selects this file by explicit path instead.
"""
from __future__ import annotations

import os
import re
from types import SimpleNamespace

import pytest

pytest.importorskip("pypdf")

import pypdf  # noqa: E402

from quirk.intelligence.scoring import SCORING_VERSION  # noqa: E402
from quirk.reports.content_model import build_exec_content  # noqa: E402
from quirk.reports.html_renderer import render_html_report, render_pdf_report  # noqa: E402


# Fixture defined LOCALLY rather than imported from
# tests/test_score_decomposition_render.py: `tests/` has no package `__init__`, and a
# cross-module private-name import would be a fragile coupling between two independent
# UAT cases. The six subscores are the same values, deliberately: 20 + 18 + 15 + 15 +
# 10 + 21 == 99, and 99 / 1.5 == 66 exactly, so the template renders the *uncapped*
# rollup branch.
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

# The six pillar row labels as they appear in the rendered decomposition table.
_PILLAR_LABELS = (
    "Hygiene",
    "Modern TLS",
    "Identity",
    "Agility",
    "Data at Rest",
    "Data in Motion",
)


def _make_minimal_cfg(outdir: str):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="207-01 PDF Decomposition Render Test Org",
            report_owner="Decomposition PDF Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=outdir),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )


def _render_or_skip(html_path: str, pdf_path: str) -> None:
    """Render through render_pdf_report; skip if the Chromium binary is unavailable.

    Mirrors `tests/test_pdf_metadata_constants.py:47-56` exactly. A `False` return means
    Playwright is not importable or the browser binary is missing / cannot launch --
    `render_pdf_report` catches PlaywrightError / TimeoutError / OSError / RuntimeError
    internally and degrades to `False` rather than raising. Converting that to a skip
    (never an error) is load-bearing: the citation guard treats an ERROR as fatal even
    under a `CI-EXEMPT:` declaration, so an escaping exception here would redden the
    required `Linux Full Suite` job regardless of how the disposition is annotated.
    """
    result = render_pdf_report(html_path, pdf_path)
    if result is False:
        pytest.skip(
            "render_pdf_report returned False - Chromium browser binary not available "
            "(Playwright runtime missing or cannot launch). This is the expected state "
            "in Linux Full Suite; UAT-88-03 executes in the Browser E2E job (D-01/D-02)."
        )
    assert result is True


def _extract_pdf_text(tmp_path) -> str:
    """Render _FULL_SCORE_RAW to HTML, then to PDF, and return the joined text layer."""
    exec_content = build_exec_content(score_raw=_FULL_SCORE_RAW, findings=[], roadmap_items=[])
    cfg = _make_minimal_cfg(str(tmp_path))

    html_path = os.path.join(str(tmp_path), "decomposition.html")
    pdf_path = os.path.join(str(tmp_path), "decomposition.pdf")
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

    _render_or_skip(html_path, pdf_path)

    reader = pypdf.PdfReader(pdf_path)
    assert len(reader.pages) > 0, "Rendered PDF has zero pages"
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_uat_88_03_decomposition_survives_pdf_render(tmp_path):
    """Covers UAT-88-03: the Score Decomposition section, all six pillar row labels, and
    the rollup arithmetic sentence are present as EXTRACTABLE TEXT in the rendered PDF.

    Red-proofing discipline, inherited from the UAT-88-02 HTML sibling: every expected
    value below is a hand-typed literal written out in this test body -- never read back
    out of `_FULL_SCORE_RAW` or `exec_content`. Reading the expectation out of the same
    dict fed to the renderer is self-referential and would pass against a wrong-arithmetic
    mutation. The fixture-sum guard immediately below makes a later silent fixture edit
    fail loudly here rather than quietly weakening these assertions.

    The table straddles a PDF page break in the real render (the "Category Score Budget"
    header repeats, with no row content lost), so asserting all six labels individually
    across the joined multi-page text is also the no-truncation proof.
    """
    # Guard: if someone edits the fixture, this fails loudly instead of silently
    # invalidating the hand-computed literals below.
    assert sum(_FULL_SCORE_RAW["subscores"].values()) == 99, (
        "Fixture subscores no longer sum to 99 - the hand-computed rollup literals in "
        "this test body are stale. Update both together."
    )
    assert _FULL_SCORE_RAW["score_divisor"] == 1.5, (
        "Fixture score_divisor changed - hand-computed rollup literals are stale."
    )

    full_text = _extract_pdf_text(tmp_path)

    # Section heading survived the render.
    assert "Score Decomposition" in full_text, (
        "Missing 'Score Decomposition' section heading in extracted PDF text"
    )

    # Each of the six pillar labels, asserted individually so a failure names the lost row.
    for label in _PILLAR_LABELS:
        assert label in full_text, (
            f"Missing decomposition row label in extracted PDF text: {label!r} "
            f"(row lost, or truncated at the table's page break)"
        )

    # Hand-computed, literal integers -- NOT read from _FULL_SCORE_RAW.
    raw_sum = 20 + 18 + 15 + 15 + 10 + 21  # == 99
    divisor = 1.5
    expected_rollup = round(raw_sum / divisor)  # == 66

    # Normalise whitespace runs (the PDF text layer inserts line breaks at page/column
    # boundaries) before the full-sentence assertion.
    normalised = re.sub(r"\s+", " ", full_text)

    # Component tokens asserted separately FIRST, so a Chromium text-layer whitespace
    # change degrades to a precise failure rather than one opaque full-string mismatch.
    # Note the PDF text layer carries plain Unicode U+00F7, never the HTML's `&divide;`.
    assert f"Rollup: {raw_sum}" in normalised, (
        f"Missing rollup raw-sum token 'Rollup: {raw_sum}' in extracted PDF text"
    )
    assert "÷" in normalised, (
        "Missing plain Unicode division sign U+00F7 in extracted PDF text"
    )
    assert f"{divisor}" in normalised, (
        f"Missing rollup divisor token {divisor!r} in extracted PDF text"
    )
    assert f"= {expected_rollup} " in normalised, (
        f"Missing rollup result token '= {expected_rollup}' in extracted PDF text"
    )
    assert "/ 100" in normalised, "Missing rollup '/ 100' denominator in extracted PDF text"

    # Full sentence, exactly as extracted from the real render.
    expected_sentence = f"Rollup: {raw_sum} ÷ {divisor} = {expected_rollup} / 100"
    assert expected_sentence in normalised, (
        f"Rollup sentence does not match hand-computed arithmetic in extracted PDF "
        f"text: expected {expected_sentence!r}"
    )
