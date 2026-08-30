"""Phase 176 Plan 01 (LABRUN-02, D-01): shape + behaviour regression guard for
the UAT-1-02 pass-condition in ``uat_runner.py``.

Why this exists: ``uat_runner.py:154`` read (from commit ``bebb1d8fc``,
2026-04-16, until this phase's fix):

    status = 'PASS' if code == 0 and ('4.2.0' in ver or 'quirk' in ver.lower()) else 'FAIL'

``'4.2.0'`` was a stale, hardcoded literal from the version shipping the day
the line was written, and ``'quirk' in ver.lower()`` never matches because
the live banner is ``QU.I.R.K. v5.15.0`` -- lowercased that is
``qu.i.r.k. v5.15.0``, and the dots break the contiguous substring
``quirk``. The condition was unsatisfiable by any current-era product
output, forcing UAT-1-02 to FAIL on every sweep since April regardless of
what shipped. This is a HARNESS defect, not a product bug and not version
drift (see 176-ASSUMPTIONS.md Part A and 176-CONTEXT.md D-01).

This module is the ONLY standing guard against that literal-rot pattern
returning. It pins the SHAPE of the corrected condition -- "no hardcoded
version literal, no .lower() substring trap, delegates to a regex search
for the documented banner format" -- rather than merely asserting today's
behaviour, because a test that only asserted "passes for v5.15.0" would rot
identically at the next version bump.

FALSIFIABILITY (D-01's required record): each test below is stated so that
a specific regression to ``uat_runner.py`` turns it red:

  - test_no_version_literal_in_condition: turns RED if a future edit
    reintroduces a quoted concrete version number (e.g. ``'4.2.0'`` or
    ``'5.15.0'``) inside the UAT-1-02 status line.
  - test_no_lower_call_in_condition: turns RED if a future edit
    reintroduces a ``.lower()`` call in that line (the dotted-acronym
    substring trap that broke the original condition).
  - test_condition_uses_regex_search_not_in: turns RED if the condition
    stops calling ``re.search`` and reverts to Python ``in``-substring
    matching, or stops checking ``code == 0``.
  - test_pattern_matches_live_version_banner / test_pattern_rejects_versionless_output:
    turn RED if the extracted regex pattern is loosened to match anything
    (e.g. ``.*``) or tightened past the shipped ``QU.I.R.K. vMAJOR.MINOR.PATCH``
    banner format.
  - test_historical_defective_condition_text_is_absent: turns RED if the
    exact historical defective text
    ``('4.2.0' in ver or 'quirk' in ver.lower())`` ever reappears anywhere
    in ``uat_runner.py``.

DEMONSTRATED (not merely asserted) falsification: the shape tests in this
module were run, at authoring time, against a scratch copy of
``uat_runner.py`` carrying the historical defective line, and observed to
FAIL. The transcript of that run is recorded verbatim in
``176-01-SUMMARY.md``.

``uat_runner.py`` calls ``argparse.ArgumentParser().parse_args()`` at MODULE
scope (see its lines 30-33), so importing it under pytest would consume
pytest's own argv and call ``sys.exit()``. Every assertion in this module is
therefore made against the file's SOURCE TEXT, resolved relative to this
test file (not the CWD), plus one live subprocess leg (Test 4) that shells
out to the built ``quirk`` CLI entry point directly -- it does not import
``uat_runner``.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UAT_RUNNER_PATH = REPO_ROOT / "uat_runner.py"
QUIRK_BIN = REPO_ROOT / ".venv" / "bin" / "quirk"

# The exact historical defective text (verbatim, pre-176-01-fix).
HISTORICAL_DEFECTIVE_TEXT = "('4.2.0' in ver or 'quirk' in ver.lower())"

# Detects a quoted literal holding a concrete N.N.N version number, e.g.
# '4.2.0' or "5.15.0". Deliberately does NOT match \d+\.\d+\.\d+ inside a
# regex pattern string (no literal digit characters there) -- the corrected
# condition's re.search(r'...\d+\.\d+\.\d+', ver) pattern must NOT trip this
# detector, while the historical '4.2.0' literal MUST.
_VERSION_LITERAL_RE = re.compile(r"""['"][0-9]+\.[0-9]+\.[0-9]+['"]""")


def _read_runner_source() -> str:
    return UAT_RUNNER_PATH.read_text(encoding="utf-8")


def _extract_status_line(source: str) -> str:
    """Locate the UAT-1-02 pass-condition line by anchoring on the
    ``rlog('UAT-1-02'`` call and walking backwards to the nearest preceding
    line whose stripped form starts with ``status =``.

    Fails loudly (naming the missing anchor) rather than silently skipping,
    so a future refactor of the block surfaces as a red test.
    """
    lines = source.splitlines()
    rlog_idx = None
    for i, line in enumerate(lines):
        if "rlog('UAT-1-02'" in line:
            rlog_idx = i
            break
    if rlog_idx is None:
        pytest.fail(
            "Missing anchor: no line containing rlog('UAT-1-02' found in "
            "uat_runner.py -- the UAT-1-02 block may have been renamed or "
            "removed. Update this test's anchor to match."
        )

    for j in range(rlog_idx, -1, -1):
        if lines[j].strip().startswith("status ="):
            return lines[j]

    pytest.fail(
        "Missing anchor: no preceding line starting with 'status =' found "
        "before the rlog('UAT-1-02' call -- the pass-condition assignment "
        "may have been restructured. Update this test's anchor to match."
    )


