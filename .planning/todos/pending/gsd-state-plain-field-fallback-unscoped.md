---
type: todo
created: 2026-09-06
source: phase-185 planning (live corruption during `gsd-sdk query state.planned-phase`)
priority: high
requirement: TOOL-05
---

# `stateReplaceField()`'s plain-field fallback is unscoped, and deterministically clobbers STATE.md body prose

**Site:** `~/.npm/_npx/4db0de1f85c3165e/node_modules/get-shit-done-cc/sdk/dist/query/state-document.js:26`
(the `gsd-sdk` npx install — NOT `~/.claude/get-shit-done/bin/lib/`, see TOOL-05 / CLAUDE.md §(h)).

```
const plainPattern = new RegExp(`(^${escaped}:\\s*)(.*)`, 'im');
```

## The defect is scoping, not anchoring

Every prior entry in this class was an **unanchored** `**Field:**` regex, fixed by adding `^…$`/`im`.
`REQUIREMENTS.md` TOOL-01 records the belief that *"the plain-text branch below it is correctly
anchored — only the bold branch was wrong."*

**That belief is false, and this is the falsification.** The plain branch *is* anchored. Anchoring
was never sufficient. The fallback is **unscoped**: it searches the entire document body and takes
the first line-initial `Status:` anywhere, with no notion of which section holds machine fields
versus narrative prose.

## Why it is deterministic for this repo, not intermittent

`stateReplaceField()` tries the anchored bold `**Status:**` pattern first (line 22 — this is the
TOOL-05 LOCAL PATCH, and it works correctly), then falls through to the plain pattern on line 26.

This project's `.planning/STATE.md` has **no `**Status:**` bold field and no plain `Status:` field
in `## Current Position` at all.** So:

1. the bold path always misses,
2. the fallback always runs,
3. the first line-initial `Status:` in the body is always the narrative sentence in the
   "Prior phase (retained for history)" block —
   `` Status: 184.3-10 complete (2026-09-05) — `src/dashboard/.../new-date-argument-guard.test.ts`, ``
4. which is replaced wholesale, destroying its trailing clause and orphaning its continuation lines
   into a headless fragment.

That line has now been destroyed **8 times** by three different verbs (`state.planned-phase` ×4,
`state.begin-phase` ×2, `phase.complete` ×1, plus this occurrence). It is not a flaky race — any
mutating state verb run against this STATE.md will hit it.

## The tell that was misread for 7 occurrences

`state.planned-phase` returns `{"updated": ["Status"]}`. That reads like a minimal, safe write.
It is the opposite: its other intended targets — `Total Plans in Phase`, `Last Activity`,
`Last Activity Description` (`state-mutation.js:959-978`) — **do not exist in this document** and
silently no-opped. So the *only* thing the verb successfully wrote was the corruption. A returned
field list naming exactly one field is a signal to look harder, not a reassurance.

## Why the existing guard does not catch it

`tests/test_gsd_state_patch.py`'s run-time source scan
(`test_bold_field_regex_class_is_fully_dispositioned`) regenerates its occurrence set from source
on every run — which is the right design — but it scans **only the `~/.claude/get-shit-done/bin/lib/`
paths** and only for `**Field:**`-shaped constructs. This site is in a different install and is not
bold-shaped, so it is invisible on both axes.

`~/.claude/gsd-npx-sdk-patches/README.md` has no ledger entry for `state-document.js:26`.

## Work

1. **Fix the fallback.** Two candidate shapes — pick one deliberately and record why:
   - (a) **Scope it.** Restrict the plain-field search to the frontmatter block or to an explicit
     `## Current Position` field region, the way `buildStateFrontmatter()`'s `## Session` guard was
     widened in 182-06.
   - (b) **Fail closed.** Return `null` when the field does not exist as a real field, rather than
     falling back to a document-wide prose search. Callers already handle `null` (they check the
     result before assigning), so a missing field would become an honest no-op instead of a
     silent misdirected write.
   (b) is likely the smaller and safer change; (a) is closer to the existing idiom. Note that a
   fix must not break the legitimate frontmatter `status:` write, which relies on this same path.
2. **Extend the run-time source scan to the npx install** and to bare `Field:` constructs, not just
   `**Field:**` ones. A guard that only looks where the last bug was is the failure mode this class
   keeps reproducing.
3. **Seed the durability layer** — pristine baseline + post-patch snapshot + ledger entry under
   `~/.claude/gsd-npx-sdk-patches/`, per CLAUDE.md §(h).
4. **Prove it at the command boundary, then live.** A green function-level test is explicitly not
   sufficient in this codebase (CLAUDE.md §(e)): run the actual verb against a fixture shaped like
   this real STATE.md, then re-demonstrate against the real file with a pre-image signature diff.
5. **Correct TOOL-01's recorded rationale** in `REQUIREMENTS.md` — the "only the bold branch was
   wrong" sentence is what let this site sit unexamined through four patch rounds.

## Note for whoever picks this up

`npx` cache dirs are content-addressed. The hash `4db0de1f85c3165e` was verified unchanged on
2026-09-06, so the existing patches are intact — but a `get-shit-done-cc` version bump creates a
new `_npx/<hash>/` directory and silently drops every patch. Re-resolve
`readlink -f "$(which gsd-sdk)"` before trusting any of the above.

**Standing workaround until patched:** pre-image `.planning/STATE.md` before any mutating state
verb and read the FULL diff hunk-by-hunk. Any hunk outside the frontmatter block is guilty until
proven intended — signature greps and arithmetic sanity-checks both pass clean on this defect.
