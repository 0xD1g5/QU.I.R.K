---
status: complete
phase: 43-dashboard-polish
source:
  - .planning/phases/43-dashboard-polish/43-01-SUMMARY.md
  - .planning/phases/43-dashboard-polish/43-02-SUMMARY.md
  - .planning/phases/43-dashboard-polish/43-03-SUMMARY.md
  - .planning/phases/43-dashboard-polish/43-04-SUMMARY.md
started: 2026-05-02T00:00:00Z
updated: 2026-05-02T00:10:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

## Current Test

[testing complete]

## Tests

### 1. A11y Harness — Happy Path
expected: |
  Run `npm run a11y:check` from `src/dashboard/`. The harness boots Vite preview with
  the seeded fixture, navigates all 9 routes via headless Chrome, and runs axe-core.
  Command exits 0 with no new violations reported beyond the locked baselines.
result: issue
reported: "Per-route output shows PASS (no new violations) on all 9 routes, but the final summary block labels 6 routes as FAIL based on raw violation count rather than baseline delta. The summary uses the wrong signal — it should show PASS for any route where violations == baseline count (no new violations), not FAIL for routes that have existing baseline violations."
severity: major

### 2. A11y Harness — Empty State Variant
expected: |
  Run `npm run a11y:check:empty` from `src/dashboard/`. The harness runs all 9 routes
  with the empty fixture variant (no scan data). Command exits 0 — every page's empty
  state is accessible with no new violations.
result: pass

### 3. Skeleton Loaders on All Pages
expected: |
  With the dev server running and network throttled (or loading fixture active), navigate
  to Findings, CBOM, Identity, and Certificates pages. Each shows a layout-matched
  skeleton (placeholder rows/cards matching the real layout) before data arrives — not
  a blank page or spinner only.
result: pass

### 4. Empty State Cards When No Scan Data
expected: |
  Using the empty fixture variant (VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=empty),
  open each page. Every page shows an explicit EmptyStateCard or empty-state message
  rather than blank whitespace or a crash. E.g. Findings shows "No findings", CBOM shows
  its empty message, etc.
result: pass

### 5. Keyboard Focus Rings on Sidebar
expected: |
  Open the dashboard in a browser. Press Tab to navigate into the sidebar. Each nav link
  (Findings, Certificates, CBOM, etc.) shows a visible focus ring (blue outline) when
  focused. No link is skipped or invisible when tabbed through.
result: pass

### 6. GitHub Actions Workflow File
expected: |
  `.github/workflows/dashboard-quality.yml` exists and is correctly configured:
  triggers on PRs touching `src/dashboard/**`, runs `npm ci → build → lint → a11y:check
  → a11y:check:empty`, and includes a Chrome installation step before the a11y steps.
result: pass

### 7. Executive Summary PDF Export
expected: |
  Open the Executive Summary page in a browser. Click the PDF export/download button.
  A PDF file is saved to disk (not just a silent no-op). The download completes
  successfully without errors.
result: issue
reported: "failed due to playwright issue"
severity: major

### 8. Pagination Controls on Findings and Identity Pages
expected: |
  Open the Findings page and Identity page. Both show Previous/Next pagination buttons
  below their tables, along with a "Page X of Y" counter. Clicking Next advances to the
  next page of results (relevant when a scan has more than 25 findings/identities).
result: issue
reported: "no numbers at all — pagination controls not visible on either page"
severity: major

### 9. Loading Variant — Skeleton Before Content
expected: |
  Run `VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=loading npx vite preview` from
  `src/dashboard/`. Navigate to the dashboard. The scan API responds with a ~3s delay,
  so PageSpinner or skeleton loaders are visible for approximately 3 seconds before
  content populates. Both scan and trends endpoints are delayed.
result: pass

## Summary

total: 9
passed: 6
issues: 3
pending: 0
skipped: 0
skipped: 0

## Gaps

- truth: "npm run a11y:check summary block shows PASS for routes with no new violations, even when those routes have existing baseline violations"
  status: failed
  reason: "User reported: Per-route output shows PASS (no new violations) on all 9 routes, but the final summary block labels 6 routes as FAIL based on raw violation count rather than baseline delta."
  severity: major
  test: 1
  artifacts:
    - src/dashboard/tests/a11y/run-a11y.mjs
  missing:
    - Summary reporting logic must compare violations == baseline count (not violations > 0) to determine PASS/FAIL per route

- truth: "Executive Summary PDF export button saves a PDF file to disk"
  status: failed
  reason: "User reported: failed due to playwright issue"
  severity: major
  test: 7
  artifacts:
    - src/dashboard/src/pages/executive.tsx
  missing:
    - PDF download working end-to-end in browser without Playwright/automation interference

- truth: "Findings and Identity pages show Previous/Next pagination buttons and page counter below their tables"
  status: failed
  reason: "User reported: no numbers at all — pagination controls not visible on either page"
  severity: major
  test: 8
  artifacts:
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/identity.tsx
  missing:
    - Pagination controls JSX rendered below table in both pages
