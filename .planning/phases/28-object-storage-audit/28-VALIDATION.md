---
phase: 28
slug: object-storage-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml ([tool.pytest.ini_options]) |
| **Quick run command** | `python -m pytest tests/ -x -q 2>&1 | tail -5` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q 2>&1 | tail -5`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-S3-01 | S3 scan | 1 | STOR-01 | — | ClientError(ServerSideEncryptionConfigurationNotFoundError) → HIGH finding | unit | `python -m pytest tests/test_s3_encryption.py -x -q` | ❌ W0 | ⬜ pending |
| 28-S3-02 | S3 scan | 1 | STOR-01 | — | SSE-KMS AWS-managed → MEDIUM, CMK → no finding | unit | `python -m pytest tests/test_s3_encryption.py -x -q` | ❌ W0 | ⬜ pending |
| 28-AZ-01 | Azure Blob scan | 2 | STOR-02 | — | platform-managed keySource → MEDIUM; CMK → no finding | unit | `python -m pytest tests/test_azure_blob.py -x -q` | ❌ W0 | ⬜ pending |
| 28-GCS-01 | GCS reuse | 2 | STOR-03 | — | Zero duplicate storage.buckets.list calls; reads gcs_scan_json sentinel | unit | `python -m pytest tests/test_gcs_reuse.py -x -q` | ❌ W0 | ⬜ pending |
| 28-SCORE-01 | Scoring | 3 | STOR-01, STOR-02 | — | dar_storage_unencrypted_ratio weight=12.0; dar_storage_aws_managed_ratio weight=4.0 | unit | `python -m pytest tests/test_dar_storage_scoring.py -x -q` | ❌ W0 | ⬜ pending |
| 28-LAB-01 | Chaos lab | 3 | STOR-01 | — | MinIO unencrypted-bucket → HIGH; encrypted-bucket → no finding | integration | `python -m pytest tests/test_chaos_storage.py -x -q -m integration` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_s3_encryption.py` — stubs for STOR-01 S3 encryption severity ladder
- [ ] `tests/test_azure_blob.py` — stubs for STOR-02 Azure Blob keySource logic
- [ ] `tests/test_gcs_reuse.py` — stubs for STOR-03 zero-duplicate GCS read
- [ ] `tests/test_dar_storage_scoring.py` — stubs for dar_storage_* counter/weight assertions
- [ ] `tests/test_chaos_storage.py` — integration stubs for MinIO chaos lab (marked `@pytest.mark.integration`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Azure Blob per-container enumeration against live Azure subscription | STOR-02 | Requires live Azure credentials and subscription | Run `quirk scan --config test_azure.yaml` with a configured Azure subscription; verify CryptoEndpoint rows with `protocol="AZURE_BLOB"` appear in DB |
| ThreadPoolExecutor(max_workers=10) parallelism under S3 rate-limiting | STOR-01 | Requires live AWS with >10 buckets | Run `quirk scan --config test_aws.yaml`; verify no OperationNotPageableError in logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
