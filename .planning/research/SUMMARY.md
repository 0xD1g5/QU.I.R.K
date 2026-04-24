# Project Research Summary

**Project:** QU.I.R.K. v4.3 — Data at Rest Milestone
**Domain:** Cryptographic inventory expansion — cloud KMS, database encryption, object storage, Kubernetes secrets, HashiCorp Vault, trend analysis
**Researched:** 2026-04-24
**Confidence:** HIGH

## Executive Summary

QU.I.R.K. v4.3 extends the existing cryptographic scanner with six new data-at-rest surfaces: a GCP connector (Cloud KMS + Cloud SQL + GCS), database encryption detection (RDS + self-hosted PostgreSQL/MySQL), object storage audit (S3 + Azure Blob + GCS), Kubernetes secrets inspection (etcd EncryptionConfiguration), a HashiCorp Vault connector (transit keys + PKI + auth), and cross-session trend analysis. All six surfaces integrate through the same scanner contract already established by `aws_connector.py` and `azure_connector.py`, meaning the architecture is well-understood and low-risk. The primary unknown is not the architecture — it is operational: privilege requirements for database probing, GCP ADC runtime failures, and K8s RBAC restrictions are all failure modes that do not surface in unit tests but break in real consultant engagements.

The recommended approach groups the six surfaces into seven phases (25–31), ordered strictly by dependency. Phase 27 (database encryption) is the critical path: it introduces the `dat_scan_json` column and `_ensure_v43_columns()` migration that every subsequent non-cloud scanner depends on. GCP and object storage share GCS bucket enumeration and must be developed together or in sequence to prevent double-enumeration. Trend analysis comes last and is purely additive — it reads existing `CryptoEndpoint` rows and requires no schema change beyond what Phase 27 already delivers. The stack delta is 7 net-new optional dependencies across 3 new extras groups (`[cloud]`, `[db]`, `[identity]` extension); zero core dependencies change.

The two highest risks for v4.3 are exact repeats of v4.2 defects: ISSUE-2 (dependency declared in scanner module but missing from pyproject.toml) and ISSUE-3 (scanner calling `datetime.now()` instead of receiving `session_start`). Both must be treated as structural requirements on every scanner phase, not afterthoughts. A third new risk class — GCP ADC runtime exception (`DefaultCredentialsError`) — requires explicit exception handling in the GCP connector because it is a runtime auth failure, not an import failure, and therefore bypasses the `GCP_AVAILABLE` flag pattern used for all other SDKs.

---

## Key Findings

### Recommended Stack

The v4.3 stack delta is minimal and well-justified. All 7 net-new libraries are pip-installable with stable GA releases, and all go into optional extras groups — zero changes to the core install. GCP libraries (`google-cloud-kms>=3.12.0`, `google-cloud-storage>=3.10.1`) pull `grpcio` and `protobuf` transitively and carry a known `protobuf 6.x` conflict with `grpcio-status` — this is the single hardest install constraint and mandates they stay in `[cloud]` extras. `hvac>=2.4.0` (Vault) and `kubernetes>=35.0.0` also belong in `[cloud]` for the same reason: they are heavy, optional, and credential-gated. `psycopg2-binary>=2.9.12` and `PyMySQL>=1.1.2` go into the new `[db]` extras group. `ldap3>=2.9.1` is the Phase 25 carry-over fix — a one-liner addition to the existing `[identity]` group.

**Core technologies (net-new):**
- `google-cloud-kms>=3.12.0` + `google-cloud-storage>=3.10.1`: GCP KMS and GCS enumeration — first-party typed clients, shared ADC credential, goes in `[cloud]` extras to avoid grpcio landmine
- `azure-mgmt-storage>=21.2.0`: Azure Blob encryption audit — mirrors `azure-mgmt-network` already in stack; `DefaultAzureCredential` reused; placement in `[cloud]` vs core is an open decision (see Gaps)
- `hvac>=2.4.0`: HashiCorp Vault connector — only maintained Python Vault client, `requests` is already transitive, goes in `[cloud]`
- `kubernetes>=35.0.0`: K8s secrets inspection — official OpenAPI-generated client, tracks K8s 1.32, goes in `[cloud]`; 25MB+ weight reinforces extras placement
- `psycopg2-binary>=2.9.12`: PostgreSQL encryption probe — self-contained binary wheel, no system deps, goes in `[db]`
- `PyMySQL>=1.1.2`: MySQL encryption probe — pure Python, MIT license, goes in `[db]`
- `ldap3>=2.9.1`: Phase 25 KERB-03 LDAP path — pure Python, one-liner addition to `[identity]`

