---
phase: 206-dashboard-ui-coverage-drain
plan: 08
subsystem: testing
tags: [vitest, react-testing-library, dashboard, roadmap, cytoscape, uat-coverage]

requires:
  - phase: 206-01
    provides: test-setup.ts pointer-capture/scrollIntoView stubs
provides:
  - UAT-7-15 (roadmap DAG horizon coding) new vitest coverage, partial (owner-placeholder + dependency-edge bullets uncovered — features absent)
  - UAT-7-16 (roadmap node detail panel) new vitest coverage, partial (owner + dependency-list bullets uncovered — features absent)
  - UAT-7-29 (roadmap node drag) honest non-conversion, blocker named, reclassified out of the jsdom-tractable set
  - One todo: roadmap detail panel renders no owner and no dependency list; roadmap.tsx ignores data.roadmap.edges
affects: [206-12 (disposition flips + denominator reclassification), 206-13 (docs/UAT-SERIES.md edits)]

tech-stack:
  added: []
  patterns:
    - "Capture the cytoscape() CONFIG argument from the vi.mock ctor (capturedConfig) and assert the elements + style arrays — a new seam for this repo; prior roadmap/exposure-map tests only captured the tap handler"
    - "Reuse of roadmap-score-lift.test.tsx's captured-tap-handler pattern for node selection against a mocked cytoscape core"

key-files:
  created:
    - src/dashboard/src/pages/__tests__/roadmap-dag-visualization.test.tsx
    - src/dashboard/src/pages/__tests__/roadmap-node-detail-panel.test.tsx
    - .planning/todos/pending/roadmap-detail-panel-owner-and-dependencies-absent.md
    - .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-roadmap.md
  modified: []

key-decisions:
  - "UAT-7-29 took the plan's option (b) — NO test written. The option (a) edge-resolvability invariant covers zero of the case's five Pass Criteria bullets, and 'after a position update' has no referent in a product that never stores positions, so asserting it would require synthesizing an event the product never handles. Stays GAP, reclassified browser-only."
  - "UAT-7-16 covers 3 of its 5 Pass Criteria bullets, not 5. 'Owner placeholder shown' and 'Dependency list shown (if any)' are absent from the product AND from the RoadmapNode type AND from the API schema — a third absent-feature finding in this phase, after 206-05's two. Named verbatim as carve-outs, filed as a todo, not fabricated."
  - "UAT-7-15's color-coding bullet is asserted at the STYLE-BINDING seam (three distinct node[phase='...'] background colors) rather than on per-node data alone, because the horizon datum survives a color collapse — the data-only assertion would not have red-proved."
  - "UAT-7-15's 'Dependencies shown as directed edges' bullet is uncovered as stated: the arrows are phase-sequencing edges synthesized by roadmap.tsx, which ignores data.roadmap.edges entirely; no item-to-item dependency model exists in the frontend, the API type, or the backend route."

requirements-completed: [COV-04]

duration: ~30min
completed: 2026-09-21
---

# Phase 206 Plan 08: Roadmap (UAT-7-15 / 7-16 / 7-29) Summary

**Wrote 2 new vitest nodes covering UAT-7-15 (DAG horizon coding, partial) and UAT-7-16 (node detail
panel, partial), red-proved both against a real mutation of `roadmap.tsx`, and returned UAT-7-29 as a
deliberate honest non-conversion with its blocker named — discovering along the way that the roadmap's
"dependency" arrows are phase-sequencing edges with no dependency model behind them anywhere in the
stack.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 completed
- **Files:** 4 created (2 test files, 1 todo, 1 red-proof fragment); `roadmap.tsx` touched only
  transiently (mutated then reverted, byte-identical to the pre-plan SHA `68c048d0` afterward)

## Accomplishments

- `roadmap-dag-visualization.test.tsx` — one `it()` capturing the configuration object handed to
  `cytoscape()` and asserting: one node element per fixture item, each carrying its own `phase`
  datum and its own title as `label`; all three horizons present and mutually distinct; a
  `node[phase='NOW'|'NEXT'|'LATER']` style rule per horizon with three mutually distinct
  `background-color`s, none equal to the base node gray; and cross-phase directed edges whose
  `source`/`target` both resolve to real node ids, styled with `target-arrow-shape: "triangle"`.
