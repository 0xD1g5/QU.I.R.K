---
phase: 43-dashboard-polish
verified: 2026-05-01T22:00:00Z
status: passed_with_overrides
score: 4/4
overrides_applied: 2
overrides:
  - gap: "Color contrast on findings tables passes WCAG AA"
    decision: "D-18 (43-CONTEXT.md) — severity badge color tokens are pre-existing brand decisions deferred to a future color-system audit phase. Violations locked into per-route baselines. Out of scope for dashboard-polish."
    accepted_by: "Digs"
    accepted_on: "2026-05-01"
    backlog: "Fix severity badge contrast ratios during future color-system audit phase"
  - gap: "Zero React warnings on all top-level routes"
    decision: "D-11/D-12 (43-CONTEXT.md, Plan 01) — recharts 2.x defaultProps warning is a known upstream issue. Allowlist approach explicitly chosen; recharts 2→3 upgrade deferred due to breaking API changes."
    accepted_by: "Digs"
    accepted_on: "2026-05-01"
    backlog: "Upgrade recharts to 3.x or replace charting primitive in a future dependency-hygiene phase"
gaps:
  - truth: "Color contrast on findings tables passes WCAG AA — verified by automated axe-core check"
    status: failed
    reason: "axe-core color-contrast violations are present on /findings, /cbom, /identity, /data-at-rest, /root, /trends. These violations were captured into per-route baseline JSONs and are accepted by the diff-mode harness (exits 0 by design), but the violations themselves remain unremediated. ROADMAP SC 4 requires findings tables to pass WCAG AA — the baseline locking mechanism does not constitute passing."
    artifacts:
      - path: "src/dashboard/tests/a11y/baseline-findings.json"
        issue: "color-contrast violation on severity badge bg-[hsl(24_95%_53%)] text-white targets in findings table"
      - path: "src/dashboard/tests/a11y/baseline-cbom.json"
        issue: "button-name violation (unnamed Radix button) + color-contrast on bg-[hsl(142_71%_45%)] text-white in CBOM table"
      - path: "src/dashboard/tests/a11y/baseline-data-at-rest.json"
        issue: "color-contrast + scrollable-region-focusable violations"
      - path: "src/dashboard/tests/a11y/baseline-root.json"
        issue: "color-contrast violation on .h-9 (executive page)"
    missing:
      - "Fix severity badge color tokens so HIGH/CRITICAL/MEDIUM/LOW badges pass 4.5:1 contrast ratio via CSS variable adjustments in index.css (D-18 compliant approach)"
      - "Fix unnamed Radix accordion/disclosure buttons on /findings and /cbom — add aria-label or visible text label to the button triggers"
      - "Fix scrollable-region-focusable on /data-at-rest overflow table — add tabindex='0' to the scrollable container"
  - truth: "Zero React warnings on all top-level routes"
    status: failed
    reason: "The recharts defaultProps React warning is still emitted at runtime on routes using recharts (executive summary, trends). It is allowlisted in console-allowlist.json so the test harness exits 0, but ROADMAP SC 1 requires 'zero React warnings', not 'zero unallowlisted React warnings'. The warning is a React 18 deprecation warning from recharts 2.x using the old defaultProps API."
    artifacts:
      - path: "src/dashboard/tests/console-allowlist.json"
        issue: "Allowlist entry suppresses the recharts warning in the harness rather than eliminating it"
      - path: "src/dashboard/src/components/ui/chart.tsx"
        issue: "Uses recharts 2.x which emits defaultProps deprecation warning"
    missing:
      - "Upgrade recharts to 3.x (which removes defaultProps usage) OR replace the recharts-dependent executive.tsx chart with a different charting primitive that does not emit React warnings"
      - "If recharts 3.x upgrade is deferred, an override should be added documenting this as an intentional deferral"
human_verification:
  - test: "Visual loading-state first paint check"
    expected: "With VITE_A11Y_FIXTURE_VARIANT=loading, hard-reload each route and observe skeleton/PageSpinner visible for ~3 seconds before content appears — no flash of empty content"
    why_human: "axe-core cannot verify visual timing behavior; automated a11y:check:loading variant is informational only per Plan 04"
  - test: "Keyboard navigation focus ring visibility"
    expected: "Tab through the sidebar on any route and observe visible blue outline ring on each Link element; Tab through table sort headers, filter inputs, and tab triggers to confirm all interactive elements are reachable with visible focus"
    why_human: "axe-core's focus-visible rule detects missing focus styles but cannot assess whether the ring is visually prominent enough in context; a developer confirmed this via Plan 04 Task 3 checkpoint but the checkpoint was self-reported"
