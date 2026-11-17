"""Phase 238 D-10/D-36: the dashboard's coverage vocabulary mirrors the Python source.

``src/dashboard/src/lib/coverage-reason.ts`` hand-copies
``COVERAGE_SKIP_ADVISORY_CATEGORIES`` from ``quirk/scanner/target_outcome.py``
(the Executive page reads it to label a partial failure Skipped rather than
Partial), and ``ScanCoverageChip.tsx`` keys its colour map by skip reason (an
unknown key silently falls back to the medium colour). Both copies are read
from the TS source at test time and compared with the live Python sets, so a
new category or reason that reaches only one side turns this file red.
Modelled on the NO_TARGET_ANSWERED_DETAIL read in tests/test_scan_coverage_api.py.
"""
from __future__ import annotations

import pathlib
import re

from quirk.models import SCAN_PHASE_SKIP_REASONS
from quirk.scanner.target_outcome import COVERAGE_SKIP_ADVISORY_CATEGORIES

_DASHBOARD_SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "dashboard" / "src"


def _read(rel: str) -> str:
    return (_DASHBOARD_SRC / rel).read_text(encoding="utf-8")


def test_ts_advisory_categories_mirror_python():
    src = _read("lib/coverage-reason.ts")
    m = re.search(
        r"export const COVERAGE_SKIP_ADVISORY_CATEGORIES: readonly string\[\] = \[(.*?)\]",
        src,
        re.S,
    )
    assert m, "COVERAGE_SKIP_ADVISORY_CATEGORIES not found in coverage-reason.ts"
    ts_categories = re.findall(r'"([a-z_]+)"', m.group(1))
    assert len(ts_categories) == 7
    assert sorted(ts_categories) == sorted(COVERAGE_SKIP_ADVISORY_CATEGORIES)


def test_chip_colours_every_skip_reason():
    src = _read("components/ScanCoverageChip.tsx")
    m = re.search(
        r"const STATUS_COLOR_CLASS: Record<string, string> = \{(.*?)\n\}",
        src,
        re.S,
    )
    assert m, "STATUS_COLOR_CLASS not found in ScanCoverageChip.tsx"
    keys = re.findall(r'^\s*"?([a-z-]+)"?\s*:', m.group(1), re.M)
    assert len(keys) == 10  # "ran" plus the nine skip reasons
    assert set(SCAN_PHASE_SKIP_REASONS) <= set(keys)


def test_ts_target_outcome_kinds_mirror_python():
    """238 UI review fix 1: phaseRecordText strips these codes from user-facing
    text, so a kind added only on the Python side would leak into a sentence."""
    from quirk.scanner.target_outcome import OUTCOME_KINDS

    src = _read("lib/coverage-reason.ts")
    m = re.search(
        r"export const TARGET_OUTCOME_KINDS: readonly string\[\] = \[(.*?)\]",
        src,
        re.S,
    )
    assert m, "TARGET_OUTCOME_KINDS not found in coverage-reason.ts"
    ts_kinds = re.findall(r'"([a-z_]+)"', m.group(1))
    assert len(ts_kinds) == 6
    assert sorted(ts_kinds) == sorted(OUTCOME_KINDS)
