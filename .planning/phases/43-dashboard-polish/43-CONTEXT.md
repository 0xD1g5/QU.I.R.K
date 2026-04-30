# Phase 43: Dashboard Polish - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Sweep all top-level dashboard routes — `/`, `/findings`, `/identity`, `/motion`, `/data-at-rest`, `/certificates`, `/cbom`, `/roadmap`, `/trends` — so each renders cleanly: zero browser console errors and zero React warnings (per a documented allowlist), explicit loading states on first paint, explicit empty states when scan data is absent, full keyboard operability with visible focus indicators, correct semantic heading hierarchy, and WCAG AA color contrast on findings tables. Implementation polish only — no new features, no scoring/scanner changes, no schema changes. Routes are already wired in `src/dashboard/src/App.tsx`; this phase touches their content and the supporting test/CI surface that proves the SC bar.

</domain>

<decisions>
## Implementation Decisions

### WCAG Verification Strategy
- **D-01 (revised after research 2026-04-30):** WCAG AA verification is automated via **`@axe-core/puppeteer`** running against a `vite preview` server. The same harness *also* captures `console.warn` / `console.error` per route, satisfying SC #1 in one CI step instead of two. Originally CONTEXT.md picked `@axe-core/cli`; research (`43-RESEARCH.md`) found the CLI does not surface console messages, so a second tool would be needed anyway. `@axe-core/puppeteer` collapses both gates into a single harness with no Playwright adoption (puppeteer-core is library-only, ~50MB chromium download).
- **D-02:** Per-route baselines stored at `src/dashboard/tests/a11y/baseline-{route-slug}.json`. Any new violation outside the baseline fails CI.
- **D-03:** A seeded scan fixture is required so axe runs against populated routes (not the empty-state branch). Planner picks the fixture mechanism — researcher recommends Vite middleware gated by `VITE_A11Y_FIXTURE=1` (~30 lines, zero new deps, no MSW).
- **D-04:** Migration door for Phase 44 — when Phase 44 adopts Playwright for UAT scenarios, the axe-core ruleset and baseline JSONs port to `@axe-core/playwright` with minimal rework (the harness changes shape; the baselines do not).

### Loading State Pattern
- **D-05:** Per-page hand-tuned skeletons on data-heavy routes — `/findings`, `/cbom`, `/motion`, `/data-at-rest`, `/identity`, `/certificates`. Each skeleton mirrors its page's layout structure (header gauges, table rows, side panels). Reuses the shadcn `<Skeleton>` primitive already in use on `/data-at-rest` from Phase 39.
- **D-06:** Shared `<PageSpinner>` component on context-derived routes — `/`, `/trends`, `/roadmap`. These routes render projections of `useScanData()` already in context, so layout-matched skeletons add visual noise without latency benefit.
- **D-07:** Loading state must be present *on first paint* — no flash of empty content before the loading view renders. Planner verifies this by checking that the page component's initial render path returns the skeleton/spinner branch when `useScanData()` is in `loading` state, not `null`/empty.

### Empty State Strategy
- **D-08:** Hybrid empty-state strategy:
  - **Per-section `EmptyStateCard` (Phase 39 pattern)** on routes with category sub-grouping: `/motion`, `/data-at-rest`, `/findings`, `/identity`, `/cbom`, `/certificates`. Each section names its category and points at the relevant scanner config.
  - **Single page-level empty state** on routes without sub-grouping: `/` (Executive), `/trends`, `/roadmap`.
- **D-09:** Documented decision rule (in CONTEXT/PLAN, not just code): "Use per-section empty cards on any route that already groups findings or scoring by category in its happy path. Use a single empty state when no sub-grouping exists."
- **D-10:** Empty-state messages must answer the question *what scanner produces this data and how does the user enable it?* Mirrors the precedent set by `motion.tsx` and Phase 39's DAR sections.

### Console-Error Budget
- **D-11:** "Strict zero with documented allowlist." Every QUIRK-owned warning is fixed in Phase 43. Third-party benign warnings (recharts `defaultProps` deprecation, react-router future-flag warnings) are captured in `src/dashboard/tests/console-allowlist.json`.
- **D-12:** Each allowlist entry MUST include: pattern (regex or exact string match), source library, upstream issue link, owner ("third-party / waiting on upstream"), and date added. Allowlist entries without all five fields fail CI lint.
- **D-13:** A small console-capture helper runs as part of the `a11y:check` flow: navigates each route, captures all `console.warn` / `console.error` calls, and asserts every captured message matches an allowlist entry. New unallowlisted warnings fail CI.
- **D-14:** Production build must NOT silence `console.warn`/`console.error` globally. The allowlist is a *test-time* assertion, not a runtime suppression.

