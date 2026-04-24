# Pitfalls Research

**Domain:** Cryptographic scanner — adding GCP, database probing, Kubernetes, HashiCorp Vault, object storage, and trend analysis to an existing Python security scanner
**Researched:** 2026-04-24
**Confidence:** HIGH (patterns derived from v4.2 audit findings + verified library documentation)

---

## Critical Pitfalls

### Pitfall 1: Dependency Declared Nowhere — ISSUE-2 Repeat

**What goes wrong:**
A new connector imports a library inside `try/except ImportError` for graceful degradation, but the library is never added to `pyproject.toml`. The scan silently degrades on every installation. Consultants never see the feature. No error, no log message loud enough to notice, no test that exercises the live code path.

This happened verbatim with `ldap3` in v4.2 (ISSUE-2). The same pattern is likely to recur for every new connector in v4.3: `hvac` for Vault, `kubernetes` for K8s, `google-cloud-kms`/`google-cloud-storage` for GCP, `psycopg2-binary`/`PyMySQL` for database probing.

**Why it happens:**
The graceful degradation pattern (`BOTO3_AVAILABLE = False`) works correctly at runtime but provides no enforcement that the dependency is actually installable. pyproject.toml is edited separately from the scanner module and there is no import-time test that fails RED when the library is missing from a fresh install.

**How to avoid:**
- Add the library to pyproject.toml in the same commit as the scanner module — treat them as one atomic unit.
- For each new connector extras group, write a test that runs `pip show <library>` or checks `importlib.util.find_spec("<library>")` under the expected install configuration. The test should FAIL if the library is not declared.
- Create a new `[cloud]` or `[datastores]` extras group for v4.3 libraries rather than polluting core. GCP libraries in particular bring heavy transitive deps (grpcio, protobuf) that conflict with other packages.

**Warning signs:**
- Graceful-degradation log message fires on every run, even with `[cloud]` extras installed.
- `pip show google-cloud-kms` (or equivalent) fails after `pip install quirk[cloud]`.
- Test coverage shows the `AVAILABLE = True` branch is never exercised.

**Phase to address:** Phase 25 (identity carry-over already adds ldap3) and every phase adding a new library. Each connector phase must include a `pyproject.toml` diff as a required deliverable.

---

### Pitfall 2: Session Timestamp Drift — ISSUE-3 Repeat

**What goes wrong:**
A new scanner calls `datetime.now(timezone.utc)` inside its endpoint constructor loop rather than receiving a shared `session_start` from `run_scan.py`. If the new scanner is slow (database connection timeout, Vault token refresh, GCP API rate limit pause), all endpoints it produces are stamped later than earlier scanners. The `/api/scan/latest` query anchors on `MAX(scanned_at)` within a 1-second window. Endpoints from earlier scanners fall outside the window and are silently excluded from API responses.

This is the exact mechanism of v4.2 ISSUE-3 (Kerberos timing defect). Adding 6 more scanners, several of which involve network round-trips to live services with unpredictable latency, multiplies the probability of this defect.

**Why it happens:**
Scanners are written in isolation. The author uses `datetime.now()` as a natural "when did I scan this?" value, unaware that a 1-second scan-window query downstream assumes all endpoints from a single scan share one timestamp.

**How to avoid:**
- All scanner functions must accept a `session_start: Optional[datetime]` parameter (pattern established in kerberos_scanner.py and v4.2 Phase 24).
- `run_scan.py` captures `session_start = datetime.now(timezone.utc)` once at scan entry and passes it through to every scanner call.
- Every new scanner must propagate `session_start` to `scanned_at` on all `CryptoEndpoint` instances it creates.
- TDD RED test: create a scan with two scanners where the second is artificially delayed; assert that all endpoints share the same `scanned_at` value.

**Warning signs:**
- New scanner function signature omits `session_start` parameter.
- `run_scan.py` call site does not pass `session_start=session_start` to the new scanner.
- Integration test shows fewer endpoints in API response than were written to the database.

**Phase to address:** Every v4.3 phase adding a new scanner. The `session_start` parameter must be part of every scanner's function signature as a design constraint, not an afterthought.

---

### Pitfall 3: GCP ADC Silent Failure — Wrong Exception Caught

