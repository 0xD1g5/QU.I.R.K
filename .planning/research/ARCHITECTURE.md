# Architecture Research

**Domain:** Cryptographic inventory scanner — v4.3 Data at Rest integration
**Researched:** 2026-04-24
**Confidence:** HIGH (based on direct codebase analysis, not training data)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          run_scan.py (orchestrator)                   │
│  Per-scanner phase blocks: each calls scan_X_targets() → List[CEP]   │
├────────────┬───────────┬──────────────┬────────────┬─────────────────┤
│  quirk/    │  quirk/   │  quirk/      │  quirk/    │  quirk/         │
│  scanner/  │  scanner/ │  scanner/    │  scanner/  │  scanner/       │
│  aws_conn. │azure_conn.│  [gcp_conn.] │ [db_scan.] │  [vault_conn.]  │
│            │           │              │            │                  │
│  scan_aws  │scan_azure │ scan_gcp     │ scan_db    │ scan_vault       │
│  _targets()│_targets() │ _targets()   │ _targets() │ _targets()       │
└─────┬──────┴─────┬─────┴──────┬───────┴──────┬─────┴────────┬────────┘
      │             │             │              │               │
      └─────────────┴─────────────┴──────────────┴───────────────┘
                                  │
                    All return List[CryptoEndpoint]
                                  │
              ┌───────────────────▼──────────────────────┐
              │          quirk/models.py                  │
              │  CryptoEndpoint (SQLAlchemy ORM row)       │
              │  • host / port / protocol / scanned_at    │
              │  • cloud_scan_json (reused for GCP)       │
              │  • [v4.3] dat_scan_json (new column)      │
              └───────────────┬──────────────────────────┘
                              │
              ┌───────────────▼──────────────────────────┐
              │          quirk/db.py                      │
              │  init_db() → _ensure_v43_columns()        │
              │  get_session() → persist endpoints         │
              └───────────────┬──────────────────────────┘
                              │
       ┌──────────────────────┴───────────────────────────────┐
       │                                                       │
┌──────▼──────────┐                              ┌────────────▼──────────┐
│ quirk/cbom/     │                              │ quirk/intelligence/   │
│ builder.py +    │                              │ evidence.py           │
│ classifier.py   │                              │ + scoring.py          │
│                 │                              │                       │
│ elif protocol   │                              │ new counters:         │
│ == "DATABASE"   │                              │ db_unencrypted_count  │
│ elif protocol   │                              │ k8s_plaintext_secrets │
│ == "K8S"        │                              │ vault_weak_key_count  │
│ elif protocol   │                              │ -> compute_readiness_ │
│ == "VAULT"      │                              │    score() new weights│
└──────┬──────────┘                              └────────────┬──────────┘
       │                                                      │
       └────────────────────────┬─────────────────────────────┘
                                │
              ┌─────────────────▼───────────────────────────────────────┐
              │         quirk/dashboard/api/routes/scan.py               │
              │  _derive_findings() -- new DAR source branches           │
              │  _derive_dat_findings() -- new function (mirror identity)│
              │  _derive_cbom() -- parse dat_scan_json columns           │
              │  GET /api/scan/latest -- adds dat_findings[]             │
              └─────────────────┬───────────────────────────────────────┘
                                │
              ┌─────────────────▼───────────────────────────────────────┐
              │         quirk/dashboard/api/routes/trends.py (NEW)       │
              │  GET /api/trends -- cross-session delta query            │
              │  Queries CryptoEndpoint table across scan timestamps      │
              └─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | File Location |
