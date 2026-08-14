---
phase: 151-phase-completion-artifact-gates
reviewed: 2026-08-13T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - scripts/verify_phase_gates.py
  - tests/test_verify_phase_gates.py
  - .githooks/pre-commit
  - CONTRIBUTING.md
  - docs/UAT-SERIES.md
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 151: Code Review Report

**Reviewed:** 2026-08-13
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed `scripts/verify_phase_gates.py` (the pure decision core + CLI glue), its test suite,
`.githooks/pre-commit`, and the `CONTRIBUTING.md`/`docs/UAT-SERIES.md` documentation additions.

Security posture is solid: `subprocess.run()` uses list-form argv everywhere (no `shell=True`,
no string interpolation into a shell), `yaml.safe_load()` is used exclusively (never bare
`yaml.load()`), phase numbers used to build file globs are constrained to `\d+(?:\.\d+)?` by
regex before ever touching the filesystem (no path-traversal surface), and the pre-commit shell
wrapper quotes its one variable expansion. No hardcoded secrets, no injection vectors found.

The `_ACCEPTED_HISTORICAL_ARCHIVE_GAPS` allowlist mechanism is sound as implemented: it is a
`frozenset` keyed on `(phase_num, milestone_tag)` tuples (not phase-number-alone), it is
explicitly and heavily commented with the citation requirement, and a dedicated test
(`test_check_destructive_archive_exception_is_milestone_scoped`) proves a hypothetical future
"phase 144" under a different milestone tag still blocks normally. This is not a growing/broad
allowlist risk.

The real defects found are all **coverage gaps in the trigger/detection logic** — places where
the gate's own stated purpose (catch silent artifact-hygiene gaps) can itself be silently bypassed
by input shapes the current implementation doesn't handle, none of which are exercised by the
(otherwise thorough) test suite. These are Warning-level: the gate still works for the common,
single-phase-close-per-commit case that the test suite exercises end-to-end, but has real blind
spots for shapes the design docs themselves partially anticipated (D-03's STATE.md+ROADMAP.md
dual-source detection was scoped but only one source is implemented; Open Question 2's decimal
sub-phase handling was applied to the trigger regex but not to `check_destructive_archive`'s
STATE.md table parser).

## Warnings

### WR-01: `_extract_phase_close_trigger()` only detects the first phase-close in a commit, silently skipping ARTIFACT-01/02/03 for any additional phases closed in the same commit

**File:** `scripts/verify_phase_gates.py:406-413`
**Issue:** `_PHASE_CLOSE_TRIGGER_RE.search(diff_text)` returns only the first regex match. If a
single commit's staged `ROADMAP.md` diff flips more than one `- [ ] **Phase N:` checkbox to
`[x]` in the same commit (a realistic shape for a milestone-closeout commit that closes several
phases at once — e.g. a batch `gsd-sdk` operation, or a squashed/rebased close), `main()` only
runs `_run_phase_close_check()` for the first matched phase number. Every other phase closed in
that same commit gets zero ARTIFACT-01/02/03 enforcement — the exact "silent artifact-hygiene
gap" class this phase exists to close, reintroduced for the multi-close case. No test in
`tests/test_verify_phase_gates.py` exercises a diff with two or more `+- [x] **Phase N:` lines.
**Fix:**
```python
def _extract_phase_close_triggers(diff_text: str) -> list[str]:
    """Pure. Return ALL phase numbers whose checkbox flips to complete in
    diff_text, not just the first."""
    return [m.group(1) for m in _PHASE_CLOSE_TRIGGER_RE.finditer(diff_text or "")]
```
and in `main()`, loop over every triggered phase number and `max()` the exit code across all of
them, instead of calling `_extract_phase_close_trigger()` (singular) once.

### WR-02: Phase-close trigger only inspects the staged `ROADMAP.md` diff, not `STATE.md`, contradicting D-03's stated dual-source design

**File:** `scripts/verify_phase_gates.py:527-536`
**Issue:** D-03 (`151-CONTEXT.md`) and the research's Pattern 5 both describe detecting a
phase-close via *either* a `ROADMAP.md` checkbox flip *or* a `STATE.md` phase-map `Status` cell
change to `Complete` — "the hook inspects the staged diff to `STATE.md`/`ROADMAP.md` for a phase
status flip to `Complete`." The implemented `main()` only ever calls `git diff --cached -- ` on
`ROADMAP.md`; `STATE.md`'s diff is never inspected as a trigger source. A commit that updates only
`STATE.md`'s phase-map status cell to `Complete...` (without also flipping the corresponding
`ROADMAP.md` checkbox in the same commit — plausible for a retroactive/out-of-band status
correction, or a commit that only touches `STATE.md`) fires zero phase-close checks. This
silently reintroduces the class of gap ARTIFACT-01/02/03 exist to prevent, for any close whose
git-visible signal lives only in `STATE.md`.
**Fix:** Either also run `git diff --cached -- .planning/STATE.md` and parse its phase-map rows
for an `Status` cell transition to `Complete` (matching the `_PHASE_MAP_ROW_RE`/
`parse_state_phase_maps` machinery already built for ARTIFACT-04), unioning triggered phase
numbers from both sources; or, if `ROADMAP.md`-only detection is an intentional narrowing from
the CONTEXT doc's dual-source language, document that narrowing explicitly in the script's
module docstring and in `151-CONTEXT.md`/a phase note, since the current code silently diverges
from the written design decision with no comment explaining why.

### WR-03: `check_destructive_archive()`'s STATE.md phase-map parser silently drops decimal sub-phase rows (e.g. `64.1`), leaving them permanently unenforced by ARTIFACT-04

