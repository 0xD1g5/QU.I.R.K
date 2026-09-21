| UAT-7-14 | `src/dashboard/src/pages/__tests__/cbom-graph-visualization.test.tsx::"builds the CBOM graph elements from the fixture with one node per algorithm and asset"` | `cbom.tsx`'s `CbomGraph` elements builder had its source-system node guard `if (!systemsSeen.has(sys)) {` replaced with `if (false) {`, so asset (source system) nodes were never pushed into the `elements` array and every algorithm→system edge lost its target node. | `AssertionError: expected [ …(3) ] to have a length of 6 but got 3` (at `expect(nodeElements).toHaveLength(expectedAlgorithms.length + expectedSystems.length)`, `cbom-graph-visualization.test.tsx:130`) | 77e111ec | 35a94129 |
| UAT-7-27 | `src/dashboard/src/pages/__tests__/cbom-graph-node-interaction.test.tsx::"updates the CBOM detail panel with the tapped node's type-specific fields"` | `cbom.tsx`'s `cy.on("tap", "node", ...)` handler had `const d = node.data()` replaced with `const d = elements.find((e) => e.group === "nodes")!.data`, so the detail panel always rendered the FIRST built node regardless of which node was tapped. | `Unable to find an element with the text: RSA-2048. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` — the dumped panel markup showed `<span class="font-semibold font-mono text-xs break-all leading-snug">AES-256-GCM</span>`, i.e. the first fixture node instead of the tapped second one (at `expect(within(panel).getByText(rsa.algorithm)).toBeInTheDocument()`) | 7ea512e8 | 03d43525 |
| UAT-7-28 | `src/dashboard/src/pages/__tests__/cbom-graph-zoom-controls.test.tsx::"calls the cytoscape zoom and fit APIs when the CBOM zoom controls are used"` | `cbom.tsx`'s zoom-in button had `onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}` replaced with `onClick={() => {}}`, so clicking "Zoom in" issued no zoom write to the cytoscape instance. | `AssertionError: expected [] to have a length of 1 but got +0` (at `expect(writes).toHaveLength(1)` after `await user.click(screen.getByRole("button", { name: "Zoom in" }))`, `cbom-graph-zoom-controls.test.tsx:116`) | 95e34535 | 7db2daea |

## Citations

UAT-7-14 -> `src/dashboard/src/pages/__tests__/cbom-graph-visualization.test.tsx::"builds the CBOM graph elements from the fixture with one node per algorithm and asset"`
- **Partial coverage.** Asserted at the adapter seam — the `elements` array captured from the mocked
  `cytoscape()` constructor: one node per fixture algorithm and one per distinct source system (counts
  derived from the fixture, never hardcoded), each node carrying the identifier the fixture supplies,
  the built node-id set being exactly the algorithm ∪ system set, and every edge's `source` and
  `target` resolving to a node present in the same array. See `## Uncovered Pass Criteria` below —
  this citation must not be written into `docs/UAT-SERIES.md` without those bullets named in
  `**Notes:**`.

UAT-7-27 -> `src/dashboard/src/pages/__tests__/cbom-graph-node-interaction.test.tsx::"updates the CBOM detail panel with the tapped node's type-specific fields"`
- **Partial coverage.** The `tap`/`node` handler is captured from the mocked `cy.on(...)` registration
  and invoked with synthetic events carrying real built-node data: first an algorithm node that is
  deliberately the SECOND fixture component (so a panel pinned to the first node fails), then a source
  system node, asserting the panel switches type and that the algorithm-only fields are gone. See
  `## Uncovered Pass Criteria` below.

UAT-7-28 -> `src/dashboard/src/pages/__tests__/cbom-graph-zoom-controls.test.tsx::"calls the cytoscape zoom and fit APIs when the CBOM zoom controls are used"`
- **Partial coverage.** The real rendered zoom-in / zoom-out / fit buttons are clicked via `user-event`
  (never the handlers directly) and the mocked `cy.zoom(...)` / `cy.fit()` call records are asserted,
  including direction: the zoom-in write is strictly greater than the current level, the zoom-out write
  strictly smaller, and `fit()` issues no zoom write of its own. See `## Uncovered Pass Criteria` below.

