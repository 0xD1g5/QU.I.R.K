---
phase: 28-object-storage-audit
reviewed: 2026-04-25T21:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - docs/UAT-SERIES.md
  - labs/storage/expected_results.md
  - pyproject.toml
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/storage/minio-seed.sh
  - quirk/cbom/builder.py
  - quirk/config_template.yaml
  - quirk/config.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - quirk/scanner/aws_connector.py
  - quirk/scanner/azure_connector.py
  - run_scan.py
  - tests/test_azure_blob.py
  - tests/test_chaos_storage.py
  - tests/test_dar_storage_scoring.py
  - tests/test_gcs_reuse.py
  - tests/test_s3_encryption.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-04-25T21:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 28 introduces S3 bucket encryption scanning (`_scan_s3_encryption`), Azure Blob container
encryption scanning (`_scan_blob_encryption`), and a GCS reuse helper
(`_process_gcs_storage_encryption`). The core scanner logic is well-constructed: the S3 severity
ladder (HIGH/MEDIUM/None) is correct, the Azure Blob keySource ladder is correct and
case-insensitive, the CBOM skip-list correctly includes both `S3` and `AZURE_BLOB` in all three
passes, evidence counters are correctly mapped (BLOB/platform-managed increments
`dar_storage_aws_managed_count` not `dar_storage_unencrypted_count`), and the GCS STOR-03
zero-API-call invariant is properly enforced. Protocol values (`"S3"` and `"AZURE_BLOB"`) are
consistent across all files.

One critical runtime crash is present: the new S3, Azure Blob, and GCS scan phase log lines in
`run_scan.py` use `logger.info("...", arg)` printf-style formatting, but `Logger.info()` accepts
only a single string argument. This will raise `TypeError` on every scan run that executes any of
the new Phase 28 phases. Two documentation bugs leave stale v4.2 version references in
`UAT-SERIES.md`. One warning-level code quality issue: `_build_endpoint` inside
`_scan_s3_encryption`'s `ThreadPoolExecutor` is not wrapped in a try/except, so a constructor
failure in any bucket's processing would abort the remaining buckets in the thread pool iteration.

---

## Critical Issues

### CR-01: `logger.info()` called with printf-style extra arguments — crashes at runtime

**File:** `run_scan.py:551`
**Issue:** `Logger.info(self, msg: str)` accepts exactly one argument beyond `self`. Three new
Phase 28 log lines call it with a format string plus positional `%d` arguments, which raises
`TypeError: Logger.info() takes 2 positional arguments but 3 were given`. This crash fires
**after** the scan completes but **before** `write_reports()` is called when any of
`enable_s3`, `enable_blob`, or `enable_gcp` is true with a populated result set.

The same anti-pattern already exists for DNSSEC/SAML/Kerberos phases (lines 592, 606, 620) and
will similarly crash those connectors. Phase 28 introduced three new instances.

**Affected lines:** 551, 571, 580, 592, 606, 620

**Fix:** Use f-strings (consistent with the rest of `run_scan.py`):

```python
# line 551
logger.info(f"S3 scan: {len(s3_endpoints)} bucket endpoints")

# line 571
logger.info(f"Azure Blob scan: {len(blob_endpoints)} container endpoints")

# line 580
logger.info(f"GCS storage re-use: {len(gcs_storage_endpoints)} derived endpoints")

# line 592-593
logger.info(f"DNSSEC scan: {len(dnssec_endpoints)} endpoints from {len(cfg.connectors.dnssec_targets)} targets")

# line 606-607
logger.info(f"SAML scan: {len(saml_endpoints)} endpoints from {len(cfg.connectors.saml_targets)} targets")

# line 620-621
logger.info(f"Kerberos scan: {len(kerberos_endpoints)} endpoints from {len(cfg.connectors.kerberos_targets)} targets")
```

---

## Warnings

### WR-01: `_build_endpoint` not wrapped in try/except inside `ThreadPoolExecutor.map()`

