---
phase: 28-object-storage-audit
verified: 2026-04-25T00:00:00Z
status: human_needed
score: 8/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Verify UAT-28-01 — S3 chaos lab end-to-end with MinIO"
    expected: "Two protocol=S3 CryptoEndpoint rows (arn:aws:s3:::encrypted-bucket → S3/sse-s3 no severity; arn:aws:s3:::unencrypted-bucket → S3/unencrypted HIGH); dar_storage_unencrypted_count==1 in evidence; 'Object storage unencrypted' in score drivers; no OperationNotPageableError in scan log"
    why_human: "Requires Docker to boot storage-s3 compose profile with minio + minio-seed, and a live boto3 S3 scan against localhost:29000 with MinIO credentials"
  - test: "Verify UAT-28-02 — Azure Blob live subscription scan"
    expected: "One CryptoEndpoint per container; platform-managed accounts produce BLOB/platform-managed/MEDIUM; CMK accounts produce BLOB/cmk/no-severity; dar_storage_aws_managed_count reflects platform-managed container count; no traceback in logs"
    why_human: "Requires a real Azure subscription with at least two storage accounts; cannot mock a live subscription scan"
  - test: "Verify UAT-28-03 — GCS reuse zero-API-call invariant at runtime"
    expected: "gcs_scanning and gcs_storage_reuse phase blocks both appear in scan logs; total storage.buckets.list calls observed = 1 (only Phase 26, not 2); per-bucket GCS rows from Phase 26 still present in DB"
    why_human: "Requires a live GCP project with ADC configured to confirm gcs_storage_reuse does not issue a second storage.buckets.list call at runtime"
---

# Phase 28: Object Storage Audit Verification Report

**Phase Goal:** QU.I.R.K. can determine per-bucket encryption policy for S3, Azure Blob, and GCS — consuming GCS enumeration data from Phase 26 rather than re-fetching, with parallel S3 probing via ThreadPoolExecutor
**Verified:** 2026-04-25
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | S3 audit returns per-bucket encryption policy using ThreadPoolExecutor(max_workers=10) — no OperationNotPageableError | VERIFIED | `ThreadPoolExecutor(max_workers=10)` at aws_connector.py:228; `list_buckets()` called directly (comment on line 174 documents the paginator anti-pattern); 10/10 tests in test_s3_encryption.py pass |
| 2 | Azure Blob audit returns per-container encryption configuration (platform-managed vs CMK) | VERIFIED | `_scan_blob_encryption` at azure_connector.py with BLOB/cmk and BLOB/platform-managed ladder; 7/7 tests in test_azure_blob.py pass |
| 3 | GCS bucket encryption audit reuses Phase 26 connector output — zero duplicate storage.buckets.list API calls | VERIFIED (unit) | `_process_gcs_storage_encryption` in run_scan.py:84 makes no API calls; `google.cloud.storage.Client.call_count == 0` asserted in test_gcs_reuse.py::test_gcs_reuse_zero_storage_buckets_list_call; 5/5 tests pass. Runtime verification requires human (UAT-28-03) |
| 4 | Unencrypted S3 → HIGH; SSE-KMS AWS-managed → MEDIUM; SSE-KMS CMK → no finding | VERIFIED | Severity ladder in aws_connector.py:183–199; all five ladder branches tested and GREEN in test_s3_encryption.py |
| 5 | All object storage findings stored in dat_scan_json and produce correctly-named CryptoEndpoint rows; results appear in CBOM | VERIFIED (with deviation) | `dat_scan_json` set on all S3 and Azure Blob rows; CBOM Pass 1/2/3 skip-lists in builder.py include "S3" and "AZURE_BLOB". **Protocol name deviation**: ROADMAP SC-5 says `protocol="STORAGE"` but D-05/D-06 locked decisions specify `protocol="S3"` and `protocol="AZURE_BLOB"`. Plan 03 SUMMARY explicitly documents this mismatch; the functional intent (findings in CBOM with correct protocol rows) is fully satisfied by the more specific values |
| 6 | dar_storage_* counters in evidence.py and weights in scoring.py with correct values | VERIFIED | `_PROTOCOL_KEYS` includes "S3" and "AZURE_BLOB"; dar_storage_unencrypted_count and dar_storage_aws_managed_count counters initialized and incremented; SCORE_WEIGHTS["dar_storage_unencrypted_ratio"]==12.0 and ["dar_storage_aws_managed_ratio"]==4.0; 9/9 tests in test_dar_storage_scoring.py pass |
| 7 | MinIO chaos lab (storage-s3 Docker Compose profile + seed script) present and structurally valid | VERIFIED | minio-seed.sh exists and is executable; contains mc mb commands for both buckets plus mc encrypt set sse-s3; docker-compose.yml includes minio/minio:latest, storage-s3 profile, minio-seed service; YAML validates; 3/3 static tests in test_chaos_storage.py pass |
| 8 | docs/UAT-SERIES.md has UAT-28-01, UAT-28-02, UAT-28-03 entries | VERIFIED | grep confirms UAT-28-01, UAT-28-02, UAT-28-03 all present; storage-s3, BLOB/platform-managed, S3/unencrypted referenced; Last Updated set to 2026-04-25 |
| 9 | No regressions in pre-existing tests (cloud connectors, intelligence, CBOM) | VERIFIED | tests/test_cloud_connectors.py (15 pass), tests/test_intelligence_evidence.py (6 pass), tests/test_intelligence_scoring.py (4 pass), tests/test_cbom_builder.py (30 pass) — all GREEN |

