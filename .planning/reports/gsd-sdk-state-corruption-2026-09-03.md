# gsd-sdk / gsd-tools: two STATE.md corruption bugs in `state begin-phase`

**Reported:** 2026-09-03
**Package:** `@gsd-build/sdk` 1.42.3 (delegates to `~/.claude/get-shit-done/bin/gsd-tools.cjs`)
**Repo:** `gsd-build/get-shit-done`, `sdk/` directory
**Observed in:** 9 occurrences across 3 milestones' phases (QU.I.R.K. v5.18, Phases 179–181)
**Severity:** silent data corruption in the file every session treats as project history

Both bugs are silent. No error, no warning, no failing test — the output is syntactically valid
Markdown that reads like something a human wrote. The only detection is diffing every write.

---

## Bug A — unanchored bold-field regex corrupts prose

### Location
`bin/lib/state-document.generated.cjs`, `stateReplaceField()`, line 42.

```js
const boldPattern = new RegExp(`(\\*\\*${escaped}:\\*\\*\\s*)(.*)`, 'i');   // no ^, no /m
```

The **plain-text branch four lines below is correctly anchored** (`^…/im`). Only the bold branch
is not, so `**Status:**` matches *anywhere in the document* — including mid-sentence inside prose —
and `(.*)` then swallows the remainder of that line.

### Reproduction

```
.planning/STATE.md
---
gsd_state_version: 1.0
milestone: v9.9
status: verifying
---

## Accumulated Context

- [Phase 170]: archived files gained a `**Status:**Ready to execute` marker. Must not change.

## Current Position

Phase: 900 (demo) — EXECUTING
Status: Ready to execute
```

```bash
node gsd-tools.cjs state begin-phase --phase 901 --name d --plans 3
```

**Before:** ``- [Phase 170]: archived files gained a `**Status:**Ready to execute` marker. Must not change.``
**After:**  ``- [Phase 170]: archived files gained a `**Status:**Executing Phase 901``

The historical sentence is rewritten and its closing backtick and trailing clause are destroyed.

### Fix (verified)

```js
const boldPattern = new RegExp(`^(\\s*\\*\\*${escaped}:\\*\\*[ \\t]*)(.*)$`, 'im');
```

After the fix the prose line is untouched and the real `Status:` field still updates.

---

## Bug B — frontmatter is reconstructed from a fixed schema, dropping unknown fields

`begin-phase` does not preserve the existing frontmatter; it rebuilds it. Fields outside the
expected schema are **silently deleted**.

### Reproduction

Input frontmatter:
```yaml
gsd_state_version: 1.0
milestone: v9.9
milestone_name: Demo Milestone
status: verifying
stopped_at: mid-flight marker
last_updated: "2026-09-03T00:00:00.000Z"
progress:
  total_phases: 7
  completed_phases: 6
  percent: 86
```

**With no `ROADMAP.md` present** — output:
```yaml
gsd_state_version: 1.0
milestone: v1.0            # ← RESET to an invented default
milestone_name: milestone  # ← RESET to an invented default
status: executing
last_updated: "..."
```
`stopped_at` and the entire `progress:` block are gone. Milestone identity is silently replaced.

**With `ROADMAP.md` present** — `milestone` and `milestone_name` survive, because they are
re-derived from the roadmap. **`stopped_at` and `progress:` are still deleted.**

So the observable behaviour is: fields with a recovery path survive; fields without one vanish.

### Impact observed in practice

`stopped_at` regressed to a stale value mid-milestone (`"Completed 180-07-PLAN.md"` after 180-08
had completed and the phase was verified), which had to be corrected by hand. Because the value is
plausible, nothing flags it.

### Suggested fix

Preserve unknown frontmatter keys through the read-modify-write cycle rather than reconstructing
from a schema — or, at minimum, warn on dropped keys the way `stateReplaceFieldWithFallback()`
already warns on a missing field.

---

## Suggested regression fixtures

1. A STATE.md containing `**Status:**` inside prose; assert the prose is byte-identical after
   `begin-phase`, and that the real field updated.
2. A STATE.md with a custom frontmatter key and a populated `progress:` block; assert both survive
   `begin-phase`, with and without `ROADMAP.md` present.

Bug A is in a `.generated.cjs` file, so a downstream patch is overwritten on regeneration — the
generator needs the fix.

---

## Local mitigation applied downstream

`bin/lib/state-document.generated.cjs` line 42 patched with the anchored regex above
(backup at `state-document.generated.cjs.bak`). Bug B is **not** patched locally; operators are
instructed to hand-edit STATE.md instead of invoking `state.*` / `roadmap.*` verbs.
