# Phase 43: Dashboard Polish — Pattern Map

**Mapped:** 2026-04-30
**Files analyzed:** 17 (8 NEW infra, 2 NEW components, 7 MODIFIED pages, plus per-page polish sweeps)
**Analogs found:** 14 / 17 (3 files have no in-repo analog: a11y harness, fixture middleware, GitHub Actions workflow — use RESEARCH.md sketches)

---

## File Classification

### NEW infrastructure (test/CI surface)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/dashboard/tests/a11y/run-a11y.mjs` | test-harness (Node ESM script) | batch → exit-code | none in repo (closest conceptually: `quantum-chaos-enterprise-lab/lab.sh` orchestration shape) | no-analog — use RESEARCH.md §"Combined harness" sketch |
| `src/dashboard/tests/a11y/routes.json` | test-config | static | `src/dashboard/src/App.tsx:29-40` (canonical route list) | exact (mirror the Routes block) |
| `src/dashboard/tests/a11y/fixture-scan.json` | test-fixture | static | `quirk/dashboard/api/schemas.py` (response shape) + live `/api/scan/latest` output | role-match |
| `src/dashboard/tests/a11y/fixture-trends.json` | test-fixture | static | `src/dashboard/src/hooks/useTrendsData.ts` consumer shape | role-match |
| `src/dashboard/tests/a11y/baseline-{slug}.json` (×9) | test-baseline | static | none — generated artifacts from first axe run | no-analog |
| `src/dashboard/tests/console-allowlist.json` | test-config | static | none | no-analog — use RESEARCH.md §"Pattern 3: Allowlist Schema" |
| `src/dashboard/vite.config.ts` (modified) | build-config | request-response (middleware) | current `vite.config.ts` (existing baseline) | exact (extend) |
| `src/dashboard/package.json` (modified) | build-config | static | current `package.json` (existing baseline) | exact (extend) |
| `.github/workflows/dashboard-quality.yml` | CI-config | event-driven (PR trigger) | none in repo (no `.github/workflows/` exists today) | no-analog — use RESEARCH.md §"Validation Architecture, Option A" |

