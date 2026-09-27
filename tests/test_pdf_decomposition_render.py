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
gracefully to `False` rather than raising -- it catches PlaywrightError /
PlaywrightTimeoutError / OSError / RuntimeError from *any* source
(`quirk/reports/html_renderer.py:1386-1391`), a missing browser binary being only the
most common one -- so this module SKIPS cleanly in the required `Linux Full Suite` CI
job, where Chromium is deliberately absent. See `_render_or_skip`: because that one
return value covers several causes, the skip reason states the ambiguity and resolves
whether a Chromium binary is actually on disk rather than asserting a cause. It executes
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

# The six decomposition rows as the PDF text layer actually renders them: the row label,
# then that pillar's subscore, then the `/25` per-pillar budget — e.g. `Hygiene 20 /25`.
#
# THE VALUES HERE ARE HAND-TYPED AND MUST STAY THAT WAY. They are deliberately NOT read
# out of `_FULL_SCORE_RAW`: deriving the expectation from the same dict that is fed to the
# renderer is self-referential and would pass against any mutation that changed both
# sides at once. The fixture-sum guard in the test body catches a fixture edit that
# strands these literals.
#
# WHY THE VALUES ARE ASSERTED AT ALL, AND NOT JUST THE LABELS (Phase 207 review W-02):
# the six row labels are STATIC TEMPLATE TEXT. They render whether or not the matching
# subscore exists — proved by mutation: deleting `subscores["data_at_rest"]` and
# re-extracting the text layer still yields `Data at Rest`, so a label-only assertion
# cannot detect a lost, zeroed or em-dashed row. Only the label-adjacent VALUE pair can.
_PILLAR_ROWS = (
    ("Hygiene", 20),
    ("Modern TLS", 18),
    ("Identity", 15),
    ("Agility", 15),
    ("Data at Rest", 10),
    ("Data in Motion", 21),
)

# The six pillar row labels as they appear in the rendered decomposition table. Derived
# from the hand-typed pairs above (still a literal in this module, never the fixture).
_PILLAR_LABELS = tuple(label for label, _ in _PILLAR_ROWS)


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