---

# Phase 43: Dashboard Polish — Verification Report

**Phase Goal:** All top-level dashboard routes render cleanly — zero browser console errors, zero React warnings, explicit loading states on first paint, explicit empty states when data is absent, and WCAG AA baseline accessibility
**Verified:** 2026-05-01T22:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Opening all top-level routes shows zero console errors and zero React warnings | FAILED | recharts `defaultProps` React warning emitted at runtime on executive+trends routes; allowlisted in console-allowlist.json so harness exits 0, but ROADMAP SC explicitly requires "zero React warnings" |
| SC2 | Each route displays explicit loading state on first paint and explicit empty state when data is missing | VERIFIED | All 9 pages have PageSpinner or layout-matched skeleton on loading; EmptyStateCard or page-level empty on empty fixture; `npm run a11y:check:empty` exits 0; human checkpoint confirmed |
| SC3 | All interactive elements keyboard-reachable with visible focus indicators | VERIFIED | Sidebar Link primitives have `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`; axe sweep exits 0 on focus-related rules; human checkpoint confirmed Tab navigation |
| SC4 | Semantic heading hierarchy correct and color contrast on findings tables passes WCAG AA | FAILED | Heading hierarchy: VERIFIED (single h1 per render path on all 9 pages; canvas wrappers have role="img" + aria-label). Color contrast: FAILED — axe `color-contrast` violations on severity badges locked into baselines on /findings, /cbom, /identity, /data-at-rest, /root, /trends; `button-name` violations on /findings + /cbom |

**Score:** 2/4 ROADMAP success criteria verified

---

### Plan Must-Have Truths

