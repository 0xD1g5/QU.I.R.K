---
phase: 43
slug: dashboard-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from `43-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom Node harness driving `@axe-core/puppeteer` (NEW — added by this phase) + existing `npm run lint` (ESLint) for inline guards |
| **Config file** | `src/dashboard/tests/a11y/routes.json`, `src/dashboard/tests/console-allowlist.json` (NEW) |
| **Quick run command** | `cd src/dashboard && npm run lint` |
| **Full suite command** | `cd src/dashboard && npm run build && npm run a11y:check` |
| **Estimated runtime** | ~45–90 seconds for full a11y sweep (10 routes × ~5–8s each, parallelized into 3-route batches) |

---

## Sampling Rate

- **After every task commit:** Run `cd src/dashboard && npm run lint` (existing ESLint config catches React hooks violations, missing key props, prop typos)
- **After every plan wave:** Run `cd src/dashboard && npm run build && npm run a11y:check` — full axe + console sweep across all 10 routes against the seeded fixture
- **Before `/gsd-verify-work`:** Full suite green; every per-route baseline JSON either committed or reviewed in PR
- **Max feedback latency:** ≤ 90 seconds (lint < 5s, build ~15s, a11y ~45–60s)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 43-XX-XX | TBD (planner assigns) | 0 | DASH-01..03 (infra) | T-43-01 (fixture leak in prod bundle) | `VITE_A11Y_FIXTURE` env never read by app code; production build excludes fixture JSON | smoke (build inspection) | `cd src/dashboard && npm run build && grep -L fixture-scan.json dist/` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 1 | DASH-01 | — | Zero unallowlisted `console.warn`/`console.error` per route | smoke (puppeteer) | `cd src/dashboard && npm run a11y:check` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 1 | DASH-02 (loading) | — | First-paint render is skeleton when `useScanData()` loading=true | smoke (axe-run with delayed-response fixture variant) | `VITE_A11Y_FIXTURE_VARIANT=loading npm run a11y:check:loading` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 1 | DASH-02 (empty) | — | `EmptyStateCard`/page-level empty renders when fixture is empty | smoke (axe-run with empty fixture) | `VITE_A11Y_FIXTURE_VARIANT=empty npm run a11y:check:empty` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 2 | DASH-03 (keyboard) | — | All interactives keyboard-reachable with visible focus | axe-core `focus-order-semantics`, `focus-visible` | `cd src/dashboard && npm run a11y:check` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 2 | DASH-03 (heading) | — | One `<h1>` per route; ordered `<h2>`/`<h3>` | axe-core `heading-order`, `page-has-heading-one` | `cd src/dashboard && npm run a11y:check` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 2 | DASH-03 (contrast) | — | WCAG AA on findings tables | axe-core `color-contrast` | `cd src/dashboard && npm run a11y:check` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 2 | DASH-03 (canvas a11y) | — | Cytoscape canvases on `/cbom`, `/roadmap` have `role="img"` + `aria-label` | axe-core `image-alt`, `region` | `cd src/dashboard && npm run a11y:check` | ❌ W0 | ⬜ pending |
| 43-XX-XX | TBD | 3 | DASH-01 (allowlist hygiene) | T-43-02 (allowlist as runtime suppression) | Allowlist JSON imported only by test harness, never by app code | smoke (lint/grep) | `cd src/dashboard && ! grep -r console-allowlist.json src/` | ❌ W0 | ⬜ pending |

*Final task IDs assigned by gsd-planner. Threat refs to be cross-linked after PLAN.md threat models are written.*
*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/dashboard/tests/a11y/run-a11y.mjs` — harness driving `@axe-core/puppeteer` (axe + console capture in one pass)
- [ ] `src/dashboard/tests/a11y/routes.json` — canonical 10-route list (mirrors `App.tsx:30-39`, excludes `/print`)
- [ ] `src/dashboard/tests/a11y/fixture-scan.json` — seeded `/api/scan/latest` payload covering motion / identity / dar / cbom / certificates / findings / roadmap / summary scores
- [ ] `src/dashboard/tests/a11y/fixture-trends.json` — seeded `/api/scan/trends` payload
- [ ] `src/dashboard/tests/a11y/baseline-{root,findings,identity,motion,data-at-rest,certificates,cbom,roadmap,trends}.json` — 9 baselines (one per route after `/print` exclusion)
- [ ] `src/dashboard/tests/console-allowlist.json` — recharts `defaultProps` deprecation + any others surfaced during Wave-1 baseline run
- [ ] `src/dashboard/vite.config.ts` — extend with `a11yFixture` plugin gated by `VITE_A11Y_FIXTURE` env
- [ ] `src/dashboard/package.json` — add `a11y:check`, `a11y:check:empty`, `a11y:check:loading`, `a11y:baseline` scripts; add `@axe-core/puppeteer` and `puppeteer-core` devDeps
- [ ] `.github/workflows/dashboard-quality.yml` — new GitHub Actions workflow per D-19 (PR trigger on `src/dashboard/**` paths)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual regression of skeleton vs final layout | DASH-02 (loading) | No visual-regression tool in scope this phase (Storybook/Percy deferred) | Reviewer compares skeleton screenshots to live page during PR review |
| Subjective "feels polished" smoke | DASH-01..03 | axe-core does not measure UX quality | Reviewer manually clicks through all 10 routes in browser before approving merge |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (a11y harness, fixtures, baselines, allowlist, CI workflow)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner finalizes task IDs and threat refs)

**Approval:** pending
