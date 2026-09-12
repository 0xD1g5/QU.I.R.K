---
phase: 202-finding-storyline-drawer
plan: 07
subsystem: testing
tags: [a11y, axe-core, puppeteer, vite, vitest, fixture-middleware]

# Dependency graph
requires:
  - phase: 202-05
    provides: "/api/findings/{id}/storyline endpoint + FindingStoryline schema"
  - phase: 202-06
    provides: "Storyline trigger button (aria-haspopup=\"dialog\"), SheetDescription fix for F8, focus contract"
provides:
  - "/api/findings fixture handler in a11yFixture() serving a fully-populated S1 FindingStoryline payload"
  - "HOOK_TARGETS entry (4th) covering useFindingStoryline.ts's fetch target"
  - "routes.json findings entry extended with an interaction declaration (slug findings-storyline)"
  - "run-a11y.mjs opened-drawer interaction pass reusing buildBaselineEntries/compareToBaseline/baselineFilename"
  - "accepted-violations-freshness.test.ts route derivation extended to include interaction.slug programmatically"
affects: [202-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Interaction step declared as an optional key on an existing routes.json route entry, never as a new route (F10a)"
    - "Loud, logged no-op skip for non-default fixture variants rather than a silent continue (F10c)"

key-files:
  created:
    - src/dashboard/tests/a11y/fixture-storyline.json
  modified:
    - src/dashboard/vite.config.ts
    - src/dashboard/tests/a11y/fixture-coverage.test.ts
    - src/dashboard/tests/a11y/routes.json
    - src/dashboard/tests/a11y/run-a11y.mjs
    - src/dashboard/tests/a11y/accepted-violations-freshness.test.ts
    - .planning/phases/202-finding-storyline-drawer/202-VALIDATION.md

key-decisions:
  - "fixture-storyline.json uses theme_score_lift: 7 / theme_finding_count: 5 (not a 1:2 ratio) so the capture cannot coincidentally hide an Invariant-3 division regression"
  - "Trigger selector: table tbody button[aria-haspopup=\"dialog\"] (the existing production attribute, no test-only data-testid added); awaitSelector: [role=\"dialog\"] (Radix Dialog.Content's default role)"
  - "Interaction slug findings-storyline is declared on the existing findings route entry, never as its own routes.json route (F10a)"

patterns-established:
  - "accepted-violations-freshness.test.ts derives ALL baseline slugs (route.slug + route.interaction.slug) via a programmatic allBaselineSlugs() helper — a future second interaction anywhere in routes.json is automatically covered with no test edit"

requirements-completed: []  # STORY-01/STORY-02 NOT complete — Task 3 (blocking human-verify) has not run

# Metrics
duration: ~45min
completed: 2026-09-12
---

# Phase 202 Plan 07: A11y opened-drawer capture — fixture, HOOK_TARGETS, interaction step (PARTIAL — Tasks 1-2 of 3)

**PARTIAL SUMMARY. Task 3 (`checkpoint:human-verify`, `gate="blocking"`) has NOT been executed, NOT self-approved, and NOT marked green. This plan is not complete. The operator must run Task 3 before 202-07 can be closed.**

`/api/findings` fixture handler serving a fully-populated S1 storyline (lift 7 / count 5, `finding_position: null`), a 4th `HOOK_TARGETS` entry, and an opened-drawer interaction step wired into `run-a11y.mjs` that reuses the harness's existing baseline-comparison helpers under its own `findings-storyline` slug — closing three independent "covered but blind" blindness mechanisms without regenerating any baseline yet.

## Performance

- **Duration:** ~45 min
- **Tasks completed:** 2 of 3 (Task 3 intentionally not run — operator's checkpoint)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- Task 1: `/api/findings` fixture handler + `fixture-storyline.json` + `HOOK_TARGETS` entry, with a RED demonstration proving the coverage guard fires when the handler is absent.
- Task 2: per-route `interaction` declaration on the existing `findings` route, a full interaction pass in `run-a11y.mjs` (loud skip on `empty`/`loading`, hard fail on missing trigger/drawer, second axe scan through the existing baseline helpers), and a programmatic fix to the freshness test's route-list derivation, proven live by a temporary demo baseline file that made the test fail as STALE.

## Task Commits

1. **Task 1: /api/findings fixture handler, its S1 payload, and the HOOK_TARGETS entry** - `5fcd4726` (feat)
2. **Task 2: The per-route interaction step, its logged no-op for non-default variants, and freshness-generator visibility** - `99691ee3` (feat)

**Task 3 was NOT run and has no commit.** No plan-metadata commit exists yet — 202-07 is not closed.

## Extracted Evidence

### `extractTemplateLiteralPrefix("useFindingStoryline.ts")` output

`/api/findings/` — extracted from the hook's `` fetchApi(`/api/findings/${id}/storyline?title=${encodeURIComponent(title)}`) `` call. Confirmed matched by the new `req.url?.startsWith('/api/findings')` handler (`"/api/findings/".startsWith("/api/findings")` is `true`).

### Task 1 — remove-the-handler RED transcript

With the `/api/findings` handler block temporarily deleted from `vite.config.ts` (restored immediately after):

```
 ❯ tests/a11y/fixture-coverage.test.ts (7 tests | 1 failed) 5ms
   × a11y fixture middleware covers every /hardware + /compare fetch target (D-14) > 'useFindingStoryline.ts''s fetch target ('/api/findings/') is matched by a vite.config.ts handler 3ms
     → useFindingStoryline.ts fetches "/api/findings/" but no vite.config.ts startsWith() handler prefix matches it. Known handler prefixes: ["/api/scan/latest","/api/scans","/api/trends","/api/hardware/vendor-trends","/api/hardware/drift","/api/compare","/api/qramm/sessions","/api/qramm/questions","/api/qramm/profiles"]: expected false to be true // Object.is equality

 Test Files  1 failed (1)
      Tests  1 failed | 6 passed (7)
```

Handler restored; `npm run test -- fixture-coverage` returned to 7/7 passing.

### `fixture-scan.json` clickable row check

No amendment needed: `fixture-scan.json`'s `default`-variant `findings[0]` already carries `"id": 1` (non-null), so the interaction step's trigger selector resolves to a real, enabled `Storyline` button. No existing `findings` baseline is affected by this plan (its content is unchanged).

### Task 2 — freshness-test-fails-as-stale transcript

`accepted-violations-freshness.test.ts`'s route derivation was extended first (`allBaselineSlugs()` below), then, with no `baseline-findings-storyline-default.json` on disk, the freshness test still passed (7/7) — proving the extension is inert until a baseline for that slug actually exists. A temporary demo file was then written by hand (never through `npm run a11y:baseline`) to prove the derivation is *live*:

```
- Totals: 3 route(s), 4 (route, rule) entries, 8 accepted violation node(s).
+ Totals: 4 route(s), 5 (route, rule) entries, 9 accepted violation node(s).
  ...
+ ## findings-storyline
+
+ | Rule | Count | Impact | WCAG | Justification |
+ |------|-------|--------|------|---------------|
+ | demo-rule-for-derivation-proof | 1 | minor | 1.4.3 | TEMPORARY demo entry proving the freshness test derives findings-storyline from routes.json — deleted before commit; real baseline is written by Task 3's npm run a11y:baseline. |
...
 Test Files  1 failed (1)
      Tests  1 failed | 6 passed (7)
```

The demo file (`baseline-findings-storyline-default.json`) was deleted immediately after capturing this transcript and was never committed — `git status` after deletion showed only the three intended source-file modifications. The real baseline is Task 3's responsibility (`npm run a11y:baseline`).

### The derivation itself (programmatic, no hand-listed slug string)

```ts
function allBaselineSlugs(): string[] {
  return routes.flatMap((route) => [route.slug, ...(route.interaction ? [route.interaction.slug] : [])])
}
```

`grep -n "findings-storyline" src/dashboard/tests/a11y/accepted-violations-freshness.test.ts` returns no matches — the string appears nowhere as a hand-written list member in that file, only in `routes.json` and inside comments.

## Files Created/Modified

- `src/dashboard/tests/a11y/fixture-storyline.json` (created) - S1 FindingStoryline fixture payload
- `src/dashboard/vite.config.ts` - `/api/findings` handler added to `a11yFixture()`, placed adjacent to `/api/compare`, above the QRAMM block; confirmed no existing `startsWith` prefix shadows it
- `src/dashboard/tests/a11y/fixture-coverage.test.ts` - 4th `HOOK_TARGETS` entry, "three" -> "four distinct handler prefixes" test renamed and extended, new fixture-well-shaped assertion for all ten locked `FindingStoryline` keys
- `src/dashboard/tests/a11y/routes.json` - `findings` entry extended with `interaction: { slug: "findings-storyline", trigger, awaitSelector }`
- `src/dashboard/tests/a11y/run-a11y.mjs` - opened-drawer interaction pass added per-route, loud skip on non-default variants, hard fail on missing trigger/unopened drawer, second axe scan reusing existing baseline helpers, summary row added
- `src/dashboard/tests/a11y/accepted-violations-freshness.test.ts` - `allBaselineSlugs()` helper derives route + interaction slugs programmatically; used by `loadDefaultBaselines()` and the "no selector stored" test
- `.planning/phases/202-finding-storyline-drawer/202-VALIDATION.md` - 202-07-T1/T2 rows flipped to `green`; 202-07-T3 left `unchecked`

## Decisions Made

- Trigger selector chosen as `table tbody button[aria-haspopup="dialog"]` — the existing production attribute from 202-06's Storyline column, not a new test-only `data-testid`. No production-source change was needed, so no statics rebuild is required for this plan (confirmed: `files_modified` in this plan's frontmatter lists only `vite.config.ts` and `tests/a11y/*`, and that held).
- `awaitSelector: [role="dialog"]` — Radix `Dialog.Content`'s default ARIA role, always present once the Sheet opens, and unique on the page (only one Sheet exists).
- Fixture lift:count chosen as 7:5 (not 1:2) per the plan's explicit anti-coincidence instruction.

## Deviations from Plan

None — plan executed exactly as written for Tasks 1-2. No `findings.tsx` edit was needed (Task 1's read-first check confirmed a clickable row already existed in `fixture-scan.json`), so no statics rebuild was triggered by this plan.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness — BLOCKED

**This plan is not complete.** Task 3 (`checkpoint:human-verify`, `gate="blocking"`) has not run. The operator checkpoint package below must be executed and approved before 202-07 (and therefore ROADMAP success criterion 4) can be considered done. Do NOT proceed to 202-08 planning/execution treating 202-07 as closed.

---

## OPERATOR CHECKPOINT PACKAGE (Task 3 — copy-paste ready)

Run in order, from `src/dashboard/`:

```bash
cd src/dashboard
npm run build
npm run a11y:baseline
npm run a11y:check
npm run a11y:check:empty
npm run a11y:check:loading
npm run test
```

**Where baselines land (full paths):**
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/tests/a11y/baseline-findings-storyline-default.json` (new — written by `npm run a11y:baseline`)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/tests/a11y/ACCEPTED-VIOLATIONS.md` (regenerated, new `## findings-storyline` section expected)
- Existing untouched baselines to diff-check as empty: `tests/a11y/baseline-findings-empty.json`, `tests/a11y/baseline-findings-loading.json`

**Markers confirming the OPENED DRAWER was captured (not a 404/error state):**
- Visually: `cd src/dashboard && VITE_A11Y_FIXTURE=1 npm run preview`, open `http://localhost:4173/findings`, click the first row's `Storyline` button (`aria-label="Open storyline for TLS 1.0 Enabled at chaos-lab.local:443"`).
- Expect to see: the narrative text from `fixture-storyline.json` ("This TLS endpoint negotiates RSA-2048 key exchange…"); a `SCORE-LIFT ATTRIBUTION` panel with theme title "Eliminate plaintext HTTP exposure", `+7 pts when all 5 findings in this theme are resolved`, `2 of 5 findings in this theme are verified closed.`, and the disclaimer beginning "This is the theme's total lift".
- Must NOT see: `Could not load the storyline for this finding.` (would mean the fixture handler is not matching — baseline worthless) or `This finding is N of N in the theme.` (would mean a fabricated `finding_position`, contradicting A4).
- No `÷`, no per-finding "share" number, no third number between the lift and the count.
- In the harness log: no `FAIL [findings-storyline]: trigger ... not found` and no `awaitSelector ... never appeared` line.

**Axe violations reported by this capture:** Not yet known — `npm run a11y:baseline` has not been run (that is Task 3's job). The operator must paste the actual `entries` from the newly-written `baseline-findings-storyline-default.json` and review each row's auto-carried-forward (or newly-required) justification in `ACCEPTED-VIOLATIONS.md` before approving.

**STALE-before-regeneration transcript:** captured above under "Task 2 — freshness-test-fails-as-stale transcript" using a hand-written temporary demo file (not a real harness run), proving the derivation mechanism is live. This is NOT the real Task 3 regeneration — Task 3 must independently confirm `accepted-violations-freshness.test.ts` passes AFTER the real `npm run a11y:baseline` run.

**Also confirm per the plan's Task 3 action:**
- `git diff` on `baseline-findings-empty.json` and `baseline-findings-loading.json` is empty (moved baselines there would be a finding, not a regeneration).
- The harness log carries the explicit skip line for both non-default variants, e.g.: `[a11y] SKIP [findings-storyline] (route: findings, variant: empty): interaction skipped by design — no table rows in this variant` and the same for `variant: loading`.
- If `buildBaselineEntries`' `refusedCritical` path fires for `findings-storyline`, do NOT route around it — fix `findings.tsx` and rebuild statics before approving.

---
*Phase: 202-finding-storyline-drawer*
*Plan 07 — PARTIAL, Tasks 1-2 of 3 complete*
*Completed: 2026-09-12*

## Self-Check: PASSED

All created/modified files confirmed present on disk; both task commit hashes (`5fcd4726`, `99691ee3`) confirmed present in `git log`.

---

## Task 3 — CHECKPOINT DISCHARGED (operator-approved 2026-09-12)

The blocking human-verify checkpoint is **approved**. The orchestrator ran the mechanical half
(build, baseline capture, gate runs) so the operator confirmed real evidence rather than running it
blind; the operator then gave explicit approval. This plan is now 3/3, not the partial 2/3 recorded above.

**The capture demonstrably baselined the OPENED DRAWER, not a 404 or error state.** Proof is the axe
evidence sample itself: `<div class="mt-4 flex-1 overflow-y-auto min-h-0 space-y-4 text-sm">` — the
scroll region 202-06 added *inside* the Sheet. An unmatched fixture request would have 404'd and
baselined the error state, which cannot contain that selector. F10b's handler worked.

**One real, phase-introduced a11y defect was found and FIXED (commit `9e51519a`).**
`scrollable-region-focusable`, impact serious, WCAG 2.1.1/2.1.3 — the drawer body scrolled but could
not take keyboard focus. Closed with `tabIndex={0}` plus a comment recording why it is required
rather than decorative.

Fixed rather than ledgered, deliberately: `ACCEPTED-VIOLATIONS.md` already accepts this same rule on
`/data-at-rest` and `/hardware`, but those are the shared shadcn Table wrapper
(`components/ui/table.tsx:9`) whose fix is an app-wide focus-order change. This container is
single-site and owned by this phase, so the blast-radius justification does not transfer. Accepting it
would also have meant defending a brand-new serious keyboard violation against success criterion 4,
and `accepted-violations-freshness.test.ts:73` hard-fails on a placeholder justification regardless.

**Post-fix evidence:**
- `findings-storyline` baseline: **0 rule(s)**, `entries: []`, console **0**
- console 0 confirms Radix's `DescriptionWarning` never fired — F8 satisfied by the real
  `SheetDescription`, NOT by a `console-allowlist.json` entry (none was added)
- `accepted-violations-freshness` + `fixture-coverage`: **14/14 green** against the ORIGINAL ledger
  (a 0-entry baseline needs no ledger section)
- frontend suite: 49/49 files, exit 0, re-run 3×

**Deliberately NOT committed — unrelated baseline churn.** `npm run a11y:baseline` regenerates every
baseline. Eleven others were timestamp-only. The twelfth,
`baseline-data-at-rest-default.json`, changed `count: 2` -> `count: 1` with zero changes to
`data-at-rest.tsx` or `components/ui/table.tsx` — exactly the render-dependence its own justification
documents ("only fires on a container *actually overflowing* at render time ... inherently
render-dependent, not a fixed structural constant"). The committed `2` came from a GitHub-hosted CI
render; this local macOS render sees `1`, so committing the local value would have reddened CI on an
unrelated route. All 13 were restored. **This is the third observation of that fragility
(2026-08-27: 1, 2026-09-02: 2, 2026-09-12: 1) and strengthens the existing follow-up to replace the
exact-count pin with a tolerance range.**

**Honest gap, recorded not resolved:** one frontend test failed on the first post-fix run, and the
orchestrator's own log trimming (`tail -5`) discarded its name before it was read. It did not
reproduce across 3 subsequent full-suite runs (exit 0 each) or 3 focus-suite runs (40 passed / 2
skipped each). Unidentified, not diagnosed — 202-08 should note it in `deferred-items.md` rather than
treat it as closed.

**Process note for the phase close:** plan 202-03's executor ran `git stash --include-untracked`,
which the executor contract prohibits. It self-reported, popped immediately, and no work was lost
(verified: no stash entries remain, tree clean, STATE.md md5 unchanged). Worth recording because a
self-reported near-miss is more useful than a silent one.
