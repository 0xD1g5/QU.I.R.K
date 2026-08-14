---
phase: 148-release-pipeline-repair-windows-asset-backfill
plan: 04
subsystem: release-pipeline
tags: [github-actions, ci-cd, release, live-verification, github-release]

dependency-graph:
  requires:
    - "148-01 (release.yml workflow_dispatch dry-run mechanism + event+ref guards)"
    - "148-02 (release-tag-hygiene.yml scheduled guard + seeded baseline)"
    - "148-03 (v5.11.0 release-notes + GitHub Release body files)"
  provides:
    - "Live-run proof (not code inspection) that the release dry-run mechanism works end-to-end, including the 1a6effc signing self-test repair"
    - "Live-run proof that the tag-hygiene guard reports per-tag status against real GitHub state"
    - "A published v5.11.0 GitHub Release carrying the PyPI-only disposition with zero assets"
  affects:
    - "153 (release tag cut — this plan is the first live proof the mechanisms 148-01/02 built actually execute)"

tech-stack:
  added: []
  patterns:
    - "Live-run evidence pattern: run IDs + URLs + per-job/per-step conclusion tables recorded in a phase EVIDENCE.md, not asserted from code inspection alone"

key-files:
  created:
    - .planning/phases/148-release-pipeline-repair-windows-asset-backfill/148-04-EVIDENCE.md
  modified: []

decisions:
  - "Task 1 checkpoint: presented outbound diff (11 commits, 14 files, 1311 insertions) and confirmed local suite green (51 passed) before requesting approval; pushed only after explicit orchestrator-relayed 'approved'"
  - "D-01/D-02/D-03/D-04 (D-148-RELEASE04) executed exactly as specified: gh release create v5.11.0 with --latest=false and --verify-tag, zero file arguments, notes body from 148-03's file"
  - "No Release objects created for v5.9 or v5.10.0 — explicitly out of scope per plan Task 3 step 7"

requirements-completed: [RELEASE-02, RELEASE-03, RELEASE-04]

metrics:
  duration: "40min"
  completed: "2026-08-11"
---

# Phase 148 Plan 04: Live-Run Proof + v5.11.0 Release Disposition Summary

Pushed the phase's local commits to `origin/main` after explicit human approval at a blocking
checkpoint, then proved the repaired release pipeline with two real GitHub Actions runs (not code
inspection) and published a bare, zero-asset `v5.11.0` GitHub Release carrying the PyPI-only
disposition.

## What Was Built

### Task 1 — Push phase 148 workflow changes to origin/main (checkpoint:human-action)

Presented the outbound diff (`git log --oneline origin/main..main`: 11 commits across 148-01/02/03;
`git diff --stat`: 14 files, 1311 insertions/30 deletions) and confirmed the local target test
suite green (`tests/test_release_workflow_dryrun_guards.py`,
`tests/test_release_tag_hygiene.py`, `tests/test_release_notes_5_11_0.py` — 51 passed) to the
orchestrator, which relayed the request to the human user. Received explicit "approved" before
taking any push action.

On approval: `git push origin main` succeeded (`2add633..60955b8 main -> main`); confirmed
`git ls-remote origin refs/heads/main` (`60955b886cae89c1ca6bfb293636c325557f8944`) equals
`git rev-parse HEAD`. Confirmed no `v5.12` tag was pushed alongside
(`git ls-remote --tags origin | grep -c 'refs/tags/v5.12'` → `0`). No repo files were modified by
this task — no commit was made for it.

### Task 2 — Dispatch and verify the release dry-run and the tag-hygiene guard

Dispatched `release.yml` via `gh workflow run release.yml --ref main` (run `31524058796`). Waited
for full completion via `gh run watch --exit-status` (windows-package job took 3m43s). Confirmed:

- Overall conclusion `success`.
- `Build wheel + sdist` → `success`; `Publish to PyPI (Trusted Publishers + Sigstore)` → `skipped`
  (the corrected D-06 event+ref guard held under a real dispatch — the PyPI job never ran).
- `Build Windows zip + attach GitHub Release asset` (windows-package) → `success`; inside it,
  `CI self-test — ephemeral cert signing round-trip` → `success` with log line
  `SELF_TEST_SIGNING: OK — signtool wiring verified end-to-end` (the D-08 live proof of the
  `1a6effc` repair); `Upload dry-run zip artifact` → `success`; `Attach zip to GitHub Release` →
  `skipped`.
- Artifact `quirk-windows-dry-run` (57,330,823 bytes) present via
  `gh api .../actions/runs/31524058796/artifacts`.
