---
type: todo
created: 2026-09-07
source: phase-186.1 plan 06 (live re-demonstration against the real .planning/STATE.md, ROADMAP.md, REQUIREMENTS.md)
priority: high
requirement: none (new defect class — SEMANTIC, not the TEXTUAL TOOL-01/TOOL-05 class this phase closed)
---

# `phase.complete` flips a phase to complete without checking its own plans are actually done — reproduced live against phase 186.1 itself, mid-execution

**This is a DIFFERENT defect class from TOOL-01/TOOL-05.** Those were TEXTUAL — a regex clobbering
prose. This is SEMANTIC — the verb writes syntactically perfect, well-formed, completely WRONG
values. No regex anchor or region-scoping fix would ever catch this; it requires the verb to check
its own completion claim against ground truth before writing it.

## What happened

During 186.1-06's live re-demonstration (Runs 5 and 6, both entry points — `gsd-sdk` npx and
`gsd-tools.cjs`), `phase.complete 186.1` was run against phase 186.1 itself — this very phase, 5 of
7 plans actually done, plan 06 not yet finished, plan 07 not started. The verb's own JSON output
correctly reported `"plans_executed": "5/7"` — the correct count was computed and available — and
in the SAME call it:

- Flipped `.planning/ROADMAP.md`'s Phase 186.1 checkbox to `[x]` complete, including its
  Plans-column row (`0/7 | Planned` -> `5/7 | Complete`) and per-wave plan checkboxes for waves
  5 and 6, which had NOT run yet.
- Checked off `TOOL-01` and `TOOL-05` as `[x]` in `.planning/REQUIREMENTS.md`.
- (`gsd-sdk` only) Set `.planning/STATE.md`'s frontmatter `status: milestone_complete`,
  `stopped_at: Milestone complete (Phase 186.1 was final phase)`, and
  `completed_plans: 142` — an IMPOSSIBLE value; the real total across all phases was 77.
- (`gsd-tools.cjs` only) Emitted three `WARNING: STATE.md field ... not found` lines, wrote
  `completed_plans: 75` (a smaller but still fabricated jump), and inserted spurious blank lines
  into several `ROADMAP.md` list items as an unrequested formatting side effect.

Both entry points reproduced the core defect: a phase self-reports its own real, partial progress
in one field of its own output while writing full completion everywhere else in the same call.

## Why this evaded every TOOL-01/TOOL-04/TOOL-05 fix

None of the four write-path bold-field regex fixes, the plain-field scoping fix, or any anchoring/
scoping change touches this code path's DECISION logic — `is_last_phase` / completion-eligibility
computation. The written values are syntactically perfect YAML/Markdown; there is no garbled bold
field, no dropped frontmatter key. A clean corruption-signature diff is not the same as a correct
write (CLAUDE.md's own standing lesson, now demonstrated a further time by a genuinely different
mechanism).

## Operative consequence

**`phase.complete` MUST NOT be used to close a phase on this machine until this is fixed.**
Phase 186.1's own close-out (plan 07 / orchestrator) hand-wrote the STATE.md/ROADMAP.md tracking
updates instead, under the pre-image + full-diff + signature-check protocol, specifically because
of this finding.

## Acceptance (for whoever picks this up)

- `phase.complete` verifies the named phase's own plan directory shows all plans actually complete
  (e.g. a SUMMARY.md exists for every PLAN.md in that phase's directory) before writing ANY
  completion state, in both entry points.
- If plans are incomplete, the verb refuses (non-zero exit, or an explicit `{"error": ...}`
  response) rather than partially completing with a misleading "plans_executed" field that
  contradicts its own writes.
- `completed_plans` arithmetic is derived from a real count, never asserted independent of the
  written checkboxes it should match.
- Proven at the command boundary against a fixture phase with N/M plans done (M > N), then
  re-demonstrated live per CLAUDE.md clause (e) — a green function-level test alone is not
  sufficient in this codebase.

## Related findings from the same live session (may share root cause / fix)

- `.planning/todos/pending/gsd-state-planned-phase-misleading-empty-updated.md` — the same
  session's sibling finding: `state.planned-phase` returns `updated: []` while silently drifting
  frontmatter values anyway.
- Confirmed npx-vs-`.cjs` behavioral divergence for identical verb + argv, observed in the same
  session across two separate run pairs (see `186.1-06-SUMMARY.md`) — worth checking whether a
  shared root cause explains both the divergence and the premature-completion bug, or whether they
  are independent.

Full transcript: `.planning/phases/186.1-close-gap-tool-01-tool-05-scope-the-plain-field-fallback/186.1-06-SUMMARY.md`, Runs 5 and 6.
