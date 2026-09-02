---
phase: 177-release-toolchain-repair
plan: 07
subsystem: release
tags: [release, ci-gate, dry-run, a11y, human-checkpoint, tag-handoff]

# Dependency graph
requires:
  - phase: 177-06
    provides: full-suite phase gate + pre-tag readiness table
provides:
  - "main pushed to origin (334 commits: full v5.16/v5.17/Phase 177 unpublished backlog)"
  - "workflow_dispatch dry-run proven empirically no-publish (run 33641321488)"
  - "three genuine a11y baseline environment-mismatch bugs found and fixed (not phase regressions)"
  - "verbatim v5.18.0 tag-push handoff block, printed and awaiting the user"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "prove CI no-publish guards from the actual run's job/step conclusions, not by citing the guard test alone"
    - "a11y baselines generated on one OS but enforced on another can diverge on overflow-triggered rules; take the CI round-trip rather than guess a count"

key-files:
  created:
    - .planning/phases/177-release-toolchain-repair/177-07-SUMMARY.md
    - .planning/todos/pending/a11y-baseline-environment-mismatch.md (gitignored, filesystem-only)
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/todos/pending/a11y-route-coverage-gap.md (gitignored, filesystem-only, cross-reference appended)
    - src/dashboard/tests/a11y/baseline-data-at-rest-default.json
    - src/dashboard/tests/a11y/baseline-data-at-rest-empty.json
    - src/dashboard/tests/a11y/baseline-data-at-rest-loading.json
    - src/dashboard/tests/a11y/ACCEPTED-VIOLATIONS.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-177-Release-Toolchain-Repair.md (Obsidian vault)

key-decisions:
  - "Gate 1 (push main + dispatch dry-run) presented with full evidence (334-commit log, 177-file diffstat, 177-06's full-suite tally and gate table) and explicitly approved by the user before either command ran"
  - "Dispatch dry-run's no-publish property proven empirically from gh run view's job/step conclusions (publish job: skipped, Attach-zip step: skipped, event: workflow_dispatch), not by citing tests/test_release_workflow_dryrun_guards.py alone"
  - "Remote CI's first-ever execution against the pushed v5.16/v5.17/Phase-177 content surfaced 3 genuine a11y baseline gaps on /data-at-rest (scrollable-region-focusable: default 1->2, empty 0->2, loading 0->2), none of them product regressions -- root cause is macOS-generated baselines (2026-08-27) enforced against a Linux CI runner that had never executed this content until this push"
  - "Two blocking halts were raised and resolved via coordinator decision before proceeding, per this plan's autonomous:false / no-product-code-change scope: (1) initial data-at-rest-default halt, (2) the empty/loading variant's baseline was 0 (never observed), so its real count was obtained via an actual CI round-trip rather than guessed, per explicit instruction to prefer a round-trip over fabricating an observed-truth value"
  - "RELEASE-01 hand-corrected from a checkbox still reading [ ] (with a 'closes on ship' table note) to [x] complete -- both root-cause halves (177-01 repo residue, 177-03 machine-wide orphan) are fixed and evidenced independent of RELEASE-02/03's ship status, which remain open"
  - "Task 3 (tag handoff) reached with all preconditions green: Dashboard Quality all 3 fixture variants, Python Staleness Gate, all 4 Windows jobs, and Linux Full Suite at its documented DEFER-172-01-only baseline, re-verified at the exact commit (9fddd4d9) that will be tagged"

requirements-completed: [RELEASE-01]

# Metrics
duration: ~140min (includes ~55min of remote CI wait time across 5 push cycles)
completed: 2026-09-02
---

# Phase 177 Plan 07: Dry-Run Rehearsal + Tag Handoff Summary

**`main` pushed for the first time in this milestone chain (334 commits), the `workflow_dispatch` release rehearsal proved empirically no-publish, three genuine (pre-existing, environment-mismatch) a11y baseline bugs surfaced by remote CI's first-ever run were found and fixed under explicit human direction, and the verbatim `v5.18.0` tag-push handoff is now printed and waiting on the user — the release has NOT shipped.**

