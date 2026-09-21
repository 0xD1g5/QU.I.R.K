| UAT-7-15 | `src/dashboard/src/pages/__tests__/roadmap-dag-visualization.test.tsx::"builds roadmap DAG elements with NOW NEXT and LATER horizon classes from the fixture"` | `roadmap.tsx`'s `PHASE_COLORS` map was collapsed so all three horizons resolve to the same value (`NOW`/`NEXT`/`LATER` all set to `"hsl(0, 72%, 51%)"`), removing the distinct NOW/NEXT/LATER color coding while leaving the per-node `phase` datum intact. | `AssertionError: expected 1 to be 3 // Object.is equality` (at `roadmap-dag-visualization.test.tsx:165`, `expect(new Set([nowColor, nextColor, laterColor]).size).toBe(3)`; diff `- 3 / + 1`) | 6fe84467 | f2cfcce6 |
| UAT-7-16 | `src/dashboard/src/pages/__tests__/roadmap-node-detail-panel.test.tsx::"opens the roadmap node detail panel with the tapped node's rationale owner and dependencies"` | `roadmap.tsx`'s `cy.on("tap", "node", ...)` handler body was changed from `setSelected(nodeById[nodeId] ?? null)` to `setSelected(nodes[0] ?? null)`, so the panel always shows the first roadmap item regardless of which node was tapped. | `TestingLibraryElementError: Unable to find an element with the text: Migrate SSH host keys off RSA-2048. This could be because the text is broken up by multiple elements...` — the printed panel DOM showed the FIRST node's title (`Rotate expiring TLS certificates`), badge (`0-30 days`) and why text (`Three certificates expire within 30 days.`) instead of the tapped second node's | 6fe84467 | f2cfcce6 |

## Citations

UAT-7-15 -> `src/dashboard/src/pages/__tests__/roadmap-dag-visualization.test.tsx::"builds roadmap DAG elements with NOW NEXT and LATER horizon classes from the fixture"`
- **Partial coverage.** Two of the case's four Pass Criteria bullets are covered in full, one is
  covered only in part, and one is uncovered — all named verbatim in the Uncovered Pass Criteria
  section below.
- Covered: the elements array contains exactly one node element per fixture roadmap item, each
  carrying its own `phase` datum (`NOW` / `NEXT` / `LATER`, asserted individually per item and
  asserted mutually distinct across the three), and its own roadmap item title as `label`. The
  `style` array binds a separate `node[phase='NOW'|'NEXT'|'LATER']` selector per horizon, each with
  its own `background-color`, all three mutually distinct and all three distinct from the base
  `node` gray. Cross-phase edges (`rankOnly: "false"`) are present, every one resolves to a real
  node id on both ends, and their style rule carries `target-arrow-shape: "triangle"` (directed).
- Assertions run against the configuration object captured from the mocked `cytoscape()` call at
  run time. The file contains no `readFileSync` and no source-text regex.

UAT-7-16 -> `src/dashboard/src/pages/__tests__/roadmap-node-detail-panel.test.tsx::"opens the roadmap node detail panel with the tapped node's rationale owner and dependencies"`
- **Partial coverage.** Three of the case's five Pass Criteria bullets are covered; two are
  uncovered because the product renders neither — named verbatim below.
- Covered: tapping a node (by invoking the product's own handler, registered via
  `cy.on("tap", "node", ...)` and captured from the mock — not a fabricated panel) opens the detail
  panel, and the panel shows the **tapped** node's item title, its timeframe badge (`31-90 days`,
  scoped with `within(panel)` because the page legend also renders all three horizon labels), and
  its `why` evidence paragraph. The fixture holds two nodes in two different horizons and the test
  taps the **second**, then additionally asserts that none of the first node's title, why text, or
  timeframe label appears in the panel — so a panel hardcoded to the first item fails both halves.
  That negative half is exactly what the red-proof mutation above exercised.
- The file contains no `readFileSync` and no source-text regex.

## Uncovered Pass Criteria

Quoted verbatim from `docs/UAT-SERIES.md` (UAT-7-15 at line 3640, UAT-7-16 at line 3660). Plan
206-12 must carry these into each case's `**Notes:**` — an unqualified citation on either test
would be a false attestation per 206-CONTEXT.md § Honest Non-Conversion.

**UAT-7-15**

- "Clicking a node shows detail panel with `Why:` text and owner placeholder" — **covered in part
  only.** The detail-panel-opens and `Why:`-text halves are covered by UAT-7-16's own cited node
  above (`roadmap-node-detail-panel.test.tsx`), not by this file. The **owner placeholder** half is
  uncovered because the product renders no owner element at all — see the todo below.