### Keyboard Navigation & Focus (Success Criterion #3)
- **D-15:** Focus indicators use Tailwind's `focus-visible:` utilities (`focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`) applied via shadcn primitives. Custom focus styles are only added where shadcn primitives don't already provide them.
- **D-16:** Sweep covers all interactive elements: tabs, buttons, sortable table headers, filter inputs, sidebar nav links, severity badge filters. Verified by axe-core's `focus-order-semantics` and `focus-visible` rules — no manual checklist.

### Heading Hierarchy & Color Contrast (Success Criterion #4)
- **D-17:** Each route has exactly one `<h1>` (the page title), with `<h2>` for major sections and `<h3>` for sub-sections. Verified by axe-core's `heading-order` and `page-has-heading-one` rules.
- **D-18:** Color contrast on findings tables (severity badges, table text on muted backgrounds) verified by axe-core's `color-contrast` rule. Any failures fixed via the existing CSS-variable token system — no hardcoded `hsl()` values introduced (Phase 39 D-13 baseline).

### CI Wiring (added after research 2026-04-30)
- **D-19:** Phase 43 creates `.github/workflows/dashboard-quality.yml` (the repo currently has no GitHub Actions workflows). The workflow runs on PRs that touch `src/dashboard/**` and executes `npm run a11y:check` (which transitively covers the console-allowlist gate via the shared puppeteer harness). Picked over folding into a (currently absent) pytest workflow because the dashboard quality gate has no Python dependencies.
- **D-20:** Cytoscape canvases on `/cbom` and `/roadmap` are known to fail axe `image-alt` / `region` rules. Phase 43 wraps each canvas with `role="img"` + a descriptive `aria-label` (one-liner per page). Researcher flagged this as a concrete plannable item, not a generic concern.
- **D-21:** `react-router` future-flag warnings are NOT expected — package.json is on `react-router-dom@7.4.0` and those warnings were the v6→v7 migration mechanism. Allowlist seed therefore only needs the recharts `defaultProps` deprecation (verified upstream issue recharts/recharts#3615; affects `/` Executive `BarChart`).

### Claude's Discretion
- Exact baseline-fixture mechanism for axe runs (Vite middleware mock vs JSON fixture vs MSW). Planner picks based on least-friction integration with `vite preview`.
- Skeleton component file layout: per-page co-located (`pages/findings.skeleton.tsx`) vs centralized (`components/skeletons/`). Either is acceptable; consistency within the chosen pattern matters more than the choice itself.
- Whether the console-capture helper is a standalone Node script or piggybacks on the axe-core CLI run. Both work.
- Order of route work — researcher/planner sequences routes by complexity or risk; phase outcome is identical regardless of order.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 43: Dashboard Polish" — Goal, Success Criteria 1–4, Requirements list (DASH-01, DASH-02, DASH-03), depends-on (Phase 39, Phase 42)
- `.planning/REQUIREMENTS.md` — DASH-01 (zero console errors), DASH-02 (loading + empty states), DASH-03 (keyboard nav + WCAG AA)
- `.planning/STATE.md` — current milestone v4.5 "Reliability & Gap Closure"; Phase 43 is the dashboard polish gate before Phase 44 (UAT Debt Automation)

### Closest Reference Patterns (Prior Dashboard Phases)
- `.planning/phases/36-dashboard-motion-tab/` — original tab-pattern phase
- `.planning/phases/39-data-at-rest-dashboard-tab/39-CONTEXT.md` §"Deferred Ideas" — explicitly defers loading polish, focus indicators, and WCAG sweep to Phase 43
- `.planning/phases/39-data-at-rest-dashboard-tab/39-CONTEXT.md` §"Code Context" — establishes per-section EmptyStateCard pattern, CSS-variable color tokens, severity-sorted tables. Phase 43 inherits and extends.
- `src/dashboard/src/pages/motion.tsx` — primary reference for `EmptyStateCard`, `SEV_ORDER`, severity-sorted tables, shadcn composition. The pattern Phase 43 enforces app-wide on data-heavy routes.
- `src/dashboard/src/pages/data-at-rest.tsx` — most recent realization of the per-section pattern; covers all 4 DAR categories.

### Frontend Touchpoints (all 10 routes — sweep target)
- `src/dashboard/src/App.tsx` lines 17–28 — Routes block; canonical list of routes Phase 43 covers
- `src/dashboard/src/pages/executive.tsx` — `/`
- `src/dashboard/src/pages/findings.tsx` — `/findings`
- `src/dashboard/src/pages/identity.tsx` — `/identity`
- `src/dashboard/src/pages/motion.tsx` — `/motion` (also serves as pattern reference)
- `src/dashboard/src/pages/data-at-rest.tsx` — `/data-at-rest` (also serves as pattern reference)
- `src/dashboard/src/pages/certificates.tsx` — `/certificates`
- `src/dashboard/src/pages/cbom.tsx` — `/cbom`
- `src/dashboard/src/pages/roadmap.tsx` — `/roadmap`
- `src/dashboard/src/pages/trends.tsx` — `/trends`
- `src/dashboard/src/pages/print.tsx` — `/print` (NOT in scope; PDF render path, separate concerns)
- `src/dashboard/src/components/sidebar.tsx` — keyboard nav target; focus styles audited here
- `src/dashboard/src/components/ui/skeleton.tsx` — shadcn primitive for D-05 skeletons
- `src/dashboard/src/hooks/useScanData.ts` — `loading` state branch is the trigger for skeleton/spinner rendering

### Backend Surface (NOT modified by this phase)
- `quirk/dashboard/api/schemas.py` — schema is fixed; Phase 43 does not change API shape
- `quirk/dashboard/api/routes/scan.py` — routes are fixed; only consumption changes

### Test Infrastructure (created by this phase)
- `src/dashboard/tests/a11y/baseline-{route-slug}.json` — per-route axe-core baselines (NEW)
- `src/dashboard/tests/console-allowlist.json` — third-party warning allowlist (NEW)
- `src/dashboard/package.json` — adds `@axe-core/cli` devDep + `a11y:check` and `console:check` scripts (NEW)

### Downstream Phases That Depend On This
- Phase 44 (UAT Debt Automation): inherits the axe-core baseline mechanism — when Phase 44 adopts Playwright, baselines port via `@axe-core/playwright` with no rework
- v4.5 release gate — DASH-01/02/03 must move from `pending` to `passing` before milestone close

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/src/pages/motion.tsx` — `EmptyStateCard`, `SEV_ORDER`, `SEVERITY_STYLES`, severity-sorted table render pattern. Phase 43 extends these app-wide.
- `src/dashboard/src/pages/data-at-rest.tsx` — Phase 39 realization of per-section empty states across 4 categories; demonstrates the pattern Phase 43 enforces on the remaining data-heavy routes.
- `src/dashboard/src/components/ui/skeleton.tsx` — shadcn `<Skeleton>` primitive; basis for D-05 layout-matched skeletons.
- `src/dashboard/src/components/ui/{card,table,badge,tabs,tooltip}.tsx` — shadcn primitives already supply `focus-visible:` ring styles. Most focus polish is verifying, not authoring.
- `src/dashboard/src/hooks/useScanData.ts` — exposes `loading` and `data` states that drive skeleton/empty rendering.

### Established Patterns
- **Per-section empty states (Phase 36, 39):** `<EmptyStateCard>` per category section, named with the category and pointing at scanner config. Phase 43 enforces this on `/findings`, `/identity`, `/cbom`, `/certificates`.
- **CSS-variable color tokens (Phase 39 D-13):** All color tokens go through CSS variables via Tailwind's theme; no hardcoded `hsl()`. Phase 43 contrast fixes must comply.
- **Severity ordering:** `SEV_ORDER` constant from `motion.tsx` (CRITICAL → HIGH → MEDIUM → LOW → INFO). Reused everywhere finding rows render.
- **Sidebar nav order (Phase 39 D-11):** Executive · Findings · Identity · Motion · Data at Rest · Certificates · CBOM · Roadmap · Trends. Locked.

### Integration Points
- **CI hook:** existing `make ci` / pytest pipeline must gain a frontend a11y step. Planner picks the integration shape (separate `npm run a11y:check` job vs combined with build).
- **Test infrastructure:** dashboard currently has zero JS test infrastructure (no vitest, playwright, jest). Phase 43 adds `@axe-core/cli` only — minimal footprint, no full test framework.
- **Vite preview server:** axe-core needs the built dashboard served somewhere; `vite preview` is the existing-stack-friendly option.

</code_context>

<specifics>
## Specific Ideas

- The user explicitly chose Option 1 (axe CLI) over Option 2 (Playwright) after weighing scope creep — Phase 43 must remain a polish phase, not "adopt our first e2e framework" phase. Planner must respect this scope discipline; do not propose Playwright in this phase.
- The user accepted strict-zero-with-allowlist on console errors — recharts and react-router warnings are the most likely allowlist entries based on the dashboard's dependency list.

</specifics>

<deferred>
## Deferred Ideas

- **Playwright + @axe-core/playwright migration** — natural Phase 44 work; baselines from Phase 43 port 1:1.
- **Drill-down evidence panel (Phase 39 deferral)** — clicking a row to see raw scanner evidence JSON. Out of Phase 43 polish scope; could be its own UX phase.
- **Visual regression testing** (Percy / Chromatic / Playwright snapshots) — not in Phase 43; would require the same e2e framework adoption Phase 43 explicitly avoided.
- **Storybook adoption for skeletons/empty states** — could improve component reuse and docs, but is a tooling phase of its own.
- **Cross-finding KMS key inventory view** (Phase 39 deferral) — still deferred; not Phase 43.
- **Automated UAT for full dashboard interaction flows** — Phase 44 (UAT Debt Automation).

</deferred>

---

*Phase: 43-dashboard-polish*
*Context gathered: 2026-04-30*
