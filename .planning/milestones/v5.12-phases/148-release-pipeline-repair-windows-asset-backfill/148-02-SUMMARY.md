---
phase: 148-release-pipeline-repair-windows-asset-backfill
plan: 02
subsystem: release-pipeline
tags: [github-actions, ci-cd, release, scheduled-guard, testing]
dependency-graph:
  requires:
    - "148-01 (release.yml dry-run mechanism, reused event+ref reasoning idiom)"
  provides:
    - "scripts/release_tag_hygiene.py pure decision function + CLI"
    - ".github/workflows/release-tag-hygiene.yml scheduled guard"
    - ".github/tag-hygiene-baseline.txt historical disposition ledger"
    - "docs/release-process.md Release Tag Hygiene Guard runbook section"
  affects:
    - "153 (release tag cut — first tag evaluated against a green-from-day-one baseline)"
tech-stack:
  added: []
  patterns:
    - "Scheduled drift-guard idiom (python-staleness.yml analog): cron + gh CLI cross-reference + $GITHUB_STEP_SUMMARY + fail-on-drift, applied to tag/release cross-referencing instead of file freshness"
key-files:
  created:
    - scripts/release_tag_hygiene.py
    - tests/test_release_tag_hygiene.py
    - .github/workflows/release-tag-hygiene.yml
    - .github/tag-hygiene-baseline.txt
  modified:
    - docs/release-process.md
decisions:
  - "D-10/D-11/D-12 implemented exactly as specified — LOOSE_RELEASE_TAG_RE (^v[0-9]) deliberately broader than release.yml's v*.*.* glob so v5.9 is evaluated; scheduled-only trigger (no push/pull_request) per D-09 since the real incidents produced zero events; baseline seeded with all 32 pre-existing tags so the first scheduled run is green"
  - "collect_backed_tags factored as its own pure helper per the interface block, unioning gh run list headBranch/displayTitle matches with gh release list tagName — covers the aged-out-Actions-history fallback case explicitly"
  - "TDD gate followed at the task-1 granularity: test file committed first against a temporarily-removed implementation (genuine RED, 9 failed + 16 errored), then the script restored and committed as GREEN (15/25 passing, remaining 10 targeting not-yet-created Task-2 files)"
metrics:
  duration: "35min"
  completed: "2026-08-11"
---

# Phase 148 Plan 02: Release Tag Hygiene Guard Summary

Added a Monday-morning scheduled workflow (also manually dispatchable) that cross-references every
release-like git tag against successful `release.yml` runs and GitHub Release objects, so a
malformed tag (`v5.9`, which never matched the strict `v*.*.*` glob) or an unpushed tag
(`v5.10.0`) becomes a visible red X in the Actions tab instead of a silent gap an operator has to
remember to check for.

## What Was Built

### Task 1 — Tag-hygiene decision script with unit tests

`scripts/release_tag_hygiene.py` implements the exact interface specified in the plan:

- `LOOSE_RELEASE_TAG_RE` (`^v[0-9]`) — intentionally looser than `release.yml`'s `v*.*.*` glob
  (D-10), so a malformed two-component tag like `v5.9` is still evaluated instead of silently
  skipped.
- `load_baseline(path)` — parses `<tag> <reason>` lines, ignoring `#` comments and blanks.
- `collect_backed_tags(run_records, release_tag_names)` — pure union helper: a tag is backed if
  it matches a successful run's `headBranch`, appears (via containment) in a run's `displayTitle`,
  or has a real GitHub Release object (the aged-out-Actions-history fallback). Both-empty inputs
  correctly yield an empty set rather than a vacuous "everything backed."
- `evaluate_tags(tags, released_tags, baseline)` — pure decision function returning
  `(flagged, exempted, summary_markdown)`; unbacked+baselined tags are `exempted` (visible, not
  hidden), unbacked+unbaselined tags are `flagged` (fail the job).
- `main(argv)` — collects tags via `git tag --list`, backed tags via `gh run list`/`gh release
  list`, treats any non-zero `gh` exit or unparseable JSON as a hard error (exit 2) rather than
  ever silently treating unreachable GitHub state as "all backed" (T-148-09), and writes the
  summary to `$GITHUB_STEP_SUMMARY` when set (else stdout).

`tests/test_release_tag_hygiene.py` covers every `<behavior>` bullet — 15 tests exercising
`evaluate_tags`, `load_baseline`, and `collect_backed_tags` directly with literal inputs, no
subprocess/network/`gh`, loaded via `importlib.util.spec_from_file_location` since `scripts/` is
not an importable package.

