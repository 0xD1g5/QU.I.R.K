# Phase 43: Dashboard Polish - Research

**Researched:** 2026-04-30
**Domain:** React + Vite frontend a11y / quality polish (axe-core, console hygiene, WCAG AA)
**Confidence:** HIGH

## Summary

Phase 43 is a polish phase against an already-shipped React 19 + Vite 8 + Tailwind 3 + shadcn dashboard with 10 routes wired in `src/dashboard/src/App.tsx:29-40`. The locked plan (CONTEXT.md) is to add `@axe-core/cli` (no test framework adoption), per-route baseline JSON files, a console-error allowlist, hand-tuned skeletons on data-heavy routes, and a hybrid empty-state strategy. The genuinely open mechanical questions are: how to drive `@axe-core/cli` against multiple URLs with seeded data, how to capture console output (since `@axe-core/cli` does NOT capture console messages), and where in CI to hook it (no `.github/workflows/` and no `Makefile` exist today — pyproject.toml hosts pytest).

**Primary recommendation:** Use `@axe-core/cli@4.11.3` driven by a thin Node script that:
1. boots `vite preview` (background), 2. iterates the 10-route list, 3. invokes `axe <url> --save baseline-{slug}.json --tags wcag2a,wcag2aa --exit`, 4. diffs new violations vs the checked-in baseline. For console capture, add a tiny **separate** Node harness using `puppeteer-core` + system Chrome (or `chrome-launcher`) — because `@axe-core/cli` only emits a11y results, not console text. Seed scan data via a Vite middleware mode that intercepts `/api/scan/latest` and `/api/scan/list` from a checked-in JSON fixture when `VITE_A11Y_FIXTURE=1`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skeleton/empty-state rendering | Browser (React component) | — | Pure presentation, driven by `useScanData()` state branches |
| `/api/scan/latest` fixture for a11y runs | Frontend Server (Vite middleware) | Static (JSON fixture) | Vite preview already serves the bundle; middleware mock keeps Python backend out of CI a11y job |
| axe-core scan execution | Headless browser harness (Node) | — | Off-page tooling; not part of runtime |
| Console capture | Headless browser harness (Node) | — | `@axe-core/cli` cannot do this; needs its own driver |
| Baseline JSON storage | Repo (`src/dashboard/tests/a11y/`) | — | Source of truth, reviewed in PRs |

## Standard Stack

### Core (NEW devDeps)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@axe-core/cli` | `^4.11.3` `[VERIFIED: npm view 2026-04-30]` | Run axe-core against URLs, emit JSON | Maintained by Deque, official wrapper around axe-core; same engine ports to `@axe-core/playwright` in Phase 44 |
| `puppeteer-core` | `^24.42.0` `[VERIFIED: npm view 2026-04-30]` | Headless Chrome driver for console capture | Smaller than `puppeteer` (no auto-download); reuses system Chrome already required by QU.I.R.K.'s PDF export path (`executive.tsx:49` references `playwright install chromium`) |
| `chrome-launcher` | `^1.2.1` `[VERIFIED: npm view 2026-04-30]` | Alternative: launch Chrome + connect via DevTools Protocol | Lighter than puppeteer-core; only needed if planner wants no Puppeteer at all |

### Already Installed (no install needed)
| Library | Version | Used For |
|---------|---------|----------|
| `vite` | `^8.0.1` | `vite preview` provides the static-server hook for axe |
| `@radix-ui/*` | various | shadcn primitives — already ship `focus-visible:` ring styling |
| shadcn `<Skeleton>` | local at `src/dashboard/src/components/ui/skeleton.tsx` | Reused for D-05 layout-matched skeletons; primitive is a single 13-line `animate-pulse rounded-md bg-primary/10` div `[VERIFIED: read file]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@axe-core/cli` driven by a wrapper script | `pa11y-ci` | `pa11y-ci` has built-in URL-list config and per-URL JSON output — but uses HTML_CodeSniffer by default, not axe-core; mixing rule engines breaks the Phase-44 "port to `@axe-core/playwright`" promise (D-04). Reject. |
| `puppeteer-core` for console capture | `playwright-core` (as a library, not test framework) | Playwright's API is ergonomically nicer, but installing it implicitly invites adopting `@playwright/test` next phase, which CONTEXT.md explicitly defers. Puppeteer keeps the polish phase scoped. |
| Vite middleware for fixture | MSW (Mock Service Worker) | MSW is the React-ecosystem standard for API mocking, but installing it adds a runtime worker concept and a service-worker registration step — overkill for a CI-only fixture. Vite middlewareMode + a tiny plugin is 30 lines and zero new deps. |
| Hand-rolled Node harness | `@axe-core/puppeteer` `^4.11.3` | Combines axe + puppeteer into one library. Strong recommendation if console capture is also wanted, because the harness already has the page handle. **This is the lowest-friction option**: one harness drives both axe and console capture; `@axe-core/cli` becomes redundant. Planner should weigh this against the CLI-only path. |