**File:** `scripts/verify_phase_gates.py:277-309` (specifically `if not phase_num.isdigit(): continue` at line 305)
**Issue:** `_PHASE_CLOSE_TRIGGER_RE` (used for the ARTIFACT-01/02/03 trigger) was deliberately
written as `\d+(?:\.\d+)?` per Research Open Question 2, with an explicit unit test
(`test_extract_phase_close_trigger_handles_decimal_subphase_number`) proving `64.1` is captured
correctly. `parse_state_phase_maps()` — the STATE.md table parser that feeds
`check_destructive_archive()` (ARTIFACT-04) — was not given the same treatment: it filters rows
with `phase_num.isdigit()`, which is `False` for a decimal phase number like `"64.1"`. Any
`Complete`-marked decimal sub-phase row in a STATE.md phase map (the codebase's own history shows
at least one precedent, `64.1-audit-residual-blockers`, cited directly in the research doc) is
silently excluded from `phase_map_rows`, meaning ARTIFACT-04 never checks whether its directory
was ever archived — a decimal sub-phase's content could vanish with no archive and the
destructive-archive gate would never notice, for as long as the project uses decimal phase
numbering. No test in the suite constructs a STATE.md fixture with a decimal-numbered row to
verify this behavior either way.
**Fix:**
```python
if not re.match(r"^\d+(?:\.\d+)?$", phase_num):
    continue
```
matching the same pattern already used for the trigger regex, plus a test mirroring
`test_parse_state_phase_maps_extracts_rows_attributed_to_section` with a `64.1` row.

### WR-04: `PHASES_ROOT`, `MILESTONES_ROOT`, `STATE_PATH`, `ROADMAP_PATH`, `UAT_SERIES_PATH` module-level constants are defined but never referenced

**File:** `scripts/verify_phase_gates.py:56-60`
**Issue:** These five `pathlib.Path` constants are computed at import time from the hardcoded
`REPO_ROOT` (`__file__`-derived), but every actual code path (`_run_phase_close_check()`,
`_run_destructive_archive_check()`, `main()`) instead recomputes the equivalent paths locally
from the injectable `repo_root` parameter (e.g. `repo_root / ".planning" / "phases"`), which is
correct — the injectable-`repo_root` seam is required for the test suite's `tmp_path`-based
fixtures to work at all, so the module constants literally *couldn't* be used in those call sites
without breaking testability. The five constants are therefore dead code: unused, and a
maintenance trap (a future contributor could plausibly reach for `PHASES_ROOT` in new code,
silently reintroducing a hardcoded-`REPO_ROOT` path that bypasses the `repo_root` test seam).
**Fix:** Delete the five unused constants, or if kept for documentation/discoverability, add a
`# NOTE: unused by design — real call sites always route through the injectable repo_root
parameter for testability` comment directly above them so a future editor doesn't wire them in
by mistake.

## Info

### IN-01: `check_phase_close()`'s ARTIFACT-01 gate validates VERIFICATION.md *presence* only, not content

**File:** `scripts/verify_phase_gates.py:153-158`
**Issue:** `verification_exists` is a pure existence check (`verification_path.exists()`, see
`scripts/verify_phase_gates.py:441`). A phase can satisfy ARTIFACT-01 by creating an empty or
placeholder `VERIFICATION.md` with no actual verification content, and the gate passes. This
matches the literal ARTIFACT-01 requirement text ("VERIFICATION.md is missing") and is consistent
with the phase's stated scope, so this is not a design defect — just worth documenting as a known
boundary of the guarantee (mirrors the `--no-verify` bypass note already present in
`CONTRIBUTING.md`/`.githooks/pre-commit`).
**Fix:** Optional: note in `CONTRIBUTING.md`'s "Installing the pre-commit artifact gate" section
that ARTIFACT-01 checks presence, not content quality, so readers don't over-trust the guarantee.

### IN-02: `_PHASE_MAP_ROW_RE` will parse any `|`-delimited line under a `## v<X.Y> Phase Map` heading as a phase row, including incidental prose tables

**File:** `scripts/verify_phase_gates.py:274, 300-307`
**Issue:** `parse_state_phase_maps()` treats every line matching the generic
`^\|\s*(\S+)\s*\|.*\|\s*([^|]*?)\s*\|\s*$` shape between a `## v<X.Y> Phase Map` heading and the
next `##` heading as a phase-map table row (filtered only by `phase_num.isdigit()`). If a future
STATE.md edit adds any other markdown table under the same section heading (e.g. an explanatory
sub-table) whose first column happens to be purely numeric, it would be silently ingested as a
bogus phase row. Low risk given the current STATE.md structure (one table per section, verified),
but there's no structural guard (e.g. requiring the header separator row `|---|---|` immediately
after the column-header row) beyond the loose regex + digit filter.
**Fix:** Low priority; consider anchoring on the known 5-column header (`Phase | Name |
Requirements | Gate | Status`) if STATE.md's shape is ever restructured with additional tables
in the same section.

### IN-03: Duplicated "Notes:" line in the new UAT-151-01 entry

**File:** `docs/UAT-SERIES.md` (UAT-151-01 entry, `**Notes:**` line)
**Issue:** `**Notes:** ARTIFACT-01, ARTIFACT-03. Requirement: ARTIFACT-01, ARTIFACT-03.` repeats
the same requirement IDs twice in one line with slightly different framing ("Notes: X. Requirement:
X."). Harmless, but reads as a copy-paste artifact against the surrounding UAT-SERIES.md
convention (compare UAT-151-02's cleaner `**Notes:** ARTIFACT-04. Requirement: ARTIFACT-04.`,
which has the same minor redundancy but is at least consistent).
**Fix:** Trim to a single clause, e.g. `**Notes:** Requirement: ARTIFACT-01, ARTIFACT-03.`

---

_Reviewed: 2026-08-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