**TDD gate:** the test file was committed first against a temporarily-relocated implementation
(`mv scripts/release_tag_hygiene.py /tmp/...`), confirming genuine RED (9 failed, 16 errored on
`FileNotFoundError`). The implementation was then restored, verified GREEN for all 15 script-level
tests, and committed separately.

Commits: `9570715` (RED), `9176ed6` (GREEN)

### Task 2 — Scheduled workflow + seeded historical baseline

`.github/workflows/release-tag-hygiene.yml`:

- Triggers: `schedule: '0 9 * * 1'` (Mondays 09:00 UTC, matching `python-staleness.yml`'s cadence)
  and `workflow_dispatch:` only — no `push`/`pull_request` (D-09: the real incidents produced zero
  events, so a per-push check has nothing to react to).
- Workflow-level `permissions: {contents: read, actions: read}` — a deliberate departure from the
  `python-staleness.yml` analog (which relies on defaults), satisfying WR-04.
- `actions/checkout@34e1148...` (v4.3.1) with `fetch-depth: 0` (the default shallow checkout
  fetches no tags, which would make `git tag --list` return nothing and the guard vacuously
  green), `actions/setup-python@a26af69...` (v5.6.0), then `python scripts/release_tag_hygiene.py`
  with `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.

`.github/tag-hygiene-baseline.txt` seeded with all 32 tags present in the repo (`git tag --list |
wc -l` == the file's non-comment/non-blank line count, verified). `v5.9`, `v5.10.0`, and `v5.11.0`
carry specific incident-accurate reasons; every other pre-existing tag carries the shared
`historical baseline — predates the tag hygiene guard (2026-08-11)` reason.

10 static guard tests appended to `tests/test_release_tag_hygiene.py`: workflow file exists/valid
YAML, trigger set (`schedule` cron + `workflow_dispatch`, no `push`/`pull_request`), permissions
block shape (no write scopes), `fetch-depth: 0` present, every `uses:` line SHA-pinned
(`^[\w./-]+@[0-9a-f]{40}$`), workflow references the script, baseline file exists/parses and
contains the three required entries. All 25 tests in the file pass.

Commit: `263afd7`

### Task 3 — Release Runbook documentation

New `## Release Tag Hygiene Guard` section in `docs/release-process.md`, placed immediately after
`## Release Runbook` and before `## One-Time Setup`: what it is, why it exists (the same `v5.9`/
`v5.10.0` incident narrative), what it checks, what red means, the three sanctioned remediations in
priority order, and the baseline file's disposition-not-mute-button contract. Runbook step 9
gained a cross-reference pointing at this guard as the standing backstop for a silently-failed tag.

Commit: `878cbd9`

## Deviations from Plan

None — the plan executed exactly as written. The TDD gate (RED via temporary implementation
relocation, then GREEN) was applied at Task 1's script-level granularity per the plan's
`tdd="true"` frontmatter; Task 2's additional static-guard tests were appended and verified
directly against the already-created files (both were built together in the same task per the
plan's own task grouping, so no separate RED/GREEN split was warranted for Task 2 — the plan does
not mark Task 2 `tdd="true"`).

## Known Stubs

None — this plan modifies CI/CD configuration, a standalone stdlib-only script, and documentation
only; no application code with data-flow stubs.

## Threat Flags

None — this plan implements exactly the mitigations specified in the phase's own `<threat_model>`
(T-148-07 through T-148-11, T-148-SC) with no new surface introduced beyond what CONTEXT.md and
the plan's interface block already scoped. Tag names flow only into Python comparisons/prints,
never into a shell `run:` interpolation or a `${{ }}` expression.

## Self-Check: PASSED

- FOUND: `scripts/release_tag_hygiene.py`
- FOUND: `tests/test_release_tag_hygiene.py` (25 tests, all passing)
- FOUND: `.github/workflows/release-tag-hygiene.yml`
- FOUND: `.github/tag-hygiene-baseline.txt` (32 entries, matches `git tag --list` count)
- FOUND: `docs/release-process.md` (modified, `## Release Tag Hygiene Guard` heading present)
- FOUND commit `9570715` (RED)
- FOUND commit `9176ed6` (GREEN)
- FOUND commit `263afd7`
- FOUND commit `878cbd9`