- `roadmap-node-detail-panel.test.tsx` — one `it()` invoking the product's own
  `cy.on("tap", "node", ...)` handler with the **second** of two fixture nodes, asserting the panel
  opens with that node's title, its timeframe badge (`31-90 days`, scoped via `within(panel)` because
  the legend also renders all three labels), and its `why` paragraph — plus a negative half asserting
  none of the first node's title/why/timeframe leaks in.
- Both tests assert against captured runtime values. Neither contains `readFileSync`; the forbidden
  `cbom-cytoscape-catch.test.tsx` shape was not used.
- Red-proved both via one `TEMPORARY(206-08)` mutation commit + immediate revert, verbatim failure
  text captured in the fragment.
- UAT-7-29 deliberately not converted; blocker written in the form 206-12 needs for a GAP reason,
  plus an explicit note that the jsdom-tractable denominator drops by one.
- A new capture-the-config test seam for this repo — prior cytoscape tests (`exposure-map`,
  `roadmap-score-lift`) only captured the `tap` handler, never the constructor argument. That seam is
  what made UAT-7-15's color-coding bullet assertable at all.

## Red-Proof Evidence

| Case | Mutation to `src/dashboard/src/pages/roadmap.tsx` | Observed failure |
|---|---|---|
| UAT-7-15 | `PHASE_COLORS` collapsed — `NOW`/`NEXT`/`LATER` all set to `"hsl(0, 72%, 51%)"` | `AssertionError: expected 1 to be 3 // Object.is equality` at `roadmap-dag-visualization.test.tsx:165` |
| UAT-7-16 | tap handler body `setSelected(nodeById[nodeId] ?? null)` → `setSelected(nodes[0] ?? null)` | `TestingLibraryElementError: Unable to find an element with the text: Migrate SSH host keys off RSA-2048` — printed panel DOM showed the FIRST node throughout |

- **TEMPORARY commit:** `6fe84467` · **Revert:** `f2cfcce6`
- `git diff 68c048d0 -- src/dashboard/src/pages/roadmap.tsx` → **empty**
- `git diff --name-only 68c048d0..HEAD -- docs/` → **empty** (no fenced doc touched)

## Test Counts