### NEW UI components

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/dashboard/src/components/PageSpinner.tsx` | component (presentational) | none (static) | `src/dashboard/src/components/ui/skeleton.tsx` | role-match |
| `src/dashboard/src/components/EmptyStateCard.tsx` (extracted) | component (presentational) | none (static) | `src/dashboard/src/pages/motion.tsx:35-43` (inline) | exact (lift-and-shift) |
| `src/dashboard/src/pages/{findings,cbom,identity,certificates}.skeleton.tsx` (co-located per RESEARCH Q3) | component (presentational) | none (static) | `src/dashboard/src/pages/executive.tsx:58-69` (inline skeleton block) and `motion.tsx:209-217` | role-match |

### MODIFIED pages (polish sweep — empty states, skeletons, focus, headings, contrast)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `src/dashboard/src/pages/findings.tsx` | page (data-heavy, table) | request-response (`useScanData`) | `src/dashboard/src/pages/motion.tsx` | exact (severity tables w/ filters) |
| `src/dashboard/src/pages/identity.tsx` | page (data-heavy, sub-grouped) | request-response | `src/dashboard/src/pages/data-at-rest.tsx` | exact (per-section EmptyStateCard) |
| `src/dashboard/src/pages/cbom.tsx` | page (data-heavy, tabs+graph) | request-response | `src/dashboard/src/pages/data-at-rest.tsx` (sections) + `cbom.tsx` itself (tabs+canvas) | role-match (split: CbomTable empty state already exists at lines 52-61 in divergent shape — normalize to EmptyStateCard) |
| `src/dashboard/src/pages/certificates.tsx` | page (data-heavy, sub-grouped) | request-response | `src/dashboard/src/pages/data-at-rest.tsx` | exact |
| `src/dashboard/src/pages/executive.tsx` | page (context-derived projection) | request-response | `src/dashboard/src/pages/executive.tsx:58-69` (existing skeleton; needs page-level empty state on `!data`) | self-extend |
| `src/dashboard/src/pages/trends.tsx` | page (context-derived projection) | request-response | `src/dashboard/src/pages/executive.tsx` (PageSpinner + page-level empty state pattern) | role-match |
| `src/dashboard/src/pages/roadmap.tsx` | page (context-derived projection, graph) | request-response | `src/dashboard/src/pages/executive.tsx` + `src/dashboard/src/pages/cbom.tsx` (canvas pattern) | role-match |
| `src/dashboard/src/components/sidebar.tsx` (focus-visible audit) | component (nav) | none | `src/dashboard/src/components/sidebar.tsx:63-76` (existing `<Link>` block) | self-extend (add `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`) |

---

## Pattern Assignments

### `src/dashboard/src/components/EmptyStateCard.tsx` (extracted shared component)

**Analog:** `src/dashboard/src/pages/motion.tsx`

**Verbatim lift-and-shift** from `motion.tsx:35-43`:

```tsx
// motion.tsx:35-43 — copy verbatim
function EmptyStateCard({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}
```

Convert to a named export and update `motion.tsx`, `data-at-rest.tsx` (`data-at-rest.tsx:63-71` is the same shape) to import it. Note `cbom.tsx:52-61` uses a divergent `<h2>+<p>` shape inside `<div className="text-center py-12">` — Phase 43 normalizes this to `<EmptyStateCard>`.

**Imports** (mirror `motion.tsx:5`):
```tsx
import { Card, CardContent } from "@/components/ui/card"
```

---

### `src/dashboard/src/components/PageSpinner.tsx` (NEW)

**Analog:** `src/dashboard/src/components/ui/skeleton.tsx` + `src/dashboard/src/pages/executive.tsx:58-69`

**Skeleton primitive** (`src/dashboard/src/components/ui/skeleton.tsx:1-15`):
```tsx
import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("animate-pulse rounded-md bg-primary/10", className)} {...props} />
  )
}

