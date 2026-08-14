---
phase: 150-test-suite-green-baseline-ci-gate
plan: "07"
subsystem: docs
tags: [docs, requirements, roadmap, uat, ledger, obsidian]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "05"
    provides: "D-12/D-13 chaos-lab cert generation (documented in this plan's ledger addendum)"
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "06"
    provides: "35 ci_extras_gap/gitignored_planning_dir skip guards (documented in this plan's ledger addendum)"
provides: "accurate public ledger, honest SUITE-02/03 requirements status, correct roadmap plan count, UAT-150 test cases"
affects: [150-08, 150-09, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - docs/test-triage-149.md
    - docs/UAT-SERIES.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "ROADMAP.md's Phase 150 header count corrected to 9 plans (not the plan's literal '6 plans' instruction) — the file already lists all 9 plan entries (150-01 through 150-09, added by earlier plans in this phase), and the plan's own instruction text was internally inconsistent (asked to both 'change to 6 plans' and 'add 150-04 through 150-09' onto an existing 3, which is 9, not 6). Matching the actual 9-entry list is the accurate outcome this task exists to produce."
  - "UAT-150-01/02/03 all use human-led evidence-artifact pass criteria (pointing at 150-CI-EVIDENCE.md) rather than hardcoding passed/skipped/xfailed counts, since those numbers drift release to release — matches the plan's explicit instruction and the Phase 56.1 CI-workflow analog's structure."

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-08-12
---

# Phase 150 Plan 07: Ledger Addendum + Honest Requirements/Roadmap + UAT-150 Cases Summary

**Brought the written record into line with what Plans 150-04 through 150-06 actually changed before the phase's evidence-gathering re-run: appended a Phase 150 CI-parity addendum to `docs/test-triage-149.md` documenting all 35 new skips (31 `ci_extras_gap` + 4 `gitignored_planning_dir`) plus the D-16 deletion, D-17 disposition, and D-12/D-13 source-level fix; corrected `.planning/REQUIREMENTS.md` so SUITE-02/SUITE-03 no longer claim `Complete` while the real CI baseline is red; fixed `.planning/ROADMAP.md`'s stale plan-count header; and added three human-led UAT-150 test cases to `docs/UAT-SERIES.md` with a synced Obsidian vault copy.**

## What Was Built

### Task 1 — Phase 150 CI-parity addendum to the disposition ledger

Appended a new `## Phase 150 CI-Parity Addendum` section to `docs/test-triage-149.md`,
positioned immediately after the existing `## Reconciliation` section (no Phase 149 cluster
table or Reconciliation content was touched — confirmed via `git diff --stat`, additions only).

The addendum covers, in the document's existing table voice:

- **Why the addendum exists** — Phase 149's ledger and Plan 150-02's local baseline were
  produced in sandboxes carrying `identity`/`hw`/`api` extras; CI's `.[all]`-only install
  excludes all three by design, so 31 tests hard-crashed on real CI instead of skipping. Cites
  the real run URL (`31598809033`) and its exact result line (38 failed, 3074 passed, 46
  skipped, 73 xfailed, 7 xpassed).
- **31-row `ci_extras_gap` table** — one row per guarded test, with file, test name, extras
  group (`hw`/`identity`/`api`), and missing package. Test names were recovered by locating the
  enclosing `def test_...`/class-method for each `tests/skip_registry.py` line reference (the
  registry itself only records line numbers, not test names).
- **4-row `gitignored_planning_dir` table** — the `.planning/audit-2026-05-08/AUDIT-TASKS.md`
  existence-check guards, naming PUBREPO-01 as the reason.
- **D-16 deletion note** — `test_package_manifest_version_is_4_1_0` deleted, not quarantined,
  with the one-line distribution-rename reason.
- **D-17 disposition note** — pointer to `150-D17-INVESTIGATION.md`, recorded as a
  test-construction-defect disposition reached *before* the real CI run (not deferred to it).
- **D-12/D-13 note** — the `email`/`grpc-tls` chaos-lab cert failure was fixed at the source in
  `lab.sh`, not skipped.

Row counts were verified to match `tests/skip_registry.py`'s Phase 150 block exactly: 31
`ci_extras_gap` table rows, 4 `gitignored_planning_dir` table rows.

### Task 2 — Corrected stale SUITE-02/SUITE-03 status and the ROADMAP plan list

`.planning/REQUIREMENTS.md`: flipped SUITE-02 and SUITE-03 checkboxes from `- [x]` to `- [ ]`,
changed both traceability rows from `Complete` to `In Progress`, and added a status note under
the Test Signal Integrity section recording the 2026-08-12 real-CI failure (38 failed,
run `31598809033`) and that remediation is completing. SUITE-01 and all other requirement rows
were left byte-unchanged.

`.planning/ROADMAP.md`'s Phase 150 block: found the plan checklist already listed all 9 plans
(150-01 through 150-09, with 150-01/02/03/04/05/06 checked `[x]` and 150-07/08/09 unchecked) —
this had already been populated by an earlier planning step, contrary to the plan's interfaces
section (frozen before that update landed). The only stale element was the summary header,
which still read `**Plans**: 6 plans` against an actual 9-entry list. Corrected the header to
`**Plans**: 9 plans` to match ground truth — see Deviations below. The phase Goal and all four
Success Criteria were left byte-unchanged (confirmed via `git diff`).

### Task 3 — UAT-150 test cases + Obsidian vault sync

Appended `## Series 150: Test Suite Green Baseline + CI Gate (Phase 150 — v5.12)` to
`docs/UAT-SERIES.md`, following the most recent section's (`Series 149`) formatting, with three
cases:

- **UAT-150-01** (SUITE-02) — the `Linux Full Suite` job concludes `success` on a real run of
  `main`; pass criteria point at the `150-CI-EVIDENCE.md` artifact and a `0 failed` pytest
  summary line, deliberately not hardcoding passed/skipped/xfailed counts since those drift.
- **UAT-150-02** (SUITE-03) — a deliberately failing test turns the job red on a real PR run,
  the PR closes unmerged, and `ci/smoke-check-150` is deleted from origin.
- **UAT-150-03** (D-12/D-13) — `./lab.sh certs` generates the six `email`/`grpc-tls` cert files
  on a fresh clone and the `email` profile starts without the bind-mount error.

All three `**Result:**` lines are left unfilled/pending (user-led walkthroughs; Result lines are
only flipped by the user, not this executor). Updated the document-wide `**Last Updated:**`
line at line 4 to record the Phase 150 wrap, prepending a new paragraph before the existing
"Earlier: Phase 149 wrap ..." chain (history preserved, not deleted).

Synced to the vault per CLAUDE.md's mandated direct-filesystem-write pattern (file is too large
for CLI `content=`): prepended the standard frontmatter block (`project: QU.I.R.K.`,
`type: reference`, `status: active`, `source: docs/UAT-SERIES.md`, `updated: 2026-08-12`) to the
full `docs/UAT-SERIES.md` content and copied it to
`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`.

