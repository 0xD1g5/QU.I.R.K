"""Phase 169 Plan 07 (UATREC-04): the standing zero-undispositioned gate.

WHAT THIS ENFORCES: this module fails the build the moment any case in
``docs/UAT-SERIES.md`` -- old or newly added -- carries an all-empty
``**Result:**`` block, i.e. ``**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP``
with no box checked. Plans 169-01 through 169-06 drained the corpus to zero
undispositioned cases; nothing stops that backlog from silently
re-accumulating as new UAT cases are written unless a check enforces the
invariant going forward. This is that check.

HOW TO FIX A FAILURE: ``test_zero_undispositioned_cases`` below reports the
exact ``UAT-<id>`` of every offending case and the 1-based line number of its
``**Result:**`` block. Open ``docs/UAT-SERIES.md`` at that line and check the
appropriate box (PASS/FAIL/SKIP). A checked SKIP box should carry a
``DEFERRED -- covered by <test-node>`` or ``GAP -- no substitute coverage``
annotation per the conventions in ``tests/test_uat_disposition_integrity.py``
and ``docs/UAT-SERIES.md``'s own header. Do NOT check a box just to satisfy
this gate -- an honest disposition (including GAP) is required, not a
rubber stamp.

WHY A PYTEST TEST, NOT A PRE-COMMIT HOOK OR DEDICATED CI STEP (D-01): the
``Linux Full Suite`` job (``.github/workflows/python-ci.yml:398-421``)
already runs ``pytest -q -m ""`` on every ``pull_request`` and every push to
``main``, with no ``continue-on-error``. Riding that job means this gate:

  1. Cannot be bypassed with ``git commit --no-verify`` (a pre-commit hook
     could be).
  2. Adds zero new CI wiring or job minutes (a dedicated step/job would add
     both).
  3. Fails identically whether run locally (``pytest -q``, since this test
     carries no ``@pytest.mark.slow`` of its own) or in CI.

WHY IT POLICES THE WHOLE DOCUMENT, NOT THE LEDGER (D-02): this gate parses
every ``### UAT-`` heading and its associated ``**Result:**`` line directly
from ``docs/UAT-SERIES.md``. It does NOT cross-reference
``docs/uat-disposition-ledger.jsonl``. A case added tomorrow is, by
definition, absent from the ledger; a ledger-scoped gate would let exactly
that failure mode through. Whole-document parsing is what makes the "gate
polices unrecorded cases" claim actually true.

WHY GAP IS A PASSING DISPOSITION, NOT A VIOLATION (D-03): this gate polices
*unrecorded* cases, not *uncovered* ones. As of Phase 169 Plan 05's
independent recount there are 57 honest, recorded ``GAP`` dispositions in
the document (a case with no substitute coverage, recorded as such). Those
cases have a checked SKIP box and are therefore dispositioned -- they must
PASS this gate. Building an allowlist of "still-GAP" case IDs would itself
be an undispositioned-case list in disguise, which is exactly what D-03
forbids.

INDEPENDENCE (matches the discipline of ``tests/test_uat_series_format.py``
and ``tests/test_uat_disposition_integrity.py``): every parsing helper below
(``HEADING_RE``, ``RESULT_LINE_RE``, ``find_undispositioned_cases``) is
written from scratch in this file. Nothing is imported from
``scripts/uat_series_normalize.py``, ``scripts/uat_disposition_apply.py``,
``tests/test_uat_series_format.py``, or ``tests/test_uat_disposition_integrity.py``.
A shared parsing bug in any of those would otherwise let this gate and the
document silently agree with each other while both are wrong about what
"undispositioned" means.

KNOWN TRAP (UAT-151-01, hit twice on this document): a naive regex scoped to
the whole case *body* (heading through next heading) false-positives on
cases whose test steps contain a literal ``- [x]`` markdown example as prose
-- e.g. a case instructing a human tester to check a box in some *other*
UI, quoted verbatim in the case's own procedure text. That literal string
inside the body is NOT the case's own disposition. This gate's
``find_undispositioned_cases`` is therefore scoped to the ``**Result:**``
LINE ONLY -- it never scans case body text -- and
``test_body_literal_checkbox_does_not_mask_undispositioned_result`` below is
a regression test proving a case with a checked-looking ``- [x]`` string in
its body, but an EMPTY ``**Result:**`` line, is still correctly flagged as
undispositioned.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Parsing helpers -- independent of scripts/ and the two sibling guard
# modules (tests/test_uat_series_format.py, tests/test_uat_disposition_integrity.py).
# ---------------------------------------------------------------------------

UAT_SERIES_PATH = Path(__file__).resolve().parents[1] / "docs" / "UAT-SERIES.md"
CI_WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "python-ci.yml"
PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Case-ID grammar matching the sibling guards' CASE_ID_PATTERN: digits, dots,
# hyphens, letters -- covers UAT-4-01, UAT-89-02-01, UAT-COMPLY-52-01, etc.
CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"

HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r"):?")
RESULT_RE = re.compile(r"^\*\*Result:\*\* *(.*)$")

# The exact shape of an undispositioned case's Result line: all three boxes
# empty, no annotation. Any variant with at least one checked box -- PASS,
# FAIL, or SKIP (including a checked SKIP carrying a GAP or DEFERRED
# annotation) -- counts as dispositioned.
ALL_EMPTY_RESULT_RE = re.compile(
    r"^- \[ \] PASS  - \[ \] FAIL  - \[ \] SKIP$"
)


def iter_case_headings(lines):
    """Yield (1-based lineno, case_id) for every ``^### UAT-...`` heading."""
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            yield i, m.group(1)