export { Skeleton }
```

**Compose for PageSpinner** following the inline pattern at `executive.tsx:58-69`:
```tsx
// executive.tsx:58-69 — abstract this into PageSpinner
if (loading) {
  return (
    <div className="space-y-6">
      <div className="flex gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-32 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-48 w-full" />
    </div>
  )
}
```

PageSpinner targets `/`, `/trends`, `/roadmap` (D-06). Should accept an optional `aria-label` and use `role="status"` so screen readers announce loading state. Render text "Loading…" inside an sr-only span.

---

### `src/dashboard/src/pages/{findings,cbom,identity,certificates}.skeleton.tsx` (co-located, per RESEARCH Q3)

**Analog:** `src/dashboard/src/pages/motion.tsx:209-217` (canonical loading branch)

**Loading branch shape** (`motion.tsx:209-217`):
```tsx
if (loading) {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}
```

**Phase 43 task:** Replace this generic 5-bar pattern with a layout-matched skeleton per page. Each `*.skeleton.tsx` exports a single component that mirrors the page's actual structure:
- `findings.skeleton.tsx` — filter row (3 small skeletons) + table (8 rows × 7 cols of skeletons)
- `cbom.skeleton.tsx` — tabs strip + filter row + table OR canvas-area placeholder
- `identity.skeleton.tsx` — 3 protocol-card skeletons + table skeleton
- `certificates.skeleton.tsx` — section headers + table skeletons

Page imports its skeleton: `import { FindingsSkeleton } from "./findings.skeleton"` and uses `if (loading) return <FindingsSkeleton />`.

---

### `src/dashboard/src/pages/findings.tsx` (modified)

**Analog:** `src/dashboard/src/pages/motion.tsx`

**State branch order** (D-07 / Pitfall 7) — must follow `motion.tsx:194-218`:
```tsx
const { data, loading, error } = useScanData()
// ... useMemo derivations ...
if (loading) return <FindingsSkeleton />     // FIRST
if (error) return <p className="text-muted-foreground text-sm">{error}</p>  // SECOND
// happy path or per-section empty state
```

`findings.tsx:32` already destructures `{ data, loading, error }` correctly — verify the `if (loading)` branch is first and uses the layout-matched skeleton.

**SEV_ORDER + SEVERITY_STYLES** (`motion.tsx:11-17, 45`):
```tsx
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}
const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 } as const
```

`findings.tsx:23-29` already has `SEVERITY_STYLES`; verify identical shape. Phase 43 contrast audit (D-18) MAY require adjusting LOW token if axe `color-contrast` flags it (Risk Register row 3) — fix via CSS variable in `index.css`, NOT by changing the inline `hsl(...)` here.

**Per-section EmptyStateCard pattern** (`motion.tsx:222-252`):
```tsx
return (
  <div className="space-y-6">
    <h1 style={{ fontSize: 20, fontWeight: 600 }}>Findings</h1>
    <section aria-labelledby="critical-section-heading">
      <h2 id="critical-section-heading" className="mb-3" style={{ fontSize: 16, fontWeight: 600 }}>
        Critical & High
      </h2>
      {criticalRows.length === 0
        ? <EmptyStateCard message="No critical or high-severity findings — review remediation roadmap for medium-priority items." />
        : <FindingsTable rows={criticalRows} />}
    </section>
    {/* ... per-severity sections ... */}
  </div>
)
```

**Heading hierarchy** (D-17): exactly one `<h1>` per route — `motion.tsx:222` shows the canonical inline-style `<h1>`. Sub-sections use `<h2>` with `aria-labelledby` (`motion.tsx:224-231`).

---

### `src/dashboard/src/pages/identity.tsx` (modified)

**Analog:** `src/dashboard/src/pages/data-at-rest.tsx`

**Per-section pattern** matching DAR's 4-category approach (`data-at-rest.tsx` is the canonical realization). Apply per-protocol sections (SSH, mTLS, JWT, etc.) each with its own `EmptyStateCard`.

**Empty-state message contract** (D-10) — name the scanner + how to enable:
```tsx
// motion.tsx:233 — exact precedent
<EmptyStateCard message="No email endpoints scanned in this session — enable the email scanner in your config or scan a mail server." />
```

---

### `src/dashboard/src/pages/cbom.tsx` (modified)

**Analog:** `src/dashboard/src/pages/data-at-rest.tsx` (empty state) + `cbom.tsx` itself (canvas wrapper already correct)

**Existing canvas a11y wrapper is already correct** (`cbom.tsx:403-409`):
```tsx
<div
  ref={containerRef}
  role="img"
  aria-label="CBOM algorithm-to-system bipartite graph. Click a node to inspect."
  className="rounded-lg border border-border bg-card"
  style={{ width: "100%", height: "calc(100vh - 260px)", minHeight: 400 }}
