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

**Update (2026-09-03, Phase 182):** Bug B has since been patched locally too, and both patches are
now behaviourally tested. See "Fix as applied locally" below. The hand-edit-only instruction above
is retired on the reporting machine as of this update — kept here verbatim as the historical
record of what was true when this report was first filed.

---

## Fix as applied locally

Both bugs are now patched in the operator's installed toolchain
(`~/.claude/get-shit-done/bin/lib/`) and locked behind a behavioural (not presence-only) test
suite, `tests/test_gsd_state_patch.py` (7 tests, QU.I.R.K. repo). This section gives upstream the
tested fix, not just the complaint.

### Bug A — final diff (`state-document.generated.cjs`, `stateReplaceField()`)

```diff
-const boldPattern = new RegExp(`(\\*\\*${escaped}:\\*\\*\\s*)(.*)`, 'i');
+const boldPattern = new RegExp(`^(\\s*\\*\\*${escaped}:\\*\\*[ \\t]*)(.*)$`, 'im');
```

One line, adds `^`/`$` anchors and the `/m` flag to match the already-correctly-anchored
plain-text branch four lines below. Verified: the prose line
`` - [Phase 170]: archived files gained a `**Status:**Ready to execute` marker. Must not change. ``
survives byte-identical through `begin-phase`, and the real `Status:` field under
`## Current Position` still updates.

### Bug B — final diff (`state.cjs`, `syncStateFrontmatter`)

```diff
   if (derivedFm.status === 'unknown' && existingFm.status && existingFm.status !== 'unknown') {
     derivedFm.status = existingFm.status;
   }

+  const mergedFm = { ...existingFm, ...derivedFm };
+  if (existingFm.progress || derivedFm.progress) {
+    mergedFm.progress = { ...existingFm.progress, ...derivedFm.progress };
+  }
+  // getMilestoneInfo (core.cjs) does not follow the omission convention: with
+  // no ROADMAP.md present it returns its OWN invented fallback
+  // ({version:'v1.0', name:'milestone'}) rather than throwing or returning
+  // null, so derivedFm.milestone/milestone_name are always truthy and would
+  // otherwise unconditionally clobber a real existing value above.
+  if (cwd && existingFm.milestone && !fs.existsSync(planningPaths(cwd).roadmap)) {
+    mergedFm.milestone = existingFm.milestone;
+    mergedFm.milestone_name = existingFm.milestone_name;
+  }
+
-  const yamlStr = reconstructFrontmatter(derivedFm);
+  const yamlStr = reconstructFrontmatter(mergedFm);
```

Nine non-comment changed lines, one hunk, one function.

**A note on scope, in prose, for whoever picks this up upstream:** the merge above defends against
frontmatter keys `buildStateFrontmatter` cannot recover — it does not, and structurally cannot,
defend against a function that *fabricates* a value instead of omitting one. `getMilestoneInfo`'s
`{version:'v1.0', name:'milestone'}` fallback is exactly that: a real, truthy value standing in for
"I don't know," which a preserve-unknown-keys overlay has no way to distinguish from a genuine
re-derivation. That is why the fix above needed a second, narrower guard on top of the merge — the
merge alone left the no-`ROADMAP.md` milestone-reset symptom unfixed. **A merge defends against
absent values, never against fabricated ones.** Upstream should know the complete fix is "merge,
plus close the one call site that invents rather than omits" — not "merge instead of rebuild" on
its own.

**The accepted trade-off, stated plainly (T-182-10):** with preserve-unknown-keys, a frontmatter
key that the body legitimately removed will persist in the merged output until something
overwrites it, rather than disappearing on the next write. This was accepted deliberately — **a
stale key is recoverable, silently deleted project history is not.** Preserving deletion semantics
properly would require an explicit removal list (a field the write path marks "delete this key on
next sync"), which is exactly the kind of schema coupling between the read path and the write
path's intent that caused this bug in the first place. We chose the smaller, safer failure mode.

### Two fixture shapes that lock the fix

1. **Bug A — prose-survival fixture.** A `STATE.md` containing a `**Status:**` code span inside
   prose (the reproduction above); run through `state begin-phase`; assert the prose line is
   byte-identical afterward, and that the real `Status:` field under `## Current Position` did
   update. A companion negative-control fixture runs the same assertion against the *unpatched*
   regex (via a throwaway toolchain copy with the pristine, pre-patch file swapped in) and confirms
   it fails — proving the fixture is sensitive, not vacuous.

2. **Bug B — round-trip frontmatter fixture, parametrized over `roadmap_present`.** A `STATE.md`
   whose frontmatter carries `stopped_at`, a populated `progress:` block (`total_phases`,
   `completed_phases`, `percent`), and a novel key present in no schema (`my_custom_key`); run
   through `state begin-phase` twice — once with a `ROADMAP.md` present, once without; assert all
   three survive and that `milestone`/`milestone_name` are preserved (not reset to the invented
   `v1.0`/`milestone` defaults) in the no-`ROADMAP.md` case specifically.

### Durability

Both patched files are registered at `~/.claude/gsd-local-patches/<relPath>` (full post-edit
snapshots) with pristine pre-patch baselines at `~/.claude/gsd-pristine/<relPath>`, verified by the
existing `verify-reapply-patches.cjs` in precise-diff mode (6 required lines for Bug A, 40 for Bug
B — both single-hunk, bounded to the actual edit, not the whole file). A loss-detection test pair
in the QU.I.R.K. repo (`test_local_patches_are_durable`, `test_patch_loss_is_actually_detected`)
proves the verifier fails loudly (non-zero exit, `reason: fail_user_lines_missing`, naming every
missing line) if a `/gsd-update` regeneration reverts Bug A's patch.