**Installation (recommended):**
```bash
cd src/dashboard
npm install --save-dev @axe-core/cli @axe-core/puppeteer puppeteer-core
```

**Version verification:** Verified against npm registry 2026-04-30. `@axe-core/cli@4.11.3` and `@axe-core/puppeteer@4.11.3` are the latest publishes; both wrap `axe-core@4.10.x`.

## Architecture Patterns

### System Architecture Diagram

```
                  ┌──────────────────────────────────────────┐
                  │           CI runner (pytest job          │
                  │           or new dashboard job)          │
                  └──────────┬───────────────────────────────┘
                             │ npm run a11y:check
                             ▼
                  ┌──────────────────────────────────────────┐
                  │ Node harness                             │
                  │  - boots `vite preview` w/ fixture flag  │
                  │  - iterates 10-route list                │
                  └──────────┬───────────────────────────────┘
                             │
              ┌──────────────┴───────────────┐
              ▼                              ▼
      ┌──────────────────┐         ┌──────────────────────┐
      │ axe-core         │         │ Headless Chrome      │
      │ (per-route scan) │         │ (console capture)    │
      └────────┬─────────┘         └──────────┬───────────┘
               │                              │
               ▼                              ▼
      ┌──────────────────┐         ┌──────────────────────┐
      │ baseline diff    │         │ allowlist match      │
      │ src/dashboard/   │         │ src/dashboard/       │
      │ tests/a11y/      │         │ tests/console-       │
      │ baseline-*.json  │         │ allowlist.json       │
      └────────┬─────────┘         └──────────┬───────────┘
               │                              │
               └────────────┬─────────────────┘
                            ▼
                    pass / fail (exit code)
```

### Recommended Project Structure (additive)
```
src/dashboard/
├── tests/                       # NEW
│   ├── a11y/
│   │   ├── run-a11y.mjs         # harness: boots preview, drives axe + console, writes/diffs JSON
│   │   ├── routes.json          # canonical 10-route list mirroring App.tsx
│   │   ├── fixture-scan.json    # seeded /api/scan/latest payload
│   │   ├── fixture-trends.json  # seeded /api/scan/trends payload
│   │   ├── baseline-root.json   # `/`
│   │   ├── baseline-findings.json
│   │   ├── baseline-identity.json
│   │   ├── baseline-motion.json
│   │   ├── baseline-data-at-rest.json
│   │   ├── baseline-certificates.json
│   │   ├── baseline-cbom.json
│   │   ├── baseline-roadmap.json
│   │   └── baseline-trends.json
│   └── console-allowlist.json   # third-party warning allowlist
├── vite.config.ts               # extend with a11y-mode plugin (gated by env var)
├── package.json                 # add @axe-core/* devDeps + scripts
└── src/components/
    └── PageSpinner.tsx          # NEW — shared spinner for `/`, `/trends`, `/roadmap` (D-06)
```

### Pattern 1: Skeleton Branch as Initial Render (D-07)

`useScanData()` already initializes `loading=true` (`src/dashboard/src/hooks/useScanData.ts:14`), so an early `if (loading) return <Skeleton/>` IS the initial render path. **Do not** introduce React `Suspense` boundaries — the hook is fetch-based, not promise-based, and Suspense would force a refactor outside Phase 43 scope.

```tsx
// Pattern (already correct in motion.tsx:209-217 and executive.tsx:58-69):
const { data, loading, error } = useScanData()
if (loading) {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}
if (error) return <p className="text-muted-foreground text-sm">{error}</p>
// happy path...
```

**Phase 43 task:** apply this same pattern with **layout-matched** skeletons (not generic 5-bar) on `/findings` (table + filter row), `/cbom` (tabs + table or graph), `/identity` (3 protocol cards + table), `/certificates`, and `/data-at-rest` (already done from Phase 39). Use `<PageSpinner>` on `/`, `/trends`, `/roadmap`.

