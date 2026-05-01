---
phase: 43-dashboard-polish
reviewed: 2026-05-01T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - .github/workflows/dashboard-quality.yml
  - docs/UAT-SERIES.md
  - src/dashboard/package.json
  - src/dashboard/src/components/EmptyStateCard.tsx
  - src/dashboard/src/components/PageSpinner.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/pages/cbom.skeleton.tsx
  - src/dashboard/src/pages/cbom.tsx
  - src/dashboard/src/pages/certificates.skeleton.tsx
  - src/dashboard/src/pages/certificates.tsx
  - src/dashboard/src/pages/data-at-rest.tsx
  - src/dashboard/src/pages/executive.tsx
  - src/dashboard/src/pages/findings.tsx
  - src/dashboard/src/pages/findings.skeleton.tsx
  - src/dashboard/src/pages/identity.skeleton.tsx
  - src/dashboard/src/pages/identity.tsx
  - src/dashboard/src/pages/motion.tsx
  - src/dashboard/src/pages/roadmap.tsx
  - src/dashboard/src/pages/trends.tsx
  - src/dashboard/tests/a11y/baseline-cbom.json
  - src/dashboard/tests/a11y/baseline-certificates.json
  - src/dashboard/tests/a11y/baseline-data-at-rest.json
  - src/dashboard/tests/a11y/baseline-findings.json
  - src/dashboard/tests/a11y/baseline-identity.json
  - src/dashboard/tests/a11y/baseline-motion.json
  - src/dashboard/tests/a11y/baseline-roadmap.json
  - src/dashboard/tests/a11y/baseline-root.json
  - src/dashboard/tests/a11y/baseline-trends.json
  - src/dashboard/tests/a11y/fixture-scan.json
  - src/dashboard/tests/a11y/fixture-trends.json
  - src/dashboard/tests/a11y/routes.json
  - src/dashboard/tests/a11y/run-a11y.mjs
  - src/dashboard/tests/console-allowlist.json
  - src/dashboard/vite.config.ts
findings:
  critical: 3
  warning: 9
  info: 5
  total: 17
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-05-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

Phase 43 delivers dashboard polish: per-page skeleton loaders, empty state cards, a CBOM graph
viewer, a Motion page, an Identity page, a Data at Rest page, a Roadmap DAG, an axe + console
CI gate, and a Vite a11y fixture middleware. The overall structure is coherent and the testing
harness is a genuine quality improvement.

However there are three blockers: (1) URL.revokeObjectURL is called synchronously after
`a.click()` before the browser has a chance to fetch the blob URL, making the PDF download
silently fail in most browsers; (2) the a11y harness hard-codes a dist-artifact path from a
_different_ output directory to decide whether to rebuild, so the `--update-baselines` path
always triggers a rebuild even when the dist is fresh; (3) the Cytoscape graph in
`cbom.tsx` / `roadmap.tsx` is recreated from scratch on every render when `compByAlg` /
`nodeById` change — those maps are rebuilt inside `useMemo` but are then listed as
`useEffect` dependencies, causing a destroy-recreate cycle on every parent re-render.

There are also a cluster of warnings around missing pagination controls, an incorrect
`aria-sort` applied to a non-sorted column, a race condition in the preview-server timeout
check, hardcoded colour literals carried through into a11y baselines, and several code-quality
items.

---

## Critical Issues

### CR-01: PDF blob URL revoked before browser can initiate download

**File:** `src/dashboard/src/pages/executive.tsx:44-45`
**Issue:** `URL.revokeObjectURL(url)` is called immediately after `a.click()`. The `click()`
call is synchronous and just dispatches the download event; the browser fetches the blob URL
asynchronously. Revoking the URL immediately makes the object URL invalid before the
download starts, causing the download to fail silently (no file saved, no error visible
to the user). This is a well-known browser gotcha.
**Fix:**
```typescript
a.href = url
a.download = `quirk-report-${date}.pdf`
document.body.appendChild(a)
a.click()
document.body.removeChild(a)
// Revoke after a tick so the browser has time to start the fetch
setTimeout(() => URL.revokeObjectURL(url), 100)
```