**File:** `quirk/scanner/aws_connector.py:208-227`
**Issue:** The inner `_classify()` function is fully exception-guarded and returns `None` on any
API error. However, `_build_endpoint` itself — which constructs `CryptoEndpoint(...)` and
assigns `ep.severity` — is not wrapped in a try/except. `executor.map()` re-raises the first
exception it encounters when iterating, which would abort processing of all remaining buckets in
the pool and propagate to the outer `except Exception` at line 234, returning only partial
results with no indication which buckets were skipped. While `CryptoEndpoint()` is unlikely to
raise under normal conditions, a SQLAlchemy model validation failure or OOM condition would
silently truncate the bucket list.

**Fix:**
```python
def _build_endpoint(bucket):
    name = bucket.get("Name", "") if isinstance(bucket, dict) else ""
    if not name:
        return None
    try:
        classification = _classify(name)
        if classification is None:
            return None
        ep = CryptoEndpoint(
            host=f"arn:aws:s3:::{name}",
            port=0,
            protocol="S3",
            service_detail=classification["service_detail"],
            dat_scan_json=json.dumps(
                {"bucket": name, **classification}, default=str
            ),
            scanned_at=ts,
        )
        if classification["severity"]:
            ep.severity = classification["severity"]
        return ep
    except Exception as exc:
        if logger:
            logger.v(f"S3 build_endpoint error for {name}: {exc}")
        return None
```

### WR-02: `UAT-SERIES.md` Gate Status and pass criteria reference stale v4.2 version

**File:** `docs/UAT-SERIES.md:6`
**Issue:** The Gate Status line reads "the **release gate** for QU.I.R.K. v4.2" but the project
is now at v4.3.0 (per `pyproject.toml`). Additionally, `UAT-1-02` pass criteria (line 94) still
specifies `quirk 4.2.0` or `QU.I.R.K. v4.2.0` as the expected output, which will cause the test
to appear to fail on a v4.3.0 install even though the version check is passing.

**Fix:**

Line 6 — update gate version:
```
**Gate Status:** This document is the **release gate** for QU.I.R.K. v4.3. All series must meet ...
```

Line 94 — update pass criteria:
```
- Output matches format: `quirk 4.3.0` or `QU.I.R.K. v4.3.0`
```

---

## Info

### IN-01: `test_chaos_storage.py` contains hardcoded MinIO credentials

**File:** `tests/test_chaos_storage.py:52-53, 75-76`
**Issue:** The Docker integration tests hardcode `aws_access_key_id="minioadmin"` and
`aws_secret_access_key="minioadmin"`. These are the canonical public test credentials for the
MinIO chaos lab defined in `docker-compose.yml` (lines 858-859), so this is not a secret leak.
The tests are additionally gated behind the `QUIRK_RUN_DOCKER_IT` environment variable and
`pytestmark = pytest.mark.integration`, preventing accidental execution in CI. No action
required, but a comment referencing `docker-compose.yml` would aid future maintainers.

**Fix (optional):**
```python
# MinIO chaos lab credentials — matches MINIO_ROOT_USER/PASSWORD in docker-compose.yml
session = boto3.Session(
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name="us-east-1",
)
```

### IN-02: `config.py` intelligence_version defaults to "4.2.0" after v4.3 bump

**File:** `quirk/config.py:164`
**Issue:** `config_from_dict()` falls back to `"4.2.0"` when `intelligence_version` is absent
from the config YAML:
```python
intelligence_version=str(intel_raw.get("intelligence_version", "4.2.0") or "4.2.0"),
```
The project is now at v4.3.0 (`pyproject.toml` line 6, `builder.py` PLATFORM_VERSION line 109).
This creates a version skew in the evidence JSON `intelligence_version` field for all users who
do not have `intelligence_version` explicitly set in their config.

**Fix:**
```python
intelligence_version=str(intel_raw.get("intelligence_version", "4.3.0") or "4.3.0"),
```

---

_Reviewed: 2026-04-25T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
