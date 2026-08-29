"""DASH-08 bidirectional drift guard: sidebar.tsx `NAV_ITEMS` order vs.
`docs/UAT-SERIES.md`'s `UAT-39-07` documented order (Phase 174, Plan 04 / D-03, D-04).

Why this exists: a nine-item Phase 39 "D-11" nav-order lock note went five items
stale over four months (Sensors, Schedules, QRAMM Assessment, Scan History, and
finally Hardware -- Phase 128, planned/reviewed/shipped, commit
07db14d75cc0f0da9546bcdd11d5c0ecf3cd9772) with nothing to catch the drift. The
canonical fourteen-item order is recorded, with full evidence, in
`.planning/phases/174-dashboard-api-correctness/174-SIDEBAR-ORDER.md`.

Falsifiability contract (BIDIRECTIONAL -- this is the whole point):
  1. Re-ordering, adding, or removing a `NAV_ITEMS` entry in `sidebar.tsx`
     WITHOUT updating `UAT-39-07`'s `**Expected:**` line in `docs/UAT-SERIES.md`
     turns `test_sidebar_matches_canonical_order` and
     `test_sidebar_and_document_agree_independently` RED.
  2. Editing `UAT-39-07`'s documented order in `docs/UAT-SERIES.md` WITHOUT a
     matching `sidebar.tsx` change turns `test_uat_39_07_matches_canonical_order`
     and `test_sidebar_and_document_agree_independently` RED.
A one-way guard (asserting only the document, or only the component, against a
constant) would let either side drift silently and just relocate the failure
mode this test exists to close -- so this file cross-checks both sources
against the canonical list AND against each other.

This file lives under `tests/` (the Python suite), not `src/dashboard/`, so the
`Linux Full Suite` CI job (which does not set up a Node toolchain) runs it
without needing `npm`/`vitest`. It reads `sidebar.tsx` and `docs/UAT-SERIES.md`
as plain text only -- it does not modify either file, and it contains no
skip markers of any kind (an unregistered skip would trip
`tests/test_skip_registry.py::test_no_unregistered_skips`, which allowlists
skips by exact `(file, lineno)`).
"""
from __future__ import annotations

import pathlib
import re

# Canonical fourteen-item order, provenance:
# .planning/phases/174-dashboard-api-correctness/174-SIDEBAR-ORDER.md
# (derived live from sidebar.tsx:35-48, 2026-08-29). If this list and
# 174-SIDEBAR-ORDER.md's "One-line canonical form" ever disagree, that file
# wins -- re-derive live from sidebar.tsx again, do not average stale copies.
CANONICAL_ORDER = [
    "Executive Summary",
    "Findings",
    "Identity",
    "Motion",
    "Hardware",
    "Data at Rest",
    "Certificates",
    "CBOM Viewer",
    "Migration Roadmap",
    "Trends",
    "Scan History",
    "Sensors",
    "Schedules",
    "QRAMM Assessment",
]


def _repo_root() -> pathlib.Path:
    """Walk up from __file__ to the repo root (identified by pyproject.toml).

    Never depends on the process working directory.
    """
    here = pathlib.Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError(
        f"could not locate repo root by walking up from {here} "
        "(no ancestor directory contains pyproject.toml)"
    )


SIDEBAR_TSX_PATH = _repo_root() / "src" / "dashboard" / "src" / "components" / "sidebar.tsx"
UAT_SERIES_PATH = _repo_root() / "docs" / "UAT-SERIES.md"

# Matches the `const NAV_ITEMS = [ ... ]` array literal only -- NOT the
# per-vertical entry appended conditionally later in the file
# (`vertical.navItem`, sidebar.tsx:63), which is deliberately outside the
# fixed fourteen-item list per 174-SIDEBAR-ORDER.md's scope note.
NAV_ITEMS_ARRAY_RE = re.compile(r"const NAV_ITEMS = \[(.*?)\n\]", re.DOTALL)
LABEL_RE = re.compile(r'label:\s*"([^"]*)"')