|-----------|----------------|---------------|
| GCP connector | Cloud KMS key specs, Cloud SQL TLS config, GCS bucket encryption | `quirk/scanner/gcp_connector.py` (new) |
| DB scanner | PostgreSQL/MySQL/RDS encryption-at-rest settings | `quirk/scanner/db_scanner.py` (new) |
| Object storage scanner | S3/Blob/GCS bucket encryption policies | `quirk/scanner/object_storage_scanner.py` (new) |
| K8s scanner | etcd EncryptionConfiguration, secret types | `quirk/scanner/k8s_scanner.py` (new) |
| Vault connector | Transit keys, PKI mounts, auth method audit | `quirk/scanner/vault_connector.py` (new) |
| Trend reporter | Cross-session delta, score delta, new/resolved findings | `quirk/intelligence/trends.py` (new) |
| Trend API route | GET /api/trends endpoint | `quirk/dashboard/api/routes/trends.py` (new) |
| CryptoEndpoint model | ORM row; extended with `dat_scan_json` column | `quirk/models.py` (extend) |
| db.py | `_ensure_v43_columns()` for additive migration | `quirk/db.py` (extend) |
| evidence.py | New DAR counters fed into subscore | `quirk/intelligence/evidence.py` (extend) |
| scoring.py | New DAR weights in SCORE_WEIGHTS / PROFILE_MULTIPLIERS | `quirk/intelligence/scoring.py` (extend) |
| cbom/builder.py | elif branches for DATABASE / K8S / VAULT protocols | `quirk/cbom/builder.py` (extend) |
| cbom/classifier.py | New algorithm entries for Vault transit key specs, K8s secretbox | `quirk/cbom/classifier.py` (extend) |
| config.py | New ConnectorsCfg fields for GCP/DB/K8s/Vault | `quirk/config.py` (extend) |
| schemas.py | DatFinding Pydantic model, TrendResponse model | `quirk/dashboard/api/schemas.py` (extend) |
| scan.py API route | `_derive_dat_findings()`, `dat_findings[]` in response | `quirk/dashboard/api/routes/scan.py` (extend) |
| run_scan.py | Phase blocks for each new scanner, `dat_endpoints` aggregate | `run_scan.py` (extend) |

---

## Recommended Project Structure

```
quirk/
├── scanner/
│   ├── aws_connector.py          # existing
│   ├── azure_connector.py        # existing
│   ├── gcp_connector.py          # NEW: Cloud KMS, Cloud SQL, GCS
│   ├── db_scanner.py             # NEW: PostgreSQL, MySQL, RDS
│   ├── object_storage_scanner.py # NEW: S3, Azure Blob, GCS policies
│   ├── k8s_scanner.py            # NEW: etcd EncryptionConfiguration
│   └── vault_connector.py        # NEW: HashiCorp Vault transit/PKI/auth
├── intelligence/
│   ├── evidence.py               # EXTEND: DAR counters
│   ├── scoring.py                # EXTEND: DAR score weights
│   ├── trends.py                 # NEW: cross-session delta queries
│   └── ... (existing)
├── cbom/
│   ├── builder.py                # EXTEND: DATABASE/K8S/VAULT elif branches
│   └── classifier.py             # EXTEND: Vault/K8s algorithm entries
├── dashboard/api/
│   ├── schemas.py                # EXTEND: DatFinding, TrendResponse
│   └── routes/
│       ├── scan.py               # EXTEND: _derive_dat_findings()
│       └── trends.py             # NEW: GET /api/trends
├── models.py                     # EXTEND: dat_scan_json column
├── db.py                         # EXTEND: _ensure_v43_columns()
└── config.py                     # EXTEND: ConnectorsCfg v4.3 fields

run_scan.py                       # EXTEND: 5 new phase blocks + endpoint aggregation
```

### Structure Rationale

- **scanner/ new files:** Each scanner surface is its own module — consistent with aws_connector.py and azure_connector.py. Never merge multiple surfaces into one file; each has distinct optional dependencies, distinct optional-import guards, and distinct test fixtures.
- **object_storage_scanner.py as its own file:** S3, Blob, and GCS share a "bucket encryption policy" shape but each requires distinct SDK calls. One file keeps the DAR-surface boundary clean and avoids merging incompatible optional-import guards.
- **intelligence/trends.py:** Trend analysis is a query/analytics concern, not a scanner concern. It reads existing CryptoEndpoint rows across timestamps — it belongs in intelligence/, not scanner/.
- **routes/trends.py:** Follows the scan.py route pattern; a separate file rather than bolting onto scan.py keeps route modules single-responsibility.

