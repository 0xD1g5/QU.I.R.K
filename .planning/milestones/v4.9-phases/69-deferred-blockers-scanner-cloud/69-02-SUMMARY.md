---
phase: 69
plan: 02
subsystem: scanner/cloud
tags: [block-02, cr-02, gcp, cloud-sql, severity-fix]
requires: []
provides:
  - "_scan_cloud_sql emits severity in severity column (not cert_pubkey_alg)"
  - "service_detail prefixed with CLOUD_SQL/ for description routing"
affects:
  - quirk/scanner/gcp_connector.py
  - tests/test_cloud_connectors.py
tech-stack:
  added: []
  patterns:
    - "CryptoEndpoint(severity=..., service_detail=...) for cloud-scan findings instead of overloading cert_pubkey_alg"
key-files:
  created: []
  modified:
    - quirk/scanner/gcp_connector.py
    - tests/test_cloud_connectors.py
decisions:
  - "D-08 (Phase 69 CONTEXT): severity → severity column; description → service_detail (CLOUD_SQL/ prefix); cert_pubkey_alg omitted"
metrics:
  duration: ~8min
  completed: 2026-05-14
requirements: [BLOCK-02]
---

# Phase 69 Plan 02: Cloud SQL severity column fix Summary

One-liner: Routed GCP Cloud SQL SSL-enforcement severity from the misused
`cert_pubkey_alg` column into the proper `severity` column, with description
moving into `service_detail` — closes BLOCK-02 (audit CR-02).

## What was built

### Task 1: `quirk/scanner/gcp_connector.py` — `_scan_cloud_sql`

- Replaced `cert_pubkey_alg=severity` with `severity=severity` on the
  `CryptoEndpoint` constructor (line ~267).
- Replaced `service_detail=instance_name` with
  `service_detail=f"CLOUD_SQL/{description.replace(' ', '-')}"` so the
  description is preserved verbatim in a human-routable field.
- `cert_pubkey_alg` is no longer passed for Cloud SQL findings — defaults to
  `None`, matching the column's intended public-key-algorithm semantic.
- `cloud_scan_json={"sslMode": ssl_mode, "finding": description}` payload
  preserved exactly.
- Other `cert_pubkey_alg=` writes in the file are unrelated (KMS algorithm
  mapping line 193, GCS sentinel line 314, GCS bucket alg line 331) and were
  not touched, per minimal-diff rule.

Commit: `1c0b39b`

### Task 2: `tests/test_cloud_connectors.py` — three Cloud SQL test rewrites

TDD flow: confirmed RED first (existing tests failed against the Task-1 fix
because they asserted the buggy behavior), then rewrote assertions:

- `test_gcp_cloud_sql_plaintext_allowed`: asserts `ep.severity == "HIGH"`,
  `(ep.cert_pubkey_alg or "") == ""`, and
  `(ep.service_detail or "").startswith("CLOUD_SQL/")` (the description-routing
  lock per the plan's behavior spec).
- `test_gcp_cloud_sql_encrypted_only`: asserts `ep.severity == "MEDIUM"` and
  `(ep.cert_pubkey_alg or "") == ""`.
- `test_gcp_cloud_sql_null_ssl_mode`: asserts `ep.severity == "HIGH"` and
  `(ep.cert_pubkey_alg or "") == ""`.

Tests not in scope (`test_gcp_cloud_sql_mtls_no_finding`,
`test_gcp_cloud_sql_encrypted_only` semantics around MTLS) were left
untouched. Fixture setup and names preserved verbatim per minimal-diff rule.

Commit: `fd0b7dd`

## Verification

```
$ python -m compileall quirk/scanner/gcp_connector.py
Compiling 'quirk/scanner/gcp_connector.py'...  [exit 0]

$ pytest tests/test_cloud_connectors.py -x -q
............... [100%]
15 passed in 0.57s

$ grep -n 'cert_pubkey_alg' quirk/scanner/gcp_connector.py | grep -iE 'sql|severity|HIGH|MEDIUM'
(no output — no severity-string writes remain)

$ grep -n 'cert_pubkey_alg' tests/test_cloud_connectors.py | grep -iE 'HIGH|MEDIUM'
(no output — no buggy assertions remain)
```

All four `<verification>` checks from the plan pass. Both `<acceptance_criteria>`
sets satisfied.

## Decisions Made

- **D-08 honored verbatim**: severity → `severity` kwarg; description →
  `service_detail` with `CLOUD_SQL/<dashed-description>` prefix;
  `cert_pubkey_alg` kwarg omitted entirely (defaults to `None`), not set to
  empty string. The test assertion `(ep.cert_pubkey_alg or "") == ""` accepts
  both None and "".
- **Test selection**: The plan's behavior spec for
  `test_gcp_cloud_sql_encrypted_only` listed `ep.severity in (None, "MEDIUM")`
  as acceptable. The current `SSL_FINDING_MAP` deterministically returns
  `MEDIUM` for `ENCRYPTED_ONLY`, so the assertion was tightened to the exact
  value `"MEDIUM"` for stronger lock-in.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## TDD Gate Compliance

- RED gate: pre-existing tests already asserted the buggy behavior and failed
  against the Task-1 fix; verified by running pytest after Task 1 commit
  (`test_gcp_cloud_sql_plaintext_allowed` failed with
  `assert False ... ep.cert_pubkey_alg`).
- GREEN gate: Task 2 (`test(69-02): ...` commit `fd0b7dd`) — 15 tests pass.
- REFACTOR gate: not needed (minimal diff).

Sequence: `fix(69-02)` (Task 1, `1c0b39b`) → `test(69-02)` (Task 2, `fd0b7dd`).
Note: per plan ordering, the source fix landed before the test rewrite (the
existing tests served as the RED state since they asserted the buggy
behavior). This is the prescribed flow for "rewrite tests that assert the bug"
tasks and is consistent with the plan's two-task structure.

## Self-Check: PASSED

- FOUND: `quirk/scanner/gcp_connector.py` (modified — `severity=severity`,
  `service_detail=f"CLOUD_SQL/...`")
- FOUND: `tests/test_cloud_connectors.py` (modified — three rewritten tests
  passing)
- FOUND commit `1c0b39b`: `fix(69-02): route Cloud SQL SSL severity ...`
- FOUND commit `fd0b7dd`: `test(69-02): assert Cloud SQL severity ...`
