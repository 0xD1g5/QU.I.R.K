---
phase: 43-dashboard-polish
reviewed: 2026-05-02T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - .github/workflows/dashboard-quality.yml
  - quirk/dashboard/api/routes/pdf.py
  - src/dashboard/src/components/EmptyStateCard.tsx
  - src/dashboard/src/components/PageSpinner.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/pages/cbom.skeleton.tsx
  - src/dashboard/src/pages/cbom.tsx
  - src/dashboard/src/pages/certificates.skeleton.tsx
  - src/dashboard/src/pages/certificates.tsx
  - src/dashboard/src/pages/data-at-rest.tsx
  - src/dashboard/src/pages/executive.tsx
  - src/dashboard/src/pages/findings.skeleton.tsx
  - src/dashboard/src/pages/findings.tsx
  - src/dashboard/src/pages/identity.skeleton.tsx
  - src/dashboard/src/pages/identity.tsx
  - src/dashboard/src/pages/motion.tsx
  - src/dashboard/src/pages/print.tsx
  - src/dashboard/src/pages/roadmap.tsx
  - src/dashboard/src/pages/trends.tsx
  - src/dashboard/tests/a11y/run-a11y.mjs
findings:
  critical: 3
  warning: 6
  info: 3
  total: 12
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-05-02
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed 20 files spanning the PDF export route, the a11y test harness, all dashboard page
components, and the CI workflow. The implementation is largely solid — skeletons, empty states,
and the Cytoscape graph components are well-structured. However, four categories of defects
require attention:

1. **pdf.py** has a data-race between Playwright's `networkidle` signal and React's async data
   render, an unhandled `ValueError` outside the try block, and `browser.close()` not in a
   `finally` guard.
2. **run-a11y.mjs** uses variant-blind baseline lookup — empty-fixture runs silently swallow new
   violations, and the summary table misreports pass/fail status for routes with acknowledged
   baseline violations.
3. **findings.tsx / identity.tsx** render the pagination bar even when only one page exists —
   the `getPageCount() > 1` guard described in the review focus is absent.
4. **print.tsx** omits the `data_in_motion` subscore from the PDF executive summary, producing
   a PDF inconsistent with the interactive dashboard.

---

## Critical Issues

### CR-01: PDF export race condition — `networkidle` does not guarantee React render completion

**File:** `quirk/dashboard/api/routes/pdf.py:54-55`
**Issue:** `page.goto(wait_until="networkidle")` returns when no pending HTTP requests remain,
but the `/print` route loads scan data via a `useScanData()` hook that triggers a fetch
(`/api/scan/latest`) on mount. The response may arrive and React may still need several
synchronous render cycles before the DOM reflects the full scan data. Playwright's
`networkidle` fires as soon as the fetch response lands — before React has reconciled and
committed the final DOM tree. The immediately following `page.wait_for_load_state("networkidle")`
at line 55 is redundant (the page is already at networkidle) and does nothing to close this
gap.

`print.tsx` contains no data-ready sentinel attribute that Playwright could wait for. On slow
machines or with large data payloads, the captured PDF may contain incomplete tables or
placeholder content.

**Fix:**

Step 1 — Add a sentinel attribute to `print.tsx` on the outer wrapper:
```tsx
// print.tsx: add data-quirk-ready="true" to the outer div so Playwright
// can wait until React finishes rendering the full data tree.
<div
  data-quirk-ready="true"
  style={{ padding: "0 24px", maxWidth: 900, margin: "0 auto" }}
>
```

Step 2 — Replace the double `networkidle` wait with a sentinel wait in `pdf.py`:
```python
page.goto(print_url, wait_until="domcontentloaded", timeout=30_000)
page.wait_for_selector("[data-quirk-ready='true']", timeout=15_000)
```
This guarantees React has finished rendering scan data before the PDF is captured.

---

### CR-02: `int()` on `QUIRK_SERVE_PORT` executes outside the `try` block — unhandled `ValueError`

**File:** `quirk/dashboard/api/routes/pdf.py:45`
**Issue:** Line 45 runs before the `try` block that starts at line 48:

```python
port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))   # line 45 — OUTSIDE try
print_url = f"http://127.0.0.1:{port}/print"

try:                                                       # line 48
    with sync_playwright() as p:
```

If `QUIRK_SERVE_PORT` contains a non-numeric value, `int()` raises `ValueError`. FastAPI's
default exception handler catches it and returns a generic HTTP 500 with no actionable
message, bypassing the structured JSON error format the route handler is designed to produce.

**Fix:** Move port resolution inside the try block or add a dedicated validation guard:
```python
try:
    port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
except ValueError:
    return Response(
        content=json.dumps({"detail": "QUIRK_SERVE_PORT is not a valid integer."}).encode(),
        status_code=500,
        media_type="application/json",
    )
print_url = f"http://127.0.0.1:{port}/print"

try:
    with sync_playwright() as p:
        ...
```

