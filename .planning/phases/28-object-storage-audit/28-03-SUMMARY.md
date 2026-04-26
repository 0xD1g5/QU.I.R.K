---
phase: 28
plan: 03
subsystem: object-storage-audit
tags: [evidence, scoring, cbom, chaos-lab, minio, docker-compose, uat, docs, stor-01, stor-02, stor-03]
dependency_graph:
  requires: [phase-28-plan-01-red-scaffold, phase-28-plan-02-scanner-green]
  provides: [dar_storage_evidence_counters, dar_storage_scoring_weights, cbom_s3_azure_blob_skip, minio_chaos_lab, uat_phase28_cases]
  affects: [quirk/intelligence/evidence.py, quirk/intelligence/scoring.py, quirk/cbom/builder.py, quantum-chaos-enterprise-lab/docker-compose.yml, quantum-chaos-enterprise-lab/storage/minio-seed.sh, labs/storage/expected_results.md, docs/UAT-SERIES.md]
tech_stack:
  added: [minio/minio:latest (chaos lab), minio/mc:latest (seed init container)]
  patterns: [dar_* counter extension, SCORE_WEIGHTS extension, CBOM pass skip-list extension, Docker Compose profile isolation (storage-s3)]
key_files:
  modified:
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
    - quirk/cbom/builder.py
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - docs/UAT-SERIES.md
  created:
    - quantum-chaos-enterprise-lab/storage/minio-seed.sh
    - labs/storage/expected_results.md
decisions:
  - "dar_storage_unencrypted_count and dar_storage_aws_managed_count follow exact dar_db_* counter pattern in evidence.py"
  - "BLOB/platform-managed maps to dar_storage_aws_managed_count (compliance gap, not HIGH) per D-09"
  - "SCORE_WEIGHTS: dar_storage_unencrypted_ratio=12.0 (same weight as plaintext DB), dar_storage_aws_managed_ratio=4.0 per D-10"
  - "CBOM Pass 1/2/3 all skip S3 and AZURE_BLOB — no key material, no cert, no TLS protocol component"
  - "MinIO profile named storage-s3 (not storage) to avoid collision with existing Phase 27 storage profile"
  - "minio-seed.sh mounted read-only via :ro volume flag per T-28-18 mitigation"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-25"
  tasks_completed: 4
  files_changed: 7
---

# Phase 28 Plan 03: Intelligence, CBOM, Chaos Lab, and Docs Summary

**One-liner:** Evidence/scoring extended with dar_storage_* counters and 12.0/4.0 weights; CBOM builder S3+AZURE_BLOB skip-lists hardened across all three passes; MinIO chaos lab added under storage-s3 Docker Compose profile; Phase 28 UAT cases documented — turning all 34 Phase 28 RED tests GREEN.

## What Was Built

### Task 1: Extend evidence.py + scoring.py for dar_storage_* counters and weights (D-09, D-10)

**quirk/intelligence/evidence.py** — Four coordinated edits:

1. `_PROTOCOL_KEYS` tuple extended with `"S3"` and `"AZURE_BLOB"` so storage protocol counts appear in evidence output (Pitfall 6 mitigation).
2. Two new counter variables added after `dar_db_*` init block:
   - `dar_storage_unencrypted_count` — S3/unencrypted HIGH findings
   - `dar_storage_aws_managed_count` — S3/sse-kms-aws + BLOB/platform-managed MEDIUM findings
3. Two new elif blocks in per-endpoint loop (same `str(getattr(ep, 'service_detail', '') or '')` defensive pattern as RDS block per T-28-14):
   - `elif proto == "S3"` — increments unencrypted_count or aws_managed_count based on service_detail substring
   - `elif proto == "AZURE_BLOB"` — increments aws_managed_count for platform-managed; BLOB/cmk is no penalty
