# The `empty` and `loading` a11y sweep legs are near-vacuous — only 1 of 10 fixture endpoints honours the variant

**Filed:** 2026-09-29, by the Phase 216 verifier (`gaps_found`, blocker B1), mechanism confirmed
independently at close-out.
**Priority:** P1 — two of the four CI a11y gate steps prove far less than their names claim.
**Owner:** Phase 220 (CI Instrument Truth) is the natural home; it is the same defect class as the
theme axis Phase 216 just repaired, one axis over.

## The observation

All three dark fixture variants carry **identical** `(rule, count)` sets for every data-bearing
route in the freshly CI-generated baselines:

| route | default-dark | empty-dark | loading-dark |
|-------|--------------|------------|--------------|
| data-at-rest | `scrollable-region-focusable:2` | `:2` | `:2` |
| certificates | `color-contrast:2` | `:2` | `:2` |
| hardware | `color-contrast:8` | `:8` | `:8` |
| compare | `color-contrast:2` | `:2` | `:2` |

**Not a copy.** `generated` timestamps are distinct and minutes apart
(`hardware-default` 18:35:46Z, `-empty` 18:36:31Z, `-loading` 18:36:53Z), so Linux really ran three
separate sweeps and really recorded default-variant numbers into the variant filenames.

**An empty fixture cannot render 8 sub-AA badges on `/hardware`.** That is the tell.

## Root cause — confirmed by reading `vite.config.ts`, not inferred

The `a11y-fixture` plugin registers BOTH `configureServer` and `configurePreviewServer`
(`vite.config.ts:175,179`), so the middleware genuinely runs under `vite preview`. The variant is
read at preview-server runtime from `process.env.VITE_A11Y_FIXTURE_VARIANT` (`:28`) — so the env
does reach it. That is all correct.

**The defect is that only ONE of ten fixture endpoints consults the variant.** `/api/scan/latest`
(`:29`) honours it — `empty` → `{}`, `loading` → a 3s delay. The other nine serve their full
fixtures unconditionally:

    :47  /api/scans              :89  /api/hardware/drift
    :52  /api/trends             :112 /api/compare
    :72  /api/hardware/vendor-trends   :134 /api/findings
    :152 /api/qramm/sessions     :158 /api/qramm/questions
    :164 /api/qramm/profiles

So any route not fed *exclusively* by `/api/scan/latest` renders fully populated under `empty`.
`/hardware` draws on `/api/hardware/drift` + `/api/hardware/vendor-trends`; `/compare` on
`/api/compare`. They render their normal content and report their normal violation counts.

**`loading` is vacuous by construction, for every route.** It returns the *complete* fixture after
a 3000ms delay. Once the harness waits for its `contentMarker`, the page has fully painted — so
`loading` measures the default state by design, not by accident. A transient skeleton cannot be
captured by a sweep that waits for content.

## What this means

- The `Run axe + console sweep (empty fixture)` and `(loading fixture)` CI steps are not worthless —
  they still exercise the `/api/scan/latest`-only routes — but they do **not** test what their names
  promise, and for the four data-bearing routes above they are duplicates of the default sweep.
- 26 of the 54 committed baselines (13 empty + 13 loading) are therefore of limited evidential value.
- **Phase 216 built a run-time drift guard for exactly this failure mode and pointed it at the theme
  axis only.** `theme-sweep-contract.test.ts` enumerates `THEMES` at run time and fails if a theme
  lacks an npm script or a CI step. Nothing does the equivalent for the *variant* axis, and nothing
  asserts that two variants must not produce identical result sets.

## Suggested fix shape (not prescriptive)

1. **A vacuity guard first, before any behaviour change** — a test that fails when two distinct
   variants produce identical `(rule, count)` sets for a route known to be variant-sensitive. That
   converts this from invisible to loud, which is the cheaper half.
2. Thread the variant through the remaining nine endpoints, at least for `empty`.
3. Decide what `loading` should mean. Either capture before first paint (no `contentMarker` wait,
   which fights the hollow-render guard) or retire the leg as unmeasurable and say so.
4. Regenerate the 26 variant baselines on Linux afterwards; expect real churn.

## Related / caused corrections

- `216-NOT-MET-AS-WRITTEN.md`, `216-VALIDATION.md`, `REQUIREMENTS.md` HARNESS-03 and the sibling
  todo `260929-a11y-data-at-rest-empty-loading-zero-vs-two-divergence.md` all described the
  residual divergence as a single `data-at-rest` 0-vs-2 entry. The real residual is **4 routes,
  2 rules**, with `/hardware` at 0-vs-**8**. Corrected at close-out.
- The same close-out wrongly stated Phase 216 "changed neither count nor variant" for those files.
  It rewrote four of them: `certificates-{empty,loading}-dark` went `(none)` → `color-contrast:2`,
  and `hardware-{empty,loading}-dark` went `color-contrast:3 + scrollable-region-focusable:1` →
  `color-contrast:8`. True only of `data-at-rest` (2→2) and `compare`. Corrected.
