| UAT-7-30 | `src/dashboard/src/pages/__tests__/print-view-layout.test.tsx::"renders the print view as single-column print sections with page-break styling and no interactive controls"` | `print.tsx:26` — dropped the page-break rule: `".print-section{break-before:page;padding-top:24px}"` → `".print-section{padding-top:24px}"` | `AssertionError: expected 'body,html{background:#fff!important;c…' to contain '.print-section{break-before:page'` | `a42be4fa` | `78b09332` |
| UAT-7-30 | *(same node — second mutation, proving a different assertion)* | `print.tsx:442` — rendered `<button type="button">Refresh</button>` inside the print container, immediately above the Section 1 cover block | `AssertionError: expected [ <button type="button"></button> ] to have a length of +0 but got 1` | `a42be4fa` | `78b09332` |
| UAT-7-21 | `src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx::"finds no hardcoded hex or raw hsl color literals in the major dashboard page and shell components"` | `print.tsx:54` — injected `".rp-probe{color:#abcdef}"` into `PRINT_CSS` (node temporarily flipped from `it.fails` to `it` so the failure diff is readable) | `AssertionError: expected [ …(96) ] to deeply equal []`, whose diff gained exactly the injected site: `+ "pages/print.tsx:54  #abcdef -> #abcdef  (contrast on light bg: 1.65:1)"` (95 → 96) | `a42be4fa` | `78b09332` |

## Citations

UAT-7-30 -> `src/dashboard/src/pages/__tests__/print-view-layout.test.tsx::"renders the print view as single-column print sections with page-break styling and no interactive controls"`
UAT-7-30 -> `src/dashboard/src/__tests__/app-print-chrome.test.tsx::"renders the print page with NO sidebar on /print"`
UAT-7-21 -> `src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx::"finds no hardcoded hex or raw hsl color literals in the major dashboard page and shell components"`

**UAT-7-30 needs BOTH nodes cited.** The first covers Pass Criteria 2-6; the second covers
Pass Criterion 1, which cannot be honestly asserted from a `render(<PrintPage />)` (see the
next section for why). Neither node covers the case alone.

**206-12/206-13 must read the dispositions from the two sections below, not from the fact that
these nodes run green.** UAT-7-21's node is green *because it is `it.fails`* — that is a
recorded FAIL, not a pass.

## Uncovered Pass Criteria

### UAT-7-30 — criterion 1, covered but NOT by this plan's node

Verbatim from `docs/UAT-SERIES.md`:

> - No sidebar visible

`print-view-layout.test.tsx` does not assert this and must never be read as doing so.
`Sidebar` is not inside `PrintPage`'s own subtree — it is a sibling that `AppShell` mounts — so
an absence assertion at that mount point would be trivially true regardless of what the shell
does. It is covered instead by `app-print-chrome.test.tsx`, which renders the real `AppShell`
under `MemoryRouter` and pairs every absence assertion with a positive control on a dashboard
route.

**Recommended disposition for UAT-7-30: PASS**, citing both nodes. All six Pass Criteria are
covered and all six hold against current source.

### UAT-7-21 — criteria 3 and 4 are NOT covered by this plan's node

Verbatim from `docs/UAT-SERIES.md`:

> - Electric-blue (`#00D8FF` or design system equivalent) used for accents
> - Dark background palette consistent across all pages

The audit covers criteria 1 and 2 (token usage / no hardcoded `#hex` literals). It does not
assert the accent hue or cross-page palette consistency, both of which are computed-style
properties that a source scan cannot settle. They are moot for the disposition — criterion 2
already fails — but they are named here so the citation is not read as full coverage.

**Recommended disposition for UAT-7-21: FAIL** — see the violation inventory below.

## UAT-7-30 product defect evidence — SUPERSEDED, the defect is FIXED

**This section does not record a defect. It records that CONTEXT D-A2's defect no longer
exists, and that plan 206-12 must therefore NOT file a todo for it.**

D-A2 (gathered 2026-09-13) ruled UAT-7-30 a confirmed product defect: `/print` was a `<Route>`
inside `AppShell`, so the sidebar shipped into every exported PDF. The plan instructed this task
to re-confirm that by command rather than cite it forward. Re-running the four prescribed
commands at execution time (2026-09-21) **falsified it.** The commands and their literal output:

