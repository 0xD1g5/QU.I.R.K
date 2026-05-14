---
phase: 67-resumable-partial-failure-scans
plan: "03"
subsystem: scan-orchestration
tags: [resumable-scans, _wrapped_phase, partial-failures, run_scan, refactor]
one_liner: "All scanner invocations migrated to _wrapped_phase — uniform BaseException capture for every scanner stage, enabling consistent partial_failures entries on crash"
requires:
  - run_scan._wrapped_phase  # from phase 41
  - run_scan._flush_stage_endpoints  # from plan 02
  - run_scan._collect_stage_partial_failures  # from plan 02
provides:
  - uniform _wrapped_phase coverage for all scanner invocations in run_scan.py
affects:
  - run_scan.py
tech_stack:
  added: []
  patterns:
    - nested def + _wrapped_phase() pattern replacing inline with _phase_timer blocks
    - import-inside-lambda pattern for optional-extra gated scanners (S3/blob/k8s/vault/saml/kerberos)
key_files:
  created: []
  modified:
    - run_scan.py
decisions:
  - "GCS storage reuse (STOR-03) kept as inline with _phase_timer — it is a pure in-memory transform with zero external I/O and no crash risk; wrapping would add noise without benefit"
  - "K8S inner EKS try/except preserved inside _run_k8s_phase — the inner try/except is an optional bolt-on extension, not a full scanner crash path"
  - "Email _emit_missing_extra_advisory call kept before _run_email_phase def — correct ordering: advisory fires on missing-extra detection regardless of whether the phase runs"
metrics:
  duration: "~10 min"
  completed: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 67 Plan 03: Scanner _wrapped_phase Migration Summary

All scanner invocations in run_scan.py that previously used inline `with _phase_timer` blocks (or, for email, an inline `try/except BaseException`) are migrated to the `_wrapped_phase()` pattern. This ensures every scanner crash produces a consistent `error_endpoints` row with `scan_error_category="exception"`, which feeds the `partial_failures` accumulator wired in Plan 02.

## What Was Built

### Task 1: API stage scanners (JWT, container, source)

Three inline `with _phase_timer` blocks in the `api` stage replaced with nested-def + `_wrapped_phase` calls:

| Scanner | Old pattern | New function | Label |
|---------|-------------|--------------|-------|
| JWT | `jwt_endpoints = []; with _phase_timer(run_stats, "jwt_scanning"):` | `_run_jwt_phase()` | `jwt_scanner` |
| Container | `container_endpoints = []; with _phase_timer(run_stats, "container_scanning"):` | `_run_container_phase()` | `container_scanner` |
| Source | `source_endpoints = []; with _phase_timer(run_stats, "source_scanning"):` | `_run_source_phase()` | `source_scanner` |

Commit: `6059414`

### Task 2: Identity, data_at_rest, and email stage scanners

Nine additional scanners migrated in the identity and data_at_rest stages, plus the email scanner:

**Identity stage:**

| Scanner | New function | Label |
|---------|--------------|-------|
| AWS | `_run_aws_phase()` | `aws_connector` |
| Azure | `_run_azure_phase()` | `azure_connector` |
| GCP | `_run_gcp_phase()` | `gcp_connector` |
| DB (pg + mysql) | `_run_db_phase()` | `db_connector` |

**Data-at-rest stage:**

| Scanner | New function | Label |
|---------|--------------|-------|
| S3 | `_run_s3_phase()` | `s3_connector` |
| Azure Blob | `_run_blob_phase()` | `azure_blob_connector` |
| K8S | `_run_k8s_phase()` | `k8s_connector` |
| DNSSEC | `_run_dnssec_phase()` | `dnssec_scanner` |
| SAML | `_run_saml_phase()` | `saml_scanner` |
| Kerberos | `_run_kerberos_phase()` | `kerberos_scanner` |
| Vault | `_run_vault_phase()` | `vault_connector` |

**Email stage:**

| Scanner | Old pattern | New function | Label |
|---------|-------------|--------------|-------|
| Email | `with _phase_timer(...): try: ... except BaseException:` | `_run_email_phase()` | `email_scanner` |

The email scanner's inline `BaseException` try/except (which duplicated `_wrapped_phase` logic) was removed. The `_emit_missing_extra_advisory` call that precedes the email phase is preserved in place — it runs before `_run_email_phase` is defined and called, which is the correct ordering.

The GCS storage reuse block (`gcs_storage_reuse`) was intentionally left with the inline `with _phase_timer` pattern — it calls `_process_gcs_storage_encryption()` which is a pure in-memory transform with zero external I/O and no crash risk.

Commit: `00ca938`

## Verification Results

All plan verification commands passed:

1. `python -m compileall run_scan.py` — PASS (no syntax errors)
2. All 12 scanner labels present in source — PASS
3. All 9 old inline timer patterns removed — PASS
4. `_wrapped_phase` call count: 19 (>= 15 threshold) — PASS
5. `except BaseException` count: 1 (only in `_wrapped_phase` def) — PASS

## Deviations from Plan

None — plan executed exactly as written. The three decisions documented in the frontmatter above reflect implementation choices made within the plan's explicit guidance (GCS keep-as-is, EKS inner try/except preservation, email advisory ordering).

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All changes are pure refactors of existing scanner call sites — behavior is identical when no exception occurs, and improved (consistent error capture) when an exception does occur. Consistent with accepted threat dispositions T-67-03-01 through T-67-03-03 in the plan's threat model.

## Known Stubs

None.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| run_scan.py (modified) | FOUND |
| commit 6059414 (Task 1) | FOUND |
| commit 00ca938 (Task 2) | FOUND |
| `_run_jwt_phase` in run_scan.py | FOUND |
| `_run_container_phase` in run_scan.py | FOUND |
| `_run_source_phase` in run_scan.py | FOUND |
| `_run_aws_phase` in run_scan.py | FOUND |
| `_run_azure_phase` in run_scan.py | FOUND |
| `_run_gcp_phase` in run_scan.py | FOUND |
| `_run_db_phase` in run_scan.py | FOUND |
| `_run_s3_phase` in run_scan.py | FOUND |
| `_run_blob_phase` in run_scan.py | FOUND |
| `_run_k8s_phase` in run_scan.py | FOUND |
| `_run_dnssec_phase` in run_scan.py | FOUND |
| `_run_saml_phase` in run_scan.py | FOUND |
| `_run_kerberos_phase` in run_scan.py | FOUND |
| `_run_vault_phase` in run_scan.py | FOUND |
| `_run_email_phase` in run_scan.py | FOUND |
| 19 _wrapped_phase call sites | FOUND |
| exactly 1 BaseException catch | FOUND |