### Pattern 2: Vite Middleware Fixture Mode

```ts
// vite.config.ts additive plugin (sketch — planner finalizes)
function a11yFixture(): Plugin {
  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith('/api/scan/latest')) {
          res.setHeader('Content-Type', 'application/json')
          res.end(readFileSync('./tests/a11y/fixture-scan.json', 'utf8'))
          return
        }
        if (req.url?.startsWith('/api/scan/trends')) {
          res.setHeader('Content-Type', 'application/json')
          res.end(readFileSync('./tests/a11y/fixture-trends.json', 'utf8'))
          return
        }
        next()
      })
    },
    configurePreviewServer(server) { /* same as above */ },
  }
}
```

**Why preview, not dev:** `vite preview` serves the production bundle and is the closest analog to deployment; axe-core results against the dev bundle would include dev-only React warnings.

### Pattern 3: Allowlist Schema (D-12)

```jsonc
// src/dashboard/tests/console-allowlist.json
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

Use **regex** matching, not exact string — React warnings interpolate component names via `%s`. `[CITED: github.com/recharts/recharts/issues/3615]`

### Anti-Patterns to Avoid
- **Suppressing console at runtime:** D-14 forbids it. Allowlist is test-time only. `[CITED: CONTEXT.md D-14]`
- **Hardcoding `hsl()` literals for contrast fixes:** Phase 39 D-13 baseline forbids it. Token CSS variables only. `[CITED: CONTEXT.md D-18]`
- **Adding `@playwright/test` or `vitest`:** Out of scope; CONTEXT.md `<deferred>` lists Playwright migration as Phase 44. `[CITED: CONTEXT.md deferred section]`
- **Trying to fix the recharts warning by patching node_modules or shimming React:** It is upstream debt; allowlist it and move on.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-route a11y scanning | Custom DOM walker | `@axe-core/cli` or `@axe-core/puppeteer` | axe-core has 90+ rules, screen-reader name resolution, color-contrast math — building a subset is months of work |
| Headless browser console capture | spawn Chrome + parse stderr | `puppeteer-core.page.on('console', ...)` | DevTools Protocol normalizes warning vs error vs info, gives source location |
| Diffing axe JSON | hand-rolled deep-equal | `axe-core` ships violation IDs; compare `result.violations[].id` + `result.violations[].nodes[].target[]` | Stable shape across versions |
| Skeleton primitive | Custom CSS + animation | shadcn `<Skeleton>` already at `src/dashboard/src/components/ui/skeleton.tsx` | 13 lines, already in use |

**Key insight:** This phase is small *only if* we lean on Deque's tooling. Building a "lightweight" a11y checker is the trap that turns a polish phase into a quarter.

## Common Pitfalls

### Pitfall 1: `@axe-core/cli` does not capture console messages
**What goes wrong:** Planner assumes one tool covers DASH-01 and DASH-03. It doesn't.
**Why it happens:** `@axe-core/cli` is purpose-built for a11y rule evaluation; it returns axe results JSON only. Console capture requires direct DevTools Protocol access.
**How to avoid:** Either (a) run two harnesses (axe-cli + a tiny puppeteer script) or (b) collapse to one harness using `@axe-core/puppeteer` which gives you both. Option (b) is recommended.
**Warning signs:** Plan task list has only one CI script and claims it "checks console errors" — wrong.

### Pitfall 2: Recharts `defaultProps` warning will be present and unfixable in this phase
**What goes wrong:** Planner blocks on getting `/` (Executive: BarChart) and `/trends` (any recharts use) to zero warnings.
**Why it happens:** `recharts@2.15.4` still uses `defaultProps` on internal components (XAxis, YAxis, Curve). `[CITED: github.com/recharts/recharts/issues/3615]` Recharts 3.x fixes it but is a major upgrade with API changes — out of scope for a polish phase.
**How to avoid:** Allowlist the `defaultProps` warning pattern from day one. Recharts 3.x upgrade is a separate phase.
**Warning signs:** Repeated patches to recharts wrappers trying to silence the warning.

### Pitfall 3: react-router future-flag warnings
**What we found:** Package.json declares `react-router-dom@^7.4.0` `[VERIFIED: read package.json]`. Future-flag warnings (`v7_startTransition`, `v7_relativeSplatPath`) are **v6 → v7 migration warnings only**; on v7 they should not fire. `[CITED: reactrouter.com/upgrading/v6]`
**Action:** Verify empirically. If they DO fire (unlikely on v7), allowlist them. If not, no action.
**Confidence:** MEDIUM — verified against docs and current install; minor risk that some transitive code path emits a warning.

### Pitfall 4: Vite preview vs dev produces different warnings
**What goes wrong:** Running axe against `vite dev` reports React StrictMode double-render warnings, hot-reload preamble logs, etc.
**Why it happens:** Dev bundle ≠ prod bundle.
**How to avoid:** Always `npm run build && npm run preview` before axe runs. The harness should `vite preview` only.

### Pitfall 5: Sidebar `<Tooltip>` visible only on narrow viewport
**What we found:** `src/dashboard/src/components/sidebar.tsx:79-81` — tooltip uses `className="lg:hidden"`, only visible below 1024px. axe-core runs at default 1280×720, so tooltip content won't be in DOM. This is fine for a11y but means **manual narrow-viewport check is needed** if Phase 43 wants to verify keyboard ergonomics on the collapsed sidebar.
**Recommendation:** Run axe at two viewports (`--viewport` is not a CLI flag — needs custom harness): wide (1280×720) and narrow (768×800). Or accept wide-only as the SC bar.

### Pitfall 6: Cytoscape graph a11y violations on `/cbom` and `/roadmap`
**What we found:** Both `cbom.tsx` and `roadmap.tsx` mount `cytoscape` which renders to `<canvas>`. Canvas content is invisible to axe-core. Likely violation: `aria-hidden`/`role="img"` missing, no text alternative.
**Recommendation:** Add `role="img"` + `aria-label` describing the graph, OR mark `aria-hidden="true"` on the canvas and ensure the same data is reachable in the table tab. `cbom.tsx` already has Tabs (table + graph), so the table is the alt.
**Confidence:** HIGH — known canvas-a11y pattern; verified by reading both files.

### Pitfall 7: First-paint flash on routes that render before `loading` flips
**What goes wrong:** A page that renders happy-path content gated only on `data?.x?.length > 0` will momentarily render the empty state before fetch completes, even if it never reaches a real empty state.
**Why it happens:** Component mounts, `data` is `null`, length check is falsy, empty state renders, then loading begins.
**How to avoid:** ALWAYS branch on `loading` first, then `error`, then `!data`, then render. `motion.tsx:209-218` is the canonical correct order. Audit every page for this order.
**Warning signs:** Empty state visible for ~50ms on hard reload.

## Runtime State Inventory

> Phase 43 is content polish + new test scaffolding. No data migrations, no service config, no OS state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified against `useScanData.ts` (read-only fetch from `/api/scan/latest`) | none |
| Live service config | None — no external services consumed by the polish work | none |
| OS-registered state | None | none |
| Secrets/env vars | New env var `VITE_A11Y_FIXTURE` consumed only by Vite middleware in CI; not a secret | document in PHASE-43 SUMMARY |
| Build artifacts | `quirk/dashboard/static/assets/index-*.{css,js}` — already gitignored output of `vite build` | none — artifacts regenerate on every CI run |

## Code Examples

### Drive axe-cli against multiple URLs
```bash
# Single-URL pattern (CLI):
npx axe http://localhost:4173/findings \
  --tags wcag2a,wcag2aa \
  --save tests/a11y/baseline-findings.json \
  --exit