def find_undispositioned_cases(lines):
    """Return [(case_id, result_lineno)] for every case whose associated
    ``**Result:**`` line has all three boxes empty (undispositioned).

    Walks the document once, tracking the most recently seen case heading's
    ID (matching the sibling guards' walk pattern). Only the ``**Result:**``
    LINE itself is inspected for checkbox state -- never the case body --
    which is what makes this immune to the UAT-151-01 body-literal-checkbox
    trap.
    """
    undispositioned: list[tuple[str, int]] = []
    current_case_id: str | None = None
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            current_case_id = m.group(1)
            continue
        m = RESULT_RE.match(line)
        if m:
            rest = m.group(1)
            if ALL_EMPTY_RESULT_RE.match(rest):
                undispositioned.append((current_case_id, i))
    return undispositioned


def _read_lines(path: Path) -> list[str]:
    """Match the sibling guards' read convention exactly -- newline="" so a
    stray Unicode line separator can't silently misalign line counts across
    parsers."""
    with path.open(encoding="utf-8", newline="") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# Fixture: read the document once (session scope)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def uat_series_lines() -> list[str]:
    assert UAT_SERIES_PATH.is_file(), f"UAT-SERIES.md not found at {UAT_SERIES_PATH}"
    return _read_lines(UAT_SERIES_PATH)


# ---------------------------------------------------------------------------
# Task 1: the zero-undispositioned gate
# ---------------------------------------------------------------------------


def test_zero_undispositioned_cases(uat_series_lines):
    """The gate: fails the build if ANY case in docs/UAT-SERIES.md has an
    all-empty **Result:** block, naming every offending case ID and line
    number so a contributor who adds one bad case is told exactly which one."""
    undispositioned = find_undispositioned_cases(uat_series_lines)
    if undispositioned:
        detail = "\n".join(
            f"  line {lineno}: {case_id}" for case_id, lineno in undispositioned
        )
        pytest.fail(
            f"{len(undispositioned)} undispositioned UAT case(s) found in "
            f"docs/UAT-SERIES.md (all three Result boxes empty):\n{detail}\n\n"
            "Fix: open docs/UAT-SERIES.md at the line(s) above and check the "
            "appropriate box (PASS/FAIL/SKIP). A checked SKIP should carry a "
            "DEFERRED or GAP annotation -- see tests/test_uat_disposition_integrity.py."
        )