| Plan | Truth | Status | Evidence |
|------|-------|--------|----------|
| 01 | `npm run a11y:check` boots vite preview, drives axe against 9 routes, exits 0 on no new violations | VERIFIED | harness at `src/dashboard/tests/a11y/run-a11y.mjs` (214 lines, parses cleanly); sets `VITE_A11Y_FIXTURE=1` in spawn env (line 64); baselines generated; human-verified |
| 01 | `VITE_A11Y_FIXTURE=1` activates Vite middleware; without it, middleware does not register | VERIFIED | vite.config.ts: `VITE_A11Y_FIXTURE` count=4 (gated in configureServer + configurePreviewServer); build exits 0; no src/ imports of tests/a11y/ |
| 01 | console-allowlist.json has recharts entry with 5 required fields | VERIFIED | All 5 fields present: pattern, library, upstream, owner, added |
| 01 | /print excluded from routes.json (9 routes only) | VERIFIED | routes.json has exactly 9 entries, /print absent |
| 02 | Every page renders skeleton/PageSpinner on loading | VERIFIED | All 9 pages: findings/cbom/identity/certificates use layout-matched skeletons; executive/trends/roadmap use PageSpinner with role="status" |
| 02 | Every page renders EmptyStateCard or page-level empty when fixture data missing | VERIFIED | 6 data-heavy pages use shared EmptyStateCard; 3 context-derived pages have page-level empty with h1 + explanatory text |
| 02 | Every page has exactly one h1 per render path | VERIFIED | data-heavy pages: 1 h1 in happy path (empty-state branches skip h1). context-derived pages: 1 h1 per return branch (each branch is a separate return — at most one renders) |
| 02 | EmptyStateCard shared across 6 pages (no inline definitions) | VERIFIED | `grep -c "function EmptyStateCard"` returns 0 in motion.tsx and data-at-rest.tsx; all 6 pages import from "@/components/EmptyStateCard" |
| 02 | Cytoscape canvas wrappers on /cbom and /roadmap have role="img" + aria-label | VERIFIED | cbom.tsx line 401: role="img" + descriptive aria-label; roadmap.tsx line 260: role="img" + descriptive aria-label |
| 03 | Sidebar Links receive focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 | VERIFIED | sidebar.tsx: all three utilities present (grep count=1 each) |
| 03 | No new hardcoded hsl() literals introduced | VERIFIED | 43-03-CONTRAST-AUDIT.md confirms no new hsl() literals; D-18 rule observed |
| 03 | Color tokens pass WCAG AA contrast | FAILED | Pre-existing color-contrast violations on severity badges locked into baselines (not fixed); axe exits 0 via diff-mode, not absolute compliance |
| 04 | All 9 baseline-{slug}.json files exist and are valid JSON | VERIFIED | All 9 files present with `{"violations": [...]}` structure; 4 routes with 0 violations (motion, certificates, roadmap, identity/data-at-rest partial) |
| 04 | `npm run a11y:check` exits 0 against happy-path fixture | UNCERTAIN | Cannot run headless Chrome in this environment; SUMMARY claims exit 0; human checkpoint confirms; baselines capture pre-existing violations as baseline |
| 04 | `npm run a11y:check:empty` exits 0 against empty fixture | UNCERTAIN | Same constraint — cannot run browser; human checkpoint confirmed |
| 04 | .github/workflows/dashboard-quality.yml runs a11y:check on PRs touching src/dashboard/** | VERIFIED | File exists, valid YAML, path filter `src/dashboard/**` present, `npm ci` + `npm run build` + both a11y:check steps present |
| 04 | Obsidian phase note exists | VERIFIED | `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-43-Dashboard-Polish.md` exists with `status: complete` frontmatter |
| 04 | docs/UAT-SERIES.md updated | VERIFIED | 12 UAT-43-0x entries present (>= 5 required) |
| 04 | console-allowlist.json never imported by src/ | VERIFIED | `grep -r "console-allowlist" src/dashboard/src/` returns 0 matches |

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/dashboard/tests/a11y/run-a11y.mjs` | VERIFIED | 214 lines, parses cleanly, contains AxePuppeteer, wcag2a/2aa tags, --update-baselines, console-allowlist.json reference, page.on('console') capture |
| `src/dashboard/tests/a11y/routes.json` | VERIFIED | 9 routes, no /print |
| `src/dashboard/tests/a11y/fixture-scan.json` | VERIFIED | findings:3, motion_findings:2, dar_findings:2, cbom_components:4, identity_findings:2, certificates:2, roadmap:object |
| `src/dashboard/tests/a11y/fixture-trends.json` | VERIFIED | dict with 15 keys |
| `src/dashboard/tests/console-allowlist.json` | VERIFIED | recharts entry with all 5 required fields |
| `src/dashboard/vite.config.ts` | VERIFIED | a11yFixture plugin present (count=2), VITE_A11Y_FIXTURE gated (count=4), configurePreviewServer present, registered in plugins array |
| `src/dashboard/package.json` | VERIFIED | @axe-core/puppeteer + puppeteer-core devDeps; all 4 a11y scripts present; node_modules/@axe-core/puppeteer exists |
| `src/dashboard/src/components/EmptyStateCard.tsx` | VERIFIED | Exports EmptyStateCard, Card+CardContent shell |
| `src/dashboard/src/components/PageSpinner.tsx` | VERIFIED | role="status" present, sr-only label present |
| `src/dashboard/src/pages/findings.skeleton.tsx` | VERIFIED | Exports FindingsSkeleton |
| `src/dashboard/src/pages/cbom.skeleton.tsx` | VERIFIED | Exports CbomSkeleton |
| `src/dashboard/src/pages/identity.skeleton.tsx` | VERIFIED | Exports IdentitySkeleton |
| `src/dashboard/src/pages/certificates.skeleton.tsx` | VERIFIED | Exports CertificatesSkeleton |
| `src/dashboard/tests/a11y/baseline-{root..trends}.json` | VERIFIED | All 9 exist, valid JSON with violations array |
| `.github/workflows/dashboard-quality.yml` | VERIFIED | Valid YAML, PR trigger on src/dashboard/**, npm ci + build + a11y:check + a11y:check:empty |
| `docs/UAT-SERIES.md` | VERIFIED | UAT-43-01..05 entries present (12 matches) |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-43-Dashboard-Polish.md` | VERIFIED | Exists with status: complete |
| `.planning/phases/43-dashboard-polish/43-VALIDATION.md` | VERIFIED | nyquist_compliant: true, wave_0_complete: true, status: complete, Approval: approved 2026-05-01 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run-a11y.mjs` | vite preview port 4173 | spawn with `VITE_A11Y_FIXTURE: '1'` in previewEnv | WIRED | Line 62-64: previewEnv object; line 82: spawn with env |
| `vite.config.ts a11yFixture` | `fixture-scan.json` | readFileSync in middleware handler | WIRED | `grep -c "fixture-scan.json" vite.config.ts` returns 2 |
| `run-a11y.mjs` | `console-allowlist.json` | regex match per console message | WIRED | `grep -c "console-allowlist.json" run-a11y.mjs` returns 1 |
| `findings.tsx` | `FindingsSkeleton` | `import { FindingsSkeleton } from "./findings.skeleton"` | WIRED | count=2 (import + usage) |
| All 6 data-heavy pages | `EmptyStateCard` | `import { EmptyStateCard } from "@/components/EmptyStateCard"` | WIRED | count=1 import in each of motion, data-at-rest, findings, identity, cbom, certificates |
| executive/trends/roadmap | `PageSpinner` | `import { PageSpinner } from "@/components/PageSpinner"` | WIRED | count=2 (import + usage) in each |
| `.github/workflows/dashboard-quality.yml` | `npm run a11y:check` | workflow step `run: npm run a11y:check` | WIRED | count=2 (happy + empty steps) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `executive.tsx` | `data` from `useScanData()` | ScanContext / `/api/scan/latest` (fixture in test mode) | Yes — fixture-scan.json has score, findings, etc. | FLOWING |
| `findings.tsx` | `data.findings` from `useScanData()` | Same | Yes — fixture has 3 findings items | FLOWING |
| `motion.tsx` | `data.motion_findings` from `useScanData()` | Same | Yes — fixture has 2 motion_findings items | FLOWING |
| `trends.tsx` | `data` from `useTrendsData()` | `/api/trends` (fixture in test mode) | Yes — fixture-trends.json is a dict with session data | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED for most — Cannot spawn headless Chrome (no system Chrome in verification environment). Build exits 0 confirmed as proxy.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Dashboard builds cleanly | `cd src/dashboard && npm run build` | Exit 0; 8 chunks built | PASS |
| run-a11y.mjs parses as valid ESM | `node --check src/dashboard/tests/a11y/run-a11y.mjs` | Exit 0 | PASS |
| routes.json has 9 routes, no /print | node one-liner | OK | PASS |
| All 9 baseline JSONs valid JSON with violations array | python3 json.load | All 9 valid | PASS |
| console-allowlist.json all 5 required fields | node one-liner | true | PASS |
| npm run lint | `cd src/dashboard && npm run lint` | 7 errors (4 in vite.config.ts from Phase 43-01 a11y plugin any types; 2 in motion.tsx pre-existing; 1 in ScanContext.tsx pre-existing) | FAIL (WARNING) |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DASH-01 | Zero console errors and zero React warnings on all top-level routes | PARTIAL | Console errors: none; React warnings: recharts defaultProps warning still emitted at runtime, allowlisted not eliminated |
| DASH-02 | Explicit loading state on first paint, explicit empty state when data missing | SATISFIED | All 9 pages have loading/empty branches; a11y:check:empty confirmed by human checkpoint |
| DASH-03 | WCAG AA baseline accessibility — keyboard nav, focus indicators, heading order, color contrast | PARTIAL | Keyboard nav + focus indicators: SATISFIED; heading order: SATISFIED; color contrast: FAILED (pre-existing violations locked into baselines, not fixed) |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/dashboard/vite.config.ts` lines 8-9 | `any` types in a11yFixture handler function (`(r: any)`, `(req: any, res: any, next: any)`) | Warning | Introduced by Phase 43-01; causes `@typescript-eslint/no-explicit-any` lint errors; test-only code, no production impact |
| `src/dashboard/tests/a11y/baseline-*.json` | color-contrast violations locked in baselines (6 routes) | Blocker | Severity badge inline `hsl()` classes produce WCAG AA color-contrast failures on findings tables; accepted as "pre-existing" but ROADMAP SC 4 requires these to pass |
| `src/dashboard/tests/a11y/baseline-findings.json`, `baseline-cbom.json` | button-name violations (unnamed Radix accordion triggers) | Warning | Accessibility issue — buttons with `aria-controls` but no accessible name |
| `src/dashboard/tests/a11y/baseline-data-at-rest.json` | scrollable-region-focusable violation | Warning | Overflow table not keyboard-focusable |

---

### Human Verification Required

#### 1. Loading-State First Paint

**Test:** `cd src/dashboard && VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=loading npm run preview` then hard-reload (Cmd+Shift+R) on /findings, /motion, /, /trends
**Expected:** Skeleton/PageSpinner visible on first paint, persisting ~3 seconds before content appears
**Why human:** axe-core cannot verify visual timing; automated a11y:check:loading is informational only per Plan 04

#### 2. Keyboard Focus Ring Visibility

**Test:** `cd src/dashboard && VITE_A11Y_FIXTURE=1 npm run preview` then Tab through sidebar links and interactive elements
**Expected:** Each sidebar Link shows a visible blue/ring outline on keyboard focus; all interactive elements (sort headers, filter inputs, tab triggers, buttons) are reachable and show focus indicator
**Why human:** The Plan 04 Task 3 checkpoint recorded developer approval but this was self-reported by the executing agent; an independent human should confirm focus ring visibility

---

### Gaps Summary

**Gap 1 — WCAG AA Color Contrast (Blocker for ROADMAP SC 4)**

The implementation chose to lock pre-existing color-contrast violations into axe baselines rather than fix them. The baselines capture `color-contrast` failures on severity badges (`HIGH: bg-[hsl(24_95%_53%)] text-white`, `GREEN: bg-[hsl(142_71%_45%)] text-white`) across 6 of 9 routes including `/findings`. ROADMAP SC 4 explicitly requires "color contrast on findings tables passes WCAG AA — verified by automated axe-core or equivalent check." A harness that exits 0 by design because it only checks *new* violations does not satisfy this requirement when the *existing* violations are themselves WCAG AA failures.

Root cause: Plan 03 Task 2 determined "no new violations" after running the axe sweep, but this was measured relative to the Plan 01 baselines which already contained violations. The D-18 rule (no new hsl() literals) was followed, but the pre-existing violations were not remediated. Plan 04's approach of baseline-locking deferred the fix.

To fix: adjust CSS variable tokens in `index.css` for severity badge colors to achieve 4.5:1 contrast ratio; the badge colors would need to use CSS variable tokens (not inline arbitrary hsl() classes) to be adjustable per D-18.

**Gap 2 — React Warning Still Emitted (Blocker for ROADMAP SC 1)**

The recharts `defaultProps` React warning is emitted at runtime on any route using recharts components. ROADMAP SC 1 says "zero React warnings." The console-allowlist mechanism provides a harness-level filter that makes the test exit 0, but does not eliminate the warning. The fix requires either upgrading recharts to 3.x or replacing the recharts-dependent chart.

**This looks intentional for Gap 2.** The plan explicitly chose the allowlist approach (D-11/D-12) as a third-party upstream issue. To accept this deviation, add to VERIFICATION.md frontmatter:

```yaml
overrides:
  - must_have: "zero React warnings on all top-level routes"
    reason: "recharts 2.x defaultProps deprecation warning is a third-party upstream issue (tracked recharts/recharts#3615); upgrading to recharts 3.x is a separate phase. Allowlisted in console-allowlist.json. The warning is benign and does not affect functionality."
    accepted_by: "{your name}"
    accepted_at: "{ISO timestamp}"
```

**This looks intentional for parts of Gap 1.** The severity badge color violations are pre-existing inline hsl() classes from Phase 39 (DAR tab) and earlier phases. Phase 43 explicitly scoped its contrast work to "no new violations" via D-18. To accept this deviation, add:

```yaml
  - must_have: "color contrast on findings tables passes WCAG AA"
    reason: "Pre-existing inline hsl() severity badge classes from pre-Phase-43 work produce color-contrast failures; D-18 prevents new hsl() literals but does not require retroactive fix of existing ones. Badge token refactor deferred to a future phase. axe harness exits 0 with no new violations introduced."
    accepted_by: "{your name}"
    accepted_at: "{ISO timestamp}"
```

**Other issues (WARNING, not blocking ROADMAP SCs):**
- Lint: 7 errors (4 from Phase 43 vite.config.ts any types in the test harness plugin). Production build unaffected — lint failures are in test infrastructure and pre-existing page code.
- button-name violations on /findings + /cbom (unnamed Radix accordion triggers) — accessibility improvement opportunity not caught by Phase 43.
- scrollable-region-focusable on /data-at-rest — overflow table needs `tabindex="0"`.

---

*Verified: 2026-05-01T22:00:00Z*
*Verifier: Claude (gsd-verifier)*