## Performance

- **Duration:** ~140 min wall-clock (Task 1 checkpoint wait not counted; Task 2/2b/2c CI round-trips ~55 min of that)
- **Started:** 2026-09-02 (Task 1 checkpoint presented)
- **Completed:** 2026-09-02 (Task 3 handoff printed, this SUMMARY written)
- **Tasks:** 3 planned; Task 1 approved, Task 2 executed (with two coordinator-directed deviation cycles), Task 3 handoff presented
- **Files modified:** 4 tracked (`.planning/REQUIREMENTS.md`, 3 `src/dashboard/tests/a11y/*.json` baselines + regenerated `ACCEPTED-VIOLATIONS.md`), plus 2 gitignored `.planning/todos/` files and 1 Obsidian vault note

## Accomplishments

### Task 1 — Gate 1: presented and approved

Presented, verbatim, the full commit list (`git log --oneline origin/main..HEAD`, 334 commits spanning the entirety of v5.16, v5.17, and Phase 177 — none of it had ever reached `origin`), the 177-file diffstat (`+16915/-4200`), 177-06's full-suite tally (`1 failed, 3780 passed`, sole failure `DEFER-172-01`), and 177-06's pre-tag gate readiness table. The user typed "approved" for both `git push origin main` and `gh workflow run release.yml --ref main`.

### Task 2 — push, dispatch, empirical no-publish proof, and two deviation cycles

1. **`git push origin main`** — fast-forward, `939a7ca6..ff52bceb`, `git rev-list --count origin/main..HEAD` → `0`.
2. **`gh workflow run release.yml --ref main`** — run `33641321488`, watched to completion. Proven empirically from `gh run view --json jobs`: `event: workflow_dispatch`, overall `conclusion: success`, `Publish to PyPI` job `conclusion: skipped`, `Attach zip to GitHub Release` step `conclusion: skipped`; `Build Windows zip` and `Build wheel + sdist` both ran and succeeded. `.venv/bin/pip index versions quirk-scanner` confirmed PyPI's latest published version remained `5.15.0`.
3. **Remote CI watch (the first-ever execution of `python-ci.yml` and `dashboard-quality.yml` against this exact `main` history)** surfaced a genuine `Dashboard Quality` failure: `data-at-rest`'s `scrollable-region-focusable` count (2) exceeded its accepted baseline (1). **Halted per the plan's stop rule** and reported to the coordinator rather than either auto-fixing (out of scope for this `autonomous: false`, no-product-code plan) or silently proceeding over red CI.
4. **Coordinator investigation and decision (deviation cycle 1):** independently confirmed via `git log --since=2026-08-27` that no commit had touched `data-at-rest.tsx`, `table.tsx`, or any `a11y/` fixture since the baseline was authored, and that the page renders four `<Table>` instances sharing the overflow wrapper — concluding this was a render-dependent count, not a regression. Directed: bump `baseline-data-at-rest-default.json`'s count 1→2 with an extended justification, regenerate `ACCEPTED-VIOLATIONS.md`, commit (`cf3b15c1`), push, re-verify.
5. **Re-verification surfaced a second, distinct failure:** the `empty`-fixture variant (a separate baseline file, `baseline-data-at-rest-empty.json`, never previously populated — baseline `0`) failed with the same rule, count `2`. **Halted again** rather than unilaterally expanding the fix beyond what was explicitly approved.
6. **Coordinator investigation and decision (deviation cycle 2):** surveyed all 33 baseline files and found the true root cause — all were generated in one local macOS batch on 2026-08-27, but the gate enforces on Linux CI, and `scrollable-region-focusable` was the only rule appearing in any baseline, appearing in exactly the one file already bumped. Directed fixing both `empty` and `loading` variants, but explicitly: **use real CI-observed counts, take the round-trip rather than guess.** `empty`'s count (2) was already known from the failing run (`33644730813`); `loading` had never executed (both prior runs failed before reaching it). Committed `empty`'s fix alone (`6f9efd27`), pushed, and captured `loading`'s real count (2) from the resulting CI run (`33645368151`) before writing `loading`'s fix (`724facf3`).
7. **Full re-verification:** pushed `724facf3`, confirmed `Dashboard Quality` green across all three fixture steps (happy/empty/loading), `Python Staleness Gate` green, all 4 `Python CI` Windows jobs green, and `Linux Full Suite` red exactly and only on `DEFER-172-01` (`1 failed, 3763 passed`, byte-identical failing-node set to the documented baseline).
8. **RELEASE-01 correction:** hand-edited `.planning/REQUIREMENTS.md` — checkbox flipped `[ ]`→`[x]`, table row corrected from "closes on ship" framing to "Complete... independent of RELEASE-02/03 shipping" — since both root-cause halves (177-01, 177-03) are fixed and evidenced regardless of release-ship status. Committed (`9fddd4d9`), pushed, and **re-verified remote CI one final time at this exact commit** (the one that will be tagged): `Dashboard Quality` all 3 variants green, `Python Staleness Gate` green, all 4 Windows jobs green, `Linux Full Suite` red only on `DEFER-172-01`.
9. Logged a follow-up item (`a11y-baseline-environment-mismatch.md`, gitignored `.planning/todos/pending/`) documenting the environment-mismatch root cause, that 31 of 33 baselines have never been checked against a Linux render, and cross-referencing the existing `a11y-route-coverage-gap.md` item for future joint triage. Did **not** regenerate all 33 baselines or touch `components/ui/table.tsx` — both explicitly out of scope, deferred to a dedicated frontend-a11y phase.
10. Updated the Obsidian phase note (`Phase-177-Release-Toolchain-Repair.md`) with Plan 177-06's and 177-07's progress, leaving `status: active` — the phase is not complete until the tag ships.