# ---------------------------------------------------------------------------
# Negative controls -- exercise find_undispositioned_cases directly on
# synthetic input, NOT the real file, proving the gate detects exactly what
# it claims and is non-vacuous (it can actually fail).
# ---------------------------------------------------------------------------


def test_negative_control_all_empty_result_is_flagged():
    synthetic = [
        "### UAT-9-01: A case with no disposition\n",
        "body text\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    undispositioned = find_undispositioned_cases(synthetic)
    assert undispositioned == [("UAT-9-01", 3)]


def test_negative_control_checked_pass_is_not_flagged():
    synthetic = [
        "### UAT-9-01: A dispositioned case\n",
        "body text\n",
        "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    assert find_undispositioned_cases(synthetic) == []


def test_negative_control_checked_skip_with_gap_annotation_is_not_flagged():
    """D-03: a checked SKIP box with a GAP (or DEFERRED) annotation is a
    valid, passing disposition -- the gate polices unrecorded cases, not
    uncovered ones."""
    synthetic = [
        "### UAT-9-01: A GAP case\n",
        "body text\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(GAP — no substitute coverage; needs a new detector)\n",
    ]
    assert find_undispositioned_cases(synthetic) == []


def test_negative_control_checked_skip_with_deferred_annotation_is_not_flagged():
    synthetic = [
        "### UAT-9-01: A DEFERRED case\n",
        "body text\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_foo.py::test_bar)\n",
    ]
    assert find_undispositioned_cases(synthetic) == []


def test_negative_control_mixed_document_flags_only_the_undispositioned_one():
    """Non-vacuity proof: a document with several dispositioned cases and
    exactly one undispositioned case flags only that one case, by ID."""
    synthetic = [
        "### UAT-1-01: Dispositioned via PASS\n",
        "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n",
        "### UAT-2-01: Dispositioned via GAP\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage)\n",
        "### UAT-3-01: The undispositioned one\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP\n",
        "### UAT-4-01: Dispositioned via FAIL\n",
        "**Result:** - [ ] PASS  - [x] FAIL (broke on 2026-08-27)  - [ ] SKIP\n",
    ]
    undispositioned = find_undispositioned_cases(synthetic)
    assert undispositioned == [("UAT-3-01", 6)]


def test_negative_control_regression_body_literal_checkbox_does_not_mask_undispositioned_result():
    """UAT-151-01 trap regression: a case whose BODY contains a literal
    ``- [x]`` markdown example (e.g. quoted procedure text instructing a
    human tester to check some *other* UI's checkbox) must NOT be mistaken
    for a dispositioned Result line. This gate scans only the **Result:**
    line itself -- never the body -- so it must still flag this case as
    undispositioned despite the body's checked-looking text."""
    synthetic = [
        "### UAT-151-01: A case whose steps quote a checked box\n",
        "**Steps:** In the target UI, verify the box now reads `- [x] Enabled`\n",
        "and confirm the toggle persisted after reload.\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    undispositioned = find_undispositioned_cases(synthetic)
    assert undispositioned == [("UAT-151-01", 4)]


# ---------------------------------------------------------------------------
# Non-vacuity proof against the REAL document: confirm the gate currently
# passes over a non-empty, real case set (not because it found nothing to
# check at all).
# ---------------------------------------------------------------------------


def test_gate_evaluates_a_non_trivial_number_of_real_cases(uat_series_lines):
    """Guards against a silently-broken parser that matches zero headings
    and therefore trivially 'passes' the gate above without checking
    anything. docs/UAT-SERIES.md has 666 ### UAT- headings as of Phase 169
    Plan 05's independent recount; this asserts a large, non-hardcoded-to-666
    floor so the test doesn't need editing every time a case is added."""
    heading_count = sum(1 for _ in iter_case_headings(uat_series_lines))
    assert heading_count > 500, (
        f"Only {heading_count} ### UAT- headings parsed from docs/UAT-SERIES.md -- "
        "expected several hundred. The heading parser may be broken, which would "
        "make test_zero_undispositioned_cases vacuously pass."
    )