**K8s critical finding:** `EncryptionConfiguration` is NOT a Kubernetes API resource. The only agentless detection path is inspecting the kube-apiserver pod spec in `kube-system` for the `--encryption-provider-config` flag. Managed clusters (EKS, GKE, AKS) each expose this through their own cloud API (`describe_cluster`, `get_cluster`, `ManagedCluster`) — three distinct API call paths, not one.

**RDS precision finding:** The 2025 Aurora field `StorageEncryptionType` (`none`/`sse-rds`/`sse-kms`) is more precise than the older `StorageEncrypted` boolean. Both should be read: `StorageEncrypted=True` with `StorageEncryptionType=sse-rds` means AWS-owned key (weaker posture than CMK).

**Vault PQC positive finding:** HashiCorp Vault transit engine supports `ml-dsa` and `slh-dsa` key types (experimental PQC). These are surfaceable as positive findings in QU.I.R.K.'s CBOM — orgs already using these are ahead on post-quantum readiness.

---

### Expected Features

All 6 surfaces have clear table-stakes definitions confirmed against official docs. The feature prioritization matrix assigns P1 to the highest-value, lowest-complexity items.

**Must have (P1 — ships in v4.3 core):**
- GCP Cloud KMS key enumeration + algorithm map + GCS CMEK detection — shares GCS work with object storage audit
- AWS RDS `StorageEncrypted` + `StorageEncryptionType` (2025 field) + `KmsKeyId` detection
- S3 encryption policy (SSE-S3 vs SSE-KMS vs CMK) + public access block (4 boolean flags)
- EKS `encryptionConfig` + GKE `databaseEncryption.state` + kube-apiserver pod spec inspection
- HashiCorp Vault transit key enumeration + type map + PKI CA cert extraction + auth method list
- Trend analysis: `ScanSession` table + score delta + new/resolved findings diff + HTML/PDF delta section

**Should have (P2 — ships if time permits, else v4.3.x):**
- K8s secret type count (self-managed clusters) — requires `list secrets` RBAC
- Azure Blob `key_source` detection (CMK vs platform-managed)
- S3 Object Lock / MFA Delete status
- Vault transit `exportable` flag detection
- Trend analysis dashboard delta badge

**Defer (P3 / v4.4+):**
- Azure SQL TDE detection, PostgreSQL pg_tde extension, AKS CMK encryption, BigQuery CMEK audit, multi-session trend chart, Vault Enterprise namespaces, Oracle DB encryption (explicitly out of scope v4.3)

**Important scope constraint:** GCP connector and object storage audit MUST share GCS bucket enumeration. Enumerating GCS twice is wasteful and violates session consistency. Phase 26 enumerates; Phase 28 consumes that data.

---

### Architecture Approach

All six new surfaces follow the scanner contract established by `aws_connector.py`: one public `scan_X_targets(...) -> List[CryptoEndpoint]` function per module, optional SDK import guard at module level, `protocol` string discriminator on the endpoint, raw detail in a JSON blob column. GCP reuses the existing `cloud_scan_json` column (protocol `"GCP"`, same as AWS/Azure). The four non-cloud surfaces (DATABASE, STORAGE, K8S, VAULT) share a new `dat_scan_json` TEXT column added by `_ensure_v43_columns()` in Phase 27 — this column is the critical-path dependency for Phases 28, 29, and 30. Trend analysis (`intelligence/trends.py`) is a pure read concern over existing `CryptoEndpoint` rows; it requires no new table, using the `scanned_at`-based session grouping already used by `list_scans()`. The evidence-to-scoring pipeline adds a `dar_` subscore prefix following the `identity_` prefix pattern established in v4.2.

**Major components (7 new files):**
1. `quirk/scanner/gcp_connector.py` — Cloud KMS, Cloud SQL TLS, GCS encryption enumeration
2. `quirk/scanner/db_scanner.py` — PostgreSQL/MySQL/RDS encryption-at-rest detection
3. `quirk/scanner/object_storage_scanner.py` — S3/Azure Blob/GCS bucket encryption policies
4. `quirk/scanner/k8s_scanner.py` — etcd EncryptionConfiguration + secret type inventory
5. `quirk/scanner/vault_connector.py` — Vault transit keys, PKI mounts, auth method audit
6. `quirk/intelligence/trends.py` — cross-session delta computation
7. `quirk/dashboard/api/routes/trends.py` — `GET /api/trends` FastAPI route

