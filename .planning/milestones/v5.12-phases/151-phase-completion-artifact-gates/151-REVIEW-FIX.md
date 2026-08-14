---
phase: 151-phase-completion-artifact-gates
fixed_at: 2026-08-14T01:30:00Z
review_path: .planning/phases/151-phase-completion-artifact-gates/151-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 151: Code Review Fix Report

**Fixed at:** 2026-08-14T01:30:00Z
**Source review:** .planning/phases/151-phase-completion-artifact-gates/151-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical + Warning; Info findings IN-01/02/03 out of scope per instruction)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `_extract_phase_close_trigger()` only detects the first phase-close in a commit

**Files modified:** `scripts/verify_phase_gates.py`, `tests/test_verify_phase_gates.py`
**Commit:** 19bad00
**Applied fix:** Replaced `_extract_phase_close_trigger()` (singular, `.search()`-based) with
`_extract_phase_close_triggers()` (plural, `.finditer()`-based, deduplicated, order-preserving).
Updated `main()` to loop over every triggered phase number and `max()` the exit code across all
of them instead of handling a single `Optional[str]`. Updated the three existing trigger-regex
unit tests to call the new plural function, added a dedicated multi-match unit test, and added a
`main()`-level regression test (`test_main_returns_1_when_commit_closes_multiple_phases_and_second_is_missing_verification`)
proving a two-phase-close commit is checked for both phases — phase 998 is clean, phase 999 (the
second match) is deliberately missing VERIFICATION.md, so the test would have wrongly passed with
exit code 0 under the pre-fix single-match behavior.

### WR-02: Phase-close trigger only inspects ROADMAP.md, never STATE.md

**Files modified:** `scripts/verify_phase_gates.py`, `tests/test_verify_phase_gates.py`
**Commit:** 4410834
**Applied fix:** Added `_extract_state_phase_close_triggers()`, mirroring the ROADMAP.md trigger
regex's `\d+(?:\.\d+)?` phase-number shape, matching added (`^\+\|`) STATE.md phase-map table rows
whose Status cell contains `Complete`. `main()`'s single injectable `git_runner` now diffs both
`.planning/ROADMAP.md` and `.planning/STATE.md` in one `git diff --cached` call, and unions
triggered phase numbers from both extractors (deduplicated, order-preserving) before running
`_run_phase_close_check()` for each. This restores the dual-source detection design described in
D-03 (`151-CONTEXT.md`)/Pattern 5. Added unit tests for the new extractor (matches, ignores
non-Complete rows, handles decimal sub-phases, deduplicates) plus a `main()`-level regression test
(`test_main_returns_1_on_state_md_only_status_flip_to_complete`) proving a STATE.md-only status
flip (no matching ROADMAP.md checkbox change in the same diff) now fires ARTIFACT-01/02/03.

### WR-03: `parse_state_phase_maps()` silently drops decimal sub-phase rows

**Files modified:** `scripts/verify_phase_gates.py`, `tests/test_verify_phase_gates.py`
**Commit:** 6e28749
**Applied fix:** Replaced the `if not phase_num.isdigit(): continue` filter with
`if not re.match(r"^\d+(?:\.\d+)?$", phase_num): continue`, matching the same pattern the
`_PHASE_CLOSE_TRIGGER_RE` trigger regex already uses for this exact shape (Open Question 2). Added
`test_parse_state_phase_maps_includes_decimal_subphase_rows`, mirroring the style of the existing
`test_parse_state_phase_maps_extracts_rows_attributed_to_section` test, with a `64.1` row proving
it now survives the filter and is attributed to the correct milestone section.

### WR-04: Unused module-level path constants

**Files modified:** `scripts/verify_phase_gates.py`
**Commit:** 0318b81
**Applied fix:** Deleted the five unused constants (`PHASES_ROOT`, `MILESTONES_ROOT`, `STATE_PATH`,
`ROADMAP_PATH`, `UAT_SERIES_PATH`), keeping `REPO_ROOT` (still used as `main()`'s default
`repo_root`). Left a `# NOTE:` comment in their place explaining that every real call site
(`_run_phase_close_check()`, `_run_destructive_archive_check()`, `main()`) routes through the
injectable `repo_root` parameter for testability, so a future editor should not reintroduce a
hardcoded-`REPO_ROOT` constant that would bypass that seam.

## Skipped Issues

None — all four in-scope findings were fixed.

---

_Fixed: 2026-08-14T01:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
