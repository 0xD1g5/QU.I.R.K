---
phase: 72-cloud-scanner-warnings
plan: 01
subsystem: scanners-cloud (AWS connector)
tags: [aws, acm, kms, s3, eks, threadpool, audit-closure]
requires: []
provides: [CLOUD-01 closure]
affects:
  - quirk/scanner/aws_connector.py
  - tests/test_aws_connector.py
  - .planning/audit-2026-05-08/AUDIT-TASKS.md
tech_stack:
  added: []
  patterns:
    - "as_completed + per-future .result() (Phase 64 idiom)"
    - "Module-level skip-state frozenset"
    - "Empty-input guard with fail-soft continue (Phase 71 D-11 precedent)"
key_files:
  created:
    - tests/test_aws_connector.py
  modified:
    - quirk/scanner/aws_connector.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-07/WR-01: _scan_acm guards describe_certificate against empty/whitespace ARN"
  - "D-08/WR-02: _scan_kms skips KeyState in {Disabled, PendingDeletion, PendingImport, Unavailable}"
  - "D-09/WR-13: _scan_s3_encryption uses as_completed + per-future result instead of executor.map"
  - "D-10/WR-14: _scan_eks_encryption iterates full enc_cfg list, emits one finding per provider"
  - "D-11/WR-19: ThreadPoolExecutor + as_completed imported at module scope"
metrics:
  tasks_completed: 3
  files_modified: 3
  tests_added: 13
  audit_rows_flipped: 5
completed: 2026-05-15
---

# Phase 72 Plan 01: AWS Connector Hardening — Summary

CLOUD-01 closed: AWS connector now emits correct findings on malformed responses
and never silently swallows worker exceptions in the S3 path.

## Tasks Completed

| Task | Name                                                                    | Commit  |
| ---- | ----------------------------------------------------------------------- | ------- |
| 1    | AWS connector fixes — ACM guard, KMS skip, EKS multi-entry, module-imp  | 20277d6 |
| 2    | S3 executor.map → as_completed migration (WR-13)                        | 9477a80 |
| 3a   | Tests for WR-01/02/13/14/19                                             | 404ab71 |
| 3b   | Audit ledger flip (WR-01/02/13/14/19 → closed)                          | 8a13153 |

## What Was Built

### Task 1 — Five-site AWS hardening (commit `20277d6`)

- **Module top:** added `from concurrent.futures import ThreadPoolExecutor, as_completed` (D-11) and `_KMS_SKIP_STATES = frozenset({"Disabled", "PendingDeletion", "PendingImport", "Unavailable"})` (D-08 backing constant).
- **`_scan_acm` (line ~60):** before `describe_certificate(CertificateArn=arn)`, added `if not arn or not arn.strip(): logger.v("ACM cert with empty ARN — skipping"); continue`. Mirrors Phase 71 D-11 fail-soft pattern. (D-07/WR-01)
- **`_scan_kms` (line ~354):** after `describe_key`, check `KeyMetadata.KeyState`; if in `_KMS_SKIP_STATES`, `logger.info(f"KMS key {key_id} skipped (state={state})")` and `continue`. (D-08/WR-02)
- **`_scan_eks_encryption` (line ~155–198):** replaced the single-emit branch that read `enc_cfg[0].get("provider", {}).get("keyArn", "")` with a `for cfg in enc_cfg:` loop emitting one `CryptoEndpoint` per provider entry. Each finding's `service_detail` carries the `keyArn`, which keeps D-04's dedup tuple distinct across multiple providers. (D-10/WR-14)
- **Function-body import removed:** the prior `from concurrent.futures import ThreadPoolExecutor` inside `_scan_s3_encryption` body deleted; replaced with a one-line comment pointing to the module-top import. (D-11/WR-19)

### Task 2 — S3 as_completed migration (commit `9477a80`)

- **`_scan_s3_encryption` (line ~329–340):** replaced
  ```python
  with ThreadPoolExecutor(max_workers=10) as executor:
      for ep in executor.map(_build_endpoint, buckets):
          if ep is not None:
              results.append(ep)
  ```
  with the Phase 64 `as_completed` idiom:
  ```python
  with ThreadPoolExecutor(max_workers=10) as executor:
      futures = {executor.submit(_build_endpoint, bucket): bucket for bucket in buckets}
      for f in as_completed(futures):
          bucket = futures[f]
          try:
              ep = f.result()
          except Exception as exc:
              if logger:
                  logger.v(f"S3 endpoint task crashed for bucket {bucket!r}: {exc}")
              continue
          if ep is not None:
              results.append(ep)
  ```
  (D-09/WR-13)