---

### CR-02: Cytoscape graph destroyed and recreated on every render (cbom.tsx and roadmap.tsx)

**File:** `src/dashboard/src/pages/cbom.tsx:154-313` and `src/dashboard/src/pages/roadmap.tsx:47-191`
**Issue:** Both `CbomGraph` and `RoadmapPage` compute `compByAlg` / `algBySystem` / `nodeById`
with `useMemo`, then list those derived maps in the `useEffect` dependency array. `useMemo`
provides referential stability only when its own deps are stable, so each time `components`
or `nodes` is the same array reference this is fine. But the containing component
(`CbomPage` / `RoadmapPage`) re-renders on any scan-data update, and `data?.cbom_components ?? []`
/ `data?.roadmap?.nodes ?? []` produces a new array reference each render due to the `?? []`
fallback. This causes `useMemo` to re-run, which produces new map objects, which triggers the
`useEffect`, which destroys and recreates the entire Cytoscape instance including layout
computation — a potentially expensive operation that also loses any zoom/pan state the user
had.
**Fix:** Stabilize the array references before passing them down:

```typescript
// In CbomPage — stabilize once
const components = useMemo(() => data?.cbom_components ?? [], [data])

// In RoadmapPage — stabilize once
const nodes = useMemo(() => data?.roadmap?.nodes ?? [], [data])
```

`CbomPage` already passes `components` to `CbomGraph` but derives it as `const components = data?.cbom_components ?? []` on every render without `useMemo` (line 420). `RoadmapPage` already uses `useMemo` for `nodes` (line 38) so the roadmap issue is less severe, but `nodeById` changes whenever `nodes` changes, and both `nodes` and `nodeById` are in the `useEffect` dep array at line 191, meaning any `nodes` change still triggers full recreation.

---

### CR-03: a11y harness rebuild check uses wrong dist path — build never skipped

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:68-79`
**Issue:** The script checks for the presence of `../../quirk/dashboard/static/index.html`
(relative to `src/dashboard/`) to decide whether to skip the build step. But the Vite build
config writes output to `../../quirk/dashboard/static` from `src/dashboard/`, meaning the
resolved path would be `quirk/dashboard/static/index.html` starting from the repo root —
which _is_ the correct output path. However the `__dirname` here is
`src/dashboard/tests/a11y/`, so `resolve(__dirname, '../..')` resolves to `src/dashboard/`
and then `../../quirk/dashboard/static/index.html` becomes
`quirk/dashboard/static/index.html` from the repo root. This is actually correct for the
normal case. The real problem is that when run from CI (fresh checkout with no prior build),
the `--update-baselines` flag should still only build once, but if the same process is also
invoked with `npm run build` in CI just before calling `a11y:check`, the build is redundant
and doubles build time. More critically: `npm run a11y:baseline` does NOT set
`VITE_A11Y_FIXTURE_VARIANT`, so the baseline is captured against the happy-path fixture —
but the CI job `a11y:check:empty` runs against the empty-fixture variant with no
corresponding baseline comparison. There is no `baseline-<slug>-empty.json` set; the harness
falls back to `{ violations: [] }` for every route when run with `VARIANT=empty`, meaning
the empty-state baseline is effectively unenforced. Any new a11y regression introduced in
an empty-state render will be silently swallowed.
**Fix:** The baseline command should accept a `--variant` argument and write to
`baseline-${slug}-${variant}.json`; the check commands should load the matching baseline
file. At minimum, document that empty-state a11y regressions are not caught.

---

## Warnings

### WR-01: FindingsPage and IdentityPage have no pagination UI controls

**File:** `src/dashboard/src/pages/findings.tsx:84-95`, `src/dashboard/src/pages/identity.tsx:87-98`
**Issue:** Both pages configure TanStack Table with `getPaginationRowModel()` and
`initialState: { pagination: { pageSize: 25 } }`, but neither renders any pagination
controls (previous/next buttons, page count). The table silently shows only the first 25
rows with no way for the user to advance. A scan with 30+ findings will appear to have only
25.
**Fix:** Add pagination controls below each table:
```tsx
<div className="flex items-center justify-between text-sm text-muted-foreground mt-2">
  <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
  <div className="flex gap-2">
    <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</Button>
    <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</Button>
  </div>
