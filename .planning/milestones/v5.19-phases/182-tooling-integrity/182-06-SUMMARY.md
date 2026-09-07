---
phase: 182-tooling-integrity
plan: 06
subsystem: tooling
tags: [gsd-tools, node, pytest, regex-anchoring, durability]

# Dependency graph
requires:
  - phase: 182-01
    provides: "Bug A write-side patch (stateReplaceField), GSD_TOOLCHAIN_AVAILABLE skip idiom, --cwd argv contract"
  - phase: 182-03
    provides: "gsd-local-patches/ + gsd-pristine/ durability layer, verify-reapply-patches.cjs convention"
  - phase: 182-05
    provides: "Live reproduction of the still-open read-side defect (stateExtractField, session-scoping guard), TOOL-04 filed, TOOL-01 reopened"
provides:
  - "Command-boundary regression test (test_begin_phase_does_not_read_body_prose_as_machine_fields) proven RED against the installed toolchain before any patch, then GREEN after"
  - "stateExtractField() anchored (read-side twin of Bug A)"
  - "Stopped-At session-scoping guard now matches '## Session Continuity' (and other header variants) via a line-anchored, word-bounded regex"
  - "focusPattern inside cmdStateBeginPhase anchored and newline-safe"
  - "Durability snapshots re-seeded; verify-reapply-patches.cjs reports {checked:2, failures:0} against grown required-line counts"
  - "182-REVIEW WR-01 closed: GSD_TOOLCHAIN_AVAILABLE now checks GSD_STATE_LIB (state.cjs)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-before-patch discipline: a positive regression test is run and its failure output recorded verbatim BEFORE any source patch is written, with a dedicated negative control proving the positive test is sensitive rather than vacuous"
    - "Discriminator-field selection for negative controls: a field used to prove a regex-anchoring defect must be neither normalized (normalizeStateStatus collapses many raw strings to one keyword) nor independently rewritten by the same command's own write path -- Paused At was chosen after Status and Last Activity were both shown empirically to fail as discriminators"

key-files:
  created: []
  modified:
    - "tests/test_gsd_state_patch.py"
    - "~/.claude/get-shit-done/bin/lib/state-document.generated.cjs (outside repo, not git-tracked)"
    - "~/.claude/get-shit-done/bin/lib/state.cjs (outside repo, not git-tracked)"
    - "~/.claude/gsd-local-patches/get-shit-done/bin/lib/state-document.generated.cjs (outside repo, not git-tracked)"
    - "~/.claude/gsd-local-patches/get-shit-done/bin/lib/state.cjs (outside repo, not git-tracked)"

key-decisions:
  - "The plan's literal negative-control design ('assert after[\"status\"] contains marker') does not work: normalizeStateStatus() collapses ANY string containing the phrase 'ready to execute' -- present in both the real Status field and the reused PROSE_LINE decoy -- to the single keyword 'executing', regardless of which occurrence the extractor picks up. Discovered empirically while proving the negative control's own RED. Switched the negative control's discriminator to a fourth, purpose-built decoy field, Paused At, which is neither normalized nor written by cmdStateBeginPhase's own transform (unlike Last Activity, which was tried second and also failed: reverting the WHOLE state-document.generated.cjs file for the negative control reverts stateReplaceField too, so an unanchored WRITE lands on the Last-Activity decoy line instead of the real field, entangling the write-side regression with the read-side one under test)."
  - "Retained the plan's original assertion 1 (status does not contain 'marker'/'Must not change') in the positive test even though it is now known to pass trivially regardless of patch state, because it is still a true and harmless statement about the observed behavior; the real discriminating assertions for the positive test are assertions 2/3 (stopped_at)."
  - "Did NOT patch state.cjs lines ~708-716 (the 'state json' session extraction) or line ~426 (boldProgressPattern) -- both deliberately left for 182-07 per this plan's explicit instruction, confirmed still present via grep."

requirements-completed: [TOOL-04]  # TOOL-01 not independently re-closed by this plan; see below

duration: 70min
completed: 2026-09-04
---

# Phase 182 Plan 06: TOOL-04 Close-Out — Command-Boundary Regression Test and Read-Side Patches