/>
```

D-20 is partially satisfied here — Phase 43 verifies axe rules `image-alt` and `region` pass, no code change required unless axe still complains.

**Normalize divergent empty state** (`cbom.tsx:52-61`):
```tsx
// CURRENT (divergent shape — normalize)
if (!components.length) {
  return (
    <div className="text-center py-12">
      <h2 className="text-foreground font-semibold text-xl">No CBOM data available</h2>
      <p className="text-muted-foreground mt-2 text-sm">
        The most recent scan did not produce CBOM output. Ensure the scanner completed successfully.
      </p>
    </div>
  )
}
```
Replace with `<EmptyStateCard message="..." />` for consistency.

---

### `src/dashboard/src/pages/certificates.tsx` (modified)

**Analog:** `src/dashboard/src/pages/data-at-rest.tsx`

Per-section empty cards by certificate category (TLS-leaf, TLS-CA, JWT-signing, etc.). Same `sortBySev` pattern as `data-at-rest.tsx:45-53`:

```tsx
function sortBySev(findings: DarFinding[]) {
  return [...findings].sort(
    (a, b) =>
      (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 99) -
      (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 99) ||
      a.host.localeCompare(b.host) ||
      (a.port ?? 0) - (b.port ?? 0),
  )
}
```

---

### `src/dashboard/src/pages/executive.tsx` (modified)

**Analog:** `src/dashboard/src/pages/executive.tsx` itself

**Already has correct skeleton** (`executive.tsx:58-69`) — refactor to use `<PageSpinner>`. **Already has error branch** (`executive.tsx:71-77`). **Add `!data` page-level empty state** between error branch and happy path (`executive.tsx:79`):

```tsx
// executive.tsx:79 — currently `if (!data) return null` — replace with page-level empty
if (!data) {
  return (
    <div className="text-center py-12">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Executive Summary</h1>
      <p className="text-muted-foreground mt-4">
        No scan data available. Run a scan first: <code>quirk scan &lt;target&gt;</code>
      </p>
    </div>
  )
}
```

Note: `useScanData.ts:30` already returns this exact error message; consider unifying.

---

### `src/dashboard/src/pages/trends.tsx` (modified)

**Analog:** `src/dashboard/src/pages/executive.tsx` (loading + page-level empty pattern)

PageSpinner on loading; page-level empty state when `useTrendsData()` returns no scan history. Single `<h1>` "Trends" plus `<h2>` per chart section.

---

### `src/dashboard/src/pages/roadmap.tsx` (modified)

**Analog:** `src/dashboard/src/pages/cbom.tsx` (canvas wrapper) + `src/dashboard/src/pages/executive.tsx` (page-level empty)

**Canvas wrapper already correct** (`roadmap.tsx:268-274`):
```tsx
<div
  ref={containerRef}
  role="img"
  aria-label="Migration roadmap DAG. Nodes colored by urgency: red = immediate (0-30d), amber = short-term (31-90d), green = long-term (90+d). Click a node to inspect."
  className="rounded-lg border border-border bg-card"
  style={{ width: "100%", height: "calc(100vh - 220px)", minHeight: 400 }}
/>
```

Phase 43: PageSpinner on loading; page-level empty when no roadmap items.

---

### `src/dashboard/src/components/sidebar.tsx` (modified)

**Analog:** `src/dashboard/src/components/sidebar.tsx` itself (extend existing `<Link>` block)

**Current Link block** (`sidebar.tsx:63-76`):
```tsx
<Link
  to={path}
  aria-label={label}
  className={cn(
    "flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors",
    "min-h-[44px]", // accessibility touch target
    isActive
      ? "text-foreground border-b-2 lg:border-b-0 lg:border-l-2 border-accent bg-accent/10"
      : "text-muted-foreground hover:text-foreground hover:bg-accent/5",
  )}
>
```

**Phase 43 addition** (per Risk Register row 6): append focus-visible utilities to the className:
```tsx
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
```

This applies the shadcn focus-ring convention used elsewhere (radix primitives ship it by default; Link is a router primitive, so it needs explicit utilities).

---

### `src/dashboard/vite.config.ts` (modified)

**Analog:** Current `vite.config.ts` (extend existing baseline)

**Current file** (lines 1-27 — verbatim baseline):
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  build: {
    outDir: '../../quirk/dashboard/static',
    emptyOutDir: true,
    chunkSizeWarningLimit: 600,
    rolldownOptions: { /* manualChunks ... */ },
  },
})
```

**Extension pattern** (per RESEARCH §"Pattern 2", D-03 fixture mechanism):
```ts
import { readFileSync } from 'node:fs'
import path from 'path'
import type { Plugin } from 'vite'

function a11yFixture(): Plugin {
  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith('/api/scan/latest')) {
          res.setHeader('Content-Type', 'application/json')
          res.end(readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8'))
          return
        }
        if (req.url?.startsWith('/api/scan/trends')) {
          res.setHeader('Content-Type', 'application/json')
          res.end(readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8'))
          return
        }
        next()
      })
    },
    configurePreviewServer(server) { /* same body */ },
  }
}

// Add to plugins array:
plugins: [react(), a11yFixture()],
```