---

## Architectural Patterns

### Pattern 1: Scanner Module Contract

Every new scanner follows the aws_connector.py pattern exactly.

**What:** A module with one public function `scan_X_targets(...) -> List[CryptoEndpoint]`. The function degrades gracefully when an optional SDK is absent. It uses protocol strings (e.g., `"GCP"`, `"DATABASE"`, `"K8S"`, `"VAULT"`) on the CryptoEndpoint. All raw data goes into `dat_scan_json` (or `cloud_scan_json` for GCP). The `cert_pubkey_alg` and `cert_pubkey_size` fields carry the encryption algorithm/key-size for CBOM classification.

**When to use:** All five new scanner surfaces.

**GCP follows the cloud_scan_json convention:**
```python
# quirk/scanner/gcp_connector.py
try:
    from google.cloud import kms_v1
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

def scan_gcp_targets(project_id: str, logger=None) -> List[CryptoEndpoint]:
    if not GCP_AVAILABLE:
        if logger:
            logger.v("google-cloud-kms not installed -- GCP scanning unavailable")
        return []
    results = []
    results.extend(_scan_cloud_kms(project_id, logger))
    results.extend(_scan_cloud_sql_tls(project_id, logger))
    results.extend(_scan_gcs_encryption(project_id, logger))
    return results
```

**Key field assignments per surface:**

| Surface | protocol | host | port | JSON column | service_detail |
|---------|----------|------|------|-------------|----------------|
| GCP KMS | `"GCP"` | resource name | 0 | `cloud_scan_json` | `"CloudKMS"` |
| GCP Cloud SQL | `"GCP"` | instance connection name | 0 | `cloud_scan_json` | `"CloudSQL"` |
| GCP GCS | `"GCP"` | bucket URI | 0 | `cloud_scan_json` | `"GCS"` |
| Database | `"DATABASE"` | DB endpoint hostname | 5432/3306 | `dat_scan_json` | `"PostgreSQL"` / `"MySQL"` / `"RDS"` |
| Object Storage | `"STORAGE"` | bucket ARN/URI | 0 | `dat_scan_json` | `"S3"` / `"AzureBlob"` / `"GCS"` |
| Kubernetes | `"K8S"` | API server URL | 6443 | `dat_scan_json` | `"etcd-secrets"` |
| Vault | `"VAULT"` | Vault server URL | 8200 | `dat_scan_json` | `"transit"` / `"pki"` / `"auth"` |

**Trade-offs:** Using `cert_pubkey_alg` for encryption-at-rest algorithm is a deliberate field reuse. The field name is TLS-centric but the CBOM classifier and evidence counters already read it generically. Adding a new column for `encryption_alg` would require touching every consumer. Reuse is correct here given the consulting-scale data model.

### Pattern 2: Column Reuse vs. New Column

**What:** GCP reuses `cloud_scan_json` (protocol `"GCP"` is a cloud surface like AWS/Azure). The DB, Object Storage, K8s, and Vault scanners use a new `dat_scan_json` column because they represent a distinct surface category.

**Additive migration in db.py:**
```python
_DAT_COLUMNS = ["dat_scan_json"]

def _ensure_v43_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _DAT_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

Call `_ensure_v43_columns(engine)` from `init_db()` after the existing `_ensure_identity_columns()` call. This is the established pattern from v4.2 (identity columns).

### Pattern 3: Evidence Counter to Scoring Weight

The identity surface established this pattern in v4.2. DAR follows the same path.

**New counters to add to evidence.py `_PROTOCOL_KEYS` and loop:**
```python
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "DATABASE", "STORAGE", "K8S", "VAULT")  # v4.3 additions