4. Four new return dict entries: `dar_storage_unencrypted_count`, `dar_storage_aws_managed_count`, `dar_storage_unencrypted_ratio`, `dar_storage_aws_managed_ratio`

**quirk/intelligence/scoring.py** — Three coordinated edits:

1. `SCORE_WEIGHTS` extended with `dar_storage_unencrypted_ratio: 12.0` and `dar_storage_aws_managed_ratio: 4.0` (per D-10). `PROFILE_MULTIPLIERS` unchanged — the `"dar_"` prefix matcher auto-covers these new keys.
2. Evidence extraction block: `dar_storage_unencrypted` and `dar_storage_aws_managed` vars added after `dar_db_*` extraction.
3. `dar_impacts` list extended with two new tuples: `("Object storage unencrypted", ...)` and `("Object storage platform-managed keys", ...)`.

**Commit:** `7ff2d36`
**Tests:** 9/9 pass in `tests/test_dar_storage_scoring.py`; 10/10 pass in `tests/test_intelligence_evidence.py` + `tests/test_intelligence_scoring.py` (no regressions)

### Task 2: Extend cbom/builder.py Pass 1/2/3 skip-lists for S3 and AZURE_BLOB

Three coordinated edits in `quirk/cbom/builder.py` (T-28-20 mitigation — explicit skip-list hardens contract against TLS default fall-through):

1. **Pass 1 elif chain** (line 410): `"S3", "AZURE_BLOB"` added to the `("POSTGRESQL", "MYSQL", "RDS")` pass-through — no algorithm registration for storage config findings.
2. **Pass 2 skip tuple** (line 436): `"S3", "AZURE_BLOB"` appended to the certificate component skip list — no cert info on storage rows.
3. **Pass 3 skip tuple** (line 516): `"S3", "AZURE_BLOB"` appended to the protocol properties skip list — not TLS/SSH network protocols.

**Commit:** `eaf43c7`
**Tests:** 30/30 pass in `tests/test_cbom_builder.py` (no regressions)

### Task 3: MinIO chaos lab — Docker Compose storage-s3 profile + seed script + expected_results.md

**quantum-chaos-enterprise-lab/storage/minio-seed.sh** — New executable init script:
- `mc alias set local http://minio:9000 minioadmin minioadmin`
- `mc mb local/encrypted-bucket --ignore-existing`
- `mc mb local/unencrypted-bucket --ignore-existing`
- `mc encrypt set sse-s3 local/encrypted-bucket` — SSE-S3 on encrypted-bucket (no-finding path)
- `unencrypted-bucket` left without encryption (HIGH finding path)

**quantum-chaos-enterprise-lab/docker-compose.yml** — Two new services appended before `volumes:` section under profile `"storage-s3"` (distinct from existing `"storage"` profile per Pitfall 3):
- `minio`: `minio/minio:latest`, ports 29000:9000 + 29001:9001, `MINIO_ROOT_USER=minioadmin`, healthcheck via `mc ready local`
- `minio-seed`: `minio/mc:latest`, `restart: "no"`, `depends_on: minio.service_healthy`, seed script mounted read-only (`T-28-18`)

**labs/storage/expected_results.md** — New file documenting:
- Lab setup (docker compose --profile storage-s3 up -d)
- Expected scan output table (2 S3 rows with service_detail + severity)
- Expected evidence/scoring impact (dar_storage_unencrypted_count=1, driver "Object storage unencrypted")
- Expected CBOM output (no algorithm/cert/protocol components for S3 rows)
- Teardown and limitations (SSE-KMS deferred, Azure/GCS require live credentials)

**Commit:** `199ee43`
**Tests:** 3/3 static tests pass in `tests/test_chaos_storage.py`; 2 live Docker tests skip (QUIRK_RUN_DOCKER_IT not set)

### Task 4: Update docs/UAT-SERIES.md with Phase 28 UAT cases

**docs/UAT-SERIES.md** — Three new UAT cases added after UAT-5-25 in a new "Phase 28: Object Storage Audit" section:

