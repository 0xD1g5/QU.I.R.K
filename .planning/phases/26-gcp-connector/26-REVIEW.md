---
phase: 26-gcp-connector
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - pyproject.toml
  - quirk/cbom/builder.py
  - quirk/config.py
  - quirk/config_template.yaml
  - quirk/db.py
  - quirk/models.py
  - quirk/scanner/gcp_connector.py
  - run_scan.py
  - tests/test_cloud_connectors.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 26 introduces the GCP connector (`gcp_connector.py`), a DB migration for `gcs_scan_json`, model field additions, config wiring, CBOM routing, and a test suite covering Cloud KMS, Cloud SQL, and GCS scanning.

The implementation is structurally sound. The ADC credential error path is correctly handled at the `google.auth.default()` call site, pagination is properly terminated via `list_next()`, the GCS `items` vs `buckets` field name pitfall is addressed, the sentinel endpoint pattern for Phase 28 hand-off is in place, and the SQL migration uses inspector-first idempotency.

Four warnings need attention before this phase is marked complete:

1. **SQL injection risk in column-name interpolation** in `db.py` (low exploitability in practice but architecturally incorrect — column names should never be interpolated into raw SQL from a mutable Python list).
2. **`CLOUD_SQL` cert_pubkey_alg carries severity strings ("HIGH"/"MEDIUM"), not algorithm names** — the CBOM builder registers these verbatim as algorithm component names, producing semantically incorrect CBOM output.
3. **`CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` keys emit an `UNKNOWN` endpoint** that is inserted into the database without filtering, potentially producing noise in reports.
4. **`_build_gcp_mock_service()` does not terminate pagination for `list_next` at all call sites** — a mock wiring gap that could mask an infinite-loop regression in pagination paths.

No critical (security, data-loss, crash) issues were found.

---

## Warnings

### WR-01: SQL injection via column-name string interpolation in db.py migration

**File:** `quirk/db.py:56` and `quirk/db.py:75`

**Issue:** Both `_ensure_identity_columns()` and `_ensure_gcp_columns()` build ALTER TABLE statements by interpolating column names from Python lists directly into an f-string, then executing them with `text()`:

```python
conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
```

SQLAlchemy's `text()` does not provide parameter binding for DDL identifiers. If a future developer adds a column name to `_IDENTITY_COLUMNS` or `_GCP_COLUMNS` that contains an injection payload (e.g., pulled from a config source, environment variable, or generated string), this becomes exploitable. The column names are currently hard-coded literals so the immediate risk is low, but the pattern is architecturally wrong and should be corrected.

**Fix:** Use `sqlalchemy.sql.expression.quoted_name` or a static allowlist validator before interpolation. Alternatively, enforce that column names match a strict `[a-z_]+` pattern before executing:

```python
import re

_SAFE_COL_RE = re.compile(r'^[a-z][a-z0-9_]*$')

for col in _GCP_COLUMNS:
    if not _SAFE_COL_RE.match(col):
        raise ValueError(f"Unsafe column name in migration: {col!r}")
    if col not in existing:
        conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
```

This eliminates the injection surface entirely for this migration pattern without requiring a third-party DDL library.

---

### WR-02: CBOM builder registers Cloud SQL severity strings as algorithm components

**File:** `quirk/cbom/builder.py:388-391`

**Issue:** Cloud SQL endpoints store a severity level string (`"HIGH"` or `"MEDIUM"`) in `cert_pubkey_alg` (set in `gcp_connector.py:253`). The CBOM builder's Pass 1 CLOUD_SQL branch unconditionally calls `_register_algorithm()` on whatever value is in `cert_pubkey_alg`:

```python
elif ep.protocol == "CLOUD_SQL":
    # Cloud SQL TLS finding -- cert_pubkey_alg holds severity level (HIGH/MEDIUM)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, ...)
```

This emits CBOM algorithm components named `"HIGH"` and `"MEDIUM"`, which are not cryptographic algorithm names. They will appear in the CycloneDX output under `components[].cryptoProperties.assetType=algorithm` with `name="HIGH"`, producing invalid CBOM content. Any downstream consumer parsing the CBOM by algorithm name will receive corrupted data.

**Fix:** Cloud SQL findings describe a TLS configuration posture, not a specific algorithm. The correct approach is to skip algorithm registration for CLOUD_SQL endpoints entirely in Pass 1 (their value is already captured in `cloud_scan_json`), or emit a well-known placeholder such as `"TLS-PLAINTEXT-ALLOWED"` that is documented as a synthetic finding type (mirroring the DNSSEC pattern that filters out `"NONE"`, `"NSEC"`, etc.):

```python
elif ep.protocol == "CLOUD_SQL":
    # Cloud SQL findings encode severity, not algorithm names — skip algorithm registration.
    # The finding detail is available in cloud_scan_json for report consumers.
    pass
```

---

### WR-03: KMS keys with CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED are emitted as endpoints

**File:** `quirk/scanner/gcp_connector.py:169-195`

**Issue:** When a GCP KMS key has algorithm `"CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED"` (or an algorithm string not present in `GCP_KMS_ALGORITHM_MAP`), the fallback returns `(algorithm or "UNKNOWN", None)` and the connector emits a `CryptoEndpoint` with `cert_pubkey_alg="UNKNOWN"`. This endpoint is inserted into the database and included in CBOM output, creating noise in reports and the CBOM.