# In build_evidence_summary() loop:
elif proto == "DATABASE":
    if ep.dat_scan_json:
        _db_data = json.loads(ep.dat_scan_json)
        if _db_data.get("ssl_mode") in ("disable", "none", "off"):
            db_unencrypted_count += 1
        if not _db_data.get("storage_encrypted"):
            db_unencrypted_at_rest_count += 1

elif proto == "K8S":
    if ep.cert_pubkey_alg == "identity":  # plaintext etcd = CRITICAL
        k8s_plaintext_secrets_count += 1

elif proto == "VAULT":
    _alg = str(getattr(ep, "cert_pubkey_alg", "") or "").lower()
    if _alg in ("aes128-gcm96",):
        vault_weak_key_count += 1
```

**New weight entries in scoring.py:**
```python
# Add to SCORE_WEIGHTS -- prefixed "dar_" so PROFILE_MULTIPLIERS can target them
"dar_db_unencrypted_ratio": 12.0,
"dar_k8s_plaintext_secrets_ratio": 15.0,
"dar_vault_weak_key_ratio": 8.0,
```

**New multiplier prefix in PROFILE_MULTIPLIERS:**
```python
PROFILE_MULTIPLIERS = {
    "strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.3},
    "balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7},
}
```

### Pattern 4: Trend Analysis Architecture

**What:** Trend analysis is a pure read-query concern over the existing `crypto_endpoints` table. It does not require a new table. It queries the last N scan sessions using the same second-truncation grouping used by `list_scans()` in scan.py, then diffs them in Python.

**Implementation location:** `quirk/intelligence/trends.py`

**Core function signature:**
```python
def compute_trend_report(
    session: Session,
    *,
    sessions_back: int = 2,
) -> Dict[str, Any]:
    """Compare the two most recent scan sessions and return delta report.

    Returns:
        {
          "sessions": [{"scan_id": ..., "score": N}, ...],
          "score_delta": +5 / -3 / 0,
          "new_findings": [...],        # host:port pairs absent in prev, present now
          "resolved_findings": [...],   # host:port pairs present in prev, absent now
          "degraded_hosts": [...],      # hosts whose severity worsened
        }
    """
```

**API exposure:** `quirk/dashboard/api/routes/trends.py` with `GET /api/trends?sessions=2`

**No new SQLite table needed.** The existing `scanned_at` timestamp grouping provides the session boundary. Two queries, each fetching one session's endpoints, then Python-side diff. Fast at consulting scale.

### Pattern 5: Identity Tab to DAR Tab Dashboard Pattern

The Identity tab (Phase 21) established the pattern for adding a new surface tab in React. The DAR surface follows the same pattern:

1. Add `DatFinding` Pydantic model to `schemas.py`
2. Add `dat_findings: List[DatFinding] = []` to `ScanLatestResponse`
3. Implement `_derive_dat_findings(endpoints)` in `scan.py` (mirrors `_derive_identity_findings`)
4. Add `dat_findings` to the `return ScanLatestResponse(...)` call
5. React: add `DatFinding` TypeScript type mirroring the Pydantic model
6. React: add "Data at Rest" tab component reading `dat_findings[]`

---

## Data Flow

### New Scanner to Dashboard Data Flow

```
run_scan.py
    gcp_endpoints   = scan_gcp_targets(project_id, logger)
    db_endpoints    = scan_db_targets(db_targets, logger)
    obj_endpoints   = scan_object_storage_targets(obj_targets, logger)
    k8s_endpoints   = scan_k8s_targets(k8s_targets, logger)
    vault_endpoints = scan_vault_targets(vault_targets, logger)

    endpoints = (...existing... + gcp_endpoints + db_endpoints
                 + obj_endpoints + k8s_endpoints + vault_endpoints)
        |
        v
    session.add(ep) for ep in endpoints   --> SQLite crypto_endpoints table
        |
        v
    GET /api/scan/latest
        |
        +-> _derive_findings(endpoints)         --> FindingItem list (existing + DAR branches)
        +-> _derive_dat_findings(endpoints)     --> DatFinding list (NEW)
        +-> build_evidence_summary(endpoints)   --> evidence dict (+ DAR counters)
        +-> compute_readiness_score(evidence)   --> score (+ DAR weights)
        +-> _derive_cbom(endpoints)             --> CbomComponent list (+ DATABASE/K8S/VAULT)
        +-> ScanLatestResponse(dat_findings=..) --> React "Data at Rest" tab