- **UAT-28-01**: S3 chaos lab end-to-end — MinIO bucket encryption scan via `storage-s3` profile; validates 2 S3 CryptoEndpoint rows, HIGH unencrypted finding, no OperationNotPageableError, dar_storage_unencrypted_count == 1
- **UAT-28-02**: Azure Blob live subscription scan — validates BLOB/platform-managed (MEDIUM) and BLOB/cmk (no finding) key source ladder against real Azure subscription (manual-only)
- **UAT-28-03**: GCS reuse zero-API-call invariant — validates `gcs_storage_reuse` phase block runs without issuing a second `storage.buckets.list` call (manual-only, requires live GCP project)

`**Last Updated:**` header updated to reflect Phase 28 additions.

**Commit:** `0032953`

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

| File | Tests | Status | Requirement |
|------|-------|--------|-------------|
| tests/test_dar_storage_scoring.py | 9/9 | GREEN | D-09, D-10 |
| tests/test_chaos_storage.py | 3/3 pass, 2/2 skip | GREEN (static) | D-08 |
| tests/test_intelligence_evidence.py | 6/6 | GREEN (regression) | — |
| tests/test_intelligence_scoring.py | 4/4 | GREEN (regression) | — |
| tests/test_cbom_builder.py | 30/30 | GREEN (regression) | — |

**Phase 28 total (across all 3 plans):**

| File | Tests | Status | Requirement |
|------|-------|--------|-------------|
| tests/test_s3_encryption.py | 10/10 | GREEN | STOR-01 |
| tests/test_azure_blob.py | 7/7 | GREEN | STOR-02 |
| tests/test_gcs_reuse.py | 5/5 | GREEN | STOR-03 |
| tests/test_dar_storage_scoring.py | 9/9 | GREEN | D-09, D-10 |
| tests/test_chaos_storage.py | 3 pass + 2 skip | GREEN | D-08 |
| **Total** | **34 pass, 2 skip** | **GREEN** | — |

**Pre-existing failure (not caused by this plan):**
- `tests/test_cli_correctness.py::test_version_consistency` — PLATFORM_VERSION 4.3.0 vs expected 4.2.0; pre-existing since Phase 27 (documented in 28-02-SUMMARY.md)

## ROADMAP Success Criterion 5 — Protocol Name Mismatch Note

ROADMAP.md item 5 states: `protocol="STORAGE"` for the new storage protocol value.

The locked decisions D-05/D-06 in `28-CONTEXT.md` specify `protocol="S3"` for S3 findings and `protocol="AZURE_BLOB"` for Azure Blob findings (not a generic `"STORAGE"` value). Plans 02 and 03 implement the locked decisions. The ROADMAP success criterion text contains an older/draft protocol name. The functional behavior is correct and satisfies the intent. The orchestrator may update the ROADMAP.md success criteria text in a follow-up commit if desired.

## Mandatory Phase Completion Steps (remaining for orchestrator per CLAUDE.md)

1. **Create Obsidian phase note** at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-28-Object-Storage-Audit.md`
2. **UAT-SERIES.md already updated** (Task 4 of this plan)
3. **Sync UAT-SERIES.md to Obsidian vault**:
   ```bash
   printf "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/UAT-SERIES.md\nupdated: 2026-04-25\n---\n\n" > /tmp/uat_vault.md
   cat docs/UAT-SERIES.md >> /tmp/uat_vault.md
   cp /tmp/uat_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
   ```
4. **Commit docs/UAT-SERIES.md** (already committed in this plan at `0032953`; orchestrator may re-commit via gsd-tools if needed)

## Known Stubs

None. All production logic is fully implemented per D-09/D-10 severity ladders and CBOM skip-list requirements.

## Threat Flags

None. All files modified are internal intelligence/CBOM processing and developer-only chaos lab infrastructure. No new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED
