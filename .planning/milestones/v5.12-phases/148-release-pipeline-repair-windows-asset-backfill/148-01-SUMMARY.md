---
phase: 148-release-pipeline-repair-windows-asset-backfill
plan: 01
subsystem: release-pipeline
tags: [github-actions, ci-cd, release, dry-run, testing]
dependency-graph:
  requires: []
  provides:
    - "release.yml workflow_dispatch dry-run mechanism"
    - "tests/test_release_workflow_dryrun_guards.py static guard suite"
    - "Release Runbook pre-tag dry-run step"
  affects:
    - "148-02 (tag-hygiene guard, reuses the same event+ref reasoning)"
    - "148-04 (live proof plan — exercises this dry-run mechanism end-to-end)"
    - "153 (release tag cut, gated on this phase)"
tech-stack:
  added: []
  patterns:
    - "Event+ref dry-run guard idiom: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/'), never ref-shape-only"
key-files:
  created:
    - tests/test_release_workflow_dryrun_guards.py
  modified:
    - .github/workflows/release.yml
    - docs/release-process.md
decisions:
  - "D-05/D-06/D-07 implemented exactly as specified in 148-CONTEXT.md — workflow_dispatch trigger, byte-identical event+ref guards on publish job and Attach-zip step, exact-complement dry-run upload guard"
  - "Static test's ref-shape regression check (test_no_guard_is_ref_shape_only) scoped to actual `if:` directive lines only, excluding explanatory comments that quote the guard literal by name — avoids a false positive against the workflow's own inline documentation"
metrics:
  duration: "25min"
  completed: "2026-08-11"
---

# Phase 148 Plan 01: Release Pipeline Dry-Run Mechanism Summary

Added a `workflow_dispatch` dry-run trigger to `.github/workflows/release.yml`, gated on the
triggering event (not just ref shape) so no manual dispatch — including one deliberately
targeting a tag ref — can ever reach PyPI or mutate a GitHub Release, and locked the guards in
place with an 11-test static YAML suite plus a new pre-tag runbook step.

## What Was Built

### Task 1 — Dry-run mechanism in release.yml

Applied the four edits specified in `148-PATTERNS.md`:

1. `workflow_dispatch:` added as a sibling trigger to `push: tags: ['v*.*.*']`, no required
   inputs.
2. `publish` job gated with `if: github.event_name == 'push' && startsWith(github.ref,
   'refs/tags/')` — the whole PyPI-publish job is unreachable from any `workflow_dispatch` run.
3. The `Attach zip to GitHub Release` step (not the whole `windows-package` job) gated with the
   byte-identical guard, so build/sign/self-test/zip-assembly still run and are provable in
   dry-run mode.
4. A new `Upload dry-run zip artifact` step inserted between "Assemble Windows operator zip" and
   "Attach zip to GitHub Release", gated on the exact logical complement
   `${{ !(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')) }}`, reusing the
   existing `actions/upload-artifact@ea165f8d...` pin (v4.6.2) verbatim, uploading to
   `quirk-windows-dry-run`.

Top-of-file comment block extended to document the manual dry-run trigger and the event-vs-ref
reasoning; a one-line comment sits above each `if:` recording that the event conjunct is
deliberate.

Commit: `bec64f4`

### Task 2 — Static guard test

Created `tests/test_release_workflow_dryrun_guards.py` (11 tests, mirroring
`tests/test_windows_ci_hardgate.py`'s structure): trigger presence, tag-push preservation,
publish-job guard polarity, windows-package job NOT gated at job level, Attach-zip step guard,
byte-identity between the two release guards, the dry-run upload step's exact-complement form
and pin, step ordering, WR-03 SHA-pinning across every `uses:` in the file, and a regression
check (`test_no_guard_is_ref_shape_only`) that every `if:` directive mentioning the bare
`startsWith(github.ref, 'refs/tags/')` form also carries the event-name conjunct.

Commit: `7ca2c8e`

### Task 3 — Release Runbook update

Inserted a new step 2 ("Run a release dry-run before tagging") into `docs/release-process.md`'s
`## Release Runbook`, between the former steps 1 and 2, renumbering the list to 1–9. Documents
the exact `gh workflow run release.yml --ref main` / `gh run watch` commands, what the dry-run
does and does not execute, the `quirk-windows-dry-run` artifact location, and the stop rule
(citing the v5.11.0 incident). Added a cross-reference in the "Monitor the release workflow"
step noting a real tag push additionally runs `publish` and attaches the Release asset.

Commit: `741122e`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Static test's ref-shape regression check false-positived on explanatory comments**
- **Found during:** Task 2, first `pytest` run
- **Issue:** `test_no_guard_is_ref_shape_only` scanned every line of `release.yml` for the
  `REF_ONLY_GUARD` substring. The comment added above the `publish` job's `if:` in Task 1
  (`# this to \`startsWith(github.ref, 'refs/tags/')\` alone (RELEASE-02, D-06).`) legitimately
  quotes the ref-only form by name while explaining why it must NOT be used — but the naive
  substring scan flagged that comment line as a live violation.
- **Fix:** Scoped the scan to lines whose stripped content starts with `if:` (actual YAML
  directives), skipping prose/comment lines. This matches the plan's own acceptance-criteria
  grep (`grep -n "if:" ... | grep "startsWith(github.ref" | grep -vc "github.event_name"`),
  which already implicitly filters to `if:`-bearing lines.
- **Files modified:** `tests/test_release_workflow_dryrun_guards.py`
- **Commit:** `7ca2c8e` (folded into the initial test-file commit — caught before first commit)

Otherwise the plan executed exactly as written; all three tasks' acceptance criteria were
verified directly (YAML parse, guard literals, step ordering, SHA-pin regex, doc grep counts).

## Known Stubs

None — this plan modifies CI/CD configuration and documentation only, no application code with
data-flow stubs.

## Threat Flags

None — this plan implements exactly the mitigations specified in the phase's own
`<threat_model>` (T-148-01, T-148-01b, T-148-02, T-148-03, T-148-04, T-148-SC) with no new
surface introduced beyond what CONTEXT.md and PATTERNS.md already scoped.

## Self-Check: PASSED

- FOUND: `.github/workflows/release.yml` (modified, `workflow_dispatch` present, both guards
  verified via the plan's exact automated verification command)
- FOUND: `tests/test_release_workflow_dryrun_guards.py` (11 tests, all passing)
- FOUND: `docs/release-process.md` (modified, `quirk-windows-dry-run` / `gh workflow run
  release.yml` / `refs/tags/` all present)
- FOUND commit `bec64f4` (`git log --oneline --all | grep bec64f4`)
- FOUND commit `7ca2c8e`
- FOUND commit `741122e`