### Task 3 — tag handoff printed (see below); Claude created no tag

## Files Created/Modified

- `.planning/phases/177-release-toolchain-repair/177-07-SUMMARY.md` — this summary
- `.planning/REQUIREMENTS.md` — RELEASE-01 marked complete (commit `9fddd4d9`)
- `.planning/todos/pending/a11y-baseline-environment-mismatch.md` — new follow-up item (gitignored, filesystem-only)
- `.planning/todos/pending/a11y-route-coverage-gap.md` — cross-reference appended (gitignored, filesystem-only)
- `src/dashboard/tests/a11y/baseline-data-at-rest-default.json` — count 1→2 (commit `cf3b15c1`)
- `src/dashboard/tests/a11y/baseline-data-at-rest-empty.json` — count 0→2 (commit `6f9efd27`)
- `src/dashboard/tests/a11y/baseline-data-at-rest-loading.json` — count 0→2 (commit `724facf3`)
- `src/dashboard/tests/a11y/ACCEPTED-VIOLATIONS.md` — regenerated from the default-variant baseline (part of commit `cf3b15c1`)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-177-Release-Toolchain-Repair.md` — Obsidian vault note updated, `status: active` preserved

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 2 (deviation) | `cf3b15c1` | fix(177-07): bump data-at-rest a11y baseline to 2 (render-dependent count, not a regression) |
| 2 (deviation) | `6f9efd27` | fix(177-07): bump data-at-rest empty a11y baseline (macOS-generated, Linux-enforced) |
| 2 (deviation) | `724facf3` | fix(177-07): bump data-at-rest loading a11y baseline (macOS-generated, Linux-enforced) |
| 2 (RELEASE-01) | `9fddd4d9` | docs(177-07): mark RELEASE-01 complete — both root-cause halves fixed and evidenced |

`main` itself was pushed (fast-forward `939a7ca6..9fddd4d9` across the session) rather than authored by this plan — the 334 pre-existing commits it carries belong to Plans 177-01 through 177-06 and the entirety of v5.16/v5.17.

## Deviations from Plan

### Auto-fixed / coordinator-directed fixes (not Rule 1-3 autonomous — this plan is `autonomous: false`; both cycles were explicitly directed by the coordinator after a halt-and-report)

**1. [Coordinator-directed, deviation cycle 1] `data-at-rest` default-variant a11y baseline was stale (macOS vs. Linux render)**
- **Found during:** Task 2, first remote `Dashboard Quality` run (`33641330619`) — first-ever execution of this gate against the pushed content.
- **Issue:** `scrollable-region-focusable` count observed as 2, baseline accepted only 1.
- **Fix:** Bumped `baseline-data-at-rest-default.json` count 1→2 with an extended justification recording the environment/render-dependence finding; regenerated `ACCEPTED-VIOLATIONS.md`.
- **Files modified:** `src/dashboard/tests/a11y/baseline-data-at-rest-default.json`, `src/dashboard/tests/a11y/ACCEPTED-VIOLATIONS.md`.
- **Commit:** `cf3b15c1`.

**2. [Coordinator-directed, deviation cycle 2] `data-at-rest` empty/loading fixture baselines had never been checked against Linux at all**
- **Found during:** Task 2 re-verification, second (`33644730813`) and third (`33645368151`) remote `Dashboard Quality` runs.
- **Issue:** Both `empty` and `loading` fixture-variant baselines were `0` (never observed) but Linux CI reported `2` for the same rule on the same route.
- **Fix:** Bumped both baselines to their real, CI-confirmed counts (2 each) with justifications recording the true root cause — all 33 baselines were macOS-generated in one 2026-08-27 batch, the gate enforces on Linux, and this was that gate's first-ever execution against this content. `loading`'s count was obtained from an actual CI run rather than assumed equal to `empty`'s.
- **Files modified:** `src/dashboard/tests/a11y/baseline-data-at-rest-empty.json`, `src/dashboard/tests/a11y/baseline-data-at-rest-loading.json`.
- **Commits:** `6f9efd27` (empty), `724facf3` (loading).

**3. [Rule 2-adjacent, coordinator-directed] RELEASE-01 requirement row was stale**
- **Found during:** Task 3 preparation, per explicit coordinator instruction to correct it if evidence supported it.
- **Issue:** Checkbox read `[ ]` and the table row said "closes on ship" even though both root-cause halves (177-01, 177-03) were already fixed and evidenced.
- **Fix:** Checkbox flipped to `[x]`; table row rewritten to state completion is independent of RELEASE-02/03's ship status.
- **Files modified:** `.planning/REQUIREMENTS.md`.
- **Commit:** `9fddd4d9`.

No product code (`quirk/`, `run_scan.py`) was touched. No autonomous Rule 1-3 fixes were applied without a coordinator halt-and-report cycle first, consistent with this plan's `autonomous: false` gating.

## Issues Encountered

- Two consecutive remote-CI red states after the initial fix, each requiring a halt-and-report cycle rather than silent iteration — this is the correct behavior per the plan's stop rule, not a failure. Both were resolved via explicit coordinator investigation and direction before any further baseline edit was made.
- `Linux Full Suite`'s job-level `conclusion: failure` on every push is expected and by design (the workflow does not soft-fail the known `DEFER-172-01` node); this is called out explicitly in the Task 3 handoff below so the user is not alarmed by it.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes. The a11y baseline edits are test-fixture data, not application surface.

## User Setup Required

**The v5.18.0 tag push — see the handoff block below.** This is the single remaining action, and it belongs to the user per this plan's locked decision D-04.

## Next Phase Readiness

`main` is pushed, dry-run proven clean, `Dashboard Quality`/`Python Staleness Gate`/all 4 Windows jobs green, `Linux Full Suite` at its documented single-failure baseline — all re-verified at the exact commit (`9fddd4d9`) about to be tagged. `git tag --list 'v5.18*'` is empty locally and on `origin`. Task 3's handoff is printed in this session's final response. Once the user pushes the tag and reports back the outcome, a continuation of this plan (or a fresh execution) must: re-execute UAT-177-01/-02/-03 with real evidence, mark RELEASE-02/RELEASE-03 complete by hand, and flip the Obsidian phase note to `status: complete`. Series 177 and RELEASE-02/03 remain honestly open at the end of this plan — **the release is STAGED and handed off, not shipped.**

---
*Phase: 177-release-toolchain-repair*
*Completed: 2026-09-02*