```
$ grep -n "Sidebar" src/dashboard/src/App.tsx
9:import { Sidebar } from "@/components/sidebar"
39: *   authenticated   → existing Sidebar + main routes tree (unchanged)
87:      <Sidebar />

$ grep -n "path=\"/print\"" src/dashboard/src/App.tsx
(no output — exit 1)

$ grep -rn "print:hidden\|@media print" src/dashboard/src/
src/dashboard/src/App.tsx:65:  // defined a `print:hidden` rule or an `@media print` block.
src/dashboard/src/__tests__/app-print-chrome.test.tsx:8: * `ml-12 lg:ml-60` content offset. Nothing in `src/` defines a `print:hidden`
src/dashboard/src/__tests__/app-print-chrome.test.tsx:9: * rule or an `@media print` block, so nothing suppressed it at print time.
src/dashboard/src/pages/__tests__/print-view-layout.test.tsx:20: * inside that shell, there is no `print:hidden` / `@media print` utility

$ grep -n "aside\|nav" src/dashboard/src/pages/print.tsx
380:  // and on unmount, so the attribute does not survive client-side navigation.
438:            QRAMM data unavailable — Q section omitted
```

Two of the four outputs contradict D-A2's premise, and the contradiction is the finding:

1. **`path="/print"` matches nothing.** D-A2 cites `/print` as a `<Route>` at `App.tsx:76`.
   It is no longer a route at all.
2. **The `print:hidden` / `@media print` hits are all comments and test prose**, three of them
   *describing the historical defect in the past tense* — including one in a regression test
   that did not exist when D-A2 was written.

The corrected picture, confirmed by reading the file rather than grepping it:

```
$ grep -n 'pathname.replace\|<Sidebar />' src/dashboard/src/App.tsx
80:  if (location.pathname.replace(/\/+$/, "") === "/print") {
87:      <Sidebar />
```

`App.tsx:80` returns `<PrintPage />` and exits **before** the shell containing `<Sidebar />` at
line 87 is ever constructed. The sidebar is not merely hidden on `/print` — it is never mounted.