**Score:** 8/9 truths verified (truth 3 partially verified — unit assertions pass, runtime confirmation is human-only per UAT-28-03)

### Protocol Name Deviation (ROADMAP SC-5)

ROADMAP.md Phase 28 Success Criterion 5 states `protocol="STORAGE"`. The locked design decisions D-05/D-06 in 28-CONTEXT.md specify `protocol="S3"` and `protocol="AZURE_BLOB"`. The implementation follows the locked decisions. Plan 03 SUMMARY documents this explicitly. The functional intent of SC-5 (findings in dat_scan_json producing CryptoEndpoint rows that appear in the CBOM) is fully satisfied. The ROADMAP text contains a draft protocol name superseded by the design decisions.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | azure-mgmt-storage>=21.0.0 in [cloud] extras | VERIFIED | 1 match for azure-mgmt-storage>=21.0.0 |
| `quirk/config.py` | ConnectorsCfg with enable_s3, enable_blob, aws_endpoint_url | VERIFIED | All 3 fields present with safe defaults (False, False, None) |
| `quirk/config_template.yaml` | Commented connector entries for object storage | VERIFIED | 3 commented entries present |
| `tests/test_s3_encryption.py` | STOR-01 tests (10 tests) | VERIFIED | 10 def test_ functions; all pass |
| `tests/test_azure_blob.py` | STOR-02 tests (7 tests) | VERIFIED | 7 def test_ functions; all pass |
| `tests/test_gcs_reuse.py` | STOR-03 tests (5 tests) | VERIFIED | 5 def test_ functions; all pass |
| `tests/test_dar_storage_scoring.py` | D-09/D-10 tests (9 tests) | VERIFIED | 9 def test_ functions; all pass |
| `tests/test_chaos_storage.py` | Chaos lab tests (5 tests: 3 static + 2 skipped) | VERIFIED | 5 def test_ functions; 3 pass, 2 skipped (QUIRK_RUN_DOCKER_IT not set) |
| `quirk/scanner/aws_connector.py` | _scan_s3_encryption() function | VERIFIED | Function exists; ThreadPoolExecutor(max_workers=10); protocol="S3"; dat_scan_json populated |
| `quirk/scanner/azure_connector.py` | _scan_blob_encryption() function | VERIFIED | Function exists; inline import guard; protocol="AZURE_BLOB"; per-container endpoint creation |
| `run_scan.py` | _process_gcs_storage_encryption helper + 3 phase blocks | VERIFIED | Helper at module level; s3_scanning, blob_scanning, gcs_storage_reuse phase blocks present; endpoint lists wired into master concatenation |
| `quirk/intelligence/evidence.py` | dar_storage_* counters and ratios | VERIFIED | _PROTOCOL_KEYS has S3+AZURE_BLOB; 2 counters; 2 elif blocks; 4 return dict entries |
| `quirk/intelligence/scoring.py` | dar_storage_* weights and impacts | VERIFIED | SCORE_WEIGHTS 12.0+4.0; 2 dar_impacts tuples ("Object storage unencrypted", "Object storage platform-managed keys") |
| `quirk/cbom/builder.py` | Pass 1/2/3 skip extensions for S3 and AZURE_BLOB | VERIFIED | All 3 passes updated; confirmed at lines 410, 438, 519 |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | storage-s3 profile with minio + minio-seed | VERIFIED | 7 references to storage-s3/minio-seed/minio; YAML valid |
| `quantum-chaos-enterprise-lab/storage/minio-seed.sh` | MinIO bucket seed script | VERIFIED | Exists; executable; 3 required mc commands present; 15 lines |
| `labs/storage/expected_results.md` | Phase 28 chaos lab expected output documentation | VERIFIED | File exists; documents Phase 28, STOR-01, both buckets, expected scan output |
| `docs/UAT-SERIES.md` | Phase 28 UAT cases | VERIFIED | UAT-28-01, UAT-28-02, UAT-28-03 all present; Last Updated 2026-04-25 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `_scan_s3_encryption` | `with _phase_timer(run_stats, 's3_scanning'): ... _scan_s3_encryption(...)` | WIRED | Confirmed at run_scan.py:536+545; gated on cfg.connectors.enable_s3 |
| `run_scan.py` | `_scan_blob_encryption` | `with _phase_timer(run_stats, 'blob_scanning'): ... _scan_blob_encryption(...)` | WIRED | Confirmed at run_scan.py:559+565; gated on cfg.connectors.enable_blob |
| `run_scan.py` | `_process_gcs_storage_encryption` | `called with gcp_endpoints after gcp_scanning block` | WIRED | Confirmed at run_scan.py:577–578; unconditional call |
| `_scan_s3_encryption` | `ThreadPoolExecutor` | `from concurrent.futures import ThreadPoolExecutor (max_workers=10)` | WIRED | aws_connector.py:228; also in docstring reference |
| `quirk/intelligence/evidence.py` | `build_evidence_summary return dict` | `dar_storage_* keys present` | WIRED | 4 keys at lines 239–242 |
| `quirk/intelligence/scoring.py SCORE_WEIGHTS` | `dar_storage_* entries` | `dar_storage_unencrypted_ratio/dar_storage_aws_managed_ratio` | WIRED | Lines 21–22 of scoring.py |
| `quirk/cbom/builder.py Pass 1` | `S3 and AZURE_BLOB protocol skip` | `elif ep.protocol in (..., "S3", "AZURE_BLOB"): pass` | WIRED | Line 410 |
| `docker-compose.yml minio-seed service` | `storage/minio-seed.sh` | `volumes mount + entrypoint` | WIRED | minio-seed service references ./storage/minio-seed.sh:ro |
| `master endpoints list` | `s3_endpoints + blob_endpoints + gcs_storage_endpoints` | `concatenation before evidence/scoring/CBOM` | WIRED | run_scan.py:627 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `_scan_s3_encryption` | `results: List[CryptoEndpoint]` | `client.list_buckets()` + `client.get_bucket_encryption(Bucket=name)` for each bucket | Yes — live boto3 API calls per bucket | FLOWING |
| `_scan_blob_encryption` | `results: List[CryptoEndpoint]` | `client.storage_accounts.list()` + `client.blob_containers.list(rg, account_name)` | Yes — live azure-mgmt-storage API calls | FLOWING |
| `_process_gcs_storage_encryption` | `return []` | GCS-SUMMARY sentinel gcs_scan_json (from Phase 26 data) | Returns empty by design (STOR-03 zero-API invariant); Phase 26 per-bucket rows already in gcp_endpoints | FLOWING (by design) |
| `build_evidence_summary` | `dar_storage_unencrypted_count`, `dar_storage_aws_managed_count` | Per-endpoint loop over all endpoints passed in | Yes — derived from actual CryptoEndpoint rows | FLOWING |
| `compute_readiness_score` | `dar_storage_unencrypted`, `dar_storage_aws_managed` | `evidence.get("dar_storage_unencrypted_count", 0)` etc. | Yes — reads evidence dict | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| S3 severity ladder (10 tests) | `python3 -m pytest tests/test_s3_encryption.py -q` | 10 passed in 0.53s | PASS |
| Azure Blob keySource ladder (7 tests) | `python3 -m pytest tests/test_azure_blob.py -q` | 7 passed | PASS |
| GCS zero-API-call invariant (5 tests) | `python3 -m pytest tests/test_gcs_reuse.py -q` | 5 passed | PASS |
| dar_storage scoring (9 tests) | `python3 -m pytest tests/test_dar_storage_scoring.py -q` | 9 passed | PASS |
| Chaos lab static checks | `python3 -m pytest tests/test_chaos_storage.py -q` | 3 passed, 2 skipped | PASS |
| Regression — cloud connectors | `python3 -m pytest tests/test_cloud_connectors.py -q` | 15 passed | PASS |
| Regression — intelligence/CBOM | `python3 -m pytest tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py tests/test_cbom_builder.py -q` | 55 passed | PASS |
| ConnectorsCfg safe defaults | `python3 -c "from quirk.config import ConnectorsCfg; c = ConnectorsCfg(); print(c.enable_s3, c.enable_blob, c.aws_endpoint_url)"` | False False None | PASS |
| docker-compose.yml YAML validity | `python3 -c "import yaml; yaml.safe_load(open('quantum-chaos-enterprise-lab/docker-compose.yml'))"` | No error | PASS |
| End-to-end live scan (S3 MinIO) | Requires Docker + storage-s3 profile | Not run | SKIP (human UAT-28-01) |
| End-to-end live scan (Azure Blob) | Requires real Azure subscription | Not run | SKIP (human UAT-28-02) |
| End-to-end GCS reuse runtime confirmation | Requires live GCP project | Not run | SKIP (human UAT-28-03) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| STOR-01 | 28-01-PLAN.md, 28-02-PLAN.md | Scanner can determine S3 bucket encryption policy per bucket (SSE-S3, SSE-KMS CMK vs AWS-managed, unencrypted) across all buckets | SATISFIED | `_scan_s3_encryption` implements complete D-06 severity ladder; ThreadPoolExecutor(max_workers=10); direct list_buckets call; 10/10 tests GREEN |
| STOR-02 | 28-01-PLAN.md, 28-02-PLAN.md | Scanner can determine Azure Blob container encryption configuration (platform-managed vs CMK) | SATISFIED | `_scan_blob_encryption` implements D-07 keySource ladder; inline azure-mgmt-storage import with ImportError guard; per-container CryptoEndpoint rows; 7/7 tests GREEN |
| STOR-03 | 28-01-PLAN.md, 28-02-PLAN.md | GCS bucket encryption audit reuses Phase 26 GCP connector output — no duplicate API calls | SATISFIED (unit) | `_process_gcs_storage_encryption` reads GCS-SUMMARY sentinel JSON without making any GCS API calls; test_gcs_reuse_zero_storage_buckets_list_call asserts google.cloud.storage.Client.call_count == 0; runtime confirmation deferred to UAT-28-03 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found in implementation files. All TODOs/FIXMEs absent. No stubs. No hardcoded empty returns masking real implementations. |

