---
type: todo
created: 2026-09-27
source: phase-207.1 execution (orchestrator pre-image/signature diff at phase start, plus 2 further hits caught by the 207.1-02 executor)
priority: medium
requirement: none (a THIRD axis of the TOOL-01/04/05 defect class, not a reopening of any of them)
---

# A field's VALUE can span multiple lines — the writer replaces only its first line and orphans the rest

**A third axis of the same defect class, found live on 2026-09-27 by the mandatory pre-image diff at
Phase 207.1's start.** CLAUDE.md §GSD `state.*` Verb Integrity clause (h) records two axes that have
each produced a miss:

1. **which install** — `~/.claude/get-shit-done/bin/lib/` vs the npx SDK (TOOL-05)
2. **which construct shape** — bold `**Field:**` vs bare `Field:` (Phase 186.1)

This is a third, orthogonal to both: **how many LINES the field's value occupies.**

## What happened

`state.begin-phase` was run against this repo's live `.planning/STATE.md`. The `Phase:` field under
`## Current Position` held a **five-line** value. The verb replaced only its FIRST line and left the
remaining four dangling beneath the new two-line value:

```
Phase: 207.1 (orphaned-browser-only-coverage-drain) — EXECUTING
Plan: 1 of 3
(`207.1-01` UAT-7-23 + control, `207.1-02` UAT-7-29 + control, ...     <- orphaned
docs/vault), plan-checker VERIFICATION PASSED with zero blockers.**    <- orphaned
Next: `/gsd-execute-phase 207.1` — in the main session on branch       <- orphaned
`phase-207-browser-only-coverage-verdict` (D-17 forbids worktree fan-out).  <- orphaned
```

Syntactically valid Markdown. Reads like something a person wrote. **Neither named corruption
signature fires** — signature (a) was verified CLEAN in the same diff (no bold-field code span was
garbled; the 186.1 anchoring and scoping hold), and the dropped `last_activity` key was a separate,
concurrent hit rather than this one.

## Why 186.1's fix cannot catch it

Phase 186.1 narrowed the plain-field fallback's searchable region to "the leading contiguous
field-shaped run immediately after a known heading." That decides **which line to find**. It says
nothing about **where that field's value ends**. Scoping fixed target selection; it never taught the
writer that a value may continue past a newline. A document whose fields are all one-liners is safe.
This repo's STATE.md is not, and never has been.

## Why the signature greps cannot catch it either

This is the part worth generalising. The signature greps compare **content-only sets** (`grep -o` /
`grep -h`, line numbers stripped) precisely so harmless line-number shifts don't raise false alarms.
But an orphaned continuation line is **unchanged content** — still byte-identical text. What changed
is only its *structural relationship* to the line above it, and a set-membership comparison has no
way to observe that. The insensitivity that makes the greps usable is the same insensitivity that
blinds them here.

**Only the FULL diff caught it.** Treat the signature greps as a cheap supplement to the full diff,
never a substitute for it — and say so wherever the protocol is written down.

## Also reconfirmed in the same phase

- `last_activity` is STILL dropped by mutating verbs on the npx install
  (`~/.npm/_npx/4db0de1f85c3165e/node_modules/get-shit-done-cc/sdk/dist/cli.js`) — 3 hits in this
  phase alone, ~6 across three sessions. CLAUDE.md's claim that signature (b) is patched is **false
  for this install**.
- `completed_phases`/`total_plans`/`percent` regressed on every one of those 3 calls, with zero real
  plans completed at the time of the first.
- **What worked:** pushing the pre-image protocol DOWN into every executor subagent prompt. Two of
  the three hits were caught by an executor and hand-corrected; the orchestrator never saw them.
  Keep that instruction in the subagent prompt, not just in the orchestrator's head.

## Suggested fix shape

The write path needs a notion of a field's value EXTENT, not just its start line: consume the
field's line plus any immediately-following lines that are not themselves field-shaped and not a
heading, and replace that whole run. Then extend 182-07's run-time source scan with a third
dimension so this axis cannot silently regress — the standing lesson being that a hand-derived list
of known sites has now failed three times in three different directions.