**Extended files (11 files, additive changes only):** `quirk/models.py`, `quirk/db.py`, `quirk/config.py`, `quirk/intelligence/evidence.py`, `quirk/intelligence/scoring.py`, `quirk/cbom/builder.py`, `quirk/cbom/classifier.py`, `quirk/dashboard/api/schemas.py`, `quirk/dashboard/api/routes/scan.py`, `quirk/dashboard/api/app.py`, `run_scan.py`.

**Breaking API decision:** `dar_` weights must be added as a 5th subscore prefix in `scoring.py` (parallel to `identity_`), NOT by extending the existing `identity_trust` subscore. This keeps surface scoring separable for future per-surface dashboard breakdowns and profile multiplier targeting.

---

### Critical Pitfalls

1. **ISSUE-2 repeat — dependency declared nowhere** — Every new connector (hvac, kubernetes, google-cloud-kms, psycopg2-binary, PyMySQL) must be added to pyproject.toml in the same commit as the scanner module. Treat pyproject.toml diff as a required PLAN.md deliverable. Write a test that checks `importlib.util.find_spec()` for each library under the expected extras configuration.

2. **ISSUE-3 repeat — session timestamp drift** — Every scanner function must accept `session_start: Optional[datetime]` and propagate it to `scanned_at` on all `CryptoEndpoint` instances. Scanners with network latency (Vault token refresh, GCP API rate limits, DB connection timeouts) are highest risk.

3. **GCP ADC runtime exception — new failure class** — `DefaultCredentialsError` fires at API call time, not import time. The `GCP_AVAILABLE` flag alone does not protect against it. Must catch `google.auth.exceptions.DefaultCredentialsError` and `google.auth.exceptions.TransportError` explicitly with actionable log messages.

4. **GCP grpcio/protobuf transitive conflict** — GCP client libraries pull `grpcio` and `protobuf`; a known open issue blocks `protobuf>=6.x` with `grpcio-status`. GCP libraries must stay in `[cloud]` extras only. Run `pip check` in CI after `pip install quirk[cloud]`.

5. **PostgreSQL pg_stat_ssl false-positive** — Querying `pg_stat_ssl` without `pg_read_all_stats` role returns only the scanner's own connection row (always SSL), producing a false "SSL enabled" result. Detect privilege level before querying; emit `insufficient-privilege` scan_error if absent.

6. **S3 `list_buckets` is not paginated** — `get_paginator('list_buckets')` raises `OperationNotPageableError`. Per-bucket encryption calls must use `ThreadPoolExecutor(max_workers=10)` with the existing `TokenBucket` rate limiter.

7. **Trend analysis NULL collision with v4.2-era scan data** — Pre-v4.3 scan rows lack `dat_scan_json`. Trend queries across v4.2-era data must limit comparison to fields present in both sessions. Every DAR finding will appear as "new" in the first post-v4.3 trend comparison — correct behavior, must be documented.

---

## Implications for Roadmap

Phases 25–31. Build order is driven by the `dat_scan_json` column dependency and the GCS sharing constraint.

### Phase 25: Identity Accuracy (carry-over from v4.2)

**Rationale:** Deferred from v4.2; no v4.3 DAR dependencies; clears the backlog before adding new scope.
**Delivers:** `ldap3>=2.9.1` in `[identity]` extras; LDAP degradation path in Kerberos scanner; OIDC RS256 token validation.
**Addresses:** ISSUE-2 carry-over from v4.2 milestone audit.
**Avoids:** ISSUE-2 repeat — pyproject.toml and scanner module committed atomically.

### Phase 26: GCP Connector

**Rationale:** GCP reuses `cloud_scan_json` (no schema change needed), so it has no dependency on Phase 27. GCS enumeration done here is passed forward to Phase 28 — Phase 26 must precede Phase 28.
**Delivers:** `gcp_connector.py` with Cloud KMS enumeration + `GCP_ALGORITHM_MAP`, Cloud SQL TLS mode, GCS CMEK. `google-cloud-kms` and `google-cloud-storage` in `[cloud]` extras. `azure-mgmt-storage` placement decision.
**Addresses:** GCP KMS P1, GCS CMEK P1, Cloud SQL TLS P1.
**Avoids:** GCP ADC `DefaultCredentialsError` uncaught; grpcio/protobuf conflict; ISSUE-2 and ISSUE-3 repeats.

### Phase 27: Database Encryption Detection (CRITICAL PATH)