```

### Trend Data Flow

```
GET /api/trends?sessions=2
    |
    v
trends.py route --> compute_trend_report(db_session, sessions_back=2)
    |
    +-> Query session timestamps (last 2 using list_scans logic)
    +-> Load endpoints for each session
    +-> Re-run build_evidence_summary per session --> per-session score
    +-> Python diff: new hosts, resolved hosts, score delta
        |
        v
    TrendResponse (new Pydantic model in schemas.py)
        |
        v
    React "Trends" tab: score sparkline, new/resolved finding counts
```

### Configuration to Scanner Activation Flow

```
config.yaml
    connectors:
      enable_gcp: true
      gcp_project_id: "my-project"
      enable_db: true
      db_targets:
        - {host: "db.example.com", port: 5432, engine: "postgresql"}
      enable_object_storage: true
      enable_k8s: true
      k8s_targets: ["https://k8s-api:6443"]
      enable_vault: true
      vault_targets: ["https://vault.example.com"]

ConnectorsCfg (config.py)       <- new fields added (enable flags + target lists)
    |
run_scan.py phase blocks        <- each checked with cfg.connectors.enable_X
    |
scan_X_targets(...)             <- called if enabled, returns [] if SDK absent
```

---

## Integration Points: Explicit New vs. Modified Files

### New Files (7 total)

| File | Purpose |
|------|---------|
| `quirk/scanner/gcp_connector.py` | GCP Cloud KMS / Cloud SQL TLS / GCS encryption |
| `quirk/scanner/db_scanner.py` | PostgreSQL / MySQL / RDS encryption-at-rest |
| `quirk/scanner/object_storage_scanner.py` | S3 / Azure Blob / GCS bucket encryption policies |
| `quirk/scanner/k8s_scanner.py` | K8s etcd EncryptionConfiguration |
| `quirk/scanner/vault_connector.py` | HashiCorp Vault transit keys / PKI mounts / auth |
| `quirk/intelligence/trends.py` | Cross-session delta computation |
| `quirk/dashboard/api/routes/trends.py` | GET /api/trends FastAPI route |

### Extended Files (additive changes only)

| File | Change |
|------|--------|
| `quirk/models.py` | Add `dat_scan_json = Column(Text, nullable=True)` in v4.3 section |
| `quirk/db.py` | Add `_ensure_v43_columns()`, call from `init_db()` after `_ensure_identity_columns()` |
| `quirk/config.py` | Add ~10 new fields to `ConnectorsCfg`: `enable_gcp`, `gcp_project_id`, `enable_db`, `db_targets`, `enable_object_storage`, `object_storage_targets`, `enable_k8s`, `k8s_targets`, `enable_vault`, `vault_targets` |
| `quirk/intelligence/evidence.py` | Add protocol keys for DATABASE/STORAGE/K8S/VAULT; add 3 new counters; add new ratios to return dict |
| `quirk/intelligence/scoring.py` | Add `"dar_"` prefixed weights to `SCORE_WEIGHTS`; add `"dar_"` prefix to `PROFILE_MULTIPLIERS` |
| `quirk/cbom/builder.py` | Add `elif protocol in ("DATABASE", "STORAGE", "K8S", "VAULT")` branches in algorithm extraction |
| `quirk/cbom/classifier.py` | Add Vault key type entries (`aes256-gcm96`, `aes128-gcm96`, `chacha20-poly1305@vault`); add K8s `secretbox` and `identity` entries |
| `quirk/dashboard/api/schemas.py` | Add `DatFinding` model; add `TrendResponse` model; extend `ScanLatestResponse` with `dat_findings: List[DatFinding] = []` |
| `quirk/dashboard/api/routes/scan.py` | Add `_derive_dat_findings()` function; add `dat_findings` to `ScanLatestResponse` return |
| `quirk/dashboard/api/app.py` | Register `/api/trends` router from `routes/trends.py` |
| `run_scan.py` | Add 5 scanner phase blocks (gcp, db, obj_storage, k8s, vault); include all new endpoint lists in aggregation |

---

## SQLite Schema Impact

### New Column

```
crypto_endpoints.dat_scan_json TEXT  -- v4.3 data-at-rest scan JSON blob
```

Installed by `_ensure_v43_columns()` using the same inspector-first, ALTER TABLE pattern as `_ensure_identity_columns()`. Idempotent. Safe to run against existing databases from v4.2 and earlier.

GCP does NOT need a new column — it reuses `cloud_scan_json` using protocol `"GCP"`.

### No New Tables

Trend analysis reads across existing `crypto_endpoints` rows grouped by `scanned_at` second window. The existing `list_scans()` pattern (strftime grouping) is the session boundary mechanism — no additional bookkeeping table needed.

---

## Build Order Across the 6 Features

Dependencies drive the order:

```
Phase 25: Identity Accuracy (carry-over from v4.2)
  - No schema change; adds ldap3 to pyproject.toml + RS-family branch in
    _derive_identity_findings(). Standalone — no v4.3 DAR dependencies.

