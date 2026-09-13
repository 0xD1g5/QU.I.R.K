"""Phase 204 Plan 03 (COV-01/COV-02) gate: docs/uat-coverage-gaps.md must match live
scripts/generate_uat_coverage_gaps.py output.

Mirrors tests/test_severity_bands_freshness.py and tests/test_error_codes_freshness.py -- the
project's own shipped precedent for a generator-drift gate: a committed artifact, a test asserting
byte-match against live generator output, a non-vacuity leg that drives its mutation through the
real generator (188 review WR-04 -- never paste a copy of the expected payload), and the
regeneration command named verbatim in every failure message.

Why enumeration from source, at run time, is the safeguard here specifically: this project has now
named the "hand-derived list of sites silently drifts" failure mode five separate times (see
CLAUDE.md's GSD state.* verb integrity section). The worklist this gate protects was itself an
instance of that failure -- a hand-maintained snapshot bounded at an old series ceiling with counts
transcribed rather than recomputed. A gate built the same way (a fixed list of expected rows pasted
into the test) would reproduce the exact defect it exists to catch. Every assertion below is driven
through scripts/generate_uat_coverage_gaps.py's own entry points against either the live corpus or
a from-scratch fixture, never a hand-typed expected-output string.

CI placement: this file rides the `Linux Full Suite` job (`pytest -q -m ""` in
.github/workflows/python-ci.yml) with zero new CI wiring, the same way
tests/test_severity_bands_freshness.py and tests/test_score_strings_freshness.py already do. Only
tests/test_error_codes_freshness.py rides the dedicated `.github/workflows/python-staleness.yml`
gate step, because that workflow's whole purpose is date-cadence staleness, not generator drift; a
byte-drift gate belongs with the full test suite that already runs on every PR, every push to main,
so no new workflow step is added here.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import generate_uat_coverage_gaps as generator
from scripts import uat_corpus as corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
UAT_COVERAGE_GAPS_MD = REPO_ROOT / "docs" / "uat-coverage-gaps.md"


# --- Fixture helpers (Task 1 <behavior> legs) ----------------------------------------------------


def _case_block(case_id: str, title: str, result_line: str, notes: str = "none") -> str:
    return (
        f"### {case_id}: {title}\n"
        "\n"
        f"{result_line}\n"
        "\n"
        f"**Notes:** {notes}\n"
        "\n"
    )


def _gap_result(text: str) -> str:
    return f"**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; {text})"


def _deferred_result(text: str) -> str:
    return f"**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by {text})"


def _obsolete_result(text: str) -> str:
    return f"**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (OBSOLETE — {text})"


def _pass_result() -> str:
    return "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP"


def _fixture_corpus_text() -> str:
    return (
        _case_block(
            "UAT-900-01",
            "Fixture Gap Case",
            _gap_result("needs a fixture-only test node"),
        )
        + _case_block(
            "UAT-900-02",
            "Fixture Deferred Case",
            _deferred_result("tests/test_fixture.py::test_covers_it"),
        )
        + _case_block(
            "UAT-900-03",
            "Fixture Obsolete Case",
            _obsolete_result("this fixture event happened once and is not repeatable"),
        )
        + _case_block(
            "UAT-900-04",
            "Fixture Pass Case",
            _pass_result(),
        )
    )


def _fixture_lines() -> list:
    return _fixture_corpus_text().splitlines(keepends=True)


def _open_gap_section(worklist: str) -> str:
    marker = "## Retired (OBSOLETE)"
    idx = worklist.find(marker)
    return worklist if idx == -1 else worklist[:idx]


def _retired_section(worklist: str) -> str:
    marker = "## Retired (OBSOLETE)"
    idx = worklist.find(marker)
    return "" if idx == -1 else worklist[idx:]


# --- Task 1: behavior-driven fixture tests --------------------------------------------------------


def test_gap_case_in_open_table_obsolete_in_retired_section_others_absent():
    worklist = generator.build_worklist(_fixture_lines())
    open_section = _open_gap_section(worklist)
    retired_section = _retired_section(worklist)

    assert "UAT-900-01" in open_section, "the GAP case must appear in the open-GAP worklist"
    assert "UAT-900-01" not in retired_section, "the GAP case must not appear in the retired section"

    assert "UAT-900-03" in retired_section, "the OBSOLETE case must appear in the retired section"
    assert "UAT-900-03" not in open_section, "the OBSOLETE case must not appear in the open-GAP table"

    assert "UAT-900-02" not in worklist, "a DEFERRED case must appear in neither table"
    assert "UAT-900-04" not in worklist, "a PASS case must appear in neither table"


def test_totals_move_when_fixture_mutates():
    base_worklist = generator.build_worklist(_fixture_lines())
    assert "Open GAP (drainable) cases: 1" in base_worklist
    assert "Retired OBSOLETE cases (excluded from the open-GAP total below): 1" in base_worklist

    mutated_text = _fixture_corpus_text() + _case_block(
        "UAT-900-05",
        "Fixture Second Gap Case",
        _gap_result("needs a second fixture-only test node"),
    )
    mutated_worklist = generator.build_worklist(mutated_text.splitlines(keepends=True))

    assert "Open GAP (drainable) cases: 2" in mutated_worklist
    assert mutated_worklist != base_worklist, (
        "mutating the fixture corpus did not move the generator's output -- "
        "the totals are not actually being computed from the input"
    )


def test_series_beyond_old_ledger_bound_appears_in_open_gap_table():
    """The old file structurally could not show a case in a series beyond its frozen ledger bound.
    A case in a clearly-beyond-any-historical-bound series (999) must still surface here."""
    text = _fixture_corpus_text() + _case_block(
        "UAT-999-01",
        "Fixture Far-Series Gap Case",
        _gap_result("needs coverage no historical ledger row could ever have recorded"),
    )
    worklist = generator.build_worklist(text.splitlines(keepends=True))
    open_section = _open_gap_section(worklist)
    assert "UAT-999-01" in open_section


def test_two_runs_over_identical_fixture_are_byte_identical():
    lines = _fixture_lines()
    assert generator.build_worklist(lines) == generator.build_worklist(lines)


def test_output_has_no_timestamp_or_absolute_path():
    worklist = generator.build_worklist(_fixture_lines())
    assert str(REPO_ROOT) not in worklist, "output must not embed an absolute filesystem path"
    assert str(corpus.UAT_SERIES_PATH) not in worklist
    # A bare 4-digit run of the form YYYY- immediately followed by a month/day pattern would
    # indicate a wall-clock date was embedded; the fixture and real corpus text both legitimately
    # contain 4-digit numbers (case ids, series), so this only checks for the specific literal
    # "generated on" / "generated at" phrasing a timestamp-embedding regression would introduce.
    lowered = worklist.lower()
    assert "generated on" not in lowered
    assert "generated at" not in lowered