Notable negative result: the `get_paginator` grep that initially appeared to match `aws_connector.py` is a comment line (`# list_buckets is NOT a paginator`) documenting the anti-pattern to avoid — the actual call is `client.list_buckets()` with no paginator.

### Human Verification Required

#### 1. UAT-28-01: S3 MinIO Chaos Lab End-to-End

**Test:** Boot `docker compose --profile storage-s3 up -d` in quantum-chaos-enterprise-lab. Wait ~10s for healthcheck + minio-seed to complete. Configure a test config.yaml with `enable_s3: true, aws_endpoint_url: http://localhost:29000`. Set `AWS_ACCESS_KEY_ID=minioadmin AWS_SECRET_ACCESS_KEY=minioadmin`. Run `quirk --config test_lab.yaml`. Inspect CryptoEndpoint rows and scan log.
**Expected:** Exactly 2 `protocol=S3` rows — `arn:aws:s3:::encrypted-bucket` with `service_detail=S3/sse-s3` and no severity; `arn:aws:s3:::unencrypted-bucket` with `service_detail=S3/unencrypted` and `severity=HIGH`. No OperationNotPageableError in logs. `dar_storage_unencrypted_count == 1` in evidence summary. Score drivers list includes "Object storage unencrypted".
**Why human:** Requires Docker running MinIO with the storage-s3 profile. The static tests confirm the seed script and compose configuration are structurally correct but cannot substitute for a live scan.