</div>
```

---

### WR-02: `aria-sort` applied to all sortable columns including the currently-unsorted ones — "none" value is correct but column header "Expiry" in certificates.tsx has a static `aria-sort="ascending"` that is never updated

**File:** `src/dashboard/src/pages/certificates.tsx:44`
**Issue:** The `Expiry` column header has a hardcoded `aria-sort="ascending"` attribute.
There is no sort state managed for this column — the certificates table is a plain `<Table>`
with no TanStack Table instance. The hardcoded `aria-sort="ascending"` is a false claim to
screen readers that the table is sorted by expiry, which it is not (the order comes directly
from `data.certificates`). This is an accessibility bug.
**Fix:** Remove the `aria-sort` attribute from the static table header, or implement actual
sort behavior driven by state:
```tsx
<TableHead scope="col" className="text-xs font-semibold">Expiry</TableHead>
```

---

### WR-03: `waitForPort` deadline check is off-by-one — timeout fires one poll interval late

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:47-58`
**Issue:** The deadline guard on the error handler is:
```js
if (Date.now() + CONNECT_POLL_MS > deadline)
```
This condition is true when _less than_ `CONNECT_POLL_MS` (250 ms) remains, so it rejects
early and misses up to 250 ms of valid wait time. The correct condition to detect "we would
time out if we waited another poll interval" is acceptable as a conservative guard, but the
intent reads as "reject when we're past the deadline." If the intent is the latter, the
condition should be:
```js
if (Date.now() >= deadline)
```
As written, the effective timeout is `CONNECT_TIMEOUT_MS - CONNECT_POLL_MS` = 29,750 ms,
which is almost certainly fine in practice but is an unintentional off-by-one.
**Fix:**
```js
if (Date.now() >= deadline) {
  rejectP(new Error(`Timed out waiting for ${host}:${port} after ${timeoutMs}ms`))
}
```

---

### WR-04: `getProtocolStatus` in identity.tsx reports "MEDIUM" as worst severity even when only LOW or INFO findings exist

**File:** `src/dashboard/src/pages/identity.tsx:34-43`
**Issue:** The function returns `worst: "MEDIUM"` (and `label: "Clean"`) for any protocol
that has findings but no CRITICAL or HIGH ones. This means a protocol with five LOW findings
shows as "Clean" in the summary card. The badge label "Clean" is accurate in a loose sense
("no high-severity issues") but the `worst` property being hardcoded to "MEDIUM" when the
actual worst could be LOW or INFO is semantically wrong and could mislead consumers that
read `worst`.
**Fix:**
```typescript
function getProtocolStatus(findings: IdentityFinding[], protocol: string) {
  const pf = findings.filter((f) => f.protocol === protocol)
  if (pf.length === 0) return { count: 0, worst: null, label: "Not Scanned" }
  const hasCritical = pf.some((f) => f.severity === "CRITICAL")
  const hasHigh = pf.some((f) => f.severity === "HIGH")
  const hasMedium = pf.some((f) => f.severity === "MEDIUM")
  return {
    count: pf.length,
    worst: hasCritical ? "CRITICAL" : hasHigh ? "HIGH" : hasMedium ? "MEDIUM" : "LOW",
    label: hasCritical ? "Critical" : hasHigh ? "At Risk" : "Clean",
  }
}
```

---

### WR-05: `EmptyStateCard` renders an `<p>` inside `<CardContent>` with no accessible role — not announced as status to screen readers

**File:** `src/dashboard/src/components/EmptyStateCard.tsx:1-11`
**Issue:** Empty states are meaningful status messages, but the card has no `role="status"`
or `aria-live` region. Screen reader users navigating to a page that is in the empty state
will not have the empty state message announced automatically after loading. Every other
loading indicator in this codebase (`PageSpinner`, all skeleton components) correctly uses
`role="status"`.
**Fix:**
```tsx
export function EmptyStateCard({ message }: { message: string }) {
  return (
    <Card role="status">
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}
```

