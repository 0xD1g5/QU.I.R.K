"""Phase 167 Plan 02 (UATREC-01, UATREC-02): mechanical guard locking the four
normalized-format invariants of ``docs/UAT-SERIES.md``.

Why this exists: Phase 167 normalized the document to one canonical result-line
format and eliminated duplicate/headingless case declarations (see
``scripts/uat_series_normalize.py`` and 167-01-SUMMARY.md). Without an automated
gate, that normalization is a one-time cleanup that silently decays as Phases
168/169 add and disposition cases. This module locks four invariants:

  1. Every ``**Result:**`` line matches exactly one canonical grammar.
  2. The count of ``### UAT-`` case headings equals the count of ``**Result:**``
     blocks (parity by construction, not by hand-counting).
  3. Every case ID extracted from a ``### UAT-`` heading is unique.
  4. No ``**ID:** UAT-<id>`` declaration exists without an enclosing
     ``### UAT-<same id>`` heading (a "headingless" declaration).
  5. (Structural corollary of #2) zero ``#### UAT-`` headings exist, since a
     case declared one level too deep silently breaks the parity that #2
     depends on.

Deliberate scope boundary (D-07 / T-167-05): this module asserts NOTHING about
whether a case's PASS/FAIL/SKIP boxes are checked. Recording actual
dispositions for undispositioned cases is UATREC-03, drained in Phases
168/169. Pre-empting that here would violate the phase boundary locked in
167-CONTEXT.md.

The parsing helpers below are written independently of
``scripts/uat_series_normalize.py`` and do NOT import from it -- a shared
parsing bug in that script would otherwise let the normalizer and this test
agree with each other while both are wrong about the actual document shape.
That independence is also why the case-ID regex below is NOT
``UAT-[0-9]*-[0-9]*``: that truncating shape collapses three-segment IDs
(``UAT-89-02-01`` and ``UAT-89-02-02`` both reduce to a phantom ``UAT-89-02``)
and is the exact regex that manufactured the incorrect "5 duplicate IDs"
figure corrected by this phase (see 167-CONTEXT.md "Duplicate Resolution").
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Parsing helpers (independent of scripts/uat_series_normalize.py)
# ---------------------------------------------------------------------------

UAT_SERIES_PATH = Path(__file__).resolve().parents[1] / "docs" / "UAT-SERIES.md"

# Case-ID grammar: digits, dots, hyphens, letters -- covers UAT-4-01,
# UAT-56.1-01, UAT-89-02-01, UAT-COMPLY-52-01, UAT-Q-53-01, UAT-DEBT-52-04,
# UAT-999.83-01. Deliberately NOT `UAT-[0-9]*-[0-9]*`: that form truncates
# three-segment IDs and manufactures phantom duplicate collisions (see module
# docstring and 167-CONTEXT.md).
CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"

HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r"):?")
SUBHEADING_RE = re.compile(r"^#### *(" + CASE_ID_PATTERN + r"):?")
RESULT_LINE_RE = re.compile(r"^\*\*Result:\*\*")
ID_DECL_RE = re.compile(r"^\*\*ID:\*\* *(" + CASE_ID_PATTERN + r")")

# Canonical **Result:** grammar (interfaces block, 167-02-PLAN.md):
# literal "**Result:** ", then three groups separated by exactly two spaces,
# each "- [ ] LABEL" or "- [x] LABEL" in PASS/FAIL/SKIP order, each optionally
# followed by a single " (annotation)" suffix. Anchored start and end of line.
CANONICAL_RESULT_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[[ x]\] PASS(?: \([^)]*\))?  "
    r"- \[[ x]\] FAIL(?: \([^)]*\))?  "
    r"- \[[ x]\] SKIP(?: \([^)]*\))?$"
)


def iter_result_lines(lines):
    """Yield (1-based lineno, line) for every line matching ``^\\*\\*Result:\\*\\*``."""
    for i, line in enumerate(lines, start=1):
        if RESULT_LINE_RE.match(line):
            yield i, line.rstrip("\n")


def iter_case_headings(lines):
    """Yield (1-based lineno, case_id) for every ``^### UAT-...`` heading."""
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            yield i, m.group(1)


def iter_subheadings(lines):
    """Yield (1-based lineno, case_id) for every ``^#### UAT-...`` heading."""
    for i, line in enumerate(lines, start=1):
        m = SUBHEADING_RE.match(line)
        if m:
            yield i, m.group(1)


def iter_id_declarations(lines):
    """Yield (1-based lineno, case_id) for every ``^**ID:** UAT-...`` line."""
    for i, line in enumerate(lines, start=1):
        m = ID_DECL_RE.match(line)
        if m:
            yield i, m.group(1)


def find_format_violations(lines):
    """Return [(lineno, line)] for **Result:** lines that are not canonical."""
    violations = []
    for lineno, line in iter_result_lines(lines):
        if not CANONICAL_RESULT_RE.match(line):
            violations.append((lineno, line))
    return violations


def find_duplicate_ids(lines):
    """Return {case_id: [linenos]} for every case ID that appears >1 time
    among ``### UAT-`` headings."""
    seen: dict[str, list[int]] = {}
    for lineno, case_id in iter_case_headings(lines):
        seen.setdefault(case_id, []).append(lineno)
    return {cid: linenos for cid, linenos in seen.items() if len(linenos) > 1}


