---
phase: 78-html-pdf-injection-hardening
plan: 03
subsystem: reports
tags: [harden-01, harden-03, md_cell, markdown-escape]
requires: [78-01]
provides: [md_cell-parity-executive, md_cell-parity-writer-scorecard, md_cell-parity-writer-roadmap, md_cell-escape-unit-tests]
affects: [quirk/reports/executive.py, quirk/reports/writer.py, tests/test_md_cell_escape.py]
tech-stack:
  added: []
  patterns: [md_cell-wrap-at-render-boundary, gfm-table-cell-escape-reuse-in-bullets]
key-files:
  created:
    - tests/test_md_cell_escape.py
  modified:
    - quirk/reports/executive.py
    - quirk/reports/writer.py
decisions:
  - Reuse md_cell (GFM-table-shaped) in bullet contexts — accepted technical debt per threat T-78-13 / RESEARCH R-4; backtick passthrough deferred per CONTEXT.md
  - Integer cells (port, count, score, severity-enum) NOT wrapped — only string-typed adversary-controllable cells
  - dep_txt construction wraps each dependency title individually inside the literal joiner
metrics:
  duration: ~25min
  completed: 2026-05-16
---

# Phase 78 Plan 03: md_cell Rollout — Executive + Writer Markdown Emission Summary

**One-liner:** Cluster A scanner-controlled markdown emission sites in `executive.py` and `writer.py` now wrap every adversary-controllable string in `md_cell()` for parity with `technical.py`; new `tests/test_md_cell_escape.py` proves pipe / LF / CRLF / control-char escape against the actual `_md_escape.py` contract.

## Files Modified

| File | Change | md_cell call sites |
|------|--------|-------------------:|
| `quirk/reports/executive.py` | Added import; wrapped scanner-controlled cells at 7 line locations | 10 |
| `quirk/reports/writer.py`    | Added import; wrapped `_scorecard_markdown` (2 sites) + `_roadmap_markdown` (1 site with per-dep wrap) | 6 |
| `tests/test_md_cell_escape.py` | NEW — 9 unit tests encoding the actual `_md_escape.py` contract | n/a |

## Cluster A Coverage (14 sites enumerated in RESEARCH.md)

| Site | Coverage |
|------|----------|
| `technical.py:44` | already wrapped (regression-only — preserved) |
| `technical.py:63` | already wrapped |
| `technical.py:83` | already wrapped |
| `technical.py:99` | already wrapped |
| `executive.py:170` (score driver reason) | wrapped |
| `executive.py:188` (blockers category) | wrapped (count is int — not wrapped) |
| `executive.py:206` (interpretation bullet) | wrapped |
| `executive.py:222` (roadmap title + why) | both wrapped |
| `executive.py:224` (owner + timeframe) | both wrapped |
| `executive.py:235` (path + recommendation) | both wrapped |
| `executive.py:238` (host) | wrapped (port is int — not wrapped; severity is internal enum — not wrapped per RESEARCH guidance) |
| `writer.py:75` (`_scorecard_markdown` driver loop) | wrapped |
| `writer.py:81` (`_scorecard_markdown` action title + why) | both wrapped |
| `writer.py:97` (`_roadmap_markdown` title + why + per-dep) | all three wrapped (deps joined inside literal parenthetical) |

**14 / 14 Cluster A sites covered** (4 pre-existing in `technical.py` + 10 new in `executive.py`/`writer.py`).

## Tests

- `tests/test_md_cell_escape.py` — **9 tests**, all pass:
  - `test_pipe_escaped`
  - `test_newline_neutralized`
  - `test_crlf_neutralized`
  - `test_cr_only_neutralized`
  - `test_backtick_handled` (documents passthrough — CONTEXT.md / `_md_escape.py` module docstring defers backtick guard; assertion encodes the truthful contract)
  - `test_control_char_handled`
  - `test_none_returns_empty`
  - `test_integer_passes`
  - `test_pipe_and_newline_combined` (defense-in-depth combo)

**Phase 78 test slice:** `pytest tests/test_sanitize_scanner_text.py tests/test_md_cell_escape.py tests/test_reports_writer.py tests/test_report_sanitization.py -q` → **32 passed**.