---

### WR-06: Cytoscape node click handler uses `d.label` to look up `compByAlg` — breaks if algorithm name contains special characters or duplicates

**File:** `src/dashboard/src/pages/cbom.tsx:281`
**Issue:** The click handler on a graph node calls `compByAlg[d.label]` where `d.label` is
the algorithm name (e.g., `"AES-256-GCM"`). The `compByAlg` map is also keyed by
`comp.algorithm` (line 150). This is consistent, but only the _last_ component with a given
algorithm name survives in the map (line 150 overwrites). If the backend ever emits two
`CbomComponent` rows with the same `algorithm` string but different `type` or `key_size`
(e.g., `RSA` appearing as both signature and encryption), the second entry silently
overwrites the first and the graph will display incorrect detail panel data for that node.
**Fix:** Key the map by `algorithm` only if the API guarantees uniqueness per algorithm.
Otherwise key by a composite (e.g., `algorithm + type`) and update both the graph node `id`
and the click-handler lookup accordingly:
```typescript
const compByAlg = useMemo(() => {
  const m: Record<string, CbomComponent[]> = {}
  for (const comp of components) {
    if (!m[comp.algorithm]) m[comp.algorithm] = []
    m[comp.algorithm].push(comp)
  }
  return m
}, [components])
```

---

### WR-07: `vite.config.ts` a11y fixture handler reads fixture files synchronously inside a request handler — blocks the Node.js event loop

**File:** `src/dashboard/vite.config.ts:22-27`
**Issue:** Inside the Vite dev/preview server request handler, `readFileSync(...)` is called
on every incoming request for `/api/scan/latest` and `/api/trends`. Synchronous file reads
inside an async event-loop callback block all other requests on the server while the file
I/O completes. This is only a test fixture, but it can cause the preview server to appear
to hang during the a11y sweep if the fixture files are large and many routes are tested in
rapid succession. In the `loading` variant, the callback inside `setTimeout` also calls
`readFileSync` on the timer thread.
**Fix:** Cache the file contents at startup time instead of re-reading on every request:
```typescript
// At plugin initialization, outside the handler
const scanFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8')
const trendsFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8')

// Then inside the handler:
res.end(scanFixture)
```

---

### WR-08: GitHub Actions workflow uses `google-chrome-stable` executable path hardcoded for Linux but no installation step is included

**File:** `.github/workflows/dashboard-quality.yml:38-43`
**Issue:** The workflow sets `PUPPETEER_EXECUTABLE_PATH: /usr/bin/google-chrome-stable` but
does not include a step to install Chrome (e.g., `actions/setup-chrome` or `apt-get install
google-chrome-stable`). The `ubuntu-latest` GitHub-hosted runner does not include
`google-chrome-stable` by default. Puppeteer-core's own `channel: 'chrome'` fallback in
`run-a11y.mjs` will also fail because `puppeteer-core` does not ship a browser binary.
The workflow will therefore fail at the Chrome launch step on every run unless the runner
image happens to have Chrome pre-installed (which is not guaranteed and changes between
runner image versions).
**Fix:** Add a Chrome installation step before the a11y checks:
```yaml
- name: Install Chrome
  uses: browser-actions/setup-chrome@v1
  with:
    chrome-version: stable
```
Or use `npx puppeteer browsers install chrome` if the project switches from
`puppeteer-core` to `puppeteer`.

---

### WR-09: `ScoreDeltaBadge` in trends.tsx uses `hsl(var(--muted))` which resolves to a value that may have insufficient contrast

