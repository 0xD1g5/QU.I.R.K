# Dashboard Quality / "Axe + Console Gate" red on `main` — RESOLVED 2026-09-28

**Filed:** 2026-09-28 (v5.25 milestone audit, operator-flagged mid-audit)
**Resolved:** 2026-09-28, same session
**Tag-blocking:** no (v5.25.0 was already tagged and published carrying the defect)

## Resolution

`src/dashboard/src/pages/cbom.tsx` QS_BADGE "Safe":
`bg-[hsl(var(--qs-node-safe))]` -> `bg-[hsl(var(--status-safe-deep))]`, keeping `text-white`.
Verified by running the real gate locally: `npm run a11y:check` now reports
`PASS [cbom]: no regressions (0 live)`.

Regression guard added at `src/dashboard/src/components/__tests__/cbom-badge-contrast-guard.test.ts`,
mutation-proved: reintroducing `--qs-node-safe` turns it red in both themes.

## Root cause

Plan 213-07 (`3f50b104`, 2026-09-28 13:41) tokenised the badge map:

```
- Safe: "bg-[hsl(142_71%_30%)] text-white"          #16833e + white = 4.84:1  PASS
+ Safe: "bg-[hsl(var(--qs-node-safe))] text-white"  #21c45d + white = 2.30:1  FAIL
```

Identical hue, identical saturation, **lightness 30% -> 45%** — and lightness is the one channel
contrast depends on, so the change reads as "the same green" in review. The 30% was deliberate:
`4d18cdf4` (165-04, "flip teal/severity foregrounds to AA-clearing dark tokens") darkened it to
clear 4.5:1, landing at 4.84 with a thin margin.

`--qs-node-safe` is a **Cytoscape node-fill** token — correct for a graph node or a legend swatch,
where nothing is drawn on top of it; wrong behind text. 213-02 had already minted the right token,
`--status-safe-deep` (142 71% 30%, the exact original value, with a light override at 24%), and
`findings.tsx:145` plus this same file's `TIER_BADGE` "Tier 3" already used it. cbom's QS_BADGE was
the lone outlier.

## TWO CORRECTIONS to this todo's original text

**1. "Red for 6 consecutive runs since `36349999153` (2026-09-27T20:58:56Z)" was WRONG.** The axe
gate's streak is **5** runs, first red `36466955883` (2026-09-28T18:41:20Z). Run `36349999153` also
failed, but in a **different job** — `E2E Smoke (real server + committed bundle)`, on
`src/pages/__tests__/exposure-map.test.tsx` (`expected "warn" to be called`). Two different causes
were collapsed into one streak by reading the workflow's red/green column instead of the per-job
conclusion.

**2. The headline conclusion "this is not a code regression" was WRONG, and followed directly from
error 1.** Anchoring on the wrong first-red run produced a breaking window
(`b262aa82..ec18cc1c`) containing five planning-docs-only commits, which supported a confident
"environmental / dependency float" diagnosis. The real window is `ec18cc1c..7f826ac5` — the entire
Phase 213 dashboard theme-token migration. It is squarely a code regression, introduced by this
project, in this milestone.

**The lesson worth keeping:** a workflow-level red/green streak is not a failure signal, it is an
aggregate of per-job signals. Always resolve the failing JOB and STEP for the first red before
computing a breaking window — a window anchored one run too early points at the wrong commits and
reads as clean evidence for the wrong conclusion.

## What this uncovered (still open)

Enumerating the full badge-pair set rather than fixing the single reported instance found
**46 of 103 pairs failing AA in at least one theme**, across 7 classes and 11 pages. Filed at
`.planning/todos/pending/260928-dashboard-badge-contrast-46-of-103-pairs-fail-aa.md`. One of the 46
(this one) was a v5.25 regression; the rest are pre-existing.

## Still open, separately

`Python CI / Linux Full Suite` is still red, but **CORRECTED 2026-09-28: not for the reason this
todo first guessed.** It is not the vitest flake and not the same family as `36349999153`'s
`exposure-map` E2E failure. The failing set is exactly two nodes —
`test_chaos_lab_idempotency::test_profile_re_up_is_idempotent[multihost]` and `[storage-s3]` —
both failing on Docker registry `unauthorized: access to the requested resource is not authorized`
while pulling `mh-storage-seed` / `minio-seed`. PR #37 reproduced the **identical** set, and its
vitest substitute node did not fail. Environmental, pre-existing, unrelated to v5.25.

So this one workflow column was red for **three** unrelated reasons in 36 hours: an `exposure-map`
E2E assertion (09-27), the cbom contrast regression fixed here (09-28), and Docker registry auth
(09-28 onward). That is the same lesson as the correction above, twice over — never read a
red/green column as a single signal.
