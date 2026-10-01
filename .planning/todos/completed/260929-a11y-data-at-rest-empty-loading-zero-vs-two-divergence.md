---
type: todo
created: 2026-09-29
source: Phase 216 plan 216-08 (HARNESS-03), measurements at
  /private/tmp/claude-501/-Volumes-Digs-1TB-Development-quantum-apps-QUIRK/01d36e00-e4c5-4c05-ad5d-a8f31fbccd43/scratchpad/216-08-measurements-FINAL.md
priority: low  # local-only; CI is green on both entries today
requirement: KBD-01
resolves_phase: 219
---

# `/data-at-rest` empty/loading `scrollable-region-focusable` diverges 0 (macOS) vs 2 (Linux CI) — deliberately NOT ranged

216-08 gave `scrollable-region-focusable` on `baseline-data-at-rest-default-dark.json` and
`baseline-data-at-rest-default-light.json` a measured `countRange: [1, 2]` (macOS observed 1,
Linux CI observed 2, both themes). The **empty** and **loading** fixture-variant baselines for the
same route and rule (`baseline-data-at-rest-empty-dark.json`,
`baseline-data-at-rest-loading-dark.json`) carry the same rule at `count: 2` (Linux-recorded
2026-09-06) but were measured locally on macOS at **0**, not 1:

```
cd src/dashboard && npm run a11y:check:empty    # FAIL [data-at-rest]: count 0 is BELOW baseline 2
cd src/dashboard && npm run a11y:check:loading  # FAIL [data-at-rest]: count 0 is BELOW baseline 2
```

This is a **wider** spread than the default variant's 1-vs-2 (which HARNESS-03's range now
absorbs). `[1, 2]` cannot cover a 0, and widening to `[0, 2]` would set the ratchet floor to zero —
exactly the "a loose tolerance could hide a real regression" failure mode 216-CONTEXT.md D-10
rejected a *global* band for. Ranging these two entries down to `[0, 2]` would silently accept "the
rule never fires" as a passing state, which defeats the point of baselining it at all.

**Disposition: leave both entries at their exact Linux-recorded `count: 2` and do not range them.**
This divergence is:

- **Pre-existing**, not introduced by Phase 216 — these two baselines were Linux-generated
  2026-09-06, before this phase touched anything (`git log --since=2026-08-27` on the relevant
  files was empty as of that baseline's own justification).
- **Local-only** — the CI `a11y` gate is green on both entries today; only a local macOS
  `a11y:check:empty` / `a11y:check:loading` run observes the divergence.

**Why it likely diverges from the default variant's 1-vs-2 spread:** `scrollable-region-focusable`
fires on a container that is actually overflowing at render time (viewport/font-metrics/row-width
dependent, per the data-at-rest justification's own "Count-pinning addendum"). The empty and
loading fixture variants render zero or placeholder rows instead of the enriched fixture's real
row set, so the four `<Table>` instances at `src/dashboard/src/pages/data-at-rest.tsx` (lines 69,
117, 177, 215) may simply not overflow at all on a narrower macOS-default viewport under those
variants — a hypothesis, not verified here.

**Retirement path:** KBD-01 (Phase 219, `.planning/REQUIREMENTS.md`) adds `tabIndex`/`role` to
`src/dashboard/src/components/ui/table.tsx` and withdraws the `scrollable-region-focusable`
acceptance outright across every route and fixture variant, including these two. When KBD-01
lands, this divergence retires along with the default-variant range — no follow-up range should be
added to `baseline-data-at-rest-empty-dark.json` / `baseline-data-at-rest-loading-dark.json` in the
meantime; if CI ever goes red on them before then, re-measure fresh rather than assuming this
todo's hypothesis still holds.


---

## SUPERSEDED IN PART, 2026-09-29 (Phase 216 verifier blocker B1)

**CORRECTED at close-out, after the Phase 216 verifier returned `gaps_found` (blocker B2).** Two
claims above were false and are withdrawn. (a) "Phase 216 changed neither count nor variant" is
false for four files this phase rewrote: `certificates-{empty,loading}-dark` went `(none)` ->
`color-contrast:2`, and `hardware-{empty,loading}-dark` went
`color-contrast:3 + scrollable-region-focusable:1` -> `color-contrast:8`. It is true only of
`data-at-rest` (2->2) and `compare`. (b) The residual divergence is not one `data-at-rest` entry: it
is **4 routes across 2 rules**, with `/hardware` at 0-vs-**8**, not 0-vs-2. (c) The deeper finding:
the `empty` and `loading` legs are **near-vacuous** — only `/api/scan/latest` of ten fixture
endpoints consults `VITE_A11Y_FIXTURE_VARIANT` (`vite.config.ts:29`; the other nine serve full
fixtures unconditionally), and `loading` returns the COMPLETE fixture after a 3s delay, so it
measures the default state by construction. All three dark variants therefore carry identical
`(rule, count)` sets for every data-bearing route, with distinct `generated` timestamps proving
three real sweeps rather than a copy. Filed at
`.planning/todos/pending/260929-a11y-empty-loading-variant-legs-are-near-vacuous.md`.

This todo's framing — a single `data-at-rest` 0-vs-2 entry — is too narrow. Read the vacuity todo
first; fixing that one may dissolve this one, since the CI-side `2` is the default fixture leaking
through rather than a genuine empty-state render.

---

## RESOLVED 2026-10-01 (Phase 219, run 36795176372)

KBD-01 (219-01) added conditional `tabIndex`/`role`/`aria-label` to the shared wrapper in
`src/dashboard/src/components/ui/table.tsx`. 219-03's CI-only round-trip (dashboard-quality.yml
run `36795176372`, head SHA `1071b372`, pinned Chrome `152.0.7977.82`) regenerated all 54
baselines and classified exactly 4 changed `(file, rule)` rows, all `REMOVED`, all
`scrollable-region-focusable`:

```
baseline-data-at-rest-default-dark.json    scrollable-region-focusable  2 -> (none)
baseline-data-at-rest-default-light.json   scrollable-region-focusable  2 -> (none)
baseline-data-at-rest-empty-dark.json      scrollable-region-focusable  2 -> (none)
baseline-data-at-rest-loading-dark.json    scrollable-region-focusable  2 -> (none)
```

The rule is absent from all 4 `data-at-rest` baselines, **including the empty and loading
variants this todo was specifically about** — there is no longer an entry for the 0-vs-2
divergence to diverge on. No `countRange` remains anywhere in the committed baselines. This todo
is resolved by disappearance, per 219-CONTEXT.md D-09.

**Not resolved by this closure:** the broader, structurally different
`260929-a11y-empty-loading-variant-legs-are-near-vacuous.md` todo (the empty/loading fixture legs
being near-vacuous for most routes because only `/api/scan/latest` consults
`VITE_A11Y_FIXTURE_VARIANT`) is unrelated to this rule's withdrawal and stays open, handed to
Phase 220.