```
`[CITED: github.com/dequelabs/axe-core-npm/blob/develop/packages/cli/README.md]`

### Combined harness (recommended) — `@axe-core/puppeteer`
```js
// src/dashboard/tests/a11y/run-a11y.mjs (sketch)
import puppeteer from 'puppeteer-core'
import { AxePuppeteer } from '@axe-core/puppeteer'
import { readFileSync, writeFileSync } from 'node:fs'

const ROUTES = JSON.parse(readFileSync('./tests/a11y/routes.json', 'utf8'))
const ALLOWLIST = JSON.parse(readFileSync('./tests/console-allowlist.json', 'utf8'))
  .entries.map(e => new RegExp(e.pattern))

const browser = await puppeteer.launch({
  channel: 'chrome',  // use system chrome
  headless: true,
})

let exit = 0
for (const { slug, path } of ROUTES) {
  const page = await browser.newPage()
  const consoleMsgs = []
  page.on('console', m => {
    if (m.type() === 'warn' || m.type() === 'error') consoleMsgs.push(m.text())
  })
  await page.goto(`http://localhost:4173${path}`, { waitUntil: 'networkidle0' })

  // axe scan
  const results = await new AxePuppeteer(page)
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze()

  // diff vs baseline
  const baseline = JSON.parse(readFileSync(`./tests/a11y/baseline-${slug}.json`, 'utf8'))
  const newViolations = results.violations.filter(v =>
    !baseline.violations.find(b => b.id === v.id))
  if (newViolations.length) { console.error(slug, 'NEW VIOLATIONS', newViolations); exit = 1 }

  // console assert
  const unallowlisted = consoleMsgs.filter(m => !ALLOWLIST.some(rx => rx.test(m)))
  if (unallowlisted.length) { console.error(slug, 'CONSOLE', unallowlisted); exit = 1 }

  await page.close()
}
await browser.close()
process.exit(exit)
```

### Empty-state card (canonical)
```tsx
// from motion.tsx:35-43 — copy this verbatim into a shared component if extracted
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
**Recommendation:** Extract to `src/dashboard/src/components/EmptyStateCard.tsx` and import. `motion.tsx`, `data-at-rest.tsx`, `cbom.tsx` (line 53-61, with `<h2>` + `<p>` divergent shape) all reimplement variants.