@pytest.fixture(scope="module")
def status_line() -> str:
    return _extract_status_line(_read_runner_source())


def test_no_version_literal_in_condition(status_line: str) -> None:
    """Test 1 (shape, primary). FALSIFIES if a concrete quoted version
    number (e.g. '4.2.0') is reintroduced into the pass-condition -- that is
    exactly the defect pattern that rotted this check for four months.
    """
    match = _VERSION_LITERAL_RE.search(status_line)
    assert match is None, (
        f"UAT-1-02 pass-condition contains a hardcoded version literal "
        f"{match.group(0)!r} -- this is the exact rot pattern fixed in "
        f"176-01 (D-01). Extracted line: {status_line!r}"
    )


def test_no_lower_call_in_condition(status_line: str) -> None:
    """Test 2 (shape). FALSIFIES if '.lower()' reappears -- the
    dotted-acronym substring trap ('quirk' never matches
    'qu.i.r.k.'.lower()) that broke the original condition.
    """
    assert ".lower()" not in status_line, (
        f"UAT-1-02 pass-condition reintroduces a .lower() substring check, "
        f"the exact trap that made 'quirk' in 'qu.i.r.k. v5.15.0'.lower() "
        f"unsatisfiable. Extracted line: {status_line!r}"
    )


def test_condition_uses_regex_search_not_in(status_line: str) -> None:
    """Test 3 (shape). FALSIFIES if the condition stops requiring
    code == 0, or stops delegating the text check to re.search in favor of
    Python 'in'-substring matching.
    """
    assert "code == 0" in status_line, (
        f"UAT-1-02 pass-condition no longer checks code == 0: {status_line!r}"
    )
    assert re.search(r"re\.search\(", status_line) is not None, (
        f"UAT-1-02 pass-condition no longer delegates to re.search(...) -- "
        f"it may have regressed to substring 'in' matching: {status_line!r}"
    )


def _extract_pattern_literal(status_line: str) -> str:
    """Pull the raw regex pattern string out of the re.search(r'...', ver)
    call in the extracted status line.
    """
    m = re.search(r"re\.search\(\s*r?['\"](.+?)['\"]\s*,\s*ver\s*\)", status_line)
    assert m is not None, (
        f"Could not extract a re.search(<pattern>, ver) pattern literal from "
        f"the UAT-1-02 status line: {status_line!r}"
    )
    return m.group(1)


def test_pattern_matches_live_version_banner(status_line: str) -> None:
    """Test 4 (behaviour). FALSIFIES if the pattern is tightened past the
    shipped 'QU.I.R.K. vMAJOR.MINOR.PATCH' banner format -- run against the
    real built CLI entry point (not an import of uat_runner.py, which is
    unimportable under pytest -- see module docstring).
    """
    if not QUIRK_BIN.exists():
        pytest.skip(
            "quirk entry point not present at .venv/bin/quirk -- environment "
            "has no built venv. Registered per skip-registry conventions."
        )
    pattern = _extract_pattern_literal(status_line)
    result = subprocess.run(
        [str(QUIRK_BIN), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"quirk --version exited {result.returncode}, expected 0"
    )
    stdout_stripped = (result.stdout + result.stderr).strip()
    assert re.search(pattern, stdout_stripped) is not None, (
        f"Extracted UAT-1-02 pattern {pattern!r} did not match live "
        f"'quirk --version' output {stdout_stripped!r}"
    )


def test_pattern_rejects_versionless_output(status_line: str) -> None:
    """Test 4b (behaviour, negative leg). FALSIFIES if the pattern is
    loosened to match anything (e.g. '.*') -- it must NOT match a
    versionless control string.
    """
    pattern = _extract_pattern_literal(status_line)
    control = "no version printed"
    assert re.search(pattern, control) is None, (
        f"Extracted UAT-1-02 pattern {pattern!r} incorrectly matched a "
        f"versionless control string {control!r} -- the pattern has been "
        f"loosened past the documented banner format."
    )


def test_historical_defective_condition_text_is_absent() -> None:
    """Test 5 (regression corpus). FALSIFIES if the exact historical
    defective condition text ('4.2.0' in ver or 'quirk' in ver.lower())
    reappears anywhere in uat_runner.py.
    """
    source = _read_runner_source()
    assert HISTORICAL_DEFECTIVE_TEXT not in source, (
        "The historical defective UAT-1-02 condition text has reappeared "
        "in uat_runner.py -- this is the exact regression 176-01 fixed."
    )