The `GCP_KMS_ALGORITHM_MAP` explicitly maps `"CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED"` to `("UNKNOWN", None)`, making this a known-bad case that should be filtered rather than surfaced.

```python
alg_name, key_size = GCP_KMS_ALGORITHM_MAP.get(
    algorithm, (algorithm or "UNKNOWN", None)
)
# alg_name may be "UNKNOWN" here — no guard follows
ep = CryptoEndpoint(...)  # emitted unconditionally
```

**Fix:** Filter `"UNKNOWN"` algorithm keys before emitting an endpoint, or log them at verbose level and skip:

```python
if alg_name == "UNKNOWN":
    if logger:
        logger.v(f"Cloud KMS key {key_name} has unspecified algorithm -- skipped")
    continue
```

---

### WR-04: Mock service does not terminate all list_next() paths in test helper

**File:** `tests/test_cloud_connectors.py:116-151`

**Issue:** `_build_gcp_mock_service()` sets `list_next.return_value = None` for the KMS location, keyRing, and cryptoKey pagination paths, and for Cloud SQL instances. However, it does not set `list_next` for the `keyRings` resource at the `locations()` level vs. at the `keyRings()` level — the mock chains through MagicMock for several nested attribute lookups. If the connector ever calls a `list_next` path that was not explicitly wired to `None`, MagicMock auto-creates a truthy return value, causing an infinite pagination loop in the test.

Specifically, the nested call in `_scan_kms`:

```python
kr_request = service.projects().locations().keyRings().list_next(
    previous_request=kr_request, previous_response=kr_response
)
```

The mock wires:
```python
svc.projects.return_value.locations.return_value.keyRings.return_value.list_next.return_value = None
```

But each call to `.projects()`, `.locations()`, `.keyRings()` returns a fresh `MagicMock()` unless the `return_value` chain is followed exactly. Since the tests pass today, the chain happens to resolve correctly for the currently configured mock paths — but any new pagination path added to the connector (e.g., a future `cryptoKeyVersions` sub-list) would silently create an auto-truthy mock and loop until timeout.

**Fix:** Add explicit `assert` checks at the end of KMS-exercising tests to confirm `list_next` was called with the correct previous-response arguments, or restructure the mock to use `spec=` on the service object to prevent auto-attribute creation:

```python
# At the end of test_gcp_kms_algorithm_mapping:
# Confirm pagination terminated (list_next called exactly once per level and returned None)
(mock_service.projects.return_value.locations.return_value
 .keyRings.return_value.list_next.assert_called_once())
```

---

## Info

### IN-01: `CMEK` and `Google-Managed` values also reach the CBOM builder as algorithm names

**File:** `quirk/cbom/builder.py:385`

**Issue:** GCS per-bucket endpoints (protocol `"GCP"`) with `cert_pubkey_alg` set to `"CMEK"` or `"Google-Managed"` are registered as algorithm components via the Pass 1 `GCP` branch (line 385). These are encryption posture labels, not algorithm names. The GCS-SUMMARY sentinel is explicitly excluded via `not in ("GCS-SUMMARY",)`, but `"CMEK"` and `"Google-Managed"` are not excluded. They will appear as algorithm entries in the CBOM.

This is lower severity than WR-02 (they are not misleading in the same way — CMEK could be argued as an algorithm category), but the comment on line 384 only mentions GCS-SUMMARY and does not document that CMEK/Google-Managed also pass through. Consider either extending the exclusion list or documenting the intentional behavior.

---

### IN-02: `google-cloud-kms` not listed as optional dependency for GCP connector

**File:** `pyproject.toml:44-47`

**Issue:** The `[cloud]` extras group lists only `google-api-python-client` and `google-auth`. The `gcp_connector.py` module uses `googleapiclient.discovery.build` (from `google-api-python-client`) and `google.auth` (from `google-auth`), which are present. However, `google-api-python-client` uses `httplib2` under the hood — if users install the `[cloud]` extra but not `httplib2`, service discovery will fail at runtime with an obscure `ImportError`. Consider adding `httplib2>=0.22.0` to the `[cloud]` extras or verifying that `google-api-python-client` pulls it transitively.

This is informational — verify the transitive dep chain before shipping to avoid a confusing install-time gap.

---

### IN-03: `gcp_project_id` passed as empty string from run_scan.py; connector validates it

**File:** `run_scan.py:469-472`

**Issue:** `run_scan.py` passes `cfg.connectors.gcp_project_id or ""` to `scan_gcp_targets()`. The connector correctly guards against an empty `project_id` at line 359. However, `ConnectorsCfg.gcp_project_id` is typed `Optional[str]` and defaults to `None`. If a user sets `gcp_project_id: ""` in config (an empty string, not omitted), `config_from_dict` will pass the empty string through to `ConnectorsCfg`, `run_scan.py` will pass `""` to the connector, and scanning will be silently skipped with only a verbose-level log message. Users who misconfigure this key with an empty string will see no warning at the info level.

Consider adding an `INFO`-level log at the `run_scan.py` call site when `gcp_project_id` is falsy but `enable_gcp` is `True`:

```python
if cfg.connectors.enable_gcp:
    if not cfg.connectors.gcp_project_id:
        logger.info("WARNING: enable_gcp=true but gcp_project_id is empty -- GCP scanning skipped")
    gcp_endpoints = scan_gcp_targets(
        project_id=cfg.connectors.gcp_project_id or "",
        logger=logger,
    )
```

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