---

### CR-03: a11y empty-fixture check uses wrong baseline — empty-state violations silently swallowed

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:160-168`
**Issue:** When `npm run a11y:check:empty` runs, the harness renders each route with the
empty-state fixture. Empty-state pages render entirely different DOM trees from the
happy-fixture pages (e.g., `EmptyStateCard` instead of data tables). The baseline lookup at
line 165 always loads `baseline-{slug}.json` — the baseline written for the happy-fixture
variant — regardless of which fixture variant is active.

No `baseline-{slug}-empty.json` files exist. When the happy-fixture baseline is absent for
a given route (the fallback at line 167-168 returns `{ violations: [] }`), all empty-fixture
violations appear as new and correctly trigger a failure. But when the happy-fixture baseline
exists and shares rule ids/targets with empty-fixture violations, those violations are silently
suppressed. The behaviour is variant-dependent and unpredictable. The acknowledged `TODO` at
line 164 documents the gap but the current code gives a false sense of coverage.

**Fix:** Make the baseline path variant-aware:
```js
const variant = process.env.VITE_A11Y_FIXTURE_VARIANT || 'default'
const baselinePath = resolve(A11Y_DIR, `baseline-${slug}-${variant}.json`)
const baseline = existsSync(baselinePath)
  ? JSON.parse(readFileSync(baselinePath, 'utf8'))
  : { violations: [] }
```
Add a corresponding `a11y:baseline:empty` npm script and generate initial empty-variant
baselines. Remove the TODO comment once implemented.

---

## Warnings

### WR-01: `browser.close()` not guarded by `finally` — skipped on `page.pdf()` exception

**File:** `quirk/dashboard/api/routes/pdf.py:62`
**Issue:** `browser.close()` at line 62 is called inside the `with sync_playwright()` block
but is not in a `finally` clause. If `page.pdf()` raises (page crash, OOM, render timeout),
`browser.close()` is skipped. The `sync_playwright()` context manager's `__exit__` eventually
terminates the Playwright subprocess forcibly, but without flushing the browser's state. This
can leave temporary Chrome profile directories on disk and suppresses any graceful shutdown
errors.

**Fix:**
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        context = browser.new_context()
        page = context.new_page()
        page.goto(print_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector("[data-quirk-ready='true']", timeout=15_000)
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "16mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
        )
    finally:
        browser.close()
```

---

### WR-02: Pagination bar rendered unconditionally — `getPageCount() > 1` guard is absent

**File:** `src/dashboard/src/pages/findings.tsx:179-186`
**File:** `src/dashboard/src/pages/identity.tsx:188-195`
**Issue:** Both pages render "Page 1 of 1" and disabled Previous/Next buttons whenever the
total results fit on a single page. The review focus specifically called out whether this
guard is present — it is not. Users with fewer than 25 findings (the `initialState` page
size) see a redundant, always-disabled pagination row.

**Fix** (apply identically to both files):
```tsx
{/* Pagination controls — only shown when data spans multiple pages */}
{table.getPageCount() > 1 && (
  <div className="flex items-center justify-between text-sm text-muted-foreground mt-2">
    <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
    <div className="flex gap-2">
      <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</Button>
      <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</Button>
    </div>
  </div>
)}
```

---

### WR-03: `print.tsx` omits `data_in_motion` subscore from PDF executive summary

**File:** `src/dashboard/src/pages/print.tsx:193-212`
**Issue:** The PDF executive summary renders five subscores: `hygiene`, `modern_tls`,
`identity_trust`, `agility_signals`, and `data_at_rest`. The `data_in_motion` subscore
shown in `executive.tsx` at line 153 is absent. Since `SubScores` in `types/api.ts:7` defines
`data_in_motion` as a non-optional field, the value is always present. The omission means a
PDF consumer sees a score breakdown that does not match the dashboard's interactive view.

**Fix:** Add the missing score item to the `score-row` div in `print.tsx`:
```tsx
<div className="score-item">
  <div className="score-number">{score.subscores.data_in_motion}</div>
  <div className="score-label">Data in Motion</div>
</div>
```

---

### WR-04: `data-at-rest.tsx` and `motion.tsx` table headers missing `scope="col"`

**File:** `src/dashboard/src/pages/data-at-rest.tsx:72-81`
**File:** `src/dashboard/src/pages/motion.tsx:52-59,134-140`
**Issue:** All `<TableHead>` elements in `data-at-rest.tsx` and `motion.tsx` omit
`scope="col"`. Every other page with data tables (`certificates.tsx`, `cbom.tsx`,
`findings.tsx`, `identity.tsx`) includes `scope="col"`. WCAG 1.3.1 (Level A) requires
column headers to be programmatically associated with their column for screen readers to
correctly announce cell context. The a11y baseline files for these routes currently record
existing violations, so this is a known gap being tracked — but it is listed here because
the inconsistency is pattern-level: the fix is clear and mechanical.

