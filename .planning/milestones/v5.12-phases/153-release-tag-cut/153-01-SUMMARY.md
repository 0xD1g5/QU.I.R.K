---
phase: 153-release-tag-cut
plan: 01
subsystem: release-process
tags: [ci, release, dry-run, verification]
dependency-graph:
  requires: []
  provides: [origin-main-sync-confirmed, live-ci-green-confirmed, release-dry-run-confirmed]
  affects: [153-02]
tech-stack:
  added: []
  patterns: ["gh run watch for live CI confirmation instead of trusting cached state"]
key-files:
  created: []
  modified: []
decisions: []
metrics:
  duration: "~15 minutes"
  completed: 2026-08-14
---

# Phase 153 Plan 01: Verify origin/main sync + live CI green + release.yml dry-run Summary

Confirmed `origin/main` is live-synced with local `main` at `e619de4dc09a56eaaa364b03beb69a62327ff1b6`, watched all three required CI workflows to a real `success` conclusion on that SHA, then triggered and watched a `workflow_dispatch` dry-run of `release.yml` that proved the signing self-test passes and zero publish/attach side effects occurred.

## What Was Built

This is a verification-only plan (`files_modified: []` in frontmatter) — no code or doc files were created or modified. All work was live confirmation via `git` and `gh` against GitHub's real state, evidenced below.

### Task 1: Confirm origin/main sync and real CI green

- Precondition check: `git rev-list --left-right --count origin/main...HEAD` returned `0  0` — local `main` (checked out as `worktree-agent-aca80b83ca9fac84f`, same commit) and `origin/main` were already in sync at commit `e619de4dc09a56eaaa364b03beb69a62327ff1b6` (Phase 152's close commit). No divergence, no push needed — the plan's push step was confirmed as a genuine no-op, not skipped blindly.
- `git ls-remote origin refs/heads/main` confirmed the remote HEAD SHA matches `git rev-parse HEAD` exactly: `e619de4dc09a56eaaa364b03beb69a62327ff1b6`.
- `gh auth status` confirmed authenticated as `0xD1g5` with `repo` + `workflow` scopes.
- `gh run list --branch main` showed Python CI (databaseId `31767014704`) was still `in_progress` on that SHA at the time of the initial check — `gh run watch` was used (not just polled) to wait for real completion rather than trusting an earlier cached snapshot.
- Final confirmed state — all three required workflows `success` on SHA `e619de4dc09a56eaaa364b03beb69a62327ff1b6`:
  - **Python CI** — https://github.com/0xD1g5/QU.I.R.K/actions/runs/31767014704 — `success` (includes Linux Full Suite, Windows Sensor Build, Windows Sensor E2E sub-jobs, all green)
  - **Dashboard Quality** — https://github.com/0xD1g5/QU.I.R.K/actions/runs/31767014538 — `success`
  - **Python Staleness Gate** — https://github.com/0xD1g5/QU.I.R.K/actions/runs/31767014460 — `success`

### Task 2: release.yml workflow_dispatch dry-run

- `gh workflow run release.yml --ref main` triggered a new run: https://github.com/0xD1g5/QU.I.R.K/actions/runs/31768252469 (databaseId `31768252469`).
- Confirmed live via `gh run list --workflow release.yml --json event`: `"event": "workflow_dispatch"` — not `push` — proving the trigger type by direct query, not assumption.
- `gh run watch 31768252469 --exit-status` confirmed the run concluded `success`:
  - `Build wheel + sdist` job — `success`
  - `Build Windows zip + attach GitHub Release asset` job — `success`, including the `CI self-test — ephemeral cert signing round-trip` step (`success`)
  - `Publish to PyPI (Trusted Publishers + Sigstore)` job — `skipped`
  - `Attach zip to GitHub Release` step (within the Windows-zip job) — `skipped`
- `gh run view 31768252469 --log | grep SELF_TEST_SIGNING` captured the literal required line:
  ```
  SELF_TEST_SIGNING: OK — signtool wiring verified end-to-end
  ```
- `gh api repos/0xD1g5/QU.I.R.K/actions/runs/31768252469/artifacts` confirmed the artifact `quirk-windows-dry-run` (57,456,241 bytes) was uploaded — the inspectable dry-run zip, never attached to a GitHub Release, as designed.
- Zero-side-effect guarantee proven live (not by YAML inspection alone): both `Publish to PyPI` and `Attach zip to GitHub Release` are confirmed `skipped` in the actual run's job/step data, matching `release.yml`'s `github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')` gate (Phase 148, D-06).

## Deviations from Plan

None — plan executed exactly as written. Both tasks' preconditions, actions, and acceptance criteria were met without any auto-fixes, blockers, or architectural questions.

## Known Stubs

None — this plan created no code or UI artifacts.

## Self-Check: PASSED

- `git rev-parse HEAD` (`e619de4dc09a56eaaa364b03beb69a62327ff1b6`) matches `git ls-remote origin refs/heads/main` — confirmed live above.
- Run `31767014704` (Python CI): `gh run list --branch main` — FOUND, `conclusion: success`.
- Run `31767014538` (Dashboard Quality): FOUND, `conclusion: success`.
- Run `31767014460` (Python Staleness Gate): FOUND, `conclusion: success`.
- Run `31768252469` (release.yml dry-run): FOUND, `conclusion: success`, `event: workflow_dispatch`.
- `SELF_TEST_SIGNING: OK — signtool wiring verified end-to-end` line: FOUND in run `31768252469`'s log.
- No files created or modified (`files_modified: []`) — `git status --porcelain` confirmed clean working tree throughout.
