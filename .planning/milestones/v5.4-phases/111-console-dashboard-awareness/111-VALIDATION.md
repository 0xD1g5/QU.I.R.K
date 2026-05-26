---
phase: 111
slug: console-dashboard-awareness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 111 — Validation Strategy

> Per-phase validation contract. Backend = pytest/TestClient; frontend = vitest + a mandatory
> `npm run build` (FastAPI serves pre-built statics — .tsx changes are invisible until rebuilt).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 7.x (FastAPI TestClient) |
| **Frontend framework** | vitest (src/dashboard/) |
| **Quick run command** | `pytest tests/ -k "registry or merge_latest or segment_filter" -q` |
| **Frontend build** | `cd src/dashboard && npm run build` (REQUIRED before statics reflect .tsx edits) |
| **Full suite command** | `pytest tests/ -q && python -m compileall quirk run_scan.py && (cd src/dashboard && npm run build && npx vitest run)` |
| **Estimated runtime** | ~90 seconds (build dominates) |

---

## Sampling Rate

- **After every backend task commit:** quick pytest command
- **After every frontend task commit:** `npm run build` + targeted vitest
- **After every plan wave:** full suite
- **Before `/gsd:verify-work`:** full suite green + a real built artifact opened (visual fidelity is human-UAT gated, not asserted by presence tests)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Requirement | Correct Behavior | Test Type | Automated Command | Status |
|-------------|------------------|-----------|-------------------|--------|
| DASH-01 | GET /api/sensor/registry returns enrolled sensors + green/stale/unknown status; Sensors page renders the table | backend + component | `pytest -k registry` ; `vitest run sensors` | ⬜ pending |
| DASH-02 | ?segment= filter on /scan/latest,/findings,/cbom (post-load, NULL-safe); nullable sensor_id/segment in schemas + types/api.ts; shared dropdown | backend + component | `pytest -k segment_filter` ; `vitest run filter` | ⬜ pending |
| DASH-03 | GET /api/merge/latest reads merge_runs + recomputes per_segment (Option A); coverage_warning banner when non-null; per-segment ScoreGauges; graceful no-merge | backend + component | `pytest -k "merge_latest or coverage"` ; `vitest run gauges` | ⬜ pending |
| (backward-compat) | single-host NULL-segment scans render unchanged; existing findings/cbom presence tests stay green | regression | `pytest tests/ -k "findings or cbom" -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No new pip or npm dependencies (reuse shadcn primitives, ScoreGauge, existing engines)
- [ ] Reuse `QUIRK_DB_PATH` conftest fixture + TestClient/auth fixtures for backend route tests
- [ ] Frontend component tests follow the existing `src/dashboard/src/**/__tests__` pattern
- [ ] `npm run build` must succeed (TypeScript types in `types/api.ts` mirror the new schema fields)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual fidelity of registry table, badges, gauges, coverage banner | DASH-01/03 | Presence tests assert fields/columns, NOT appearance (project rule) | Run `npm run build`, open the dashboard, visually confirm against 111-UI-SPEC.md; human UAT |
| Live multi-sensor coverage banner | DASH-03 | Needs a real merge with a missing sensor | Deferred to Phase 112 chaos-lab E2E |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags (vitest run, not vitest watch)
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
