# Phase 206: Red-Proof Ledger

**Method:** for each converted UAT case, temporarily mutate the PRODUCTION source the cited test
node exercises (never the test's own assertion — that would prove nothing about whether the test
checks real behaviour), run the cited node by name, observe it go red, then revert. Follow Phase
205-04's precedent exactly: a `TEMPORARY(206-NN): induce red-proof — REVERTED IN THE NEXT COMMIT`
commit immediately followed by its revert commit, so the red observation is in the git record, not
just asserted in prose.

| Case | Cited node | Mutation applied | Observed failure message | TEMPORARY commit | Revert commit |
|------|------------|-------------------|---------------------------|-------------------|----------------|
<!-- ASSEMBLED BY 206-12 FROM red-proof/206-RED-PROOF-*.md — DO NOT HAND-ADD ROWS -->
| UAT-7-03 | `src/dashboard/src/pages/__tests__/executive-score-gauge.test.tsx::"renders the executive score gauge with the fixture score, its rating label, and the confidence badge"` | Confidence badge ternary in `executive.tsx` changed to always render the literal string `TEMPORARY-206-02-BROKEN-CONFIDENCE` for the `HIGH` confidence rating branch, instead of `"High Confidence"`. | `TestingLibraryElementError: Unable to find an element with the text: High Confidence. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` | dc30e4e9 | 91cf84b6 |
| UAT-7-04 | `src/dashboard/src/pages/__tests__/executive-severity-chart.test.tsx::"renders one severity chart category label per severity present in the fixture with counts derived from the same fixture"` | `executive.tsx`'s `chartData` severity list changed from `["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]` to `["HIGH", "MEDIUM", "LOW", "INFO"]`, dropping the CRITICAL bucket entirely from the chart's y-axis categories. | `TestingLibraryElementError: Unable to find an element with the text: CRITICAL. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` | dc30e4e9 | 91cf84b6 |
| UAT-7-05 | `src/dashboard/src/pages/__tests__/executive-driver-cards.test.tsx::"renders four score driver cards whose subscores come from the fixture and sum to at most 100"` | The `<SubscoreSlot score={score.subscores.agility_signals} label="Agility" maxValue={25} />` gauge row in `executive.tsx`'s score-gauges Card was deleted, reducing the rendered driver count from four to three. | `TestingLibraryElementError: Unable to find an element with the text: Agility. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` | dc30e4e9 | 91cf84b6 |
| UAT-7-06 | `src/dashboard/src/pages/__tests__/findings-table-renders.test.tsx::"renders the findings table with its documented columns and one row per fixture finding"` | The `{ accessorKey: "protocol", header: "Protocol" }` column definition was deleted from `findings.tsx`'s memoized `columns` array, dropping the Protocol column entirely. | `TestingLibraryElementError: Unable to find an accessible element with the role "columnheader" and name "Protocol"` | d3eda8fb | 67ddcf9b |
| UAT-7-07 | `src/dashboard/src/pages/__tests__/findings-sorting.test.tsx::"toggles ascending and descending order when the Severity column header is clicked"` | The severity column's `ColumnDef` gained `sortingFn: () => 0`, a constant comparator so `getSortedRowModel()` never reorders rows regardless of click count. | `AssertionError: expected [ 'host-medium.example.com', …(3) ] to not deeply equal [ 'host-medium.example.com', …(3) ]` (at `expect(afterFirstClick).not.toEqual(initialOrder)`) | d3eda8fb | 67ddcf9b |
| UAT-7-24 | `src/dashboard/src/pages/__tests__/findings-pagination.test.tsx::"paginates the findings table at 25 rows per page and advances with the next control"` | `initialState.pagination.pageSize` was changed from `25` to `100`, so all 27 fixture rows rendered on a single page instead of paginating. | `AssertionError: expected 27 to be 25 // Object.is equality` (at `expect(page1Rows.length).toBe(PAGE_SIZE)`) | d3eda8fb | 67ddcf9b |
| UAT-7-08 | `src/dashboard/src/pages/__tests__/findings-filtering.test.tsx::"narrows the findings table to matching rows when a severity filter is applied"` | `findings.tsx`'s severity predicate was replaced with a constant-true one (`filtered.filter(() => true)`), so selecting CRITICAL left every row in place. | `AssertionError: expected [ 'crit-a.example.com', …(3) ] to deeply equal [ 'crit-a.example.com', …(1) ]` — received added `low-a.example.com` and `medium-a.example.com` (at `expect(afterFilter).toEqual([...CRITICAL_HOSTS].sort())`) | 69d05cc0 | 96592fca |
| UAT-7-09 | `src/dashboard/src/pages/__tests__/findings-detail-slideout.test.tsx::"opens the finding detail slide-out with the selected finding's fields when its row is clicked"` | The row `onClick` handler was changed from `openStoryline(row.original, row.id)` to `openStoryline(findings[0], row.id)`, so every row click opens the FIRST finding's drawer. | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Bravo finding about an undersized RSA key"` — the DOM dump shows the drawer heading is `"Alpha finding about session resumption"` instead | 69d05cc0 | 96592fca |
| UAT-7-37 | `src/dashboard/src/pages/__tests__/findings-protocol-filter.test.tsx::"combines the protocol filter with the severity filter to narrow the findings table"` | The protocol branch was changed to re-start from the unfiltered list (`filtered = data.findings.filter((f) => f.protocol === protocolFilter)`), so each filter still worked alone but the two no longer intersected. | `AssertionError: expected [ 'tls-crit.example.com', …(1) ] to deeply equal [ 'tls-crit.example.com' ]` — received added `tls-low.example.com` (at `expect(currentHostSet()).toEqual([TLS_CRIT])`, the TLS+CRITICAL intersection assertion) | 69d05cc0 | 96592fca |
| UAT-7-10 | `src/dashboard/src/pages/__tests__/certificates-inventory-table.test.tsx::"renders the certificate inventory table with its documented columns and expiry and self-signed indicators"` | `certificates.tsx`'s expiry-cell `AlertTriangle` render condition (`(daysToExpiry !== null && daysToExpiry < 30)`) was replaced with the constant `false`, so the icon never renders regardless of a certificate's expiry state. | `AssertionError: expected null not to be null` (at `expect(expiredExpiryCell.querySelector("svg")).not.toBeNull()`) | 2b798f94 | eb38442d |
| UAT-7-34 | `src/dashboard/src/pages/__tests__/identity-empty-state.test.tsx::"renders a Not Scanned state for each identity protocol card when identity findings are absent"` | `identity.tsx`'s `PROTOCOLS` constant was narrowed from `["KERBEROS", "SAML", "DNSSEC"]` to `["KERBEROS", "SAML"]`, so only two of the three protocol summary cards render. | `TestingLibraryElementError: Unable to find an element with the text: DNSSEC` (at `screen.getByText(label)` for `label = "DNSSEC"`) | 2b798f94 | eb38442d |
| UAT-7-25 | `src/dashboard/src/pages/__tests__/cbom-algorithm-search.test.tsx::"filters the CBOM algorithm table case-insensitively as the search box is typed into"` | `cbom.tsx`'s `CbomTable` search predicate `c.algorithm.toLowerCase().includes(search.toLowerCase())` was replaced with the case-sensitive `c.algorithm.includes(search)`, so a lowercase query no longer matches an uppercase-stored algorithm name. | `TestingLibraryElementError: Unable to find an element with the text: AES-256-GCM. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` (at `expect(screen.getByText("AES-256-GCM")).toBeInTheDocument()` after typing the lowercase query `"aes"`) | 8a7eef19 | 55df8784 |
| UAT-7-26 | `src/dashboard/src/pages/__tests__/cbom-quantum-safety-filter.test.tsx::"filters the CBOM algorithm table to the selected quantum-safety classification"` | `cbom.tsx`'s `CbomTable` filter predicate `const matchQs = qsFilter === "all" \|\| c.quantum_safety === qsFilter` was replaced with the constant `const matchQs = true`, so selecting a quantum-safety classification from the dropdown no longer narrows the table at all. | `Error: expect(element).not.toBeInTheDocument() — expected document not to contain element, found <td class="...">AES-256-GCM</td> instead` (at `expect(screen.queryByText("AES-256-GCM")).not.toBeInTheDocument()` after selecting "Vulnerable") | 04a2cd68 | e1e62bc8 |
| UAT-7-14 | `src/dashboard/src/pages/__tests__/cbom-graph-visualization.test.tsx::"builds the CBOM graph elements from the fixture with one node per algorithm and asset"` | `cbom.tsx`'s `CbomGraph` elements builder had its source-system node guard `if (!systemsSeen.has(sys)) {` replaced with `if (false) {`, so asset (source system) nodes were never pushed into the `elements` array and every algorithm→system edge lost its target node. | `AssertionError: expected [ …(3) ] to have a length of 6 but got 3` (at `expect(nodeElements).toHaveLength(expectedAlgorithms.length + expectedSystems.length)`, `cbom-graph-visualization.test.tsx:130`) | 77e111ec | 35a94129 |
| UAT-7-27 | `src/dashboard/src/pages/__tests__/cbom-graph-node-interaction.test.tsx::"updates the CBOM detail panel with the tapped node's type-specific fields"` | `cbom.tsx`'s `cy.on("tap", "node", ...)` handler had `const d = node.data()` replaced with `const d = elements.find((e) => e.group === "nodes")!.data`, so the detail panel always rendered the FIRST built node regardless of which node was tapped. | `Unable to find an element with the text: RSA-2048. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` — the dumped panel markup showed `<span class="font-semibold font-mono text-xs break-all leading-snug">AES-256-GCM</span>`, i.e. the first fixture node instead of the tapped second one (at `expect(within(panel).getByText(rsa.algorithm)).toBeInTheDocument()`) | 7ea512e8 | 03d43525 |
| UAT-7-28 | `src/dashboard/src/pages/__tests__/cbom-graph-zoom-controls.test.tsx::"calls the cytoscape zoom and fit APIs when the CBOM zoom controls are used"` | `cbom.tsx`'s zoom-in button had `onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}` replaced with `onClick={() => {}}`, so clicking "Zoom in" issued no zoom write to the cytoscape instance. | `AssertionError: expected [] to have a length of 1 but got +0` (at `expect(writes).toHaveLength(1)` after `await user.click(screen.getByRole("button", { name: "Zoom in" }))`, `cbom-graph-zoom-controls.test.tsx:116`) | 95e34535 | 7db2daea |
| UAT-7-15 | `src/dashboard/src/pages/__tests__/roadmap-dag-visualization.test.tsx::"builds roadmap DAG elements with NOW NEXT and LATER horizon classes from the fixture"` | `roadmap.tsx`'s `PHASE_COLORS` map was collapsed so all three horizons resolve to the same value (`NOW`/`NEXT`/`LATER` all set to `"hsl(0, 72%, 51%)"`), removing the distinct NOW/NEXT/LATER color coding while leaving the per-node `phase` datum intact. | `AssertionError: expected 1 to be 3 // Object.is equality` (at `roadmap-dag-visualization.test.tsx:165`, `expect(new Set([nowColor, nextColor, laterColor]).size).toBe(3)`; diff `- 3 / + 1`) | 6fe84467 | f2cfcce6 |
| UAT-7-16 | `src/dashboard/src/pages/__tests__/roadmap-node-detail-panel.test.tsx::"opens the roadmap node detail panel with the tapped node's rationale owner and dependencies"` | `roadmap.tsx`'s `cy.on("tap", "node", ...)` handler body was changed from `setSelected(nodeById[nodeId] ?? null)` to `setSelected(nodes[0] ?? null)`, so the panel always shows the first roadmap item regardless of which node was tapped. | `TestingLibraryElementError: Unable to find an element with the text: Migrate SSH host keys off RSA-2048. This could be because the text is broken up by multiple elements...` — the printed panel DOM showed the FIRST node's title (`Rotate expiring TLS certificates`), badge (`0-30 days`) and why text (`Three certificates expire within 30 days.`) instead of the tapped second node's | 6fe84467 | f2cfcce6 |
| UAT-7-40 | `src/dashboard/src/pages/__tests__/hardware-advisory-banner.test.tsx::"renders the hardware advisory banner text from the fixture drift data"` | `hardware.tsx`'s unconditional advisory `<div role="note">…Hardware findings are advisory-only and do not affect the readiness score.</div>` block was deleted outright, so the page renders with no advisory banner while every other element is untouched. | `TestingLibraryElementError: Unable to find an accessible element with the role "note"` (at `screen.getAllByRole("note")`) | 49a5aa2b | f4e1b775 |
| UAT-7-41 | `src/dashboard/src/pages/__tests__/hardware-device-table.test.tsx::"renders the hardware device table with its documented columns and tier badges in fixture order"` | Ordering mutation: `hardware.tsx`'s `sorted` comparator was reversed on both keys (`TIER_ORDER[b] - TIER_ORDER[a] \|\| b.vendor.localeCompare(a.vendor)`), so every row still renders with its own correct data and only the row ORDER — the property UAT-7-41 names — changes. | `AssertionError: expected [ 'Zebra', 'Aruba', 'Fortinet', …(2) ] to deeply equal [ 'Cisco', 'HPE', 'Fortinet', …(2) ]` (at `expect(renderedVendorOrder).toEqual(EXPECTED_DISPLAY_ORDER)`) | 49a5aa2b | f4e1b775 |
| UAT-7-20 | `src/dashboard/src/__tests__/shell-spa-routing.test.tsx::"renders the findings page from the app route table when navigating directly to slash findings"` | `App.tsx`'s real route table entry `<Route path="/findings" element={<FindingsPage />} />` re-pointed at `element={<ExecutivePage />}`, so `/findings` resolves to the wrong page component. | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Findings"` | 705e9c39 | 472878a8 |
| UAT-7-22 | `src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx::"switches the theme and persists the selection to localStorage when the theme toggle is used"` | `theme-provider.tsx`'s `setTheme` had its `localStorage.setItem(storageKey, t)` line removed, so the theme still switches on the document but is never persisted. | `AssertionError: expected null to be 'light' // Object.is equality` | 705e9c39 | 472878a8 |
| UAT-7-31 | `src/dashboard/src/components/__tests__/dashboard-branding.test.tsx::"renders the QUIRK wordmark in the sidebar and the configured document title"` | The full wordmark text node inside `sidebar.tsx`'s logo `<span className="text-accent font-black ... font-mono">` blanked to whitespace, leaving the `Q` monogram in place. | `TestingLibraryElementError: Unable to find an element with the text: QU.I.R.K.. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` | 705e9c39 | 472878a8 |
| UAT-7-30 | `src/dashboard/src/pages/__tests__/print-view-layout.test.tsx::"renders the print view as single-column print sections with page-break styling and no interactive controls"` | `print.tsx:26` — dropped the page-break rule: `".print-section{break-before:page;padding-top:24px}"` → `".print-section{padding-top:24px}"` | `AssertionError: expected 'body,html{background:#fff!important;c…' to contain '.print-section{break-before:page'` | `a42be4fa` | `78b09332` |
| UAT-7-30 | *(same node — second mutation, proving a different assertion)* | `print.tsx:442` — rendered `<button type="button">Refresh</button>` inside the print container, immediately above the Section 1 cover block | `AssertionError: expected [ <button type="button"></button> ] to have a length of +0 but got 1` | `a42be4fa` | `78b09332` |
| UAT-7-21 | `src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx::"finds no hardcoded hex or raw hsl color literals in the major dashboard page and shell components"` | `print.tsx:54` — injected `".rp-probe{color:#abcdef}"` into `PRINT_CSS` (node temporarily flipped from `it.fails` to `it` so the failure diff is readable) | `AssertionError: expected [ …(96) ] to deeply equal []`, whose diff gained exactly the injected site: `+ "pages/print.tsx:54  #abcdef -> #abcdef  (contrast on light bg: 1.65:1)"` (95 → 96) | `a42be4fa` | `78b09332` |