### Canvas a11y wrapper (cytoscape pages)
```tsx
<div
  ref={containerRef}
  role="img"
  aria-label={`CBOM dependency graph showing ${nodes.length} cryptographic components`}
  className="..."
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `axe-cli` (deprecated) | `@axe-core/cli` | 2018 — `dequelabs/axe-cli` archived; `@axe-core/cli` is the supported package `[CITED: github.com/dequelabs/axe-cli (archived)]` | Don't search npm for "axe-cli" — use `@axe-core/cli` |
| `puppeteer` (auto-downloads Chromium) | `puppeteer-core` (uses installed Chrome) | Ongoing | Smaller install, faster CI; QU.I.R.K. already requires Chrome via Playwright for PDF export |
| `defaultProps` on function components | JS default parameters | React 18.3 deprecation, removed in React 19 | recharts 2.x emits the warning; recharts 3.x fixes it `[CITED: github.com/recharts/recharts/issues/3615]` |
| react-router v6 future flags | react-router v7 (default behaviors) | v7 release — flags became defaults | This project is on v7.4.0; future-flag warnings should be absent |

**Deprecated/outdated:**
- `axe-cli` (the package without the scope) — archived 2018+, do not use.
- React `defaultProps` on function components — removed in React 19.

## Project Constraints (from CLAUDE.md)

- **PEP 8 for any Python touches.** Phase 43 is JS/TS-heavy; minimal Python expected.
- **`python -m compileall` after Python changes.** Likely N/A for this phase.
- **Chaos lab maintenance:** N/A — Phase 43 doesn't touch `quantum-chaos-enterprise-lab/`.
- **Mandatory phase completion steps (CLAUDE.md):**
  1. Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-43-Dashboard-Polish.md` (write directly to filesystem; file too large for `obsidian CLI content=`).
  2. Update `docs/UAT-SERIES.md` for any series affected by dashboard changes.
  3. Sync `UAT-SERIES.md` to Obsidian via the documented `/tmp/uat_vault.md` pattern.
  4. Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs commit`.
- **Frontmatter standards** apply to any new vault notes (`project: QU.I.R.K.`, `type`, `status`, `source`, `updated`).

Plans MUST include explicit tasks for the four mandatory completion steps.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Custom Node harness driving `@axe-core/puppeteer` (NEW — added by this phase) |
| Config file | `src/dashboard/tests/a11y/routes.json` + `src/dashboard/tests/console-allowlist.json` (NEW) |
| Quick run command | `cd src/dashboard && npm run a11y:check` |
| Full suite command | `cd src/dashboard && npm run build && npm run a11y:check` (build is a prereq) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Zero console errors / React warnings on every route (allowlisted exceptions only) | smoke (headless browser) | `cd src/dashboard && npm run a11y:check` | ❌ Wave 0 |
| DASH-02 (loading) | First-paint render is skeleton/spinner when `useScanData()` loading=true | unit/component? **No JS test framework** — verify via axe run with `loading` simulated by delayed fixture, or manual via UAT | manual + axe-run with delayed-response fixture | ❌ Wave 0 |
| DASH-02 (empty) | `EmptyStateCard` (or page-level empty) renders when scan data missing | smoke (axe run with empty fixture) | `VITE_A11Y_FIXTURE_VARIANT=empty cd src/dashboard && npm run a11y:check:empty` | ❌ Wave 0 |
| DASH-03 (keyboard) | All interactive elements reachable via keyboard with visible focus | axe-core `focus-order-semantics`, `focus-visible` rules | `cd src/dashboard && npm run a11y:check` | ❌ Wave 0 |
| DASH-03 (heading) | Exactly one `<h1>`, ordered `<h2>`/`<h3>` | axe-core `heading-order`, `page-has-heading-one` | `cd src/dashboard && npm run a11y:check` | ❌ Wave 0 |
| DASH-03 (contrast) | WCAG AA on findings tables | axe-core `color-contrast` | `cd src/dashboard && npm run a11y:check` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd src/dashboard && npm run lint` (existing) — ESLint guards prop typos, hooks rules.
- **Per wave merge:** `cd src/dashboard && npm run build && npm run a11y:check` — full a11y + console sweep across all 10 routes.
- **Phase gate:** Full suite green before `/gsd-verify-work`. Each baseline JSON either committed or reviewed in PR.

