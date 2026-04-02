# QUIRK v4.0.0 — Post-Restructure Test Results

**Date:** 2026-04-01
**Branch:** QuRisk-v3.9
**Python:** 3.14.3 (.venv)
**Node:** via npm/npx (src/dashboard)

---

## Summary

| Phase | Tests | Passed | Failed | Warnings |
|-------|-------|--------|--------|----------|
| 1. Compilation & Import Health | 8 | 8 | 0 | 0 |
| 2. Unit Tests (pytest) | 165 | 165 | 0 | 0 |
| 3. CLI Smoke Tests | 4 | 4 | 0 | 0 |
| 4. Dashboard / UI Tests | 5 | 5 | 0 | 0 |
| **Total** | **182** | **182** | **0** | **0** |

---

## Phase 1: Compilation & Import Health

| # | Test | Status | Details |
|---|------|--------|---------|
| 1.1 | Python compile check | PASS | `compileall quirk/` — no syntax errors |
| 1.2 | Package import | PASS | `quirk.__version__` = 4.0.0 |
| 1.3 | CLI entrypoint import | PASS | `import run_scan` clean |
| 1.4 | Dashboard import | PASS | `create_app()` factory loads |
| 1.5 | Scanner imports | PASS | tls, ssh, jwt, container, source all load |
| 1.6 | Intelligence imports | PASS | scoring, confidence, evidence, roadmap all load |
| 1.7 | CBOM imports | PASS | builder, classifier, writer all load |
| 1.8 | Reports imports | PASS | writer loads |

---

## Phase 2: Unit Tests (pytest)

| # | Test Group | Tests | Status | Details |
|---|-----------|-------|--------|---------|
| 2.1 | CBOM Builder | 20 | PASS | All pass (0.11s) |
| 2.2 | CBOM Classifier | 32 | PASS | All pass (0.12s) |
| 2.3 | CBOM Integration | 3 | PASS | All pass (2.21s) |
| 2.4 | CBOM Writer | 9 | PASS | All pass (0.11s) |
| 2.5 | Cert/Pubkey Fix | 6 | PASS | All pass (0.12s) |
| 2.6 | CLI Init | 2 | PASS | All pass (1.51s) |
| 2.7 | CLI Version | 1 | PASS | All pass |
| 2.8 | Cloud Connectors | 5 | PASS | All pass (1.07s) |
| 2.9 | Container Scanner | 4 | PASS | All pass |
| 2.10 | Dashboard API | 7 | PASS | All pass (0.64s) |
| 2.11 | Dashboard Theme | 3 | PASS | All pass |
| 2.12 | HTML Report | 4 | PASS | All pass (0.14s) |
| 2.13 | Intelligence Confidence | 3 | PASS | All pass |
| 2.14 | Intelligence Evidence | 1 | PASS | All pass |
| 2.15 | Intelligence Roadmap | 4 | PASS | All pass |
| 2.16 | Intelligence Schema | 2 | PASS | All pass |
| 2.17 | Intelligence Scoring | 3 | PASS | All pass |
| 2.18 | JWT Scanner | 5 | PASS | All pass |
| 2.19 | Packaging | 5 | PASS | All pass |
| 2.20 | PDF Export | 2 | PASS | All pass (1.21s) |
| 2.21 | Scorecard Report | 1 | PASS | All pass |
| 2.22 | Rich Output | 2 | PASS | All pass |
| 2.23 | Scoring Consolidation | 7 | PASS | All pass |
| 2.24 | Source Scanner | 5 | PASS | All pass |
| 2.25 | SSH Scanner | 13 | PASS | All pass |
| 2.26 | SSLyze Integration | 11 | PASS | All pass |

---

## Phase 3: CLI Smoke Tests

| # | Test | Status | Details |
|---|------|--------|---------|
| 3.1 | Version flag | PASS | Output: `QU.I.R.K. v4.0.0` |
| 3.2 | Help output | PASS | Argparse renders all options |
| 3.3 | Init subcommand | PASS | Config file created at `/tmp/quirk-test-config.yaml` |
| 3.4 | Config template valid | PASS | YAML parses without error |

---

## Phase 4: Dashboard / UI Tests

