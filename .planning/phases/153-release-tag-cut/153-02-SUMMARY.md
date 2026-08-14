---
phase: 153-release-tag-cut
plan: 02
subsystem: release
tags: [versioning, pyproject, release-notes, docs]

# Dependency graph
requires:
  - phase: 153-01
    provides: pre-tag dry-run / release-pipeline verification that this plan's version bump follows
provides:
  - "pyproject.toml [project.version] bumped to 5.12.0 (sole canonical source)"
  - "Six-surface version parity verified green via tests/test_version.py"
  - "README.md heading and docs/UAT-SERIES.md header/UAT-1-02 manual literals updated to 5.12.0"
  - "docs/release-notes/5.12.0.md written, documenting the v5.11.0 Windows-asset gap closure"
affects: [153-03]

# Tech tracking
tech-stack:
  added: []
  patterns: ["pyproject.toml as sole canonical version SoT; manual literal surfaces (README heading, UAT-SERIES header/UAT-1-02) require explicit separate edits per the project's Version bump doc checklist"]

key-files:
  created: [docs/release-notes/5.12.0.md]
  modified: [pyproject.toml, README.md, docs/UAT-SERIES.md]

key-decisions:
  - "No towncrier invocation and no CHANGELOG.md edit — towncrier is not installed and changelog.d/ has no pending fragments, matching the v5.9-v5.11 precedent of a standalone docs/release-notes/X.Y.Z.md file instead."
  - "docs/release-notes/5.12.0.md's Known Issues section explicitly states the v5.11.0 Windows-asset gap is now closed (citing RELEASE-01) rather than a bare 'None', per the plan's interface guidance."

patterns-established: []

requirements-completed: [RELEASE-01]

# Metrics
duration: 15min
completed: 2026-08-14
---

# Phase 153 Plan 02: Version Bump to 5.12.0 Summary

**Bumped the canonical `pyproject.toml` version to 5.12.0, verified all six derived version surfaces stay in parity via `tests/test_version.py`, updated the three manual (non-derived) version literals in README.md and docs/UAT-SERIES.md, and wrote `docs/release-notes/5.12.0.md` documenting the v5.11.0 Windows-asset gap closure — all landed in one explicit-file-list commit ahead of the Plan 153-03 tag-cut checkpoint.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-14T03:46:00Z (approx)
- **Completed:** 2026-08-14T04:01:26Z
- **Tasks:** 2 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `pyproject.toml [project.version]` reads `5.12.0`; all 6 `tests/test_version.py` assertions pass green, confirming `quirk.__version__`, `PLATFORM_VERSION` (cbom builder + reports writer), and `IntelligenceCfg().intelligence_version` all derive correctly.
- Updated the three manual version-string literals that do NOT derive from `pyproject.toml`: README.md's H1 heading, docs/UAT-SERIES.md's header block (`**Version:**` + a new `**Last Updated:**` clause prepended, prior "Earlier:" history left intact), and UAT-1-02's Pass Criteria / Notes.
- Wrote `docs/release-notes/5.12.0.md` following the exact section structure of `5.11.0.md` (title / Released / Milestone / What's New per-phase bullets for Phases 148-153 / Known Issues / Upgrade Guidance / See Also / closing attribution), with the Known Issues section explicitly stating the v5.11.0 Windows-asset gap is now closed and citing RELEASE-01.
- Landed everything in a single commit `chore(release): v5.12.0` touching exactly the four expected files, verified via `git log -1 --name-only`.

## Task Commits

Both tasks landed in one combined commit, per this plan's explicit instruction (Task 2's `<action>` step 5 specifies a single commit covering all four files, and the plan's own acceptance criteria checks for exactly that commit) — this overrides the generic one-commit-per-task default:

1. **Task 1: Bump pyproject.toml and verify six-surface version parity** — verified locally (6/6 `tests/test_version.py` passing) before staging; the `pyproject.toml` edit was folded into the combined commit below rather than committed standalone, to satisfy the plan's Task 2 acceptance criteria that the single release commit include `pyproject.toml`.
2. **Task 2: Update manual version literals, write release notes, and commit** — `4e8e74d` (`chore(release): v5.12.0`), touching `README.md`, `docs/UAT-SERIES.md`, `docs/release-notes/5.12.0.md`, `pyproject.toml`.

_Note: An initial standalone commit for Task 1 (`0a9fd47`) was created, then reverted via `git reset --soft HEAD~1` once it became clear the plan requires all four files in one commit — no history rewrite occurred since it had not been pushed anywhere; see Deviations below._

## Files Created/Modified
- `pyproject.toml` — `[project.version]` bumped `5.11.0` → `5.12.0` (sole canonical edit)
- `README.md` — H1 heading `# QU.I.R.K. — v5.11.0` → `# QU.I.R.K. — v5.12.0`
- `docs/UAT-SERIES.md` — header `**Version:**`/`**Last Updated:**` updated with a new v5.12 milestone-close clause (prior "Earlier:" narrative preserved); UAT-1-02 Pass Criteria and Notes updated to `v5.12.0`
- `docs/release-notes/5.12.0.md` — new file, full v5.12.0 release notes matching the `5.11.0.md` structure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking, self-corrected] Task 1 committed standalone before recognizing the plan requires a single combined commit**
- **Found during:** Between Task 1 and Task 2
- **Issue:** The generic `task_commit_protocol` calls for one commit per task, so Task 1's `pyproject.toml` edit was initially committed on its own (`0a9fd47`). Re-reading Task 2's `<action>` (explicit `git add pyproject.toml README.md docs/UAT-SERIES.md docs/release-notes/5.12.0.md` then one `git commit`) and its acceptance criteria (checks that the *most recent* commit touches exactly those four files) showed this plan deliberately overrides the generic per-task-commit default with a single combined release commit.
- **Fix:** `git reset --soft HEAD~1` to un-commit `0a9fd47` while keeping `pyproject.toml`'s change staged/working-tree intact, then proceeded with Task 2's edits and landed everything in one commit `4e8e74d` as the plan specifies.
- **Files affected:** none beyond the version-bump files already listed above (git history only)
- **Commit:** `4e8e74d`

None of Rules 1/2/4 applied — no bugs found, no missing critical functionality, no architectural changes needed. This was purely a commit-sequencing correction to honor the plan's explicit single-commit instruction over the generic default.

## Known Stubs

None. This plan touches only version-string literals and static release-notes prose; no UI/data-flow stubs introduced.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes. Consistent with the plan's `<threat_model>` (Tampering via `git add -A` mitigated by explicit file lists in both commits actually made; Repudiation via version-string drift mitigated by the green `tests/test_version.py` run and the `grep` sweep for stale `5.11.0` literals, both confirmed above).

## Next Steps
- Plan 153-03 (not part of this plan's scope) cuts the actual `v5.12.0` git tag in the foreground with explicit human confirmation, then verifies the live tagged CI run (RELEASE-01) end-to-end, including the repaired Windows-asset signing self-test.

## Self-Check: PASSED
- FOUND: `pyproject.toml` (version 5.12.0 confirmed via diff)
- FOUND: `README.md`
- FOUND: `docs/UAT-SERIES.md`
- FOUND: `docs/release-notes/5.12.0.md`
- FOUND commit: `4e8e74d` (`git log --oneline --all | grep 4e8e74d` → present)