**Cause of the staleness:** commit `93e5afb1`, *"fix(print): render /print without the dashboard
chrome"*, authored **2026-09-14 06:41:57 -0400** — one day *after* 206-CONTEXT.md was gathered
(2026-09-13) and before this phase reached wave 3. It is an ancestor of HEAD. Its message names
the same blast radius D-A2 did ("every PDF exported through POST /api/export/pdf carried the
navigation sidebar down its left edge") and states the fix was structural rather than CSS
precisely so a class rename cannot silently reintroduce it. It shipped with a 7-case regression
suite, `src/dashboard/src/__tests__/app-print-chrome.test.tsx`, red-proved at the time against
the pre-fix `App.tsx`. That suite runs green today (**7 passed**).

**Consequences for the rest of the phase:**

- **UAT-7-30's recommended disposition is PASS, not FAIL.** D-A2's FAIL instruction is obsolete.
- **206-12 must NOT file a `.planning/todos/pending/` entry for the print sidebar.** The todo
  D-A2 called for would describe an already-fixed defect.
- The PDF-export blast-radius note in D-A2 is likewise resolved by `93e5afb1`.
- D-A2's underlying reasoning was sound when written; only its facts expired. This is the
  general hazard the plan itself warned about in another direction — evidence re-confirmed by
  command at execution time, rather than cited forward, is what caught it.

## UAT-7-21 violation inventory — the case genuinely FAILS

The audit's detector is full strength: no allowlist, no baseline snapshot, no narrowed pattern.
Its assertion is `expect(violations).toEqual([])`, and it genuinely fails. As of **2026-09-21**
it finds **95 hardcoded colour literals across 10 of the audited files**:

| File | Literals | Nature |
|---|---|---|
| `pages/print.tsx` | 45 | The injected `PRINT_CSS` print stylesheet — a deliberately light, theme-independent client deliverable |
| `pages/trends.tsx` | 12 | Recharts series colours, raw `hsl(N N% N%)` triples |
| `pages/cbom.tsx` | 11 | Cytoscape node/edge style literals + one legend swatch inline style |
| `pages/executive.tsx` | 9 | Severity palette, `bg-[#d4893a]` Tailwind arbitrary values, one inline `style={{ color: "#d4893a" }}` |
| `pages/exposure-map.tsx` | 6 | `cssVar(...) \|\| "#hex"` fallbacks and a Cytoscape literal |
| `pages/healthcare.tsx` | 4 | Inline `style={{ color: "#4ba8a8" }}` on icons |
| `pages/sensors.tsx` | 3 | `bg-[#d4893a]` / `text-[#d4893a]` arbitrary values |
| `pages/roadmap.tsx` | 3 | Badge background literals |
| `pages/schedules.tsx` | 2 | `border-[#2b8a86]` / `text-[#2b8a86]` arbitrary values |
| `components/sidebar.tsx` | 0 | Clean — its only `#hex` text is inside a line comment, which the detector strips |

The verdict is robust to how the scope is drawn. UAT-7-21's criterion 2 is specifically about
*inline styles*; even under that narrowest possible reading the case still fails, on
`executive.tsx:545`, `healthcare.tsx:134/150/204`, `roadmap.tsx:296/305` and `cbom.tsx:436`.

`print.tsx`'s 45 are arguably by design — `/print` is a white-background client deliverable, not
a themed dashboard surface — so the honest headline for a remediation todo is **50 literals
across 9 dashboard page files**, with print.tsx's 45 reported separately. That breakdown is a
classification of the finding, not a narrowing of the detector: the audit reports all 95.

**Recommended disposition for UAT-7-21: FAIL**, with a remediation todo for the 50.

### Why the node is `it.fails`, and what that does and does not mean

A hard-red node would take `dashboard-quality.yml` and the UAT citation guard's vitest execution
leg down with it, obscuring the finding rather than publishing it. `it.fails` records the verdict
instead: the body runs, every assertion is evaluated, and nothing is ignored.

Both directions of that contract were proved, not assumed:

- **Sensitivity** — injecting one literal into a file inside the audited glob moved the reported
  set from 95 to 96 and named the exact new site (row 3 of the table above).
- **Contingency** — with the scan temporarily returning no source lines, the node went **red**
  with `Error: Expect test to fail`. The green result is therefore caused by real violations,
  not by a test that always throws.
- **Non-vacuity** — the glob guard is hoisted to module scope, where a throw is a collection
  error `it.fails` cannot absorb. Verified live: filtering the page glob to empty produced
  `Error: hardcoded-color-audit: only 1 files resolved — src/pages/ has far more than that`,
  with `Tests  no tests`.

When the product is fixed, this node goes red with `Expect test to fail` — that is the signal to
drop `.fails` and re-disposition UAT-7-21 to PASS.

## Deviations from the plan

1. **Filename is `hardcoded-color-audit.test.tsx`, not `.test.ts` as the plan specifies.**
   `tests/test_uat_disposition_integrity.py`'s `VITEST_REF_RE` only matches
   `...__tests__/[\w.-]+\.test\.tsx::"..."` — a citation to a `.test.ts` file is unresolvable by
   the guard. The plan's stated filename would have produced an uncitable artifact. The file
   contains no JSX; `.tsx` is purely to satisfy the citation grammar.

2. **The contrast helpers were extracted to `components/__tests__/color-contrast-helpers.ts`**
   (not a `*.test.ts`, so vitest does not collect it), and both pre-existing copies — in
   `muted-token-contrast-guard.test.ts` and `executive-tooltip-contrast-guard.test.ts` — now
   import from it. The plan authorised this ("extract them to a shared test helper module if
   that is cleaner, updating the existing guard to import from it"). Behaviour-preserving:
   those two guards run **16 passed** before and after. The audit reuses `contrastRatio` and
   `hslToHex` substantively — every reported violation is resolved to hex and scored against the
   light-theme background, which is what makes a raw `hsl()` triple and a `#hex` literal
   comparable in one inventory.

3. **No `.planning/todos/` entry was created by this plan** — per the plan's explicit
   instruction that 206-12 files todos. Note that the todo D-A2 asked for (print sidebar) must
   **not** be filed at all, and a **new** one is needed for UAT-7-21's 50 dashboard literals.