## Tally

Every number below was derived at run time by the command beside it, on 2026-09-21, from the ten
fragments under `red-proof/` and from `git`. **No number here was read off `206-CONTEXT.md`, the
ROADMAP, or any plan's prose.** Nothing is reconciled toward 28.

| Quantity | Value | Derivation command |
|---|---|---|
| Converted cases (distinct case IDs across all fragments' `## Citations` sections) | **25** | `grep -h '^UAT-7-[0-9]* ->' red-proof/206-RED-PROOF-*.md \| sed 's/ ->.*//' \| sort -u \| wc -l` |
| Cited test nodes (citation lines; ≥ converted cases, because one case may need two nodes) | **26** | `grep -hc '^UAT-7-[0-9]* ->' red-proof/206-RED-PROOF-*.md` summed |
| Red-proved cases (distinct case IDs in this ledger's body rows) | **25** | `grep -o '^\| UAT-7-[0-9]*' 206-RED-PROOF.md \| sort -u \| wc -l` |
| Ledger body rows (≥ red-proved cases, because one case may carry two mutations) | **26** | `grep -c '^\| UAT-7-' 206-RED-PROOF.md` |
| Honestly non-converted (no test written) | **3** — `UAT-7-12`, `UAT-7-23`, `UAT-7-29` | set difference: the 28-case inventory in `206-CONTEXT.md` § domain minus the 25 derived above |
| Reclassified OUT of the jsdom-tractable set | **2** — `UAT-7-23`, `UAT-7-29` | `grep -l 'jsdom-tractable set' red-proof/*.md` → `roadmap`, `shell` (a narrower pattern quoting the bolded phrase verbatim returns only `roadmap` — the `shell` fragment bolds it as `**leaves the jsdom-tractable set**`, so the `**` breaks the match; this is why the loose form is the one recorded) |
| TEMPORARY red-proof commits | **13** | `git log --oneline --grep='^TEMPORARY(206-' \| wc -l` |
| Matching revert commits | **13** | `git log --oneline --grep='Revert "TEMPORARY(206-' \| wc -l` |

### Reconciliation of the two counts SC#2 requires to be equal

The plan requires "converted cases equals red-proved cases". **They are equal, at 25.** The raw
row count (26) and the raw citation-line count (26) both exceed 25 by exactly one, for the same
single reason, recorded here rather than smoothed over:

- **`UAT-7-30` carries TWO citation lines and TWO body rows.** Its two nodes are
  `print-view-layout.test.tsx` (Pass Criteria 2-6) and `app-print-chrome.test.tsx` (Pass
  Criterion 1, "No sidebar visible") — the print-style fragment states explicitly that "neither
  node covers the case alone". Its two rows are two *different* mutations against the *first*
  node, proving two different assertions in it (the page-break rule, and the no-interactive-
  controls assertion).

Neither excess is a hand-added row and neither is an uncited row: every body-row case ID appears in
a `## Citations` section, and every cited case ID has at least one body row. Verified:

```
$ comm -3 <(grep -o '^| UAT-7-[0-9]*' 206-RED-PROOF.md | sed 's/^| //' | sort -u) \
          <(grep -h '^UAT-7-[0-9]* ->' red-proof/*.md | sed 's/ ->.*//' | sort -u)
(no output — the two sets are identical)
```

### Git-trail verification

All 13 TEMPORARY commits and all 13 reverts resolve, and each row's pair is
`TEMPORARY(206-NN)` / `Revert "TEMPORARY(206-NN)"` with the **same** plan number `NN` as the
fragment that recorded it. Every SHA cited in the 26 rows passed `git cat-file -e <sha>^{commit}`.

One caution for a future reader: `git log --grep="TEMPORARY(206-"` (unanchored) returns **27**, not
26. The 27th is `5de6b563 test(206-05): red-prove UAT-7-10/7-34, …`, an ordinary plan commit whose
*body* quotes the string. Anchor the pattern (`--grep='^TEMPORARY(206-'`) to get the real 13.

### Fragment completeness

All ten fragments named in `red-proof/README.md` exist, and each one's row count matches the case
count its plan was assigned. No fragment is missing and no fragment is short:

| Fragment | Rows | Cases |
|---|---|---|
| `executive` | 3 | 7-03, 7-04, 7-05 |
| `findings-a` | 3 | 7-06, 7-07, 7-24 |
| `findings-b` | 3 | 7-08, 7-09, 7-37 |
| `certificates-identity` | 2 | 7-10, 7-34 (7-12 non-converted, evidence section only) |
| `cbom-table` | 2 | 7-25, 7-26 |
| `cbom-graph` | 3 | 7-14, 7-27, 7-28 |
| `roadmap` | 2 | 7-15, 7-16 (7-29 non-converted, evidence section only) |
| `hardware` | 2 | 7-40, 7-41 |
| `shell` | 3 | 7-20, 7-22, 7-31 (7-23 non-converted, evidence section only) |
| `print-style` | 3 | 7-30 (×2 mutations), 7-21 |