**Rationale:** Introduces `dat_scan_json` column and `_ensure_v43_columns()`. Phases 28, 29, 30 all depend on this column. Establishes `dar_` subscore prefix. Must come before all non-cloud DAR scanner phases.
**Delivers:** `db_scanner.py` with RDS `StorageEncrypted`/`StorageEncryptionType`/`KmsKeyId`; `rds.force_ssl` parameter group check; PostgreSQL `pg_stat_ssl` probe; MySQL `have_ssl` + `require_secure_transport`. `psycopg2-binary` and `PyMySQL` in `[db]` extras. `dat_scan_json` column + migration.
**Addresses:** AWS RDS P1; PostgreSQL/MySQL self-hosted P2.
**Avoids:** `pg_stat_ssl` false-positive (privilege detection first); ISSUE-2 and ISSUE-3 repeats.

### Phase 28: Object Storage Audit

**Rationale:** Depends on `dat_scan_json` from Phase 27. Receives GCS bucket data from Phase 26 (not re-enumerated).
**Delivers:** `object_storage_scanner.py` with S3 SSE-S3/SSE-KMS/CMK + public access block + Object Lock; Azure Blob `key_source`; GCS CMEK via shared Phase 26 data.
**Addresses:** S3 encryption P1, S3 public access P1, Azure Blob P2.
**Avoids:** `list_buckets` paginator error; sequential per-bucket loop (ThreadPoolExecutor from day one); ISSUE-3 repeat.

### Phase 29: Kubernetes Secrets Inspection

**Rationale:** Depends on `dat_scan_json` from Phase 27. Independent of Phases 26/28. Can be developed in parallel with Phase 28 post-Phase 27.
**Delivers:** `k8s_scanner.py` with EKS `encryptionConfig`; GKE `databaseEncryption.state`; kube-apiserver pod spec inspection; secret type count. `kubernetes>=35.0.0` in `[cloud]` extras.
**Addresses:** EKS/GKE etcd encryption P1; K8s secret type count P2.
**Avoids:** K8s EncryptionConfiguration API misconception (pod spec, not API resource); K8s RBAC 403 silent failure; `secret.data` decoded values never logged.

### Phase 30: HashiCorp Vault Connector

**Rationale:** Depends on `dat_scan_json` from Phase 27. No dependency on Phases 28 or 29.
**Delivers:** `vault_connector.py` with transit key enumeration + `VAULT_TRANSIT_KEY_MAP`; PKI CA cert extraction; auth method list; `ml-dsa`/`slh-dsa` PQC positive finding. `hvac>=2.4.0` in `[cloud]` extras.
**Addresses:** Vault transit P1, Vault PKI P1, auth method list P2, PQC positive finding.
**Avoids:** Vault key type mapping error (must be `"RSA"` not `"rsa-2048"`); KV v1/v2 auto-detection failure; `keys[version]` timestamp confusion as `cert_pubkey_size`.

### Phase 31: Trend Analysis

**Rationale:** Must come last — requires scan data from all scanner phases. Purely additive read-side feature; no schema change needed.
**Delivers:** `quirk/intelligence/trends.py` with `compute_trend_report()`; `GET /api/trends` route; HTML/PDF delta section; React Trends tab (score delta badge minimum viable).
**Addresses:** Trend score delta P1, new/resolved findings diff P2, dashboard delta badge P2.
**Avoids:** NULL collision with v4.2-era data (document expected behavior); timestamp drift breaking session grouping; write-time delta computation (compute at query time only).

---

### Phase Ordering Rationale

- Phase 25 first: carry-over with no DAR dependency; clears backlog before adding new scope.
- Phase 26 before Phase 28: GCP connector enumerates GCS buckets; object storage audit reuses that data. Reversing the order means double-enumeration or re-architecture.
- Phase 27 before Phases 28/29/30: `dat_scan_json` column and `_ensure_v43_columns()` are shared infrastructure. Phases 28, 29, 30 are independent of each other once Phase 27 completes — parallel development is possible.
- Phase 31 last: trend analysis on zero or partial data is meaningless; all scanner surfaces must produce at least one scan session before trend output is useful.

---

### Research Flags

**No phases require a `/gsd-research-phase` call.** All patterns, library APIs, integration shapes, and pitfall mitigations are fully specified at HIGH confidence across the four research files.