def _chromium_verdict() -> str:
    """Best-effort: report whether a Chromium binary is actually on disk here.

    Mirrors the pattern `cf8c1224` added to `browser_e2e_harness.chromium_page()`. NEVER
    RAISES -- every failure path returns a string, because this function is only ever
    called on the way into a `pytest.skip` and an exception escaping it would convert that
    intended SKIP into an ERROR (D-10).
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = p.chromium.executable_path
            present = os.path.exists(exe)
    except Exception as exc:  # pragma: no cover - resolution is not itself expected to fail
        return (
            f"Could not resolve the Chromium executable path ({type(exc).__name__}: {exc}), "
            "so this skip cannot say whether a browser is installed -- playwright itself may "
            "not be importable, which is also an expected state on a minimal install."
        )
    if present:
        return (
            f"Chromium executable IS present at {exe}, so a MISSING BROWSER IS NOT THE "
            "EXPLANATION here. Investigate this as a real render failure; do NOT read it as "
            "expected non-coverage."
        )
    return (
        f"Chromium executable is NOT installed (looked for {exe}) -- this is the expected "
        "state in Linux Full Suite."
    )


def _render_or_skip(html_path: str, pdf_path: str) -> None:
    """Render through render_pdf_report; skip if it degraded instead of producing a PDF.

    Converting that degradation to a skip (never an error) is load-bearing: the citation
    guard treats an ERROR as fatal even under a `CI-EXEMPT:` declaration, so an escaping
    exception here would redden the required `Linux Full Suite` job regardless of how the
    disposition is annotated. That contract is why the `except` in `_chromium_verdict` is
    deliberately bare.

    WHAT A `False` RETURN DOES AND DOES NOT TELL US (corrected per Phase 207 review W-03).
    An earlier revision of this skip reason asserted a single cause -- "Chromium browser
    binary not available". That is the *expected* cause in `Linux Full Suite`, but it is
    not what the return value means: `render_pdf_report` catches
    `(PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError)` from ANY source and
    returns `False` (`quirk/reports/html_renderer.py:1386-1391`), so a template render
    failure, a page-load timeout or a disk error all land in the same bucket. Naming one
    cause in the reason string would send a future reader of a Browser E2E skip -- where
    Chromium is installed on purpose -- looking for a browser that is right there. So the
    reason now states the ambiguity and appends a resolved verdict on whether the binary
    is actually on disk.
    """
    # TRIAGE-149 CLUSTER 2 — the shared-Playwright-singleton contamination, hitting this node
    # directly. Found 2026-09-27 by running the FULL suite rather than this file: standalone this
    # node passes 3/3 in ~0.6s, but in an unfiltered suite run `sync_playwright().__enter__` raises
    # `AttributeError: 'PlaywrightContextManager' object has no attribute '_playwright'` because an
    # earlier test tore the singleton's greenlet/event-loop machinery down. That is the exact
    # signature documented at docs/test-triage-149.md:57-75 for the other 14 victims.
    #
    # It matters here beyond tidiness: `render_pdf_report` catches PlaywrightError /
    # PlaywrightTimeoutError / OSError / RuntimeError, and AttributeError is in NONE of those, so it
    # propagated and the node FAILED rather than skipped — breaking D-10's skip-never-error contract
    # in the required Linux Full Suite job. Observed failing in BOTH legs of the full suite.
    #
    # Narrow on purpose: only the two-token contamination signature is converted to a skip, and any
    # other AttributeError is re-raised. A blanket `except AttributeError` here would hide a real
    # renderer bug behind an environment-shaped skip. Coverage is not lost — this node executes for
    # real in the Browser E2E job, a separate process where nothing has pre-torn-down the singleton,
    # which is precisely the structural cure D-01/D-02 chose that job for.
    try:
        result = render_pdf_report(html_path, pdf_path)
    except AttributeError as exc:
        message = str(exc)
        if "PlaywrightContextManager" not in message or "_playwright" not in message:
            raise
        pytest.skip(
            "TRIAGE-149 Cluster 2: the shared Playwright singleton was torn down by an earlier "
            f"test in this process, so sync_playwright() could not start -- {message}. This is "
            "order-dependent contamination, NOT a defect in UAT-88-03 or in render_pdf_report: "
            "this node passes standalone. It is skipped rather than failed because an ERROR or "
            "FAILURE here reddens the required Linux Full Suite check regardless of any CI-EXEMPT "
            "declaration, while a skip does not (D-10). UAT-88-03 executes for real in the "
            "Browser E2E job (D-01/D-02), a separate process with no such contamination."
        )

    if result is False:
        pytest.skip(
            "render_pdf_report() degraded to False, so no PDF was produced and UAT-88-03 "
            "cannot be asserted in this run. The return value does NOT identify a cause: "
            "render_pdf_report catches PlaywrightError / PlaywrightTimeoutError / OSError / "
            "RuntimeError from any source (quirk/reports/html_renderer.py:1386-1391), so a "
            "missing Chromium binary, a template render failure, a page-load timeout and a "
            f"disk error are indistinguishable here. {_chromium_verdict()} The expected "
            "cause in Linux Full Suite is the missing binary; UAT-88-03 executes for real "
            "in the Browser E2E job (D-01/D-02)."
        )

    # ARTIFACT-LEVEL check, replacing an earlier `assert result is True` that could not
    # fail (Phase 207 review I-01): `render_pdf_report` returns only True or False and the
    # False branch has already skipped, so the old assertion had no reachable failing
    # state. These two CAN fail -- they catch a renderer that reports success without
    # leaving a usable file on disk, and they name that condition instead of letting it
    # surface as an opaque pypdf parse error in the caller.
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0, (
        f"render_pdf_report returned {result!r} (not False, so this is not the "
        f"missing-browser skip path) but left no non-empty PDF at {pdf_path!r}."
    )
    with open(pdf_path, "rb") as fh:
        magic = fh.read(5)
    assert magic == b"%PDF-", (
        f"render_pdf_report returned {result!r} but the file at {pdf_path!r} does not "
        f"begin with the %PDF- magic bytes; first 5 bytes were {magic!r}."
    )


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
    header repeats between the `Modern TLS` and `Identity` rows), so every row assertion
    below runs against the JOINED multi-page text.

    WHAT THE LABEL LEG DOES AND DOES NOT PROVE (corrected per Phase 207 review W-02). An
    earlier revision of this docstring claimed that asserting all six labels individually
    across the joined text "is also the no-truncation proof". It is not. The six labels are
    static template text: they render whether or not the matching subscore exists, which
    was established by mutation — with `subscores["data_at_rest"]` deleted, `Data at Rest`
    is STILL in the extracted text layer. The label leg therefore proves only that no row's
    *label* was lost or truncated at the page break. The no-truncation-of-DATA proof is the
    per-row label-adjacent VALUE leg below (`_PILLAR_ROWS`), which is what fails when a row
    goes missing, zero or em-dashed. Do not weaken it back to labels alone.
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

    # Normalise whitespace runs (the PDF text layer inserts line breaks at page/column
    # boundaries) before any assertion that spans more than one token. Done ONCE here, and
    # used by both the per-row leg and the rollup-sentence leg below.
    normalised = re.sub(r"\s+", " ", full_text)

    # Section heading survived the render.
    assert "Score Decomposition" in full_text, (
        "Missing 'Score Decomposition' section heading in extracted PDF text"
    )

    # Each of the six pillar labels, asserted individually so a failure names the lost row.
    # NOTE: the labels are static template text (see the docstring) — this leg proves the
    # label survived the page break, NOT that the row carries data. That is the next leg.
    for label in _PILLAR_LABELS:
        assert label in full_text, (
            f"Missing decomposition row label in extracted PDF text: {label!r} "
            f"(row lost, or truncated at the table's page break)"
        )

    # Each of the six pillar SUBSCORE VALUES, asserted as a label-adjacent pair so a lost,
    # zeroed or em-dashed row fails a NAMED leg here rather than only showing up two legs
    # later in the rollup arithmetic. Expected strings are built from the hand-typed
    # literals in `_PILLAR_ROWS`, never from `_FULL_SCORE_RAW`.
    #
    # `/25` is included because it is the per-pillar budget the template renders right
    # after the value; requiring the full `<label> <value> /25` triple is what makes this
    # positional rather than a bare "the digit 20 appears somewhere in a 7-page document".
    for label, value in _PILLAR_ROWS:
        expected_row = f"{label} {value} /25"
        assert expected_row in normalised, (
            f"Missing decomposition row VALUE in extracted PDF text: expected the "
            f"label-adjacent triple {expected_row!r}. The row label itself is static "
            f"template text and asserting it alone cannot catch this, so if the label leg "
            f"above passed and this failed, the row rendered WITHOUT its subscore (lost, "
            f"zeroed, or em-dashed) — or the value changed."
        )

    # Hand-computed, literal integers -- NOT read from _FULL_SCORE_RAW.
    raw_sum = 20 + 18 + 15 + 15 + 10 + 21  # == 99
    divisor = 1.5
    expected_rollup = round(raw_sum / divisor)  # == 66

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