- "Dependencies shown as directed edges" — **uncovered as stated.** Directed, arrowheaded edges
  are built and asserted, but they are *phase-sequencing* edges, not per-item dependency edges.
  `roadmap.tsx` ignores `data.roadmap.edges` entirely and synthesizes its own two edge families
  (`roadmap.tsx:107-142`); the backend's edges are themselves only the two phase-to-phase
  transitions (`quirk/dashboard/api/routes/scan.py:1316-1321`, `reason="Phase dependency"`). No
  item-to-item dependency model exists anywhere in the stack, so there is nothing to assert.
- Also structurally out of reach at this seam and NOT claimed: the rendered canvas itself — whether
  nodes are visibly drawn, their laid-out geometry, and edge routing. The mock captures the
  configuration handed to Cytoscape; it does not draw. This is the cytoscape partial-coverage
  licence D-A3 extends to the roadmap cases.

**UAT-7-16**

- "Owner placeholder shown" — **uncovered.** `grep -rni "owner"` returns zero matches in both
  `src/dashboard/src/pages/roadmap.tsx` and `src/dashboard/src/types/api.ts`. The panel
  (`roadmap.tsx:279-331`) renders only title, phase/timeframe badge, optional closure-state badge,
  optional score-lift badge and optional `why`. The `RoadmapNode` type has no `owner` field, and
  neither does the API schema (`quirk/dashboard/api/schemas.py`). No assertion was fabricated.
- "Dependency list shown (if any)" — **uncovered.** `grep -rni "depend"` returns zero matches in
  `roadmap.tsx`. There is no dependency list element and no dependency field on `RoadmapNode` —
  same root absence as UAT-7-15's dependency-edge bullet above.

Both are filed as a single product-gap todo at
`.planning/todos/pending/roadmap-detail-panel-owner-and-dependencies-absent.md` (per 206-CONTEXT.md
§ Specific Ideas: file, do not fix). Neither case can reach full PASS until that todo is actioned;
both should be dispositioned partial-PASS with these bullets named.

## Non-conversions

**UAT-7-29 — "Roadmap — Node Drag" — NOT CONVERTED. No test file was written. Stays GAP,
reclassified out of the jsdom-tractable set, routed to Phase 207's browser verdict.**

Blocker, in the form plan 206-12 needs for a GAP reason:

> Node drag is entirely internal to the real Cytoscape renderer. `roadmap.tsx` registers no drag,
> `grab`, `free`, `position`, or `dragfree` handler and never reads or writes node positions — it
> hands an `elements` array with no `position` key to `cytoscape()` and lets dagre lay the graph
> out. Every one of the case's five Pass Criteria ("Node moves smoothly during drag", "All
> connected edges update position in real-time", "Node stays in new position after release",
> "Other nodes not affected by the drag", "Layout does not reset on node release") is a property of
> the renderer's own hit-testing, position bookkeeping and repaint, none of which a mocked
> `cytoscape` module performs. Requires a real browser.

Deliberate choice of the plan's option (b) over option (a). Option (a) offered a data-layer
invariant — "every edge's `source` and `target` still resolve to nodes in the elements array
independent of node positions". That invariant is real and is in fact already asserted, as a
supporting assertion, inside UAT-7-15's cited node above. But it is **not** what UAT-7-29 claims:

1. It covers **zero** of the case's five Pass Criteria bullets. Citing it would leave a citation
   whose entire carve-out list is the case's whole criteria set — a false attestation by
   206-CONTEXT.md's own rule, not a partial one.
2. The phrase "after a position update" has no referent in this product. Positions do not exist in
   any state `roadmap.tsx` owns, so a test would have to synthesize a position-update event the
   product never handles and then assert that an array built before that event was dispatched is
   unchanged. That is faking the very thing under test — the exact bar 206-CONTEXT.md sets for an
   unconvertible case.

Per 206-CONTEXT.md § Honest Non-Conversion this case **stays GAP** (it does not become DEFERRED —
no substitute exists) and per the SC#3/SC#4 adjudication in § Specific Ideas it leaves the
jsdom-tractable set and joins the browser-only group alongside `UAT-7-01`, `UAT-7-17`, `UAT-7-32`.
**Record this reclassification explicitly in the denominator** — the jsdom-tractable series-7 count
drops from 28 by one here; do not silently redefine it.