**Closed TOOL-04 by writing a full-command regression test FIRST, proving it RED against the installed toolchain, then patching `stateExtractField()`, the Stopped-At session-scoping guard, and the in-command `focusPattern` inside `cmdStateBeginPhase` itself — and re-seeding the durability layer so none of it silently reverts.**

## Task 1: The full-command regression test, written first and proven RED

Added to `tests/test_gsd_state_patch.py`:
- `PAUSED_AT_PROSE_LINE`, `STOPPED_AT_PROSE_LINE`, `FOCUS_PROSE_LINE` fixture-decoy constants (reusing the existing `PROSE_LINE`)
- `_full_command_state_md()` — a fixture shaped like the real `.planning/STATE.md`: frontmatter with `milestone`, `milestone_name`, `stopped_at`, a novel `my_custom_key`, and a populated `progress:` block; a real `**Current focus:**` line near the top; an `## Accumulated Context` section with four prose decoys quoting `**Status:**`, `**Stopped At:**`, `**Current focus:**`, and `**Paused At:**` inside code spans; a `## Current Position` section with plain `Status:` field; and a `## Session Continuity` section (the exact header variant the guard failed on) with the real `**Stopped At:**` value.
- `test_begin_phase_does_not_read_body_prose_as_machine_fields` — runs the INSTALLED toolchain's full `state begin-phase` command against this fixture and asserts the resulting frontmatter is not corrupted by body prose.
- `test_full_command_fixture_is_sensitive_to_the_unpatched_extractor` — the RED-proving negative control, run against `unpatched_gsd_tree` (pristine `state-document.generated.cjs`).
- WR-01: `GSD_TOOLCHAIN_AVAILABLE` now also checks `GSD_STATE_LIB.is_file()`, and `GSD_SKIP_REASON` names it.

**Verbatim RED output** (positive test failing against the installed, pre-Task-2 toolchain; negative control already green, proving sensitivity):

```
.venv/bin/pytest tests/test_gsd_state_patch.py -q
...
    # Assertion 2: stopped_at is not the out-of-section prose decoy.
    stopped_at = after.get("stopped_at") or ""
>       assert "stale-archived-value" not in stopped_at, (
            f"frontmatter stopped_at was read from an out-of-section "
            f"**Stopped At:** prose decoy instead of the real "
            f"## Session Continuity value (got: {stopped_at!r})"
        )
E       AssertionError: frontmatter stopped_at was read from an out-of-section **Stopped At:** prose decoy instead of the real ## Session Continuity value (got: 'stale-archived-value` verbatim.')
E       assert 'stale-archived-value' not in 'stale-archi...e` verbatim.'
E
E         'stale-archived-value' is contained here:
E           stale-archived-value` verbatim.

tests/test_gsd_state_patch.py:574: AssertionError
=========================== short test summary info ============================
FAILED tests/test_gsd_state_patch.py::test_begin_phase_does_not_read_body_prose_as_machine_fields
1 failed, 8 passed in 0.49s
```

The failure is on assertion 2 (a corrupted `stopped_at` value), not a collection error, fixture error, or non-zero subprocess exit — a real, diagnosable RED. Assertion 1 (the `status`/`marker` check) passed even in the RED run; see the Deviations section below for why that assertion cannot discriminate on its own, and why it was kept anyway.

**A deviation surfaced while proving this file's OWN negative control RED**, before touching any `.cjs` file: the plan's literal design for the negative control ("assert `after["status"]` contains `marker`") does not work. `normalizeStateStatus()` collapses any string containing the phrase "ready to execute" — present in both the real `Status:` field and the reused `PROSE_LINE` decoy — to the single keyword `"executing"`, regardless of which occurrence the (patched or unpatched) extractor picks up. A second attempted discriminator, `Last Activity`, also failed: `unpatched_gsd_tree` reverts the WHOLE `state-document.generated.cjs` file, which un-patches `stateReplaceField()` (the write side) right alongside `stateExtractField()` (the read side under test) — so the unanchored *write* landed on the `Last Activity` decoy line instead of the real field, entangling the write-side regression with the read-side one the control means to isolate. The negative control's discriminator was changed to a fourth, purpose-built decoy field, `Paused At` — never written by `begin-phase`, never normalized — which isolated the extractor defect cleanly. This is documented as a Rule 1 auto-fix (the plan's literal assertion design was a bug, not the fixture's underlying intent) and is fully disclosed in the test file's own docstrings, not silently substituted.

