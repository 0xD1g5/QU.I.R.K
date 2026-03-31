---
phase: 05-web-dashboard
plan: 04
subsystem: ui
tags: [fastapi, react, sqlite, sqlalchemy, tanstack-table, recharts, shadcn-ui, quantum-readiness]

requires:
  - phase: 05-02
    provides: FastAPI app factory, schemas, health route pattern
  - phase: 05-03
    provides: PDF export route (POST /api/export/pdf) used by ExecutivePage button
  - phase: 05-06
    provides: useScanData hook (already implemented, kept as-is)

provides:
  - GET /api/scan/latest endpoint returning ScanLatestResponse with score, findings, certificates, cbom_components, roadmap
  - _derive_findings: synthesizes findings from CryptoEndpoint rows (HTTP, legacy TLS, weak ciphers, expired certs, weak RSA, quantum-vulnerable algorithms)
  - _derive_cbom: aggregates algorithm usage across endpoints into CbomComponent list
  - _derive_roadmap: calls build_phased_roadmap() and maps to RoadmapData graph nodes/edges
  - ScoreGauge: SVG arc gauge component with score-based color coding (green/amber/red) and overall variant
  - ExecutivePage: 5 arc gauges, confidence badge, vertical severity bar chart, PDF export button, scan metadata row
  - FindingsPage: TanStack Table v8 with severity filter, global search, Sheet slide-out detail panel
  - CertificatesPage: certificate inventory table with expiry color coding and quantum-safety badges
  - App.tsx routes wired: /, /findings, /certificates now render real pages

affects: [05-05, 05-07, reporting]

tech-stack:
  added: []
  patterns:
    - "Route-level DI override in conftest.py using shared-cache SQLite URI for cross-thread test access"
    - "Findings synthesized from CryptoEndpoint rows at query time — no separate findings table"
    - "CBOM aggregated by algorithm key from endpoint scan columns at API layer"
    - "ScoreGauge uses SVG polar coordinate math for semicircular arc fill"

key-files:
  created:
    - quirk/dashboard/api/routes/scan.py
    - src/dashboard/src/components/gauges/ScoreGauge.tsx
    - src/dashboard/src/pages/executive.tsx
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/certificates.tsx
  modified:
    - quirk/dashboard/api/app.py
    - tests/test_dashboard_api.py
    - tests/conftest.py
    - src/dashboard/src/App.tsx

key-decisions:
  - "conftest.py uses sqlite:///file::memory:?cache=shared&uri=true so the in-memory DB is accessible from FastAPI's sync route worker thread — plain sqlite:///:memory: creates a separate DB per connection"
  - "Findings derived at API layer from CryptoEndpoint columns — no separate findings table needed for v1"
  - "CBOM components aggregated by algorithm string across all endpoints at query time"

patterns-established:
  - "FastAPI dependency override requires shared-cache SQLite for sync route handlers in test environments"
  - "All three primary views (Executive, Findings, Certificates) share a single useScanData() call and split data from the response"

requirements-completed: [UI-02, UI-03]

duration: 6min
completed: 2026-03-31
---

# Phase 05 Plan 04: Scan API Endpoint and Primary Data Views Summary

**GET /api/scan/latest endpoint wired to SQLite intelligence functions, with Executive (5 arc gauges + severity chart), Findings (TanStack Table + Sheet), and Certificate Inventory (expiry color-coded + quantum-safety badges) pages**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-31T11:23:41Z
- **Completed:** 2026-03-31T11:29:17Z
- **Tasks:** 3 (Task 1, Task 2a, Task 2b)
- **Files modified:** 8

## Accomplishments

- Implemented `GET /api/scan/latest` connecting intelligence functions (scoring, confidence, evidence, roadmap) and CBOM classifier to live SQLite data
- Built ScoreGauge SVG arc component and ExecutivePage with 5 gauges (overall + 4 subscores), recharts severity breakdown, and wired PDF export button
- Built FindingsPage (TanStack Table v8 with severity filter, global search, Sheet slide-out) and CertificatesPage (expiry color-coding, quantum-safety badges sorted by expiry)
- All 7 dashboard API tests pass (none skipped); `npm run build` exits 0 producing 796 KB bundle

## Task Commits

Each task was committed atomically:

1. **Task 1: GET /api/scan/latest endpoint** - `c8233c6` (feat)
2. **Task 2a: ScoreGauge + ExecutivePage** - `822423f` (feat)
3. **Task 2b: FindingsPage + CertificatesPage + App.tsx routing** - `91dbce0` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `quirk/dashboard/api/routes/scan.py` — GET /api/scan/latest: _derive_findings, _derive_cbom, _derive_roadmap, get_latest_scan
- `quirk/dashboard/api/app.py` — registered scan.router with /api prefix
- `tests/test_dashboard_api.py` — replaced 4 pytest.skip stubs with real assertions
- `tests/conftest.py` — fixed DB fixture: shared-cache SQLite URI + dependency override
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — SVG arc gauge, polar coordinate fill, score-based color
- `src/dashboard/src/pages/executive.tsx` — 5 arc gauges, recharts vertical bar chart, PDF export
- `src/dashboard/src/pages/findings.tsx` — TanStack Table, severity filter, global search, Sheet detail panel
- `src/dashboard/src/pages/certificates.tsx` — certificate table, expiry color coding, quantum-safety badges
- `src/dashboard/src/App.tsx` — wired /, /findings, /certificates to real page components

## Decisions Made

- Shared-cache SQLite URI (`file::memory:?cache=shared&uri=true`) required for FastAPI TestClient because sync route handlers run in a thread pool — plain `:memory:` creates a separate per-connection DB invisible to the session passed via DI override
- Findings derived at API layer: no separate findings table needed; all finding logic is in `_derive_findings()` from CryptoEndpoint columns

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed conftest.py to use shared-cache SQLite for dependency override**

- **Found during:** Task 1 (test verification)
- **Issue:** conftest.py created a plain in-memory SQLite DB but FastAPI's sync route handlers run in anyio thread pool — the test DB was invisible to the route via the DI override, causing `no such table: crypto_endpoints` failures
- **Fix:** Changed SQLite URI to `file::memory:?cache=shared&uri=true` with `connect_args={"check_same_thread": False}` and updated conftest to call `create_app()` instead of importing the module-level `app` singleton so dependency override applies cleanly
- **Files modified:** tests/conftest.py
- **Verification:** All 7 dashboard API tests pass
- **Committed in:** c8233c6 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical test infrastructure)
**Impact on plan:** Required for test correctness. No scope creep.

## Issues Encountered

- SQLite in-memory DB thread isolation: shared-cache URI pattern is the standard solution for SQLAlchemy + FastAPI TestClient with sync route handlers. Documented as a decision for future test infrastructure.

## Known Stubs

None — all three pages are fully wired to live API data via `useScanData()`.

## Next Phase Readiness

- `/` (Executive), `/findings`, `/certificates` are fully functional
- `/cbom` and `/roadmap` remain as Placeholder components — implemented in 05-05
- PDF export button on Executive page is wired; POST /api/export/pdf endpoint exists from 05-06 (Wave 2)
- 148 tests passing across full suite

---
*Phase: 05-web-dashboard*
*Completed: 2026-03-31*