**What goes wrong:**
The GCP connector wraps initialization in a broad `except Exception` and returns an empty list. When Application Default Credentials are absent (no `GOOGLE_APPLICATION_CREDENTIALS` env var, no `gcloud auth application-default login`, no attached service account), the library raises `google.auth.exceptions.DefaultCredentialsError`. If the except block does not log this specifically, the scan returns zero GCP results with no actionable error message. The consultant assumes GCP is not configured rather than that their credentials are missing.

Secondary failure: `google.auth.exceptions.TransportError` fires when network access to the GCP metadata server fails in air-gapped environments. This is a different exception class requiring separate handling.

**Why it happens:**
The AWS and Azure connectors use `BOTO3_AVAILABLE` / `AZURE_AVAILABLE` flags to degrade when the SDK is not installed. GCP credentials are a runtime problem, not an import problem — the SDK imports fine but fails on first API call. The established pattern does not cover runtime auth failures.

**How to avoid:**
- Import `google.auth.exceptions` at module level within the `try/except ImportError` block.
- In the scan function, catch `google.auth.exceptions.DefaultCredentialsError` explicitly and log: "GCP credentials not found — run `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS."
- Catch `google.auth.exceptions.TransportError` separately and log: "GCP metadata server unreachable — expected in air-gapped environments."
- Both exceptions must degrade gracefully (return empty list), but must log the specific cause.

**Warning signs:**
- Connector returns empty list with no log message when run without GCP credentials.
- `GOOGLE_APPLICATION_CREDENTIALS` is unset and the connector does not emit any warning.
- Air-gapped test environment produces unhandled `TransportError`.

**Phase to address:** GCP connector phase.

---

### Pitfall 4: GCP grpcio/protobuf Transitive Conflict With Core Dependencies

**What goes wrong:**
`google-cloud-kms`, `google-cloud-storage`, and other GCP client libraries pull in `grpcio`, `grpcio-status`, and `protobuf` as transitive dependencies. As of 2025, `grpcio-status` does not allow protobuf 6.x (confirmed open issue in the google-cloud-python repository). Installing GCP libraries alongside other grpc-using packages (or after upgrading protobuf) can silently downgrade shared packages or produce `pkg_resources.VersionConflict` errors at import time.

If GCP libraries are placed in core `dependencies`, every `pip install quirk` will install these heavy transitive deps regardless of whether GCP scanning is needed. This contradicts QUIRK's lightweight core-install principle (established by impacket being placed in `[identity]` extras only).

**Why it happens:**
GCP Python libraries are structured to require gRPC because the underlying APIs use gRPC transport. The packaging team assumed gRPC would always be available. Placing GCP libraries in core breaks offline or air-gapped installs with slow package resolution.

**How to avoid:**
- Place ALL GCP libraries (`google-cloud-kms`, `google-cloud-storage`) in a `[cloud]` extras group — do not add them to core `dependencies`.
- Pin protobuf to a range compatible with the installed grpcio version: e.g. `protobuf>=4.0,<6`.
- Run `pip install quirk[cloud]` in CI to verify no version conflicts at install time.
- GCP connector module must use the same `GCP_AVAILABLE` flag pattern as AWS/Azure.

**Warning signs:**
- `pip install quirk` installs grpcio or protobuf without the user requesting cloud extras.
- `pip check` fails after `pip install quirk[cloud]`.
- Import of `google.cloud.kms` raises `ImportError: cannot import name 'X' from 'google.protobuf'`.

**Phase to address:** GCP connector phase — extras group design must precede any library addition.

---

### Pitfall 5: Database Probing Requires Elevated Privileges — False Negatives Without Them

**What goes wrong:**
Querying PostgreSQL's `pg_stat_ssl` to detect connection encryption requires membership in `pg_read_all_stats` (a predefined PostgreSQL role). A plain application user cannot see rows in `pg_stat_ssl` for other sessions — they only see their own connection. The scanner connects, queries `pg_stat_ssl`, gets one row (its own connection, which always uses SSL because the scanner requested it), and reports "SSL enabled" — a false positive relative to the actual server-wide encryption posture.

Similarly, detecting `ssl = on` in `pg_hba.conf` or `postgresql.conf` requires either OS-level access (not agentless) or superuser to read `pg_settings`. Without superuser, `SELECT * FROM pg_settings WHERE name = 'ssl'` may return no rows or a permission error.