- Zero side effects: `gh release list` output byte-identical before/after the dispatch; PyPI
  `quirk-scanner` version list unchanged.

Dispatched `release-tag-hygiene.yml` via `gh workflow run` (run `31524420671`). Completed green in
9s. Reproduced the job summary content (script is a pure git-tag/gh-API cross-reference with no
other time-dependent behavior) and confirmed the EXEMPT section names `v5.9` (malformed
two-component tag), `v5.10.0` (never pushed), and `v5.11.0` (PyPI-only disposition) with their
specific reasons, plus 14 OK/backed tags, and zero flagged tags.

Wrote `.planning/phases/148-release-pipeline-repair-windows-asset-backfill/148-04-EVIDENCE.md`
recording both run IDs/URLs, full per-job/per-step conclusion tables, the self-test log line, the
artifact proof, the before/after Release-list and PyPI comparisons, and the tag-hygiene summary
text, each mapped to SC-1/SC-2/SC-3.

Commit: `b1a470a`

### Task 3 — Create the bare v5.11.0 GitHub Release carrying the disposition

Confirmed pre-state: `gh release view v5.11.0` → "release not found"; `git ls-remote --tags origin
refs/tags/v5.11.0` → resolved SHA; `docs/release-notes/5.11.0.md` present on `origin/main` via the
Contents API (so the release body's link resolves).

Created the Release: `gh release create v5.11.0 --title "v5.11.0 — PyPI-only release (no Windows
asset)" --notes-file docs/release-notes/5.11.0-github-release-body.md --latest=false
--verify-tag`. No file arguments passed — zero assets is the point (D-02).

Verified: `assets` length `0`; body contains `PyPI-only`, `1a6effc`, `v5.12.0`, and a link to
`docs/release-notes/5.11.0.md`; `isDraft` `false`, `isPrerelease` `false`; `tagName` `v5.11.0`;
`--latest=false` used so `v5.8.0` is not displaced as GitHub's "Latest" designation.
`gh release list` now includes `v5.11.0` and still excludes `v5.9`/`v5.10.0` — no Release objects
were fabricated for either, per the plan's explicit prohibition.

Appended the Release URL, verification JSON, and body excerpt to `148-04-EVIDENCE.md`, mapped to
SC-4.

Commit: `33a1085`

## Deviations from Plan

### Auto-fixed Issues

None — Rules 1-3 were not triggered; every command in the plan's `<action>` blocks executed as
written and produced the expected output on the first attempt.

Note: `.planning/` is gitignored in this repo (PUBREPO-PLANNING-EXCL, Phase 120). Per the existing
pattern established in 148-03 (where `148-03-SUMMARY.md` was force-added), `148-04-EVIDENCE.md`
and this `148-04-SUMMARY.md` were staged with `git add -f` for their respective commits. This is
not a deviation from plan intent — the plan's own frontmatter explicitly lists
`148-04-EVIDENCE.md` under `files_modified`, and the file needed to be committed for the phase's
artifact trail to be reproducible from git history.

## Known Stubs

None — this plan performs live GitHub Actions dispatches and a Release-object creation; no
application code with data-flow stubs was touched.

## Threat Flags

None — this plan executes exactly the mitigations specified in the phase's own `<threat_model>`
(T-148-16 through T-148-21, T-148-SC), each verified with a positive live-run assertion rather
than an assumption: T-148-16/17 (dry-run leaves publish/Release untouched — confirmed via
byte-identical before/after comparisons), T-148-18 (only `v5.11.0` given a Release object, bound
via `--verify-tag`, no `v5.9`/`v5.10.0` fabrication), T-148-19 (run IDs/URLs recorded in
EVIDENCE.md), T-148-20 (Task 1 checkpoint gated the push on explicit approval), T-148-21 (no
baseline manipulation — the tag-hygiene run was green because 148-02's seeding was already
correct, not because this plan suppressed a finding).

## Self-Check: PASSED

- FOUND: `.planning/phases/148-release-pipeline-repair-windows-asset-backfill/148-04-EVIDENCE.md`
- FOUND commit `b1a470a` (`git log --oneline --all | grep b1a470a`)
- FOUND commit `33a1085` (`git log --oneline --all | grep 33a1085`)
- FOUND live run `31524058796` — conclusion `success`
  (`gh run view 31524058796 --json conclusion -q .conclusion`)
- FOUND live run `31524420671` — conclusion `success`
- FOUND GitHub Release `v5.11.0` — `assets: 0`, `isDraft: false`
  (`gh release view v5.11.0 --json assets,isDraft`)