## Uncovered Pass Criteria

Verbatim bullet text from `docs/UAT-SERIES.md`. Plan 206-12 must paste these into each case's
`**Notes:**` — an unqualified citation on any of these three tests would be a false attestation.

### UAT-7-14 (CBOM Page — Graph Visualization)

Covered (at the element-construction layer only):
- `Graph renders with visible nodes and edges` — covered **only as element construction**. The test
  proves the page builds node and edge elements and hands them to cytoscape; it does **not** prove
  anything is *visibly* rendered, because the engine is mocked and jsdom has no canvas.
- `At least 3 connected nodes visible` — covered **only as connectivity of the built elements**
  (the set of node ids reachable through the built edges is asserted ≥ 3). The word "visible" is
  not covered, for the same reason.

Not covered at all:
- `Nodes draggable`
- `Scroll-to-zoom works`
- `Clicking a node shows details panel or tooltip` — not asserted by *this* test. The detail-panel
  behaviour is covered separately by UAT-7-27's node-interaction test, but only via a synthetic
  handler invocation, never a real click on a rendered node.

### UAT-7-27 (CBOM Graph — Node Interaction)

Covered:
- `Algorithm node click shows: algorithm name, quantum-safety classification, connected source systems`
  — all three fields asserted, **but** the "click" is a direct invocation of the registered `tap`
  handler, not a real pointer event hit-testing a rendered node.
- `Source system node click shows: host:port or file path, connected algorithms` — same caveat on
  "click". The file-path variant of the label is not exercised; the fixture uses `host:port`.
- `Panel updates when clicking different nodes` — asserted by driving a second node of a different
  type and checking the algorithm-only fields disappear. Same caveat on "clicking".

Not covered at all:
- `Node colors match quantum-safety: green (Safe), amber (At Risk), red (Vulnerable)` — this test
  asserts detail-panel fields only. Node fill is applied by a cytoscape stylesheet
  (`"background-color": "data(color)"`) evaluated inside the mocked engine, so neither the rendered
  color nor its green/amber/red correspondence is observable here.

### UAT-7-28 (CBOM Graph — Zoom Controls)

Covered:
- `Zoom in/out buttons change zoom level visibly` — covered **only as the API call and its
  direction** (`cy.zoom(level)` with a strictly larger level on zoom-in, strictly smaller on
  zoom-out). The word "visibly" is not covered; no rendered viewport exists.
- `"Fit to Viewport" shows all nodes within visible area` — covered **only as the `cy.fit()`
  delegation**. Whether the resulting viewport actually contains every node is cytoscape-internal
  geometry and unreachable.

Not covered at all:
- `Mouse scroll wheel zooms` — the test asserts the page passes `userZoomingEnabled: true` into the
  cytoscape config, which is supporting evidence only; whether a wheel gesture then zooms is
  engine-internal and not claimed.
- `Click-drag on background pans the view` — same: `userPanningEnabled: true` is asserted in the
  config, the gesture itself is not.
- `No nodes disappear off-screen permanently`

## Disposition recommendation for plan 206-13

All three cases have a genuine, red-proved assertion at the adapter seam and are **citable as
partial coverage**, provided the verbatim bullet lists above are copied into their `**Notes:**`.
None of the three is recommended for an unqualified PASS, and none is recommended to stay GAP:
each one's covered fraction is the substantive data/adapter half of the case, not a formality.

The residue in all three cases is the same single blocker — **rendered-canvas behaviour (pixel
visibility, pointer hit-testing, drag, wheel, viewport geometry) is not observable with cytoscape
mocked under jsdom** — which is exactly the browser-only surface routed to Phase 207. No new
product defect was found by these three tests.
