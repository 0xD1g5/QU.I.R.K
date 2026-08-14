# Phase 151: Phase-Completion Artifact Gates - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-13
**Phase:** 151-phase-completion-artifact-gates
**Areas discussed:** Enforcement layer (initial), Corrected enforcement layer, Hook trigger, Hook consolidation, Retroactive scope, ARTIFACT-03 heuristic

---

## Enforcement layer (initial proposal)

| Option | Description | Selected |
|--------|-------------|----------|
| CI meta-gate test | pytest test matching test_skip_registry.py convention, walks .planning/phases/ in CI | ✓ (initially) |
| Git pre-commit/pre-push hook | Repo-local hook, blocks commit before .planning/ is stripped by gitignore | |
| Both | Local hook + CI backstop | |

**User's choice:** CI meta-gate test (initially selected)
**Notes:** This choice was invalidated immediately after — direct verification (`git check-ignore -v` on a file under `.planning/`) confirmed `.planning/` is entirely gitignored on this public repo. A CI-based check would find zero phase directories in Actions' checkout and enforce nothing. Re-asked as "Corrected enforcement" below.

---

## Corrected enforcement layer

| Option | Description | Selected |
|--------|-------------|----------|
| Local pre-commit/pre-push hook | Reads .planning/phases/ on disk before commit strips visibility | ✓ |
| gsd-sdk query the phase-completion workflow calls | Check step inside execute-phase/verify-phase flow itself | |
| Both, same script | Shared script invoked from both entry points | |

**User's choice:** Local pre-commit/pre-push hook
**Notes:** Confirmed as the only mechanism that can see `.planning/` at all, since it's gitignored and never reaches CI.

---

## Hook trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Only phase-closing commits | Detect STATE.md/ROADMAP.md diff flipping a phase to Complete, then check artifacts | ✓ |
| Every commit | Unconditional check on every commit | |

**User's choice:** Only phase-closing commits
**Notes:** STATE.md and ROADMAP.md are the two `.planning/` files that survived the Phase 120 gitignore rule (tracked from before it existed) — this is what makes diff-based trigger detection possible.

---

## Hook consolidation

| Option | Description | Selected |
|--------|-------------|----------|
| One shared script, two check functions | scripts/verify_phase_gates.py with check_phase_close() + check_destructive_archive() | ✓ |
| Two separate scripts | Independent, separately testable units | |

**User's choice:** One shared script, two check functions
**Notes:** Matches existing single-purpose-script-per-concern convention (release_tag_hygiene.py) at the file level while keeping the two concerns (phase-close vs. destructive-deletion) logically separate.

---

## Retroactive scope

| Option | Description | Selected |
|--------|-------------|----------|
| Future-only, no backfill | Gate prevents recurrence going forward; historical gaps stay as-is | ✓ |
| Backfill 144's missing UAT-SERIES.md entry | Also close the one still-open historical gap | |

**User's choice:** Future-only, no backfill
**Notes:** 145/147 already got VERIFICATION.md retroactively at v5.11 audit closeout per STATE.md; Phase 144's gap is treated as closed/accepted history.

---

## ARTIFACT-03 "user-facing" heuristic

| Option | Description | Selected |
|--------|-------------|----------|
| files_modified path heuristic | Scan PLAN.md files_modified for user-facing surface paths (dashboard, CLI, renderers, scanners) | ✓ |
| Explicit phase-level opt-out flag | Default-require UAT entry; phase can declare `user_facing: false` | |

**User's choice:** files_modified path heuristic
**Notes:** No opt-out flag — avoids relying on planners remembering to set a marker.

---

## Claude's Discretion

- Exact STATE.md/ROADMAP.md diff-parsing approach (regex vs. structured parse) for the phase-close trigger.
- Hook installation mechanism (`.githooks/` + `core.hooksPath` vs. `pre-commit` framework) — check CONTRIBUTING.md conventions first.
- VALIDATION.md staleness-detection parsing approach — check its actual on-disk shape before deciding.

## Deferred Ideas

None — discussion stayed within phase scope.