- Cited nodes after revert: **2 passed, 0 failed** (`Test Files 2 passed (2) / Tests 2 passed (2)`)
- Full dashboard suite: **Test Files 70 passed (70) / Tests 445 passed | 2 skipped (447)**, 0 failed
- `npm run lint` → 0 errors (1 pre-existing warning in `ConnectorsPanel.test.tsx`, not this plan's)
- `npm run build` → `✓ built in 526ms`, exit 0, and produced no working-tree change (`roadmap.tsx`
  unchanged, so bundle hashes identical)

## Task Commits

1. **Task 1: UAT-7-15 DAG horizon-coding test** — `cdc680c3` (test)
2. **Task 2: UAT-7-16 detail-panel test + product todo** — `27591c1c` (test)
3. **Task 3: red-proof + fragment** — `6fe84467` (TEMPORARY) / `f2cfcce6` (revert) / `a72e3304` (fragment)

## UAT-7-29 Verdict — option (b), non-conversion

The plan offered two acceptable outcomes and asked for a stated choice. **Option (b) was chosen: no
test file exists; UAT-7-29 stays GAP.**

Option (a) proposed asserting that every edge's `source`/`target` still resolve to nodes "after a
position update". Two reasons that was rejected:

1. It covers **zero** of UAT-7-29's five Pass Criteria bullets. A citation whose carve-out list is
   the case's entire criteria set is a false attestation, not a partial one, under CONTEXT's rule.
   (The invariant itself is real and *is* asserted — as a supporting assertion inside UAT-7-15's
   node, where it is on-subject.)
2. "After a position update" has no referent here. `roadmap.tsx` registers no `grab`/`free`/
   `dragfree`/`position` handler (verified by grep — zero matches) and passes elements with no
   `position` key. A test would have to synthesize a position event the product never handles, then
   assert an array built before that event is unchanged — faking the thing under test, which is
   exactly CONTEXT's bar for unconvertible.

Per the SC#3/SC#4 adjudication, UAT-7-29 leaves the jsdom-tractable set and joins the browser-only
group (`UAT-7-01`, `UAT-7-17`, `UAT-7-32`). **206-12 must record this denominator change explicitly.**

## Deviations from Plan

### New Findings Beyond Plan Scope

**1. [Deviation — absent-feature discovery] UAT-7-16 covers 3 of 5 bullets, not 5.**

The plan's acceptance criteria required asserting **all five** of UAT-7-16's Pass Criteria bullets
and stated that owner and dependencies should be reachable. They are not — this is a product
absence, discovered by reading `roadmap.tsx` and `types/api.ts` in full per `<read_first>`:

- `grep -rni "owner" src/dashboard/src/pages/roadmap.tsx src/dashboard/src/types/api.ts` → 0 matches
- `grep -rni "depend" src/dashboard/src/pages/roadmap.tsx` → 0 matches
- `quirk/dashboard/api/schemas.py`'s `RoadmapNode` carries no owner or dependency field either

The plan anticipated this possibility ("If any bullet is genuinely unassertable at this seam, name it
verbatim in the roadmap fragment's uncovered-bullets section rather than citing the test
unqualified") and that escape hatch was taken: both bullets are quoted verbatim in the fragment's
`## Uncovered Pass Criteria` section, and a todo is filed. No assertion was fabricated. This is the
phase's third absent-feature finding, after 206-05's UAT-7-12 and self-signed-flag discoveries.

**2. [Deviation — deeper finding] The roadmap's "dependency" arrows are not dependencies.**

Found while assessing UAT-7-15's fourth bullet. `roadmap.tsx` **ignores `data.roadmap.edges`
entirely** and synthesizes its own two edge families at `roadmap.tsx:107-142` (invisible
within-phase rank edges + visible cross-phase arrows). The backend's edges are themselves only the
two phase-to-phase transitions (`quirk/dashboard/api/routes/scan.py:1316-1321`,
`reason="Phase dependency"`). So an operator seeing arrows in the DAG will read them as
prerequisite relationships between remediation items, and they are not — they encode time-horizon
sequencing. Recorded in the same todo with a proposed two-way fix (model real dependencies, or
relabel the arrows honestly). Not fixed here — product work, out of scope per CONTEXT.

**3. [Deviation — assertion seam changed, not weakened] UAT-7-15's color bullet is asserted on the
`style` array, not on node data alone.**

The plan's suggested red-proof mutation was "collapse all horizons to one class". A data-only
assertion (`data.phase` per node) would have survived that mutation, since `roadmap.tsx` keys color
off `node[phase='...']` **style selectors** while the `phase` datum stays intact. The test therefore
asserts both: the per-node datum *and* the three distinct style bindings. That is what actually went
red (`expected 1 to be 3`). A test that had only asserted the datum would have been green against a
product with no color coding at all — the precise failure this phase's red-proof discipline exists to
catch.

No Rule 4 (architectural) decision was needed; all findings were handled within Rules 1-3 plus the
plan's own named escape hatches.

## Known Stubs

None. This plan is test-only and introduced no UI stub, placeholder, or hardcoded empty value.

## Threat Flags

None. No network endpoint, auth path, file access pattern, or schema change. The plan's own register
(T-206-08-01 red-proof-must-not-ship, T-206-08-02 faked-drag spoofing) is mitigated as designed: the
pre-plan-SHA diff on `roadmap.tsx` is empty, and no drag event was synthesized anywhere — UAT-7-29
has no test file at all.

## Issues Encountered

None. Both tests passed on first run and went red as intended under mutation.

## Next Steps

- **206-12** reads this fragment's `## Citations` for UAT-7-15/7-16, its `## Non-conversions`
  section for UAT-7-29's GAP reason, and must record the jsdom-tractable denominator dropping by one
  (UAT-7-29 reclassified browser-only, alongside 206-10's UAT-7-23 reclassification).
- **206-13** flips UAT-7-15 and UAT-7-16 to partial-PASS in `docs/UAT-SERIES.md`, carrying the
  uncovered bullets verbatim into each case's `**Notes:**`, and rewrites UAT-7-29's GAP reason.
  This plan touched no file under `docs/`.
- One product-gap todo available for prioritization:
  `.planning/todos/pending/roadmap-detail-panel-owner-and-dependencies-absent.md`.

## Self-Check: PASSED

All 4 created files verified present on disk. All 5 cited commit hashes (`cdc680c3`, `27591c1c`,
`6fe84467`, `f2cfcce6`, `a72e3304`) verified present in `git log --oneline --all`.
