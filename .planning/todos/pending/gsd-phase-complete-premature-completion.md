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

---

## Feasibility & Effort — verified live 2026-09-12 (read the code, did not infer)

**Operator decision 2026-09-12: fix deferred deliberately, not forgotten.** This machine is the
single development machine going forward, so the fix is wanted eventually — but not mid-milestone.
v5.23 finishes under the existing hand-edit + pre-image + signature-diff protocol first.

### Verdict: CONFIRMED feasible · effort S (≈half a session) · no spike needed

The guard has a precise, already-available insertion point. In the npx SDK install,
`sdk/dist/query/phase-lifecycle.js`:

```js
848:  const planCount = plans.length;
849:  const summaryCount = summaries.length;
      // ←← NOTHING between here and the Step C/E/F writes ever compares these two values
1154: plans_executed: `${summaryCount}/${planCount}`,   // reports the truth, having already ignored it
```

The verb computes exact ground truth at 848-849 and reports it honestly at 1154. There is no
eligibility check of any kind in between. That is the whole defect — it is a missing conditional,
not a logic error, which is why no anchoring/scoping fix could ever have caught it.

`--force` precedent already exists **in this same file** at line 663 (`phase.remove`:
`Phase N has X executed plan(s). Use --force to remove anyway.`), so the refusal shape is
established in-codebase rather than invented.

### Scope of the fix session

1. Guard in `phaseComplete` after line 849: refuse (`GSDError`, Validation) when
   `summaryCount < planCount` unless `--force`. Mirror into the `.cjs` install
   (`~/.claude/get-shit-done/bin/lib/phase.cjs`, `cmdPhaseComplete`).
2. Same treatment for `state.planned-phase`'s `updated: []` misreport — see
   `gsd-state-planned-phase-misleading-empty-updated.md` (sibling todo, same session).
3. Command-boundary test against a fixture phase at N/M (M > N), then a live
   re-demonstration per CLAUDE.md clause (e) — a green function-level test is never sufficient here.
4. Snapshot + pristine-baseline both installs per the `~/.claude/gsd-npx-sdk-patches/` convention.
5. **Environment hygiene (operator-requested):** prune the stale second npx cache dir
   `~/.npm/_npx/9785a834b31d581d` (get-shit-done-cc **v1.30.0**, zero LOCAL PATCH markers). It has
   **no `sdk/dist/cli.js`**, so it is NOT a reachable entry point and NOT a third unpatched install
   — cache residue only. Removing it eliminates the ambiguity rather than any live hazard.

### Install inventory as verified 2026-09-12 (all patches INTACT — no silent wipe has occurred)

| Install | Resolves from | Version | `LOCAL PATCH` files | Reachable? |
|---------|---------------|---------|---------------------|------------|
| `~/.npm/_npx/4db0de1f85c3165e/…/get-shit-done-cc/sdk/dist/` | `gsd-sdk` → `cli.js` | 1.42.3 | 6 | **yes — live** |
| `~/.claude/get-shit-done/bin/lib/` | `gsd-tools.cjs` (node path) | 1.42.3 | 2 (`state.cjs`, `state-document.generated.cjs`) | yes |
| `~/.npm/_npx/9785a834b31d581d/…/get-shit-done-cc/` | nothing — no `sdk/dist/cli.js` | 1.30.0 | 0 | no — prune |

The npx-hash-rotation hazard CLAUDE.md clause (h)(2) warns about **has not fired**: the live hash is
still `4db0de1f85c3165e` and still v1.42.3.

### Upstream status — a dead end short-term, DO NOT UPGRADE to chase it

- Issue **#4243 is CLOSED** (`open-gsd/gsd-core`). It only ever covered the **TEXTUAL** class
  (bold-field regex + frontmatter key drop). The maintainer's triage comment states our 1.42.3
  "predates or omits those fixes."
- **1.42.3 IS the latest published stable.** The upstream fixes exist only in `1.43.0-rc1`/`rc2`
  and `1.50.0-canary.1`/`.2`. Upgrading would trade a known-patched install for an unverified
  prerelease **and** rotate the content-addressed npx hash, silently wiping all 21 patched sites.
- **This SEMANTIC class was never filed upstream.** Adjacent issues prove maintainers act on it
  when told: **#4067** (`state.advance-plan`: phase-complete branch can fire while sibling plans are
  still executing) CLOSED/confirmed-bug; **#2022** (`roadmap update-plan-progress` checks the
  phase-level checkbox with zero verification gate) CLOSED/confirmed-bug; **#4624** OPEN
  (orchestrator-worktree workers finishing without lifecycle reconciliation). Filing this with the
  `completed_plans: 142`-at-5/7 evidence is part of the fix session, and may make the local patch
  unnecessary on a later release.

### Correction to the standing blanket rule

CLAUDE.md's operative guidance reads as "every mutating GSD verb is unsafe on this machine." The
**demonstrated** exposure is narrower: the textual class is patched and guarded in both reachable
installs, and the open semantic exposure is **two named verbs** (`phase.complete`,
`state.planned-phase`). The blanket is retained as conservative risk management — nobody has done
the per-verb clearing work — but it should not be read as evidence that every verb has been caught
misbehaving. Keep hand-editing; know why.