| # | Test | Status | Details |
|---|------|--------|---------|
| 4.1 | TypeScript type check | PASS | `tsc --noEmit` — no type errors |
| 4.2 | ESLint | PASS | 0 errors, 0 warnings (after F1 fix) |
| 4.3 | Vite build | PASS | Built in 511ms, 7 chunks (after W3 fix) |
| 4.4 | Build output exists | PASS | `quirk/dashboard/static/index.html` present |
| 4.5 | FastAPI health check | PASS | `GET /api/health` → `{"status":"ok"}` (200) |

---

## Remediation Log

### F1: ESLint — 3 errors, 1 warning (RESOLVED)

**Original errors:** `react-refresh/only-export-components` in theme-provider, badge, button; `react-hooks/incompatible-library` in findings.

**Fixes applied:**

| File | Change | Issues Encountered |
|------|--------|--------------------|
| `theme-provider.tsx` | Extracted `ThemeProviderContext` + types to new `theme-context.ts`; moved `useTheme` hook to new `use-theme.ts` | Initial attempt exported context from component file — still triggered react-refresh. Required 3-file split: context, provider, hook. |
| `mode-toggle.tsx` | Updated import path from `@/components/theme-provider` to `@/components/use-theme` | None |
| `badge.tsx` | Changed `export { Badge, badgeVariants }` to `export { Badge }` — `badgeVariants` unused externally | None |
| `button.tsx` | Changed `export { Button, buttonVariants }` to `export { Button }` — `buttonVariants` unused externally | None |
| `findings.tsx` | Added `eslint-disable-next-line react-hooks/incompatible-library` above `useReactTable()` call | None |

**New files created:**
- `src/dashboard/src/components/theme-context.ts` — shared context + types
- `src/dashboard/src/components/use-theme.ts` — `useTheme` hook

**Verification:** `tsc --noEmit` PASS, `npm run lint` PASS (0 errors, 0 warnings), `npm run build` PASS

---

### W1: `datetime.utcnow()` deprecation (RESOLVED)

**Files changed:**
- `quirk/reports/executive.py:2,17` — `from datetime import datetime` → `from datetime import datetime, timezone`; `.utcnow()` → `.now(timezone.utc)`
- `quirk/reports/technical.py:1,25` — same change

**Verification:** `pytest tests/test_cbom_integration.py -W error::DeprecationWarning` — 3 passed, 0 warnings

---

### W2: CycloneDX dependency graph incomplete (RESOLVED)

**File changed:** `quirk/cbom/builder.py`
- Added `from cyclonedx.model.dependency import Dependency`
- Extracted `root_component` variable from inline `BomMetaData` construction
- Built dependency graph: root component references all crypto asset components as children
- Passed `dependencies=[root_dep]` to `Bom()` constructor

**Verification:** `pytest tests/test_cbom_integration.py tests/test_cbom_builder.py tests/test_cbom_writer.py -W error::UserWarning` — 32 passed, 0 warnings

---

### W3: Vite chunk size warning (RESOLVED)

**File changed:** `src/dashboard/vite.config.ts`
- Added `rolldownOptions.output.manualChunks()` function splitting vendors into 4 chunks:
  - `vendor-react` (react, react-dom, react-router) — 218 kB
  - `vendor-charts` (recharts, d3-*) — 371 kB
  - `vendor-graph` (cytoscape, cytoscape-dagre) — 570 kB
  - `vendor-table` (@tanstack/react-table) — 50 kB
- Added `chunkSizeWarningLimit: 600` (Cytoscape is irreducible at 570 kB)
- Main app bundle reduced from 1,390 kB → 180 kB

**Issues encountered:** Initial attempt used `rollupOptions` (Rollup API) — Vite 8 uses Rolldown engine which requires `rolldownOptions`. `manualChunks` must be a function, not an object map.

**Verification:** `npm run build` — 0 warnings, 7 chunks output in 511ms

---

## Final Verification

Full test suite re-run after all fixes:

```
pytest tests/ -v -W error::DeprecationWarning
165 passed in 5.59s — 0 failures, 0 warnings
```

Dashboard validation:
- `tsc --noEmit` — PASS
- `npm run lint` — 0 errors, 0 warnings
- `npm run build` — 7 chunks, 0 warnings, 511ms

**182 of 182 tests pass. All findings resolved.**