### Wave 0 Gaps
- [ ] `src/dashboard/tests/a11y/run-a11y.mjs` — harness driving axe + console capture
- [ ] `src/dashboard/tests/a11y/routes.json` — canonical 10-route list (mirrors `App.tsx:30-39`, excludes `/print`)
- [ ] `src/dashboard/tests/a11y/fixture-scan.json` — seeded `/api/scan/latest` payload (covers all data shapes: motion, identity, dar, cbom, certificates, findings, roadmap, summary scores)
- [ ] `src/dashboard/tests/a11y/fixture-trends.json` — seeded `/api/scan/trends` payload
- [ ] `src/dashboard/tests/a11y/baseline-{root,findings,identity,motion,data-at-rest,certificates,cbom,roadmap,trends}.json` — 9 files (one per top-level route)
- [ ] `src/dashboard/tests/console-allowlist.json` — initial entries for recharts `defaultProps`, plus any others discovered during Wave-1 baseline run
- [ ] `src/dashboard/vite.config.ts` — extend with `a11yFixture` plugin (gated by `VITE_A11Y_FIXTURE` env)
- [ ] `src/dashboard/package.json` — add `a11y:check`, `a11y:baseline` scripts; add devDeps
- [ ] CI hook — no `.github/workflows/` exists today. Either:
  - **Option A:** Create `.github/workflows/dashboard-a11y.yml` running `npm ci && npm run build && npm run a11y:check` on PRs touching `src/dashboard/**`.
  - **Option B:** Add a pytest-driven shell test in `tests/test_dashboard_a11y.py` that subprocess-runs the npm script. Aligns with pyproject's existing pytest harness.
  - **Recommendation:** Option A — separate JS tooling job. Frontend a11y has zero overlap with pytest concerns; folding it in adds Node setup to every Python CI run.

## Security Domain

> Polish phase — no auth/data/crypto changes. Per ASVS, only V1 (Architecture) is touched indirectly via test infrastructure changes.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | no (no new inputs) | N/A |
| V6 Cryptography | no | N/A |
| V14 Configuration | yes (mild) | New env var `VITE_A11Y_FIXTURE` is dev/test-only and must be off in production builds — verify in plan |

### Known Threat Patterns for {React + Vite}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fixture leak in production bundle | Information Disclosure | Vite middleware ONLY runs when `VITE_A11Y_FIXTURE=1` is set at server-launch time; production preview/build never sets it. Plan must verify build output does not contain fixture JSON. |
| Allowlist bypass turning into runtime suppression | Tampering | D-14 enforces test-time only — verified by lint that the allowlist is never imported by app code (only by test harness). |

## Open Questions (RESOLVED)

1. **CI host: GitHub Actions vs other?**
   - What we know: No `.github/workflows/` exists; pyproject.toml has pytest config; Phase 41 was "CI Stability" but the actual CI provider is undocumented in files I read.
   - What's unclear: Where does `make ci` (referenced in CONTEXT.md) actually run? Is there a CI provider?
   - Recommendation: Planner should confirm with user during plan-check; if no CI provider is wired, Phase 43 ships the npm script and documents the local-run procedure, leaving CI hookup to a follow-up.
   - **RESOLVED (D-19):** Phase 43 creates `.github/workflows/dashboard-quality.yml` — GitHub Actions is the CI provider. No Makefile integration needed; the new workflow is a standalone PR gate for `src/dashboard/**` changes.