**Security gate** (T-43-01): the plugin only activates when `VITE_A11Y_FIXTURE=1` env is set. Fixture JSON files live under `tests/`, never imported by `src/`, so production builds cannot leak them. Plan must include a grep-lint task: `! grep -r 'tests/a11y' src/`.

---

### `src/dashboard/package.json` (modified)

**Analog:** Current `package.json` (extend existing baseline)

**Current scripts** (`package.json:6-11`):
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview"
}
```

**Extension** (per VALIDATION.md Wave 0 requirements):
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "a11y:check": "node tests/a11y/run-a11y.mjs",
  "a11y:check:empty": "VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=empty node tests/a11y/run-a11y.mjs",
  "a11y:check:loading": "VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=loading node tests/a11y/run-a11y.mjs",
  "a11y:baseline": "VITE_A11Y_FIXTURE=1 node tests/a11y/run-a11y.mjs --update-baselines"
}
```

**New devDeps** (per RESEARCH §"Standard Stack"):
```json
"devDependencies": {
  "@axe-core/puppeteer": "^4.11.3",
  "puppeteer-core": "^24.42.0"
}
```

Versions verified by researcher 2026-04-30. CONTEXT D-01 (revised) chose `@axe-core/puppeteer` over `@axe-core/cli` to collapse axe + console capture into one harness.

---

### `src/dashboard/tests/a11y/routes.json` (NEW)

**Analog:** `src/dashboard/src/App.tsx:29-40`

**Source of truth** for routes (`App.tsx:29-40`):
```tsx
<Routes>
  <Route path="/" element={<ExecutivePage />} />
  <Route path="/findings" element={<FindingsPage />} />
  <Route path="/identity" element={<IdentityPage />} />
  <Route path="/motion" element={<MotionPage />} />
  <Route path="/data-at-rest" element={<DataAtRestPage />} />
  <Route path="/certificates" element={<CertificatesPage />} />
  <Route path="/cbom" element={<CbomPage />} />
  <Route path="/roadmap" element={<RoadmapPage />} />
  <Route path="/trends" element={<TrendsPage />} />
  <Route path="/print" element={<PrintPage />} />  {/* EXCLUDED from a11y sweep */}
</Routes>
```

**routes.json shape:**
```json
[
  { "slug": "root",          "path": "/" },
  { "slug": "findings",      "path": "/findings" },
  { "slug": "identity",      "path": "/identity" },
  { "slug": "motion",        "path": "/motion" },
  { "slug": "data-at-rest",  "path": "/data-at-rest" },
  { "slug": "certificates",  "path": "/certificates" },
  { "slug": "cbom",          "path": "/cbom" },
  { "slug": "roadmap",       "path": "/roadmap" },
  { "slug": "trends",        "path": "/trends" }
]
```

9 entries — `/print` deliberately omitted (CONTEXT.md scope).

---

### `src/dashboard/tests/a11y/fixture-scan.json` (NEW)

**Analog:** `quirk/dashboard/api/schemas.py` (response schema) + `src/dashboard/src/types/api.ts` (TypeScript shape consumed by `useScanData`)

**Source-of-truth fields** required (derived from page consumers):
- `score`, `confidence`, `meta` (executive.tsx:81)
- `findings: FindingItem[]` (findings.tsx:13, 39-49 — `FindingItem` type)
- `motion_findings: MotionFinding[]` (motion.tsx:3, 197)
- `dar_findings: DarFinding[]` (data-at-rest.tsx:3)
- `cbom_components: CbomComponent[]` (cbom.tsx:5)
- identity, certificates, roadmap fields per their page consumers

