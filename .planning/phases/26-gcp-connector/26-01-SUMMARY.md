---
phase: 26-gcp-connector
plan: 01
subsystem: infra
tags: [gcp, cloud-connector, pyproject, config, orm, sqlite, migration, testing]

# Dependency graph
requires:
  - phase: 17-identity-infrastructure
    provides: _ensure_identity_columns pattern and [identity] extras group that _ensure_gcp_columns mirrors exactly

provides:
  - "[cloud] extras group in pyproject.toml with google-api-python-client and google-auth"
  - "ConnectorsCfg.enable_gcp and ConnectorsCfg.gcp_project_id fields with safe defaults"
  - "GCP connector block (commented) in config_template.yaml"
  - "CryptoEndpoint.gcs_scan_json ORM column for Phase 28 data hand-off"
  - "_GCP_COLUMNS list and _ensure_gcp_columns() idempotent migration in quirk/db.py"
  - "Wave 0 GCP test scaffold: 10 test functions in test_cloud_connectors.py"

affects:
  - 26-02-gcp-connector-impl
  - 26-03-gcp-connector-wiring
  - 28-object-storage

# Tech tracking
tech-stack:
  added:
    - "google-api-python-client>=2.0.0 (in [cloud] optional extras)"
    - "google-auth>=2.36.0 (in [cloud] optional extras)"
  patterns:
    - "_GCP_COLUMNS + _ensure_gcp_columns() mirrors _IDENTITY_COLUMNS + _ensure_identity_columns() exactly"
    - "Conditional import with _HAS_GCP_MODULE flag for test scaffold before module exists"
    - "_build_gcp_mock_service() helper pattern for Discovery API chainable mock setup"

key-files:
  created:
    - none
  modified:
    - pyproject.toml
    - quirk/config.py
    - quirk/config_template.yaml
    - quirk/models.py
    - quirk/db.py
    - tests/test_cloud_connectors.py

key-decisions:
  - "google-api-python-client and google-auth placed in new [cloud] extras group (not core deps) per D-01"
  - "enable_gcp and gcp_project_id appended at end of ConnectorsCfg body with safe defaults per D-06"
  - "gcs_scan_json added as v4.3 section after v4.2 identity fields in models.py and db.py per D-03"
  - "Test scaffold uses _HAS_GCP_MODULE conditional import so file does not break before Plan 02"
  - "test_gcp_ensure_columns_idempotent runs immediately (tests quirk.db only); remaining 9 GCP tests skip until Plan 02"

patterns-established:
  - "GCP extras group placement: immediately after [identity] in pyproject.toml optional-dependencies"
  - "GCP column migration guard: inspector-first idempotent ALTER TABLE pattern matching _ensure_identity_columns"
  - "Wave 0 test scaffold: _build_gcp_mock_service() sets all list_next() to None for pagination termination"

requirements-completed:
  - GCP-01
  - GCP-02
  - GCP-03

# Metrics
duration: 3min
completed: 2026-04-25
---

# Phase 26 Plan 01: GCP Connector Infrastructure Summary

**[cloud] extras group, ConnectorsCfg GCP fields, gcs_scan_json ORM column, _ensure_gcp_columns() migration guard, and 10-function Wave 0 test scaffold — all GCP prerequisites in place for Plan 02**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-25T00:30:53Z
- **Completed:** 2026-04-25T00:33:07Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `[cloud]` optional extras group to pyproject.toml with `google-api-python-client>=2.0.0` and `google-auth>=2.36.0` (no grpcio, no google-cloud-kms per D-01)
- Extended `ConnectorsCfg` with `enable_gcp: bool = False` and `gcp_project_id: Optional[str] = None`; added GCP block to config_template.yaml
- Added `gcs_scan_json` ORM column to `CryptoEndpoint` plus matching `_GCP_COLUMNS` / `_ensure_gcp_columns()` idempotent migration in `init_db()`
- Created Wave 0 GCP test scaffold in `test_cloud_connectors.py`: 10 test functions covering GCP-01 (KMS mapping, unavailable, credentials error), GCP-02 (all 4 sslMode cases), GCP-03 (CMEK detection, gcs_scan_json hand-off), and DB migration idempotency
- `test_gcp_ensure_columns_idempotent` PASSES immediately; 9 connector tests correctly SKIP pending Plan 02

## Task Commits

1. **Task 1: Infrastructure -- pyproject.toml, config.py, config_template.yaml, models.py, db.py** - `8308be7` (feat)
2. **Task 2: Wave 0 test scaffold -- GCP tests in test_cloud_connectors.py** - `7346049` (test)

## Files Created/Modified

- `pyproject.toml` - Added `[cloud]` extras group after `[identity]` with google-api-python-client and google-auth
- `quirk/config.py` - Added `enable_gcp: bool = False` and `gcp_project_id: Optional[str] = None` to ConnectorsCfg
- `quirk/config_template.yaml` - Added commented GCP connector block after identity block
- `quirk/models.py` - Added v4.3 GCP section with `gcs_scan_json = Column(Text, nullable=True)`
- `quirk/db.py` - Added `_GCP_COLUMNS`, `_ensure_gcp_columns()`, and call in `init_db()` after `_ensure_identity_columns()`
- `tests/test_cloud_connectors.py` - Updated docstring, added conditional GCP import, added 10 GCP test functions + `_build_gcp_mock_service()` helper

## Decisions Made

- `google-api-python-client` and `google-auth` in `[cloud]` extras only — no core dependency change, keeps lightweight base install
- `gcs_scan_json` column mirrors the `_IDENTITY_COLUMNS` / `_ensure_identity_columns()` pattern exactly — consistent migration guard approach across all version bands
- Test scaffold uses `_HAS_GCP_MODULE` conditional import and `@pytest.mark.skipif` — file does not fail import before Plan 02 creates `gcp_connector.py`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all infrastructure changes compiled clean and verification tests passed on first attempt.

## Known Stubs

None — no stub values or placeholder data introduced. All new fields have proper safe defaults (`False`, `None`). The `gcs_scan_json` column is intentionally `nullable=True` until Plan 02 writes data.

## Threat Flags

No new threat surface introduced beyond what the plan's threat model already documents (T-26-01, T-26-02).

## Next Phase Readiness

- Plan 02 (`gcp_connector.py` implementation) can proceed immediately — all infrastructure prerequisites are in place
- 9 skipped GCP tests will go GREEN when Plan 02 creates `quirk/scanner/gcp_connector.py`
- Plan 03 (integration wiring in `run_scan.py` and `builder.py`) depends on Plan 02's connector being complete

---
*Phase: 26-gcp-connector*
*Completed: 2026-04-25*