def find_orphan_ids(lines):
    """Return [(lineno, case_id)] for every ``**ID:**`` declaration that is not
    preceded -- with no intervening ``### UAT-`` heading of a *different* ID --
    by a ``### UAT-<same id>`` heading.

    Walks the document once, tracking the most recently seen case heading's
    ID. An ``**ID:**`` line is an orphan if the current heading context does
    not match its own ID (including the case of no heading context at all).
    """
    orphans: list[tuple[int, str]] = []
    current_heading_id: str | None = None
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            current_heading_id = m.group(1)
            continue
        m = ID_DECL_RE.match(line)
        if m:
            declared_id = m.group(1)
            if declared_id != current_heading_id:
                orphans.append((i, declared_id))
    return orphans


def _read_lines(path: Path) -> list[str]:
    """Match scripts/uat_series_normalize.py::_read exactly.

    str.splitlines() also breaks on \x0b, \x0c, \x1c-\x1e, \x85, U+2028 and
    U+2029, which readlines(newline="") does not. A stray Unicode line
    separator pasted into a title or annotation would give the two parsers
    different line counts and silently misalign parity.
    """
    with path.open(encoding="utf-8", newline="") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# Fixture: read the document once (session scope -- 19.5k+ lines, five tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def uat_series_lines() -> list[str]:
    assert UAT_SERIES_PATH.is_file(), f"UAT-SERIES.md not found at {UAT_SERIES_PATH}"
    return _read_lines(UAT_SERIES_PATH)


# ---------------------------------------------------------------------------
# Test 1: single canonical **Result:** format
# ---------------------------------------------------------------------------


def test_all_result_lines_canonical(uat_series_lines):
    violations = find_format_violations(uat_series_lines)
    if violations:
        shown = violations[:20]
        detail = "\n".join(f"  line {lineno}: {line!r}" for lineno, line in shown)
        more = f"\n  ... and {len(violations) - 20} more" if len(violations) > 20 else ""
        pytest.fail(
            f"{len(violations)} non-canonical **Result:** line(s) found:\n{detail}{more}"
        )


# ---------------------------------------------------------------------------
# Test 2: heading count == result-block count (equality of two computed
# values -- never a hardcoded constant, so Phase 168/169 additions don't
# require editing this test)
# ---------------------------------------------------------------------------


def test_heading_count_equals_result_block_count(uat_series_lines):
    heading_count = sum(1 for _ in iter_case_headings(uat_series_lines))
    result_count = sum(1 for _ in iter_result_lines(uat_series_lines))
    assert heading_count == result_count, (
        f"### UAT- heading count ({heading_count}) != **Result:** block count "
        f"({result_count}); difference = {heading_count - result_count}"
    )


# ---------------------------------------------------------------------------
# Test 3: case ID uniqueness
# ---------------------------------------------------------------------------


def test_no_duplicate_case_ids(uat_series_lines):
    duplicates = find_duplicate_ids(uat_series_lines)
    if duplicates:
        detail = "\n".join(
            f"  {cid}: lines {linenos}" for cid, linenos in sorted(duplicates.items())
        )
        pytest.fail(f"{len(duplicates)} duplicate case ID(s) found:\n{detail}")


# ---------------------------------------------------------------------------
# Test 4: no headingless **ID:** declarations
# ---------------------------------------------------------------------------


def test_no_headingless_id_declarations(uat_series_lines):
    orphans = find_orphan_ids(uat_series_lines)
    if orphans:
        detail = "\n".join(f"  line {lineno}: {cid}" for lineno, cid in orphans)
        pytest.fail(f"{len(orphans)} headingless **ID:** declaration(s) found:\n{detail}")


# ---------------------------------------------------------------------------
# Test 5: no mis-levelled (#### UAT-) case headings
# ---------------------------------------------------------------------------


def test_no_mislevelled_case_headings(uat_series_lines):
    subheadings = list(iter_subheadings(uat_series_lines))
    if subheadings:
        detail = "\n".join(f"  line {lineno}: {cid}" for lineno, cid in subheadings)
        pytest.fail(f"{len(subheadings)} #### UAT- heading(s) found (must be ###):\n{detail}")


# ---------------------------------------------------------------------------
# Negative controls -- exercise the helpers directly on synthetic input, NOT
# against the real file, proving the checks actually detect what they claim.
# ---------------------------------------------------------------------------


def test_negative_control_bare_result_line_is_a_violation():
    synthetic = ["**Result:** PASS\n"]
    violations = find_format_violations(synthetic)
    assert violations == [(1, "**Result:** PASS")]


def test_negative_control_duplicate_heading_is_detected():
    synthetic = [
        "### UAT-9-01: First occurrence\n",
        "body text\n",
        "### UAT-9-01: Second occurrence\n",
    ]
    duplicates = find_duplicate_ids(synthetic)
    assert duplicates == {"UAT-9-01": [1, 3]}


def test_negative_control_canonical_line_passes():
    synthetic = ["**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP\n"]
    assert find_format_violations(synthetic) == []


def test_negative_control_headingless_id_is_orphan():
    synthetic = [
        "### UAT-1-01: Some case\n",
        "**ID:** UAT-1-01\n",
        "body\n",
        "**ID:** UAT-2-01\n",  # no enclosing ### UAT-2-01 heading
    ]
    orphans = find_orphan_ids(synthetic)
    assert orphans == [(4, "UAT-2-01")]