def _parse_sidebar_labels() -> list[str]:
    if not SIDEBAR_TSX_PATH.is_file():
        raise AssertionError(f"expected sidebar.tsx at {SIDEBAR_TSX_PATH}, file not found")
    text = SIDEBAR_TSX_PATH.read_text(encoding="utf-8")
    match = NAV_ITEMS_ARRAY_RE.search(text)
    if match is None:
        raise AssertionError(
            f"could not locate a `const NAV_ITEMS = [ ... ]` array literal in {SIDEBAR_TSX_PATH}"
        )
    array_body = match.group(1)
    labels = LABEL_RE.findall(array_body)
    if not labels:
        raise AssertionError(
            f"NAV_ITEMS array in {SIDEBAR_TSX_PATH} matched but contained no label: \"...\" entries"
        )
    return labels


# `**Expected:**` line for UAT-39-07, e.g.:
#   **Expected:** Order is Executive Summary · Findings · ... · QRAMM Assessment. (...)
# Labels are separated by " · " (middle dot); the sentence may continue with a
# trailing parenthetical after the final label + period, which is why the
# terminal segment is trimmed of a trailing "." and any "(...)" suffix rather
# than assumed to end cleanly at the delimiter.
UAT_39_07_EXPECTED_RE = re.compile(r"^\*\*Expected:\*\* Order is (.+)$", re.MULTILINE)


def _parse_uat_39_07_labels() -> list[str]:
    if not UAT_SERIES_PATH.is_file():
        raise AssertionError(f"expected UAT-SERIES.md at {UAT_SERIES_PATH}, file not found")
    text = UAT_SERIES_PATH.read_text(encoding="utf-8")
    heading_idx = text.find("### UAT-39-07:")
    if heading_idx == -1:
        raise AssertionError(f"could not locate '### UAT-39-07:' heading in {UAT_SERIES_PATH}")
    # Scope the search to this case's own block (up to the next '### ' heading
    # or '---' separator) so a label-shaped string in an unrelated case can
    # never be picked up.
    next_heading_idx = text.find("\n### ", heading_idx + 1)
    block_end = next_heading_idx if next_heading_idx != -1 else len(text)
    block = text[heading_idx:block_end]

    match = UAT_39_07_EXPECTED_RE.search(block)
    if match is None:
        raise AssertionError(
            f"could not locate a '**Expected:** Order is ...' line inside UAT-39-07's block in {UAT_SERIES_PATH}"
        )
    sentence = match.group(1)
    # Strip a trailing parenthetical annotation (Phase 174 correction note),
    # if present, before splitting on the middle-dot delimiter.
    sentence = re.sub(r"\s*\([^)]*\)\s*$", "", sentence).strip()
    # Drop a trailing sentence-terminating period on the last label only.
    if sentence.endswith("."):
        sentence = sentence[:-1]
    labels = [segment.strip() for segment in sentence.split("·")]
    labels = [label for label in labels if label]
    if not labels:
        raise AssertionError(
            f"UAT-39-07's '**Expected:**' line in {UAT_SERIES_PATH} parsed to zero labels"
        )
    return labels


def test_sidebar_matches_canonical_order():
    """`sidebar.tsx`'s NAV_ITEMS labels, in declaration order, equal the
    canonical fourteen-item list exactly and in order (whole-list equality,
    not membership -- a re-ordering must be caught, not just an addition)."""
    assert _parse_sidebar_labels() == CANONICAL_ORDER


def test_uat_39_07_matches_canonical_order():
    """UAT-39-07's documented `**Expected:**` order, parsed independently of
    sidebar.tsx, equals the same canonical fourteen-item list exactly and in
    order."""
    assert _parse_uat_39_07_labels() == CANONICAL_ORDER


def test_sidebar_and_document_agree_independently():
    """The two sources -- derived independently of each other and of the
    CANONICAL_ORDER constant used by the other two tests -- must still agree
    with each other. This is the bidirectional half of the guard: neither
    side can be "corrected" in isolation without this test catching the
    resulting disagreement, even in the hypothetical case where both sides
    drifted away from CANONICAL_ORDER in the same wrong direction."""
    assert _parse_sidebar_labels() == _parse_uat_39_07_labels()