For MySQL/RDS, detecting `have_ssl`, `require_secure_transport`, and encryption-at-rest status similarly requires `SHOW GLOBAL VARIABLES` which requires `REPLICATION CLIENT` or `PROCESS` privilege in MySQL 8+.

**Why it happens:**
Scanner authors test against a development database where they have superuser access. The permission requirements of production read-only credentials are not considered until deployment.

**How to avoid:**
- Explicitly require and document: `pg_read_all_stats` role grant (PostgreSQL) or `PROCESS` + `REPLICATION CLIENT` grants (MySQL) in the scanner's prerequisite documentation.
- At scan time, detect the privilege level by querying `SELECT pg_has_role(current_user, 'pg_read_all_stats', 'member')` and emit a `scan_error` field value of `"insufficient-privilege"` if the role is absent.
- Never conflate "my connection is SSL" with "server requires SSL for all connections."
- Use `SHOW server_version` and `SHOW ssl` (PostgreSQL) as unprivileged fallback checks that confirm SSL is compiled in, with a warning that server-wide enforcement cannot be confirmed without `pg_read_all_stats`.

**Warning signs:**
- Scanner always reports SSL enabled regardless of server configuration.
- Test against a restricted user reports success where a superuser test would show differences.
- `pg_stat_ssl` query returns exactly one row.

**Phase to address:** Database encryption detection phase.

---

### Pitfall 6: HashiCorp Vault KV Version Auto-Detection Failure

**What goes wrong:**
A Vault instance can have KV v1 mounts and KV v2 mounts simultaneously at different paths. The hvac client's `client.secrets.kv.v2.read_secret_version()` raises a `VaultError` against a v1 mount because v2 prepends `/data/` to the path internally and v1 does not. Conversely, calling v1 methods against a v2 mount returns 404. There is no automatic detection of which version a mount uses in hvac.

The correct approach is to call `client.sys.list_mounted_secrets_engines()` and inspect the `options.version` field of each KV mount. However, if the Vault token lacks `sys/mounts` read access (common with AppRole tokens scoped to specific paths), this call returns 403 and the connector has no way to auto-detect version.

**Why it happens:**
Documentation examples show single-version setups. Developers test against a dev Vault instance with a single KV v2 mount and assume the API is uniform.

**How to avoid:**
- Call `client.sys.list_mounted_secrets_engines()` first and record each KV mount's version.
- If `sys/mounts` is not accessible, fall back to attempting v2 first, then v1, catching `hvac.exceptions.InvalidRequest` or `hvac.exceptions.Forbidden` explicitly.
- Expose the detected version in `cloud_scan_json` so the CBOM entry is auditable.
- In config, allow the user to specify `vault_kv_version: 1` or `vault_kv_version: 2` to bypass auto-detection when they know their mount version.

**Warning signs:**
- Vault connector returns empty results against a v1 KV mount.
- `VaultError: 404` or `InvalidPath` in connector logs when scanning known-good mounts.
- Scanner configured for v2 when instance has only v1 mounts.

**Phase to address:** HashiCorp Vault connector phase.

---

### Pitfall 7: Vault Transit Key `type` Field Not Mapping to QUIRK Algorithm Names

**What goes wrong:**
The Vault Transit secrets engine `read_key` response returns a `type` field with values like `aes256-gcm96`, `chacha20-poly1305`, `ecdsa-p256`, `rsa-2048`. These are Vault's internal type names. QUIRK's `cert_pubkey_alg` field and CBOM classifier expect NIST-aligned algorithm names (`AES`, `ECDSA`, `RSA`). Without an explicit mapping table, the transit key type lands verbatim in `cert_pubkey_alg` and QUIRK's quantum-readiness scoring engine does not recognize it — the key gets classified as `UNKNOWN` and scores incorrectly.

A secondary issue: the `keys` object in the read_key response contains version numbers as string keys (e.g., `"1": 1442851412`) where the values are Unix timestamps, not key material or key sizes. Treating timestamp values as `cert_pubkey_size` (an easy integer confusion) produces nonsense values in the billions.

**Why it happens:**
The AWS connector already has `KMS_KEY_SPEC_MAP` as the precedent for this mapping. New connector authors may assume Vault uses the same naming convention or fail to build the lookup table.

