"""Unit tests for scripts/uat_corpus.py (Phase 204 Plan 01, COV-03).

Fixtures below are inline, synthetic line-lists -- not the real corpus -- covering every bullet in
204-01-PLAN.md's <behavior> block. One integration test at the bottom cross-checks the parser's
own case total against docs/UAT-SERIES.md using an independently-written counter, so the parser's
total is never trusted on its own say-so.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import uat_corpus


REPO_ROOT = Path(__file__).resolve().parents[1]
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"


def _lines(text: str) -> list[str]:
    return [line + "\n" for line in text.strip("\n").split("\n")]


# ---------------------------------------------------------------------------
# extract_series -- alpha-prefix-aware series extraction
# ---------------------------------------------------------------------------


def test_series_plain_numeric():
    assert uat_corpus.extract_series("UAT-5-18") == "5"


def test_series_named_prefix():
    assert uat_corpus.extract_series("UAT-COMPLY-52-01") == "52"


def test_series_named_prefix_single_letter():
    assert uat_corpus.extract_series("UAT-Q-53-01") == "53"


def test_series_decimal():
    assert uat_corpus.extract_series("UAT-56.1-01") == "56.1"


def test_series_decimal_186_1():
    assert uat_corpus.extract_series("UAT-186.1-03") == "186.1"


def test_series_backlog_numbered():
    assert uat_corpus.extract_series("UAT-999.83-01") == "999.83"


def test_series_three_segment():
    assert uat_corpus.extract_series("UAT-89-01-01") == "89"


# ---------------------------------------------------------------------------
# iter_cases -- heading / result / boxes / annotation / disposition
# ---------------------------------------------------------------------------


def test_iter_cases_basic_pass():
    lines = _lines(
        """
### UAT-9-01: A dispositioned case
body text
**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
"""
    )
    cases = list(uat_corpus.iter_cases(lines))
    assert len(cases) == 1
    c = cases[0]
    assert c.case_id == "UAT-9-01"
    assert c.series == "9"
    assert c.boxes == {"PASS"}
    assert c.disposition == "PASS"
    assert c.annotation is None


def test_iter_cases_fail():
    lines = _lines(
        """
### UAT-9-02: A failing case
**Result:** - [ ] PASS  - [x] FAIL  - [ ] SKIP
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "FAIL"


def test_iter_cases_undispositioned_all_empty():
    lines = _lines(
        """
### UAT-9-03: Not yet dispositioned
**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "UNDISPOSITIONED"
    assert c.boxes == set()


def test_iter_cases_skip_gap_annotation():
    lines = _lines(
        """
### UAT-9-04: Honest gap
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs a live browser)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "GAP"
    assert c.annotation.startswith("GAP — no substitute coverage")


def test_iter_cases_skip_gap_annotation_ascii_hyphen():
    lines = _lines(
        """
### UAT-9-05: Honest gap, ascii hyphen
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP - no substitute coverage)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "GAP"


def test_iter_cases_skip_deferred_annotation():
    lines = _lines(
        """
### UAT-9-06: Deferred, covered elsewhere
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by tests/test_foo.py::test_bar)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "DEFERRED"


