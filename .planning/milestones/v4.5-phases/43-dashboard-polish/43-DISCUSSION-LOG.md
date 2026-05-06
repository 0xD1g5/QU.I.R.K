# Phase 43: Dashboard Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 43-dashboard-polish
**Areas discussed:** WCAG verification strategy, Loading state pattern, Empty state strategy, Console-error budget

---

## WCAG Verification Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot axe CLI script | `@axe-core/cli` devDep + `npm run a11y` script hits each route on `vite preview`, writes baseline JSON. CI diffs against baseline. | ✓ |
| Playwright + axe-core in CI | Stand up Playwright as the dashboard's first e2e framework, run `@axe-core/playwright` per PR. Most durable, but adds 5–10 min CI time and a full framework. | |
| Vitest + jsdom + jest-axe | Component-level axe checks via Vitest + RTL + jest-axe. Cheaper than Playwright but misses focus order / live-region issues. | |
| Manual checklist + screenshots | Document SCs, run axe DevTools manually per route, attach screenshots. No automation. Falls below SC #4 bar. | |

**User's choice:** Option 1 (axe-core CLI), after Claude offered a recommendation.
**Notes:** User initially leaned toward Option 2 (Playwright) but flagged it as outside their expertise. Claude recommended Option 1 on the basis that (a) it satisfies SC #4 literally, (b) Playwright adoption is itself phase-shaped work that would inflate Phase 43 scope, (c) Phase 44 (UAT Debt Automation) is the natural home for Playwright and baselines port via `@axe-core/playwright` 1:1 with no rework. User accepted the recommendation.

---

## Loading State Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Per-page hand-tuned skeletons | Each data-heavy route gets a layout-matched skeleton mirroring Phase 39's motion/DAR pattern. Lighter context-derived routes use a shared `<PageSpinner>`. | ✓ |
| Shared `<PageSkeleton>` for all | One skeleton with rough header + content shapes used on every route. Less code, less polish, visually homogeneous. | |
| Spinner-only | Single shared `<PageSpinner>` centered in page region. Fastest to ship, least informative. | |

**User's choice:** Per-page hand-tuned skeletons (Recommended).
**Notes:** Continues the precedent set by Phase 39 (which used a layout-matched skeleton on `/data-at-rest`). The split keeps polish high on data-heavy routes without adding noise on routes that derive from in-context data.

---

## Empty State Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid — per-section where meaningful | Per-section `EmptyStateCard` on routes with category sub-grouping (`/motion`, `/data-at-rest`, `/findings`, `/identity`, `/cbom`, `/certificates`); page-level on `/`, `/trends`, `/roadmap`. Rule documented in CONTEXT/PLAN. | ✓ |
| Per-section everywhere | Every route with any sub-grouping gets per-section empty cards. Maximum information density, risk of visual noise. | |
| Page-level only | Single 'No scan data' card per route. Simplest, loses Phase 39's already-shipped granularity. | |

**User's choice:** Hybrid (Recommended).
**Notes:** Preserves Phase 36/39 per-section idiom on routes where category absence is itself meaningful (e.g., "no JWT findings" tells the user something), avoids visual noise on overview routes. Decision rule will be codified in CONTEXT.md so future routes inherit the same pattern.

---

## Console-Error Budget

| Option | Description | Selected |
|--------|-------------|----------|
| Strict zero w/ allowlist | Audit current warnings, fix every QUIRK-owned one, then add a documented allowlist for known-benign third-party noise (recharts, react-router). CI helper asserts no NEW warnings outside the allowlist. | ✓ |
| Strict zero, no exceptions | Patch or fork third-party libs as needed. Most defensible on paper, ongoing dep burden. | |
| Only QUIRK code must be clean | "No warnings from src/dashboard/**" rule. Pragmatic but loose interpretation of SC #1 ("zero"). | |

**User's choice:** Strict zero with documented allowlist (Recommended).
**Notes:** Each allowlist entry must include pattern, source library, upstream issue link, owner, and date added. Allowlist is a test-time assertion; production builds do NOT silence `console.warn`/`console.error`.

---

## Claude's Discretion

- Exact baseline-fixture mechanism for axe runs (Vite middleware mock vs JSON fixture vs MSW)
- Skeleton component file layout (per-page co-located vs centralized in `components/skeletons/`)
- Whether the console-capture helper is a standalone Node script or piggybacks on the axe-core CLI run
- Order in which routes are polished (no functional impact on phase outcome)

## Deferred Ideas

- **Playwright + @axe-core/playwright migration** — Phase 44 (UAT Debt Automation)
- **Drill-down evidence panel** (carried forward from Phase 39 deferral) — future UX phase
- **Visual regression testing** (Percy / Chromatic / Playwright snapshots) — needs the e2e framework Phase 43 explicitly avoided
- **Storybook adoption for skeletons/empty states** — own tooling phase
- **Cross-finding KMS key inventory view** — carried forward from Phase 39 deferral
- **Automated UAT for full dashboard interaction flows** — Phase 44
