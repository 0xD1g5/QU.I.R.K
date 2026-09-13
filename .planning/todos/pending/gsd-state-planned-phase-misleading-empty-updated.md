---
type: todo
created: 2026-09-07
source: phase-186.1 plan 06 (live re-demonstration against the real .planning/STATE.md)
priority: medium
requirement: none (new defect class — SEMANTIC, not the TEXTUAL TOOL-01/TOOL-05 class this phase closed)
---

# `state.planned-phase` returns `updated: []` (reads as a safe no-op) while silently drifting frontmatter values anyway, and diverges between entry points for identical argv

**A DIFFERENT defect class from TOOL-01/TOOL-05** — no corrupted prose, no dropped key, just a
return value that misrepresents what the verb actually wrote.

## What happened

During 186.1-06's live re-demonstration (Run 1, `gsd-sdk` npx), `state.planned-phase --phase 999
--plans 3` against the real `.planning/STATE.md` returned:

```
{ "updated": [], "phase": "999", "plan_count": 3 }
```

`updated: []` reads as "nothing changed." The full `git diff` showed otherwise — three frontmatter
values changed in the same call:

- `stopped_at` regressed from a description of the CURRENT real state ("PLANNED... ready to
  execute") to a STALE prior value from an earlier session ("context gathered").
- `last_updated` bumped (expected).
- `completed_plans` jumped from 70 to 75 — arithmetic fabrication; zero plans were actually
  completed by this call.

## Entry-point divergence (same verb, same argv)

Run 2 (`gsd-tools.cjs`, identical argv) produced a ZERO-BYTE diff — no changes at all — for the
same verb call that Run 1's `gsd-sdk` npx entry point used to rewrite three frontmatter values.
This is a confirmed, reproducible behavioral divergence between the two installs for identical
input, reinforcing CLAUDE.md clause (h)(1)'s standing point that "the toolchain is patched" can
never be asserted as a single fact across both installs — each entry point must be independently
verified for every claim, including claims about what a verb's return value means.

## Why this evaded every TOOL-01/TOOL-04/TOOL-05 fix

This is not a regex-scoping or anchoring defect — the written frontmatter values are syntactically
valid. The defect is that the verb's own "what changed" bookkeeping (`updated: [...]`) does not
track every field it actually mutates, so a caller relying on that field to decide whether to
re-verify is misled into skipping verification exactly when verification was most needed.

## Acceptance (for whoever picks this up)

- `updated` (or equivalent per-verb "what changed" field) names EVERY field the verb call actually
  wrote, across both entry points, for `state.planned-phase` at minimum — audit sibling verbs for
  the same gap.
- `completed_plans` and `stopped_at` are never rewritten to a value that doesn't reflect either (a)
  a real completed-plan count derived from disk state, or (b) the actual current description of
  the phase's progress — never a stale, earlier-session value silently restored.
- The npx-vs-`.cjs` divergence for `state.planned-phase` (and any other verb showing the same
  pattern) is either resolved (both entry points do the same thing) or explicitly documented as an
  intentional per-install behavior difference, not left as an undocumented surprise.
- Proven at the command boundary with before/after diffs asserted against the `updated` field's own
  claim, then re-demonstrated live per CLAUDE.md clause (e).

## Related findings from the same live session (may share root cause / fix)

- `.planning/todos/pending/gsd-phase-complete-premature-completion.md` — the same session's more
  severe sibling finding: `phase.complete` writes full completion state for a phase that is not
  actually complete.

Full transcript: `.planning/phases/186.1-close-gap-tool-01-tool-05-scope-the-plain-field-fallback/186.1-06-SUMMARY.md`, Run 1 (and Runs 3/4 for the same frontmatter-drift pattern under `state.begin-phase`).

---

**2026-09-12:** Operator confirmed this should be fixed eventually (single dev machine going
forward), deferred until after v5.23. Bundle it into the same fix session as the sibling
`gsd-phase-complete-premature-completion.md` — that todo now carries the verified feasibility
assessment, the install inventory, and the upstream status for BOTH verbs. Same defect class, same
two installs, same test-and-re-demonstrate protocol; fixing them separately would duplicate all the
snapshot/baseline/durability work.