**How to avoid:**
- Define a `VAULT_TRANSIT_KEY_MAP` constant before writing any endpoint construction code: `{"aes256-gcm96": ("AES", 256), "ecdsa-p256": ("ECDSA", 256), "rsa-2048": ("RSA", 2048), ...}` covering all documented Vault Transit key types.
- Never use `keys[version_number]` values as `cert_pubkey_size` — those are Unix timestamps.
- Use `data["latest_version"]` (an integer) to confirm the key is active, not for sizing.
- TDD RED test: mock a transit `read_key` response and assert that `cert_pubkey_alg` is `"RSA"` (not `"rsa-2048"`) and `cert_pubkey_size` is `2048` (not a timestamp).

**Warning signs:**
- `cert_pubkey_alg` in database contains Vault-native type strings like `"aes256-gcm96"`.
- `cert_pubkey_size` values are in billions (Unix epoch seconds).
- Scoring engine reports `UNKNOWN` algorithm for Vault transit keys.

**Phase to address:** HashiCorp Vault connector phase.

---

### Pitfall 8: Kubernetes EncryptionConfiguration — API Server vs. Direct etcd Access

**What goes wrong:**
The definitive evidence of etcd encryption-at-rest is the `--encryption-provider-config` argument on the kube-apiserver process, which is only readable by examining the node's process table or the control plane pod spec. A scanner using only the Kubernetes API (the safe, agentless path) cannot read this argument. Calling `v1_api.list_namespaced_secret()` confirms secrets exist and shows their types, but gives no information about whether etcd encrypts them at rest.

A scanner that only lists secrets and reports "found 42 secrets" without detecting whether EncryptionConfiguration is present produces a finding that is meaninglessly incomplete for a quantum-readiness audit.

**Why it happens:**
The kubernetes-client Python library targets the API server — it is the correct agentless tool. But encryption-at-rest configuration lives at the infrastructure layer (kube-apiserver manifest or process args), not the API layer.

**How to avoid:**
- For managed Kubernetes (GKE, EKS, AKS): call the respective managed API to check encryption status (e.g., GKE `get_cluster()` returns `database_encryption.state`; EKS `describe_cluster()` returns `encryptionConfig`). This is the only reliable agentless path for managed clusters.
- For self-managed clusters: attempt to read the kube-apiserver pod spec from the `kube-system` namespace (`v1_api.read_namespaced_pod()` for the apiserver static pod). The `--encryption-provider-config` flag will be in `spec.containers[0].command`. Document that this requires `pods/get` in `kube-system`.
- Always emit a `scan_error` field value of `"encryption-config-inaccessible"` when neither path succeeds, rather than silently implying encryption status is known.

**Warning signs:**
- Kubernetes scanner only enumerates secrets without any etcd encryption status field.
- `cloud_scan_json` for K8s endpoints lacks `etcd_encryption_provider` key.
- Scanner reports clean status on a cluster where etcd encryption is not configured.

**Phase to address:** Kubernetes secrets inspection phase.

---

### Pitfall 9: K8s RBAC — `list` vs. `get` on Secrets and the Namespace Scope Problem

**What goes wrong:**
`kubectl auth can-i list secrets` returns `yes` only if the ServiceAccount or kubeconfig user has ClusterRole `list` on `secrets` cluster-wide. In practice, most read-only audit accounts have `get`-only on specific namespaces. The kubernetes-client `list_namespaced_secret()` call then raises `kubernetes.client.rest.ApiException: 403` at runtime. If the scanner catches this with `except Exception` and continues silently, the finding count for K8s is zero with no indication of why.

A secondary RBAC problem: `list` on secrets grants access to all secret data in the namespace, which many cluster operators are unwilling to grant to a scanning tool. The connector design must accommodate a `get`-only, namespace-restricted mode.

**Why it happens:**
Testing against a local `kind` or `minikube` cluster with `kubectl` configured as cluster-admin hides RBAC restrictions that are standard in production clusters.