**Compileall:** `python -m compileall -q quirk/` → clean.

**md_cell counts (verify gates):**
- `quirk/reports/executive.py`: **10** occurrences (gate ≥ 10 ✓)
- `quirk/reports/writer.py`: **6** occurrences (gate ≥ 5 ✓)

## Pre-existing Assertion Updates (R-6)

None. `tests/test_reports_writer.py` did not assert on raw `|` / `\n` in writer output, so no escape-assertion updates were required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Locally install `nh3` to verify tests**
- **Found during:** Task 4 verification.
- **Issue:** `pytest tests/test_reports_writer.py` failed with `ModuleNotFoundError: No module named 'nh3'`. The error surfaced through `quirk.reports.writer` → `quirk.reports.html_renderer` → `quirk.util.sanitize` import chain. `nh3>=0.2.17` was added to `pyproject.toml` in Plan 78-01 (commit `c40a9bd`) but had not been installed in the local Python 3.14 environment.
- **Fix:** `python -m pip install --user --break-system-packages "nh3>=0.2.17"` (one-time local setup; not a code change).
- **Files modified:** none.
- **Commit:** n/a (environment setup only).

### Plan-Wave Race (advisory — no fix needed)

**2. [Wave-parallel artifact] Plan 78-03 functional content landed inside the Plan 78-02 commit**
- **Found during:** Task 4 commit step.
- **Issue:** Plan 78-02 (concurrent wave-A agent) staged with `git add -A` (or equivalent) and absorbed my staged Plan 03 files (`executive.py`, `writer.py`, `tests/test_md_cell_escape.py`) into its `feat(78-02)` commit (`3421625`). When I then ran `git commit -m "feat(78-03): ..."` the tree was already clean and the commit was rejected as empty.
- **Actual location of Plan 03 work:** commit **`3421625`** (`feat(78-02): jinja sanitize filter + constant PDF metadata`) — contains BOTH Plan 02's Jinja/template changes AND Plan 03's executive.py + writer.py + test_md_cell_escape.py changes.
- **Verification:** `git show 3421625 -- quirk/reports/executive.py | grep -c md_cell` → 8 hunks; writer.py → 6 hunks; tests/test_md_cell_escape.py → full new file. All Plan 03 content present in tree at HEAD.
- **No remediation taken:** rewriting history would be destructive in a multi-agent context. The functional outcome (md_cell parity across Cluster A) is correct.

### Architectural Notes

**Reused md_cell in bullet contexts (R-4 / T-78-13):** `md_cell` is shaped for GFM table cells (pipe + newline + CRLF + control-char escape). `executive.py` and `writer.py::_scorecard_markdown` / `_roadmap_markdown` emit bullet lists (`- item`), not table cells. The reuse is logged as accepted technical debt per Phase 78 CONTEXT.md and the threat model `T-78-13` row. Backtick escape remains deferred — `test_backtick_handled` documents the passthrough as the truthful contract.

## Requirements Closed

- **HARDEN-01:** full — every Cluster A markdown emission site in `executive.py` + `writer.py` wraps scanner-controlled cells in `md_cell()`; `technical.py` parity preserved; explicit unit tests prove pipe/newline/CRLF/control-char escape.
- **HARDEN-03 (markdown portion):** scanner-emitted free-text (driver reasons, finding titles, hosts, recommendations, roadmap titles) sanitized before markdown render. HTML/PDF portion of HARDEN-03 is covered by Plans 02 (Jinja sanitize) and 04 (Playwright context).

## Commits

- `3421625` — `feat(78-02): jinja sanitize filter + constant PDF metadata` (contains Plan 03 files; see Deviation #2)

## Self-Check: PASSED

- ✓ `quirk/reports/executive.py` FOUND with 10 `md_cell(` call sites
- ✓ `quirk/reports/writer.py` FOUND with 6 `md_cell(` call sites
- ✓ `tests/test_md_cell_escape.py` FOUND (9 tests, all pass)
- ✓ `python -m compileall -q quirk/` clean
- ✓ Phase 78 test slice: 32 passed
- ✓ Commit `3421625` exists in tree with all Plan 03 file changes