Planner should run a real scan against the chaos lab `all` profile, capture the `/api/scan/latest` response, sanitize, and check the JSON in. Never edit by hand.

---

### `src/dashboard/tests/console-allowlist.json` (NEW)

**Analog:** none in repo. Use RESEARCH §"Pattern 3":

```jsonc
{
  "$schema": "./console-allowlist.schema.json",
  "entries": [
    {
      "pattern": "^Warning: %s: Support for defaultProps will be removed.*",
      "library": "recharts@2.15.4",
      "upstream": "https://github.com/recharts/recharts/issues/3615",
      "owner": "third-party / waiting on upstream",
      "added": "2026-04-30",
      "note": "Resolved by recharts 3.x; upgrade is a separate phase."
    }
  ]
}
```

D-12 enforces the 5-field schema (`pattern`, `library`, `upstream`, `owner`, `added` — `note` optional). Use **regex** not exact string (React interpolates `%s`).

---

### `src/dashboard/tests/a11y/run-a11y.mjs` (NEW)

**Analog:** none in repo. Use RESEARCH §"Combined harness — `@axe-core/puppeteer`" sketch as the starting blueprint. Key responsibilities:
1. Boot `vite preview` as a subprocess with `VITE_A11Y_FIXTURE=1` env.
2. Wait for port 4173 to accept connections.
3. For each route in `routes.json`: `page.on('console', ...)` capture, `page.goto(url, { waitUntil: 'networkidle0' })`, `new AxePuppeteer(page).withTags(['wcag2a', 'wcag2aa']).analyze()`.
4. Diff axe `violations[].id + violations[].nodes[].target[]` against `baseline-{slug}.json`. New violations → exit 1.
5. Filter captured console messages against `console-allowlist.json` regex entries. Unallowlisted → exit 1.
6. Tear down preview subprocess on exit.

**`--update-baselines` mode:** when flag present, write the current axe results to baseline JSON instead of diffing (used by `a11y:baseline` script after a deliberate accepted change).

---

### `.github/workflows/dashboard-quality.yml` (NEW)

**Analog:** none in repo (no `.github/workflows/` directory exists today — D-19).

Use the standard GitHub Actions pattern:
- `on: pull_request: paths: ['src/dashboard/**']`
- Single job: checkout → setup-node@v4 → `cd src/dashboard && npm ci && npm run build && npm run a11y:check`
- Use `actions/setup-node@v4` with `cache: 'npm'` and `cache-dependency-path: src/dashboard/package-lock.json`
- Chrome install: `actions/setup-chrome@v1` OR rely on Ubuntu runner default; `puppeteer-core` uses `channel: 'chrome'`.

Per D-19 rationale: separate workflow chosen over folding into a (currently absent) pytest workflow because the dashboard quality gate has no Python dependencies.

---

## Shared Patterns

### Page-render branch order (D-07, Pitfall 7)

**Source:** `src/dashboard/src/pages/motion.tsx:194-218`
**Apply to:** ALL 9 in-scope pages (`/`, `/findings`, `/identity`, `/motion`, `/data-at-rest`, `/certificates`, `/cbom`, `/roadmap`, `/trends`)

```tsx
const { data, loading, error } = useScanData()
const derived = useMemo(() => /* ... */, [data])  // useMemo MUST come before early returns
if (loading) return <Skeleton-or-PageSpinner />   // 1. loading FIRST
if (error)   return <p className="text-muted-foreground text-sm">{error}</p>  // 2. error
// 3. happy path or per-section/page-level empty state
```

**Anti-pattern:** branching on `data?.x?.length > 0` before the `loading` check causes empty-state flash on first paint.

---

### Empty-state copy contract (D-10)

**Source:** `src/dashboard/src/pages/motion.tsx:233, 248`
**Apply to:** every `<EmptyStateCard message="..." />` invocation

Message must answer: *what scanner produced this and how does the user enable it?*