2. **Should we do `@axe-core/cli` OR `@axe-core/puppeteer`?**
   - What we know: CONTEXT.md specifies `@axe-core/cli`. Console capture requires a separate driver. `@axe-core/puppeteer` collapses both.
   - What's unclear: Is the CONTEXT.md choice load-bearing, or was it a proxy for "use axe-core, not Playwright"?
   - Recommendation: Planner asks the user during plan-check whether `@axe-core/puppeteer` (one harness for axe + console) is acceptable; CONTEXT.md's intent ("not Playwright") is preserved either way.
   - **RESOLVED (D-01 revised after research):** Use `@axe-core/puppeteer` — single harness drives both axe scans and console capture. `@axe-core/cli` alone cannot capture console messages. CONTEXT.md was amended post-research to reflect this; the "not Playwright" intent is preserved.

3. **Skeleton file layout — co-located vs `components/skeletons/`?**
   - CONTEXT.md leaves this to Claude's discretion (D-50 implicit).
   - Recommendation: Co-locate as `pages/findings.skeleton.tsx` etc. Rationale: skeletons are tightly coupled to their page's layout; centralizing them adds import noise without reuse benefit (no skeleton is shared between two pages in this design).
   - **RESOLVED (Claude's Discretion):** Co-located skeleton files (`pages/findings.skeleton.tsx` etc.) chosen per research recommendation. Centralized `components/skeletons/` is acceptable if planner prefers consistency; outcome is identical per CONTEXT.md.

4. **Trends route fixture — what `useTrendsData()` shape?**
   - What we know: `useTrendsData.ts` exists alongside `useScanData.ts`; `trends.tsx` uses it; recharts is NOT imported by trends (it's only on `/`).
   - What's unclear: Whether the trends fixture needs separate file or shares scan fixture.
   - Recommendation: Plan a quick read of `useTrendsData.ts` during Wave 0 to determine.
   - **RESOLVED (Plan 43-01 T1 read_first):** Executor reads `src/dashboard/src/hooks/useTrendsData.ts` as part of Wave 1 task 1 to determine fixture shape before writing `fixture-trends.json`. A separate fixture file is pre-planned; it can be collapsed into `fixture-scan.json` if the hook shares the same data shape.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite, npm scripts | ✓ (assumed — already running) | per `engines` (none declared) | — |
| npm | Install devDeps | ✓ | — | — |
| System Chrome / Chromium | puppeteer-core (via `channel: 'chrome'`) | ✓ — already required by Playwright PDF export (`executive.tsx:49`) | system-installed | Use `puppeteer` (full) instead of `puppeteer-core` if Chrome unavailable on CI host — accepts ~150MB Chromium download |
| `vite` `^8.0.1` | preview server | ✓ | 8.0.1 (devDep) | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — the Chrome/puppeteer-core path has the documented fallback above if a CI host lacks Chrome.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `/cbom` and `/roadmap` cytoscape canvases fail axe `image-alt`/`region` rules | HIGH | Medium — fix is a 1-line `aria-label` | Add canvas wrapper attrs in Wave 1 |
| recharts `defaultProps` warning on `/` (Executive: `BarChart` at `executive.tsx:6`) | CERTAIN | Low — allowlist | Allowlist entry on day one |
| Color contrast on `LOW` severity badge (`hsl(213_94%_68%)` on dark bg) may fail | MEDIUM | Medium — token swap needed | Run baseline first; if it fails, adjust token in `index.css` not inline |
| `/findings` `<Sheet>` (radix dialog) focus trap on close | LOW | Medium | Radix handles this correctly out of box; verify via axe `focus-trap` rule |
| `<Tabs>` on `/cbom` keyboard reachability (radix tabs) | LOW | Low | Radix tabs are keyboard-accessible by default |
| Sidebar link (`<Link>` with `aria-label` and visual icon-only on narrow viewport) — focus indicator visibility | MEDIUM | Low — Tailwind class addition | `sidebar.tsx:67` already has `transition-colors`; need `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2` added |
| Hidden interactive elements via `<details>/<summary>` on `/trends` (`trends.tsx:38-69`) | LOW | Low — native HTML, axe already validates | Native `<details>` is accessible; verify focus indicator |
| Setting `VITE_A11Y_FIXTURE` accidentally leaks fixture into prod bundle | LOW | Medium | Plan task: add lint check that `VITE_A11Y_FIXTURE` is only consumed in vite.config.ts, not in `src/` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | react-router v7 does not emit future-flag warnings (verified against v7 docs, not against running app) | Pitfall 3 | Low — if it does, allowlist them |
| A2 | `make ci` exists or there is some pytest CI; Makefile not found in workspace root | Validation Architecture / Open Q1 | Medium — drives where the new npm script gets hooked |
| A3 | `useTrendsData()` returns a shape distinct from `useScanData()` and benefits from a separate fixture | Open Q4 | Low — easy to merge if not |
| A4 | All shadcn primitives in this repo already include `focus-visible:` ring styling without modification | Standard Stack — Already Installed | Medium — if they don't, custom focus styles must be added per primitive (still small) |
| A5 | Contrast on `LOW` severity badge passes WCAG AA against the dark theme background | Risk Register | Medium — fix would expand token system, not just badge styling |
| A6 | The dashboard runs in production strictly behind FastAPI (`quirk/dashboard/api/`), not as a separate static site, so the same `/api/scan/latest` URL works in prod and `vite preview + middleware` in CI | Pattern 2 | Low — same-origin assumption is consistent with `useScanData.ts:24-27` |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Zero console errors and zero React warnings on `/motion`, `/trends`, `/findings`, `/data-at-rest`, and other top-level routes (allowlisted third-party warnings excepted) | Console capture harness via `puppeteer-core` or `@axe-core/puppeteer` — see Pattern §System Architecture; allowlist schema §Pattern 3; recharts pitfall §Pitfall 2 |
| DASH-02 | Explicit loading state on first paint + explicit empty state when data missing — no flash of raw empty content | Skeleton pattern §Pattern 1 (D-07 ordering: loading → error → !data → happy); per-section EmptyStateCard precedent at `motion.tsx:35-43` and `data-at-rest.tsx`; PageSpinner extraction §Recommended Project Structure |
| DASH-03 | Keyboard nav with visible focus indicators, semantic heading hierarchy, WCAG AA color contrast on findings tables — verified by axe-core or equivalent | axe-core CLI/puppeteer §Standard Stack; rules `focus-order-semantics`, `focus-visible`, `heading-order`, `page-has-heading-one`, `color-contrast` (D-16, D-17, D-18); cytoscape canvas a11y §Pitfall 6; sidebar focus styling §Risk Register |

## Sources

### Primary (HIGH confidence)
- `@axe-core/cli` README — `https://github.com/dequelabs/axe-core-npm/blob/develop/packages/cli/README.md` — `--save`, `--dir`, `--exit`, multi-URL support
- `@axe-core/cli` npm — `https://www.npmjs.com/package/@axe-core/cli` — version `4.11.3` `[VERIFIED: npm view 2026-04-30]`
- React Router v7 upgrade — `https://reactrouter.com/upgrading/v6` — future flags were a v6→v7 mechanism; project is on v7.4.0
- Project files read this session: `App.tsx`, `motion.tsx`, `data-at-rest.tsx` (excerpt), `findings.tsx` (excerpt), `executive.tsx` (excerpt), `cbom.tsx` (excerpt), `trends.tsx` (excerpt), `roadmap.tsx` (excerpt), `identity.tsx` (excerpt), `sidebar.tsx`, `useScanData.ts`, `ScanContext.tsx`, `skeleton.tsx`, `package.json`, `vite.config.ts`, `CLAUDE.md`, `43-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/config.json`

### Secondary (MEDIUM confidence)
- recharts `defaultProps` issue — `https://github.com/recharts/recharts/issues/3615` — confirms warning is upstream
- recharts React 19 — `https://github.com/recharts/recharts/issues/4558` — recharts 2.15+ supports React 19; warning persists until 3.x
- WebSearch result on axe-cli + GitHub Actions workflow patterns — referenced informally; not a single canonical doc

### Tertiary (LOW confidence)
- The exact CI provider for QU.I.R.K. — not located in workspace; inferred from CONTEXT.md "make ci" reference

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm versions verified, peer-dep compat verified
- Architecture: HIGH — derived from reading actual files, not generic patterns
- Pitfalls: HIGH — recharts/cytoscape/sidebar each verified against the codebase
- CI hook strategy: MEDIUM — no CI workflow file found; recommendation is best-fit, not verified

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (a11y tooling moves slowly; recharts 3.x adoption could shift the allowlist story sooner)