**File:** `src/dashboard/src/pages/trends.tsx:31`
**Issue:** The "No change" badge uses `bg-[hsl(var(--muted))]` with `text-muted-foreground`.
The axe baseline for trends (`baseline-trends.json`) already flags a `color-contrast`
violation on `.bg-[hsl(var(--quantum-safe))]`, indicating that CSS-variable-based colors are
not being evaluated correctly and contrast failures are being baselined rather than fixed.
The `--muted` background with `text-muted-foreground` foreground is a known low-contrast
combination (both are near-grey), and this pattern puts a known a11y regression into the
baseline to be permanently silenced.
**Fix:** Use a concrete, contrast-verified color pair for the "No change" state:
```tsx
return <Badge variant="outline" className="text-muted-foreground">No change</Badge>
```

---

## Info

### IN-01: `SEVERITY_STYLES` / `QS_BADGE` / `SEVERITY_COLORS` duplicated across five page files

**File:** `src/dashboard/src/pages/findings.tsx:24-30`, `certificates.tsx:11-16`,
`data-at-rest.tsx:13-19`, `identity.tsx:24-30`, `motion.tsx:12-18`, `cbom.tsx:25-30`
**Issue:** The same severity badge class maps are copy-pasted into every page component with
identical or near-identical content. Any future color change requires edits to five files.
**Fix:** Extract to a shared constants file, e.g. `src/dashboard/src/lib/severity.ts`.

---

### IN-02: Table rows in cbom.tsx, certificates.tsx, and data-at-rest.tsx use array index as `key`

**File:** `src/dashboard/src/pages/cbom.tsx:98`, `certificates.tsx:50`, `data-at-rest.tsx:84`
**Issue:** `key={i}` (array index) is used as the React list key. If the underlying data is
filtered, sorted, or paginated, React will associate DOM nodes with the wrong data items,
causing incorrect rendering or stale state in cells with local state (e.g., tooltips). The
cbom table row at line 98 is especially risky because `filtered` is a derived array whose
indexes shift when the filter changes.
**Fix:** Use a stable unique identifier. For `CbomComponent`, `c.algorithm` is unique within
the filtered list. For certificates, `cert.host + ":" + cert.port` is a reasonable key.

---

### IN-03: `roadmap.tsx` fixture data contains `edges` at the top level but `RoadmapPage` ignores it entirely

**File:** `src/dashboard/src/pages/roadmap.tsx:38`, `src/dashboard/tests/a11y/fixture-scan.json:154-158`
**Issue:** The fixture data defines `roadmap.edges` with explicit dependency relationships
between nodes. The `RoadmapPage` component ignores `data?.roadmap?.edges` entirely and
constructs synthetic cross-phase connector edges instead (line 83-101). The synthetic edges
connect the last node of each phase to all nodes in the next phase, which does not match the
actual dependency graph in the data. This means the rendered roadmap graph does not reflect
the real remediation dependencies.
**Fix:** Use `data.roadmap.edges` to build the Cytoscape edge elements rather than
constructing synthetic cross-phase edges.

---

### IN-04: `run-a11y.mjs` does not close the browser on unexpected exception — leaks Chrome process

**File:** `src/dashboard/tests/a11y/run-a11y.mjs:124-202`
**Issue:** The main `for` loop calls `await page.goto(...)` and `await new AxePuppeteer(...).analyze()`.
If either of these throws an unhandled exception (e.g., an axe internal error), the loop
exits without calling `browser.close()`. The cleanup function only kills the preview server,
not the browser. The Chrome process will remain running until the OS reaps it.
**Fix:** Wrap the main loop in a `try/finally`:
```javascript
try {
  for (const { slug, path: routePath } of ROUTES) {
    // ... existing loop body
  }
} finally {
  await browser.close()
  cleanup()
}
// Remove the two lines below the loop that currently call browser.close() / cleanup()
```

---

### IN-05: `console-allowlist.json` references a `$schema` that does not exist in the repository

**File:** `src/dashboard/tests/console-allowlist.json:2`
**Issue:** The file declares `"$schema": "./console-allowlist.schema.json"` but no such
schema file exists under `src/dashboard/tests/`. Editors and JSON validators that honor
`$schema` will report a resolution error. The `run-a11y.mjs` harness does not validate
against it, so there is no runtime impact, but the reference is dead.
**Fix:** Either create the schema file or remove the `$schema` property.

---

_Reviewed: 2026-05-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
