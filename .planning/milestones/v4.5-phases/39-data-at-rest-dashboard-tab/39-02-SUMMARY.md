---
phase: 39-data-at-rest-dashboard-tab
plan: "02"
subsystem: api
tags: [fastapi, pydantic, typescript, dar, data-at-rest, dashboard, projection]

# Dependency graph
requires:
  - phase: 39-01
    provides: Wave 0 test scaffold (tests/test_dar_dashboard.py with 8 RED tests)

provides:
  - DarFinding Pydantic model with category discriminator and 12 DAR-specific optional fields
  - dar_findings field on ScanLatestResponse (default empty list)
  - _derive_dar_findings() projection function with per-protocol dispatch for 7 protocols
  - TypeScript DarFinding interface mirror in src/dashboard/src/types/api.ts
  - All 8 Wave 0 tests GREEN

affects:
  - 39-03 (frontend data-at-rest.tsx imports DarFinding from types/api)
  - 39-04 (same)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-protocol dispatch table (DAR_PROTOCOLS set) in _derive_dar_findings() — mirrors _derive_motion_findings pattern"
    - "json.loads(dat_scan_json) wrapped in try/except with {} fallback (V5 input validation pattern)"
    - "scan_error guard at top of projection loop — skips failed endpoints"
    - "Pydantic DarFinding superset model: universal baseline fields + category discriminator + protocol-specific optional fields"

key-files:
  created:
    - tests/test_dar_dashboard.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/scan.py
    - src/dashboard/src/types/api.ts

key-decisions:
  - "DarFinding uses category discriminator string ('database'|'object_storage'|'kubernetes'|'vault') per D-02"
  - "S3/Azure/K8s/Vault helpers receive parsed dat dict, not service_detail from endpoint — these protocols store context entirely in dat_scan_json"
  - "_dar_db() and _dar_rds() parse ep.service_detail string only — db_connector.py does not write dat_scan_json"
  - "seal_type and auto_unseal always None for Vault findings — vault_connector.py does not probe sys/seal-status (Pitfall 4)"
  - "public_access and versioning always None for S3 — aws_connector S3 scanner does not probe ACLs or versioning (Pitfall 6)"

patterns-established:
  - "Per-protocol dispatch: DAR_PROTOCOLS set + if/elif chain in _derive_dar_findings()"
  - "Helper functions (_dar_db, _dar_rds, _dar_s3, _dar_azure_blob, _dar_k8s, _dar_vault) extract protocol logic cleanly"

requirements-completed: [GAP-04]

# Metrics
duration: 12min
completed: 2026-04-29
---

# Phase 39 Plan 02: DAR Schema + Projection Summary

**Typed DarFinding Pydantic model + _derive_dar_findings() projection with 7-protocol dispatch, wired into ScanLatestResponse — all 8 Wave 0 tests GREEN**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 2 (+ TDD RED scaffold)
- **Files modified:** 4

## Accomplishments

- DarFinding Pydantic model with 9 universal baseline fields + required `category` discriminator + 12 DAR-specific optional fields
- ScanLatestResponse.dar_findings: List[DarFinding] = [] field (default empty, never absent)
- _derive_dar_findings() projection with POSTGRESQL/MYSQL/RDS/S3/AZURE_BLOB/KUBERNETES/VAULT dispatch
- TypeScript DarFinding interface mirror in src/dashboard/src/types/api.ts + dar_findings on ScanLatestResponse
- All 8 Wave 0 tests GREEN; full test suite 669 passed with no regressions

## Task Commits

1. **TDD RED: Failing test scaffold** - `bfde641` (test)
2. **Task 1: DarFinding schema + TS mirror** - `2168cee` (feat)
3. **Task 2: _derive_dar_findings() implementation** - `c47e257` (feat)

## Files Created/Modified

- `tests/test_dar_dashboard.py` - 8 unit + integration tests for DAR projection and API contract (TDD RED scaffold)
- `quirk/dashboard/api/schemas.py` - DarFinding Pydantic model class; dar_findings field on ScanLatestResponse
- `quirk/dashboard/api/routes/scan.py` - DAR_PROTOCOLS set; _derive_dar_findings(); 6 protocol helpers; DarFinding import; wired into return statement
- `src/dashboard/src/types/api.ts` - DarFinding TypeScript interface; dar_findings: DarFinding[] on ScanLatestResponse

## Decisions Made

- Test scaffold (Wave 0 test file) created inline as part of TDD RED phase since plan 01 was a parallel wave that had not yet committed to this worktree. Functionally identical result.
- S3/Azure/K8s/Vault helper functions do NOT receive `service_detail` from the endpoint — they receive the parsed `dat` dict only, since these protocols store all context in `dat_scan_json`.
- `_dar_k8s()` discriminates shapes by `"namespace" in dat` (secret enumeration) vs provider field (cluster encryption). This is the safest discriminator per RESEARCH.md Pitfall 2.

## Deviations from Plan

None — plan executed exactly as specified. The test file creation was handled inline (TDD RED step) rather than as a dependency on plan 01 output, which is structurally equivalent.

## Issues Encountered

Pre-existing test failure: `tests/test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` fails because `importlib.metadata.version('quirk')` returns `'4.0.0'` instead of `'4.4.0'` — this is a packaging environment issue unrelated to plan 02 changes. Confirmed pre-existing by stash test. 669 tests pass excluding this known failure.

## Threat Model Compliance

- **T-39-01 (V5 input validation):** Every `json.loads(dat_scan_json)` call wrapped in `try/except Exception: dat = {}`. One malformed row cannot abort projection of all others.
- **T-39-02 (info disclosure):** kms_key_id carries only human-readable labels ("AWS-managed"/"CMK") derived from service_detail — no KMS ARN is stored by the scanner.
- **T-39-03 (DoS):** getattr guards on every field access; scan_error skipped early; severity sort O(n log n); no recursion or external I/O.

## Known Stubs

None — all fields are properly derived from scanner output. Fields that are structurally absent in current scanner output (public_access, versioning, seal_type, auto_unseal) are documented in RESEARCH.md and render as null (UI shows —).

## Next Phase Readiness

- Frontend (Plan 03) can now `import { DarFinding } from "@/types/api"` and consume `data?.dar_findings`
- `data?.score.subscores.data_at_rest` is already in SubScores (pre-existing from Phase 27)
- No backend changes needed for Plans 03/04

## Self-Check: PASSED

---
*Phase: 39-data-at-rest-dashboard-tab*
*Completed: 2026-04-29*