### Task 3 — Tests + audit flip

- **`tests/test_aws_connector.py`** (new file, 13 tests, all passing):
  - WR-01: `test_scan_acm_skips_empty_arn`, `test_scan_acm_skips_whitespace_arn`, `test_scan_acm_emits_for_valid_arn`
  - WR-02: `test_scan_kms_skips_non_encrypting_states` (parametrized x4: Disabled/PendingDeletion/PendingImport/Unavailable) + `test_scan_kms_emits_for_enabled`
  - WR-13: `test_scan_s3_propagates_build_endpoint_exception` (behavioral) + `test_scan_s3_uses_as_completed_pattern` (structural)
  - WR-14: `test_scan_eks_emits_per_provider_entry` + `test_scan_eks_single_provider_still_one_finding`
  - WR-19: `test_threadpool_executor_imported_at_module_scope`
- **Audit ledger:** WR-01, WR-02, WR-13, WR-14, WR-19 flipped to `Phase 72 | [x] closed` with per-row evidence (5 line-edits, single docs commit `8a13153`).

## Verification Commands Run

```bash
python -m compileall quirk/scanner/aws_connector.py    # exits 0
pytest tests/test_aws_connector.py -x                  # 13 passed in 0.13s
grep -cE "scanners-cloud/WR-(01|02|13|14|19).*Phase 72.*\[x\] closed" \
  .planning/audit-2026-05-08/AUDIT-TASKS.md            # == 5
grep -nE "^from concurrent\.futures import" quirk/scanner/aws_connector.py    # line 10
grep -cnE "enc_cfg\[0\]" quirk/scanner/aws_connector.py                       # 0
grep -nE "executor\.map\(_build_endpoint" quirk/scanner/aws_connector.py      # 0
git diff --stat .planning/audit-2026-05-08/AUDIT-TASKS.md                     # 5 ins / 5 del
```

## Deviations from Plan

**Logger contract adjustment (not a deviation; CLAUDE.md compliance):** Plan
examples used `logger.warning(...)` and `logger.info(...)`. The project's
`quirk/logging_util.py::Logger` exposes only `.v(...)`, `.info(...)`, and
`.stamp(...)` — no `.warning` method. To avoid `AttributeError` in
production, I used:

- `logger.v(...)` for the ACM empty-ARN message (D-07) — matches the existing
  `.v()` usage across `_scan_acm`'s sibling exception path.
- `logger.info(...)` for the KMS skip message (D-08) — D-08 explicitly says
  "INFO-level log", and the project Logger has an `.info` method.
- `logger.v(...)` for the S3 worker-crash message (D-09) — matches the
  existing `.v()` usage in the `_build_endpoint` body's own try/except.

Tests use `MagicMock` for the logger so both `.v` and `.info` are accepted;
this also matches the rest of the codebase's test pattern (e.g.
`tests/test_k8s_connector.py`).

**Audit cite vs. current code (RESEARCH C-1):** As noted in `72-RESEARCH.md`,
D-09's audit cite references `executor.map(_classify, ...)` but the actual
current code at `aws_connector.py:303-306` reads `executor.map(_build_endpoint, buckets)`.
Applied the locked behavior change (executor.map → as_completed) to the
**current** call site name; the inner function identifier is irrelevant to the
locked decision. Documented in audit-row evidence and Task 2 commit message.

No other deviations — five locked sites edited atomically; D-25 do-not-touch
list honored (no incidental refactor in `_scan_rds_encryption`,
`_scan_cloudfront`, `_scan_elbv2`, or `scan_aws_targets`).

## Self-Check: PASSED

- `quirk/scanner/aws_connector.py` modified — verified via `git diff HEAD~4 HEAD -- quirk/scanner/aws_connector.py` (2 commits, 65+11 insertions, 33+1 deletions)
- `tests/test_aws_connector.py` created — verified `[ -f tests/test_aws_connector.py ]` true, 13 tests passing
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` 5 rows flipped — verified `grep -c` == 5
- All four commits present in `git log --oneline -5`: 8a13153, 404ab71, 9477a80, 20277d6