Phase 26: GCP Connector
  - Reuses cloud_scan_json (existing column) and "GCP" protocol string.
  - Follows aws_connector.py exactly. No schema change required.
  - Dependencies: None beyond Phase 25.

Phase 27: Database Encryption Detection
  - Introduces dat_scan_json column and _ensure_v43_columns() in db.py.
  - This column is shared by Object Storage, K8s, and Vault scanners.
    Must come FIRST among DAR scanner phases.
  - Introduces "DATABASE" protocol + "dar_" subscore weights in scoring.py.
  - Dependencies: None beyond Phase 25/26.

Phase 28: Object Storage Audit
  - Reuses dat_scan_json column (installed by Phase 27).
  - Adds "STORAGE" protocol for S3/Blob/GCS policy endpoints.
  - Dependencies: Phase 27 (dat_scan_json column must exist).

Phase 29: Kubernetes Secrets Inspection
  - Reuses dat_scan_json column. Adds "K8S" protocol.
  - "identity" provider in EncryptionConfiguration = plaintext = CRITICAL.
  - Dependencies: Phase 27 (dat_scan_json column must exist).

Phase 30: HashiCorp Vault Connector
  - Reuses dat_scan_json column. Adds "VAULT" protocol.
  - hvac client with VAULT_TOKEN env var or config field.
  - Transit key types map directly to classifier.py entries.
  - Dependencies: Phase 27 (dat_scan_json column must exist).

Phase 31: Trend Analysis
  - Pure read over existing CryptoEndpoint rows — no schema change.
  - Requires DAR scanner phases to produce data worth trending.
  - New trends.py + routes/trends.py + React Trends tab.
  - Dependencies: All scanner phases complete for meaningful data.