**All phases use standard patterns:**
- Phase 25: one-liner ldap3 addition to existing extras group
- Phase 26: mirrors aws_connector.py exactly; library APIs confirmed
- Phase 27: existing boto3 session; pg_stat_ssl and MySQL queries documented
- Phase 28: S3/Blob/GCS APIs standard; ThreadPoolExecutor pattern established
- Phase 29: K8s pod spec inspection path fully documented in official K8s docs
- Phase 30: hvac API shape confirmed; VAULT_TRANSIT_KEY_MAP fully specified
- Phase 31: session grouping uses existing `list_scans()` pattern; no new DB patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 7 library versions verified via PyPI as of 2026-04-24; grpcio/protobuf conflict is a known open issue with documented workaround |
| Features | HIGH | GCP/AWS/Azure/K8s/Vault official docs verified; codebase patterns confirmed via direct code analysis |
| Architecture | HIGH | Based on direct codebase analysis; all integration points specified with file names and function signatures |
| Pitfalls | HIGH | ISSUE-2 and ISSUE-3 patterns derived from v4.2 milestone audit; GCP ADC, pg_stat_ssl, K8s RBAC, S3 pagination pitfalls confirmed against official library docs |

**Overall confidence:** HIGH

### Gaps to Address

- **`azure-mgmt-storage` placement:** `azure-mgmt-network` is currently in core deps. If `azure-mgmt-storage` joins it in core, placement is consistent but adds mgmt-plane weight to all installs. If moved to `[cloud]`, more principled but inconsistent with `azure-mgmt-network`. Decide in Phase 26/28 PLAN.md and document as a key decision in PROJECT.md.

- **GCS sharing implementation mechanism:** `gcp_connector.py` and `object_storage_scanner.py` must share GCS bucket enumeration results. Whether this is a shared return value, a cached singleton, or explicit pass-through in `run_scan.py` is unspecified. Needs design decision before Phase 28 begins.

- **`ScanSession` table vs. `scanned_at`-based grouping:** FEATURES.md calls for a new `ScanSession` table; ARCHITECTURE.md concludes no new table is needed (use existing `scanned_at` grouping). The no-new-table approach is stronger and should be adopted for Phase 31, confirmed in the Phase 31 PLAN.md.

- **React Trends tab scope:** Minimum viable (score delta badge) vs. full Trends tab with sparklines. Phase 31 planning should define which deliverable is in scope.

---

## Sources

### Primary (HIGH confidence)

- `google-cloud-kms` PyPI (v3.12.0, 2026-03-26), `google-cloud-storage` PyPI (v3.10.1, 2026-03-23)
- Google Cloud KMS Python docs — `KeyManagementServiceClient`, `CryptoKeyVersion.algorithm` enum
- `hvac` PyPI (v2.4.0, 2025-10-30) + python-hvac.org — transit/PKI/sys API shape
- `kubernetes` PyPI (v35.0.0, 2026-01-16) — K8s 1.32 target
- kubernetes.io — EncryptionConfiguration is not a queryable API resource; pod spec inspection is canonical
- `psycopg2-binary` PyPI (v2.9.12, 2026-04-20), `PyMySQL` PyPI (v1.1.2, 2025-08-24)
- `ldap3` PyPI — v2.9.1 stable; v2.10.2rc4 pre-release only
- boto3 RDS `describe_db_instances` docs — `StorageEncrypted`, `StorageEncryptionType` (2025 Aurora field), `KmsKeyId`
- google-auth exceptions docs — `DefaultCredentialsError`, `TransportError` types
- googleapis/google-cloud-python issue #13874 — grpcio-status protobuf 6.x conflict (open as of 2025)
- QUIRK v4.2 Milestone Audit Report (`.planning/v4.2-MILESTONE-AUDIT.md`) — ISSUE-2, ISSUE-3 root cause
- Direct codebase analysis: `quirk/scanner/aws_connector.py`, `azure_connector.py`, `kerberos_scanner.py`, `quirk/models.py`, `quirk/db.py`, `quirk/intelligence/evidence.py`, `scoring.py`, `quirk/cbom/builder.py`, `classifier.py`, `quirk/dashboard/api/routes/scan.py`, `quirk/config.py`, `pyproject.toml`

### Secondary (MEDIUM confidence)

- PostgreSQL docs — `pg_read_all_stats` role requirement for cross-session `pg_stat_ssl` visibility
- AWS S3 boto3 docs — `s3:GetEncryptionConfiguration`; `list_buckets` not paginated
- HashiCorp Vault Transit API docs — `keys` object Unix timestamps; `type` field values; KV v1/v2 coexistence
- Kubernetes secrets RBAC docs — `list` vs `get`; namespace scope restrictions

### Tertiary (LOW confidence)

- `azure-mgmt-storage>=21.2.0` version — confirmed approximately March 2026 via WebSearch; exact PyPI release date not verified
- GCP Cloud SQL TLS field — `ssl_mode` via `sqladmin_v1beta4` Discovery API; not independently verified in STACK.md (STACK.md covers KMS/GCS only)

---

*Research completed: 2026-04-24*
*Ready for roadmap: yes*