#### 2. UAT-28-02: Azure Blob Live Subscription Scan

**Test:** With `pip install quirk[cloud]` and Azure CLI logged in, configure config.yaml with `enable_blob: true, azure_subscription_id: <real-uuid>`. Run `quirk --config azure_uat.yaml`. Inspect output.
**Expected:** One CryptoEndpoint row per blob container. Platform-managed accounts: `BLOB/platform-managed`, `severity=MEDIUM`. CMK accounts: `BLOB/cmk`, no severity. `dar_storage_aws_managed_count` reflects platform-managed container count. No traceback in logs.
**Why human:** Requires a real Azure subscription with at least two storage accounts. Cannot simulate live azure-mgmt-storage StorageManagementClient behavior end-to-end.

#### 3. UAT-28-03: GCS Reuse Zero-API-Call Invariant at Runtime

**Test:** With ADC configured (`gcloud auth application-default login`), run `quirk --config gcp_uat.yaml` with `enable_gcp: true`. Inspect scan logs for both `gcs_scanning` and `gcs_storage_reuse` phase block entries. Compare storage.buckets.list call count (expected: 1, from Phase 26 only).
**Expected:** Both phase blocks appear in timing log. Total storage.buckets.list calls = 1 (Phase 26 only; Phase 28 gcs_storage_reuse adds 0 calls). Per-bucket GCS rows from Phase 26 remain in DB.
**Why human:** Requires a live GCP project and gcloud ADC to confirm the runtime API call count; the unit test patches the client and verifies call_count == 0 but cannot validate against an actual GCP scan flow.

### Gaps Summary

No blocking gaps found. All automated checks pass. The phase is complete pending human end-to-end validation of the three live-cloud scan paths (MinIO/S3, Azure Blob, GCS runtime). The single noted deviation — ROADMAP SC-5 using `protocol="STORAGE"` where the implementation uses `protocol="S3"` and `protocol="AZURE_BLOB"` — is intentional, documented in Plan 03 SUMMARY, and functionally correct per the locked design decisions (D-05/D-06).

---

_Verified: 2026-04-25T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