## Task 2: Patch stateExtractField(), the Stopped-At session-scoping guard, and the Current-focus rewrite

**Edit A** — `~/.claude/get-shit-done/bin/lib/state-document.generated.cjs`, `stateExtractField()`:
```
before: new RegExp(`\*\*${escaped}:\*\*[ \t]*(.+)`, 'i')
after:  new RegExp(`^\s*\*\*${escaped}:\*\*[ \t]*(.+)$`, 'im')
```

**Edit B** — `~/.claude/get-shit-done/bin/lib/state.cjs`, `buildStateFrontmatter()` (~line 762):
```
before: /##\s*Session\s*\n/i
after:  /^##\s+Session\b[^\n]*\n([\s\S]*?)(?=\n##|$)/im
```

**Edit C** — `~/.claude/get-shit-done/bin/lib/state.cjs`, `cmdStateBeginPhase()` (~line 1175):
```
before: /(\*\*Current focus:\*\*\s*).*/i
after:  /^(\s*\*\*Current focus:\*\*[ \t]*).*$/im
```

Each site carries a `LOCAL PATCH (2026-09-03)` comment in the existing house voice, naming TOOL-04 and the upstream issue (`open-gsd/gsd-core#4243`).

**Deliberate non-changes, confirmed by grep after the edits:**
- `state.cjs` line ~708 (`state json`'s session extraction, `/##\s*Session\s*\n/i`) — left untouched. It feeds a read-only report, not a STATE.md write; 182-07 enumerates and dispositions it deliberately. Confirmed present, unchanged: `grep -Fc '##\s*Session\s*\n' state.cjs` → `1` (fixed-string match on line 708's literal regex source text).
- `state.cjs` line ~426 (`boldProgressPattern = /(\*\*Progress:\*\*\s*).*/i`) — left untouched; 182-07 Task 1 needs it unpatched to prove its enumeration gate is sensitive. `grep -c 'boldProgressPattern = /('` → `1`.

**Verbatim GREEN output after all three edits:**
```
.venv/bin/pytest tests/test_gsd_state_patch.py -q
.........                                                                [100%]
9 passed in 0.47s
```

All acceptance-criteria greps confirmed:
- `grep -c "LOCAL PATCH (2026-09-03)" state-document.generated.cjs` → `2`
- `grep -c "LOCAL PATCH (2026-09-03)" state.cjs` → `3`
- `grep -v "^\s*//" state-document.generated.cjs | grep -c "boldPattern = new RegExp(.\^"` → `2`
- `grep -c 'Session\\b' state.cjs` → `1`
- `grep -c "focusPattern = /\^" state.cjs` → `1`
- `grep -c "focusPattern = /("` → `0` (old unanchored form gone)
- `node -e "require('state.cjs')"` and same for `state-document.generated.cjs` → both exit `0`

## Task 3: Re-seed the durability layer

**Pristine-hash comparison** (must equal `backup-meta.json`'s recorded `pristine_hashes`, confirming the pristine baselines were not touched):
```
sha256(gsd-pristine/.../state-document.generated.cjs) = 6157fcee866734c9931d3d49ec06e46951c59ed6fb5926667c07ede4dba31c38
sha256(gsd-pristine/.../state.cjs)                    = 2f0fa21e5b9587176168f65c7e788d61edb32700de96845ba7b004b4d31c2155
```
Both match `backup-meta.json`'s recorded hashes exactly. Pristine untouched.

**Byte-copy re-seed:** `~/.claude/gsd-local-patches/get-shit-done/bin/lib/{state-document.generated.cjs,state.cjs}` overwritten with the Task-2-patched installed files. `diff` between snapshot and installed for both files: no output (byte-identical).

**Per-file required-line counts** (using the verifier's own `isSignificantLine` predicate — min 12 significant chars, excluding pure punctuation/decorative-comment-only lines — computed as installed-vs-pristine, since that is what the freshly-reseeded snapshot now equals):
- `state-document.generated.cjs`: **19** required lines (182-03 recorded **6** before this plan) — grown, as expected (Task 2 added Edit A's patch comment + anchored regex).
- `state.cjs`: **72** required lines (182-03 recorded **40** before this plan) — grown, as expected, and specifically reflects BOTH of Task 2's two hunks in this file: `grep -c "focusPattern = /\^" gsd-local-patches/.../state.cjs` → `1`, confirming Edit C (the Current-focus anchor) specifically reached the snapshot, not just Edit B (the session guard).

**Verifier result after re-seed:**
```
node ~/.claude/get-shit-done/bin/verify-reapply-patches.cjs \
  --patches-dir ~/.claude/gsd-local-patches --config-dir ~/.claude \
  --pristine-dir ~/.claude/gsd-pristine --json
{
  "checked": 2,
  "failures": 0,
  "results": [
    {"file": "get-shit-done/bin/lib/state-document.generated.cjs", "status": "ok", "missing": [], "reason": null},
    {"file": "get-shit-done/bin/lib/state.cjs", "status": "ok", "missing": [], "reason": null}
  ]
}
```

`.venv/bin/pytest tests/test_gsd_state_patch.py -q` → `9 passed` (including `test_local_patches_are_durable` and `test_patch_loss_is_actually_detected`, both against the re-seeded layer).

## Full Verification Sweep

- `.venv/bin/pytest tests/test_gsd_state_patch.py -q` → `9 passed`
- `.venv/bin/pytest tests/test_cli_helper_usage.py -q` → `2 passed` (GATE-03's baseline unchanged — no raw `subprocess`/`cwd=` call site introduced)
- `node ~/.claude/get-shit-done/bin/verify-reapply-patches.cjs ... --json` → `{"checked":2,"failures":0}`
- `git status --porcelain .planning/ROADMAP.md .planning/STATE.md` → empty (neither touched by this plan)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries. This plan patches existing regex-anchoring defects in an already-identified trust boundary (body prose → frontmatter fields); no new surface introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in the plan's own test design] Negative control's `status`/`marker` discriminator does not work; switched to a `Paused At` decoy**
- **Found during:** Task 1, before touching any `.cjs` file — while proving the negative control itself RED-sensitive.
- **Issue:** `normalizeStateStatus()` collapses any string containing "ready to execute" to the keyword `"executing"` regardless of which `**Status:**` occurrence an extractor (patched or not) reads. A second attempt using `Last Activity` also failed because `unpatched_gsd_tree` reverts the whole file (both `stateExtractField` and `stateReplaceField`), so the unanchored write lands on the decoy line instead of the real field.
- **Fix:** Introduced `PAUSED_AT_PROSE_LINE` as a fourth fixture decoy and switched the negative control's assertion to check `after.get("paused_at")`. Both the positive test and the negative control were updated to keep the fixture (and its four prose decoys) shared and consistent.
- **Files modified:** `tests/test_gsd_state_patch.py`.
- **Commit:** `5f0b1585` (Task 1).

### Non-issues confirmed, not fixed (in scope per plan's explicit instruction)
- `state.cjs`'s `state json` session-extraction site (~line 708) and `boldProgressPattern` (~line 426) were read and deliberately left unpatched, per this plan's explicit instruction reserving them for 182-07.

## Self-Check: PASSED

- `tests/test_gsd_state_patch.py` — FOUND, contains `Session Continuity` (≥1), `GSD_STATE_LIB.is_file()` (≥2), `FOCUS_PROSE_LINE` (≥3)
- `~/.claude/get-shit-done/bin/lib/state-document.generated.cjs` — FOUND, contains `LOCAL PATCH (2026-09-03)` (count 2)
- `~/.claude/get-shit-done/bin/lib/state.cjs` — FOUND, contains `LOCAL PATCH (2026-09-03)` (count 3), `Session Continuity`-tolerant guard, anchored `focusPattern`
- `~/.claude/gsd-local-patches/get-shit-done/bin/lib/state-document.generated.cjs` — FOUND, byte-identical to installed file
- `~/.claude/gsd-local-patches/get-shit-done/bin/lib/state.cjs` — FOUND, byte-identical to installed file
- Commit `5f0b1585` — FOUND: `git log --oneline --all | grep -q 5f0b1585` → match
- `git status --porcelain .planning/ROADMAP.md .planning/STATE.md` — empty, confirmed untouched
