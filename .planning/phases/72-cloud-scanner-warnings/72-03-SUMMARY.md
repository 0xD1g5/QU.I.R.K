---
phase: 72-cloud-scanner-warnings
plan: 03
subsystem: scanners-cloud
tags: [gcp, kms, cloud-sql, pagination, audit-closure]
requires: []
provides:
  - MAX_KMS_PAGES module constant (per-loop runaway-scan cap)
  - _GCP_KMS_SKIP_ALGORITHMS frozenset (raw-algorithm skip semantics)
  - Cloud SQL instance description routed via service_detail slash-suffix
affects: [quirk/scanner/gcp_connector.py]
tech_stack:
  added: []
  patterns: [PROTO-05-D-01-fail-loud-bound, Phase-69-BLOCK-02-service_detail-routing]
key_files:
  created:
    - tests/test_gcp_connector.py
  modified:
    - quirk/scanner/gcp_connector.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions: [D-01, D-01a, D-16, D-17, D-25]
metrics:
  duration_min: ~25
  tasks_completed: 3
  tests_added: 6
  audit_rows_closed: 3
completed: 2026-05-15
---

# Phase 72 Plan 03: GCP Connector Correctness (CLOUD-03) Summary

GCP connector now bounded against runaway KMS pagination (`MAX_KMS_PAGES = 1000` per loop), treats `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` and `UNKNOWN` algorithm strings identically via an explicit pre-map skip set with INFO logging, and surfaces the Cloud SQL instance `description` through `service_detail` so report renderers can reach it.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | MAX_KMS_PAGES cap + per-loop counters + _GCP_KMS_SKIP_ALGORITHMS skip + INFO log | `cce4e7b` |
| 2 | Cloud SQL service_detail verification (verification-only path attempted; corrective path actually required — see "Deviations" below) | (folded into Task 3 GREEN commit) |
| 3 | Tests (RED) — `tests/test_gcp_connector.py` with 6 tests | `ecae0a7` |
| 3 | Cloud SQL service_detail slash-suffix encoding fix (GREEN for WR-22) | `2f6921e` |
| 3 | Audit rows WR-04 / WR-05 / WR-22 flipped to `Phase 72 \| [x] closed` | rolled into `8a13153` (concurrent Plan 72-01 docs commit) |

## What Was Built

### WR-04 — GCP KMS pagination cap (D-01 / D-01a)

`quirk/scanner/gcp_connector.py` now defines:

```python
MAX_KMS_PAGES = 1000  # per-loop cap; ~1M items at default page size
```

Each of the three pagination loops in `_scan_kms` (locations → key-rings → crypto-keys) maintains its own `page_count` counter (D-01a default: per-loop). When `page_count > MAX_KMS_PAGES`, the loop raises:

```python
raise ValueError(
    f"GCP KMS pagination exceeded {MAX_KMS_PAGES} pages for "
    f"{<resource_identifier>}; aborting to prevent runaway scan"
)
```

`<resource_identifier>` is the in-scope resource (`project_resource` / `location_name` / `key_ring_name`) so the error message identifies which loop tripped. Mirrors PROTO-05 / WR-14 D-01 fail-loud pattern.

### WR-05 — UNSPECIFIED + UNKNOWN raw-algorithm skip (D-16)

Module-scope:

```python
_GCP_KMS_SKIP_ALGORITHMS = frozenset({
    "CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED",
    "UNKNOWN",
})
```

Inside `_scan_kms`, BEFORE the `GCP_KMS_ALGORITHM_MAP.get(...)` lookup:

```python
if algorithm in _GCP_KMS_SKIP_ALGORITHMS:
    if logger:
        logger.info("GCP key %s skipped (algorithm=%s)", key_name, algorithm)
    continue
```

The pre-existing post-map `alg_name == "UNKNOWN"` branch was retained per D-25 (do-not-touch — other algorithms may legitimately map to "UNKNOWN" via the default tuple, and pruning that branch would be incidental cleanup).

### WR-22 — Cloud SQL instance description in service_detail (D-17 / C-3 adjudication)

`_scan_cloud_sql` now reads `instance.get("description")` and encodes it into `service_detail` via slash-suffix:

```python
instance_description = instance.get("description") or "no-description"
instance_desc_slug = instance_description.replace(" ", "-")
# ...
service_detail = (
    f"CLOUD_SQL/{description.replace(' ', '-')}"
    f"/{instance_desc_slug}"
)
```

The encoding matches Phase 69 BLOCK-02's `service_detail` routing pattern. No schema change — the existing single `service_detail` column carries both the finding-description and the instance-description, separated by `/`.

## Deviations from Plan

### [Rule 1 — Task 2 verification ambiguity resolved to corrective path]

**Found during:** Task 3 RED phase, while writing `test_cloud_sql_service_detail_contains_description`.

**Issue:** Plan Task 2 / RESEARCH C-3 anticipated that `_scan_cloud_sql` already surfaced the description in `service_detail` via the slash-suffix at line 268 (`service_detail=f"CLOUD_SQL/{description.replace(' ', '-')}"`). The RED test asserted that an instance with `description="Production primary DB"` would produce a `service_detail` containing `"Production-primary-DB"`.

**Actual finding:** The `description` local variable in that line refers to the **finding description** (from `SSL_FINDING_MAP`, e.g. "plaintext connections allowed"), NOT the Cloud SQL instance's `description` field. The instance description was carried only in `cloud_scan_json`. The RED test correctly failed — the audit row's strict reading was correct.

**Fix (per Plan Task 2 step 3, corrective path):** Extended the `service_detail` slash-suffix to include both pieces of information: `CLOUD_SQL/<finding-desc-slug>/<instance-desc-slug>`. Falls back to `"no-description"` when the instance has no description. No schema change.

**Files modified:** `quirk/scanner/gcp_connector.py` (one block in `_scan_cloud_sql`)

**Commit:** `2f6921e`

## Audit Ledger

- `scanners-cloud/WR-04` → `Phase 72 | [x] closed` (line 94, evidence cites commit `cce4e7b`)
- `scanners-cloud/WR-05` → `Phase 72 | [x] closed` (line 95, evidence cites commit `cce4e7b`)
- `scanners-cloud/WR-22` → `Phase 72 | [x] closed` (line 112, evidence cites commits `2f6921e` and `cce4e7b`)

Note: due to concurrent Wave-1 execution, the audit-row flips were durably committed under sibling Plan 72-01's docs commit (`8a13153`) rather than a separate 72-03 docs commit. The flips are present in HEAD and contain full per-row evidence; the only consequence is a different commit boundary than the plan-prescribed "three rows, single docs commit". No content lost.

## Tests

`tests/test_gcp_connector.py` — 6 tests, all passing:

| Test | Covers |
|------|--------|
| `test_kms_pagination_cap_raises_after_1000_pages` | WR-04 / D-01 (parametrized at MAX_KMS_PAGES+1) |
| `test_kms_pagination_under_cap_completes` | WR-04 negative case (no false-positive at 5 pages) |
| `test_kms_skips_unspecified_and_unknown_algorithms[CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED]` | WR-05 / D-16 (skip + INFO log) |
| `test_kms_skips_unspecified_and_unknown_algorithms[UNKNOWN]` | WR-05 / D-16 (skip + INFO log) |
| `test_kms_emits_for_real_algorithm` | WR-05 negative-of-skip (`GOOGLE_SYMMETRIC_ENCRYPTION` produces finding) |
| `test_cloud_sql_service_detail_contains_description` | WR-22 / D-17 (instance description routes through service_detail) |

Pytest output: `6 passed in 0.29s`. No regressions in sibling cloud-SQL / GCP tests (`pytest -k "gcp or cloud_sql"` → 22 passed).

## Verification

- `python -m compileall quirk/scanner/gcp_connector.py` exits 0
- `pytest tests/test_gcp_connector.py -x` → 6 passed
- `grep -cE "scanners-cloud/WR-(04|05|22).*Phase 72.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → 3
- D-25 compliance: only `_scan_kms`, `_scan_cloud_sql`, and module-scope constants edited; no incidental cleanup elsewhere in the file

## Self-Check: PASSED

- `quirk/scanner/gcp_connector.py` — FOUND
- `tests/test_gcp_connector.py` — FOUND
- Commits `cce4e7b`, `ecae0a7`, `2f6921e` — all FOUND in `git log --oneline --all`
- Audit rows WR-04 / WR-05 / WR-22 flipped — VERIFIED (3 matches)