## Task Commits

| Task | Commit | Message |
|---|---|---|
| 2 | `9ff98fc` | `docs(150-07): correct stale SUITE-02/03 Complete status and roadmap plan count` |
| 1 | `d287cdc` | `docs(150-07): add Phase 150 CI-parity addendum to the disposition ledger` |
| 3 | `b9af731` | `docs(150-07): update UAT-SERIES.md` |

(Task 2 was committed first in execution order since it was addressed while confirming ground
truth for the ROADMAP plan list before writing the ledger addendum; all three tasks' content
matches the plan's task numbering.)

## Deviations from Plan

**1. [Rule 1 - Bug] ROADMAP.md Phase 150 header corrected to "9 plans", not the plan's literal
"6 plans" instruction.**
- **Found during:** Task 2
- **Issue:** The plan's `<action>` text said "change `**Plans**: 3 plans` to `6 plans`... Add
  150-04 through 150-09 unchecked." But the file's actual current state (already updated by an
  earlier, unlogged planning step before this plan dispatched) shows all 9 plan entries
  (150-01 through 150-09) already listed, with 150-01 through 150-06 checked `[x]`. The plan's
  interfaces section, which described the file as still showing "3 plans... 150-01 through
  150-03 only," was stale relative to this ground truth. Following the literal "6 plans"
  instruction would have made the header claim fewer plans than the list beneath it actually
  contains — exactly the kind of inaccuracy this task exists to eliminate.
- **Fix:** Set the header to `**Plans**: 9 plans`, matching the true count of listed plan
  entries. Did not alter the plan list itself (already correct), the Goal, or the Success
  Criteria.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** `9ff98fc`

No other deviations. All three tasks' documented content (ledger addendum rows, REQUIREMENTS.md
status flip, UAT-150 cases) matches the plan's instructions exactly.

## Issues Encountered

None beyond the ROADMAP header count discrepancy documented above.

## User Setup Required

None.

## Next Phase Readiness

The public record (ledger, requirements, roadmap, UAT series) now accurately reflects the
phase's in-progress state: SUITE-02/SUITE-03 are honestly `In Progress`, all 35 skips from
Plans 150-05/150-06 are documented in the public ledger, and UAT-150-01..03 are in place with
pending `Result:` lines awaiting the live-fire evidence Plans 150-08 and 150-09 will gather.
Plan 150-08 (green real-CI run + live-fire red-run proof) and Plan 150-09
(150-VERIFICATION.md + the SUITE-02/03 flip to Complete + Obsidian phase note/hub refresh) are
unblocked to proceed.

## Self-Check: PASSED

- `docs/test-triage-149.md` — FOUND; `grep -c "ci_extras_gap"` → 2, `grep -c
  "gitignored_planning_dir"` → 2 (both ≥1, satisfying the acceptance criterion); addendum table
  row counts verified 31 and 4, matching `tests/skip_registry.py`'s Phase 150 block exactly
- `.planning/REQUIREMENTS.md` — FOUND; SUITE-02/SUITE-03 both `- [ ]` / `In Progress`; SUITE-01
  unchanged at `- [x]` / `Complete`
- `.planning/ROADMAP.md` — FOUND; Phase 150 block reads `**Plans**: 9 plans`;
  `grep -c "150-0[4-9]-PLAN.md"` → 6; Goal and Success Criteria byte-unchanged (confirmed via
  `git diff`)
- `docs/UAT-SERIES.md` — FOUND; `grep -c "UAT-150-0[123]"` → 4; header `**Last Updated:**`
  names 2026-08-12 and Phase 150, "Earlier:" chain preserved
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — FOUND; `grep -c "UAT-150-01"` → 2;
  frontmatter has `source: docs/UAT-SERIES.md` and `updated: 2026-08-12`
- Commit `9ff98fc` — FOUND via `git log --oneline --all | grep 9ff98fc`
- Commit `d287cdc` — FOUND via `git log --oneline --all | grep d287cdc`
- Commit `b9af731` — FOUND via `git log --oneline --all | grep b9af731`
- `pytest tests/test_cli_correctness.py tests/test_phase135_docs_presence.py
  tests/test_phase136_docs_presence.py -q -m ""` → `18 passed, 3 xfailed` (0 failed)
- `pytest tests/test_skip_registry.py -q -m ""` → `1 passed` (meta-gate stays green, no new
  skip markers introduced by this docs-only plan)