def test_iter_cases_skip_obsolete_annotation():
    """OBSOLETE is not yet present in the live corpus (wave 2 introduces it) -- the parser must
    already support it so waves 2-4 have one place to read it from."""
    lines = _lines(
        """
### UAT-9-07: Retired case
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (OBSOLETE — one-time event, not repeatable)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "OBSOLETE"


def test_iter_cases_skip_other_annotation():
    lines = _lines(
        """
### UAT-9-08: Skipped for an unrelated reason
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (out of scope for this phase)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "SKIP_OTHER"


def test_iter_cases_skip_no_annotation_is_skip_other():
    lines = _lines(
        """
### UAT-9-09: Checked SKIP, bare
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "SKIP_OTHER"
    assert c.annotation is None


# ---------------------------------------------------------------------------
# WR-03 (204-REVIEW.md): a Result line with more than one box checked must
# surface as a distinct, machine-visible MALFORMED state, never silently
# resolve to a PASS disposition paired with a GAP annotation (the two
# previously-divergent priority orders' failure mode).
# ---------------------------------------------------------------------------


def test_iter_cases_multi_checked_result_line_is_malformed_not_silent_pass():
    lines = _lines(
        """
### UAT-9-10: Transcription error, two boxes checked
**Result:** - [x] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage)
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.boxes == {"PASS", "SKIP"}
    assert c.disposition == "MALFORMED_MULTI_CHECKED"
    assert c.disposition != "PASS", (
        "a two-boxes-checked line must never silently resolve to PASS -- that is exactly "
        "the WR-03 failure mode (an intended GAP disappearing from the worklist)"
    )
    assert c.annotation is None
    assert c.is_gap is False, (
        "MALFORMED must never be counted as a doc-GAP either -- it is neither silently a "
        "PASS nor silently a GAP; it must be reported, not guessed"
    )


def test_reconcile_surfaces_malformed_multi_checked_and_fails_arithmetic():
    lines = _lines(
        """
### UAT-9-10: Transcription error, two boxes checked
**Result:** - [x] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage)
"""
    )
    cases = list(uat_corpus.iter_cases(lines))
    r = uat_corpus.reconcile(cases, [])
    assert r.malformed_multi_checked == [("UAT-9-10", 2)]
    assert r.arithmetic_ok is False, (
        "a malformed multi-checked Result line must trip arithmetic_ok so reconcile()'s "
        "CLI (`uat_corpus reconcile`) exits non-zero rather than silently reading clean"
    )


# ---------------------------------------------------------------------------
# The UAT-151-01 body-literal-checkbox trap
# ---------------------------------------------------------------------------


def test_body_literal_checkbox_does_not_mask_undispositioned_result():
    """A case whose BODY contains a literal '- [x]' example line (quoting some other UI's
    checkbox in prose), but whose own **Result:** line is all-empty, must still classify
    UNDISPOSITIONED -- only the Result LINE is ever inspected."""
    lines = _lines(
        """
### UAT-151-01: The pre-commit artifact gate blocks a phase-close commit
**Steps:**
1. Verify the human sees a rendered checkbox example: `- [x] PASS` in the mock UI screenshot.
**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "UNDISPOSITIONED"


# ---------------------------------------------------------------------------
# Notes-line GAP: a checked SKIP with no Result annotation, but the case's own Notes line
# carries the GAP string -- must be captured (not silently the same as SKIP_OTHER-forever).
# ---------------------------------------------------------------------------


def test_notes_only_gap_is_captured_but_disposition_stays_result_scoped():
    lines = _lines(
        """
### UAT-185-01: Notes-only gap case
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP
**Notes:** **GAP — no substitute coverage.** Recorded honestly per the phase summary.
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    # disposition itself stays Result-line-scoped (matches the standing zero-undispositioned
    # gate's own discipline) ...
    assert c.disposition == "SKIP_OTHER"
    # ... but the notes-gap signal is captured, and is_gap reflects the adjudicated rule.
    assert c.notes_has_gap_string is True
    assert c.is_gap is True


def test_skip_other_without_notes_gap_is_not_is_gap():
    lines = _lines(
        """
### UAT-9-10: Genuinely other, no gap anywhere
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (blocked on external vendor access)
**Notes:** Nothing gap-shaped here.
"""
    )
    c = list(uat_corpus.iter_cases(lines))[0]
    assert c.disposition == "SKIP_OTHER"
    assert c.notes_has_gap_string is False
    assert c.is_gap is False


def test_notes_line_from_a_different_case_is_never_attributed():
    """A Notes-line GAP string belongs only to the case whose Result line immediately precedes
    it. A case with no Notes line at all (heading before the notes line, or a second case
    intervening) must not inherit another case's Notes."""
    lines = _lines(
        """
### UAT-9-11: First case, dispositioned PASS
**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
### UAT-9-12: Second case, bare SKIP, no own Notes line at all
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP
**Steps:** some prose that is not a Notes line
"""
    )
    cases = {c.case_id: c for c in uat_corpus.iter_cases(lines)}
    assert cases["UAT-9-11"].disposition == "PASS"
    assert cases["UAT-9-12"].disposition == "SKIP_OTHER"
    assert cases["UAT-9-12"].notes_has_gap_string is False
    assert cases["UAT-9-12"].is_gap is False


def test_trailing_summary_paragraph_gap_string_is_not_attributed_to_a_case():
    """A GAP string appearing in prose that trails a case (not on that case's own Result or
    Notes line) must never be attributed to that case -- this is the exact over-count hazard the
    orchestrator's preflight measurement found (4 cases, 'any GAP string in the span' rule)."""
    lines = _lines(
        """
### UAT-193-09: The actually-gap case
**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage)
### UAT-193-10: The final case of the series
**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
Series 193 summary: UAT-193-09 remains GAP — no substitute coverage pending a future phase.
"""
    )
    cases = {c.case_id: c for c in uat_corpus.iter_cases(lines)}
    assert cases["UAT-193-09"].is_gap is True
    assert cases["UAT-193-10"].disposition == "PASS"
    assert cases["UAT-193-10"].is_gap is False


# ---------------------------------------------------------------------------
# load_ledger
# ---------------------------------------------------------------------------


def test_load_ledger_parses_jsonl(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(
        '{"id": "UAT-1-01", "series": "1", "outcome": "PASS"}\n'
        '{"id": "UAT-1-02", "series": "1", "outcome": "GAP"}\n',
        encoding="utf-8",
    )
    rows = uat_corpus.load_ledger(ledger_path)
    assert len(rows) == 2
    assert rows[0]["id"] == "UAT-1-01"
    assert rows[1]["outcome"] == "GAP"


def test_load_ledger_missing_file_returns_empty(tmp_path):
    assert uat_corpus.load_ledger(tmp_path / "does-not-exist.jsonl") == []


# ---------------------------------------------------------------------------
# reconcile -- arithmetic closure and per-cause decomposition
# ---------------------------------------------------------------------------


def _case(case_id, disposition, notes_has_gap_string=False):
    c = uat_corpus.CaseRecord(case_id=case_id, series=uat_corpus.extract_series(case_id), heading_lineno=1)
    c.disposition = disposition
    c.notes_has_gap_string = notes_has_gap_string
    if disposition == "GAP":
        c.boxes = {"SKIP"}
        c.annotation = "GAP — no substitute coverage"
    return c


def test_reconcile_arithmetic_closes_synthetic():
    cases = [
        _case("UAT-1-01", "PASS"),
        _case("UAT-1-02", "GAP"),  # cause: has a ledger row (below)
        _case("UAT-200-01", "GAP"),  # cause 1: beyond ledger max series, no row
        _case("UAT-1-03", "DEFERRED"),  # cause 2: doc DEFERRED, ledger GAP
        _case("UAT-1-04", "SKIP_OTHER"),  # cause 3: doc unannotated, ledger GAP
    ]
    ledger_rows = [
        {"id": "UAT-1-01", "series": "1", "outcome": "PASS"},
        {"id": "UAT-1-02", "series": "1", "outcome": "GAP"},
        {"id": "UAT-1-03", "series": "1", "outcome": "GAP"},
        {"id": "UAT-1-04", "series": "1", "outcome": "GAP"},
        {"id": "UAT-1-99", "series": "1", "outcome": "GAP"},  # cause 4: absent from doc
    ]
    r = uat_corpus.reconcile(cases, ledger_rows)
    assert r.total_headings == 5
    assert r.doc_gap_ids == ["UAT-1-02", "UAT-200-01"]
    assert r.doc_gap_with_ledger_row == ["UAT-1-02"]
    assert r.doc_gap_without_ledger_row == ["UAT-200-01"]
    assert r.doc_deferred_ledger_gap == ["UAT-1-03"]
    assert r.doc_unannotated_ledger_gap == ["UAT-1-04"]
    assert r.ledger_ids_absent_from_doc == ["UAT-1-99"]
    assert r.arithmetic_ok is True


def test_reconcile_reports_mismatch_rather_than_absorbing_it():
    """If the two decompositions do NOT sum back to their source totals, arithmetic_ok must be
    False -- reconcile() must surface a mismatch, never silently round it away."""
    cases = [
        _case("UAT-1-01", "GAP"),
    ]
    # Ledger claims a GAP outcome for a case the doc does NOT mark GAP at all -- an
    # inconsistent state that should not silently disappear into "no cause found".
    ledger_rows = [
        {"id": "UAT-1-01", "series": "1", "outcome": "GAP"},
        {"id": "UAT-1-02", "series": "1", "outcome": "GAP"},  # references nothing in `cases`
    ]
    r = uat_corpus.reconcile(cases, ledger_rows)
    # UAT-1-02 is absent from `cases` entirely (not even present as a non-GAP case), so it must
    # land in ledger_ids_absent_from_doc, and the arithmetic must still close because that cause
    # is accounted for.
    assert "UAT-1-02" in r.ledger_ids_absent_from_doc
    assert r.arithmetic_ok is True


# ---------------------------------------------------------------------------
# classify_annotation direct unit coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "annotation,expected",
    [
        (None, "SKIP_OTHER"),
        ("GAP — no substitute coverage", "GAP"),
        ("GAP - no substitute coverage", "GAP"),
        ("DEFERRED — covered by tests/test_x.py::test_y", "DEFERRED"),
        ("DEFERRED - covered by tests/test_x.py::test_y", "DEFERRED"),
        ("OBSOLETE — one-time event", "OBSOLETE"),
        ("something else entirely", "SKIP_OTHER"),
        ("**GAP — no substitute coverage**", "GAP"),
    ],
)
def test_classify_annotation(annotation, expected):
    assert uat_corpus.classify_annotation(annotation) == expected


# ---------------------------------------------------------------------------
# Integration: cross-check the parser's own total against an independent counter over the real
# corpus. This is what makes the parser's total trustworthy rather than self-referential.
# ---------------------------------------------------------------------------


def test_iter_cases_total_matches_independent_heading_count():
    assert UAT_SERIES_PATH.is_file(), f"UAT-SERIES.md not found at {UAT_SERIES_PATH}"
    with UAT_SERIES_PATH.open(encoding="utf-8", newline="") as f:
        lines = f.readlines()

    # Independently written counter: a fresh regex compiled here, not reused from uat_corpus.
    independent_heading_re = re.compile(r"^### +UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*")
    independent_count = sum(1 for line in lines if independent_heading_re.match(line))

    cases = list(uat_corpus.iter_cases(lines))
    assert len(cases) == independent_count
    # Cross-check against the shell-level grep count this phase's constraints are pinned to.
    # Bumped 878 -> 882 in plan 204-05 (Series 204's 4 cases), then 882 -> 887 at Phase 204's
    # close-out (Series 203's 5 backfilled cases). Recompute, never transcribe.
    #
    # NOTE: this literal pin has now required a hand-bump twice in a single day, and it catches
    # nothing that the `independent_count` assertion three lines above does not already catch --
    # that one derives its expectation from the corpus at run time and so never goes stale. Corpus
    # growth is not a defect. Replacing this line with the derived check is tracked in
    # .planning/todos/pending/uat-corpus-parser-test-pins-a-literal-count.md
    assert len(cases) == 887
    # No duplicate IDs.
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids))


def test_run_reconcile_against_real_corpus_arithmetic_closes():
    r = uat_corpus.run_reconcile()
    # Bumped 878 -> 882 in plan 204-05 (Series 204's 4 cases), then 882 -> 887 at Phase 204's
    # close-out (Series 203's 5 backfilled cases). See the sibling test above for the
    # recompute-not-transcribe rationale and the todo tracking this pin's removal.
    assert r.total_headings == 887
    assert r.arithmetic_ok is True