**Fix:** Add `scope="col"` to every `<TableHead>` in both files:
```tsx
<TableHead scope="col" className="text-xs font-semibold">Engine</TableHead>
```

---

### WR-05: Summary table in `run-a11y.mjs` misreports `FAIL` for routes with acknowledged violations

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:206,215`
**Issue:** Line 206 stores `results.violations.length` (total violations, including
baseline-acknowledged ones) in the per-route summary. Line 215 uses `violations === 0` to
decide whether to print `PASS` or `FAIL`. Since 7 of 9 routes have baseline violations
(cbom: 3 nodes, data-at-rest: 3 nodes, findings: 4 nodes, identity: 3 nodes, root: 1 node,
trends: 1 node), every clean check run prints `FAIL` in the human-readable summary for those
routes — even though the exit code is 0 and no new violations were introduced.

This is purely cosmetic but causes developer confusion when reading CI logs, as the summary
table appears to show failures on a green build.

**Fix:** Track per-route actual failure status separately:
```js
let routeFailed = false
// ... after diff check:
if (newViolations.length > 0) { exitCode = 1; routeFailed = true; ... }
// ... after console check:
if (unallowlisted.length > 0) { exitCode = 1; routeFailed = true; ... }

summary.push({ slug, violations: results.violations.length, console: unallowlisted.length, failed: routeFailed })

// In summary output:
const status = UPDATE_BASELINES ? 'WRITTEN' : s.failed ? 'FAIL' : 'PASS'
```

---

### WR-06: CI workflow hardcodes Chrome binary path instead of using action output

**File:** `.github/workflows/dashboard-quality.yml:43,48`
**Issue:** Both a11y steps set `PUPPETEER_EXECUTABLE_PATH: /usr/bin/google-chrome-stable`
as a literal string rather than using the `browser-actions/setup-chrome` action's
`chrome-path` output. If a future runner image or action version installs Chrome to a
different prefix, the hardcoded path silently fails with "binary not found" and the a11y
gate is broken.

**Fix:** Capture the action's output and reference it:
```yaml
- name: Install Chrome
  id: setup-chrome
  uses: browser-actions/setup-chrome@v1
  with:
    chrome-version: stable

- name: Run axe + console sweep (happy fixture)
  run: npm run a11y:check
  env:
    PUPPETEER_EXECUTABLE_PATH: ${{ steps.setup-chrome.outputs.chrome-path }}

- name: Run axe + console sweep (empty fixture)
  run: npm run a11y:check:empty
  env:
    PUPPETEER_EXECUTABLE_PATH: ${{ steps.setup-chrome.outputs.chrome-path }}
```

---

## Info

### IN-01: Double `networkidle` wait in `pdf.py` is dead code

**File:** `quirk/dashboard/api/routes/pdf.py:54-55`
**Issue:** `page.goto(wait_until="networkidle", timeout=30_000)` already blocks until the
network goes idle. The immediately following `page.wait_for_load_state("networkidle")` is a
no-op — the condition it waits for is already satisfied. It adds confusion about whether the
redundancy is intentional.
**Fix:** Remove `page.wait_for_load_state("networkidle")` at line 55. Replace both with the
sentinel-based wait described in CR-01.

---

### IN-02: `vite preview` stdout silently discarded — startup logs unavailable for CI debugging

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:84,87`
**Issue:** `previewProc` is spawned with `stdio: 'pipe'` but only `stderr` is forwarded to
`process.stderr`. Vite writes its "Local: http://..." ready message to stdout. In CI failure
scenarios (e.g., port already in use, vite startup crash), stdout output is unavailable for
diagnosis.
**Fix:**
```js
previewProc.stdout.on('data', d => process.stdout.write(d))
previewProc.stderr.on('data', d => process.stderr.write(d))
```

---

### IN-03: `print.tsx` crashes if API returns `roadmap: null` at runtime

**File:** `src/dashboard/src/pages/print.tsx:243`
**Issue:** Line 167 destructures `roadmap` from `data`. TypeScript types it as `RoadmapData`
(non-optional), so no compiler warning fires. However, an older scan record or a
partially-completed scan could return `roadmap: null` from the API at runtime. Line 243
then throws `TypeError: Cannot read properties of null (reading 'nodes')`.

`roadmap.tsx` guards defensively with `data?.roadmap?.nodes ?? []`. `print.tsx` does not.
**Fix:**
```tsx
<PrintRoadmap nodes={roadmap?.nodes ?? []} />
```

---

_Reviewed: 2026-05-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