Examples from `motion.tsx`:
```tsx
"No email endpoints scanned in this session — enable the email scanner in your config or scan a mail server."
"No broker endpoints scanned in this session — enable the broker scanner in your config or scan a message broker host."
```

Pattern: `"No <category> <noun> scanned in this session — <enablement instruction>."`

---

### Severity tokens — DO NOT introduce new `hsl()` literals (D-18, Phase 39 D-13)

**Source:** `src/dashboard/src/pages/motion.tsx:11-17`, `data-at-rest.tsx:12-18`, `findings.tsx:23-29`
**Apply to:** any color contrast fix during Phase 43

The same `SEVERITY_STYLES` map is duplicated across 3 pages (motion, dar, findings). Phase 43 sweep MAY DEDUPE into a shared constant in `src/dashboard/src/lib/severity.ts` if convenient, but is NOT required. What IS required: any contrast-rule failure flagged by axe must be fixed by adjusting the CSS-variable token (e.g., `--severity-low`) in `index.css`, NOT by editing the inline `bg-[hsl(...)]` strings.

---

### Heading hierarchy (D-17)

**Source:** `src/dashboard/src/pages/motion.tsx:222-231`
**Apply to:** every page

```tsx
<h1 style={{ fontSize: 20, fontWeight: 600 }}>{PageTitle}</h1>
<section aria-labelledby="<id>-section-heading">
  <h2 id="<id>-section-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
    {SectionTitle}
  </h2>
  ...
</section>
```

Exactly one `<h1>` per route. Sub-sections `<h2>` linked to their `<section>` via `aria-labelledby`.

---

### Cytoscape canvas a11y (D-20)

**Source:** `src/dashboard/src/pages/cbom.tsx:403-409`, `roadmap.tsx:268-274` (already correct)
**Apply to:** any future canvas mounts

```tsx
<div
  ref={containerRef}
  role="img"
  aria-label="<descriptive sentence including data summary and interaction hint>"
  className="rounded-lg border border-border bg-card"
  style={{ width: "100%", height: "...", minHeight: 400 }}
/>
```

Phase 43 verification confirms axe `image-alt` and `region` rules pass; no code change required unless axe flags a remaining issue.

---

### Focus-visible ring on Link/anchor primitives

**Source:** shadcn primitive convention (radix primitives ship it; React Router `<Link>` does not)
**Apply to:** `src/dashboard/src/components/sidebar.tsx:66-72` (the `<Link>` className)

Append:
```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

shadcn `<Button>`, `<Input>`, etc. already include this; only non-shadcn interactive elements (router Links, native `<details>/<summary>`) need the explicit utilities.

---

## No Analog Found

Files where no in-repo file serves a similar role; planner uses RESEARCH.md sketches and external docs:

| File | Role | Reason | Fallback Source |
|------|------|--------|-----------------|
| `src/dashboard/tests/a11y/run-a11y.mjs` | Node ESM test harness | No JS test infra exists in dashboard today | RESEARCH.md §"Combined harness" + `@axe-core/puppeteer` README |
| `src/dashboard/tests/a11y/baseline-{slug}.json` (×9) | axe-core result snapshots | Generated artifacts; no analog | First `npm run a11y:baseline` produces them |
| `.github/workflows/dashboard-quality.yml` | GitHub Actions workflow | No `.github/workflows/` directory exists | RESEARCH.md §"Validation Architecture, Option A" |

---

## Metadata

**Analog search scope:** `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `src/dashboard/src/hooks/`, `src/dashboard/`, `src/dashboard/src/App.tsx`
**Files scanned:** 11 (all 10 page files + sidebar + 4 supporting files)
**Pattern extraction date:** 2026-04-30

**Match-quality summary:**
- exact analog: 7 files
- role-match analog: 7 files
- self-extend: 3 files (executive.tsx, sidebar.tsx, vite.config.ts, package.json — modify in place)
- no-analog: 3 files (harness, baselines, CI workflow)