```

**Phase 28 and 29 are independent once Phase 27 is complete** — they can be developed in parallel if desired. Phase 30 benefits from the K8s patterns but has no strict code dependency on Phase 29.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 consultant, 1 client | Current SQLite model is correct. No changes needed. |
| 10 concurrent clients | Still fine. SQLite WAL mode + single-writer pattern holds. |
| SaaS (future milestone) | Replace SQLite with PostgreSQL. Trend queries need index on scanned_at. Scanner phase blocks become Celery tasks. |

---

## Anti-Patterns

### Anti-Pattern 1: Separate Table for Each Scanner Surface

**What people do:** Create `db_encryption_results`, `k8s_secrets_results` tables.

**Why it's wrong:** The CBOM pipeline, evidence layer, and dashboard API all iterate `CryptoEndpoint` rows. A separate table means every consumer needs to join or separately query it. The current architecture's strength is that all surfaces flow through one table — breaking that requires touching every consumer.

**Do this instead:** Add `dat_scan_json` to `crypto_endpoints` and use `protocol` + `service_detail` as discriminators. The JSON blob captures all surface-specific detail without a new table.

### Anti-Pattern 2: Merging Multiple Scanner Surfaces Into One File

**What people do:** Put db_scanner, k8s_scanner, and vault_connector into a single `dat_scanners.py`.

**Why it's wrong:** Each scanner has distinct dependencies (psycopg2, kubernetes, hvac), distinct optional-import guards, and distinct test fixtures. Merging them means a failure in one surface's optional-import guard breaks all. It also violates the single-responsibility established by aws_connector.py and azure_connector.py.

**Do this instead:** One file per scanner surface. Each file handles its own optional import guard, `SDK_AVAILABLE` flag, and graceful degradation.

### Anti-Pattern 3: Computing Trend Deltas at Write Time

**What people do:** Store `is_new_this_scan=True` in the CryptoEndpoint row at insert time.

**Why it's wrong:** "New" is a relative comparison that depends on which sessions you're comparing. A finding that was "new" in session 3 is no longer "new" in session 4. Baking this into the row loses the ability to compare arbitrary session pairs and creates stale state.

**Do this instead:** Compute trend deltas at query time in `trends.py`, comparing the endpoint sets of two sessions in Python. The data is already in `crypto_endpoints` — no write-time bookkeeping needed.

### Anti-Pattern 4: Checking SDK Availability With Exception-for-Control-Flow Inside Functions

**What people do:** `try: import hvac; except ImportError: return []` inside the scan function body on every call.

**Why it's wrong:** The pattern established in aws_connector.py is: optional import at module level, module-level `SDK_AVAILABLE = True/False` flag, function checks the flag early and returns. This is correct and avoids repeated import attempts.

**Do this instead:**
```python
try:
    import hvac
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False

def scan_vault_targets(...):
    if not HVAC_AVAILABLE:
        return []
    ...
```

### Anti-Pattern 5: Skipping the CBOM elif Branch for New Protocols

**What people do:** Wire up a new scanner that produces `protocol="DATABASE"` endpoints but forget to add the elif branch in `cbom/builder.py`, so those endpoints appear as UNKNOWN in the CBOM.

**Why it's wrong:** The CBOM is a primary deliverable. Missing scanner coverage in the CBOM means the consultant's deliverable to the client is incomplete — database encryption posture won't appear in the CycloneDX output.

**Do this instead:** For each new protocol string added, immediately add the corresponding elif branch in `builder.py` and the corresponding algorithm entries in `classifier.py` before marking the phase complete.

---

## Sources

- Direct codebase analysis: `quirk/scanner/aws_connector.py`, `quirk/scanner/azure_connector.py`, `quirk/scanner/kerberos_scanner.py` (scanner contract pattern)
- Direct codebase analysis: `quirk/models.py` (CryptoEndpoint schema — all existing columns)
- Direct codebase analysis: `quirk/db.py` (additive migration pattern via `_ensure_identity_columns`)
- Direct codebase analysis: `quirk/intelligence/evidence.py` + `scoring.py` (counter to weight pattern)
- Direct codebase analysis: `quirk/cbom/builder.py` + `classifier.py` (CBOM pipeline, elif branch pattern)
- Direct codebase analysis: `quirk/dashboard/api/routes/scan.py` (`_derive_identity_findings` identity tab pattern, `list_scans` session grouping)
- Direct codebase analysis: `quirk/dashboard/api/schemas.py` + `run_scan.py` (orchestration and API contract)
- Direct codebase analysis: `quirk/config.py` (`ConnectorsCfg` enable-flag + target-list pattern)
- Direct codebase analysis: `pyproject.toml` (optional dependency extras pattern)
- Project context: `.planning/PROJECT.md` v4.3 requirements

---
*Architecture research for: QU.I.R.K. v4.3 Data at Rest integration*
*Researched: 2026-04-24*