**How to avoid:**
- Catch `kubernetes.client.rest.ApiException` specifically and check `e.status == 403`. Log: "K8s RBAC insufficient — need `list` on `secrets` in namespace `X`."
- Support a `kubeconfig_namespaces` config list to restrict scanning to specific namespaces rather than requiring cluster-wide `list`.
- Document the minimum required RBAC manifest in the scanner module docstring and in the documentation phase.
- Never try to list all namespaces first (requires `list` on `namespaces` — another RBAC hurdle); instead iterate over user-configured namespaces.

**Warning signs:**
- K8s scanner returns zero results against a cluster known to have secrets.
- No `scan_error` field in K8s endpoints when credentials are present but RBAC is insufficient.
- Connector catches `ApiException` without checking `.status` attribute.

**Phase to address:** Kubernetes secrets inspection phase.

---

### Pitfall 10: Object Storage Enumeration at Scale — Per-Bucket API Calls Without Rate Limiting

**What goes wrong:**
An AWS account can have thousands of S3 buckets. `list_buckets()` returns all of them in one call (no paginator needed — unlike most boto3 operations, `list_buckets` is not paginatable and raises `OperationNotPageableError` if a paginator is attempted). But `get_bucket_encryption()` is a separate per-bucket API call. With 500 buckets, a naive loop makes 500 sequential `GetBucketEncryption` calls plus 500 `GetBucketLocation` calls — 1,000 total API calls, taking minutes and potentially hitting S3 request rate limits or IAM `GetBucketEncryption` throttling.

GCS has a similar pattern: `list_buckets()` followed by per-bucket `get_iam_policy()` calls. Azure Blob Storage requires iterating containers per storage account.

**Why it happens:**
Dev/test accounts have 5–20 buckets. The sequential-per-bucket pattern is not obviously slow until deployed against an enterprise account.

**How to avoid:**
- Use a thread pool (`concurrent.futures.ThreadPoolExecutor`) with a conservative `max_workers` (e.g. 10) to parallelize per-bucket calls while respecting rate limits.
- Apply QUIRK's existing `TokenBucket` rate limiter from `quirk/engine/rate_limiter.py` to object storage enumeration.
- Add a `max_buckets` config option that caps enumeration; emit a `scan_error` note if the limit is hit.
- Use `s3:GetEncryptionConfiguration` permission check early; emit informative error if it is missing from the IAM policy before attempting per-bucket enumeration.
- Never call `get_paginator('list_buckets')` — it does not exist; iterate the `list_buckets()` response directly.

**Warning signs:**
- S3 scanner takes more than 30 seconds on an enterprise account.
- `ClientError: Throttling` in boto3 logs.
- `OperationNotPageableError` raised on `list_buckets` paginator attempt.

**Phase to address:** Object storage audit phase.

---

### Pitfall 11: SQLite Trend Delta — Schema Changes Between Scan Sessions Break the Query

