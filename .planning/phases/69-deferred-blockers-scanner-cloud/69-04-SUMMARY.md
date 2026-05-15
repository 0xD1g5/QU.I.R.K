---
phase: 69
plan: 04
subsystem: scanner-cloud
tags: [block-04, cr-10, azure, blob, finding-id]
requires: []
provides: [BLOB-PLATFORM, BLOB-UNKNOWN, BLOB-CMK]
affects: [quirk/scanner/azure_connector.py, quirk/intelligence/evidence.py]
tech_stack:
  added: []
  patterns: [three-way-branch-on-key-source, finding_id-in-dat_scan_json]
key_files:
  created: []
  modified:
    - quirk/scanner/azure_connector.py
    - quirk/intelligence/evidence.py
    - tests/test_azure_blob.py
decisions:
  - "D-04 honored: same MEDIUM severity tier, distinct finding_id + description, no new schema column"
  - "Extended evidence.py scoring (Rule 2) so BLOB/unknown counts in dar_storage_aws_managed_count alongside BLOB/platform-managed, preserving MEDIUM-tier scoring impact"
metrics:
  duration_minutes: 7
  completed: 2026-05-14
  tasks: 1
  files_changed: 3
requirements: [BLOCK-04]
---

# Phase 69 Plan 04: Azure Blob Three-Way Key Source Branch Summary

Differentiate Azure Blob encryption findings between known platform-managed
(`microsoft.storage` → `BLOB-PLATFORM`) and unknown/absent key source
(`BLOB-UNKNOWN`) so downstream CBOM intelligence can tell "we know it's
platform-managed" apart from "we couldn't determine the key source".

## What Was Built

`_scan_blob_encryption` now branches three ways on the lowercased
`encryption.key_source`:

| key_source              | service_detail          | finding_id     | severity |
| ----------------------- | ----------------------- | -------------- | -------- |
| `microsoft.keyvault`    | `BLOB/cmk`              | `BLOB-CMK`     | None     |
| `microsoft.storage`     | `BLOB/platform-managed` | `BLOB-PLATFORM`| MEDIUM   |
| absent / null / ""      | `BLOB/unknown`          | `BLOB-UNKNOWN` | MEDIUM   |

`finding_id` and `description` are encoded into the existing
`dat_scan_json` payload alongside `key_source` (raw value or `"absent"`).
No CryptoEndpoint schema column was added.

## Verification

- `pytest tests/test_azure_blob.py -x -q` → 10 passed
- `pytest tests/test_dar_storage_scoring.py -x -q` → 9 passed (regression
  guard — `BLOB/platform-managed` substring unchanged)
- `python -m compileall quirk/scanner/azure_connector.py` → exit 0
- `grep -n 'finding_id=' quirk/scanner/azure_connector.py` → no
  CryptoEndpoint kwarg (Pitfall 6 honored; finding_id lives only in the
  JSON payload)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] Extend scoring to count BLOB/unknown**
- **Found during:** Task 1 acceptance review
- **Issue:** `quirk/intelligence/evidence.py:204` used substring match
  `"BLOB/platform-managed" in sd` to drive `dar_storage_aws_managed_count`.
  After splitting off `BLOB/unknown` it would no longer match, so a new
  MEDIUM-tier finding would silently bypass scoring — masking the severity
  D-04 explicitly preserves.
- **Fix:** Broadened the predicate to
  `"BLOB/platform-managed" in sd or "BLOB/unknown" in sd`. Both MEDIUM
  postures now count identically toward the same scoring bucket.
- **Files modified:** `quirk/intelligence/evidence.py`
- **Commit:** `9787c9f`

### Test Rename

- `test_azure_blob_absent_key_source_medium` (asserted the old conflated
  behavior) was removed and superseded by
  `test_azure_blob_absent_key_source_unknown`. No other test fixtures or
  downstream consumers keyed on the old implicit finding_id, confirmed via
  grep of `BLOB/platform-managed|BLOB/cmk|BLOB/unknown` across the repo.

## Known Stubs

None.

## Commits

| Commit  | Type | Description                                                     |
| ------- | ---- | --------------------------------------------------------------- |
| 26b8664 | test | RED — BLOB-PLATFORM/BLOB-UNKNOWN finding_id semantics           |
| 9787c9f | fix  | GREEN — three-way Azure Blob key_source branch (BLOCK-04)       |

## Self-Check: PASSED

- FOUND: `quirk/scanner/azure_connector.py` (modified)
- FOUND: `quirk/intelligence/evidence.py` (modified)
- FOUND: `tests/test_azure_blob.py` (modified)
- FOUND commit: `26b8664`
- FOUND commit: `9787c9f`