**What goes wrong:**
Trend analysis queries compare `scanned_at` timestamps across sessions to compute score deltas and new/resolved findings. If the schema between two scan sessions differs (e.g., a column added in v4.3 does not exist in an older scan's data), a GROUP BY or JOIN across sessions may silently exclude columns that are `NULL` in older rows, producing incorrect deltas.

More subtle: if `session_start` was not used consistently in older scans (the ISSUE-3 pattern), the "session boundary" — the time range used to group a scan's results — may overlap or have gaps. A naive `WHERE scanned_at BETWEEN :start AND :end` query produces phantom findings or misses real ones.

**Why it happens:**
SQLite does not enforce schema across rows; adding a column adds `NULL` for all existing rows. A trend query written against v4.3 schema fields silently returns no results for v4.2-era sessions that lack those fields.

**How to avoid:**
- Define "session" as all endpoints where `scanned_at` falls within a computed window anchored by the `MAX(scanned_at)` of the session (the existing `/api/scan/latest` approach). Do not rely on absolute timestamps for session grouping.
- Store a `scan_session_id` (e.g. UUID or ISO timestamp string) in a separate sessions table if trend analysis becomes complex. This table can be added additively via the `_ensure_identity_columns()` inspector-first pattern from `db.py`.
- Before any delta query, check that both sessions have the same schema columns for the fields being compared; skip fields absent in either session.
- Write trend queries against the minimal common schema (fields present in all historical scans), not against fields only added in v4.3.

**Warning signs:**
- Delta report shows every v4.3 finding as "new" even for hosts that were scanned in v4.2.
- `NULL` values in trend-critical columns for all endpoints from pre-v4.3 scans.
- Session boundary detection produces sessions of 0 or 1 endpoints.

**Phase to address:** Trend analysis phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Broad `except Exception` in connector scan functions | Prevents any crash from propagating | Swallows auth failures, permission errors, and API version mismatches silently | Never in new v4.3 code — catch specific exceptions and log the cause |
| Single-region GCP/cloud scan without region iteration | Simple to implement | Misses resources in other regions; enterprise GCP spans many regions | Acceptable as v1 if documented; must emit warning when multi-region is needed |
| Hardcoding `vault_kv_version = 2` | Fast implementation | Breaks against v1 mounts without clear error | Acceptable only if config exposes an override option |
| Using `psycopg2-binary` in production | Avoids native build | Binary wheels not always available for all Python versions and platforms | Acceptable for scanner use case — binary is fine, note as tech debt |
| Querying only the `default` Kubernetes namespace | Avoids RBAC complexity | Misses secrets in other namespaces | Acceptable as v1 if config exposes `kubeconfig_namespaces` list |
| Per-bucket sequential enumeration | Simple loop | Slow and throttled on enterprise accounts | Never — implement thread pool from day one |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GCP ADC | Assuming `google.cloud.kms.KeyManagementServiceClient()` works without explicit credential setup | Catch `google.auth.exceptions.DefaultCredentialsError` before first API call; log actionable setup instructions |
| GCP KMS pagination | Using direct `list_crypto_keys()` without iterating `next_page_token` | Use the client library's built-in pager: the client's list methods return iterables that handle pagination automatically |
| Vault hvac | Calling `client.is_authenticated()` and assuming token is still valid mid-scan | `is_authenticated()` only checks token presence, not expiry. Wrap individual API calls in `except hvac.exceptions.Forbidden` |
| Vault KV | Using `client.read(path)` low-level API against KV v2 (misses `/data/` prefix) | Use typed methods: `client.secrets.kv.v2.read_secret_version(path=path, mount_point=mount)` |
| Kubernetes kubeconfig | Calling `config.load_kube_config()` which reads `~/.kube/config` and fails when running as a pod or in CI | Try `config.load_incluster_config()` first; fall back to `load_kube_config(config_file=...)` with explicit path from QUIRK config |
| K8s secret base64 | Treating `secret.data` values as the actual secret content for analysis | `secret.data` values are base64-encoded; for crypto audit, only inspect key type and metadata — never log decoded secret values |
| PostgreSQL pg_stat_ssl | Joining own connection's SSL status to infer server-wide policy | Require `pg_read_all_stats` role; detect its absence before querying; emit `insufficient-privilege` finding if absent |
| MySQL encryption | Relying on `SHOW STATUS LIKE 'Ssl_cipher'` for the scanner connection as proxy for server config | Query `SHOW GLOBAL VARIABLES LIKE 'have_ssl'` and `require_secure_transport`; requires `PROCESS` or `REPLICATION CLIENT` privilege |
| S3 `list_buckets()` | Calling `get_paginator('list_buckets')` — raises `OperationNotPageableError` | S3 `list_buckets` is not paginated — iterate the returned list directly; pagination only applies to `list_objects_v2` |
| GCS bucket IAM | Calling `bucket.get_iam_policy()` without `storage.buckets.getIamPolicy` IAM permission | Catch `google.api_core.exceptions.Forbidden`; emit finding indicating IAM policy unavailable; fall back to checking `bucket.default_kms_key_name` instead |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential per-bucket encryption check | S3/GCS scan takes minutes; S3 throttling errors | Use `ThreadPoolExecutor(max_workers=10)` with QUIRK's `TokenBucket` rate limiter | More than 50 buckets in one account |
| Per-namespace K8s secret list without limit | K8s API returns thousands of secrets; scan stalls | Use `limit=100` and `continue` token pagination in `list_namespaced_secret()`; cap at configurable `max_secrets` | More than 500 secrets in one namespace |
| Vault transit key full-version enumeration | Vault with many key versions returns all version timestamps | Only read `latest_version` and `type` from `read_key`; skip version-by-version enumeration | More than 20 key versions per transit key |
| Database scanner with no connection timeout | PostgreSQL/MySQL on unreachable host blocks for OS default | Set `connect_timeout` in connection string; default to 5 seconds matching other scanner timeouts | Any unreachable DB host |
| GCP KMS full key ring enumeration | Large GCP projects with many key rings cause N+1 API calls (one per key ring to list keys) | Implement `max_key_rings` and `max_keys_per_ring` config caps | More than 10 key rings in one project |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging database connection strings including passwords | Credentials in scan logs visible to anyone with log access | Never log the full connection string; log only `host:port/dbname` with user; redact password |
| Storing Vault token in QUIRK config.yaml as plaintext | Token persists on disk; file read equals token read | Support `VAULT_TOKEN` env var as the preferred input; document that config.yaml vault token should have read-only, path-scoped policy only |
| Logging K8s `secret.data` decoded values | Secret material in scan logs | Never decode or log `secret.data` — only log metadata: `name`, `type`, `namespace`, `creation_timestamp` |
| Requesting `cluster-admin` kubeconfig for K8s scanning | Over-privilege expands blast radius of compromised scanner | Document minimum RBAC manifest requiring only `list`/`get` on `secrets` in specific namespaces |
| GCP connector requesting `roles/owner` or `roles/editor` | Over-privilege; violates least-privilege consultant workflow | Document minimum roles: `roles/cloudkms.viewer` plus `roles/storage.objectViewer`; scanner must be read-only |
| Database scanner using credentials with write access | Accidental write during scan | Require read-only DB user; document required grants per engine |

---

## "Looks Done But Isn't" Checklist

- [ ] **GCP connector:** `GCP_AVAILABLE` flag exists AND `google-cloud-kms` AND `google-cloud-storage` are in `[cloud]` extras in pyproject.toml — verify `pip install quirk[cloud]` succeeds without version conflicts
- [ ] **GCP connector:** `DefaultCredentialsError` is caught explicitly and logged with actionable text — verify by running scanner with no GCP credentials configured
- [ ] **Vault connector:** `VAULT_TRANSIT_KEY_MAP` lookup table present — verify `cert_pubkey_alg` for `rsa-2048` transit key is `"RSA"` (not `"rsa-2048"`) in database
- [ ] **Vault connector:** KV version detection attempted via `sys/mounts`; falls back gracefully if 403 — verify by testing against a v1 KV mount
- [ ] **Database probing:** Privilege detection query runs before `pg_stat_ssl` — verify scanner emits `insufficient-privilege` scan_error when connecting as a low-privilege user
- [ ] **K8s scanner:** `ApiException` with `status=403` is caught and logged with namespace and resource details — verify by running against a cluster with no `list secrets` RBAC
- [ ] **K8s scanner:** EncryptionConfiguration detection path present for managed clusters (GKE/EKS/AKS API calls) — verify `cloud_scan_json` contains `etcd_encryption_provider` key
- [ ] **Object storage:** Per-bucket calls use `ThreadPoolExecutor`, not a sequential loop — verify by checking for `concurrent.futures` import in connector
- [ ] **All new scanners:** `session_start` parameter accepted and propagated to `scanned_at` on all `CryptoEndpoint` instances — verify by grepping function signatures
- [ ] **All new scanners:** Library declared in pyproject.toml extras group matching the scanner — verify `pip install quirk` (no extras) does NOT install the library
- [ ] **Trend analysis:** Session boundary defined by shared `session_start`, not by datetime range — verify delta query does not use `BETWEEN :ts1 AND :ts2` anchored on wall clock
- [ ] **All new connectors:** New `scan_*_json` column added with inspector-first `ALTER TABLE ... ADD COLUMN` pattern — verify idempotent on existing database

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Missing dependency in pyproject.toml (ISSUE-2 repeat) | LOW | Add library to extras group in pyproject.toml; bump version; re-ship. No schema change needed. |
| Session timestamp drift (ISSUE-3 repeat) | MEDIUM | Pass `session_start` into scanner; requires `run_scan.py` edit plus test update. Existing DB rows remain with stale timestamps — trend analysis must account for schema mismatch on old rows. |
| GCP credential exception uncaught | LOW | Add specific `except DefaultCredentialsError` block with log message. No schema or behavior change. |
| grpcio/protobuf conflict in core deps | HIGH | Move GCP libs from `dependencies` to `[cloud]` extras; update all import guards; re-test all install paths. Breaking change to anyone who relied on core install providing GCP support. |
| Vault key map missing type | LOW | Add missing entry to `VAULT_TRANSIT_KEY_MAP`; no schema change; re-run scan. |
| K8s 403 swallowed silently | LOW | Add `ApiException` handler; add `scan_error` field to endpoint. Low risk — no data loss, just silent failure becomes visible. |
| Database privilege error misread as clean | MEDIUM | Add privilege detection query; update existing findings to add `insufficient-privilege` classification; existing clean findings from low-privilege scans may need to be invalidated. |
| Object storage sequential loop throttled | MEDIUM | Refactor to thread pool; no schema change; performance fix only. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Missing pyproject.toml dependency (ISSUE-2 repeat) | Every connector phase — enforce as PLAN.md requirement | `pip install quirk` (no extras) does not import the library; `pip install quirk[cloud]` does |
| Session timestamp drift (ISSUE-3 repeat) | Every scanner phase — `session_start` in function signature | All endpoints from one scan share identical `scanned_at`; API response count matches DB count |
| GCP ADC silent failure | GCP connector phase | Running connector without credentials logs actionable error and returns `[]` |
| grpcio/protobuf transitive conflict | GCP connector phase — extras group design | `pip check` passes after `pip install quirk[cloud]`; `pip install quirk` does not install grpcio |
| Database privilege false positive | Database encryption detection phase | Low-privilege user scan emits `insufficient-privilege` finding; superuser scan emits encryption status |
| Vault KV version mismatch | HashiCorp Vault connector phase | Connector tested against v1 and v2 mounts; correct findings produced for both |
| Vault transit key type not mapped | HashiCorp Vault connector phase | TDD RED test: `rsa-2048` type produces `cert_pubkey_alg="RSA"`, `cert_pubkey_size=2048` |
| K8s EncryptionConfiguration inaccessible | Kubernetes secrets phase | Endpoint has `etcd_encryption_provider` in `cloud_scan_json` or `scan_error="encryption-config-inaccessible"` |
| K8s RBAC 403 swallowed | Kubernetes secrets phase | 403 produces visible `scan_error` field and log message with namespace and resource |
| Object storage sequential throttling | Object storage audit phase | S3 scan completes under 30s on a 200-bucket account using thread pool |
| SQLite schema mismatch in trend queries | Trend analysis phase | Delta query returns correct zero-diff result for two identical scans of same host |
| Missing `scan_*_json` column | Every phase adding a new surface | `ALTER TABLE` migration runs idempotently; existing DB column not duplicated |

---

## Sources

- QUIRK v4.2 Milestone Audit Report (`.planning/v4.2-MILESTONE-AUDIT.md`) — ISSUE-2, ISSUE-3, NEW-ISSUE-1 root cause analysis
- QUIRK PROJECT.md Key Decisions table — impacket in `[identity]` extras rationale, shared `session_start` pattern
- hvac Transit documentation (python-hvac.org/en/stable/usage/secrets_engines/transit.html) — read_key response structure, key type enumeration
- Vault Transit API (developer.hashicorp.com/vault/api-docs/secret/transit) — keys object format (Unix timestamps, not key material); supported type names
- Vault KV v2 API (developer.hashicorp.com/vault/api-docs/secret/kv/kv-v2) — `/data/` path prefix requirement vs v1; v1/v2 coexistence
- google-auth exceptions (googleapis.dev/python/google-auth/latest/reference/google.auth.exceptions.html) — `DefaultCredentialsError`, `TransportError` types
- googleapis/google-cloud-python issue #13874 — grpcio-status protobuf 6.x conflict (open as of 2025)
- Kubernetes official docs (kubernetes.io/docs/concepts/configuration/secret/) — RBAC `list` vs `get` on secrets; etcd encryption-provider-config
- PostgreSQL documentation — `pg_read_all_stats` role requirement for cross-session `pg_stat_ssl` visibility
- AWS S3 boto3 documentation — `s3:GetEncryptionConfiguration` IAM permission; `list_buckets` is not paginated

---
*Pitfalls research for: QU.I.R.K. v4.3 Data at Rest — GCP, database probing, K8s, HashiCorp Vault, object storage, trend analysis*
*Researched: 2026-04-24*
